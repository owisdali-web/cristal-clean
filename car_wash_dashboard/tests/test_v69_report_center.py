import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class V69ReportCenterContractTest(unittest.TestCase):
    def test_manifest_version_and_report_backend_are_registered(self):
        manifest = ast.literal_eval((ROOT / '__manifest__.py').read_text(encoding='utf-8'))
        self.assertTrue(manifest['version'].startswith('18.0.6.9'))
        init_source = (ROOT / 'models/__init__.py').read_text(encoding='utf-8')
        self.assertIn('report_center', init_source)
        controller_init = (ROOT / 'controllers/__init__.py').read_text(encoding='utf-8')
        self.assertIn('reports', controller_init)

    def test_backend_exposes_filtered_report_center_from_paid_pos_and_mrp(self):
        source = (ROOT / 'models/report_center.py').read_text(encoding='utf-8')
        self.assertIn('def get_report_center_data', source)
        self.assertIn("('order_id.state', 'in', list(PAID_POS_STATES))", source)
        self.assertIn('_cw_analytics_wash_product_ids', source)
        for token in (
            "'kpis'", "'revenue_trend'", "'cars_by_service'", "'payment_methods'",
            "'operations'", "'services'", "'stations'", "'customers'", "'supplies'",
            "'exceptions'", "'filter_options'",
        ):
            self.assertIn(token, source)
        for field in ('period', 'date_from', 'date_to', 'station_id', 'service_id', 'vehicle_size', 'customer_id', 'status'):
            self.assertIn(field, source)
        self.assertNotIn('.create(', source)
        self.assertNotIn('.write(', source)
        self.assertNotIn('.unlink(', source)

    def test_export_controller_has_authenticated_pdf_and_excel_routes(self):
        source = (ROOT / 'controllers/reports.py').read_text(encoding='utf-8')
        self.assertIn('/car_wash_dashboard/reports/pdf', source)
        self.assertIn('/car_wash_dashboard/reports/xlsx', source)
        self.assertIn("auth='user'", source)
        self.assertIn('get_report_center_data', source)
        self.assertIn('xlsxwriter', source)
        self.assertIn('reportlab', source)
        self.assertIn('Content-Disposition', source)

    def test_reports_page_is_internal_navigation_not_standard_list_action(self):
        js = (ROOT / 'static/src/js/dashboard.js').read_text(encoding='utf-8')
        xml = (ROOT / 'static/src/xml/dashboard.xml').read_text(encoding='utf-8')
        for token in ('reportsLoading', 'reportsLoaded', 'reportTab', 'reportFilters', 'fetchReports', 'setReportTab', 'applyReportPreset', 'exportReport', 'printReport'):
            self.assertIn(token, js)
        self.assertIn('get_report_center_data', js)
        self.assertIn('this.state.page = "reports"', js)
        self.assertIn("state.page === 'reports'", xml)
        self.assertIn("state.page === 'reports' ? 'is-active'", xml)

    def test_report_visual_contract_matches_approved_mockup(self):
        xml = (ROOT / 'static/src/xml/dashboard.xml').read_text(encoding='utf-8')
        for label in (
            'Period', 'Station', 'Service', 'Vehicle Size', 'Customer', 'Apply Filters', 'Reset',
            'Overview', 'Operations', 'Revenue', 'Services', 'Stations', 'Customers', 'Supplies', 'Exceptions',
            'Total Cars', 'Finished Cars', 'Waiting Cars', 'Total Revenue', 'Average Ticket', 'Unique Customers',
            'Revenue Trend', 'Cars by Service', 'Payment Methods', 'Recent Wash Operations',
            'Print Report', 'Export PDF', 'Export Excel', 'Saved Reports', 'Daily Center Report',
            'Monthly Management', 'Revenue Report', 'Station Performance', 'Customer Report', 'Inventory Report',
        ):
            self.assertIn(label, xml)

        css = (ROOT / 'static/src/css/dashboard_concept_replica.css').read_text(encoding='utf-8')
        for selector in (
            '.cw-reports-page', '.cw-report-filters', '.cw-report-tabs', '.cw-report-kpis',
            '.cw-report-chart-card', '.cw-report-table', '.cw-report-actions', '.cw-saved-reports',
        ):
            self.assertIn(selector, css)

    def test_print_pdf_xlsx_actions_use_same_active_filters(self):
        js = (ROOT / 'static/src/js/dashboard.js').read_text(encoding='utf-8')
        self.assertIn('reportQueryString()', js)
        self.assertIn('window.print()', js)
        self.assertIn('/car_wash_dashboard/reports/pdf?', js)
        self.assertIn('/car_wash_dashboard/reports/xlsx?', js)
        self.assertIn('this.state.reportFilters', js)


if __name__ == '__main__':
    unittest.main()
