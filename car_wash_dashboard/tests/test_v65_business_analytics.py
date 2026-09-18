import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class V65BusinessAnalyticsContractTest(unittest.TestCase):
    def test_manifest_and_backend_contract(self):
        manifest = ast.literal_eval((ROOT / '__manifest__.py').read_text(encoding='utf-8'))
        self.assertTrue(manifest['version'].startswith('18.0.6.9'))
        self.assertIn('point_of_sale', manifest['depends'])

        init_source = (ROOT / 'models/__init__.py').read_text(encoding='utf-8')
        self.assertIn('business_analytics', init_source)

        source_path = ROOT / 'models/business_analytics.py'
        self.assertTrue(source_path.exists())
        source = source_path.read_text(encoding='utf-8')
        self.assertIn('def get_business_analytics_data', source)
        for token in (
            "'kpis'", "'daily_washes'", "'popular_services'", "'station_utilization'",
            "'top_customers'", "'low_supplies'", "'revenue_trend'", "'customer_mix'",
            "'revenue_by_category'", "'recent_activity'",
        ):
            self.assertIn(token, source)
        self.assertIn('_cw_analytics_period_bounds', source)
        self.assertNotIn('.create(', source)
        self.assertNotIn('.write(', source)
        self.assertNotIn('.unlink(', source)

    def test_frontend_navigation_and_analytics_rpc_contract(self):
        js = (ROOT / 'static/src/js/dashboard.js').read_text(encoding='utf-8')
        xml = (ROOT / 'static/src/xml/dashboard.xml').read_text(encoding='utf-8')

        for token in (
            'analyticsPeriod', 'analyticsLoading', 'showAnalytics', 'showOperations',
            'fetchAnalytics', 'setAnalyticsPeriod', 'get_business_analytics_data',
        ):
            self.assertIn(token, js)

        self.assertIn('Business Analytics', js + xml)
        self.assertIn('Today\\\'s Revenue', xml)
        self.assertIn('Monthly Revenue', xml)
        self.assertIn('Daily Washes', xml)
        self.assertIn('Popular Services', xml)
        self.assertIn('Station Utilization', xml)
        self.assertIn('Top Customers', xml)
        self.assertIn('Supplies Near Depletion', xml)
        self.assertIn('Revenue Trend', xml)
        self.assertIn('New vs Returning Customers', xml)
        self.assertIn('Revenue by Service Category', xml)
        self.assertIn('Recent Activity', xml)
        self.assertIn('showAnalytics', xml)
        self.assertIn('showOperations', xml)

    def test_analytics_visual_contract(self):
        css = (ROOT / 'static/src/css/dashboard_concept_replica.css').read_text(encoding='utf-8')
        for selector in (
            '.cw-analytics-page',
            '.cw-analytics-kpis',
            '.cw-analytics-kpi',
            '.cw-analytics-grid',
            '.cw-analytics-card',
            '.cw-line-chart',
            '.cw-bars-chart',
            '.cw-donut',
            '.cw-ranked-list',
            '.cw-activity-list',
        ):
            self.assertIn(selector, css)

    def test_analytics_callbacks_are_bound_and_pos_metrics_are_wash_scoped(self):
        js = (ROOT / 'static/src/js/dashboard.js').read_text(encoding='utf-8')
        for handler in ('showAnalytics', 'showOperations', 'fetchAnalytics', 'setAnalyticsPeriod', 'onAnalyticsPeriodChange'):
            self.assertIn(f'this.{handler} = this.{handler}.bind(this);', js)

        source = (ROOT / 'models/business_analytics.py').read_text(encoding='utf-8')
        self.assertIn('_cw_analytics_wash_product_ids', source)
        self.assertIn("('product_id', 'in', wash_product_ids)", source)
        self.assertIn('_cw_analytics_line_amount', source)


if __name__ == '__main__':
    unittest.main()
