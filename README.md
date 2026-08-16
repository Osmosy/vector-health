# Vector Health

![Vector Health](assets/vector-logo.png)

**Vector Health** — единая библиотека медицинских и биомедицинских навыков для AI-агентов
(Hermes, OpenClaw, Claude Code, Codex и любой SKILL.md-совместимой платформы). Объединение
четырёх открытых коллекций плюс собственный пайплайн DICOM→VLM, дедупликация по именам и
единая структура `skills/<name>/SKILL.md`.

**1508 навыков** (из 1604 до дедупликации) · 4 источника + 1 собственный · MIT + Apache-2.0

---

## Что внутри

| Источник | Уникальных навыков | Фокус | Лицензия |
|---|---|---|---|
| [OpenClaw-Medical-Skills](https://github.com/FreedomIntelligence/OpenClaw-Medical-Skills) | 777 | биоинформатика, геномика, клинические БД, drug discovery | MIT |
| [medical-research-skills](https://github.com/aipoch/medical-research-skills) (AIPOCH) | 599 | исследовательский workflow: evidence, дизайн, анализ, письмо | MIT |
| [openmed](https://github.com/maziyarpanahi/openmed) | 72 | клинический NLP, FHIR, деидентификация, HIPAA, ICD-10 | Apache-2.0 |
| [medsci-skills](https://github.com/Aperivue/medsci-skills) (Aperivue) | 59 | протоколы, статистика, мета-анализ, гранты, imaging | MIT |
| dicom-vlm-analysis (собственный) | 1 | DICOM → локальная vision-модель (medgemma) | MIT |

**Домены**: клиника · геномика · биоинформатика (RNA-seq, scRNA-seq, GWAS, variant calling) ·
drug discovery · медицинская визуализация (DICOM/радиомика) · FHIR/интероперабельность ·
деидентификация и HIPAA · исследовательский дизайн · академическое письмо.

---

## Структура

```
vector-health/
├── skills/               # 1508 навыков, по одному каталогу на навык
│   └── <name>/SKILL.md   # + references/, scripts/, templates/, assets/ (если есть)
├── skills-index.json     # каталог: имя + описание каждого навыка (для поиска)
├── scripts/              # build_index.py (генерация каталога), validate_skills.py (валидация+скан)
├── .github/workflows/    # CI: валидация frontmatter + скан секретов/PII на каждый push
├── assets/               # логотип Vector
├── README.md
└── NOTICE.md             # атрибуция и лицензии источников
```

Каждый навык — самодостаточный `SKILL.md` с frontmatter (`name`, `description`, иногда
`license`, `metadata`). Навыки сохраняют исходную структуру вспомогательных файлов.

---

## Как пользоваться

Навыки читаются **по запросу**, а не индексируются все сразу (1500 описаний в системном
промпте — это лишний контекст). Рабочая модель:

```
# найти навык
find skills -maxdepth 1 -type d -name '*<ключевое слово>*'

# прочитать и выполнить инструкции
read_file skills/<name>/SKILL.md
```

Установка в агент (опционально, выборочно):

- **Hermes**: скопировать нужный каталог в `~/.hermes/skills/<category>/<name>/`.
- **OpenClaw**: скопировать в `<workspace>/skills/` или `~/.openclaw/skills/`.
- **Claude Code / Codex**: любая `skills/`-директория, подключённая к агенту.

### dicom-vlm-analysis

Собственный навык: чтение DICOM/КТ локальной vision-моделью без облака.
`pydicom` (рендер с window/level) → PNG → Ollama `medgemma:4b` (`/api/generate`, `images=[base64]`).
Подробности и скрипты — в `skills/dicom-vlm-analysis/`.

---

## Ключевые принципы

1. **Один каталог — один навык.** Единая структура `skills/<name>/SKILL.md` для всех источников.
2. **Дедупликация по имени.** При совпадении имён приоритет отдаётся более курируемому
   источнику: medsci-skills > openmed > AIPOCH > OpenClaw-Medical.
3. **Без блоата.** Исключены vendored-репозитории (`repo/`), `node_modules`, файлы >5 МБ,
   шаблоны-многотонники — только инструкции, ссылки и нужные скрипты/референсы.
4. **On-demand.** Навыки не грузятся в контекст без необходимости.
5. **Провенанс сохраняется.** NOTICE.md фиксирует источник и лицензию каждого набора.

---

## Основание

- Собрано для экосистемы **Vector** (github.com/Osmosy).
- Источники (см. NOTICE.md): FreedomIntelligence/OpenClaw-Medical-Skills (MIT),
  aipoch/medical-research-skills (MIT), maziyarpanahi/openmed (Apache-2.0),
  Aperivue/medsci-skills (MIT).
- Собственный вклад: `dicom-vlm-analysis` (MIT, Osmosy).

> ⚠️ Медицинские навыки — инструменты для специалистов и исследователей, а не замена
> врачебной интерпретации. Диагностические выводы остаются компетенцией квалифицированного врача.
