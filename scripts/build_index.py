#!/usr/bin/env python3
"""Сгенерировать skills-index.json — каталог навыков (имя + описание) для поиска.

Обход рекурсивный: часть навыков апстримов лежит внутри каталогов-контейнеров
(`spatial-transcriptomics-analysis/bioSkills/…`, `variant-interpretation-acmg/…`),
и плоский обход верхнего уровня терял их из каталога — 28 навыков были в дереве,
но не находились поиском. Поле `path` показывает, где навык лежит.

Запуск: python3 scripts/build_index.py
"""
import datetime
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, "skills")

SKIP_DIRS = {"__pycache__", "node_modules", ".venv", ".git"}


def parse_frontmatter(text):
    # пропустить ведущие HTML-комментарии (COPYRIGHT NOTICE у bio-* навыков)
    t = text.lstrip()
    while t.startswith('<!--'):
        end = t.find('-->')
        if end == -1:
            return {}
        t = t[end + 3:].lstrip()
    m = re.match(r'^---\s*\n(.*?)\n---', t, re.DOTALL)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).splitlines():
        if ':' in line:
            k, _, v = line.partition(':')
            fm[k.strip().lower()] = v.strip().strip('"\'')
    return fm


def first_line(value):
    if not value:
        return ""
    return value.splitlines()[0].strip()


skills = []
errors = []
for root, dirs, files in os.walk(SKILLS):
    dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
    if "SKILL.md" not in files:
        continue
    rel = os.path.relpath(root, SKILLS)
    name = fm_name = None
    with open(os.path.join(root, "SKILL.md"), encoding="utf-8", errors="replace") as f:
        text = f.read()
    fm = parse_frontmatter(text)
    name = fm.get("name") or os.path.basename(root)
    desc = first_line(fm.get("description"))
    if not desc:
        errors.append(rel)
    skills.append({"name": name, "path": rel.replace(os.sep, "/"), "description": desc})

skills.sort(key=lambda s: (s["name"].lower(), s["path"]))
out = {
    "project": "vector-health",
    "generated": datetime.date.today().isoformat(),
    "total": len(skills),
    "note": "path — каталог навыка относительно skills/. Вложенные навыки "
            "(контейнеры вроде spatial-transcriptomics-analysis) включены.",
    "skills": skills,
}
with open(os.path.join(ROOT, "skills-index.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

print(f"skills-index.json: {len(skills)} навыков, без описания: {len(errors)}")
if errors:
    print("без description:", errors[:20])
