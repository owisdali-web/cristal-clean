import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class V6931TranslationPoIntegrityTest(unittest.TestCase):
    def test_manifest_version(self):
        manifest = ast.literal_eval((ROOT / "__manifest__.py").read_text(encoding="utf-8"))
        self.assertEqual(manifest["version"], "18.0.6.9.5")

    def test_every_translation_entry_has_module_comment(self):
        text = (ROOT / "i18n" / "ar_001.po").read_text(encoding="utf-8")
        offenders = []
        for block in text.split("\n\n"):
            if "msgid " not in block or 'msgid ""' in block:
                continue
            if "#. module: car_wash_dashboard" not in block:
                first_msgid = next((line for line in block.splitlines() if line.startswith("msgid ")), "<unknown>")
                offenders.append(first_msgid)
        self.assertEqual(offenders, [], msg=f"Entries missing module comment: {offenders}")

    def test_invalid_custom_extracted_comment_is_removed(self):
        text = (ROOT / "i18n" / "ar_001.po").read_text(encoding="utf-8")
        self.assertNotIn("#. car_wash_dashboard report center interactive/export enhancements", text)

if __name__ == "__main__":
    unittest.main()
