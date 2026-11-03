# SPDX-License-Identifier: GPL-3.0-or-later
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock,patch
from fx240.typography import capabilities,_capabilities,font,resolve_font


class TypographyTests(unittest.TestCase):
    def test_bundled_variable_weight_changes_real_glyphs(self):
        path=resolve_font();info=capabilities(path)
        self.assertTrue(info['variable'])
        self.assertNotEqual(bytes(font(path,32,300).getmask('45.2')),bytes(font(path,32,700).getmask('45.2')))

    def test_static_font_reports_style_without_fake_weight_axis(self):
        face=Mock();face.getname.return_value=('Synthetic Family','Regular')
        face.get_variation_axes.side_effect=OSError('not variable')
        _capabilities.cache_clear()
        with patch('fx240.typography.load_font',return_value=face):
            info=_capabilities('/synthetic/regular.ttf',0,1)
        self.assertFalse(info['variable']);self.assertEqual(info['style'],'Regular')
        _capabilities.cache_clear()

    @unittest.skipUnless(importlib.util.find_spec('PySide6'),'Optional Qt dependency missing')
    def test_static_style_selection_uses_another_real_font_path(self):
        from PySide6.QtCore import QCoreApplication
        from fx240.workspace import EditorWorkspace
        from fx240.profiles import ProfileStore
        from fx240.session import Settings
        app=QCoreApplication.instance() or QCoreApplication([])
        workspace=EditorWorkspace(Settings(),ProfileStore(memory=True),lambda:Settings(),lambda:[],
                    lambda:[('Synthetic Family · Regular','/synthetic/regular.ttf'),('Synthetic Family · Bold','/synthetic/bold.ttf')],lambda:'en')
        workspace.model.updateSelected({'font_path':'/synthetic/regular.ttf'})
        with patch('fx240.workspace.capabilities',return_value={'variable':False,'family':'Synthetic Family','style':'Regular','minimum':100,'maximum':900}):
            self.assertFalse(workspace.fontInfo['variable'])
            self.assertEqual(workspace.fontStyles,['Regular','Bold'])
            workspace.selectFontStyle(1)
        self.assertEqual(workspace.model.selected['font_path'],'/synthetic/bold.ttf')
        workspace.close()
