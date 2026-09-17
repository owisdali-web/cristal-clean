import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class V672FrontendTranslationBundleTest(unittest.TestCase):
    def test_manifest_version_is_v672(self):
        manifest = ast.literal_eval((ROOT / '__manifest__.py').read_text(encoding='utf-8'))
        self.assertEqual(manifest['version'], '18.0.6.9')

    def test_ir_http_model_is_imported(self):
        models_init = (ROOT / 'models' / '__init__.py').read_text(encoding='utf-8')
        self.assertIn('from . import ir_http', models_init)

    def test_ir_http_registers_module_in_frontend_translation_bundle(self):
        path = ROOT / 'models' / 'ir_http.py'
        self.assertTrue(path.exists(), 'models/ir_http.py must exist')
        source = path.read_text(encoding='utf-8')
        self.assertIn("_inherit = 'ir.http'", source)
        self.assertIn('@classmethod', source)
        self.assertIn('def _get_translation_frontend_modules_name', source)
        self.assertIn('super()._get_translation_frontend_modules_name()', source)
        self.assertIn("'car_wash_dashboard'", source)

    def test_station_details_has_arabic_translation(self):
        po = (ROOT / 'i18n' / 'ar_001.po').read_text(encoding='utf-8')
        self.assertIn('msgid "Station details"', po)
        self.assertIn('msgstr "تفاصيل المحطة"', po)

    def test_vendor_chart_library_is_not_part_of_translation_contract(self):
        # The bundled Chart.js file may contain identifiers like `_t(` internally;
        # it is third-party minified source and must not be treated as Odoo translation code.
        dashboard_sources = [
            ROOT / 'static/src/js/dashboard.js',
            ROOT / 'static/src/js/components/kpi_card.js',
            ROOT / 'static/src/js/components/queue_panel.js',
            ROOT / 'static/src/js/components/station_card.js',
            ROOT / 'static/src/js/components/station_detail.js',
        ]
        for path in dashboard_sources:
            self.assertTrue(path.exists(), path)
            self.assertNotIn('static/src/js/libs/chart.umd.min.js', str(path))

    def test_no_dynamic_odoo_translation_calls_in_dashboard_sources(self):
        import re
        sources = [
            ROOT / 'static/src/js/dashboard.js',
            ROOT / 'static/src/js/components/queue_panel.js',
            ROOT / 'static/src/js/components/station_card.js',
            ROOT / 'static/src/js/components/station_detail.js',
        ]
        offenders = []
        pattern = re.compile(r'_t\(\s*([A-Za-z_$][\w$\.]*)\s*\)')
        for path in sources:
            for match in pattern.finditer(path.read_text(encoding='utf-8')):
                offenders.append((path.relative_to(ROOT).as_posix(), match.group(1)))
        self.assertEqual(offenders, [], msg=f'Dynamic _t calls: {offenders}')

    def test_ui_translation_catalog_is_loaded_before_dashboard_components(self):
        manifest = ast.literal_eval((ROOT / '__manifest__.py').read_text(encoding='utf-8'))
        assets = manifest['assets']['web.assets_backend']
        catalog = 'car_wash_dashboard/static/src/js/ui_translations.js'
        self.assertIn(catalog, assets)
        dashboard = 'car_wash_dashboard/static/src/js/dashboard.js'
        self.assertLess(assets.index(catalog), assets.index(dashboard))


if __name__ == '__main__':
    unittest.main()
