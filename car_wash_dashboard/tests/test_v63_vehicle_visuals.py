import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class V63VehicleVisualContractTest(unittest.TestCase):
    def test_manifest_version_is_v63(self):
        manifest = ast.literal_eval((ROOT / '__manifest__.py').read_text(encoding='utf-8'))
        self.assertEqual(manifest['version'], '18.0.6.3')

    def test_reference_style_small_and_large_assets_exist(self):
        for name in ('vehicle_small.webp', 'vehicle_large.webp'):
            path = ROOT / 'static/src/img' / name
            self.assertTrue(path.exists(), name)
            self.assertGreater(path.stat().st_size, 10_000, name)

    def test_backend_exposes_size_driven_vehicle_visuals(self):
        source = (ROOT / 'models/mrp_production_extend.py').read_text(encoding='utf-8')
        self.assertIn("return 'large'", source)
        self.assertIn("return 'small'", source)
        self.assertIn("'vehicle_visual': self._cw_vehicle_visual", source)

    def test_all_dashboard_vehicle_surfaces_use_shared_photo_selector(self):
        helper = ROOT / 'static/src/js/vehicle_visuals.js'
        self.assertTrue(helper.exists())
        helper_text = helper.read_text(encoding='utf-8')
        self.assertIn('vehicle_small.webp', helper_text)
        self.assertIn('vehicle_large.webp', helper_text)
        self.assertIn('vehicle_size', helper_text)

        for name in ('queue_panel.js', 'station_card.js', 'station_detail.js'):
            text = (ROOT / 'static/src/js/components' / name).read_text(encoding='utf-8')
            self.assertIn('vehicleImagePath', text, name)
            self.assertNotIn('concept_car.webp', text, name)
            self.assertNotIn('car_pickup.svg', text, name)

    def test_manifest_loads_vehicle_visual_helper_before_components(self):
        manifest = ast.literal_eval((ROOT / '__manifest__.py').read_text(encoding='utf-8'))
        assets = manifest['assets']['web.assets_backend']
        helper = 'car_wash_dashboard/static/src/js/vehicle_visuals.js'
        self.assertIn(helper, assets)
        helper_index = assets.index(helper)
        for name in ('kpi_card.js', 'queue_panel.js', 'station_card.js', 'station_detail.js'):
            path = f'car_wash_dashboard/static/src/js/components/{name}'
            self.assertLess(helper_index, assets.index(path))

    def test_css_keeps_photo_vehicles_contained_without_cartoon_distortion(self):
        css = (ROOT / 'static/src/css/dashboard_concept_replica.css').read_text(encoding='utf-8')
        self.assertIn('.cw-station-vehicle img', css)
        self.assertIn('.cw-queue-car img', css)
        self.assertIn('.cw-detail-car img', css)
        self.assertIn('object-fit: contain', css)
        self.assertIn('filter: drop-shadow', css)


if __name__ == '__main__':
    unittest.main()
