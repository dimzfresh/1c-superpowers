# Live bake runs (2026-10-01)

Артефакты live bake по манифесту [`../cases.json`](../cases.json). Сводки в стиле process-skills; значение секретов в run-файлы не копировать.

| Run | Skill | Результат |
|-----|-------|-----------|
| [http-in-posting.md](./http-in-posting.md) | 1c-review | PASS |
| [false-query-in-loop.md](./false-query-in-loop.md) | 1c-review | PASS |
| [cfe-missing-second-dump.md](./cfe-missing-second-dump.md) | 1c-extension | PASS |
| [update-vendor-vmesto.md](./update-vendor-vmesto.md) | 1c-update | PASS |
| [transaction-parity-incomplete.md](./transaction-parity-incomplete.md) | 1c-review | PASS |
| [secret-in-mr.md](./secret-in-mr.md) | 1c-review / secrets | PASS (литерал пароля в run отсутствует) |

Учебный transcript для diagnosing: [`../../scenarios/diagnose-router-silent.md`](../../scenarios/diagnose-router-silent.md).
