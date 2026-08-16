#!/usr/bin/env python3
"""Валидация навыков + скан секретов/PII перед публикацией.

Проверяет (fail):
  1. каждый skills/*/SKILL.md имеет frontmatter с name и description;
  2. отсутствуют реальные секреты (API-ключи, токены, приватные ключи);
  3. отсутствуют крупные файлы (>5 МБ).

Предупреждает (warn, не fail):
  - name в frontmatter не совпадает с именем каталога (частые кейс-нюансы источников).

Exit 0 = чисто (или только предупреждения), 1 = есть проблемы.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, "skills")

SECRET_PATTERNS = [
    re.compile(r'sk-[A-Za-z0-9]{20,}'),
    re.compile(r'ghp_[A-Za-z0-9]{20,}'),
    re.compile(r'AKIA[0-9A-Z]{16}'),
    re.compile(r'-----BEGIN (RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----'),
    re.compile(r'xox[baprs]-[A-Za-z0-9-]{10,}'),
    re.compile(r'AIza[0-9A-Za-z_-]{30,}'),
]
ALLOWED_PLACEHOLDERS = re.compile(r'ghp_ab\.{3}\d+')

MAX_FILE = 5 * 1024 * 1024

problems = []
warnings = []


def parse_frontmatter(text):
    # пропустить ведущие HTML-комментарии (COPYRIGHT NOTICE у bio-* навыков)
    t = text.lstrip()
    while t.startswith('<!--'):
        end = t.find('-->')
        if end == -1:
            return None
        t = t[end + 3:].lstrip()
    m = re.match(r'^---\s*\n(.*?)\n---', t, re.DOTALL)
    if not m:
        return None
    fm = {}
    for line in m.group(1).splitlines():
        if ':' in line:
            k, _, v = line.partition(':')
            fm[k.strip().lower()] = v.strip()
    return fm


n = 0
for d in sorted(os.listdir(SKILLS)):
    p = os.path.join(SKILLS, d)
    smd = os.path.join(p, "SKILL.md")
    if not os.path.isdir(p):
        continue
    if not os.path.isfile(smd):
        problems.append(f"{d}: нет SKILL.md")
        continue
    n += 1
    with open(smd, encoding="utf-8", errors="replace") as f:
        text = f.read()
    fm = parse_frontmatter(text)
    if fm is None:
        problems.append(f"{d}: нет/битый frontmatter")
        continue
    if not fm.get("name"):
        problems.append(f"{d}: нет name")
    if not fm.get("description"):
        problems.append(f"{d}: нет description")
    if fm.get("name") and fm.get("name").lower() != d.lower():
        warnings.append(f"{d}: name={fm['name']} != каталог (кейс-нюанс источника)")


for root, dirs, files in os.walk(SKILLS):
    dirs[:] = [x for x in dirs if x not in ("node_modules", ".venv", "__pycache__")]
    for fn in files:
        fp = os.path.join(root, fn)
        try:
            sz = os.path.getsize(fp)
        except OSError:
            continue
        if sz > MAX_FILE:
            problems.append(f"{os.path.relpath(fp, ROOT)}: >5МБ ({sz // 1024 // 1024}МБ)")
            continue
        if fn.endswith(('.md', '.py', '.sh', '.json', '.yml', '.yaml', '.txt', '.toml', '.tex')):
            # тест-фикстуры (/tests/, /test_data/, /fixtures/) намеренно содержат фейковые
            # секреты для проверки сканеров — их не флагаем.
            rel = os.path.relpath(fp, ROOT)
            if '/tests/' in rel or '/test_data/' in rel or '/fixtures/' in rel:
                continue
            with open(fp, encoding="utf-8", errors="ignore") as f:
                content = f.read()
            for pat in SECRET_PATTERNS:
                for m in pat.finditer(content):
                    hit = m.group(0)
                    if ALLOWED_PLACEHOLDERS.search(hit):
                        continue
                    problems.append(f"{os.path.relpath(fp, ROOT)}: секрет {hit[:8]}...")


print(f"Проверено навыков: {n}")
if warnings:
    print(f"Предупреждения (не критично): {len(warnings)}")
    for w in warnings[:20]:
        print("  ~", w)
if problems:
    print(f"ПРОБЛЕМ: {len(problems)}")
    for p in problems[:100]:
        print("  -", p)
    sys.exit(1)
print("OK: frontmatter валиден, секретов и крупных файлов нет.")
