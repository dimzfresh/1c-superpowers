import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
REQUIRED = ("Когда ставить:", "Не ставить:", "Как доказать:", "Тяжесть:")


def description(name):
    text = (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")
    start = text.index("description:")
    return text[start : text.index("\n---", start)]


def rules():
    found = []
    for path in SKILLS.rglob("*.md"):
        text = re.sub(r"```.*?```", "", path.read_text(encoding="utf-8"), flags=re.DOTALL)
        for chunk in text.split("\n### ")[1:]:
            title = chunk.splitlines()[0].strip()
            found.append((path.relative_to(ROOT).as_posix(), title, chunk))
    return found


class CardTests(unittest.TestCase):
    def test_every_rule_has_an_exception(self):
        cards = rules()
        self.assertGreaterEqual(len(cards), 20)
        missing = []
        for path, title, body in cards:
            for marker in REQUIRED:
                if marker not in body:
                    missing.append(f"{path} / {title}: нет «{marker}»")
        self.assertEqual(missing, [])

    def test_verdict_and_scope(self):
        review = (SKILLS / "1c-review" / "SKILL.md").read_text(encoding="utf-8")
        gate = (SKILLS / "1c-review" / "gate.md").read_text(encoding="utf-8")
        self.assertIn("## Процесс", review)
        self.assertIn("## Чеклисты", review)
        self.assertIn("Процедуру целиком не переписывать", review)
        self.assertIn("[repo.md](repo.md)", review)
        repo = (SKILLS / "1c-review" / "repo.md").read_text(encoding="utf-8")
        self.assertIn("<!-- 1c-review -->", repo)
        self.assertIn("REQUEST_CHANGES", repo)
        self.assertIn("публикацию не принимает", repo)
        install = (ROOT / "scripts" / "install.sh").read_text(encoding="utf-8")
        self.assertIn(".cursor/plugins/local}/1c-superpowers", install)
        self.assertNotIn("ONEC_DUMP=", install)
        self.assertIn("## Область ревью", review)
        self.assertIn("изменённые процедуры", review)
        self.assertNotIn("«критично» или «важно»", review)
        self.assertIn("шаблону ограничения", review)
        self.assertIn("какие контуры смотрелись", review)
        self.assertIn("## Прикладное решение", review)
        self.assertIn("Предмет — изменённые файлы", review)
        extension = (SKILLS / "1c-review" / "extension.md").read_text(encoding="utf-8")
        objects = (SKILLS / "1c-review" / "objects.md").read_text(encoding="utf-8")
        self.assertIn("права на новый объект в diff не видны", objects)
        self.assertIn("std 683", objects)
        secrets = (SKILLS / "1c-review" / "secrets.md").read_text(encoding="utf-8")
        queries = (SKILLS / "1c-review" / "queries.md").read_text(encoding="utf-8")
        transactions = (SKILLS / "1c-review" / "transactions.md").read_text(encoding="utf-8")
        self.assertIn("в сводку и в публикацию не копировать", secrets)
        self.assertIn("Разыменование через точку", queries)
        self.assertIn("ФоновыеЗадания.Выполнить", transactions)
        self.assertIn("по имени и синониму", objects.lower())
        self.assertIn("Одного пути мало", extension)
        self.assertIn("не хватает факта", extension.lower())
        self.assertNotIn("ЗаказКлиента", review)
        handoff = (SKILLS / "1c-review" / "handoff.md").read_text(encoding="utf-8")
        versions = (SKILLS / "1c-review" / "versions.md").read_text(encoding="utf-8")
        self.assertNotIn("зарплат", handoff.lower())
        self.assertNotIn("типовой ERP", versions)
        self.assertIn("какие контуры смотрелись", gate)
        self.assertNotIn("явно названы законными случаями", gate)

    def test_one_summary_door(self):
        review = description("1c-review")
        flat = " ".join(review.lower().split())
        self.assertIn("единственный скилл, который пишет сводку", flat)
        self.assertIn("перед сдачей расширения", flat)
        self.assertIn("перед обновлением поставщика", flat)
        self.assertIn("подписка", flat)
        for word in ("проверк", "ревью", "модул", "запрос", "проведен", "обмен", "расширен", "проверено"):
            self.assertIn(word, flat)
        skill_paths = {path.relative_to(SKILLS).as_posix() for path in SKILLS.rglob("SKILL.md")}
        self.assertIn("1c-review/SKILL.md", skill_paths)
        self.assertIn("using-1c-superpowers/SKILL.md", skill_paths)
        for neighbor in ("1c-verification", "1c-extension", "1c-exchange"):
            self.assertIn(f"{neighbor}/SKILL.md", skill_paths)
        for path in SKILLS.rglob("SKILL.md"):
            name = path.parent.name
            desc_flat = " ".join(description(name).lower().split())
            if name == "1c-review":
                self.assertIn("пишет сводку", desc_flat)
            else:
                self.assertNotIn("пишет сводку", desc_flat)
        for neighbor in ("1c-verification", "1c-extension", "1c-exchange"):
            body = (SKILLS / neighbor / "SKILL.md").read_text(encoding="utf-8").lower()
            self.assertNotIn("пишет сводку", body)
            self.assertIn("1c-review", body)

    def test_no_absolute_ban(self):
        banned = ("всегда запрещ", "категорически нельзя", "запрещено всегда")
        hits = []
        for path in SKILLS.rglob("*.md"):
            lowered = path.read_text(encoding="utf-8").lower()
            for phrase in banned:
                if phrase in lowered:
                    hits.append(f"{path.name}: {phrase}")
        self.assertEqual(hits, [])


class GateScriptTests(unittest.TestCase):
    def test_classifies_without_running(self):
        fixture = ROOT / "tests" / "fixture-repo"
        completed = subprocess.run(
            ["python3", str(ROOT / "skills" / "1c-verification" / "scripts" / "find_checks.py"), str(fixture)],
            check=True,
            capture_output=True,
            text=True,
        )
        output = completed.stdout
        self.assertIn("можно читать файлы", output)
        self.assertIn("Configuration.xml", output)
        self.assertIn("не запускать из ревью", output)
        self.assertIn("packagedef", output)
        self.assertNotIn("Запустить", output)

    def test_detects_vanessa_features_for_tdd(self):
        fixture = ROOT / "tests" / "fixture-tdd-va"
        completed = subprocess.run(
            ["python3", str(ROOT / "skills" / "1c-verification" / "scripts" / "find_checks.py"), str(fixture)],
            check=True,
            capture_output=True,
            text=True,
        )
        output = completed.stdout
        self.assertIn("можно запускать сценарии (TDD)", output)
        self.assertIn(".feature", output)

    def test_detects_yaxunit_for_tdd(self):
        fixture = ROOT / "tests" / "fixture-tdd-yaxunit"
        completed = subprocess.run(
            ["python3", str(ROOT / "skills" / "1c-verification" / "scripts" / "find_checks.py"), str(fixture)],
            check=True,
            capture_output=True,
            text=True,
        )
        output = completed.stdout
        self.assertIn("можно запускать сценарии (TDD)", output)
        self.assertTrue(
            "yaxunit" in output.lower() or "Test_Smoke.bsl" in output,
            output,
        )


class TransactionsCardTests(unittest.TestCase):
    def test_parity_requires_complete_fragment(self):
        text = (SKILLS / "1c-review" / "transactions.md").read_text(encoding="utf-8")
        self.assertIn("неполному фрагменту", text.lower())
        self.assertIn("не хватает факта", text.lower())
        self.assertIn("оба конца парности доказаны", text.lower())


if __name__ == "__main__":
    unittest.main()
