import ast
import html
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def po_entries():
    text = (ROOT / 'i18n' / 'ar_001.po').read_text(encoding='utf-8')
    entries = {}
    blocks = re.split(r'\n\s*\n', text)
    for block in blocks:
        mid = re.search(r'^msgid\s+"(.*)"$', block, re.M)
        mst = re.search(r'^msgstr\s+"(.*)"$', block, re.M)
        if mid and mst and mid.group(1):
            entries[mid.group(1)] = mst.group(1)
    return entries


class V696ArabicRuntimeHardeningTest(unittest.TestCase):
    def test_translation_helper_is_an_executable_odoo_module_not_a_commented_stub(self):
        source = (ROOT / 'static/src/js/ui_translations.js').read_text(encoding='utf-8')
        stripped = source.lstrip()
        self.assertTrue(stripped.startswith('/** @odoo-module **/'))
        marker_pos = source.find('/** @odoo-module **/')
        ar_pos = source.find('const AR_UI_TRANSLATIONS')
        import_pos = source.find('import { _t } from "@web/core/l10n/translation";')
        self.assertGreaterEqual(marker_pos, 0)
        self.assertGreater(import_pos, marker_pos)
        self.assertGreater(ar_pos, import_pos)
        self.assertNotIn('});* @odoo-module **/', source)

    def test_runtime_helper_has_explicit_arabic_fallback_and_language_detection(self):
        source = (ROOT / 'static/src/js/ui_translations.js').read_text(encoding='utf-8')
        self.assertIn('const AR_UI_TRANSLATIONS', source)
        self.assertIn('function isArabicUi()', source)
        self.assertIn('document.documentElement', source)
        self.assertIn('startsWith("ar")', source)
        self.assertIn('AR_UI_TRANSLATIONS[text]', source)

    def test_arabic_fallback_covers_every_ui_translation_key_except_brand(self):
        source = (ROOT / 'static/src/js/ui_translations.js').read_text(encoding='utf-8')
        ui_block = re.search(
            r'const UI_TRANSLATIONS = Object\.freeze\(\{(.*?)\}\);',
            source,
            re.S,
        )
        ar_block = re.search(
            r'const AR_UI_TRANSLATIONS = Object\.freeze\(\{(.*?)\}\);',
            source,
            re.S,
        )
        self.assertIsNotNone(ui_block)
        self.assertIsNotNone(ar_block)
        ui_keys = set(re.findall(r'^\s*"([^"]+)"\s*:', ui_block.group(1), re.M))
        ar_pairs = dict(re.findall(r'^\s*"([^"]+)"\s*:\s*"([^"]*)"\s*,?$', ar_block.group(1), re.M))
        expected = {key for key in ui_keys if key != 'Crystal Clean'}
        missing = sorted(key for key in expected if not ar_pairs.get(key, '').strip())
        self.assertEqual(missing, [], msg=f'Missing Arabic runtime fallbacks: {missing}')
        self.assertNotIn('Crystal Clean', ar_pairs)

    def test_every_literal_tr_call_has_runtime_arabic_fallback_and_po_entry(self):
        ui_source = (ROOT / 'static/src/js/ui_translations.js').read_text(encoding='utf-8')
        ar_block = re.search(r'const AR_UI_TRANSLATIONS = Object\.freeze\(\{(.*?)\}\);', ui_source, re.S)
        ui_block = re.search(r'const UI_TRANSLATIONS = Object\.freeze\(\{(.*?)\}\);', ui_source, re.S)
        self.assertIsNotNone(ar_block)
        self.assertIsNotNone(ui_block)
        ar_keys = set(re.findall(r'^\s*"([^"]+)"\s*:', ar_block.group(1), re.M))
        ui_keys = set(re.findall(r'^\s*"([^"]+)"\s*:', ui_block.group(1), re.M))
        entries = po_entries()
        tr_terms = set()
        for path in [ROOT / 'static/src/js/dashboard.js', ROOT / 'static/src/xml/dashboard.xml']:
            source = path.read_text(encoding='utf-8')
            for match in re.finditer(r"\btr\(\s*(['\"])(.*?)\1\s*\)", source, re.S):
                label = html.unescape(match.group(2)).replace("\\'", "'").replace("\\\"", "\"")
                if '\n' not in label and label != 'Crystal Clean':
                    tr_terms.add(label)
        missing_ui = sorted(term for term in tr_terms if term not in ui_keys)
        missing_ar = sorted(term for term in tr_terms if term not in ar_keys)
        missing_po = sorted(term for term in tr_terms if not entries.get(term, '').strip())
        self.assertEqual(missing_ui, [], msg=f'tr() labels missing UI_TRANSLATIONS: {missing_ui}')
        self.assertEqual(missing_ar, [], msg=f'tr() labels missing Arabic fallback: {missing_ar}')
        self.assertEqual(missing_po, [], msg=f'tr() labels missing Arabic PO: {missing_po}')

    def test_po_has_nonempty_translation_for_every_frontend_literal(self):
        entries = po_entries()
        missing = []
        for path in (ROOT / 'static').rglob('*.js'):
            source = path.read_text(encoding='utf-8')
            for match in re.finditer(r'_t\(\s*(["\'])(.*?)\1\s*(?:,|\))', source, re.S):
                label = match.group(2)
                if '\n' not in label and label != 'Crystal Clean' and not entries.get(label, '').strip():
                    missing.append(label)
        self.assertEqual(sorted(set(missing)), [], msg=f'Missing frontend PO translations: {sorted(set(missing))}')

    def test_real_python_translation_literals_have_nonempty_po_entries(self):
        entries = po_entries()
        missing = []
        for path in [ROOT / 'models', ROOT / 'controllers']:
            for pyfile in path.rglob('*.py'):
                tree = ast.parse(pyfile.read_text(encoding='utf-8'))
                for node in ast.walk(tree):
                    if not isinstance(node, ast.Call) or not node.args:
                        continue
                    if not isinstance(node.func, ast.Name) or node.func.id != '_':
                        continue
                    first = node.args[0]
                    if isinstance(first, ast.Constant) and isinstance(first.value, str):
                        if first.value != 'Crystal Clean' and not entries.get(first.value, '').strip():
                            missing.append(first.value)
        self.assertEqual(sorted(set(missing)), [], msg=f'Missing backend PO translations: {sorted(set(missing))}')

    def test_dynamic_report_status_and_exception_copy_is_translated_in_template(self):
        xml = (ROOT / 'static/src/xml/dashboard.xml').read_text(encoding='utf-8')
        self.assertNotIn('t-esc="row.status_label"', xml)
        self.assertIn('t-esc="tr(row.status_label)"', xml)
        self.assertNotIn('t-esc="row.type"', xml)
        self.assertIn('t-esc="tr(row.type)"', xml)
        self.assertNotIn('t-esc="row.message"', xml)
        self.assertIn('t-esc="tr(row.message)"', xml)

    def test_manifest_version_is_valid_next_patch(self):
        manifest = ast.literal_eval((ROOT / '__manifest__.py').read_text(encoding='utf-8'))
        parts = manifest['version'].split('.')
        self.assertLessEqual(len(parts), 5)
        self.assertEqual(parts[:2], ['18', '0'])


if __name__ == '__main__':
    unittest.main()
