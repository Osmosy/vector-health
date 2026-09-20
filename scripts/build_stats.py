#!/usr/bin/env python3
"""Единый источник чисел для документов: scripts/stats.json.

Запуск: python3 scripts/build_stats.py [--check]

Почему файл генерируется, а не пишется руками: он был рукописным, и в нём
разошлись числа — `by_source_top.OpenClaw` показывал 779 при фактических 777
(сумма по источникам не сходилась с `top_level`), а число скриптов устаревало
при каждом добавлении файла. Валидатор эти поля не сверял, поэтому расхождение
дожило до чтения документа человеком. Числа считаются из дерева; ручная правка
бессмысленна — при следующем прогоне файл перезаписывается.

--check ничего не пишет и падает, если файл на диске разошёлся с деревом.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
OWN_DEFAULT = ("abdominal-ct-findings", "atrial-fibrillation-treatment", "dicom-vlm-analysis")


def all_skills() -> list[pathlib.Path]:
    """Все каталоги с SKILL.md, рекурсивно, как относительные пути от skills/."""
    found = []
    for dirpath, dirnames, filenames in os.walk(SKILLS):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        if "SKILL.md" in filenames or "SKILL.MD" in filenames:
            found.append(pathlib.Path(dirpath).relative_to(SKILLS))
    return sorted(found)


def origin_map() -> dict[str, str]:
    with open(ROOT / "scripts" / "upstream-origin.json", encoding="utf-8") as f:
        return json.load(f)["origin"]


def restricted_counts() -> tuple[dict[str, int], dict[str, list[str]]]:
    """Ограниченные лицензии — считаются из дерева, а не из пересказа в документах.

    Три разных ограничения, три разных признака:

    - `proprietary_hat` — проприетарная шапка В ТЕКСТЕ SKILL.md (OpenClaw держит
      «proprietary and confidential … All Rights Reserved» при MIT-бейдже в README);
    - `anthropic` — файл `LICENSE.txt` с «© 2025 Anthropic, PBC» рядом с навыком
      (офисные навыки: docx/pdf/pptx/xlsx и их варианты). Считать их по упоминанию
      слова «Anthropic» в тексте нельзя: оно встречается и в описаниях;
    - `non_commercial` — поле `license: Non-Commercial` в frontmatter SKILL.md.
      Именно поле, а не слово: «non-commercial» как термин встречается в методичках
      о лицензиях (`check-reporting`, `publish-skill`) и в предупреждениях о весах
      модели, и это не навыки под NC.
    """
    skills = all_skills()
    proprietary, anthropic, non_commercial = [], [], []

    for rel in skills:
        skill_md = SKILLS / rel / "SKILL.md"
        if not skill_md.is_file():
            skill_md = SKILLS / rel / "SKILL.MD"
        try:
            text = skill_md.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        low = text.lower()
        if "proprietary and confidential" in low and "all rights reserved" in low:
            proprietary.append(str(rel))

        # поле frontmatter: `license: Non-Commercial` (регистр и кавычки не важны)
        for line in text.splitlines():
            m = re.match(r"\s*license\s*:\s*(.+)", line, re.I)
            if m and re.search(r"non-?commercial", m.group(1), re.I):
                non_commercial.append(str(rel))
                break

        # файл лицензии Anthropic лежит рядом с навыком или в его каталоге
        for candidate in (SKILLS / rel / "LICENSE.txt",):
            if candidate.is_file() and "anthropic" in candidate.read_text(
                    encoding="utf-8", errors="replace").lower():
                anthropic.append(str(rel))
                break

    lists = {
        "proprietary_hat": sorted(proprietary),
        "anthropic": sorted(anthropic),
        "non_commercial": sorted(non_commercial),
    }
    counts = {kind: len(names) for kind, names in lists.items()}
    return counts, lists


def restricted_by_source(lists: dict[str, list[str]], origin: dict[str, str]) -> dict[str, dict[str, int]]:
    """Разбивка ограниченных навыков по источникам.

    Факт с практическим смыслом: 308 проприетарных шапок — все из OpenClaw, то
    есть митигация одна (не считать их MIT), а не 308 разных историй. Вложенные
    навыки относятся к источнику своего каталога-контейнера.
    """
    out: dict[str, dict[str, int]] = {}
    for kind, names in lists.items():
        per: collections.Counter = collections.Counter()
        for name in names:
            parts = name.split("/")
            src = origin.get(name) or origin.get(parts[0]) or "unknown"
            per[src] += 1
        out[kind] = dict(sorted(per.items(), key=lambda kv: -kv[1]))
    return out


def scripts_counts() -> dict[str, int]:
    """Состав каталога scripts/ — числа для документов и диаграммы."""
    py = sh = js = json_files = 0
    for dirpath, dirnames, filenames in os.walk(ROOT / "scripts"):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for fn in filenames:
            if fn.endswith(".py"):
                py += 1
            elif fn.endswith(".sh"):
                sh += 1
            elif fn.endswith(".js") or fn.endswith(".mjs"):
                js += 1
            elif fn.endswith(".json") and fn != "stats.json":
                json_files += 1
    return {"py": py, "sh": sh, "js": js, "json": json_files,
            "total": py + sh + js + json_files}


def validate_checks() -> int:
    """Число проверок валидатора — из фактического прогона.

    Почему прогон, а не подсчёт по исходнику: статический подсчёт давал 25 против
    26 фактических (часть проверок даёт две записи) — то есть документ снова
    называл бы число, которого нет. Вызов идёт с переменной VH_IN_STATS: валидатор
    по ней пропускает свою проверку stats.json, иначе получается цикл
    (validate -> build_stats --check -> validate).
    """
    import os
    proc = subprocess.run([sys.executable, "-B", str(ROOT / "scripts" / "validate.py")],
                          cwd=ROOT, capture_output=True, text=True,
                          env={**os.environ, "VH_IN_STATS": "1"})
    out = (proc.stdout or "") + (proc.stderr or "")
    m = re.search(r"ПРОВЕРОК: (\d+)", out)
    return int(m.group(1)) if m else 0


def tests_counts() -> dict[str, int]:
    """Тестовые файлы: сколько их и сколько проверок в основном наборе."""
    tests_dir = ROOT / "tests"
    files = sorted(f.name for f in tests_dir.iterdir() if f.is_file()) if tests_dir.is_dir() else []
    # Число проверок тестов НЕ считается здесь: статический подсчёт вызовов даёт
    # 155 против 213 фактических, потому что часть тестов выполняется в циклах
    # (по семи испытаниям, по категориям). Называть в документе число, которого
    # нет, — ровно тот дефект, который эта работа и чинит, поэтому в документах
    # называется состав файлов, а число прогоняется в CI.
    return {"files": len(files), "names": files}


def build() -> dict:
    skills = all_skills()
    origin = origin_map()

    def source_of(rel: pathlib.Path) -> str:
        for key in (str(rel), rel.parts[0]):
            if key in origin:
                return origin[key]
        return "unknown"

    top = collections.Counter()
    everything = collections.Counter()
    for rel in skills:
        src = source_of(rel)
        everything[src] += 1
        if len(rel.parts) == 1:
            top[src] += 1

    own = sorted(k for k, v in origin.items() if v == "own" and (SKILLS / k).is_dir())
    if not own:
        own = sorted(OWN_DEFAULT)

    restricted_by_kind, restricted_lists = restricted_counts()

    # Уникальные навыки с ограничениями и пересечения между видами. Сумма видов
    # (319) уникальным навыкам не равна и вводила в заблуждение: два «Non-Commercial»
    # навыка — это ОДИН навык varCADD в двух местах (одинаковый blob sha), и он же
    # несёт проприетарную шапку. Документ, складывающий 308 + 9 + 2, обещает 319
    # ограниченных навыков, которых в дереве нет.
    _sets = {k: set(v) for k, v in restricted_lists.items()}
    _unique: set[str] = set().union(*_sets.values()) if _sets else set()
    overlaps = []
    _keys = sorted(_sets)
    for i, a in enumerate(_keys):
        for b in _keys[i + 1:]:
            inter = sorted(_sets[a] & _sets[b])
            if inter:
                overlaps.append({"kinds": [a, b], "skills": inter,
                                 "note": "сумма видов считает такой навык дважды"})
    # varCADD: два пути, один навык — показываем это явно, а не только числом
    nc_dupes = []
    if len(_sets.get("non_commercial", ())) == 2:
        import hashlib
        shas = {}
        for name in _sets["non_commercial"]:
            f = SKILLS / name / "SKILL.md"
            if f.is_file():
                shas.setdefault(hashlib.sha256(f.read_bytes()).hexdigest(), []).append(name)
        for sha, names in shas.items():
            if len(names) == 2:
                nc_dupes.append({"sha256": sha, "paths": sorted(names),
                                 "note": "один навык в двух местах: «два NC-навыка» — "
                                         "это он же, а не два разных"})

    return {
        "generated_from": "дерево skills/ + scripts/upstream-origin.json + scripts/restricted-licenses.json",
        "generated_by": "scripts/build_stats.py — файл не править руками",
        "total": len(skills),
        "top_level": sum(top.values()),
        "nested": len(skills) - sum(top.values()),
        "by_source_top": dict(sorted(top.items(), key=lambda kv: -kv[1])),
        "by_source_all": dict(sorted(everything.items(), key=lambda kv: -kv[1])),
        "unknown_source": everything.get("unknown", 0),
        "own": own,
        "restricted": restricted_by_kind,
        "restricted_skills": restricted_lists,
        "restricted_unique": len(_unique),
        "restricted_overlaps": overlaps,
        "non_commercial_same_skill": nc_dupes,
        "restricted_by_source": restricted_by_source(restricted_lists, origin),
        "scripts": scripts_counts(),
        "validate_checks": validate_checks(),
        "tests": tests_counts(),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="не писать файл, только сверить с деревом")
    args = ap.parse_args()

    stats = build()
    path = ROOT / "scripts" / "stats.json"
    text = json.dumps(stats, ensure_ascii=False, indent=1, sort_keys=False) + "\n"

    if args.check:
        if not path.is_file():
            print("ОШИБКА: нет scripts/stats.json", flush=True)
            return 1
        stored = path.read_text(encoding="utf-8")
        if stored != text:
            print("ОШИБКА: scripts/stats.json разошёлся с деревом — пересобери "
                  "scripts/build_stats.py", flush=True)
            try:
                a, b = json.loads(stored), stats
                for key in sorted(set(a) | set(b)):
                    if a.get(key) != b.get(key):
                        print(f"  {key}: в файле {a.get(key)!r} → в дереве {b.get(key)!r}", flush=True)
            except json.JSONDecodeError as e:
                print(f"  файл не парсится: {e}", flush=True)
            return 1
        print("stats.json соответствует дереву", flush=True)
        return 0

    path.write_text(text, encoding="utf-8")
    print(f"stats.json пересобран: {stats['total']} навыков "
          f"({stats['top_level']} верхних + {stats['nested']} вложенных), "
          f"источники: {', '.join(f'{k}={v}' for k, v in stats['by_source_all'].items())}", flush=True)
    if stats["unknown_source"]:
        print(f"ВНИМАНИЕ: {stats['unknown_source']} навыков без источника в карте происхождения",
              flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

