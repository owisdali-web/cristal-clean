import ast
import re
import unittest
from pathlib import Path
from lxml import etree

ROOT = Path(__file__).resolve().parents[1]


class V671FullArabicTranslationTest(unittest.TestCase):
    def test_manifest_version_is_v671(self):
        manifest = ast.literal_eval((ROOT / '__manifest__.py').read_text(encoding='utf-8'))
        self.assertTrue(manifest['version'].startswith('18.0.6.9'))

    def test_dashboard_components_expose_translation_helper(self):
        files = (
            'static/src/js/dashboard.js',
            'static/src/js/components/queue_panel.js',
            'static/src/js/components/station_card.js',
            'static/src/js/components/station_detail.js',
        )
        for rel in files:
            source = (ROOT / rel).read_text(encoding='utf-8')
            self.assertIn('translateUi', source, msg=rel)
            self.assertRegex(source, r'\btr\s*\(\s*text\s*,\s*\.\.\.args\s*\)', msg=rel)
            self.assertIn('return translateUi(text, ...args);', source, msg=rel)

    def test_no_visible_english_literals_remain_in_dashboard_template(self):
        path = ROOT / 'static/src/xml/dashboard.xml'
        root = etree.parse(str(path)).getroot()
        offenders = []
        for element in root.iter():
            for value in (element.text, element.tail):
                if not value:
                    continue
                text = ' '.join(value.split())
                if text and re.search(r'[A-Za-z]{2,}', text):
                    offenders.append((element.sourceline, text))
            for attr in ('title', 'placeholder', 'aria-label'):
                value = element.get(attr)
                if value and re.search(r'[A-Za-z]{2,}', value):
                    offenders.append((element.sourceline, f'{attr}={value}'))
        # The English brand name is intentionally language-neutral.
        offenders = [item for item in offenders if item[1] not in ('Crystal Clean',)]
        self.assertEqual(offenders, [], msg=f'Untranslated template literals: {offenders}')

    def test_operational_kpis_and_analytics_click_labels_use_tr(self):
        xml = (ROOT / 'static/src/xml/dashboard.xml').read_text(encoding='utf-8')
        required = (
            "label=\"tr('Total Active Cars')\"",
            "label=\"tr('General Waiting Queue')\"",
            "label=\"tr('Available Stations')\"",
            "label=\"tr('Finished Today')\"",
            "openAnalyticsDetail('today_revenue', false, tr('Today\\'s Revenue'))",
            "openAnalyticsDetail('station_overall', false, tr('Station Utilization'))",
        )
        for token in required:
            self.assertIn(token, xml, msg=token)

    def test_arabic_catalog_contains_remaining_runtime_labels(self):
        po = (ROOT / 'i18n/ar_001.po').read_text(encoding='utf-8')
        required = (
            'View full queue', 'cars waiting for next available station', 'No cars are waiting.',
            'Ready for next car', 'Time in station', 'Current Operation', 'Service Notes',
            'Loading car wash dashboard…', 'Cleaner Cars', 'Brighter Days', 'Today', 'This Month',
            'vs. yesterday', 'vs. last month', 'Cars Washed', 'By Volume', 'Overall', 'Utilization',
            'By Washes', 'Low Stock', 'Live', 'Analytics Drill-down', 'Loading detail…',
            'Station configuration needs attention', 'Configure', 'in stations now', 'cars waiting',
            'of 10 stations', 'completed wash orders', 'No active cars', 'Queue is clear',
            'No available stations', 'No completed washes today', 'Each station handles one car at a time.',
        )
        for label in required:
            self.assertIn(f'msgid "{label}"', po, msg=label)


if __name__ == '__main__':
    unittest.main()
