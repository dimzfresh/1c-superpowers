#!/usr/bin/env python3
"""Показывает, какие проверки лежат в репозитории. Ничего не запускает и базу не открывает."""

from __future__ import annotations

import os
import sys
from pathlib import Path

READ_ONLY = {
    ".bsl-language-server.json": "BSL Language Server. Анализ файлов, базу не трогает.",
    "Configuration.xml": "Выгрузка конфигурации: есть что читать (это не команда проверки). В базу не грузить.",
    "sonar-project.properties": "Настройки Sonar. Только читать; сам анализ — в CI, не из ревью.",
}

# Vanessa / feature — оракул для 1c-tdd (ветка VA).
TDD_SCENARIOS = {
    "vanessa-automation.json": "Каркас Vanessa Automation. Для TDD: есть оракул, сценарии можно гонять командой проекта.",
    "VAParams.json": "Параметры Vanessa. Для TDD: оракул есть; из ревью базу не обновлять.",
    "vrunner.json": "vanessa-runner без тяжёлого env. Для TDD уточнить команду; из ревью не грузить базу.",
    "yaxunit.json": "Каркас YAxUnit. Для TDD: модульные тесты можно гонять командой проекта.",
    "YAxUnit.json": "Каркас YAxUnit. Для TDD: модульные тесты можно гонять командой проекта.",
}

CI_FILES = {
    ".gitlab-ci.yml": "CI GitLab. Читать, что гоняет pipeline; не запускать локально из ревью.",
    "Jenkinsfile": "CI Jenkins. Читать, что гоняет pipeline; не запускать локально из ревью.",
}
CI_DIRS = {".github/workflows"}
PRUNE = {".git", "node_modules", ".idea", "__pycache__"}

DO_NOT_RUN = {
    "packagedef": "Описание пакета OneScript (opm). Установку и запуск из ревью не выполнять.",
    "vanessa-runner.json": "Может обновлять базу. Из ревью не запускать. Для TDD — только если команда проекта явно без загрузки cf.",
    "env.json": "Окружение запуска 1С. Из ревью не запускать, пока в файле не видно, что это только чтение.",
}


def classify(root: Path) -> list[str]:
    lines: list[str] = []
    seen: set[Path] = set()
    feature_hit = False
    yaxunit_hit = False
    def walk():
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = sorted(d for d in dirnames if d not in PRUNE)
            for fn in sorted(filenames):
                yield Path(dirpath) / fn

    for path in walk():
        if path in seen:
            continue
        name = path.name
        relative = path.relative_to(root).as_posix()
        lower_parts = {p.lower() for p in path.parts}
        if name in READ_ONLY:
            lines.append(f"можно читать файлы\t{relative}\t{READ_ONLY[name]}")
            seen.add(path)
        elif name in TDD_SCENARIOS:
            lines.append(
                f"можно запускать сценарии (TDD)\t{relative}\t{TDD_SCENARIOS[name]}"
            )
            seen.add(path)
        elif name in CI_FILES or (
            path.suffix.lower() in {".yml", ".yaml"}
            and any(path.relative_to(root).as_posix().startswith(d + "/") for d in CI_DIRS)
        ):
            lines.append(
                f"CI объявлен (читать, не запускать)\t{relative}\t"
                + CI_FILES.get(name, "CI GitHub Actions. Читать, что гоняет workflow.")
            )
            seen.add(path)
        elif name in DO_NOT_RUN:
            lines.append(f"не запускать из ревью\t{relative}\t{DO_NOT_RUN[name]}")
            seen.add(path)
        elif path.suffix.lower() == ".feature" and not feature_hit:
            lines.append(
                "можно запускать сценарии (TDD)\t"
                f"{relative}\t"
                "Найдены .feature: Vanessa/оракул в репо есть. TDD — гонять; из ревью — не стартовать базу молча."
            )
            seen.add(path)
            feature_hit = True
        elif (
            not yaxunit_hit
            and path.suffix.lower() == ".bsl"
            and ("yaxunit" in lower_parts or "yaxunit" in name.lower())
        ):
            lines.append(
                "можно запускать сценарии (TDD)\t"
                f"{relative}\t"
                "Найдены тесты YAxUnit (.bsl). TDD — гонять; из ревью базу не поднимать."
            )
            seen.add(path)
            yaxunit_hit = True
        elif (
            not yaxunit_hit
            and path.suffix.lower() == ".bsl"
            and "tests" in lower_parts
            and name.lower().startswith("test")
        ):
            lines.append(
                "можно запускать сценарии (TDD)\t"
                f"{relative}\t"
                "Каталог tests/*.bsl похож на YAxUnit/юнит-тесты. Уточнить фреймворк; для TDD — оракул есть."
            )
            seen.add(path)
            yaxunit_hit = True
        if len(lines) >= 40:
            break
    return lines


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    if not root.is_dir():
        print(f"Каталог не найден: {root}", file=sys.stderr)
        return 2
    lines = classify(root)
    if not lines:
        print("шлагбаум не настроен")
        return 0
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
