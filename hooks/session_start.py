#!/usr/bin/env python3
"""SessionStart: подкладывает роутер using-1c-superpowers в контекст (Claude Code)."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
router = (ROOT / "skills" / "using-1c-superpowers" / "SKILL.md").read_text(encoding="utf-8")
body = re.sub(r"\A---.*?\n---\n", "", router, count=1, flags=re.S)
context = (
    "AI супер скила для 1С разработки. Каталог плагина: "
    f"{ROOT}. Скрипт проверки репозитория: skills/1c-verification/scripts/find_checks.py.\n\n"
    "Перед любым ответом по задаче 1С следуй роутеру:\n\n" + body
)
print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": context}}, ensure_ascii=False))
