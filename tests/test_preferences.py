# SPDX-License-Identifier: GPL-3.0-or-later
from dataclasses import replace
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from fx240.preferences import Preferences
from fx240.session import Settings
from fx240.i18n import translate


class PreferenceTests(unittest.TestCase):
    def test_roundtrip_all_settings_without_device_or_output_state(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'private/settings.json'
            store=Preferences(path)
            config=replace(Settings(),font_weight=500,comet_speed=2,accent='#ac8aff',
                           comet_style='rainbow',temperature_unit='F',device='/dev/transient')
            store.save(config,'es','light')
            restored,ui=Preferences(path).load()
            self.assertEqual(restored,replace(config,device=None))
            self.assertEqual(ui,{'language':'es','theme':'light'})
            self.assertEqual(path.stat().st_mode & 0o777,0o600)
            data=json.loads(path.read_text())
            self.assertNotIn('device',data['display'])
            self.assertNotIn('send',data['display'])
            self.assertNotIn('output_requested',data['display'])

    def test_decimal_timing_values_are_restored_without_spurious_reset(self):
        with tempfile.TemporaryDirectory() as temp:
            store=Preferences(Path(temp)/'settings.json')
            for fps,delay in ((24.0,2.0),(17.5,2.5)):
                config=replace(Settings(),fps=fps,delay_ms=delay)
                store.save(config,'en','dark')
                loaded,ui=store.load()
                self.assertEqual(loaded,config)
                self.assertEqual(store.warning,'')
                self.assertEqual(store.issues,[])

    def test_corruption_and_invalid_fields_have_safe_fallbacks(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'settings.json'
            path.write_text('broken json')
            store=Preferences(path)
            self.assertEqual(store.load()[0],Settings())
            self.assertTrue(store.warning)
            path.write_text(json.dumps({'version':1,'display':{'quality':65.5,'font_path':'/missing/font.ttf',
                'temperature_unit':'Kelvin','accent':'#68b5ff','comet_speed':2,'device':'/dev/not-saved'},
                'application':{'language':'invalid','theme':'light'}}))
            recovered=Preferences(path)
            restored,ui=recovered.load()
            fields={issue['field'] for issue in recovered.issues}
            self.assertEqual(fields,{'quality','font_path','temperature_unit','language'})
            self.assertEqual(restored.quality,65)
            self.assertIsNone(restored.font_path)
            self.assertIsNone(restored.device)
            self.assertEqual(restored.temperature_unit,'C')
            self.assertEqual(restored.accent,'#68b5ff')
            self.assertEqual(restored.comet_speed,2)
            self.assertEqual(ui['theme'],'light')

    def test_interrupted_replace_preserves_previous_file(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'settings.json'
            store=Preferences(path)
            store.save(Settings(),'en','dark')
            original=path.read_bytes()
            with patch('fx240.preferences.os.replace',side_effect=OSError('simulated disk error')):
                with self.assertRaises(OSError):store.save(replace(Settings(),comet_speed=2),'es','light')
            self.assertEqual(path.read_bytes(),original)
            self.assertEqual(list(Path(temp).iterdir()),[path])

    def test_xdg_location_and_translations_preserve_unknown_sensor_identity(self):
        with tempfile.TemporaryDirectory() as temp,patch.dict(os.environ,{'XDG_CONFIG_HOME':temp}):
            self.assertEqual(Preferences().path,Path(temp)/'fx240-linux/settings.json')
        self.assertEqual(translate('Settings','es'),'Ajustes')
        self.assertEqual(translate('CPU k10temp Tctl','es'),'CPU k10temp Tctl')
        self.assertEqual(translate('Settings','en'),'Settings')
