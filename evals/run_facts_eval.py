#!/usr/bin/env python3
"""Eval «с выгрузкой и без»: что добавляют факты о конфигурации (из выгрузки или готового MCP).

Режимы: skills_facts, skills_nofacts, base_facts, base_nofacts.
  python3 evals/run_facts_eval.py --dump <каталог>   # промпты для агента
  python3 evals/run_facts_eval.py --check            # оценка evals/transcripts_facts/<id>.<mode>.<n>.txt
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evals" / "transcripts_facts"
MODES = ("base_nofacts", "base_facts", "skills_nofacts", "skills_facts")

_spec = importlib.util.spec_from_file_location("run_eval", ROOT / "evals" / "run_eval.py")
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)


def cases() -> list[dict]:
    return json.loads((ROOT / "evals" / "facts.json").read_text(encoding="utf-8"))


def build_prompt(case: dict, mode: str) -> str:
    code = (ROOT / case["fixture"]).read_text(encoding="utf-8")
    task = case["prompt"]
    if mode.endswith("_facts"):
        task += "\n\nДанные конфигурации (из выгрузки или ответ любого MCP метаданных):\n```\n" + case["facts"] + "\n```"
    task += f"\n\n```bsl\n{code}\n```"
    if mode.startswith("skills"):
        return "Следуй этим скиллам:\n\n" + base.skills_text() + "\n\n=== ЗАДАЧА ===\n" + task
    return task


def expectation(case: dict, mode: str) -> dict:
    return case["with_facts"] if mode.endswith("_facts") else case["no_facts"]


def dump(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for case in cases():
        for mode in MODES:
            (directory / f"{case['id']}.{mode}.prompt.txt").write_text(build_prompt(case, mode), encoding="utf-8")


def check_saved() -> int:
    totals = {m: [0, 0] for m in MODES}
    print(f"{'кейс':16}" + "".join(f"{m:16}" for m in MODES))
    for case in cases():
        row = []
        for mode in MODES:
            files = sorted(OUT.glob(f"{case['id']}.{mode}.*.txt"))
            ok = sum(not base.check(expectation(case, mode), f.read_text(encoding="utf-8")) for f in files)
            totals[mode][0] += ok
            totals[mode][1] += len(files)
            row.append(f"{ok}/{len(files)}")
        print(f"{case['id']:16}" + "".join(f"{x:16}" for x in row))
    for mode, (ok, n) in totals.items():
        print(f"ИТОГО {mode}: {ok}/{n}" + (f" ({100 * ok // n}%)" if n else ""))
    return 0


def verdicts() -> None:
    """Вердикты (править / сдать с оговоркой / можно сдавать) и «не хватает факта» по ячейкам."""
    import collections
    import re

    print(f"{'кейс':16}{'режим':16}вердикты")
    for case in cases():
        for mode in MODES:
            counter: collections.Counter = collections.Counter()
            for path in sorted(OUT.glob(f"{case['id']}.{mode}.*.txt")):
                text = path.read_text(encoding="utf-8")
                found = re.search(r"(?im)\*{0,2}Вердикт:?\*{0,2}:?\s*\**\s*(править|сдать с оговоркой|можно сдавать)", text)
                counter[found.group(1) if found else "без вердикта"] += 1
                if re.search(r"(?i)не хватает факта", text):
                    counter["«не хватает факта»"] += 1
            if counter:
                print(f"{case['id']:16}{mode:16}{dict(counter)}")


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--dump":
        dump(Path(sys.argv[2]))
    elif sys.argv[1:] == ["--verdicts"]:
        verdicts()
    elif sys.argv[1:] == ["--check"]:
        sys.exit(check_saved())
    else:
        print(__doc__)
