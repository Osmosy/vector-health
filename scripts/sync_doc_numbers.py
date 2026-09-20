#!/usr/bin/env python3
"""Подставить числа из stats.json в документы. Запуск: python3 scripts/sync_doc_numbers.py [--check]

Зачем. Число проверок валидатора живёт в четырёх документах, и каждая новая
проверка делает их устаревшими. Править четыре файла руками после каждой правки
валидатора — работа, которую человек забудет: именно так «21 проверка» дожила до
проверки внешним аудитом, а «26» разъехалось с «27» на один коммит.

Скрипт заменяет числа по ЯВНЫМ шаблонам (какой файл, что искать, на что менять),
а `--check` ничего не пишет и падает при расхождении — его вызывает валидатор.
Шаблоны с якорем на слово «проверк», чтобы не задеть числа в других значениях.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# (файл, шаблон, что подставляется вместо группы 1)
PATTERNS = (
    ("README.md",
     r"validate\.py\s+# валидатор репозитория: (\d+) проверок", "checks"),
    ("AGENTS.md",
     r"`python3 scripts/validate\.py` \((\d+) проверок", "checks"),
    ("INSTALL.md",
     r"python3 scripts/validate\.py\s+# всё: (\d+) проверок", "checks"),
    ("agent-description.md",
     r"[Вв]алидатор репозитория — `python3 scripts/validate\.py`: (\d+) проверок", "checks"),
)


def stats() -> dict:
    return json.loads((ROOT / "scripts" / "stats.json").read_text(encoding="utf-8"))


def apply(check: bool) -> int:
    s = stats()
    values = {"checks": s["validate_checks"], "scripts": s["scripts"]["total"]}
    problems = []
    for rel, pattern, key in PATTERNS:
        path = ROOT / rel
        if not path.is_file():
            problems.append(f"{rel}: нет файла")
            continue
        text = path.read_text(encoding="utf-8")
        want = str(values[key])
        m = re.search(pattern, text)
        if not m:
            problems.append(f"{rel}: не найден шаблон ({pattern[:45]}…)")
            continue
        if m.group(1) == want:
            continue
        if check:
            problems.append(f"{rel}: названо {m.group(1)}, а в stats.json {want}")
        else:
            text = text[:m.start(1)] + want + text[m.end(1):]
            path.write_text(text, encoding="utf-8")
            print(f"{rel}: {m.group(1)} → {want}")
    if problems:
        for p in problems:
            print(f"ОШИБКА: {p}", file=sys.stderr)
        print("запусти: python3 scripts/sync_doc_numbers.py", file=sys.stderr)
        return 1
    print("числа в документах совпадают со stats.json" + (" (--check)" if check else ""))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="не писать: только сверить с stats.json")
    args = ap.parse_args()
    return apply(args.check)


if __name__ == "__main__":
    sys.exit(main())
