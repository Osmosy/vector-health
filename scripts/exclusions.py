#!/usr/bin/env python3
"""Единственное определение служебного артефакта апстрима.

Зачем отдельный модуль. Правила исключения жили в трёх копиях — в
`sync_upstreams.py` (константы `EXCLUDE_*`), в `service_artifacts.py` (свои копии)
и в валидаторе, — и копии разошлись. Замер: синхронизация помечает в дереве
**173** файла, инвентарь видел **149**; расхождение в 24 файла — это файлы во
вложенных каталогах навыка (`references/`, `scripts/`, `assets/`, `database/`),
куда инвентарь не заглядывал. Файл `*_audit_result.json` в `references/` валидатор
не замечал вовсе.

Правило теперь одно: `classify(path) -> kind | None`, и её используют все.
Две копии одной арифметики расходятся — это уже случалось здесь с подсчётом
состава `scripts/` (`6 JSON` против `7`) и с числами проверок в документах.

Правила намеренно УЖЕ, чем были:
- маркер `_coverage` заменён точными именами: он цеплял рабочие скрипты
  `self-review/scripts/check_artifact_coverage.py` и
  `render-pdf-doc/scripts/scan_glyph_coverage.py`, которые вызываются из SKILL.md
  (синхронизация такие файлы никогда не обновила бы);
- `/docs/` применяется только к корню репозитория апстрима, а не к подкаталогу
  навыка: под него попадали шесть рабочих документов `ppt-master/scripts/docs/`.
"""
from __future__ import annotations

# Каталоги, которых в библиотеке быть не должно: отрезаны при сборке или служебные.
EXCLUDE_PARTS = (
    "/evals/", "/eval/", "/fixtures/", "/repo/", "/node_modules/", "/.git/",
    "/tests/", "/test_data/", "/.github/", "/challenges/",
    "/lint_challenge/", "/analysis_run_challenge/", "/_challenge/",
)
# Тяжёлые форматы: данные прогонов и бинарные выгрузки, а не материал навыка.
EXCLUDE_SUFFIX = (".npy", ".xlsx", ".parquet", ".h5ad", ".rds", ".bam", ".zip", ".whl")
# Служебные артефакты по имени файла.
EXCLUDE_MARKERS = (
    "_audit_result", "audit_result", "eval_report", "POLISH_CHANGELOG",
    "CHANGELOG", "_coverage", "conftest.py",
)
# Точные имена вместо широкого `_coverage`: широкий маркер задевал рабочие скрипты
# (`check_artifact_coverage.py`, `scan_glyph_coverage.py`).
COVERAGE_NAMES = ("coverage.json", ".coverage", "coverage.xml", "coverage.lcov")

# Каталоги, которые считаются служебными целиком (нужны и для уборки пустых).
SERVICE_DIRS = ("tests", "test_data", "evals", "eval", "fixtures", "challenges",
                "lint_challenge", "analysis_run_challenge", "_challenge")

# Подкаталоги навыка, в которые НУЖНО заглядывать: служебный файл может лежать
# там. До этой правки инвентарь обходил только корень навыка и именованные
# служебные каталоги, поэтому 24 файла синхронизация помечала, а инвентарь не видел.
NESTED_SCAN_DIRS = ("references", "scripts", "assets", "database", "data", "templates",
                    "prompts", "examples", "docs", "src", "lib", "config")


def _parts(path: str) -> list[str]:
    return ["/" + p + "/" for p in path.replace("\\", "/").strip("/").split("/")]


def classify(path: str, *, is_repo_root_doc: bool = False) -> str | None:
    """Вид служебного артефакта или None, если файл — материал навыка.

    `path` — путь ВНУТРИ навыка (например `references/x_audit_result.json`).
    `is_repo_root_doc` — правда, если путь ведёт в `/docs/` корня РЕПОЗИТОРИЯ
    апстрима (тогда правило `/docs/` применяется); у подкаталога навыка `docs/`
    материалом считается.
    """
    p = "/" + path.replace("\\", "/").lstrip("/")
    name = p.rsplit("/", 1)[-1]

    if is_repo_root_doc and "/docs/" in p:
        return "каталог docs/ в корне источника"
    for part in EXCLUDE_PARTS:
        if part in p:
            # `/tests/` и подобные — служебный каталог целиком
            return f"каталог {part.strip('/')}/"
    if name in COVERAGE_NAMES:
        return "файл покрытия"
    if name.endswith(EXCLUDE_SUFFIX):
        return "исключённое расширение"
    for marker in EXCLUDE_MARKERS:
        if marker in name:
            # `_coverage` как маркер больше не используется (см. COVERAGE_NAMES)
            if marker == "_coverage":
                continue
            return "служебный артефакт по имени"
    return None


def is_service_dir(name: str) -> bool:
    """Каталог целиком служебный (для уборки опустевших)."""
    return name in SERVICE_DIRS
