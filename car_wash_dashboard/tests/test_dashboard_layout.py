from pathlib import Path
import re
import unittest


MODULE_ROOT = Path(__file__).resolve().parents[1]
CSS_PATH = MODULE_ROOT / "static/src/css/dashboard_concept_replica.css"


class DashboardFullscreenCssTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.css = CSS_PATH.read_text(encoding="utf-8")

    def test_dashboard_is_not_capped_to_1440_pixels(self):
        self.assertNotIn("max-width:1440px", self.css.replace(" ", ""))
        self.assertRegex(
            self.css,
            re.compile(r"\.o_car_wash_dashboard\.cc-odoo-shell\s*#crystal-concept\s*\{[^}]*width\s*:\s*100%", re.S),
        )

    def test_odoo_shell_fills_available_client_action_area(self):
        self.assertRegex(
            self.css,
            re.compile(r"\.o_car_wash_dashboard\.cc-odoo-shell\s*\{[^}]*width\s*:\s*100%[^}]*min-height\s*:\s*100%", re.S),
        )

    def test_large_desktop_gets_scaled_dashboard_components(self):
        self.assertIn("@media (min-width: 1600px)", self.css)
        for selector in (
            "#crystal-concept .cc-body",
            "#crystal-concept .cc-heading h1",
            "#crystal-concept .cc-stat-value",
            "#crystal-concept .cc-showroom",
            "#crystal-concept .cc-station-scene",
        ):
            self.assertIn(selector, self.css)

    def test_main_spacing_uses_fluid_scaling(self):
        self.assertIn("clamp(", self.css)


if __name__ == "__main__":
    unittest.main()
