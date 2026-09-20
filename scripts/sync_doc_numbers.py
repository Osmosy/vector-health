#!/usr/bin/env python3
"""Подставить числа из stats.json в документы. Запуск: python3 scripts/sync_doc_numbers.py [--check]

Зачем. Числа из дерева живут в четырёх документах, и каждое добавление проверки
или скрипта делало их устаревшими. Править четыре файла руками после каждой правки
валидатора — работа, которую человек забудет: именно так «21 проверка» дожила до
внешнего аудита, «26» разъехалось с «27» за один коммит, а состав `scripts/`
устаревал трижды.

Шаблоны задают: файл, регулярное выражение и ключи stats.json для групп в порядке
появления (None — группа не число, оставляем как есть). `--check` ничего не пишет
и падает при расхождении — вызывается в CI. Якоря привязаны к словам
(«проверок», «Скрипты»), чтобы не задеть числа в других значениях.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

PATTERNS = (
    ("README.md",
     r"(validate\.py\s+# валидатор репозитория: )(\d+)( проверок)",
     (None, "validate_checks", None)),
    ("AGENTS.md",
     r"(`python3 scripts/validate\.py` \()(\d+)( проверок)",
     (None, "validate_checks", None)),
    ("INSTALL.md",
     r"(python3 scripts/validate\.py\s+# всё: )(\d+)( проверок)",
     (None, "validate_checks", None)),
    ("agent-description.md",
     r"([Вв]алидатор репозитория — `python3 scripts/validate\.py`: )(\d+)( проверок)",
     (None, "validate_checks", None)),
    # Состав scripts/ — тоже число из дерева: строка устаревала при каждом новом
    # файле, и это случалось уже трижды (12 → 16 → 17 → 19 → 20).
    ("agent-description.md",
     r"(\| Скрипты \| )(\d+)( \(`scripts/`: )(\d+)( \.py, )(\d+)( установщик, )(\d+)( JSON)",
     (None, "scripts.total", None, "scripts.py", None, "scripts.sh", None,
      "scripts.json", None)),
)


def get(stats: dict, dotted: str):
    cur = stats
    for part in dotted.split("."):
        cur = cur[part]
    return cur


def apply(check: bool) -> int:
    stats = json.loads((ROOT / "scripts" / "stats.json").read_text(encoding="utf-8"))
    problems: list[str] = []
    changes: list[str] = []
    for rel, pattern, keys in PATTERNS:
        path = ROOT / rel
        if not path.is_file():
            problems.append(f"{rel}: нет файла")
            continue
        text = path.read_text(encoding="utf-8")
        if not re.search(pattern, text):
            problems.append(f"{rel}: не найден шаблон ({pattern[:50]}…)")
            continue
        # Подстановка идёт по одному совпадению за проход, от ПОСЛЕДНЕЙ числовой
        # группы к первой: замена смещает позиции, и идти слева направо значит
        # испортить следующие группы.
        numbers = [(i, k) for i, k in enumerate(keys, start=1) if k]
        for _ in range(len(numbers)):
            m = re.search(pattern, text)
            if not m:
                break
            replaced = False
            for idx, key in reversed(numbers):
                want = str(get(stats, key))
                got = m.group(idx)
                if got == want or not got.isdigit():
                    continue
                changes.append(f"{rel}: {got} → {want} ({key})")
                if not check:
                    text = text[:m.start(idx)] + want + text[m.end(idx):]
                replaced = True
                break
            if not replaced:
                break
        if not check and changes:
            path.write_text(text, encoding="utf-8")
    if problems:
        for pr in problems:
            print(f"ОШИБКА: {pr}", file=sys.stderr)
        return 1
    for ch in changes:
        print(("ОШИБКА: " if check else "") + ch, file=sys.stderr if check else sys.stdout)
    if check and changes:
        print("запусти: python3 scripts/sync_doc_numbers.py", file=sys.stderr)
        return 1
    print("числа в документах совпадают со stats.json" + (" (--check)" if check else ""))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="не писать: только сверить со stats.json")
    args = ap.parse_args()
    return apply(args.check)


if __name__ == "__main__":
    sys.exit(main())
