AI супер скила для 1С разработки

**Статус:** релиз **1.1.0** — полный процессный контур без заглушек в `SKILL.md`.

Набор процессных скиллов для AI-агента (Cursor, Claude Code, Codex и любой, кто читает `SKILL.md`). Не каталог tool-skills и не замена BSL LS / Sonar: сначала фаза и роутер, потом инструменты и MCP.

## Состав (16 скиллов)

| Контур | Скиллы |
|--------|--------|
| Роутинг | `using-1c-superpowers` |
| Задумать → спланировать → сделать | `1c-brainstorming`, `1c-writing-plans`, `1c-executing-plans` |
| Реализация и сбои | `1c-tdd`, `1c-systematic-debugging`, `1c-performance` |
| Сдача | `1c-verification`, `1c-review`, `1c-receiving-review`, `1c-finish-branch` |
| Домен 1С | `1c-extension`, `1c-update`, `1c-exchange` |
| Набор и диагностика | `1c-writing-skills`, `diagnosing-1c-superpowers` |

Цепочка по умолчанию: brainstorm → plan → execute (+ tdd / extension / update / exchange) → при сбое debug → verify → review → finish. **Сводку и вердикт сдачи** пишет только `1c-review`.

Карточки правил (`transactions`, `exchange`, `extension`, `gate`, …) лежат в `skills/1c-review/` и открываются, когда diff их касается. Область — изменённые процедуры и явно подтянутые файлы; без выгрузки — «не хватает факта», не выдуманный запрет.

## Установка

Через [skills.sh](https://www.skills.sh/) (Cursor, Claude Code, Codex и другие агенты):

```sh
npx skills add dimzfresh/1c-superpowers
```

Или из клона репозитория, из каталога плагина:

```sh
sh scripts/install.sh
```

Скрипт создаёт симлинк в `~/.cursor/plugins/local/1c-superpowers`. Отдельный «1С-агент» не нужен — это скиллы для того агента, которым уже пользуетесь. Для Cursor: `sh scripts/install.sh`. Для Claude Code: каталог плагина содержит `.claude-plugin/plugin.json` и SessionStart-хук `hooks/`, который подкладывает роутер в контекст (`claude --plugin-dir <каталог>`). Для остальных агентов подключайте каталог `skills/` целиком: скиллы ссылаются друг на друга по соседним папкам, скрипт `find_checks.py` лежит в `skills/1c-verification/scripts/`.

**Для разработки нужна выгрузка конфигурации или готовый MCP** (для ревью присланного фрагмента не обязательны, но без фактов вердикт всегда «сдать с оговоркой»). Факты о конфигурации берутся из файлов выгрузки или готовых MCP для 1С: список и границы в [skills/1c-review/facts.md](skills/1c-review/facts.md). Собственного MCP плагин не поставляет.

## Проверка


```sh
python3 -m unittest discover -s tests -v
```

Сценарии вход → выход: каталог `scenarios/` и жёсткие evals `evals/cases.json` (HTTP, CFE без dump, ложный запрос в цикле, update `&Вместо`, неполная парность транзакции).


## Evals (A/B, без самоотчётов)

`evals/negative.json` — кейсы на ложные срабатывания (законная явная запись движений, привилегированный режим с выключением, `&Вместо` с продолжением, вложенная транзакция) и один реальный сетевой вызов в транзакции. Прогон с набором скиллов и без него:

```sh
EVAL_AGENT_CMD='claude -p' python3 evals/run_eval.py
```

Сырые ответы пишутся в `evals/transcripts/`, PASS/FAIL ставит скрипт по regex. Прогон на 29 кейсов × 3 повтора (with 87/87, without 79/87) и разбор с ограничениями: [`evals/transcripts/RESULTS.md`](evals/transcripts/RESULTS.md). Это сигнал, не статистика. Ручные записи прошлых «bake»-прогонов перенесены в `evals/archive/` (это не измерения).

Что даёт выгрузка или MCP: [`evals/transcripts_facts/RESULTS.md`](evals/transcripts_facts/RESULTS.md). С фактами вердикт определённый и верный, без них всегда «сдать с оговоркой» + «не хватает факта».

На слабой модели (haiku 4.5) выигрыш заметнее: with 57/58, without 64/87, разбор: [`evals/transcripts_haiku/RESULTS.md`](evals/transcripts_haiku/RESULTS.md).
