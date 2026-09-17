import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class V66InteractiveAnalyticsContractTest(unittest.TestCase):
    def test_manifest_version_is_v66(self):
        manifest = ast.literal_eval((ROOT / '__manifest__.py').read_text(encoding='utf-8'))
        self.assertEqual(manifest['version'], '18.0.6.9')

    def test_backend_exposes_read_only_detail_rpc(self):
        source = (ROOT / 'models/business_analytics.py').read_text(encoding='utf-8')
        self.assertIn('def get_business_analytics_detail', source)
        for detail_type in (
            'today_revenue', 'monthly_revenue', 'washes_today', 'active_customers',
            'average_ticket', 'daily_washes', 'popular_service', 'station',
            'top_customer', 'supply', 'revenue_week', 'customer_mix',
            'revenue_category', 'recent_activity', 'station_overall', 'customer_mix_overall',
        ):
            self.assertIn(detail_type, source)
        self.assertIn("'model'", source)
        self.assertIn("'res_id'", source)
        self.assertNotIn('.create(', source)
        self.assertNotIn('.write(', source)
        self.assertNotIn('.unlink(', source)

    def test_summary_rows_include_stable_click_keys(self):
        source = (ROOT / 'models/business_analytics.py').read_text(encoding='utf-8')
        self.assertIn("'product_id': product_id", source)
        self.assertIn("'category_id':", source)
        self.assertIn("'bucket_key':", source)
        self.assertIn("'week_index':", source)
        self.assertIn("'model': 'pos.order'", source)
        self.assertIn("'model': 'mrp.production'", source)

    def test_frontend_has_bound_detail_handlers_and_rpc(self):
        js = (ROOT / 'static/src/js/dashboard.js').read_text(encoding='utf-8')
        for handler in ('openAnalyticsDetail', 'closeAnalyticsDetail', 'openAnalyticsRecord'):
            self.assertIn(f'this.{handler} = this.{handler}.bind(this);', js)
        self.assertIn('get_business_analytics_detail', js)
        self.assertIn('analyticsDetail', js)
        self.assertIn('analyticsDetailLoading', js)

    def test_every_analytics_surface_is_clickable(self):
        xml = (ROOT / 'static/src/xml/dashboard.xml').read_text(encoding='utf-8')
        expected = (
            "openAnalyticsDetail('today_revenue'",
            "openAnalyticsDetail('monthly_revenue'",
            "openAnalyticsDetail('washes_today'",
            "openAnalyticsDetail('active_customers'",
            "openAnalyticsDetail('average_ticket'",
            "openAnalyticsDetail('daily_washes'",
            "openAnalyticsDetail('popular_service'",
            "openAnalyticsDetail('station'",
            "openAnalyticsDetail('top_customer'",
            "openAnalyticsDetail('supply'",
            "openAnalyticsDetail('revenue_week'",
            "openAnalyticsDetail('customer_mix'",
            "openAnalyticsDetail('revenue_category'",
            "openAnalyticsDetail('recent_activity'",
        )
        for token in expected:
            self.assertIn(token, xml)

    def test_detail_panel_and_interactive_styles_exist(self):
        xml = (ROOT / 'static/src/xml/dashboard.xml').read_text(encoding='utf-8')
        css = (ROOT / 'static/src/css/dashboard_concept_replica.css').read_text(encoding='utf-8')
        for token in ('cw-analytics-detail-panel', 'cw-analytics-detail-row', "tr('Open in Odoo')"):
            self.assertIn(token, xml)
        for selector in (
            '.cw-analytics-clickable',
            '.cw-analytics-detail-panel',
            '.cw-analytics-detail-row',
            '.cw-analytics-detail-backdrop',
        ):
            self.assertIn(selector, css)


if __name__ == '__main__':
    unittest.main()
