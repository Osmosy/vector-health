# vector-health — часть экосистемы Vector

Библиотека медицинских и биомедицинских навыков: 1541 навык из четырёх
открытых коллекций (OpenClaw-Medical-Skills, AIPOCH medical-research-skills,
openmed, Aperivue medsci-skills) плюс три собственных. Дедупликация по именам,
единая структура `skills/<имя>/SKILL.md`, карта происхождения по каждому навыку.

Содержание — не программа, а справочники и методики: markdown-навыки и скрипты
обслуживания библиотеки (синхронизация, каталог, проверки).

## Связанные проекты

- Хаб экосистемы: https://github.com/Osmosy/vector-work
- Юридический хаб: https://github.com/Osmosy/vector-legal
- Маркетинговое агентство: https://github.com/Osmosy/vector-marketing
- Приёмы для продуктовых роликов: https://github.com/Osmosy/vector-shotcraft
- Прогноз спроса: https://github.com/Osmosy/vector-prediction

## Для агентов

- Читай сначала `README.md`, для установки — `INSTALL.md`
- Навыки — `skills/<имя>/SKILL.md` (1541; вендоренные наборы с атрибуцией в `NOTICE.md`)
- Каталог для поиска — `skills-index.json` (имя, путь, описание)
- Три собственных навыка — `skills/dicom-vlm-analysis`, `skills/atrial-fibrillation-treatment`,
  `skills/abdominal-ct-findings`
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
| Навыки | 1541 (`skills/`), из них 1538 из четырёх сторонних коллекций |
| Навыки верхнего уровня | 1513 каталогов |
| Вложенные навыки | 28 (внутри каталогов-контейнеров апстримов) |
| Собственные навыки | 3 (`dicom-vlm-analysis`, `atrial-fibrillation-treatment`, `abdominal-ct-findings`) |
| Скрипты | 12 (`scripts/`: 7 .py, 1 установщик, 4 JSON-манифеста) |
| Тесты | 1 файл (`tests/test_scripts.py`, 131 проверка) |
| Диаграмма | 1 живая (`docs/vector-health.architecture.html`) |

## Ограничения лицензий — обязательно к прочтению

MIT репозитория покрывает **собственный вклад**. У части вендоренных навыков лицензия
ограничивает использование, и это надо знать ДО работы с ними (полная таблица и
разбор — `NOTICE.md`):

| Что | Навыков | Следствие |
|---|---|---|
| Проприетарная шапка в тексте навыка («proprietary and confidential… All Rights Reserved», © MD BABU MIA — из апстрима OpenClaw) | 308 | считать MIT нельзя |
| Офисные навыки Anthropic (`xlsx`, `pdf`, `docx`, `pptx`, `PPTX-Skill` и их `-official` варианты) | 9 | «© 2025 Anthropic, PBC. All rights reserved» |
| `Non-Commercial` | 2 | коммерческое использование запрещено |
| Таксономия RADAR в `abdominal-ct-findings` | 1 | текст — Apache-2.0 (ок), но **веса модели — CC BY-NC-SA 4.0** и не берутся |

Перед использованием конкретного навыка проверьте его поле `license` и первые строки
`SKILL.md`. Числа сверяются с деревом: `python3 scripts/validate.py`.

## Источник и лицензии

Собственный вклад (сборка, скрипты, документация, три навыка) — MIT (© Osmosy).
Вендоренные навыки сохраняют лицензии источников: MIT (OpenClaw-Medical-Skills,
AIPOCH, Aperivue) и Apache-2.0 (openmed). Полные тексты лицензий —
`THIRD_PARTY_LICENSES/`, сводка и оговорки — `NOTICE.md`.

У OpenClaw-Medical-Skills файла лицензии в корне нет: MIT заявлена только в
README — это зафиксировано в `NOTICE.md` отдельным пунктом.
