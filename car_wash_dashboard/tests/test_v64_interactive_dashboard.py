import ast
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class V64InteractiveDashboardContractTest(unittest.TestCase):
    def test_manifest_version_is_v64(self):
        manifest = ast.literal_eval((ROOT / '__manifest__.py').read_text(encoding='utf-8'))
        self.assertEqual(manifest['version'], '18.0.6.7.2')

    def test_backend_exposes_finished_today_rows_for_interactive_kpi(self):
        source = (ROOT / 'models/mrp_production_extend.py').read_text(encoding='utf-8')
        self.assertIn("'finished_today_items': finished_today_items", source)
        self.assertIn("'finished_today_domain': finished_today_domain", source)
        self.assertIn("'finished_at'", source)

    def test_kpi_card_is_clickable_and_accepts_active_state(self):
        component = (ROOT / 'static/src/js/components/kpi_card.js').read_text(encoding='utf-8')
        xml = (ROOT / 'static/src/xml/dashboard.xml').read_text(encoding='utf-8')
        self.assertIn('onClick', component)
        self.assertIn('active', component)
        self.assertIn('t-on-click="props.onClick"', xml)
        self.assertIn('is-active', xml)

    def test_dashboard_has_context_focus_modes_and_audio_feedback(self):
        js = (ROOT / 'static/src/js/dashboard.js').read_text(encoding='utf-8')
        for token in (
            'focusMode', 'viewMode', 'audioEnabled', 'activateFocus', 'clearFocus',
            'activeStations', 'availableStations', 'finishedTodayItems',
            'toggleViewMode', 'playUiTone', 'showStationDirectory',
        ):
            self.assertIn(token, js)
        self.assertIn('AudioContext', js)

    def test_kpis_and_station_navigation_drive_in_dashboard_views(self):
        xml = (ROOT / 'static/src/xml/dashboard.xml').read_text(encoding='utf-8')
        for mode in ('active', 'waiting', 'available', 'finished'):
            self.assertIn(f"activateFocus('{mode}')", xml)
        self.assertIn('showStationDirectory', xml)
        self.assertIn('state.focusMode', xml)
        self.assertIn('cw-focus-panel', xml)
        self.assertIn('cw-station-directory', xml)


    def test_activate_focus_callback_is_bound_to_dashboard_instance(self):
        js = (ROOT / 'static/src/js/dashboard.js').read_text(encoding='utf-8')
        self.assertIn('this.activateFocus = this.activateFocus.bind(this);', js)

    def test_all_interactive_event_handlers_are_bound_to_dashboard_instance(self):
        js = (ROOT / 'static/src/js/dashboard.js').read_text(encoding='utf-8')
        handlers = (
            'onSearchInput', 'clearFocus', 'showStationDirectory', 'toggleViewMode',
            'toggleAudio', 'showLiveStatus', 'selectStation', 'closeStation',
            'manualRefresh', 'openQueue', 'openCars', 'openServices', 'openCustomers',
            'openReports', 'openProduction', 'openWorkorder', 'openShopFloor',
            'openStationSettings',
        )
        for handler in handlers:
            self.assertIn(
                f'this.{handler} = this.{handler}.bind(this);',
                js,
                msg=f'{handler} must be bound before OWL passes it as an event callback',
            )

    def test_grid_view_toggle_supports_grid_and_list(self):
        xml = (ROOT / 'static/src/xml/dashboard.xml').read_text(encoding='utf-8')
        css = (ROOT / 'static/src/css/dashboard_concept_replica.css').read_text(encoding='utf-8')
        self.assertIn('toggleViewMode', xml)
        self.assertIn("state.viewMode === 'grid'", xml)
        self.assertIn('is-list', xml)
        self.assertRegex(css, r'\.cw-station-grid\.is-list\s*\{')

    def test_interaction_feedback_toast_exists(self):
        js = (ROOT / 'static/src/js/dashboard.js').read_text(encoding='utf-8')
        xml = (ROOT / 'static/src/xml/dashboard.xml').read_text(encoding='utf-8')
        css = (ROOT / 'static/src/css/dashboard_concept_replica.css').read_text(encoding='utf-8')
        self.assertIn('feedbackText', js)
        self.assertIn('cw-feedback-toast', xml)
        self.assertRegex(css, r'\.cw-feedback-toast\s*\{')


if __name__ == '__main__':
    unittest.main()
