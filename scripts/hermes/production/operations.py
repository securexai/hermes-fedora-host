"""Durable stopped-state transactions. Recovery runs before any new mutation."""

from pathlib import Path
from time import monotonic
from uuid import uuid4

from .primitives import Refused, atomic, canonical, read_json, require


class Transaction:
    def __init__(self, root, backend):
        self.root, self.backend = Path(root), backend
        self.journal = self.root / "journal.json"

    def save(self, row, stage):
        row["stage"] = stage
        # Publish a terminal journal only after its per-attempt evidence persists.
        atomic(self.root / "attempts" / (row["id"] + ".json"), canonical(row))
        atomic(self.journal, canonical(row))

    def recover(self):
        if not self.journal.exists():
            return
        row = read_json(self.journal)
        require(row.get("protocol", 1) == 1, "incompatible-transaction-protocol")
        if row["stage"] in ("committed", "recovered", "aborted"):
            return
        pending = dict(row)
        phase = "stop"
        try:
            self.backend.stop()
            if row["stage"] in ("prepared", "stopped"):
                # No application mutation started. An unfinished snapshot is retained.
                phase = "activation"
                self.backend.restart_previous(row["previous"])
                phase = "verification"
                if row["previous"]:
                    self.backend.verify(row["previous"])
                terminal = "aborted"
            else:
                require(
                    row["previous"] is not None and row["snapshot"] is not None,
                    "initial-install-incomplete-private-recovery-required",
                )
                phase = "restore"
                # Never restart old images on the attempted version's state.
                self.backend.restore(row["snapshot"], row["previous"])
                phase = "activation"
                self.backend.activate(row["previous"])
                phase = "verification"
                self.backend.verify(row["previous"])
                phase = "current-pointer"
                self.backend.set_current(row["previous"])
                terminal = "recovered"
            phase = "finalization"
            self.save(row, terminal)
        except BaseException:
            # Cleanup must run even if activation partially started both services
            # or a durable pointer/evidence write failed after verification.
            stopped = False
            try:
                self.backend.stop()
                stopped = True
            except BaseException:
                pass
            evidence = pending | {"recovery_phase": phase, "services_stopped": stopped}
            failures = []
            for path, value in (
                (self.journal, pending),
                (self.root / "attempts" / (row["id"] + ".json"), pending),
                (
                    self.root
                    / "attempts"
                    / (row["id"] + ".recovery-failed-" + uuid4().hex + ".json"),
                    evidence,
                ),
            ):
                try:
                    atomic(path, canonical(value))
                except BaseException:
                    failures.append("journal" if path == self.journal else "evidence")
            if not stopped or failures:
                reason = "recovery-failed"
                if not stopped:
                    reason += ":service-stop-failed-safety-unconfirmed"
                if failures:
                    reason += ":retention-failed-" + ",".join(failures)
                raise Refused(reason) from None
            raise

    def deploy(self, candidate, *, upgrade=False):
        self.recover()
        previous = self.backend.current()
        self.backend.prepare(candidate, previous)
        if previous == candidate:
            self.backend.verify(candidate)
            return {"status": "UNCHANGED", "release": candidate}
        require(previous is None or upgrade, "use-explicit-upgrade")
        row = {
            "protocol": 1,
            "id": uuid4().hex,
            "previous": previous,
            "candidate": candidate,
            "snapshot": None,
            "timings": {},
        }
        self.save(row, "prepared")
        try:
            started = monotonic()
            self.backend.stop()
            self.save(row, "stopped")
            if previous:
                row["snapshot"] = self.backend.snapshot(row["id"], previous)
            row["timings"]["stopped_backup"] = monotonic() - started
            self.save(row, "backed_up")
            for stage, action in (
                ("import", self.backend.import_images),
                ("configuration", self.backend.configure),
                ("restart", self.backend.activate),
                ("verification", self.backend.verify),
            ):
                self.save(row, stage)
                started = monotonic()
                action(candidate)
                row["timings"][stage] = monotonic() - started
            # Journal remains recoverable until BOTH current pointer and commit persist.
            self.backend.set_current(candidate)
            self.save(row, "committed")
            return {"status": "CHANGED", "release": candidate, "timings": row["timings"]}
        except BaseException:
            # Do not include exception strings: upstream failures may contain credentials.
            atomic(self.root / "attempts" / (row["id"] + ".failed.json"), canonical(row))
            self.recover()
            raise

    def rollback(self):
        self.recover()
        row = read_json(self.journal)
        if row["stage"] == "recovered":
            self.backend.verify(row["previous"])
            return {"status": "UNCHANGED", "release": row["previous"]}
        require(
            row["stage"] == "committed" and row["previous"] and row["snapshot"],
            "no-matching-rollback-snapshot",
        )
        # A rollback itself is recoverable, and retains the failed version's state.
        self.save(row, "rollback")
        self.recover()
        return {"status": "ROLLED_BACK", "release": row["previous"]}
