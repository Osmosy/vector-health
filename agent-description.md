# vector-health — часть экосистемы Vector

Библиотека медицинских и биомедицинских навыков: 1540 навыков из четырёх
открытых коллекций (OpenClaw-Medical-Skills, AIPOCH medical-research-skills,
openmed, Aperivue medsci-skills) плюс два собственных. Дедупликация по именам,
единая структура `skills/<имя>/SKILL.md`, карта происхождения по каждому навыку.

Содержание — не программа, а справочники и методики: markdown-навыки и скрипты
обслуживания библиотеки (синхронизация, каталог, проверки).

## Связанные проекты

- Хаб экосистемы: https://github.com/Osmosy/vector-work
- Юридический хаб: https://github.com/Osmosy/vector-legal
- Кинематографичные приёмы: https://github.com/Osmosy/vector-shotcraft
- Прогноз спроса: https://github.com/Osmosy/vector-prediction

## Для агентов

- Читай сначала `README.md`, для установки — `INSTALL.md`
- Навыки — `skills/<имя>/SKILL.md` (1540; вендоренные наборы с атрибуцией в `NOTICE.md`)
- Каталог для поиска — `skills-index.json` (имя, путь, описание)
- Два собственных навыка — `skills/dicom-vlm-analysis`, `skills/atrial-fibrillation-treatment`
- Архитектура (живая диаграмма) — `docs/vector-health.architecture.html`
- Инвентарь битых ссылок — `docs/broken-refs.md`
- Перед коммитом прогони проверки: `python3 scripts/validate.py`,
  `python3 scripts/broken_refs.py --strict-own`, `python3 tests/test_scripts.py`
  (то же выполняет CI в `.github/workflows/validate.yml`)
- Вендоренные навыки не редактировать руками: обновление только через
  `python3 scripts/sync_upstreams.py`

## Состав

| Что | Сколько |
|-----|---------|
| Навыки | 1540 (`skills/`), из них 1538 из четырёх сторонних коллекций |
| Навыки верхнего уровня | 1512 каталогов |
| Вложенные навыки | 28 (внутри каталогов-контейнеров апстримов) |
| Собственные навыки | 2 (`dicom-vlm-analysis`, `atrial-fibrillation-treatment`) |
| Скрипты | 6 (`scripts/`) |
| Тесты | 1 файл (`tests/test_scripts.py`) |
| Диаграмма | 1 живая (`docs/vector-health.architecture.html`) |

## Источник и лицензии

Собственный вклад (сборка, скрипты, документация, два навыка) — MIT (© Osmosy).
Вендоренные навыки сохраняют лицензии источников: MIT (OpenClaw-Medical-Skills,
AIPOCH, Aperivue) и Apache-2.0 (openmed). Полные тексты лицензий —
`THIRD_PARTY_LICENSES/`, сводка и оговорки — `NOTICE.md`.

У OpenClaw-Medical-Skills файла лицензии в корне нет: MIT заявлена только в
README — это зафиксировано в `NOTICE.md` отдельным пунктом.
