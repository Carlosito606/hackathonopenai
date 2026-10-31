"""Operator tests use synthetic local processes; no Reactor or credential access."""
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from .reactor_window import child, utc


class OperatorWindowTest(unittest.TestCase):
    def test_reservation_requires_an_explicit_utc_timezone(self):
        self.assertEqual(utc('2026-10-31T06:00:00Z'), utc('2026-10-31T06:00:00+00:00'))
        for value in ['2026-10-31T06:00:00', '2026-10-31T06:00:00+01:00']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                utc(value)

    def test_failed_client_is_not_treated_as_an_answer(self):
        with self.assertRaisesRegex(RuntimeError, 'exit code 7'):
            child([sys.executable, '-c', 'raise SystemExit(7)'], {}, None, 5)

    def test_deadline_stops_descendants_as_well_as_the_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            marker, ready = root / 'orphan', root / 'ready'
            descendant = 'import time;from pathlib import Path;time.sleep(2);Path(' + repr(str(marker)) + ").write_text('unexpected')"
            parent = ('import subprocess,sys,time;from pathlib import Path;'
                      'subprocess.Popen([sys.executable,"-c",' + repr(descendant) + ']);'
                      'Path(' + repr(str(ready)) + ").write_text('started');time.sleep(30)")
            with self.assertRaises(TimeoutError):
                child([sys.executable, '-c', parent], {}, root, 1)
            self.assertTrue(ready.exists())
            time.sleep(1.3)
            self.assertFalse(marker.exists())


if __name__ == '__main__':
    unittest.main()
