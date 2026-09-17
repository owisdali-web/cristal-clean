import ast
import importlib.util
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_pure_logic():
    spec = importlib.util.spec_from_file_location('cw_logic', ROOT / 'dashboard_logic.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class V62ContractTest(unittest.TestCase):
    def test_manifest_version_is_v62(self):
        manifest = ast.literal_eval((ROOT / '__manifest__.py').read_text(encoding='utf-8'))
        self.assertEqual(manifest['version'], '18.0.6.8')

    def test_vehicle_size_does_not_guess_from_legacy_vehicle_type(self):
        logic = load_pure_logic()
        for value in ('car', 'truck', 'van', 'pickup', 'suv', 'sedan'):
            self.assertEqual(logic.normalize_vehicle_size(value, ''), '')
        self.assertEqual(logic.normalize_vehicle_size('small', ''), 'small')
        self.assertEqual(logic.normalize_vehicle_size('large', ''), 'large')
        self.assertEqual(logic.normalize_vehicle_size('', 'تنظيف خارجي - سيارة صغيرة'), 'small')
        self.assertEqual(logic.normalize_vehicle_size('', 'تنظيف داخلي - سيارة كبيرة'), 'large')

    def test_dashboard_root_uses_page_scroll_not_clipping(self):
        css = (ROOT / 'static/src/css/dashboard_concept_replica.css').read_text(encoding='utf-8')
        root = re.search(r'\.cw-dashboard-app\s*\{(.*?)\}', css, re.S)
        self.assertIsNotNone(root)
        block = root.group(1)
        self.assertNotRegex(block, r'overflow\s*:\s*hidden')
        self.assertRegex(block, r'(?<!min-)height\s*:\s*100%')
        self.assertRegex(block, r'overflow-y\s*:\s*auto')
        main = re.search(r'\.cw-main\s*\{(.*?)\}', css, re.S)
        self.assertIsNotNone(main)
        self.assertNotRegex(main.group(1), r'overflow\s*:\s*auto')

    def test_station_migration_exists_and_maps_a1_to_a10(self):
        path = ROOT / 'migrations/18.0.6.1/post-migrate.py'
        self.assertTrue(path.exists())
        text = path.read_text(encoding='utf-8')
        self.assertIn('A1', text)
        self.assertIn('A10', text)
        self.assertIn("'automatic'", text)
        self.assertIn("'polishing'", text)
        self.assertIn("'general'", text)
        self.assertIn("'active': True", text)
        self.assertIn("'car_wash_enabled': True", text)
        self.assertNotIn('.unlink(', text)
        self.assertNotIn('.create(', text)

    def test_explicit_vehicle_size_fields_exist(self):
        sale = (ROOT / 'models/sale_order_extend.py').read_text(encoding='utf-8')
        production = (ROOT / 'models/mrp_production_extend.py').read_text(encoding='utf-8')
        view = (ROOT / 'views/sale_order_views.xml').read_text(encoding='utf-8')
        self.assertIn('car_wash_vehicle_size = fields.Selection', sale)
        self.assertIn('car_wash_vehicle_size = fields.Selection', production)
        self.assertIn('name="car_wash_vehicle_size"', view)
        self.assertIn("['car_wash_vehicle_size', 'x_cc_vehicle_size', 'vehicle_size']", production)

    def test_realtime_bus_and_polling_fallback_exist(self):
        realtime = ROOT / 'models/dashboard_realtime.py'
        self.assertTrue(realtime.exists())
        py = realtime.read_text(encoding='utf-8')
        js = (ROOT / 'static/src/js/dashboard.js').read_text(encoding='utf-8')
        self.assertIn("self.env['bus.bus']._sendone", py)
        self.assertIn('car_wash_dashboard_refresh', py)
        self.assertIn('x_cc_vehicle_plate', py)
        self.assertNotIn("'vehicle_plate':", py)
        self.assertNotIn("'x_cc_vehicle_plate':", py)
        self.assertIn('useService("bus_service")', js)
        self.assertIn('addChannel', js)
        self.assertIn('addEventListener("notification"', js)
        self.assertIn('30000', js)

    def test_routing_diagnostic_exists_without_destructive_rewrite(self):
        wc = (ROOT / 'models/mrp_workcenter_extend.py').read_text(encoding='utf-8')
        notes = (ROOT / 'UPGRADE_NOTES.md').read_text(encoding='utf-8')
        self.assertIn('get_car_wash_routing_diagnostics', wc)
        self.assertRegex(notes, r'one(?:\s+active)?\s+Work Order')
        self.assertRegex(notes, r'(does not delete|instead of deleting|never delete)')
        self.assertNotIn('.unlink(', wc)

    def test_mrp_size_sync_uses_explicit_sale_size_only(self):
        production = (ROOT / 'models/mrp_production_extend.py').read_text(encoding='utf-8')
        self.assertIn('_cw_sync_vehicle_size_from_sale', production)
        self.assertIn("sale.car_wash_vehicle_size", production)
        self.assertNotIn("vehicle_type ==", production)

    def test_sale_vehicle_edits_trigger_refresh_without_payload_leak(self):
        py = (ROOT / 'models/dashboard_realtime.py').read_text(encoding='utf-8')
        for field in ('x_cc_vehicle_plate', 'x_cc_vehicle_model', 'x_cc_vehicle_color', 'x_cc_vehicle_notes'):
            self.assertIn(field, py)
        self.assertNotIn("'plate':", py)
        self.assertNotIn("'customer_name':", py)

    def test_mrp_size_resync_runs_when_sale_reference_arrives_late(self):
        realtime = (ROOT / 'models/dashboard_realtime.py').read_text(encoding='utf-8')
        self.assertIn("'x_cc_sale_order_ref' in vals", realtime)
        self.assertIn('_cw_sync_vehicle_size_from_sale()', realtime)


    def test_progress_percentage_uses_real_elapsed_and_expected_minutes(self):
        logic = load_pure_logic()
        self.assertEqual(logic.calculate_progress_percent(6, 10), 60)
        self.assertEqual(logic.calculate_progress_percent(9, 10), 90)
        self.assertEqual(logic.calculate_progress_percent(15, 10), 100)
        self.assertEqual(logic.calculate_progress_percent(0, 10), 0)
        self.assertFalse(logic.calculate_progress_percent(4, 0))
        self.assertFalse(logic.calculate_progress_percent(False, 10))

    def test_concept_reference_shell_is_present(self):
        xml = (ROOT / 'static/src/xml/dashboard.xml').read_text(encoding='utf-8')
        for label in ('Dashboard', 'Cars', 'Work Centers', 'Services', 'Customers', 'Reports', 'Settings'):
            self.assertIn(label, xml)
        self.assertIn('General Waiting Queue', xml)
        self.assertIn('Work Centers (10)', xml)
        self.assertIn('viewModeLabel', xml)
        self.assertIn('cw-user-summary', xml)
        self.assertIn('cw-detail-drawer', xml)

    def test_routing_migration_preserves_material_links_on_retained_operation(self):
        text = (ROOT / 'migrations/18.0.6.1/post-migrate.py').read_text(encoding='utf-8')
        self.assertIn('bom.bom_line_ids', text)
        self.assertIn("'operation_id': keeper.id", text)
        self.assertIn('bom.byproduct_ids', text)
        self.assertIn('blocked_by_operation_ids', text)

    def test_routing_migration_is_company_scoped(self):
        text = (ROOT / 'migrations/18.0.6.1/post-migrate.py').read_text(encoding='utf-8')
        self.assertIn("Bom.search([('company_id', '=', company_id)])", text)
        self.assertNotIn("('company_id', 'in', [False, company_id])", text)

    def test_routing_migration_consolidates_known_service_boms_reversibly(self):
        text = (ROOT / 'migrations/18.0.6.1/post-migrate.py').read_text(encoding='utf-8')
        for code in (
            'CC-OPS-AUTO', 'CC-OPS-DEEP', 'CC-OPS-EXT', 'CC-OPS-FULL',
            'CC-OPS-INT', 'CC-OPS-PASTE', 'CC-OPS-POWDER', 'CC-OPS-SALON',
            'CC-OPS-SHINE',
        ):
            self.assertIn(code, text)
        self.assertIn('alternative_workcenter_ids', text)
        self.assertIn("'active': False", text)
        self.assertIn("'A9'", text)
        self.assertIn("'A10'", text)
        self.assertNotIn('.unlink(', text)

    def test_dashboard_payload_exposes_reusable_wash_domain_for_navigation(self):
        production = (ROOT / 'models/mrp_production_extend.py').read_text(encoding='utf-8')
        js = (ROOT / 'static/src/js/dashboard.js').read_text(encoding='utf-8')
        self.assertIn("'wash_order_domain': base_domain", production)
        self.assertIn('wash_order_domain', js)

    def test_reference_vehicle_assets_are_used_for_small_and_large_visuals(self):
        helper = (ROOT / 'static/src/js/vehicle_visuals.js').read_text(encoding='utf-8')
        self.assertIn('vehicle_small.webp', helper)
        self.assertIn('vehicle_large.webp', helper)
        for name in ('queue_panel.js', 'station_card.js', 'station_detail.js'):
            text = (ROOT / 'static/src/js/components' / name).read_text(encoding='utf-8')
            self.assertIn('vehicleImagePath', text)

    def test_detail_drawer_is_docked_not_modal_overlay(self):
        xml = (ROOT / 'static/src/xml/dashboard.xml').read_text(encoding='utf-8')
        css = (ROOT / 'static/src/css/dashboard_concept_replica.css').read_text(encoding='utf-8')
        self.assertNotIn('cw-drawer-backdrop', xml)
        drawer = re.search(r'\.cw-detail-drawer\s*\{(.*?)\}', css, re.S)
        self.assertIsNotNone(drawer)
        self.assertNotRegex(drawer.group(1), r'position\s*:\s*(absolute|fixed)')
        self.assertRegex(drawer.group(1), r'position\s*:\s*sticky')
        self.assertRegex(drawer.group(1), r'overflow-y\s*:\s*auto')
        self.assertIn('.cw-dashboard-app.has-detail', css)


if __name__ == '__main__':
    unittest.main()
