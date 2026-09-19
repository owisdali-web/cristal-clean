import ast
import importlib.util
import re
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_customer_logic():
    spec = importlib.util.spec_from_file_location('cw_customer_logic', ROOT / 'customer_logic.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def po_entries():
    text = (ROOT / 'i18n' / 'ar_001.po').read_text(encoding='utf-8')
    entries = {}
    for block in re.split(r'\n\s*\n', text):
        mid = re.search(r'^msgid\s+"(.*)"$', block, re.M)
        mst = re.search(r'^msgstr\s+"(.*)"$', block, re.M)
        if mid and mst and mid.group(1):
            entries[mid.group(1)] = mst.group(1)
    return entries


class V697Customers360Test(unittest.TestCase):
    def test_customer_segment_rules_are_deterministic(self):
        logic = load_customer_logic()
        self.assertEqual(logic.customer_segment(1, 80, 2, 500), 'new')
        self.assertEqual(logic.customer_segment(3, 220, 5, 500), 'regular')
        self.assertEqual(logic.customer_segment(6, 350, 4, 500), 'frequent')
        self.assertEqual(logic.customer_segment(3, 800, 4, 500), 'high_value')
        self.assertEqual(logic.customer_segment(8, 1200, 45, 500), 'inactive')

    def test_high_value_cutoff_uses_top_quintile_without_zeroing_small_datasets(self):
        logic = load_customer_logic()
        self.assertEqual(logic.high_value_cutoff([]), 0.0)
        self.assertEqual(logic.high_value_cutoff([100]), 100.0)
        self.assertEqual(logic.high_value_cutoff([100, 200, 300, 400, 500]), 500.0)
        self.assertEqual(logic.high_value_cutoff([100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]), 900.0)

    def test_backend_customer_intelligence_contract_is_company_scoped_paid_pos_and_read_only(self):
        source = (ROOT / 'models/customer_intelligence.py').read_text(encoding='utf-8')
        self.assertIn('def get_customer_intelligence_data', source)
        self.assertIn('def get_customer_intelligence_detail', source)
        self.assertIn("('order_id.company_id', '=', self.env.company.id)", source)
        self.assertIn("('order_id.state', 'in', list(PAID_POS_STATES))", source)
        self.assertIn("customer_visits[partner.id].add(order.id)", source)
        for forbidden in ('.create(', '.write(', '.unlink('):
            self.assertNotIn(forbidden, source)

    def test_top_customer_chart_does_not_duplicate_each_ranked_customer(self):
        source = (ROOT / 'models/customer_intelligence.py').read_text(encoding='utf-8')
        block = re.search(r"'top_by_revenue': \[(.*?)\],\n\s*'most_frequent'", source, re.S)
        self.assertIsNotNone(block)
        self.assertEqual(block.group(1).count('for row in rows[:6]'), 1)

    def test_customer_timeline_translates_standard_mrp_state_labels_explicitly(self):
        source = (ROOT / 'models/customer_intelligence.py').read_text(encoding='utf-8')
        for token in ("_('Draft')", "_('Confirmed')", "_('In Progress')", "_('To Close')", "_('Done')", "_('Cancelled')"):
            self.assertIn(token, source)

    def test_backend_exposes_customer_kpis_rows_charts_filters_and_detail(self):
        source = (ROOT / 'models/customer_intelligence.py').read_text(encoding='utf-8')
        for token in (
            "'total_customers'", "'new_this_month'", "'returning_customers'",
            "'frequent_customers'", "'inactive_customers'", "'average_spend'",
            "'customers'", "'top_by_revenue'", "'most_frequent'",
            "'new_vs_returning'", "'service_preferences'", "'filter_options'",
            "'vehicles'", "'timeline'", "'services'",
        ):
            self.assertIn(token, source)

    def test_customers_sidebar_opens_internal_page_and_keeps_live_journey_nested(self):
        js = (ROOT / 'static/src/js/dashboard.js').read_text(encoding='utf-8')
        xml = (ROOT / 'static/src/xml/dashboard.xml').read_text(encoding='utf-8')
        open_customers = re.search(r'\n\s*async openCustomers\(\) \{(.*?)\n\s*\}', js, re.S)
        self.assertIsNotNone(open_customers)
        self.assertIn('this.state.page = "customers"', open_customers.group(1))
        self.assertIn('fetchCustomers', open_customers.group(1))
        self.assertNotIn('res_model: "res.partner"', open_customers.group(1))
        self.assertIn("state.page === 'customers'", xml)
        self.assertIn("state.page === 'customer_display'", xml)
        self.assertIn("tr('Live Car Journey')", xml)

    def test_customers_frontend_has_interactive_360_contract(self):
        js = (ROOT / 'static/src/js/dashboard.js').read_text(encoding='utf-8')
        xml = (ROOT / 'static/src/xml/dashboard.xml').read_text(encoding='utf-8')
        for token in (
            'customersLoading', 'customerFilters', 'selectedCustomerId', 'customerDetail',
            'fetchCustomers', 'selectCustomer', 'closeCustomerDetail', 'openCustomerRecord',
            'applyCustomerSegment', 'applyCustomerService',
        ):
            self.assertIn(token, js)
        for token in (
            'cw-customers-page', 'cw-customer-kpis', 'cw-customer-list',
            'cw-customer-360', 'cw-customer-timeline', 'cw-customer-vehicles',
            'cw-customer-chart', "tr('Total Customers')", "tr('New This Month')",
            "tr('Returning Customers')", "tr('Frequent Customers')",
            "tr('Inactive Customers')", "tr('Average Spend')",
        ):
            self.assertIn(token, xml)

    def test_kpi_drilldowns_match_their_displayed_customer_populations(self):
        js = (ROOT / 'static/src/js/dashboard.js').read_text(encoding='utf-8')
        xml = (ROOT / 'static/src/xml/dashboard.xml').read_text(encoding='utf-8')
        self.assertIn('state.customerBehaviorFilter === "new_month"', js)
        self.assertIn('row.is_new_this_month', js)
        self.assertIn('state.customerBehaviorFilter === "frequent"', js)
        self.assertIn('Number(row.visits || 0) >= 5', js)
        self.assertIn("applyCustomerBehavior('new_month')", xml)
        self.assertIn("applyCustomerBehavior('frequent')", xml)

    def test_customer_360_styles_support_light_dark_and_rtl(self):
        css = (ROOT / 'static/src/css/dashboard_concept_replica.css').read_text(encoding='utf-8')
        for selector in (
            '.cw-customers-page', '.cw-customer-360', '.cw-customer-chart',
            '.theme-dark .cw-customers-page', '.is-rtl .cw-customers-page',
        ):
            self.assertIn(selector, css)

    def test_new_customer_labels_are_in_arabic_catalog_and_runtime_fallback(self):
        entries = po_entries()
        required = (
            'Customer Intelligence', 'Customer 360', 'Total Customers', 'New This Month',
            'Frequent Customers', 'Inactive Customers', 'Customer Search', 'All Segments',
            'Regular', 'Frequent', 'High Value', 'Inactive', 'Known Vehicles',
            'Visit Timeline', 'Top Customers by Revenue', 'Most Frequent Customers',
            'Service Preferences', 'Open Customer in Odoo', 'No customers match the filters.',
        )
        missing = [label for label in required if not entries.get(label, '').strip()]
        self.assertEqual(missing, [], msg=f'Missing Arabic Customers 360 labels: {missing}')
        ui = (ROOT / 'static/src/js/ui_translations.js').read_text(encoding='utf-8')
        for label in required:
            self.assertIn(f'"{label}"', ui)

    def test_manifest_version_is_valid_v697(self):
        manifest = ast.literal_eval((ROOT / '__manifest__.py').read_text(encoding='utf-8'))
        self.assertEqual(manifest['version'], '18.0.6.9.7')


if __name__ == '__main__':
    unittest.main()
