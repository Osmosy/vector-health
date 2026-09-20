#!/usr/bin/env python3
"""Собрать текст карточки Vector Health для сайта экосистемы из stats.json.

Запуск: python3 scripts/build_hub_card.py [--write /path/to/vector-hub/index.html] [--check путь]

Зачем. Карточка на osmosy.github.io живёт в ДРУГОМ репозитории (`vector-hub`),
поэтому валидатор vector-health её не видит: расхождение «1508 скиллов + DICOM»
продержалось до внешнего аудита, потому что сверять было нечем. Скрипт делает текст
из `scripts/stats.json` — тогда число в карточке и число в дереве приходят из одного
места, и повторная сверка не требует памяти.

Без аргументов печатает готовый текст карточки (его можно вставить вручную).
``--check ПУТЬ`` проверяет, что карточка на сайте содержит актуальные числа,
``--write ПУТЬ`` заменяет описание карточки Vector Health.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CARD_RE = re.compile(
    r'(<a class="proj" href="https://github\.com/Osmosy/vector-health">\s*'
    r'<div class="proj-name">Vector Health</div>\s*'
    r'<div class="proj-desc">)(.*?)(</div>)', re.S)


def card_text() -> str:
    s = json.loads((ROOT / "scripts" / "stats.json").read_text(encoding="utf-8"))
    own = len(s.get("own") or [])
    collectors = len([k for k in s["by_source_all"] if k not in ("own", "unknown")])
    return (f"Единая медицинская библиотека навыков: {s['total']} навык "
            f"({collectors} открытые коллекции + {own} собственных), включая таксономию "
            f"RADAR для КТ брюшной полости.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", metavar="ПУТЬ", help="проверить карточку на сайте")
    ap.add_argument("--write", metavar="ПУТЬ", help="обновить карточку на сайте")
    args = ap.parse_args()
    text = card_text()

    if not args.check and not args.write:
        print(text)
        return 0

    target = pathlib.Path(args.check or args.write).expanduser()
    if not target.is_file():
        print(f"ОШИБКА: нет файла {target}", file=sys.stderr)
        return 1
    body = target.read_text(encoding="utf-8")
    m = CARD_RE.search(body)
    if not m:
        print(f"ОШИБКА: в {target} не найдена карточка Vector Health", file=sys.stderr)
        return 1
    current = m.group(2).strip()
    if current == text:
        print(f"карточка Vector Health совпадает со stats.json: {text}")
        return 0
    if args.check:
        print("ОШИБКА: карточка Vector Health разошлась со stats.json", file=sys.stderr)
        print(f"  на сайте: {current[:120]}", file=sys.stderr)
        print(f"  в дереве: {text[:120]}", file=sys.stderr)
        return 1
    target.write_text(body[:m.start(2)] + text + body[m.end(2):], encoding="utf-8")
    print(f"карточка обновлена: {text}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
