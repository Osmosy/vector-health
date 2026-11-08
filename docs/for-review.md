# Что проверить повторно (для внешней проверки)

Коммит: `ccc0fde`. Хеши ниже — sha256 файлов в этом коммите: если присланный архив совпадает по ним, значит он не из кеша.

## Файлы

| Файл | Байт | sha256 |
|---|---|---|
| `README.md` | 24972 | `c61b529d676fc523…` |
| `NOTICE.md` | 13407 | `2d1f7a54f8f0ddd5…` |
| `AGENTS.md` | 8273 | `e81bd27aff9b2379…` |
| `INSTALL.md` | 14178 | `955f309473b9b5aa…` |
| `agent-description.md` | 6156 | `28aee8146046f4ef…` |
| `scripts/validate.py` | 118841 | `bbdad5eda0bfb1f3…` |
| `scripts/build_stats.py` | 14643 | `f3d3a46654a9137f…` |
| `scripts/stats.json` | 13897 | `b97d3d9802f90cc0…` |
| `scripts/broken_refs.py` | 44515 | `3c8eded9866123f6…` |
| `scripts/service_artifacts.py` | 11725 | `44225b6cfcd489d9…` |
| `scripts/refs.py` | 12625 | `b9b6b77b259c9a6a…` |
| `docs/broken-refs.md` | 49764 | `687bcfd4eca26519…` |
| `docs/tree-digest.json` | 513768 | `561883127f02be4d…` |
| `docs/trials-verified.json` | 4828 | `e2d97fbf98b97664…` |
| `tests/test_scripts.py` | 63510 | `cabd17b1ec0cb4b7…` |
| `tests/mutation_check.py` | 12660 | `bc5730d8cc8f00b2…` |
| `tests/run_offline.py` | 2826 | `0650da41909a0490…` |
| `skills/atrial-fibrillation-treatment/SKILL.md` | 13021 | `a3369865c38266d0…` |
| `.github/workflows/validate.yml` | 8850 | `77ae928ac4e16ff5…` |

## Ключевые числа

Все — из `scripts/stats.json`, который генерируется из дерева (`python3 scripts/build_stats.py --check` падает при расхождении):

- навыков всего 1542 = верхних 1514 + вложенных 28
- по источникам: OpenClaw=805, aipoch=600, openmed=74, Aperivue=59, own=4
- уникальных навыков с ограничениями **317**: проприетарных шапок 308, Anthropic 9, Non-Commercial 2 (сумма видов 319 завышена: два NC — это один навык varCADD в двух местах, и он же входит в проприетарные)
- ссылок 3528, битых 492, категорий 11
- копий общих файлов: 5 | пар идентичных навыков: 4 | почти-дублей: 2
- файлов в `scripts/`: 22 (13 .py, 2 установщик, 7 JSON) | тестовых файлов: 3
- **проверок валидатора: 30** (число из прогона, сверяется в каждом документе)
- тестов: прогон `python3 tests/run_offline.py` (сеть заблокирована в процессе)

## Что изменилось с прошлой проверки

Шесть коммитов по плану `docs/fix-plan.md`: уборка служебных артефактов апстримов (1100 файлов, 8.4 МБ), сверка испытаний `atrial-fibrillation-treatment` по первоисточнику (Europe PMC), отказ перезаписывать отчёт деградировавшими числами, тесты без сети, происхождение вложенных навыков, числа из stats.json.

## Как проверить, не запуская репозиторий

- `docs/tree-digest.json` — по каждому навыку путь, sha256, размер SKILL.md, `name` из frontmatter, признак расхождения, наличие description, проприетарная шапка. Пересчёт навыков, вложенных, расхождений и шапок идёт по нему.
- `docs/trials-verified.json` — семь испытаний: журнал, год, том, страницы, PMID, тип публикации, цифра первичной точки.
- `docs/broken-refs.md` — инвентарь ссылок с категориями.
