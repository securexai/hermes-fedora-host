"""Prepare an encrypted-backup-bound B7 candidate using a public synthetic credential.

Runs as the enrolled certifier. It never requests a provider credential and never
claims UA acceptance. The operator session retains cleanup ownership.
"""
import argparse
from pathlib import Path
import tempfile

from certify import Certifier, archive_candidate
from common import canonical, decode, digest, protected_file, report, require, atomic
from gates import backup_snapshot


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    args = parser.parse_args()
    config = decode(protected_file(args.config, 0).read_bytes())
    certifier = Certifier(config)
    with tempfile.TemporaryFile() as archive:
        archive_candidate(Path(config['candidate']), certifier.raw, certifier.manifest, archive)
        certifier.exchange(certifier.frame('stage'), archive)
    certifier.request('seed')
    receipt = certifier.request('snapshot')
    with tempfile.TemporaryDirectory(prefix='hermes-b7-', dir='/dev/shm') as scratch:
        source = Path(scratch) / 'snapshot.tar'
        with source.open('xb') as output:
            source.chmod(0o600); certifier.exchange(certifier.frame('backup'), output=output)
        require(digest(source) == receipt['snapshot_sha256'], 'snapshot-hash-mismatch')
        backup = backup_snapshot(source, config, certifier.manifest['release_id'])
        backup['source_path'] = str(source)
        atomic(Path(config['state_dir']) / 'backup.json', canonical(backup))
    certifier.request('backup-verified', backup_snapshot=backup['snapshot'], snapshot_sha256=backup['sha256'])
    certifier.request('credential', key='hermes-public-b7-canary-' + config['run_id'])
    # No lease field: cleanup cannot mistake the canary for a provider credential.
    certifier.save('b7-operator-ready', provider_credential_issued=False)
    return {'ok': True, 'stage': 'b7-operator-ready', 'run_id': config['run_id']}


if __name__ == '__main__': report(main)
