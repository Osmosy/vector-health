#!/usr/bin/env python3
"""Сгенерировать skills-index.json — каталог навыков (имя + описание) для поиска."""
import json
import os
import re
import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, "skills")

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
for d in sorted(os.listdir(SKILLS)):
    p = os.path.join(SKILLS, d)
    smd = os.path.join(p, "SKILL.md")
    if not os.path.isdir(p) or not os.path.isfile(smd):
        continue
    with open(smd, encoding="utf-8", errors="replace") as f:
        text = f.read()
    fm = parse_frontmatter(text)
    name = fm.get("name") or d
    desc = first_line(fm.get("description"))
    if not desc:
        errors.append(d)
    skills.append({"name": name, "description": desc})

skills.sort(key=lambda s: s["name"].lower())
out = {
    "project": "vector-health",
    "generated": datetime.date.today().isoformat(),
    "total": len(skills),
    "skills": skills,
}
with open(os.path.join(ROOT, "skills-index.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

print(f"skills-index.json: {len(skills)} навыков, без описания: {len(errors)}")
if errors:
    print("без description:", errors[:20])
