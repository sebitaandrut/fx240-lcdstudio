# SPDX-License-Identifier: GPL-3.0-or-later
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from fx240.profiles import ProfileStore,validate_library,MAX_LIBRARY_BYTES
from fx240.scene import scene_json,default_scene


class ProfileTests(unittest.TestCase):
    def test_names_are_metadata_and_library_is_private(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'private/profiles.json';store=ProfileStore(path)
            identifier=store.save('../Example',scene_json(default_scene()))
            self.assertEqual(list(Path(folder).iterdir()),[path.parent])
            self.assertEqual(path.stat().st_mode & 0o777,0o600)
            loaded=ProfileStore(path)
            self.assertEqual(loaded.get(identifier)['name'],'../Example')
            self.assertEqual(loaded.profiles,store.profiles)
            before=path.read_bytes()
            for name in ('FOCUS','../example','', 'line\nbreak'):
                with self.assertRaises(ValueError):store.save(name,scene_json(default_scene()))
                self.assertEqual(path.read_bytes(),before)

    def test_count_and_schema_limits_preserve_previous_library(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'profiles.json';store=ProfileStore(path)
            for index in range(8):store.save('Example '+str(index),scene_json(default_scene()))
            before=path.read_bytes()
            with self.assertRaises(ValueError):store.save('Extra',scene_json(default_scene()))
            self.assertEqual(path.read_bytes(),before)
            with self.assertRaises(ValueError):validate_library({'version':True,'profiles':[]})
            bad=json.loads(before);bad['profiles'][0]['scene']='{"version":1,"layers":[{"id":"a","kind":"qml"}]}'
            with self.assertRaises(ValueError):validate_library(bad)

    def test_corrupt_oversized_and_linked_library_are_not_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'profiles.json'
            for payload in (b'broken',b'x'*(MAX_LIBRARY_BYTES+1)):
                path.write_bytes(payload);store=ProfileStore(path)
                self.assertTrue(store.error)
                with self.assertRaises(ValueError):store.save('Example',scene_json(default_scene()))
                self.assertEqual(path.read_bytes(),payload)
            path.unlink();target=Path(folder)/'target';target.write_bytes(b'personal')
            path.symlink_to(target);store=ProfileStore(path)
            self.assertTrue(store.error)
            with self.assertRaises(ValueError):store.save('Example',scene_json(default_scene()))
            self.assertEqual(target.read_bytes(),b'personal')

    def test_interrupted_save_preserves_file_and_memory(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'profiles.json';store=ProfileStore(path)
            identifier=store.save('Example',scene_json(default_scene()));before=path.read_bytes()
            with patch('fx240.profiles.os.replace',side_effect=OSError('synthetic failure')):
                with self.assertRaises(OSError):store.save('Renamed',scene_json(default_scene()),identifier)
            self.assertEqual(path.read_bytes(),before);self.assertEqual(store.get(identifier)['name'],'Example')
            self.assertEqual(list(Path(folder).iterdir()),[path])
            store.delete(identifier);self.assertEqual(ProfileStore(path).profiles,[])

    def test_library_metadata_validation_never_reads_assets(self):
        data={'version':1,'profiles':[{'id':'profile-1','name':'Example','scene':scene_json(default_scene())}]}
        with patch('fx240.localfiles.os.open') as opened:
            self.assertEqual(validate_library(data)['profiles'][0]['id'],'profile-1')
            opened.assert_not_called()

    def test_relative_xdg_does_not_put_private_files_in_working_tree(self):
        import os
        from fx240.preferences import Preferences
        with patch.dict(os.environ,{'XDG_CONFIG_HOME':'relative-config'}),patch('fx240.localfiles.Path.home',return_value=Path('/synthetic-user')):
            self.assertEqual(Preferences().path,Path('/synthetic-user/.config/fx240-linux/settings.json'))
            self.assertEqual(ProfileStore(memory=True).path,Path('/synthetic-user/.config/fx240-linux/profiles.json'))

    def test_default_destination_is_independent_of_profile_names(self):
        import os
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);config=root/'configuration'
            sentinel=root/'outside.json';sentinel.write_bytes(b'synthetic sentinel')
            with patch.dict(os.environ,{'XDG_CONFIG_HOME':str(config)}):
                store=ProfileStore()
                self.assertEqual(store.path,config/'fx240-linux/profiles.json')
                for name in ('../outside.json','/outside.json','nested/name'):
                    store.save(name,scene_json(default_scene()))
                self.assertEqual([item['name'] for item in ProfileStore().profiles],
                                 ['../outside.json','/outside.json','nested/name'])
            self.assertEqual(sentinel.read_bytes(),b'synthetic sentinel')
            self.assertEqual(set(path.relative_to(root) for path in root.rglob('*') if path.is_file()),
                             {Path('outside.json'),Path('configuration/fx240-linux/profiles.json')})
            self.assertEqual(store.path.stat().st_mode & 0o777,0o600)

    def test_hard_link_and_fifo_library_are_preserved(self):
        import os
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);path=root/'profiles.json';target=root/'sentinel'
            target.write_bytes(b'synthetic sentinel');os.link(target,path)
            store=ProfileStore(path)
            self.assertTrue(store.error)
            with self.assertRaises(ValueError):store.save('Example',scene_json(default_scene()))
            self.assertEqual(target.read_bytes(),b'synthetic sentinel')
            self.assertEqual(path.stat().st_ino,target.stat().st_ino)
            path.unlink();os.mkfifo(path)
            store=ProfileStore(path)
            self.assertTrue(store.error)
            with self.assertRaises(ValueError):store.save('Example',scene_json(default_scene()))
            import stat
            self.assertTrue(stat.S_ISFIFO(path.lstat().st_mode))
