import ast
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PO = ROOT / 'i18n' / 'ar_001.po'


class V698TranslationOccurrenceIntegrityTest(unittest.TestCase):
    def test_manifest_version_is_v698_or_newer(self):
        manifest = ast.literal_eval((ROOT / '__manifest__.py').read_text(encoding='utf-8'))
        self.assertGreaterEqual(tuple(map(int, manifest['version'].split('.'))), (18, 0, 6, 9, 8))

    def test_no_invalid_module_description_occurrence(self):
        text = PO.read_text(encoding='utf-8')
        offenders = [
            line for line in text.splitlines()
            if line.startswith('#: model:ir.module.module,description:')
        ]
        self.assertEqual(
            offenders,
            [],
            msg=f'Unsupported ir.module.module description occurrences: {offenders}',
        )

    def test_paid_pos_visit_entry_is_module_scoped_and_has_real_sources(self):
        text = PO.read_text(encoding='utf-8')
        blocks = [block for block in re.split(r'\n\s*\n', text) if 'msgid "Paid POS Visit"' in block]
        self.assertEqual(len(blocks), 1, msg='Paid POS Visit must have exactly one PO entry')
        block = blocks[0]
        self.assertIn('#. module: car_wash_dashboard', block)
        self.assertIn('msgstr "زيارة مدفوعة عبر نقطة البيع"', block)
        self.assertNotIn('#: model:ir.module.module,description:', block)
        py_source = (ROOT / 'models' / 'customer_intelligence.py').read_text(encoding='utf-8')
        js_source = (ROOT / 'static' / 'src' / 'js' / 'ui_translations.js').read_text(encoding='utf-8')
        self.assertIn("_('Paid POS Visit')", py_source)
        self.assertIn('_t("Paid POS Visit")', js_source)


if __name__ == '__main__':
    unittest.main()
