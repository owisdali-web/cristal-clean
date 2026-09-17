import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class V691ReportCenterRuntimeHotfixTest(unittest.TestCase):
    def test_manifest_version_is_691(self):
        manifest = ast.literal_eval((ROOT / '__manifest__.py').read_text(encoding='utf-8'))
        self.assertEqual(manifest['version'], '18.0.6.9.1')

    def test_pos_line_search_does_not_order_by_related_field(self):
        source = (ROOT / 'models/report_center.py').read_text(encoding='utf-8')
        self.assertNotIn("order='order_id.date_order asc, id asc'", source)
        self.assertNotIn('order="order_id.date_order asc, id asc"', source)
        self.assertIn("order='id asc'", source)

    def test_pos_lines_are_sorted_in_python_by_order_date_then_id(self):
        source = (ROOT / 'models/report_center.py').read_text(encoding='utf-8')
        self.assertIn('lines = lines.sorted(', source)
        self.assertIn('line.order_id.date_order', source)
        self.assertIn('line.id', source)


if __name__ == '__main__':
    unittest.main()
