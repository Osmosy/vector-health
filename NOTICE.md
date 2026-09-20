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
| [alibaba-damo-academy/damo-radar](https://github.com/alibaba-damo-academy/damo-radar) | Apache-2.0 (© Alibaba DAMO Academy) | таксономия 146 находок × 18 органов в `skills/abdominal-ct-findings/references/radar-taxonomy.json` | названия на ZH/EN взяты из `results/RADAR_infer_results_demo.csv` без изменений; переводы на русский — наши |

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
| Офисные навыки Anthropic | **9** (`xlsx`, `pdf`, `docx`, `pptx`, `PPTX-Skill` — плюс варианты `xlsx-official`, `pdf-anthropic`, `docx-official`, `pptx-official`) | «© 2025 Anthropic, PBC. All rights reserved» + `LICENSE.txt` рядом, условия — по вашему соглашению с Anthropic | не MIT; использование регулируется договором с Anthropic |
| Non-Commercial | 2 (`varcadd-pathogenicity`, `variant-interpretation-acmg/varCADD`) | `Non-Commercial` | коммерческое использование запрещено |

**Итого уникальных навыков с ограничениями — 317.** Сумма по видам (308 + 9 + 2 = 319) завышена: два «Non-Commercial» — это один навык `varCADD` в двух местах (`varcadd-pathogenicity` и `variant-interpretation-acmg/varCADD`, один и тот же sha), и он же входит в 308 с проприетарной шапкой. Ещё один юридический нюанс: у навыка `deepvariant` вложенная копия (`variant-interpretation-acmg/bioSkills/deepvariant`) несёт проприетарную шапку, а верхняя (`bio-variant-calling-deepvariant`) — нет; обе версии есть в апстриме отдельно, текст не переписывается.
