# SPDX-License-Identifier: GPL-3.0-or-later
"""Keep source-controlled UI labels and fixed application errors translatable."""
import ast
from pathlib import Path
import re
import unittest
from fx240.i18n import SPANISH,translate,runtime_text

ROOT=Path(__file__).resolve().parents[1]/'src/fx240'
STRING=r'"(?:[^"\\]|\\.)*"|\x27(?:[^\x27\\]|\\.)*\x27'


class TranslationCoverageTests(unittest.TestCase):
    def test_qml_labels_choices_and_tooltips_have_spanish_entries(self):
        messages=set()
        for path in (ROOT/'qml').glob('*.qml'):
            text=path.read_text()
            for pattern in (r'\btr\(([^()\n]*)\)',r'\bhelp\s*:\s*("(?:[^"\\]|\\.)*")',r'\bmodel\s*:\s*\[([^\]\n]*)\]'):
                for match in re.finditer(pattern,text):
                    for value in re.finditer(STRING,match[1]):
                        # Comparisons inside translated ternaries use canonical
                        # enum values; only the selected labels are UI text.
                        if match[1][:value.start()].rstrip().endswith(('===','!==','==','!=')):continue
                        messages.add(ast.literal_eval(value[0]))
        # Unit symbols and color values are data, not language-specific labels.
        missing=sorted(value for value in messages if value and value not in SPANISH and value not in ('°C','°F') and not re.fullmatch(r'#[0-9a-fA-F]{6}',value))
        self.assertEqual(missing,[])

    def test_fixed_application_errors_have_spanish_entries(self):
        messages=set()
        for path in ROOT.glob('*.py'):
            if path.name=='i18n.py':continue
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node,ast.Raise) and isinstance(node.exc,ast.Call) and node.exc.args:
                    value=node.exc.args[0]
                    if isinstance(value,ast.Constant) and isinstance(value.value,str):messages.add(value.value)
        self.assertEqual(sorted(messages-set(SPANISH)),[])

    def test_media_action_and_runtime_messages_translate_without_translating_user_data(self):
        self.assertEqual(translate('Replace image / GIF…','es'),'Reemplazar imagen / GIF…')
        self.assertEqual(translate('Replace image / GIF…','en'),'Replace image / GIF…')
        self.assertEqual(runtime_text('GIF decoder failed','es'),'Falló la decodificación del GIF')
        self.assertEqual(translate('CPU synthetic Tctl','es'),'CPU synthetic Tctl')
        self.assertEqual(translate('/synthetic/example.gif','es'),'/synthetic/example.gif')
