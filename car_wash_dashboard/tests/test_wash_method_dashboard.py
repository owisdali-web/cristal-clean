from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]


class WashMethodDashboardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sale_model = (ROOT / 'models/sale_order_extend.py').read_text(encoding='utf-8')
        cls.mrp_model = (ROOT / 'models/mrp_production_extend.py').read_text(encoding='utf-8')
        cls.menu_xml = (ROOT / 'views/menu_views.xml').read_text(encoding='utf-8')
        cls.sale_view = (ROOT / 'views/sale_order_views.xml').read_text(encoding='utf-8')
        cls.js = (ROOT / 'static/src/js/dashboard.js').read_text(encoding='utf-8')
        cls.qweb = (ROOT / 'static/src/xml/dashboard.xml').read_text(encoding='utf-8')
        cls.css = (ROOT / 'static/src/css/dashboard_concept_replica.css').read_text(encoding='utf-8')

    def test_operational_wash_method_field_exists_without_replacing_legacy_wash_type(self):
        self.assertIn('wash_method = fields.Selection', self.sale_model)
        self.assertIn('wash_method = fields.Selection', self.mrp_model)
        self.assertIn("('automatic', 'غسيل آلي')", self.mrp_model)
        self.assertIn("('manual', 'غسيل يدوي')", self.mrp_model)
        self.assertIn("wash_type = fields.Selection(WASH_TYPES", self.mrp_model)

    def test_dashboard_rpc_accepts_optional_wash_method_filter(self):
        self.assertRegex(self.mrp_model, r'def _cw_wash_domain\(self, wash_method=False\)')
        self.assertRegex(self.mrp_model, r'def get_dashboard_data\(self, wash_method=False\)')
        self.assertIn("domain.append(('wash_method', '=', wash_method))", self.mrp_model)
        self.assertIn("'wash_method':", self.mrp_model)

    def test_sale_order_form_exposes_wash_method(self):
        self.assertIn('name="wash_method"', self.sale_view)

    def test_sale_and_production_keep_wash_method_in_sync_without_recursion(self):
        self.assertIn('cw_sync_wash_method', self.sale_model)
        self.assertIn('cw_sync_wash_method', self.mrp_model)
        self.assertIn('def write(self, vals):', self.mrp_model)

    def test_mrp_form_view_exposes_wash_method(self):
        path = ROOT / 'views/mrp_production_views.xml'
        self.assertTrue(path.exists())
        text = path.read_text(encoding='utf-8')
        self.assertIn('name="wash_method"', text)
        self.assertIn('name="bom_div"', text)
        ET.fromstring(text)

    def test_four_menu_actions_exist(self):
        for label in ('لوحة التحكم العامة', 'الغسيل الآلي', 'الغسيل اليدوي', 'التقارير'):
            self.assertIn(label, self.menu_xml)
        for tag in (
            'car_wash_dashboard.overview_action',
            'car_wash_dashboard.automatic_action',
            'car_wash_dashboard.manual_action',
            'car_wash_dashboard.reports_action',
        ):
            self.assertIn(tag, self.menu_xml)
            self.assertIn(tag, self.js)

    def test_js_routes_sections_and_calls_filtered_rpc(self):
        for section in ('overview', 'automatic', 'manual', 'reports'):
            self.assertIn(f'"{section}"', self.js)
        self.assertIn('get_dashboard_data', self.js)
        self.assertRegex(self.js, re.compile(r'\[washMethod\]', re.S))
        self.assertIn('reportData', self.js)

    def test_mode_specific_scenes_and_reports_are_in_qweb(self):
        for token in ('cc-auto-tunnel', 'cc-manual-bay', 'cc-report-comparison'):
            self.assertIn(token, self.qweb)
        self.assertIn('الغسيل الآلي', self.qweb)
        self.assertIn('الغسيل اليدوي', self.qweb)
        self.assertIn('التجفيف', self.qweb)
        self.assertNotIn('الفحص قيد التنفيذ', self.qweb)

    def test_mode_scene_css_and_modern_car_assets_exist(self):
        self.assertIn('.cc-auto-tunnel', self.css)
        self.assertIn('.cc-manual-bay', self.css)
        self.assertIn('@keyframes cc-auto-brush-spin', self.css)
        self.assertIn('@keyframes cc-manual-foam-float', self.css)
        self.assertTrue((ROOT / 'static/src/img/car_modern_small.svg').exists())
        self.assertTrue((ROOT / 'static/src/img/car_modern_large.svg').exists())


if __name__ == '__main__':
    unittest.main()
