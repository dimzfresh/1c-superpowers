#!/usr/bin/env python3
"""Прогон evals A/B: одна и та же задача с набором скиллов и без него.

Агент задаётся командой, читающей промпт со stdin и пишущей ответ в stdout:
    EVAL_AGENT_CMD='claude -p' python3 evals/run_eval.py
Сырые ответы сохраняются в evals/transcripts/<id>.<with|without>.txt, проверка — по regex
из evals/negative.json. Никаких «самоотчётов»: PASS ставит только этот скрипт.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ["EVAL_TRANSCRIPTS"]) if os.environ.get("EVAL_TRANSCRIPTS") else ROOT / "evals" / "transcripts"
BUNDLE = [
    "skills/using-1c-superpowers/SKILL.md",
    "skills/1c-review/SKILL.md",
    "skills/1c-review/transactions.md",
    "skills/1c-review/extension.md",
    "skills/1c-review/standards.md",
    "skills/1c-review/exchange.md",
    "skills/1c-review/queries.md",
    "skills/1c-review/gate.md",
    "skills/1c-review/forms.md",
    "skills/1c-review/jobs.md",
    "skills/1c-review/caching.md",
    "skills/1c-review/versions.md",
    "skills/1c-review/secrets.md",
    "skills/1c-performance/SKILL.md",
    "skills/1c-review/facts.md",
    "skills/1c-review/print.md",
    "skills/1c-review/reports.md",
]


def skills_text(files: list[str] | None = None) -> str:
    return "\n\n".join(
        f"=== {rel} ===\n{(ROOT / rel).read_text(encoding='utf-8')}" for rel in (files or BUNDLE)
    )


def build_prompt(case: dict, with_skills: bool, targeted: bool = False) -> str:
    task = case["prompt"]
    if case.get("fixture"):
        code = (ROOT / case["fixture"]).read_text(encoding="utf-8")
        task = f"{task}\n\n```bsl\n{code}\n```"
    if not with_skills:
        return task
    files = case.get("targeted_bundle") if targeted else case.get("bundle")
    # Задача идёт первой: длинный файл при чтении агентом может обрезаться с конца.
    return "=== ЗАДАЧА ===\n" + task + "\n\n=== СКИЛЛЫ (следуй им при выполнении задачи) ===\n\n" + skills_text(files)


NEGATION = re.compile(r"(?i)ложн|нарушением не|не нарушени|не является|не считается|не запрещ|не ставл|не критичн")


def asserted_text(answer: str) -> str:
    """Текст без секции «Не вошло в замечания» и без предложений-отрицаний:
    там ответ как раз объясняет, почему запрета нет."""
    answer = re.split(r"(?im)^#+\s*Не вошло", answer)[0]
    sentences = re.split(r"(?<=[.!?\n])\s+", answer)
    return " ".join(s for s in sentences if not NEGATION.search(s))


def check(case: dict, answer: str) -> list[str]:
    errors = [f"нет {p}" for p in case.get("must_match", []) if not re.search(p, answer)]
    limit = case.get("max_question_marks")
    if limit is not None and answer.count("?") > limit:
        errors.append(f"вопросов {answer.count('?')} > {limit}")
    asserted = asserted_text(answer)
    errors += [f"есть запрещённое {p}" for p in case.get("must_not_match", []) if re.search(p, asserted)]
    return errors


def all_cases() -> list[dict]:
    return json.loads((ROOT / "evals" / "negative.json").read_text(encoding="utf-8"))


def dump(directory: Path, targeted: bool = False) -> None:
    """Сохранить промпты для агента, который не вызывается из shell (например субагент)."""
    directory.mkdir(parents=True, exist_ok=True)
    for case in all_cases():
        for mode in ("without", "with"):
            (directory / f"{case['id']}.{mode}.prompt.txt").write_text(
                build_prompt(case, mode == "with", targeted), encoding="utf-8"
            )


REPS = 3


def transcripts(case_id: str, mode: str) -> list[Path]:
    return sorted(OUT.glob(f"{case_id}.{mode}.*.txt"))


def check_saved() -> int:
    """Оценить сохранённые ответы evals/transcripts/<id>.<mode>.<n>.txt: доля PASS на ячейку."""
    totals = {"with": [0, 0], "without": [0, 0]}
    weak = 0
    for case in all_cases():
        row = []
        for mode in ("without", "with"):
            files = transcripts(case["id"], mode)
            ok = sum(not check(case, f.read_text(encoding="utf-8")) for f in files)
            totals[mode][0] += ok
            totals[mode][1] += len(files)
            row.append(f"{ok}/{len(files)}")
        print(f"{case['id']:32} without {row[0]:5} with {row[1]:5}")
        if row[1].split("/")[0] != row[1].split("/")[1]:
            weak += 1
    for mode, (ok, n) in totals.items():
        print(f"ИТОГО {mode}: {ok}/{n}" + (f" ({100 * ok // n}%)" if n else ""))
    return 1 if weak else 0


def main() -> int:
    if len(sys.argv) == 3 and sys.argv[1] == "--dump":
        dump(Path(sys.argv[2]))
        return 0
    if len(sys.argv) == 3 and sys.argv[1] == "--dump-targeted":
        dump(Path(sys.argv[2]), targeted=True)
        return 0
    if sys.argv[1:] == ["--check"]:
        return check_saved()
    cmd = shlex.split(os.environ.get("EVAL_AGENT_CMD", "claude -p"))
    cases = all_cases()
    OUT.mkdir(exist_ok=True)
    failed = 0
    for case in cases:
        for mode in ("without", "with"):
            prompt = build_prompt(case, mode == "with")
            done = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=600)
            answer = done.stdout
            (OUT / f"{case['id']}.{mode}.1.txt").write_text(answer, encoding="utf-8")
            errors = check(case, answer)
            print(f"{'PASS' if not errors else 'FAIL'}\t{case['id']}\t{mode}\t{'; '.join(errors)}")
            failed += bool(errors) and mode == "with"
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
