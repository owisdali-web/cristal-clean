import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class V68CustomerLoungeDisplayContractTest(unittest.TestCase):
    def test_manifest_version_is_v68(self):
        manifest = ast.literal_eval((ROOT / '__manifest__.py').read_text(encoding='utf-8'))
        self.assertEqual(manifest['version'], '18.0.6.9')

    def test_customer_display_is_nested_under_customers_in_sidebar(self):
        xml = (ROOT / 'static/src/xml/dashboard.xml').read_text(encoding='utf-8')
        self.assertIn('cw-nav-customer-group', xml)
        self.assertIn('openCustomers', xml)
        self.assertIn('showCustomerDisplay', xml)
        self.assertIn("tr('Live Car Journey')", xml)
        self.assertLess(xml.index('openCustomers'), xml.index('showCustomerDisplay'))

    def test_customer_display_handlers_are_bound_for_owl_callbacks(self):
        js = (ROOT / 'static/src/js/dashboard.js').read_text(encoding='utf-8')
        for handler in ('showCustomerDisplay', 'advanceFeaturedVehicle', 'toggleCustomerTvMode', 'onCustomerFullscreenChange'):
            self.assertIn(f'this.{handler} = this.{handler}.bind(this);', js)

    def test_customer_display_uses_existing_dashboard_payload_only(self):
        js = (ROOT / 'static/src/js/dashboard.js').read_text(encoding='utf-8')
        for token in ('state.data.queue', 'state.data.stations', 'state.data.finished_today_items'):
            self.assertIn(token, js)
        self.assertNotIn('get_customer_display_demo_data', js)
        self.assertNotIn('create_customer_display', js)

    def test_customer_display_has_four_customer_facing_stages(self):
        js = (ROOT / 'static/src/js/dashboard.js').read_text(encoding='utf-8')
        xml = (ROOT / 'static/src/xml/dashboard.xml').read_text(encoding='utf-8')
        for stage in ('waiting', 'washing', 'finishing', 'ready'):
            self.assertIn(stage, js)
        for label in ('Waiting', 'Washing', 'Drying / Finishing', 'Ready for Pickup'):
            self.assertIn(label, xml)

    def test_featured_vehicle_rotates_every_two_minutes_and_ready_has_priority(self):
        js = (ROOT / 'static/src/js/dashboard.js').read_text(encoding='utf-8')
        self.assertIn('CUSTOMER_FEATURE_ROTATION_MS = 120000', js)
        self.assertIn('advanceFeaturedVehicle', js)
        self.assertIn('customerFeaturedVehicle', js)
        self.assertIn('customerDisplayReadyVehicles', js)
        self.assertIn('handleCustomerReadyPriority', js)

    def test_customer_display_supports_eta_and_tv_fullscreen(self):
        js = (ROOT / 'static/src/js/dashboard.js').read_text(encoding='utf-8')
        xml = (ROOT / 'static/src/xml/dashboard.xml').read_text(encoding='utf-8')
        css = (ROOT / 'static/src/css/dashboard_concept_replica.css').read_text(encoding='utf-8')
        self.assertIn('customerEtaLabel', js)
        self.assertIn('toggleCustomerTvMode', js)
        self.assertIn('requestFullscreen', js)
        self.assertIn('exitFullscreen', js)
        self.assertIn('cw-customer-display-page', xml)
        self.assertIn('cw-customer-featured', xml)
        self.assertIn('.cw-customer-display-page', css)
        self.assertIn('.customer-display-tv', css)

    def test_customer_display_is_read_only(self):
        js = (ROOT / 'static/src/js/dashboard.js').read_text(encoding='utf-8')
        # Customer display should not introduce a dedicated mutation RPC/action.
        start = js.find('showCustomerDisplay')
        self.assertNotEqual(start, -1)
        customer_slice = js[start:start + 14000]
        for forbidden in ('.write(', '.unlink(', '.create(', 'button_start', 'button_finish'):
            self.assertNotIn(forbidden, customer_slice)


if __name__ == '__main__':
    unittest.main()
