import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class V67IdentityI18nThemeContractTest(unittest.TestCase):
    def test_manifest_version_is_v67(self):
        manifest = ast.literal_eval((ROOT / '__manifest__.py').read_text(encoding='utf-8'))
        self.assertEqual(manifest['version'], '18.0.6.7')

    def test_crystal_clean_brand_asset_and_sidebar_contract(self):
        xml = (ROOT / 'static/src/xml/dashboard.xml').read_text(encoding='utf-8')
        self.assertTrue((ROOT / 'static/src/img/crystal_clean_logo.webp').exists())
        self.assertIn('/car_wash_dashboard/static/src/img/crystal_clean_logo.webp', xml)
        self.assertIn('Crystal Clean', xml)
        self.assertIn('WASH CENTER', xml)
        self.assertNotIn('CleanDrive', xml)

    def test_theme_state_toggle_and_persistence_exist(self):
        js = (ROOT / 'static/src/js/dashboard.js').read_text(encoding='utf-8')
        xml = (ROOT / 'static/src/xml/dashboard.xml').read_text(encoding='utf-8')
        css = (ROOT / 'static/src/css/dashboard_concept_replica.css').read_text(encoding='utf-8')
        for token in (
            'theme:', 'toggleTheme', 'loadThemePreference', 'saveThemePreference',
            'car_wash_dashboard_theme',
        ):
            self.assertIn(token, js)
        self.assertIn('this.toggleTheme = this.toggleTheme.bind(this);', js)
        self.assertIn('toggleTheme', xml)
        self.assertIn('theme-dark', xml)
        self.assertIn('.cw-dashboard-app.theme-dark', css)
        self.assertIn('Dark mode', ROOT.joinpath('i18n/ar_001.po').read_text(encoding='utf-8'))

    def test_rtl_direction_contract_exists(self):
        js = (ROOT / 'static/src/js/dashboard.js').read_text(encoding='utf-8')
        xml = (ROOT / 'static/src/xml/dashboard.xml').read_text(encoding='utf-8')
        css = (ROOT / 'static/src/css/dashboard_concept_replica.css').read_text(encoding='utf-8')
        self.assertIn('detectRtl', js)
        self.assertIn('isRtl', js)
        self.assertIn('is-rtl', xml)
        self.assertIn('.cw-dashboard-app.is-rtl', css)

    def test_dynamic_component_labels_use_odoo_translation(self):
        for rel in (
            'static/src/js/components/queue_panel.js',
            'static/src/js/components/station_card.js',
            'static/src/js/components/station_detail.js',
        ):
            source = (ROOT / rel).read_text(encoding='utf-8')
            self.assertIn('@web/core/l10n/translation', source, msg=rel)
            self.assertIn('_t(', source, msg=rel)

    def test_arabic_catalog_covers_operational_and_analytics_surfaces(self):
        po = (ROOT / 'i18n/ar_001.po').read_text(encoding='utf-8')
        required = (
            'Crystal Clean', 'WASH CENTER', 'Business Analytics', 'Car Wash Dashboard',
            'Today\'s Revenue', 'Monthly Revenue', 'Daily Washes', 'Popular Services',
            'Station Utilization', 'Top Customers', 'Supplies Near Depletion',
            'Revenue Trend', 'New vs Returning Customers', 'Revenue by Service Category',
            'Recent Activity', 'General Waiting Queue', 'Work Centers', 'Grid View',
            'List View', 'Available', 'Busy', 'Finishing', 'Open in Odoo',
            'Light mode', 'Dark mode', 'Search cars, customers, or plates...',
        )
        for label in required:
            self.assertIn(f'msgid "{label}"', po, msg=label)
        self.assertIn('msgstr "تحليلات الأعمال"', po)
        self.assertIn('msgstr "الوضع الداكن"', po)

    def test_backend_detail_labels_use_odoo_translation(self):
        source = (ROOT / 'models/business_analytics.py').read_text(encoding='utf-8')
        self.assertIn('from odoo import _, api, fields, models', source)
        for label in (
            "_('Today\\'s Revenue')", "_('Monthly Revenue')", "_('Station Utilization')",
            "_('Payment received')", "_('Recent Activity')",
        ):
            self.assertIn(label, source)


if __name__ == '__main__':
    unittest.main()
