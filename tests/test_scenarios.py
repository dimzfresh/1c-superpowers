from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"


class ScenarioTests(unittest.TestCase):
    def test_verify_extension_exchange_scenarios(self):
        for name, needle in [
            ("verify-gate.md", "синтаксис"),
            ("extension-missing-dump.md", "не хватает факта"),
            ("exchange-http-posting.md", "править"),
            ("bake-http-in-posting.md", "править"),
            ("bake-http-in-posting.md", "http"),
            ("bake-http-in-posting.md", "проведен"),
            ("bake-http-in-posting.md", "shop.example"),
            ("bake-http-in-posting.md", "запрос в цикле"),
            ("plan-no-code-before-ok.md", "без кода"),
            ("plan-no-code-before-ok.md", "пути"),
            ("tdd-no-oracle-stop.md", "нет оракула"),
            ("tdd-no-oracle-stop.md", "стоп"),
            ("debug-hypothesis-from-fact.md", "факт"),
            ("debug-hypothesis-from-fact.md", "гипотез"),
            ("update-vendor-killers.md", "убьёт merge"),
            ("update-vendor-killers.md", "1c-update"),
            ("update-vendor-killers.md", "1c-review"),
            ("update-vendor-killers.md", "полныеправа"),
            ("bake-extension-missing-cfe.md", "не хватает факта"),
            ("bake-extension-missing-cfe.md", "править"),
            ("bake-update-vendor.md", "править"),
            ("bake-update-vendor.md", "продолж"),
            ("bake-transaction-parity-incomplete.md", "не хватает факта"),
            ("bake-transaction-parity-incomplete.md", "парность"),
            ("bake-secret-in-mr.md", "не копировать"),
            ("bake-secret-in-mr.md", "править"),
            ("diagnose-router-silent.md", "using-1c-superpowers"),
            ("diagnose-router-silent.md", "роутер"),
        ]:
            text = (ROOT / "scenarios" / name).read_text(encoding="utf-8")
            self.assertIn(needle, text.lower())


class ProcessSkillTests(unittest.TestCase):
    def test_neighbor_skills_link_cards_and_handoff(self):
        for name, card in [
            ("1c-verification", "gate.md"),
            ("1c-extension", "extension.md"),
            ("1c-exchange", "exchange.md"),
        ]:
            path = SKILLS / name / "SKILL.md"
            self.assertTrue(path.is_file(), name)
            text = path.read_text(encoding="utf-8").lower()
            self.assertIn(card, text)
            self.assertIn("1c-review", text)
            self.assertIn("не хватает факта", text)
            self.assertIn("diff", text)

    def test_tdd_and_debug_skills_core(self):
        tdd = (SKILLS / "1c-tdd" / "SKILL.md").read_text(encoding="utf-8").lower()
        self.assertTrue((SKILLS / "1c-tdd" / "SKILL.md").is_file())
        for needle in (
            "yaxunit",
            "vanessa",
            "нет оракула",
            "стоп",
            "1c-review",
            "можно запускать сценарии",
            "find_checks",
            "ветка",
        ):
            self.assertIn(needle, tdd)
        self.assertIn("ветка yaxunit", tdd)
        self.assertIn("ветка va", tdd)

        debug = (SKILLS / "1c-systematic-debugging" / "SKILL.md").read_text(encoding="utf-8").lower()
        self.assertTrue((SKILLS / "1c-systematic-debugging" / "SKILL.md").is_file())
        for needle in ("симптом", "жр", "гипотез", "наугад", "1c-review"):
            self.assertIn(needle, debug)


if __name__ == "__main__":
    unittest.main()
