#!/bin/sh
# Ставит скиллы локально для Cursor (симлинк в plugins/local).
# Сами SKILL.md работают в любом агенте, который их читает.
# Репозиторный MCP и выгрузку не настраивает.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
DEST="${CURSOR_PLUGINS_LOCAL:-$HOME/.cursor/plugins/local}/1c-superpowers"
mkdir -p "$(dirname "$DEST")"
if [ -L "$DEST" ]; then
  echo "уже стоит: $DEST -> $(readlink "$DEST")"
  exit 0
fi
if [ -e "$DEST" ]; then
  echo "по пути $DEST уже есть каталог, ссылку не затираю" >&2
  exit 1
fi
ln -s "$ROOT" "$DEST"
echo "поставлено: $DEST -> $ROOT"
echo "перезагрузите окно Cursor. MCP метаданных подключается отдельно (список готовых — skills/1c-review/facts.md)."
