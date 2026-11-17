"""Run the existing regression suite once, without network or child processes.

This is test infrastructure; application modules, tests and fixtures are unchanged.
Run from the publication-candidate root. Temporary data stays inside this directory.
"""
from pathlib import Path
import json
import os
import sqlite3
import sys
import tempfile
import unittest


def main():
    root = Path(__file__).resolve().parents[1]
    if Path.cwd().resolve() != root:
        raise SystemExit('Run this command from the publication-candidate root.')
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(root))
    sandbox_parent = root / '.test-tmp'
    if sandbox_parent.is_symlink():
        raise SystemExit('Refusing a symlinked test temporary directory.')
    sandbox_created = not sandbox_parent.exists()
    sandbox_parent.mkdir(mode=0o700, exist_ok=True)
    blocked = []

    def no_live_io(event, args):
        if event in {'socket.connect', 'socket.getaddrinfo', 'socket.sendto',
                     'socket.bind', 'subprocess.Popen', 'os.system', 'os.exec'}:
            blocked.append(event)
            raise RuntimeError('Live network/process operations are disabled in regression tests.')

    sys.addaudithook(no_live_io)
    print('Python:', '.'.join(map(str, sys.version_info[:3])), flush=True)
    print('SQLite:', sqlite3.sqlite_version, flush=True)
    print('Scope: existing root tests only; live network and child processes blocked.', flush=True)
    previous_tempdir = tempfile.tempdir
    try:
        with tempfile.TemporaryDirectory(prefix='regression-', dir=sandbox_parent) as sandbox:
            tempfile.tempdir = sandbox
            suite = unittest.defaultTestLoader.discover('tests', pattern='test*.py')
            result = unittest.TextTestRunner(verbosity=2).run(suite)
    finally:
        tempfile.tempdir = previous_tempdir
        if sandbox_created:
            try:
                sandbox_parent.rmdir()
            except OSError:
                pass  # Preserve unexpected scratch contents rather than deleting them.
    summary = {'tests_run': result.testsRun, 'failures': len(result.failures),
               'errors': len(result.errors), 'skipped': len(result.skipped),
               'blocked_live_io_events': blocked,
               'successful': result.wasSuccessful() and not blocked}
    print('TEST_RUN_SUMMARY=' + json.dumps(summary, sort_keys=True), flush=True)
    return 0 if summary['successful'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
