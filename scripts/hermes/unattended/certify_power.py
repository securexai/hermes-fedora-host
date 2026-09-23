"""Root-owned, fixed-domain power helper for the unprivileged lab certifier."""
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

DOMAIN = 'lab-hermes-server'
UUID = '4db6369a-2b8b-427f-a47a-a5d83bb40cff'
DISK = '/var/lib/libvirt/images/hermes-tpm-lab/lab-hermes-server.qcow2'


def main():
    assert os.geteuid() == 0 and len(sys.argv) == 1
    raw = sys.stdin.buffer.readline(1025)
    assert len(raw) <= 1024 and raw.endswith(b'\n')
    value = json.loads(raw)
    assert set(value) == {'action'} and value['action'] in {'state', 'shutdown', 'start'}
    base = ['/usr/bin/virsh', '-c', 'qemu:///system']
    root = ET.fromstring(subprocess.check_output(base + ['dumpxml', DOMAIN], timeout=15))
    assert root.findtext('name') == DOMAIN and root.findtext('uuid') == UUID
    disks = root.findall('./devices/disk')
    assert len(disks) == 1 and disks[0].get('device') == 'disk'
    assert disks[0].find('source').get('file') == DISK
    if value['action'] != 'state':
        subprocess.run(base + [value['action'], DOMAIN], check=True, timeout=30, stdout=subprocess.DEVNULL)
    state = subprocess.check_output(base + ['domstate', DOMAIN], timeout=15).decode().strip()
    print(json.dumps({'ok': True, 'domain_uuid': UUID, 'state': state}))


if __name__ == '__main__':
    try: main()
    except Exception:
        print('{"ok":false,"error":"lab-power-rejected"}')
        raise SystemExit(78) from None
