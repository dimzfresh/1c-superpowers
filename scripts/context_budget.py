#!/usr/bin/env python3
"""Сколько контекста съедает набор: описания (грузятся всегда), тела скиллов и карточки (по требованию).

Токены оцениваются грубо (по символам); точные числа зависят от токенизатора модели.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
CHARS_PER_TOKEN = 2.8  # русский текст с кодом, оценка


def description(text: str) -> str:
    match = re.search(r"description:\s*>\s*\n(.*?)\n---", text, re.S)
    return " ".join(match.group(1).split()) if match else ""


def measure() -> dict:
    rows, cards = [], []
    for skill in sorted(SKILLS.iterdir()):
        md = skill / "SKILL.md"
        if not md.is_file():
            continue
        text = md.read_text(encoding="utf-8")
        body = re.sub(r"\A---.*?\n---\n", "", text, count=1, flags=re.S)
        rows.append({"name": skill.name, "description": len(description(text)), "body": len(body)})
        for extra in sorted(skill.glob("*.md")):
            if extra.name != "SKILL.md":
                cards.append({"name": f"{skill.name}/{extra.name}", "chars": len(extra.read_text(encoding="utf-8"))})
    return {"skills": rows, "cards": cards}


def tokens(chars: int) -> int:
    return round(chars / CHARS_PER_TOKEN)


def main() -> int:
    data = measure()
    always = sum(r["description"] for r in data["skills"])
    print(f"{'скилл':32}{'description':>12}{'тело, симв.':>13}{'≈токенов тела':>15}")
    for r in data["skills"]:
        print(f"{r['name']:32}{r['description']:>12}{r['body']:>13}{tokens(r['body']):>15}")
    print(f"\nГрузится всегда (описания {len(data['skills'])} скиллов): {always} симв., ≈{tokens(always)} токенов")
    print(f"Карточки по требованию: {sum(c['chars'] for c in data['cards'])} симв. в {len(data['cards'])} файлах")
    biggest = sorted(data["skills"], key=lambda r: -r["body"])[:3]
    print("Самые тяжёлые тела:", ", ".join(f"{r['name']} ({r['body']})" for r in biggest))
    return 0


if __name__ == "__main__":
    sys.exit(main())
