# NOTICE — источники и лицензии

Vector Health объединяет навыки из следующих открытых репозиториев. Каждый навык сохраняет
лицензию своего источника (указана в frontmatter `license`, где она есть). Атрибуция и ссылки:

## 1. OpenClaw-Medical-Skills
- Репозиторий: https://github.com/FreedomIntelligence/OpenClaw-Medical-Skills
- Лицензия: MIT
- Вклад: ~777 уникальных навыков (биоинформатика, геномика, клинические БД, drug discovery).
  В том числе `medical-specialty-briefs` — навык из их каталога (в апстриме лежит как `SKILL.MD`).

## 2. medical-research-skills (AIPOCH)
- Репозиторий: https://github.com/aipoch/medical-research-skills
- Лицензия: MIT (Copyright 2026 AIPOCH)
- Вклад: ~600 уникальных навыков (Evidence Insights, Protocol Design, Data Analysis,
  Academic Writing, Other), включая `skill-auditor` — аудитор SKILL.md-навыков.

## 3. openmed (maziyarpanahi)
- Репозиторий: https://github.com/maziyarpanahi/openmed
- Лицензия: Apache-2.0
- Вклад: ~74 уникальных навыка (клинический NLP, FHIR, деидентификация, HIPAA, ICD-10),
  включая роутер `ask-openmed` и `setup-openmed` (политика деидентификации).

## 4. medsci-skills (Aperivue)
- Репозиторий: https://github.com/Aperivue/medsci-skills
- Лицензия: MIT (Copyright 2026 Aperivue)
- Вклад: ~59 уникальных навыков (протоколы, статистика, мета-анализ, гранты, imaging).

## Собственный вклад
- `dicom-vlm-analysis` — MIT (Copyright Osmosy): DICOM → локальная vision-модель.
- `atrial-fibrillation-treatment` — MIT (Copyright Osmosy): тактика при фибрилляции предсердий.

## Синхронизация с источниками
`scripts/sync_upstreams.py` приводит вендоренные навыки к состоянию апстрима: сравнивает
локальные файлы с HEAD источника, обновляет изменившиеся, добирает файлы, на которые
ссылается SKILL.md, и удаляет то, что апстрим убрал. Карта происхождения
(`scripts/upstream-origin.json`) фиксирует, из какого источника пришёл каждый навык, —
при коллизии имён версия другого источника не перезаписывается.

---

Примечание: библиотека — агрегация. Полные тексты лицензий доступны в исходных репозиториях
по ссылкам выше. Если вы автор навыка и хотите изменить атрибуцию или удалить его — создайте
issue/PR.
