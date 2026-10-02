#!/usr/bin/env python3
"""PreToolUse (Bash): не даёт агенту сделать то, что скиллы только просят не делать.

Блокирует:
  * `git push --force` / `-f` / `--force-with-lease` в защищённые ветки (main, master, develop, release/*);
  * запись в защищённую ветку прямым `git push <remote> <local>:<protected>` с force;
  * загрузку конфигурации в базу и запуск предприятия на базе из ревью (DESIGNER /LoadCfg, /UpdateDBCfg, /DumpIB для записи).

Читает JSON события со stdin, отвечает JSON-решением. Вне Bash или при сомнении молчит (разрешает).
"""

from __future__ import annotations

import json
import re
import shlex
import sys

PROTECTED = re.compile(r"^(main|master|develop|release/.*|hotfix/.*)$")
DB_WRITE = re.compile(r"/(LoadCfg|LoadConfigFromFiles|UpdateDBCfg|RestoreIB|ExecuteDeploy)\b", re.IGNORECASE)


def _split(command: str) -> list[list[str]]:
    parts: list[list[str]] = []
    for chunk in re.split(r"&&|\|\||;|\n", command):
        try:
            parts.append(shlex.split(chunk))
        except ValueError:
            parts.append(chunk.split())
    return parts


def reason_to_block(command: str) -> str | None:
    for tokens in _split(command):
        if not tokens:
            continue
        if tokens[0] == "git" and "push" in tokens:
            rest = tokens[tokens.index("push") + 1:]
            forced = any(t in {"-f", "--force", "--force-with-lease"} or t.startswith("--force-with-lease=") for t in rest)
            forced = forced or any(t.startswith("+") or ":+" in t for t in rest if not t.startswith("-"))
            if forced:
                targets = [t for t in rest if not t.startswith("-")]
                refs = []
                for t in targets[1:] if len(targets) > 1 else targets:
                    refs.append(t.split(":")[-1].removeprefix("refs/heads/").removeprefix("+"))
                if not targets or any(PROTECTED.match(r) for r in refs) or len(targets) <= 1:
                    return "force-push в защищённую или неуказанную ветку запрещён набором 1c-superpowers (1c-finish-branch). Нужны verify и review на этом HEAD, а force-push в main, master, develop и release/* не делается без прямой просьбы автора вне агента."
        if DB_WRITE.search(" ".join(tokens)):
            return "загрузка конфигурации в базу и обновление базы запрещены из ревью и verify (1c-verification): рабочую базу набор не трогает."
    return None


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if event.get("tool_name") != "Bash":
        return 0
    command = (event.get("tool_input") or {}).get("command", "")
    reason = reason_to_block(command)
    if reason:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": reason}}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
