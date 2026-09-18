import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class V681CustomerDisplayPolishContractTest(unittest.TestCase):
    def test_manifest_version_is_v681(self):
        manifest = ast.literal_eval((ROOT / '__manifest__.py').read_text(encoding='utf-8'))
        self.assertTrue(manifest['version'].startswith('18.0.6.9'))

    def test_customer_display_carries_the_live_dashboard_theme_class(self):
        xml = (ROOT / 'static/src/xml/dashboard.xml').read_text(encoding='utf-8')
        self.assertIn("'cw-customer-display-page theme-' + state.theme", xml)

    def test_customer_display_has_explicit_light_and_dark_palettes(self):
        css = (ROOT / 'static/src/css/dashboard_concept_replica.css').read_text(encoding='utf-8')
        self.assertIn('.cw-customer-display-page.theme-light {', css)
        self.assertIn('.cw-customer-display-page.theme-dark {', css)
        self.assertIn('--cwl-surface:', css)
        self.assertIn('--cwl-card:', css)

    def test_featured_car_uses_stable_tv_friendly_rendering(self):
        css = (ROOT / 'static/src/css/dashboard_concept_replica.css').read_text(encoding='utf-8')
        self.assertIn('width: min(92%, 520px);', css)
        self.assertIn('max-height: 230px;', css)
        self.assertIn('object-position: center center;', css)
        self.assertIn('animation: none;', css)

    def test_customer_display_typography_is_larger_for_lounge_viewing(self):
        css = (ROOT / 'static/src/css/dashboard_concept_replica.css').read_text(encoding='utf-8')
        for token in (
            '.cw-customer-stage-column > header h3 {',
            'font-size: 18px;',
            '.cw-customer-car-copy strong { font-size: 15px;',
            '.cw-customer-car-copy small { color: var(--cwl-card-muted); font-size: 12px;',
            '.cw-customer-display-page:fullscreen .cw-customer-car-copy strong',
            'font-size: 18px;',
        ):
            self.assertIn(token, css)

    def test_customer_light_mode_recolors_all_customer_surfaces(self):
        css = (ROOT / 'static/src/css/dashboard_concept_replica.css').read_text(encoding='utf-8')
        for token in (
            '.cw-customer-display-page.theme-light .cw-customer-display-header',
            '.cw-customer-display-page.theme-light .cw-customer-featured',
            '.cw-customer-display-page.theme-light .cw-customer-stage-column',
            '.cw-customer-display-page.theme-light .cw-customer-vehicle-card',
            '.cw-customer-display-page.theme-light .cw-customer-display-footer',
        ):
            self.assertIn(token, css)


if __name__ == '__main__':
    unittest.main()
