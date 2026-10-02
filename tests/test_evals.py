"""Evals: манифесты, фикстуры и корректность проверок. Прогоны моделей лежат в evals/transcripts*/."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "evals" / "cases.json"
RUNS = ROOT / "evals" / "archive" / "manual-runs"


def load_cases() -> list[dict]:
    return json.loads(CASES.read_text(encoding="utf-8"))


class EvalCasesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cases = load_cases()

    def test_manifest_has_core_and_secret(self):
        ids = {c["id"] for c in self.cases}
        required = {
            "http-in-posting",
            "false-query-in-loop",
            "cfe-missing-second-dump",
            "update-vendor-vmesto",
            "transaction-parity-incomplete",
            "secret-in-mr",
        }
        self.assertTrue(required.issubset(ids), f"нет кейсов: {required - ids}")
        self.assertGreaterEqual(len(self.cases), 6)

    def test_each_case_has_scenario_and_expectations(self):
        for case in self.cases:
            with self.subTest(case=case["id"]):
                scenario = ROOT / case["scenario"]
                self.assertTrue(scenario.is_file(), case["scenario"])
                text = scenario.read_text(encoding="utf-8").lower()
                for needle in case.get("must_mention") or []:
                    self.assertIn(needle.lower(), text, f"{case['id']}: scenario без «{needle}»")
                for banned in case.get("must_not_mention") or []:
                    if banned.lower() in text:
                        self.assertTrue(
                            any(
                                marker in text
                                for marker in (
                                    "не ставить",
                                    f"не «{banned.lower()}",
                                    f'не "{banned.lower()}',
                                    "ложн",
                                    "запрещён",
                                    "запрещен",
                                )
                            )
                            or f"не {banned.lower()}" in text
                            or "не доказан" in text,
                            f"{case['id']}: «{banned}» без маркера отказа",
                        )
                for cls in case.get("expected_classes") or []:
                    self.assertIn(cls.lower(), text, f"{case['id']}: нет класса «{cls}»")
                verdict = case.get("expected_verdict")
                if verdict:
                    self.assertIn(verdict.lower(), text, f"{case['id']}: нет вердикта «{verdict}»")

    def test_fixtures_exist_when_declared(self):
        for case in self.cases:
            rel = case.get("fixture")
            if not rel:
                continue
            path = (ROOT / rel).resolve()
            self.assertTrue(path.is_file(), f"{case['id']}: нет fixture {rel} → {path}")

    def test_http_fixture_contains_http_and_loop_pattern(self):
        path = (
            ROOT / "tests/fixture-http-posting/Documents/ЗаказКлиента/Ext/ObjectModule.bsl"
        ).resolve()
        self.assertTrue(path.is_file(), path)
        body = path.read_text(encoding="utf-8")
        self.assertIn("HTTPСоединение", body)
        self.assertIn("ОбработкаПроведения", body)
        self.assertIn("Выполнить().Выгрузить()", body)
        self.assertIn("Остаток = Новый Запрос", body)

    def test_update_fixture_vmesto_without_continue(self):
        path = ROOT / "tests" / "fixture-update" / "Ext" / "ObjectModule.bsl"
        body = path.read_text(encoding="utf-8")
        self.assertIn("&Вместо", body)
        self.assertNotIn("ПродолжитьВызов", body)

    def test_incomplete_parity_fixture(self):
        path = ROOT / "tests" / "fixture-transactions" / "incomplete-parity.bsl"
        body = path.read_text(encoding="utf-8")
        self.assertIn("НачатьТранзакцию", body)
        self.assertNotIn("ЗафиксироватьТранзакцию", body)
        self.assertNotIn("ОтменитьТранзакцию", body)

    def test_secret_fixture_has_literal_but_run_redacts(self):
        fixture = ROOT / "tests" / "fixture-secrets" / "FormModule.bsl"
        body = fixture.read_text(encoding="utf-8")
        self.assertIn("УЧЕБНЫЙ_ЛИТЕРАЛ_ПАРОЛЯ", body)
        run = (RUNS / "secret-in-mr.md").read_text(encoding="utf-8")
        self.assertNotIn("УЧЕБНЫЙ_ЛИТЕРАЛ_ПАРОЛЯ", run)
        self.assertIn("править", run.lower())
        secrets = (ROOT / "skills" / "1c-review" / "secrets.md").read_text(encoding="utf-8")
        self.assertIn("комментарий MR", secrets)
        self.assertIn("не копировать", secrets.lower())


class DiagnoseAndTddExtraTests(unittest.TestCase):
    def test_diagnose_router_silent_transcript(self):
        path = ROOT / "scenarios" / "diagnose-router-silent.md"
        text = path.read_text(encoding="utf-8").lower()
        self.assertIn("using-1c-superpowers", text)
        self.assertIn("роутер", text)
        self.assertIn("1c-review", text)
        diag = (ROOT / "skills" / "diagnosing-1c-superpowers" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("diagnose-router-silent.md", diag)

    def test_tdd_has_yaxunit_branch(self):
        tdd = (ROOT / "skills" / "1c-tdd" / "SKILL.md").read_text(encoding="utf-8").lower()
        self.assertIn("yaxunit", tdd)
        self.assertIn("ветка yaxunit", tdd)
        self.assertIn("ветка va", tdd)


if __name__ == "__main__":
    unittest.main()


class NegativeEvalManifestTests(unittest.TestCase):
    def test_negative_manifest_is_runnable(self):
        import re

        cases = json.loads((ROOT / "evals" / "negative.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(cases), 5)
        for case in cases:
            with self.subTest(case=case["id"]):
                if case.get("fixture"):
                    self.assertTrue((ROOT / case["fixture"]).is_file())
                for rel in case.get("bundle", []):
                    self.assertTrue((ROOT / rel).is_file(), rel)
                self.assertTrue(case["must_match"] or case["must_not_match"])
                for pattern in case["must_match"] + case["must_not_match"]:
                    re.compile(pattern)

    def test_runner_checks_regexes(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location("run_eval", ROOT / "evals" / "run_eval.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        case = {"must_match": ["править"], "must_not_match": ["запрещ"]}
        self.assertEqual(module.check(case, "Вердикт: править"), [])
        self.assertEqual(len(module.check(case, "всё запрещено")), 2)


class MirrorTests(unittest.TestCase):
    def test_workspace_mirror_in_sync(self):
        mirror = ROOT.parent / ".cursor" / "skills"
        if not mirror.is_dir():
            self.skipTest("зеркала нет")
        for src in (ROOT / "skills").rglob("*.md"):
            twin = mirror / src.relative_to(ROOT / "skills")
            self.assertTrue(twin.is_file(), f"нет в зеркале: {twin}")
            self.assertEqual(src.read_text(encoding="utf-8"), twin.read_text(encoding="utf-8"), f"дрейф: {twin}")


class NegationCheckTests(unittest.TestCase):
    def test_denial_sentences_are_not_findings(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location("run_eval", ROOT / "evals" / "run_eval.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        case = {"must_match": [], "must_not_match": ["(?i)явн\\w+ запис\\w+[^.\\n]{0,40}запрещ"]}
        self.assertEqual(module.check(case, "Замечание «явная запись запрещена» было бы ложным."), [])
        self.assertEqual(len(module.check(case, "Явная запись запрещена в проведении.")), 1)
        self.assertEqual(module.check(case, "### Не вошло в замечания\nЯвная запись запрещена — ложный запрет."), [])


class QuestionLimitTests(unittest.TestCase):
    def test_question_limit(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location("run_eval", ROOT / "evals" / "run_eval.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        case = {"must_match": [], "must_not_match": [], "max_question_marks": 2}
        self.assertEqual(module.check(case, "Один вопрос?"), [])
        self.assertEqual(len(module.check(case, "Раз? Два? Три?")), 1)


class FactsEvalManifestTests(unittest.TestCase):
    def test_facts_manifest(self):
        import re

        cases = json.loads((ROOT / "evals" / "facts.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(cases), 6)
        for case in cases:
            with self.subTest(case=case["id"]):
                self.assertTrue((ROOT / case["fixture"]).is_file())
                self.assertTrue(case["facts"].strip())
                for key in ("with_facts", "no_facts"):
                    for pattern in case[key]["must_match"] + case[key]["must_not_match"]:
                        re.compile(pattern)
