#!/usr/bin/env python3
"""Exercise shipped memory approval handlers in a disposable, credential-free profile.

Run with the pinned gateway's Python, working directory /opt/hermes. No model or
messaging API is called. Never reads or approves the operator's existing queue.
"""

import asyncio
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace


def main():
    with tempfile.TemporaryDirectory(prefix="hermes-memory-approval-") as directory:
        os.environ["HERMES_HOME"] = directory
        home = Path(directory)
        (home / "config.yaml").write_text(
            "memory:\n  write_approval: true\n  memory_enabled: true\n"
            "  user_profile_enabled: true\n", encoding="utf-8"
        )
        # Imports must follow profile isolation: some shipped modules cache config.
        sys.path.insert(0, "/opt/hermes")
        from gateway.slash_commands import GatewaySlashCommandsMixin
        from hermes_cli.cli_commands_mixin import CLICommandsMixin
        from tools import write_approval
        from tools.memory_tool import load_on_disk_store, memory_tool

        assert write_approval.write_approval_enabled("memory")

        def dispatch(channel, command):
            if channel == "cli":
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    CLICommandsMixin._handle_memory_command(
                        SimpleNamespace(agent=None), "/memory " + command
                    )
                return output.getvalue()
            event = SimpleNamespace(get_command_args=lambda: command)
            runner = SimpleNamespace(_write_approval_setter=lambda *_: None)
            return asyncio.run(
                GatewaySlashCommandsMixin._handle_memory_command(runner, event)
            )

        def stage(content):
            result = json.loads(memory_tool(
                action="add", target="memory", content=content,
                store=load_on_disk_store(),
            ))
            assert result.get("staged") is True, result
            assert "Not yet saved" in result["message"], result
            assert write_approval.get_pending("memory", result["pending_id"])
            return result["pending_id"]

        for channel in ("cli", "gateway"):
            content = f"Synthetic {channel} approval regression marker."
            pending_id = stage(content)
            memory = home / "memories" / "MEMORY.md"
            assert not memory.exists() or content not in memory.read_text()
            assert pending_id in dispatch(channel, "pending")
            response = dispatch(channel, "approve " + pending_id)
            assert "Approved 1 memory write(s)." in response, response
            assert content in memory.read_text()
            assert write_approval.get_pending("memory", pending_id) is None

            rejected = f"Synthetic {channel} rejected regression marker."
            pending_id = stage(rejected)
            assert "Rejected pending memory write" in dispatch(
                channel, "reject " + pending_id
            )
            assert rejected not in memory.read_text()
            assert write_approval.get_pending("memory", pending_id) is None
            print(f"{channel.upper()}_STAGE_APPROVE_REJECT=PASS")

        subprocess.run([
            sys.executable, "-c",
            "from tools.memory_tool import load_on_disk_store; "
            "s=load_on_disk_store(); "
            "text=s.format_for_system_prompt('memory'); "
            "assert 'Synthetic cli approval regression marker.' in text; "
            "assert 'Synthetic gateway approval regression marker.' in text; "
            "assert 'rejected regression marker' not in text; "
            "print('FRESH_PROCESS_MEMORY_RECALL=PASS')",
        ], cwd="/opt/hermes", check=True)
        assert write_approval.list_pending("memory") == []
        assert write_approval.write_approval_enabled("memory")
        print("APPROVAL_GATE_PRESERVED=PASS")
    print("MEMORY_APPROVAL_PROBE=PASS")


if __name__ == "__main__":
    main()
