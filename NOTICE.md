# Сторонние компоненты и атрибуция

Репозиторий распространяется под лицензией MIT (см. `LICENSE`). Ниже — четыре
сторонние коллекции, навыки которых включены в библиотеку. Каждая сохраняет
собственную лицензию; полные тексты — в `THIRD_PARTY_LICENSES/`.

## Что именно взято

| Набор | Лицензия | Взято | Статус |
|---|---|---|---|
| [FreedomIntelligence/OpenClaw-Medical-Skills](https://github.com/FreedomIntelligence/OpenClaw-Medical-Skills) | MIT (заявлена в README, файла `LICENSE` в корне нет) | `skills/` — 777 навыков: биоинформатика, геномика, клинические БД, drug discovery | тексты байт-в-байт |
| [aipoch/medical-research-skills](https://github.com/aipoch/medical-research-skills) | MIT (© AIPOCH) | `skills/` — 600 навыков: evidence, дизайн исследования, анализ, письмо, аудит навыков | тексты байт-в-байт |
| [maziyarpanahi/openmed](https://github.com/maziyarpanahi/openmed) | Apache-2.0 | `skills/` — 74 навыка: клинический NLP, FHIR, деидентификация, HIPAA, ICD-10 | тексты байт-в-байт |
| [Aperivue/medsci-skills](https://github.com/Aperivue/medsci-skills) | MIT (© Aperivue) | `skills/` — 59 навыков: протоколы, статистика, мета-анализ, гранты, imaging | тексты байт-в-байт |
| собственные | MIT (© Osmosy) | `skills/dicom-vlm-analysis`, `skills/atrial-fibrillation-treatment`, `skills/abdominal-ct-findings` | написаны здесь (таксономия в последнем — из RADAR, см. ниже) |
| [alibaba-damo-academy/damo-radar](https://github.com/alibaba-damo-academy/damo-radar) | Apache-2.0 (© Alibaba DAMO Academy) | таксономия 146 находок × 18 анатомических структур в `skills/abdominal-ct-findings/references/radar-taxonomy.json` | названия на ZH/EN взяты из `results/RADAR_infer_results_demo.csv` без изменений; переводы на русский — наши |

Коллизии имён разрешались в пользу одного источника: один и тот же навык в
разных коллекциях бывает с разным содержимым, и в библиотеке остаётся одна
версия. Какая именно — фиксирует карта происхождения
(`scripts/upstream-origin.json`, сопоставление по blob SHA).

## RADAR (Alibaba DAMO Academy) — только таксономия, не модель

`skills/abdominal-ct-findings` использует **текстовые названия классов** из открытого
репозитория [alibaba-damo-academy/damo-radar](https://github.com/alibaba-damo-academy/damo-radar)
(файл `results/RADAR_infer_results_demo.csv`): 146 находок × 18 структур, названия на
китайском и английском взяты без изменений, переводы на русский — наши.

| Артефакт RADAR | Лицензия | Взят ли к нам |
|---|---|---|
| Код репозитория | Apache-2.0 | нет (только текст названий) |
| **Веса модели** | **CC BY-NC-SA 4.0** (некоммерческая) | **нет и не будут** |
| Запись в Zenodo | CC-BY-4.0 | нет |

Практический вывод: веса — некоммерческие, и это ограничение не про нас, потому что
мы их не берём. Таксономия — это список названий классов, а не модель; лицензия
Apache-2.0 покрывает её использование с сохранением атрибуции (она в этом файле).

## Оговорка по лицензии OpenClaw-Medical-Skills

У этого репозитория **нет файла `LICENSE` в корне**: MIT заявлена только бейджем
и строкой в README. Отдельные `LICENSE.txt` лежат внутри навыков, которые
команда OpenClaw вендорила сама (pdf, docx, pptx, markitdown), — это лицензии
их источников, а не корневая лицензия коллекции.

Практический вывод: юридически это слабее, чем файл лицензии. Мы фиксируем
фактическое положение дел, не додумывая за апстрим, и держим это здесь, чтобы
тот, кто переносит навыки дальше, видел риск, а не обнаруживал его после.

## Ограниченные лицензии внутри библиотеки — читать до использования

Лицензия репозитория (MIT) покрывает **собственный вклад**. У части вендоренных
навыков лицензия ограничивает использование независимо от неё — сводка по факту
дерева (`scripts/restricted-licenses.json`):

| Что | Навыков | Лицензия | Следствие |
|---|---|---|---|
| Навыки с проприетарной шапкой в самом тексте | **308** (280 из OpenClaw + 28 вложенных) | «This code is proprietary and confidential… All Rights Reserved», © 2026 MD BABU MIA, PhD (шапка — из апстрима OpenClaw, не наша правка) | текст прямо запрещает копирование; MIT-статус этих файлов не подтверждён |
| Офисные навыки Anthropic | **9** (`PPTX-Skill`, `docx`, `docx-official`, `pdf`, `pdf-anthropic`, `pptx`, `pptx-official`, `xlsx`, `xlsx-official`) | «© 2025 Anthropic, PBC. All rights reserved» + `LICENSE.txt` рядом, условия — по вашему соглашению с Anthropic | не MIT; использование регулируется договором с Anthropic |
| Non-Commercial | 2 (`varcadd-pathogenicity`, `variant-interpretation-acmg/varCADD`) | `Non-Commercial` | коммерческое использование запрещено |

**Итого уникальных навыков с ограничениями — 317.** Сумма по видам (308 + 9 + 2 = 319) завышена: два «Non-Commercial» — это один навык `varCADD` в двух местах (`varcadd-pathogenicity` и `variant-interpretation-acmg/varCADD`, один и тот же sha), и он же входит в 308 с проприетарной шапкой. Ещё один юридический нюанс: у навыка `deepvariant` вложенная копия (`variant-interpretation-acmg/bioSkills/deepvariant`) несёт проприетарную шапку, а верхняя (`bio-variant-calling-deepvariant`) — нет; обе версии есть в апстриме отдельно, текст не переписывается.

Это расхождение — **свойство апстримов, а не ошибка сборки**: проприетарная шапка
лежит в файлах OpenClaw-Medical-Skills, который при этом заявляет MIT в README.
Мы фиксируем факт и не переписываем чужие шапки (правка была бы затиранием
лицензионной информации), но и не выдаём их за свободные.

**Практический вывод.** Перед коммерческим использованием конкретного навыка
проверьте его поле `license` и первые строки `SKILL.md`. Для 308 навыков с
проприетарной шапкой считать их MIT нельзя; для офисных навыков Anthropic нужно
ваше действующее соглашение. Атрибуция ниже верна, но она не отменяет этих
ограничений.

Откуда эти ограничения: проприетарные шапки — все 308 из OpenClaw; офисные навыки
Anthropic — 8 из OpenClaw и 1 из AIPOCH (`PPTX-Skill` — тот самый девятый, который
не упоминался ни в одном документе, пока внешний аудит не сверил числа);
Non-Commercial — 2 из OpenClaw. То есть митигация по проприетарным одна на
источник, а не 308 отдельных историй. Числа считаются из дерева
(`scripts/build_stats.py`), сверяются валидатором.

## Чего в репозитории нет и почему

- **Служебных результатов работы апстримов.** Отчёты прогонов (`eval_report_*`),
  аудиты (`*_audit_result*`), `POLISH_CHANGELOG.md`, каталоги `evals/` — это следы
  их внутренних процессов, а не материал навыка. Приведено в соответствие с
  деревом: `python3 scripts/sync_upstreams.py --prune` удалил **1100 таких файлов
  (8.4 МБ)**, из них по маркеру имени 714 (`audit_result` 318, `eval_report` 255,
  `POLISH_CHANGELOG` 141) и 386 внутри тестовых каталогов, на которые никто не
  ссылается.
- **Тестовых каталогов, на которые НИКТО не ссылается.** Из 504 файлов в `tests/`
  осталось **146** в 45 каталогах: файл каталога сохраняется, если его путь
  встречается в `SKILL.md` или в `references/` — так, `LightGBM-analysis`
  описывает работу на `tests/data/dt_sample1.csv`. Пустые каталоги убраны: каталог
  без файлов — след уборки, а не материал.
- **Демо-датасетов на мегабайты.** Две выгрузки 23andMe у `genome-compare`
  (`data/george_church_23andme.txt.gz`, `data/manuel_corpas_23andme.txt.gz`) не
  тянутся сознательно: пример генома, а не материал навыка.

Правила и исключения: `scripts/service_artifacts.py` (инвентарь),
`scripts/kept-service-files.json` (сохранённое с причиной), `--prune` в
`scripts/sync_upstreams.py` (применение). Повторный запуск даёт ноль.

## Как обновляются навыки

Не вручную: синхронизация идёт скриптом, который сравнивает локальные файлы с
апстримом; повторный запуск даёт ноль изменений.

```bash
python3 scripts/sync_upstreams.py --dry-run    # что изменилось бы
python3 scripts/sync_upstreams.py              # применить
python3 scripts/sync_upstreams.py --only openmed
```

Отдельный случай — «гибридные» навыки: `SKILL.md` пришёл из одного источника,
а его `references/` и `scripts/` существуют только в другом, более полном форке
(`gwas-database`, `pathml`, `pydicom`, `shap`, `hypothesis-generation`,
`pyhealth` и др.: SKILL.md от AIPOCH, остальное — в форке
OpenClaw-Medical-Skills). Такие файлы синхронизация добирает из форка и никогда
не подменяет владельческий `SKILL.md`.

## Использовано как источник идей (файлы не включены)

- [Hermes Agent](https://github.com/NousResearch/hermes-agent) — платформа, под
  которую собрана библиотека.
- Экосистема Vector: [vector-work](https://github.com/Osmosy/vector-work) (хаб),
  [vector-legal](https://github.com/Osmosy/vector-legal),
  [vector-shotcraft](https://github.com/Osmosy/vector-shotcraft).

---

Библиотека — агрегация. Если вы автор навыка и хотите изменить атрибуцию или
удалить его — создайте issue/PR.
