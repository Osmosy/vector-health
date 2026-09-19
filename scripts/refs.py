#!/usr/bin/env python3
"""Разбор ссылок на файлы внутри SKILL.md — общий для синхронизации, инвентаря и валидатора.

Почему отдельный модуль: три скрипта решали одну задачу по-своему, и расхождение
давало разные ответы на вопрос «какие файлы нужны навыку» — синхронизация тянула
один набор, инвентарь ругал другой. Один разбор — одна правда.

Две тонкости, каждая из которых даёт ложные срабатывания:

1. **Путь берётся целиком, а не с середины.** В строке
   `python ooxml/scripts/unpack.py <file>` путь — `ooxml/scripts/unpack.py`.
   Шаблон, ищущий с `scripts/`, возвращает `scripts/unpack.py`, такого файла нет —
   и живой файл попадает в отчёт как «битая ссылка». Поэтому префикс до первого
   известного каталога сохраняется.

2. **Примеры путей в коде — не ссылки.** Конструкции вида
   `data/fitness-logs/YYYY-MM/YYYY-MM-DD.json`, `scripts/xxx.py`,
   `data/output.vcf.gz` описывают ФОРМУ пути, а не конкретный файл. Их нельзя
   требовать: подстановочные метки (`YYYY`, `xxx`, `your_`, `EXAMPLE`, `<...>`)
   и явные слова-заглушки помечаются как пример.
"""
import re

# Каталоги, в которых навыки держат вспомогательные файлы
KNOWN_DIRS = ("references", "scripts", "templates", "assets", "prompts", "data",
              "examples", "checklists", "fixtures", "lib", "bin", "src", "ooxml")

# Ловим путь с префиксом: начинается с известного каталога, либо с цепочки
# сегментов, последний из которых — известный каталог (ooxml/scripts/x.py).
# Расширение может быть составным: output.vcf.gz, data.tar.bz2 — шаблон,
# берущий один сегмент, возвращает `data/output.vcf`, и живой файл выглядит
# отсутствующим.
_DIRS = "|".join(KNOWN_DIRS)
# Ссылка ВВЕРХ от каталога навыка: `../../scripts/x.py`, `../docs/install.md`.
# Такой шаблон нужен отдельно: путь может вести в каталог, которого нет в
# KNOWN_DIRS (`docs/`, `examples/` корня репозитория, `omicverse_guide/`), и
# основной шаблон его пропускает. Пропуск не безобиден: 108 ссылок вверх не
# попадали в инвентарь вовсе — 9 из них ведут на реальные файлы источников, а 64
# битые. Инвентарь, который «не видит» четверть ссылок, обещает полноту, которой
# не даёт.
_UP_RE = r"(?:\.\./)+(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+\.[A-Za-z0-9]{1,6}"
REF_RE = re.compile(
    rf"`?((?:[A-Za-z0-9_.-]+/)*(?:{_DIRS})/[A-Za-z0-9_./-]*?\.[A-Za-z0-9]+(?:\.[A-Za-z0-9]+)*|{_UP_RE})`?"
)

# Маркеры формы пути, а не имени файла
PLACEHOLDER_RE = re.compile(
    r"(YYYY|MM|DD|xxx|XXX|your[_-]|<[^>]+>|\{\{|\}\}|PLACEHOLDER|EXAMPLE)"
)
# Имена-заглушки: «file.py», «output.vcf.gz» описывают форму, а не конкретный файл
PLACEHOLDER_NAMES = {"your_file.py", "file.py", "path/file.py", "output.vcf.gz",
                     "output.g.vcf.gz", "xxx.py", "input.txt"}
# Хвосты, выдающие URL, а не путь в навыке: «seaborn.pydata.org/examples/index.html»
# Домен — это первый сегмент с двумя и более точками и известным TLD.
_TLD = ("org", "com", "net", "io", "ru", "dev", "ai", "edu", "gov", "co", "uk", "de", "cn", "su")
_URLISH_RE = re.compile(rf"^[a-z0-9-]+(?:\.[a-z0-9-]+)+\.(?:{'|'.join(_TLD)})/")


def find_refs(text: str) -> list[str]:
    """Пути файлов, упомянутые в тексте навыка, в порядке появления (без дублей)."""
    seen: dict[str, None] = {}
    for m in REF_RE.finditer(text):
        seen.setdefault(m.group(1), None)
    return list(seen)


def is_placeholder(ref: str) -> bool:
    """True, если это форма пути (пример в коде) или чужой URL, а не файл навыка.

    Три случая, каждый давал ложную «битую ссылку»:
      - метка формы: `data/health-logs/YYYY-MM/YYYY-MM-DD.json`;
      - имя-заглушка из документации: `src/path/file.py`, `examples/example.json`;
      - доменное имя с путём из текста статьи: `seaborn.pydata.org/examples/index.html`.

    При этом `data/emergency-example.json` — НЕ заглушка: это конкретное имя
    файла, и если его нет, ссылка действительно битая.
    """
    if PLACEHOLDER_RE.search(ref):
        return True
    if _URLISH_RE.match(ref) and not ref.endswith((".md", ".py", ".sh", ".yml", ".yaml")):
        return True
    return ref in PLACEHOLDER_NAMES or ref.rsplit("/", 1)[-1] in PLACEHOLDER_NAMES


def to_skill_relative(ref: str, skill_name: str) -> str | None:
    """Привести ссылку к пути относительно каталога навыка.

    Апстримы пишут ссылки как угодно, кроме правильного:
      `/Users/z04030865/.openclaw/workspace/skills/<name>/scripts/main.py`
      `skills/<name>/scripts/main.py`
      `.trae/skills/<name>/scripts/client.py`
      `./data/events.jsonl`
    Файл при этом существует и лежит внутри навыка. Без нормализации такие
    ссылки навсегда остаются «битыми», хотя чинятся одной закачкой.

    Возвращает хвост после имени навыка (или путь без `./`), либо None.
    """
    if not ref:
        return None
    m = re.search(rf"/{re.escape(skill_name)}/(.+)$", ref)
    if m:
        return m.group(1)
    if ref.startswith("./"):
        return ref[2:]
    return None
