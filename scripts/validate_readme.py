#!/usr/bin/env python3
"""Проверить, что числа и утверждения README не расходятся с деревом.

README заявлял «1508 навыков», тогда как в дереве их было 1537 — расхождение
жило месяцами, потому что ничто его не сверяло. Здесь проверяется:

  1. число навыков в README = число каталогов с SKILL.md (включая вложенные);
  2. разбивка по источникам в таблице = карта происхождения upstream-origin.json;
  3. skills-index.json актуален: total и наличие вложенных навыков;
  4. каждый скрипт, упомянутый в README, существует;
  5. NOTICE.md упоминает все четыре источника и собственный вклад.

Exit 0 = всё сходится, 1 = расхождение (CI валит сборку).

Запуск: python3 scripts/validate_readme.py
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, "skills")

errors: list[str] = []


def read(rel: str) -> str:
    path = os.path.join(ROOT, rel)
    if not os.path.isfile(path):
        errors.append(f"нет файла {rel}")
        return ""
    with open(path, encoding="utf-8") as f:
        return f.read()


def count_skills() -> int:
    """Навык = каталог с SKILL.md, вложенные считаются тоже."""
    total = 0
    for root, dirs, files in os.walk(SKILLS):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        if "SKILL.md" in files:
            total += 1
    return total


readme = read("README.md")
actual = count_skills()

# 1. Общее число навыков.
m = re.search(r"\*\*(\d+)\s+навык", readme)
if not m:
    errors.append("README: не найдено утверждение о числе навыков (**N навыков**)")
elif int(m.group(1)) != actual:
    errors.append(f"README: заявлено {m.group(1)} навыков, в дереве {actual}")

# 2. Разбивка по источникам.
origin_path = os.path.join(ROOT, "scripts", "upstream-origin.json")
if os.path.isfile(origin_path):
    with open(origin_path, encoding="utf-8") as f:
        origin = json.load(f)["origin"]
    by_source: dict[str, int] = {}
    for label in origin.values():
        by_source[label] = by_source.get(label, 0) + 1
    claims = {
        "OpenClaw-Medical-Skills": "OpenClaw",
        "medical-research-skills": "aipoch",
        "maziyarpanahi/openmed": "openmed",
        "Aperivue/medsci-skills": "Aperivue",
    }
    for marker, label in claims.items():
        row = next((l for l in readme.splitlines() if marker in l and l.startswith("|")), "")
        nums = re.findall(r"\|\s*(\d+)\s*\|", row)
        if not nums:
            errors.append(f"README: в строке источника «{marker}» нет числа навыков")
            continue
        claimed, real = int(nums[0]), by_source.get(label, 0)
        # допускаем ±2: у части навыков источник определяется по имени, а не по
        # blob SHA (апстрим менял содержимое), и точное число дрейфует
        if abs(claimed - real) > 2:
            errors.append(f"README: у «{marker}» заявлено {claimed}, карта даёт {real}")
else:
    errors.append("нет scripts/upstream-origin.json — нечем сверять источники")

# 3. Индекс актуален.
idx_path = os.path.join(ROOT, "skills-index.json")
if os.path.isfile(idx_path):
    with open(idx_path, encoding="utf-8") as f:
        idx = json.load(f)
    if idx.get("total") != actual:
        errors.append(f"skills-index.json: total={idx.get('total')}, в дереве {actual} "
                      f"— перегенерируй scripts/build_index.py")
    nested_idx = sum(1 for s in idx.get("skills", []) if "/" in str(s.get("path", "")))
    # Вложенный = путь внутри каталога навыка, а не прямо в skills/. Считать надо
    # именно относительную глубину: «skills/<name>/SKILL.md» — верхний уровень.
    nested_real = sum(1 for root, dirs, files in os.walk(SKILLS)
                      if "SKILL.md" in files and os.sep in os.path.relpath(root, SKILLS))
    if nested_idx < nested_real:
        errors.append(f"skills-index.json: вложенных навыков {nested_idx}, "
                      f"в дереве {nested_real} — плоский обход их теряет")
else:
    errors.append("нет skills-index.json")

# 4. Скрипты, упомянутые в README, существуют.
for script in sorted(set(re.findall(r"scripts/([A-Za-z0-9_]+\.py)", readme))):
    if not os.path.isfile(os.path.join(ROOT, "scripts", script)):
        errors.append(f"README: ссылка на несуществующий scripts/{script}")

# 5. NOTICE перечисляет источники и собственный вклад.
notice = read("NOTICE.md")
for needle in ("OpenClaw-Medical-Skills", "aipoch", "openmed", "Aperivue",
               "Собственный вклад", "sync_upstreams.py"):
    if needle not in notice:
        errors.append(f"NOTICE.md: не упомянуто «{needle}»")

if errors:
    print(f"ПРОБЛЕМ: {len(errors)}")
    for e in errors:
        print("  -", e)
    sys.exit(1)
print(f"OK: README сходится с деревом ({actual} навыков), индекс актуален, NOTICE полон.")
