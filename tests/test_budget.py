import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("budget", ROOT / "scripts" / "context_budget.py")
budget = importlib.util.module_from_spec(spec)
spec.loader.exec_module(budget)


class ContextBudgetTests(unittest.TestCase):
    def test_always_loaded_descriptions_are_small(self):
        data = budget.measure()
        total = sum(r["description"] for r in data["skills"])
        self.assertLessEqual(total, 4000, f"описания съедают {total} символов контекста постоянно")
        for r in data["skills"]:
            self.assertLessEqual(r["description"], 600, r["name"])
            self.assertGreater(r["description"], 40, r["name"])

    def test_skill_bodies_do_not_balloon(self):
        for r in budget.measure()["skills"]:
            self.assertLessEqual(r["body"], 12000, f"{r['name']}: тело {r['body']} символов, вынести в карточки")


if __name__ == "__main__":
    unittest.main()
