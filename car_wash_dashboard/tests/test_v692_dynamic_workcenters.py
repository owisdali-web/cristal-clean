import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class V692DynamicWorkCentersContractTest(unittest.TestCase):
    def test_manifest_version_is_v692(self):
        manifest = ast.literal_eval((ROOT / '__manifest__.py').read_text(encoding='utf-8'))
        self.assertEqual(manifest['version'], '18.0.6.9.2')

    def test_dashboard_backend_returns_only_real_enabled_active_stations(self):
        source = (ROOT / 'models/mrp_production_extend.py').read_text(encoding='utf-8')
        self.assertIn("('car_wash_enabled', '=', True)", source)
        self.assertNotIn('build_station_slots(real_station_payloads, target=10)', source)
        self.assertNotIn("warnings.append('The dashboard expects 10 real car-wash stations.')", source)
        self.assertNotIn("warnings.append(_('Configure eight General stations.'))", source)
        self.assertIn("'target_station_count': len(real_station_payloads)", source)

    def test_dashboard_station_payload_is_numbered_from_real_records_only(self):
        source = (ROOT / 'models/mrp_production_extend.py').read_text(encoding='utf-8')
        self.assertIn('for slot_number, station in enumerate(real_station_payloads, start=1):', source)
        self.assertIn("station['slot_number'] = slot_number", source)
        self.assertNotIn("'is_placeholder': True", source)

    def test_dashboard_uses_dynamic_station_count_in_heading_and_kpi(self):
        xml = (ROOT / 'static/src/xml/dashboard.xml').read_text(encoding='utf-8')
        js = (ROOT / 'static/src/js/dashboard.js').read_text(encoding='utf-8')
        self.assertNotIn("tr('Work Centers (10)')", xml)
        self.assertNotIn("tr('of 10 stations')", xml)
        self.assertIn('workCentersTitle', xml)
        self.assertIn('stationCapacityLabel', xml)
        self.assertIn('get workCentersTitle()', js)
        self.assertIn('get stationCapacityLabel()', js)

    def test_station_grid_adapts_to_real_station_count(self):
        xml = (ROOT / 'static/src/xml/dashboard.xml').read_text(encoding='utf-8')
        js = (ROOT / 'static/src/js/dashboard.js').read_text(encoding='utf-8')
        css = (ROOT / 'static/src/css/dashboard_concept_replica.css').read_text(encoding='utf-8')
        self.assertIn('stationGridClass', xml)
        self.assertIn('get stationGridClass()', js)
        for token in (
            '.cw-station-grid.station-count-1',
            '.cw-station-grid.station-count-2',
            '.cw-station-grid.station-count-3',
            '.cw-station-grid.station-count-4',
            '.cw-station-grid.station-count-5',
            '.cw-station-grid.station-count-6',
            '.cw-station-grid.station-count-many',
        ):
            self.assertIn(token, css)


if __name__ == '__main__':
    unittest.main()
