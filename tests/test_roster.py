import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_SKILLS = [
    "using-1c-superpowers",
    "1c-brainstorming",
    "1c-writing-plans",
    "1c-executing-plans",
    "1c-tdd",
    "1c-systematic-debugging",
    "1c-performance",
    "1c-verification",
    "1c-review",
    "1c-receiving-review",
    "1c-finish-branch",
    "1c-extension",
    "1c-update",
    "1c-exchange",
    "1c-writing-skills",
    "diagnosing-1c-superpowers",
]


class RosterTests(unittest.TestCase):
    def test_plugin_brand_and_name(self):
        meta = json.loads((ROOT / ".cursor-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["name"], "1c-superpowers")
        self.assertIn("AI супер скила для 1С разработки", meta["displayName"])
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertTrue(readme.startswith("AI супер скила для 1С разработки"))
        install = (ROOT / "scripts" / "install.sh").read_text(encoding="utf-8")
        self.assertIn("/1c-superpowers", install)
        self.assertNotIn("/1c-review\"", install.replace("1c-review-plugin", ""))

    def test_using_router_exists_and_routes(self):
        path = ROOT / "skills" / "using-1c-superpowers" / "SKILL.md"
        self.assertTrue(path.is_file())
        text = path.read_text(encoding="utf-8")
        self.assertIn("до ответа", text.lower())
        self.assertIn("1c-review", text)
        self.assertIn("1c-verification", text)
        scenario = (ROOT / "scenarios" / "routing-phrases.md").read_text(encoding="utf-8")
        # минимум 8 строк вида: фраза → `skill`
        rows = [ln for ln in scenario.splitlines() if "→" in ln and "`" in ln]
        self.assertGreaterEqual(len(rows), 8)

    def test_task3_process_skills_present(self):
        for name in ("1c-verification", "1c-extension", "1c-exchange"):
            self.assertTrue((ROOT / "skills" / name / "SKILL.md").is_file(), name)

    def test_all_required_skills_present(self):
        for name in REQUIRED_SKILLS:
            self.assertTrue((ROOT / "skills" / name / "SKILL.md").is_file(), name)


if __name__ == "__main__":
    unittest.main()
