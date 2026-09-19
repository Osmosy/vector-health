#!/usr/bin/env python3
"""Сверка: доставленный HTML диаграммы воспроизводится из своей спецификации.

Запуск: python3 scripts/check_diagram.py <delivered.html> <rebuilt.html>

Зачем отдельный скрипт, а не `cmp` в CI: в артефакт вписывается версия
рендерера (`<meta name="generator" content="archify X.Y.Z">`). Локальная сборка
и CI отличаются ровно этой строкой — шесть байт на файл в 700 КБ, — поэтому
побайтовое сравнение валило бы сборку при каждом обновлении archify, ничего не
говоря о содержимом диаграммы. Нормализуем версию и сравниваем всё остальное.

Exit 0 — воспроизводится; exit 1 — есть расхождения (печатаются построчно).
"""
import difflib
import re
import sys

VERSION_RE = re.compile(r'<meta name="generator" content="archify [^"]+">')
NORMALIZED = '<meta name="generator" content="archify VERSION">'


def normalized(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return VERSION_RE.sub(NORMALIZED, f.read())


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 1
    delivered_path, rebuilt_path = sys.argv[1], sys.argv[2]
    try:
        delivered = normalized(delivered_path)
        rebuilt = normalized(rebuilt_path)
    except OSError as e:
        print(f"ОШИБКА: не читается файл — {e}", file=sys.stderr)
        return 1

    if delivered == rebuilt:
        print("HTML воспроизводится из спецификации (версия рендерера нормализована)")
        return 0

    diff = list(difflib.unified_diff(delivered.splitlines(), rebuilt.splitlines(),
                                     fromfile=delivered_path, tofile=rebuilt_path, n=0))
    print(f"РАСХОЖДЕНИЕ: {delivered_path} не воспроизводится из спецификации "
          f"({len([l for l in diff if l[:1] in '+-' and l[:3] not in ('+++', '---')])} строк)", file=sys.stderr)
    for line in diff[:30]:
        print(line, file=sys.stderr)
    print("\nПересобрать: node archify/bin/archify.mjs deliver architecture "
          "docs/vector-health.architecture.json docs/vector-health.architecture.html "
          "--quality showcase", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
