#!/usr/bin/env python3
"""Слепая оценка судьёй: пары ответов «без скиллов» и «со скиллами» в случайном порядке.

  python3 evals/judge.py --dump <каталог_промптов> [--transcripts evals/transcripts] [--rep 1] [--seed 7]
  python3 evals/judge.py --score <каталог_ответов_судьи> <каталог_промптов>

Судья получает задачу, эталон правильного ответа (evals/judge_truth.json) и два ответа A и B,
не зная, какой из них со скиллами. Порядок задаётся seed и хранится в key.json (судье не показывается).
Судья пишет JSON: {"A": {"correct": 0|1, "false_claims": n}, "B": {...}, "winner": "A"|"B"|"tie", "reason": "..."}.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RUBRIC = """Ты независимый оценщик ревью кода 1С. Ниже задача, эталон правильного ответа и два ответа, A и B.
Ты не знаешь, как получены ответы. Оцени каждый ответ только по эталону и по коду, не по длине и стилю.

Для каждого ответа поставь:
- "correct": 1, если главный вывод ответа совпадает с эталоном (дефект найден или законный приём не назван нарушением или процессная просьба выполнена как в эталоне), иначе 0;
- "false_claims": число утверждений, поданных как проблема или как факт, которые эталон считает законными или которые не следуют из присланного кода (например утверждения о режиме блокировок или версии платформы, которых в задаче нет). Приём, названный в ответе законным, ложным утверждением не считается.
Затем "winner": "A", "B" или "tie" (кто лучше по correct, затем по меньшему числу false_claims) и "reason" одной фразой.

Верни только JSON, без пояснений вне JSON."""


import os


def load_truth() -> dict:
    path = os.environ.get("JUDGE_TRUTH")
    return json.loads((Path(path) if path else ROOT / "evals" / "judge_truth.json").read_text(encoding="utf-8"))


def load_cases() -> dict:
    path = os.environ.get("EVAL_MANIFEST")
    return {c["id"]: c for c in json.loads((Path(path) if path else ROOT / "evals" / "negative.json").read_text(encoding="utf-8"))}


def task_text(case: dict) -> str:
    text = case["prompt"]
    if case.get("fixture"):
        text += "\n\n```bsl\n" + (ROOT / case["fixture"]).read_text(encoding="utf-8") + "\n```"
    return text


def dump(out: Path, transcripts: Path, rep: int, seed: int) -> None:
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    truth, cases, key = load_truth(), load_cases(), {}
    for cid in sorted(truth):
        wo = transcripts / f"{cid}.without.{rep}.txt"
        wi = transcripts / f"{cid}.with.{rep}.txt"
        if not (wo.is_file() and wi.is_file()):
            continue
        pair = [("without", wo.read_text(encoding="utf-8")), ("with", wi.read_text(encoding="utf-8"))]
        rng.shuffle(pair)
        key[cid] = {"A": pair[0][0], "B": pair[1][0]}
        prompt = (
            f"{RUBRIC}\n\n=== ЗАДАЧА ===\n{task_text(cases[cid])}\n\n=== ЭТАЛОН ===\n{truth[cid]['truth']}\n\n"
            f"=== ОТВЕТ A ===\n{pair[0][1]}\n\n=== ОТВЕТ B ===\n{pair[1][1]}\n"
        )
        (out / f"{cid}.judge.prompt.txt").write_text(prompt, encoding="utf-8")
    (out / "key.json").write_text(json.dumps(key, ensure_ascii=False, indent=2), encoding="utf-8")


def parse(path: Path) -> dict | None:
    text = path.read_text(encoding="utf-8")
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < 0:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None


def score(results: Path, prompts: Path) -> dict:
    key = json.loads((prompts / "key.json").read_text(encoding="utf-8"))
    truth = load_truth()
    agg = {m: {"correct": 0, "false_claims": 0, "n": 0, "wins": 0} for m in ("with", "without")}
    ties, missing, bykind = 0, [], {}
    for cid, mapping in key.items():
        path = results / f"{cid}.judge.json"
        data = parse(path) if path.is_file() else None
        if not data or "A" not in data or "B" not in data:
            missing.append(cid)
            continue
        for side in ("A", "B"):
            mode = mapping[side]
            agg[mode]["correct"] += int(data[side].get("correct", 0))
            agg[mode]["false_claims"] += int(data[side].get("false_claims", 0))
            agg[mode]["n"] += 1
            k = bykind.setdefault(truth[cid]["kind"], {"with": [0, 0], "without": [0, 0]})
            k[mode][0] += int(data[side].get("correct", 0))
            k[mode][1] += 1
        winner = data.get("winner")
        if winner in ("A", "B"):
            agg[mapping[winner]]["wins"] += 1
        else:
            ties += 1
    return {"agg": agg, "ties": ties, "missing": missing, "by_kind": bykind}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump")
    ap.add_argument("--score", nargs=2)
    ap.add_argument("--transcripts", default=str(ROOT / "evals" / "transcripts"))
    ap.add_argument("--rep", type=int, default=1)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    if args.dump:
        dump(Path(args.dump), Path(args.transcripts), args.rep, args.seed)
        return 0
    if args.score:
        r = score(Path(args.score[0]), Path(args.score[1]))
        for mode in ("without", "with"):
            a = r["agg"][mode]
            print(f"{mode:8} верных {a['correct']}/{a['n']}  ложных утверждений {a['false_claims']}  побед {a['wins']}")
        print(f"ничьих {r['ties']}, нет оценки: {len(r['missing'])} {r['missing']}")
        for kind, v in sorted(r["by_kind"].items()):
            print(f"  {kind:10} без скиллов {v['without'][0]}/{v['without'][1]}   со скиллами {v['with'][0]}/{v['with'][1]}")
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
