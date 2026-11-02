# SPDX-License-Identifier: GPL-3.0-or-later
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('fx240_capture_example', Path(__file__).resolve().parents[1]/'examples/compare_usb_capture.py')
capture_example = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capture_example)


class CaptureCommandTests(unittest.TestCase):
    def test_option_like_filename_is_a_single_absolute_argument(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'-X lua_script=synthetic'; path.write_bytes(b'capture')
            with patch.object(capture_example.shutil, 'which', return_value='/usr/bin/tshark'):
                command = capture_example.tshark_command(path, 12)
                self.assertEqual(command[:3], ['/usr/bin/tshark', '-r', str(path.resolve())])
                self.assertEqual(command.count('-r'), 1)
                with self.assertRaises(ValueError):
                    capture_example.tshark_command(path, '12 -X payload')
                with self.assertRaises(ValueError):
                    capture_example.tshark_command(Path(folder), 12)
