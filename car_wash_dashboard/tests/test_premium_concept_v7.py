from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PremiumConceptV7Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qweb = (ROOT / 'static/src/xml/dashboard.xml').read_text(encoding='utf-8')
        cls.css = (ROOT / 'static/src/css/dashboard_concept_replica.css').read_text(encoding='utf-8')
        cls.js = (ROOT / 'static/src/js/dashboard.js').read_text(encoding='utf-8')
        cls.mrp = (ROOT / 'models/mrp_production_extend.py').read_text(encoding='utf-8')
        cls.manifest = (ROOT / '__manifest__.py').read_text(encoding='utf-8')

    def test_premium_shell_matches_approved_concept_sections(self):
        for token in (
            'cc-v7-sidebar',
            'cc-v7-topbar',
            'cc-v7-kpi-row',
            'cc-v7-wash-showcase',
            'cc-v7-auto-feature',
            'cc-v7-manual-feature',
            'cc-v7-bottom-grid',
            'cc-v7-stations-widget',
            'cc-v7-queue-widget',
            'cc-v7-time-widget',
            'cc-v7-revenue-widget',
        ):
            self.assertIn(token, self.qweb)

    def test_overview_loads_auto_and_manual_payloads_for_comparison(self):
        self.assertRegex(
            self.js,
            re.compile(r"activeSection\s*===\s*['\"]overview['\"].*?_fetchDashboard\(['\"]automatic['\"]\).*?_fetchDashboard\(['\"]manual['\"]\)", re.S),
        )
        self.assertIn('revenueSplitStyle', self.js)
        self.assertIn('automaticRevenuePercent', self.js)

    def test_vehicle_breakdown_and_identity_data_are_exposed(self):
        self.assertIn("'vehicle_counts':", self.mrp)
        self.assertIn("'user_name':", self.mrp)
        self.assertIn("'company_city':", self.mrp)

    def test_premium_css_contains_fullscreen_sidebar_and_feature_scenes(self):
        for selector in (
            '#crystal-concept .cc-v7-shell',
            '#crystal-concept .cc-v7-sidebar',
            '#crystal-concept .cc-v7-main',
            '#crystal-concept .cc-v7-auto-feature',
            '#crystal-concept .cc-v7-manual-feature',
            '#crystal-concept .cc-v7-donut',
        ):
            self.assertIn(selector, self.css)
        self.assertIn('linear-gradient', self.css)
        self.assertIn('conic-gradient', self.css)

    def test_qweb_does_not_call_js_global_number_constructor(self):
        self.assertNotRegex(self.qweb, r"\bNumber\s*\(")
        self.assertIn('formatAmount(state.data.revenue_today)', self.qweb)
        self.assertIn('formatAmount(value)', self.js)

    def test_version_is_bumped(self):
        self.assertIn("'version': '18.0.7.1'", self.manifest)


if __name__ == '__main__':
    unittest.main()
