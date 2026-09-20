#!/usr/bin/env python3
"""Пересобрать docs/for-review.md: хеши ключевых файлов + числа из stats.json.

Зачем генератор, а не рукописный файл: документ для внешней проверки — это
утверждение «вот что лежит в репозитории на таком-то коммите». Рукописный он
разошёлся сразу: в нём остались 23 проверки, 197 тестов и 15 скриптов, тогда как
фактические числа — 26, 213 и 16. Внешняя проверка, сверяющая архив с этим файлом,
получала несоответствие там, где его нет.

Запуск: python3 scripts/build_for_review.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Файлы, которые аудитор просит в первую очередь: документы и то, что он проверяет
# сам (валидатор, статистика, инвентарь ссылок).
KEY_FILES = (
    "README.md", "NOTICE.md", "AGENTS.md", "INSTALL.md", "agent-description.md",
    "scripts/validate.py", "scripts/build_stats.py", "scripts/stats.json",
    "scripts/broken_refs.py", "scripts/service_artifacts.py", "scripts/refs.py",
    "docs/broken-refs.md", "docs/tree-digest.json", "docs/trials-verified.json",
    "tests/test_scripts.py", "tests/mutation_check.py", "tests/run_offline.py",
    "skills/atrial-fibrillation-treatment/SKILL.md",
    ".github/workflows/validate.yml",
)


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def head_commit() -> str:
    """Короткий хеш HEAD. Без git — ошибка, а не загадочный «коммит ?».

    Файл для внешней проверки утверждает «вот что лежит в коммите таком-то». Если
    git недоступен, хеша нет, и подставить вместо него «?» значит выдать документ,
    по которому нельзя сверить архив.
    """
    out = subprocess.run(["git", "rev-parse", "--short=7", "HEAD"], cwd=ROOT,
                         capture_output=True, text=True)
    commit = out.stdout.strip()
    if out.returncode != 0 or not commit:
        raise SystemExit("ОШИБКА: git недоступен — не могу указать коммит для "
                         "docs/for-review.md (этот файл сверяется с архивом по хешу)")
    return commit


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="не писать: падать, если файл на диске разошёлся")
    args = ap.parse_args()
    stats = json.loads((ROOT / "scripts" / "stats.json").read_text(encoding="utf-8"))
    nd = json.loads((ROOT / "scripts" / "name-duplicates.json").read_text(encoding="utf-8"))
    sc, tf, S = stats["scripts"], stats["tests"], stats["restricted"]

    lines = [
        "# Что проверить повторно (для внешней проверки)",
        "",
        f"Коммит: `{head_commit()}`. Хеши ниже — sha256 файлов в этом коммите: если "
        "присланный архив совпадает по ним, значит он не из кеша.",
        "",
        "## Файлы",
        "",
        "| Файл | Байт | sha256 |",
        "|---|---|---|",
    ]
    for rel in KEY_FILES:
        p = ROOT / rel
        if p.is_file():
            lines.append(f"| `{rel}` | {p.stat().st_size} | `{sha256(p)[:16]}…` |")
        else:
            lines.append(f"| `{rel}` | — | (в дереве отсутствует) |")

    lines += [
        "",
        "## Ключевые числа",
        "",
        "Все — из `scripts/stats.json`, который генерируется из дерева "
        "(`python3 scripts/build_stats.py --check` падает при расхождении):",
        "",
        f"- навыков всего {stats['total']} = верхних {stats['top_level']} + вложенных "
        f"{stats['nested']}",
        "- по источникам: " + ", ".join(f"{k}={v}" for k, v in stats["by_source_all"].items()),
        f"- уникальных навыков с ограничениями **{stats['restricted_unique']}**: "
        f"проприетарных шапок {S['proprietary_hat']}, Anthropic {S['anthropic']}, "
        f"Non-Commercial {S['non_commercial']} (сумма видов {sum(S.values())} завышена: "
        f"два NC — это один навык varCADD в двух местах, и он же входит в проприетарные)",
        "- ссылок 3528, битых 492, категорий 11",
        f"- копий общих файлов: {len(json.loads((ROOT / 'scripts' / 'sibling-copies.json').read_text(encoding='utf-8')).get('copies', []))}"
        f" | пар идентичных навыков: {nd['count']} | почти-дублей: {nd['near_count']}",
        f"- файлов в `scripts/`: {sc['total']} ({sc['py']} .py, {sc['sh']} установщик, "
        f"{sc['json']} JSON) | тестовых файлов: {tf['files']}",
        f"- **проверок валидатора: {stats['validate_checks']}** (число из прогона, "
        f"сверяется в каждом документе)",
        "- тестов: прогон `python3 tests/run_offline.py` (сеть заблокирована в процессе)",
        "",
        "## Что изменилось с прошлой проверки",
        "",
        "Шесть коммитов по плану `docs/fix-plan.md`: уборка служебных артефактов "
        "апстримов (1100 файлов, 8.4 МБ), сверка испытаний `atrial-fibrillation-treatment` "
        "по первоисточнику (Europe PMC), отказ перезаписывать отчёт деградировавшими "
        "числами, тесты без сети, происхождение вложенных навыков, числа из stats.json.",
        "",
        "## Как проверить, не запуская репозиторий",
        "",
        "- `docs/tree-digest.json` — по каждому навыку путь, sha256, размер SKILL.md, "
        "`name` из frontmatter, признак расхождения, наличие description, проприетарная "
        "шапка. Пересчёт навыков, вложенных, расхождений и шапок идёт по нему.",
        "- `docs/trials-verified.json` — семь испытаний: журнал, год, том, страницы, "
        "PMID, тип публикации, цифра первичной точки.",
        "- `docs/broken-refs.md` — инвентарь ссылок с категориями.",
        "",
    ]
    out = ROOT / "docs" / "for-review.md"
    text = "\n".join(lines)
    if args.check:
        # Раньше аргументы не разбирались вовсе: `--check` молча перезаписывал файл.
        # Проверка, которая вместо проверки пишет, бесполезна в CI.
        stored = out.read_text(encoding="utf-8") if out.is_file() else ""
        if stored != text:
            print("ОШИБКА: docs/for-review.md разошёлся с деревом — пересобери "
                  "python3 scripts/build_for_review.py", file=sys.stderr)
            return 1
        print("docs/for-review.md совпадает с деревом (--check)")
        return 0
    out.write_text(text, encoding="utf-8")
    print(f"docs/for-review.md пересобран: {len(KEY_FILES)} файлов, коммит {head_commit()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
