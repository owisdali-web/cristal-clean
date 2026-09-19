import ast
import html
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
XML = ROOT / 'static/src/xml/dashboard.xml'
UI = ROOT / 'static/src/js/ui_translations.js'
PO = ROOT / 'i18n/ar_001.po'


def _object_keys(source, name):
    match = re.search(rf'const {name} = Object\.freeze\(\{{(.*?)\}}\);', source, re.S)
    if not match:
        return set()
    return set(re.findall(r'^\s*"((?:\\.|[^"])*)"\s*:', match.group(1), re.M))


def _po_blocks():
    text = PO.read_text(encoding='utf-8')
    result = {}
    for block in re.split(r'\n\s*\n', text):
        mid = re.search(r'^msgid\s+"(.*)"$', block, re.M)
        if mid and mid.group(1):
            result[mid.group(1)] = block
    return result


class V699ArabicOwlRuntimeTest(unittest.TestCase):
    def test_manifest_version_is_v699_or_newer(self):
        manifest = ast.literal_eval((ROOT / '__manifest__.py').read_text(encoding='utf-8'))
        self.assertGreaterEqual(tuple(map(int, manifest['version'].split('.'))), (18, 0, 6, 9, 9))

    def test_owl_template_does_not_call_js_global_constructors(self):
        source = XML.read_text(encoding='utf-8')
        forbidden = ['Number', 'String', 'Boolean', 'Object', 'Array', 'Date', 'JSON', 'parseInt', 'parseFloat']
        offenders = []
        for name in forbidden:
            for match in re.finditer(rf'\b{name}\s*\(', source):
                offenders.append((name, source[:match.start()].count('\n') + 1))
        self.assertEqual(offenders, [], msg=f'Global JS calls inside OWL template: {offenders}')

    def test_frontend_visible_copy_uses_single_translation_gateway(self):
        offenders = []
        for path in (ROOT / 'static/src/js').rglob('*.js'):
            if path.name == 'ui_translations.js':
                continue
            source = path.read_text(encoding='utf-8')
            for match in re.finditer(r'\b_t\s*\(', source):
                offenders.append((str(path.relative_to(ROOT)), source[:match.start()].count('\n') + 1))
        self.assertEqual(offenders, [], msg=f'Direct _t() calls bypass translateUi(): {offenders}')

    def test_arabic_runtime_detection_understands_odoo_rtl_state(self):
        source = UI.read_text(encoding='utf-8')
        self.assertIn('classList?.contains("o_rtl")', source)
        self.assertIn('getComputedStyle', source)
        self.assertIn('direction', source)

    def test_translation_gateway_covers_every_frontend_literal(self):
        ui_source = UI.read_text(encoding='utf-8')
        ui_keys = _object_keys(ui_source, 'UI_TRANSLATIONS')
        ar_keys = _object_keys(ui_source, 'AR_UI_TRANSLATIONS')
        self.assertEqual(ui_keys, ar_keys, msg=f'UI/Arabic gateway key mismatch: UI-only={sorted(ui_keys-ar_keys)}, AR-only={sorted(ar_keys-ui_keys)}')

        required = set()
        # XML custom tr() calls.
        xml = XML.read_text(encoding='utf-8')
        for match in re.finditer(r"\btr\(\s*(['\"])(.*?)\1\s*\)", xml, re.S):
            label = html.unescape(match.group(2)).replace("\\'", "'").replace('\\"', '"')
            if '\n' not in label and label != 'Crystal Clean':
                required.add(label)
        # JS this.tr()/translateUi() literal calls outside the gateway.
        for path in (ROOT / 'static/src/js').rglob('*.js'):
            if path.name == 'ui_translations.js':
                continue
            source = path.read_text(encoding='utf-8')
            for match in re.finditer(r"(?:this\.tr|translateUi)\(\s*(['\"])(.*?)\1", source, re.S):
                label = match.group(2).replace("\\'", "'").replace('\\"', '"')
                if '\n' not in label and label != 'Crystal Clean':
                    required.add(label)
        missing = sorted(required - ui_keys)
        self.assertEqual(missing, [], msg=f'Frontend literals missing from translation gateway: {missing}')

    def test_every_translation_gateway_term_is_javascript_scoped_in_po(self):
        source = UI.read_text(encoding='utf-8')
        keys = _object_keys(source, 'UI_TRANSLATIONS')
        blocks = _po_blocks()
        missing = []
        not_js = []
        for key in sorted(keys):
            if key == 'Crystal Clean':
                continue
            block = blocks.get(key)
            if not block:
                missing.append(key)
            elif '#. odoo-javascript' not in block:
                not_js.append(key)
        self.assertEqual(missing, [], msg=f'Gateway terms missing PO entry: {missing}')
        self.assertEqual(not_js, [], msg=f'Gateway PO terms not marked odoo-javascript: {not_js}')


if __name__ == '__main__':
    unittest.main()
