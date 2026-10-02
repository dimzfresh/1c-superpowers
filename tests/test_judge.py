import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("judge", ROOT / "evals" / "judge.py")
judge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(judge)


class JudgeTests(unittest.TestCase):
    def test_truth_covers_every_case(self):
        cases = set(judge.load_cases())
        truth = judge.load_truth()
        self.assertEqual(cases, set(truth))
        for item in truth.values():
            self.assertIn(item["kind"], {"defect", "legit", "need_fact", "process"})
            self.assertGreater(len(item["truth"]), 30)

    def test_blind_dump_hides_mode_and_unblinds_scores(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            tr = tmp / "tr"
            tr.mkdir()
            for cid in judge.load_truth():
                (tr / f"{cid}.without.1.txt").write_text("ответ без", encoding="utf-8")
                (tr / f"{cid}.with.1.txt").write_text("ответ со", encoding="utf-8")
            out = tmp / "p"
            judge.dump(out, tr, 1, 7)
            key = json.loads((out / "key.json").read_text(encoding="utf-8"))
            self.assertEqual(len(key), len(judge.load_truth()))
            sample = next(iter(key))
            prompt = (out / f"{sample}.judge.prompt.txt").read_text(encoding="utf-8")
            self.assertNotIn("со скиллами", prompt.split("=== ЗАДАЧА ===")[1])
            self.assertEqual({v for v in key[sample].values()}, {"with", "without"})
            res = tmp / "r"
            res.mkdir()
            for cid, m in key.items():
                with_side = "A" if m["A"] == "with" else "B"
                other = "B" if with_side == "A" else "A"
                (res / f"{cid}.judge.json").write_text(json.dumps({with_side: {"correct": 1, "false_claims": 0}, other: {"correct": 0, "false_claims": 2}, "winner": with_side}), encoding="utf-8")
            r = judge.score(res, out)
            n = len(key)
            self.assertEqual(r["agg"]["with"]["correct"], n)
            self.assertEqual(r["agg"]["without"]["false_claims"], 2 * n)
            self.assertEqual(r["agg"]["with"]["wins"], n)
            self.assertEqual(r["missing"], [])

    def test_seed_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            tr = tmp / "tr"; tr.mkdir()
            for cid in judge.load_truth():
                (tr / f"{cid}.without.1.txt").write_text("x", encoding="utf-8")
                (tr / f"{cid}.with.1.txt").write_text("y", encoding="utf-8")
            judge.dump(tmp / "a", tr, 1, 3); judge.dump(tmp / "b", tr, 1, 3)
            self.assertEqual((tmp / "a" / "key.json").read_text(), (tmp / "b" / "key.json").read_text())


if __name__ == "__main__":
    unittest.main()


class SingleModeTests(unittest.TestCase):
    def test_single_dump_and_score(self):
        import os
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            tr = tmp / "tr"; tr.mkdir()
            truth = judge.load_truth()
            for cid in truth:
                (tr / f"{cid}.with.1.txt").write_text("ответ", encoding="utf-8")
            out = tmp / "p"
            judge.dump_single(out, tr, "with", 1)
            files = list(out.glob("*.single.prompt.txt"))
            self.assertEqual(len(files), len(truth))
            res = tmp / "r"; res.mkdir()
            for cid in truth:
                (res / f"{cid}.with.single.json").write_text(json.dumps({"correct": 1, "false_claims": 2}), encoding="utf-8")
            r = judge.score_single(res, "with")
            self.assertEqual(r["total"]["correct"], len(truth))
            self.assertEqual(r["total"]["false_claims"], 2 * len(truth))
