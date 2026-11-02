# SPDX-License-Identifier: GPL-3.0-or-later
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from fx240.localfiles import read_regular
from fx240.autostart import Autostart
from fx240.preferences import Preferences
from fx240.lifecycle import LifecycleTrace
from fx240.session import Settings
from fx240.focus import resolve_font
import json


class LocalFileTests(unittest.TestCase):
    def test_private_read_rejects_links_without_touching_target(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'target';target.write_bytes(b'personal')
            for kind in ('symlink','hardlink'):
                link=Path(folder)/kind
                if kind=='symlink':link.symlink_to(target)
                else:os.link(target,link)
                with self.assertRaises(ValueError):read_regular(link,100,private=True)
                store=Preferences(link)
                self.assertEqual(store.load()[0],Settings())
                self.assertTrue(store.load_error)
                self.assertEqual(target.read_bytes(),b'personal')

    def test_fifo_preferences_and_startup_fail_before_open(self):
        with tempfile.TemporaryDirectory() as folder:
            startup=Autostart(folder)
            startup.path.parent.mkdir()
            os.mkfifo(startup.path)
            with patch('fx240.localfiles.os.open') as opened:
                self.assertTrue(Preferences(startup.path).load()[0]==Settings())
                for enabled in (True,False):
                    with self.assertRaises(OSError):startup.set_enabled(enabled)
                opened.assert_not_called()

    def test_descriptor_rechecked_if_file_replaced_by_fifo(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'input';path.write_bytes(b'valid')
            original=os.open
            def replace_then_open(name,flags):
                path.unlink();os.mkfifo(path)
                self.assertTrue(flags & os.O_NONBLOCK)
                return original(name,flags)
            with patch('fx240.localfiles.os.open',side_effect=replace_then_open):
                with self.assertRaisesRegex(ValueError,'regular file'):read_regular(path,100)

    def test_growing_file_still_has_a_byte_limit(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'input';path.write_bytes(b'a')
            original=os.fdopen
            def grow_then_read(fd,*args,**kwargs):
                with path.open('ab') as stream:stream.write(b'b'*20)
                return original(fd,*args,**kwargs)
            with patch('fx240.localfiles.os.fdopen',side_effect=grow_then_read):
                with self.assertRaisesRegex(ValueError,'byte limit'):read_regular(path,10)

    def test_trace_hardlink_preserves_target_contents_and_permissions(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'target';target.write_bytes(b'personal');target.chmod(0o644)
            link=Path(folder)/'trace';os.link(target,link)
            LifecycleTrace(link).emit('gui-start')
            self.assertEqual(target.read_bytes(),b'personal')
            self.assertEqual(target.stat().st_mode & 0o777,0o644)

    def test_large_startup_entry_is_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            startup=Autostart(folder);startup.path.parent.mkdir()
            startup.path.write_bytes(b'x'*65537)
            with self.assertRaises(OSError):startup.set_enabled(True)
            self.assertEqual(startup.path.stat().st_size,65537)

    def test_saved_fifo_font_is_rejected_without_decoder_or_open(self):
        with tempfile.TemporaryDirectory() as folder:
            font=Path(folder)/'font.ttf';os.mkfifo(font)
            path=Path(folder)/'settings.json'
            path.write_text(json.dumps({'version':1,'display':{'font_path':str(font)}}))
            with patch('fx240.focus.ImageFont.truetype') as decoder:
                with self.assertRaises(ValueError):resolve_font(font)
                store=Preferences(path);settings,_=store.load()
                self.assertIsNone(settings.font_path)
                self.assertEqual(store.issues[0]['field'],'font_path')
                decoder.assert_not_called()
