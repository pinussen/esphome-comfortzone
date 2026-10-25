#!/usr/bin/env python3
"""Import a committed library snapshot, or check the vendored source hashes.

python3 scripts/sync_library.py --import-from ../comfortzone_heatpump
python3 scripts/sync_library.py --check [--source ../comfortzone_heatpump]
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / 'components/comfortzone/third_party/comfortzone_heatpump'
LOCK = VENDOR.parent / 'comfortzone_heatpump.lock.json'

def git(source, *args):
    return subprocess.check_output(['git', '-C', str(source), *args])

def digest(data):
    return hashlib.sha256(data).hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--import-from', type=Path)
    group.add_argument('--check', action='store_true')
    parser.add_argument('--source', type=Path)
    args = parser.parse_args()
    if args.import_from:
        source = args.import_from.resolve()
        commit = git(source, 'rev-parse', 'HEAD').decode().strip()
        files = [f for f in git(source, 'ls-tree', '-r', '--name-only', commit).decode().splitlines()
                 if ('/' not in f and f.endswith(('.cpp', '.h')))
                 or f in ('library.json','library.properties','LICENSE','README.txt',
                          'registers_v170.json','REGISTERS-170.md','tools/generate_registers.py')]
        if not files or 'comfortzone_heatpump.cpp' not in files:
            raise SystemExit('Not a comfortzone_heatpump source checkout')
        hashes = {}
        for name in sorted(files):
            data = git(source, 'show', f'{commit}:{name}')
            (VENDOR / name).parent.mkdir(parents=True, exist_ok=True)
            (VENDOR / name).write_bytes(data)
            hashes[name] = digest(data)
        LOCK.write_text(json.dumps({'repository': 'https://github.com/pinussen/comfortzone_heatpump',
                                    'commit': commit, 'sha256': hashes}, indent=2)+'\n')
        print(f'Imported {len(files)} committed library files from {commit}')
    lock = json.loads(LOCK.read_text())
    for name, expected in lock['sha256'].items():
        actual = digest((VENDOR / name).read_bytes())
        if actual != expected:
            raise SystemExit(f'Vendor differs from locked snapshot: {name}')
        if args.source and digest(git(args.source, 'show', f"{lock['commit']}:{name}")) != expected:
            raise SystemExit(f'Source commit differs: {name}')
    for source in [*VENDOR.glob('*.cpp'), *VENDOR.glob('*.h')]:
        if source.name not in lock['sha256']:
            raise SystemExit(f'Unrecorded library source: {source.name}')
    print(f"Library snapshot verified: {lock['commit']}")

if __name__ == '__main__':
    main()
