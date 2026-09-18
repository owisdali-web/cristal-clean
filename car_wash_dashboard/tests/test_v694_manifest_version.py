import ast
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class V694ManifestVersionTest(unittest.TestCase):
    def test_odoo18_manifest_version_is_valid(self):
        manifest = ast.literal_eval((ROOT / "__manifest__.py").read_text(encoding="utf-8"))
        version = manifest["version"]
        self.assertRegex(version, r"^18\.0\.\d+\.\d+(?:\.\d+)?$")
        self.assertLessEqual(len(version.split(".")), 5)

if __name__ == "__main__":
    unittest.main()
