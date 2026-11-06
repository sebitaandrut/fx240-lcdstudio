# SPDX-License-Identifier: GPL-3.0-or-later
import os
from pathlib import Path
import tempfile
import unittest

from tools.wayland_trial_files import (
    new_run_directory, open_trial_file, private_run_directory, read_trial_file,
)


class WaylandTrialFilesTests(unittest.TestCase):
    def test_runs_have_separate_private_directories(self):
        with tempfile.TemporaryDirectory() as folder:
            parent = Path(folder) / 'results'
            first = new_run_directory(parent, False)
            second = new_run_directory(parent, False)
            self.assertNotEqual(first, second)
            self.assertEqual(first.parent, parent)
            self.assertTrue(first.name.startswith('baseline-'))
            self.assertEqual(private_run_directory(first).stat().st_mode & 0o777, 0o700)
            link = parent / 'linked-run'
            link.symlink_to(first, target_is_directory=True)
            with self.assertRaises(ValueError):
                private_run_directory(link)
            parent.chmod(0o777)
            with self.assertRaises(ValueError):
                new_run_directory(parent, True)

    def test_symlinks_and_existing_output_preserve_the_target(self):
        with tempfile.TemporaryDirectory() as folder:
            run = new_run_directory(folder, True)
            target = Path(folder) / 'synthetic-target'
            target.write_text('original')
            target.chmod(0o600)
            for name, mode in (('client-events.jsonl', 'a'), ('ready', 'x'), ('client.log', 'x'), ('result.json', 'x')):
                with self.subTest(name=name):
                    link = run / name
                    link.symlink_to(target)
                    with self.assertRaises(OSError), open_trial_file(link, mode):
                        self.fail('Linked output was opened')
                    with self.assertRaises(OSError):
                        read_trial_file(link, missing_ok=True)
                    self.assertEqual(target.read_text(), 'original')
            os.link(target, run / 'hard-linked-events')
            with self.assertRaises(ValueError), open_trial_file(run / 'hard-linked-events', 'a'):
                self.fail('Hard-linked output was opened')
            fifo = run / 'fifo'
            os.mkfifo(fifo, 0o600)
            with self.assertRaises(ValueError):
                read_trial_file(fifo)

    def test_regular_events_and_marker_keep_private_permissions(self):
        with tempfile.TemporaryDirectory() as folder:
            run = new_run_directory(folder, True)
            events = run / 'client-events.jsonl'
            for line in ('first\n', 'second\n'):
                with open_trial_file(events, 'a') as stream:
                    stream.write(line)
            self.assertEqual(read_trial_file(events), 'first\nsecond\n')
            self.assertEqual(events.stat().st_mode & 0o777, 0o600)
            marker = run / 'ready'
            self.assertEqual(read_trial_file(marker, missing_ok=True), '')
            with open_trial_file(marker, 'x') as stream:
                stream.write('ready')
            with self.assertRaises(FileExistsError), open_trial_file(marker, 'x'):
                self.fail('Existing marker was opened for replacement')
            self.assertEqual(read_trial_file(marker), 'ready')
