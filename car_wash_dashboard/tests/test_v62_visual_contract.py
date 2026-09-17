import ast
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class V62VisualContractTest(unittest.TestCase):
    def test_manifest_version_is_v62(self):
        manifest = ast.literal_eval((ROOT / '__manifest__.py').read_text(encoding='utf-8'))
        self.assertEqual(manifest['version'], '18.0.6.5')

    def test_station_payload_exposes_real_expected_duration_progress(self):
        production = (ROOT / 'models/mrp_production_extend.py').read_text(encoding='utf-8')
        self.assertIn("['duration_expected']", production)
        self.assertIn("'expected_minutes':", production)
        self.assertIn("'progress_percent':", production)
        self.assertIn('_cw_progress_percent', production)
        # Progress must be derived from work-order timing, not hard-coded demo values.
        self.assertNotRegex(production, r"'progress_percent'\s*:\s*(45|55|60|75|80|90)")

    def test_station_card_renders_progress_only_when_backed_by_expected_duration(self):
        xml = (ROOT / 'static/src/xml/dashboard.xml').read_text(encoding='utf-8')
        self.assertIn('cw-progress-track', xml)
        self.assertIn('progress_percent', xml)
        self.assertIn('expected_minutes', xml)
        self.assertIn('progressStyle()', xml)

    def test_visual_status_supports_finishing_without_mutating_workorder_state(self):
        component = (ROOT / 'static/src/js/components/station_card.js').read_text(encoding='utf-8')
        production = (ROOT / 'models/mrp_production_extend.py').read_text(encoding='utf-8')
        self.assertIn('finishing: "Finishing"', component)
        self.assertIn("'visual_status':", production)
        self.assertNotIn("workorder.write", production)
        self.assertNotIn("wo.write", production)

    def test_reference_sidebar_art_asset_exists(self):
        asset = ROOT / 'static/src/img/sidebar_wash_reference.webp'
        self.assertTrue(asset.exists())
        self.assertGreater(asset.stat().st_size, 10_000)
        css = (ROOT / 'static/src/css/dashboard_concept_replica.css').read_text(encoding='utf-8')
        xml = (ROOT / 'static/src/xml/dashboard.xml').read_text(encoding='utf-8')
        self.assertIn('sidebar_wash_reference.webp', xml)
        self.assertIn('.cw-sidebar-art', css)

    def test_reference_desktop_geometry_keeps_queue_and_five_station_columns(self):
        css = (ROOT / 'static/src/css/dashboard_concept_replica.css').read_text(encoding='utf-8')
        layout = re.search(r'\.cw-operations-layout\s*\{(.*?)\}', css, re.S)
        grid = re.search(r'\.cw-station-grid\s*\{(.*?)\}', css, re.S)
        detail = re.search(r'\.cw-dashboard-app\.has-detail\s*\{(.*?)\}', css, re.S)
        self.assertIsNotNone(layout)
        self.assertIsNotNone(grid)
        self.assertIsNotNone(detail)
        self.assertRegex(layout.group(1), r'grid-template-columns\s*:\s*3(?:0|1)\dpx\s+minmax\(0,\s*1fr\)')
        self.assertRegex(grid.group(1), r'grid-template-columns\s*:\s*repeat\(5,\s*minmax\(0,\s*1fr\)\)')
        self.assertRegex(detail.group(1), r'grid-template-columns\s*:\s*210px\s+minmax\(0,\s*1fr\)\s+330px')

    def test_detail_panel_has_reference_sections_and_safe_odoo_actions(self):
        xml = (ROOT / 'static/src/xml/dashboard.xml').read_text(encoding='utf-8')
        for label in ('Service', 'Vehicle Size', 'Customer', 'Service Notes', 'Time in station'):
            self.assertIn(label, xml)
        # Keep Shop Floor as truth instead of silently mutating the work order from the dashboard.
        self.assertIn('Open Wash Screen', xml)
        self.assertIn('Open Car Wash Order', xml)
        self.assertNotIn('t-on-click="markFinished"', xml)


    def test_detail_mode_compacts_station_progress_like_reference(self):
        css = (ROOT / 'static/src/css/dashboard_concept_replica.css').read_text(encoding='utf-8')
        self.assertRegex(css, r'\.cw-dashboard-app\.has-detail\s+\.cw-progress-row\s*\{[^}]*display\s*:\s*none')

    def test_dashboard_still_uses_page_scroll(self):
        css = (ROOT / 'static/src/css/dashboard_concept_replica.css').read_text(encoding='utf-8')
        root = re.search(r'\.cw-dashboard-app\s*\{(.*?)\}', css, re.S)
        self.assertIsNotNone(root)
        block = root.group(1)
        self.assertRegex(block, r'overflow-y\s*:\s*auto')
        self.assertNotRegex(block, r'overflow\s*:\s*hidden')


if __name__ == '__main__':
    unittest.main()
