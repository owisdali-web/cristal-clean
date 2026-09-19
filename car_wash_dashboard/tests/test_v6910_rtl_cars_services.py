import ast
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / 'static/src/css/dashboard_concept_replica.css'
JS = ROOT / 'static/src/js/dashboard.js'
XML = ROOT / 'static/src/xml/dashboard.xml'


class V6910RtlCarsServicesTest(unittest.TestCase):
    def test_manifest_version_is_v6910_or_newer(self):
        manifest = ast.literal_eval((ROOT / '__manifest__.py').read_text(encoding='utf-8'))
        self.assertGreaterEqual(tuple(map(int, manifest['version'].split('.'))), (18, 0, 6, 9, 10))

    def test_rtl_sidebar_is_mirrored_on_desktop(self):
        css = CSS.read_text(encoding='utf-8')
        self.assertRegex(css, r'\.cw-dashboard-app\.is-rtl\s+\.cw-sidebar\s*\{[^}]*grid-column:\s*2;')
        self.assertRegex(css, r'\.cw-dashboard-app\.is-rtl\.has-detail\s+\.cw-sidebar\s*\{[^}]*grid-column:\s*3;')
        self.assertRegex(css, r'\.cw-dashboard-app\.is-rtl\s+\.cw-main\s*\{[^}]*grid-column:\s*1;')
        self.assertRegex(css, r'\.cw-dashboard-app\.is-rtl\s+\.cw-detail-drawer\s*\{[^}]*grid-column:\s*1;')

    def test_cars_and_services_are_dashboard_pages(self):
        js = JS.read_text(encoding='utf-8')
        xml = XML.read_text(encoding='utf-8')
        self.assertIn('this.state.page = "cars";', js)
        self.assertIn('this.state.page = "services";', js)
        self.assertIn("state.page === 'cars'", xml)
        self.assertIn("state.page === 'services'", xml)
        self.assertIn('Open All Wash Orders', xml)
        self.assertIn('Service Performance', xml)

    def test_pages_use_report_center_data_not_generic_lists(self):
        js = JS.read_text(encoding='utf-8')
        self.assertGreaterEqual(js.count('"get_report_center_data"'), 3)
        self.assertIn('async fetchCars(', js)
        self.assertIn('async fetchServices(', js)
        self.assertIn('openCarOrders()', js)
        self.assertIn('manageServices()', js)

    def test_car_stage_normalizes_odoo_done_and_cancel_states(self):
        js = JS.read_text(encoding='utf-8')
        self.assertIn('if (stage === "done" || stage === "finished") return "finished";', js)
        self.assertIn('if (stage === "cancel" || stage === "cancelled") return "cancelled";', js)


if __name__ == '__main__':
    unittest.main()
