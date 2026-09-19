<div align="center">

<img src="assets/vector-logo.png" alt="Vector Health" width="200"/>

# Vector Health

[![Architecture: live](https://img.shields.io/badge/Architecture-live_diagram-4f8ff7.svg)](https://osmosy.github.io/vector-health/docs/vector-health.architecture.html)

**Библиотека медицинских и биомедицинских навыков для AI-агентов — 1541 навык из четырёх открытых коллекций плюс три собственных**

[![Hermes Agent](https://img.shields.io/badge/Hermes-Agent-blue.svg)](https://github.com/NousResearch/hermes-agent)
[![Ecosystem: Vector](https://img.shields.io/badge/Ecosystem-Vector-blue.svg)](https://osmosy.github.io/)
[![Skills: 1541](https://img.shields.io/badge/Skills-1541-green.svg)](#состав)
[![Sources: 4](https://img.shields.io/badge/Upstream_collections-4-blueviolet.svg)](NOTICE.md)
[![Own skills: 2](https://img.shields.io/badge/Own_skills-2-orange.svg)](#собственные-навыки)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Документация:** [Установка](INSTALL.md) · [Архитектура (live)](https://osmosy.github.io/vector-health/docs/vector-health.architecture.html) · [Источники и лицензии](NOTICE.md) · [Ограниченные лицензии](NOTICE.md#ограниченные-лицензии-внутри-библиотеки--читать-до-использования) · [Битые ссылки](docs/broken-refs.md) · [Для агентов](AGENTS.md)

</div>

---

Библиотека медицинских и биомедицинских навыков: 1541 `SKILL.md` из четырёх
открытых коллекций плюс три собственных навыка. Не программа, не сервис и **не
медицинское изделие**: навыки описывают методики — как считать мета-анализ, как
читать DICOM локальной моделью, как оценить риск смещения.

Единая структура `skills/<имя>/SKILL.md`, дедупликация по именам и карта
происхождения по каждому навыку: видно, из какой коллекции он пришёл.

## Состав

| Источник | Навыков | Фокус | Лицензия |
|---|---|---|---|
| [OpenClaw-Medical-Skills](https://github.com/FreedomIntelligence/OpenClaw-Medical-Skills) | 777 | биоинформатика, геномика, клинические БД, drug discovery | MIT (заявлена в README, файла нет) |
| [medical-research-skills](https://github.com/aipoch/medical-research-skills) (AIPOCH) | 600 | evidence, дизайн исследования, анализ, письмо, аудит навыков | MIT |
| [openmed](https://github.com/maziyarpanahi/openmed) | 74 | клинический NLP, FHIR, деидентификация, HIPAA, ICD-10 | Apache-2.0 |
| [medsci-skills](https://github.com/Aperivue/medsci-skills) (Aperivue) | 59 | протоколы, статистика, мета-анализ, гранты, imaging | MIT |
| собственные | 3 | DICOM → локальная vision-модель; тактика при фибрилляции предсердий; таксономия находок КТ брюшной полости | MIT |

**1541 навык** — 1513 каталогов верхнего уровня и 28 вложенных (апстримы держат
часть навыков внутри каталогов-контейнеров, например
`variant-interpretation-acmg/bioSkills/…`). Каталог включает вложенные: у них
отдельное поле `path`.

**Домены**: клиника · геномика · биоинформатика (RNA-seq, scRNA-seq, GWAS, variant
calling) · drug discovery · медицинская визуализация (DICOM/радиомика) ·
FHIR/интероперабельность · деидентификация и HIPAA · исследовательский дизайн ·
академическое письмо.

## Как это работает

```
Четыре апстрима ──┐
OpenClaw  777     │
AIPOCH    600     ├─→ sync_upstreams.py ─→ skills/ (1541)  ─→ агент читает по запросу
openmed    74     │   (идемпотентно:          │
Aperivue   59     │    повторный запуск = 0)   ├─→ build_index.py ─→ skills-index.json
                  │                           │                      (поиск без загрузки всего)
собственные 2 ────┘                           └─→ validate.py ─→ CI: числа, лицензии, ссылки
```

Порядок работы с библиотекой:

1. **Найти** навык по каталогу `skills-index.json` (имя, путь, описание) — не
   грузить 1541 описание в контекст.
2. **Прочитать** `skills/<имя>/SKILL.md` и следовать методике.
3. **Обновить** при необходимости: `python3 scripts/sync_upstreams.py`.
4. **Проверить** перед коммитом: `python3 scripts/validate.py`.

## Быстрый старт

```bash
git clone https://github.com/Osmosy/vector-health.git
cd vector-health

# найти навык по каталогу
python3 -c "
import json
for s in json.load(open('skills-index.json'))['skills']:
    if 'dicom' in s['name']: print(s['path'], '—', s['description'][:80])
"

# прочитать методику
less skills/dicom-vlm-analysis/SKILL.md

# подключить к своему агенту (Hermes)
cp -r skills/dicom-vlm-analysis ~/.hermes/skills/

# проверить целостность
python3 scripts/validate.py
```

Ставить все 1541 сразу не нужно: каталог существует ровно затем, чтобы брать по
надобности.

## Собственные навыки

- **`dicom-vlm-analysis`** — чтение DICOM/КТ локальной vision-моделью без облака:
  `pydicom` (рендер с window/level) → PNG → Ollama `medgemma:4b`
  (`/api/generate`, `images=[base64]`).
- **`atrial-fibrillation-treatment`** — тактика при фибрилляции предсердий:
  контроль ритма, катетерная аблация, антикоагуляция.
- **`abdominal-ct-findings`** — таксономия находок КТ брюшной полости:
  146 находок × 18 органов на русском, английском и китайском (источник — открытая
  модель RADAR), плюс методика честного замера качества модели на внешнем тесте.

Эти три навыка можно править напрямую — синхронизация их не трогает.

## Структура репозитория

```
vector-health/
├── skills/                    # 1541 навык (1513 верхних + 28 вложенных)
│   └── <имя>/SKILL.md         # + references/, scripts/, assets/ (если есть)
├── skills-index.json          # каталог для поиска: имя, путь, описание
├── scripts/
│   ├── sync_upstreams.py      # синхронизация с четырьмя апстримами (идемпотентна)
│   ├── build_index.py         # сборка каталога (рекурсивно, с вложенными)
│   ├── validate.py            # валидатор репозитория: 15 проверок (спина CI)
│   ├── broken_refs.py         # инвентарь ссылок внутри навыков
│   ├── upstream-origin.json   # карта происхождения: навык → источник
│   ├── name-mismatches.json   # учтённые расхождения name и каталога (69)
│   └── restricted-licenses.json  # навыки с ограниченной лицензией (308)
├── docs/
│   ├── vector-health.architecture.{json,html}  # живая диаграмма
│   └── broken-refs.md         # инвентарь битых ссылок с причиной
├── tests/test_scripts.py      # проверки скриптов
├── THIRD_PARTY_LICENSES/      # полные тексты лицензий источников
├── .github/workflows/         # CI
├── LICENSE                    # MIT (собственный вклад)
├── NOTICE.md                  # атрибуция, оговорки по лицензиям
├── INSTALL.md                 # установка для стороннего пользователя
├── AGENTS.md                  # правила для AI-агентов в этом репозитории
├── agent-description.md       # краткая машинная сводка
├── _config.yml                # Jekyll: чтобы шапка README рендерилась
└── README.md
```

## Ключевые решения и грабли

- **Идемпотентная синхронизация.** `sync_upstreams.py` сравнивает **локальный файл
  с HEAD апстрима**, а не «базу с head». Второй вариант законно описывает дельту,
  но каждый запуск печатает одно и то же — и проверить, применена ли она, нечем.
  Сейчас повторный запуск даёт `обновить 0, добавить 0, удалить 0`.
- **«Гибридные» навыки.** У части навыков `SKILL.md` пришёл из одного апстрима, а
  его `references/` и `scripts/` существуют только в другом, более полном форке
  (`gwas-database`, `pathml`, `pydicom`, `shap`, `hypothesis-generation`: SKILL.md
  от AIPOCH, остальное — в форке OpenClaw). Синхронизация добирает такие файлы из
  форка и никогда не подменяет владельческий `SKILL.md`.
- **Две версии одного навыка в апстриме.** AIPOCH держит один и тот же навык в
  нескольких категориях с **разным** содержимым. Версия выбирается по совпадению с
  локальной, иначе файл подменяется содержимым чужой категории.
- **Битые ссылки не «чистятся».** 485 битых ссылок: 2 — демо-датасеты по 4.9 МБ
  (не тянем), 483 — файлы, которых нет ни у одного источника (у апстримов лежали в
  отрезанных `tests/`/`evals/`). Правка чужого текста не сделала бы навык рабочим,
  поэтому вместо неё — инвентарь с причиной: `docs/broken-refs.md`.
- **Вложенные навыки в каталоге.** 28 навыков лежат внутри каталогов-контейнеров;
  плоский обход `skills/` их терял — они были в дереве, но не находились поиском.

## Экосистема Vector

| Проект | Что |
|---|---|
| [vector-work](https://github.com/Osmosy/vector-work) | Хаб экосистемы |
| [vector-legal](https://github.com/Osmosy/vector-legal) | Юридические навыки (170+) |
| [vector-marketing](https://github.com/Osmosy/vector-marketing) | Маркетинговое агентство (19 агентов) |
| [vector-shotcraft](https://github.com/Osmosy/vector-shotcraft) | Приёмы для продуктовых роликов |
| [vector-prediction](https://github.com/Osmosy/vector-prediction) | Прогноз спроса |
| **vector-health** | Медицинские навыки (этот репозиторий) |

## Журнал версий

| Дата | Изменение |
|---|---|
| 2026-08-16 | Сборка библиотеки из четырёх коллекций: каталог навыков, CI |
| 2026-08-16 | Добавлен собственный навык `atrial-fibrillation-treatment` |
| 2026-09-19 | Синхронизация с апстримами: 113 файлов, новые навыки `ask-openmed`, `setup-openmed`, `skill-auditor` |
| 2026-09-19 | Каталог включает 28 вложенных навыков (был плоский обход — часть была невидима поиску) |
| 2026-09-19 | Докачка файлов-ссылок из форков (34 файла) + инвентарь битых ссылок |
| 2026-09-19 | Зафиксированы ограниченные лицензии: 308 проприетарных шапок, 8 навыков Anthropic, 2 Non-Commercial |
| 2026-09-19 | Оформление по стандарту экосистемы: LICENSE, INSTALL, AGENTS, `validate.py`, живая диаграмма, Pages |
| 2026-09-19 | Собственный навык `abdominal-ct-findings`: таксономия 146 находок КТ брюшной полости (18 структур, 3 языка) + методика замера качества; 15 проверок CI |

## Лицензии

Собственный вклад (сборка, скрипты, документация, три навыка) — **MIT** (© 2026
Osmosy). Вендоренные навыки сохраняют лицензии источников: MIT (OpenClaw,
AIPOCH, Aperivue) и Apache-2.0 (openmed). Полные тексты —
`THIRD_PARTY_LICENSES/`; сводка — `NOTICE.md`.

**Ограничения внутри библиотеки — читать до использования.** Лицензия
репозитория покрывает только собственный вклад. По факту дерева
(`scripts/restricted-licenses.json`):

| Что | Навыков | Следствие |
|---|---|---|
| Проприетарная шапка в тексте навыка («proprietary and confidential… All Rights Reserved», © MD BABU MIA — из апстрима OpenClaw) | 308 | считать MIT нельзя; текст прямо запрещает копирование |
| Офисные навыки Anthropic (`xlsx`, `pdf`, `docx`, `pptx` + `-official`) | 8 | «© 2025 Anthropic, PBC. All rights reserved»; нужен ваш договор с Anthropic |
| `Non-Commercial` | 2 | коммерческое использование запрещено |

Это свойство апстримов, а не сборки: OpenClaw заявляет MIT в README, держа
проприетарную шапку в 280 своих навыках. Чужие лицензионные тексты мы не
переписываем — фиксируем факт.

> **Ограничение.** Навыки — методики для специалистов и исследователей, не замена
> врачебной интерпретации. Ни один вывод библиотеки не является диагнозом,
> назначением или заключением: клиническое решение остаётся за квалифицированным
> специалистом.
