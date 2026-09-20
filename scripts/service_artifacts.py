#!/usr/bin/env python3
"""Инвентарь служебных артефактов апстримов внутри навыков.

Запуск: python3 scripts/service_artifacts.py [--json]

Зачем. NOTICE обещал, что служебные результаты работы апстримов (`eval_report_*`,
`*_audit_result*`, `POLISH_CHANGELOG.md`, каталоги `evals/` и `tests/`) при сборке
отрезаны. По факту они в дереве: 278 `eval_report`, 320 `audit_result`,
141 `POLISH_CHANGELOG`, 91 каталог `tests/`. Расхождение документа с деревом —
и заодно лишние десятки мегабайт.

Что делает скрипт: перечисляет такие файлы, группирует по признаку и источнику и
для каждого отвечает на главный вопрос — ССЫЛАЕТСЯ ли на него текст навыка.
Без этого ответа удалять нельзя: файл, на который ссылается `SKILL.md`, — материал
навыка, а не мусор (категория «Путь разошёлся» в инвентаре ссылок указывает именно
на `tests/expected_output/`).
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, "skills")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import refs as refs_mod  # noqa: E402

# Правила совпадают с scripts/sync_upstreams.py — иначе инвентарь и синхронизация
# отвечали бы на вопрос «что лишнее» по-разному
EXCLUDE_PARTS = ("/evals/", "/eval/", "/fixtures/", "/repo/", "/node_modules/", "/.git/",
                 "/tests/", "/test_data/", "/.github/", "/challenges/",
                 "/lint_challenge/", "/analysis_run_challenge/", "/_challenge/")
EXCLUDE_SUFFIX = (".npy", ".xlsx", ".parquet", ".h5ad", ".rds", ".bam", ".zip", ".whl")
EXCLUDE_MARKERS = ("_audit_result", "audit_result", "eval_report", "POLISH_CHANGELOG",
                   "CHANGELOG", "_coverage", "coverage.json", "conftest.py")
# `/docs/` из правил синхронизации здесь НЕ берём: у навыка могут быть свои
# `docs/` с материалом. Отсутствие в инвентаре — решение, а не забывчивость.


REFERENCE_DIRS = ("references", "docs", "assets", "prompts", "examples")


def owner_files(skill_dir: str) -> str:
    """Материал навыка, по которому ищем ссылки: SKILL.md + справочные каталоги.

    Служебные артефакты в этот набор НЕ входят, и это принципиально: иначе
    `POLISH_CHANGELOG.md` ссылается сам на себя («- POLISH_CHANGELOG.md — WRITTEN»)
    и попадает в «на него ссылаются, удалять нельзя». Проверка вырождается в
    «всё ссылается на всё», и решение об удалении принять нельзя.
    """
    parts = []
    for name in ("SKILL.md", "SKILL.MD"):
        p = os.path.join(skill_dir, name)
        if os.path.isfile(p):
            parts.append(open(p, encoding="utf-8", errors="replace").read())
            break
    for sub in REFERENCE_DIRS:
        d = os.path.join(skill_dir, sub)
        if not os.path.isdir(d):
            continue
        for base, dirs, files in os.walk(d):
            dirs[:] = [x for x in dirs if x != "__pycache__"]
            for f in files:
                if f.lower().endswith((".md", ".txt", ".json", ".yml", ".yaml")):
                    try:
                        parts.append(open(os.path.join(base, f), encoding="utf-8",
                                          errors="replace").read())
                    except OSError:
                        pass
    return "\n".join(parts)


def referenced(text: str, rel_to_skill: str) -> bool:
    """Ссылается ли текст навыка на файл (по имени и по пути)."""
    base = os.path.basename(rel_to_skill)
    if base in text:
        return True
    return rel_to_skill.replace(os.sep, "/") in text


def collect() -> dict:
    items = []
    for root, dirs, files in os.walk(SKILLS):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        if "SKILL.md" not in files and "SKILL.MD" not in files:
            continue
        rel_skill = os.path.relpath(root, SKILLS).replace(os.sep, "/")
        text = owner_files(root)
        for f in files:
            full = os.path.join(root, f)
            rel_in_skill = os.path.relpath(full, root).replace(os.sep, "/")
            posix = "/" + rel_in_skill
            kind = None
            if any(m in f for m in EXCLUDE_MARKERS):
                kind = "служебный артефакт по имени"
            elif f.endswith(EXCLUDE_SUFFIX):
                kind = "исключённое расширение"
            elif any(p in posix for p in ("/evals/", "/eval/", "/fixtures/", "/test_data/")):
                kind = "тестовый каталог (evals/fixtures)"
            if kind:
                items.append({"skill": rel_skill, "rel": rel_in_skill, "kind": kind,
                              "bytes": os.path.getsize(full) if os.path.isfile(full) else 0,
                              "referenced": referenced(text, rel_in_skill)})
        # Каталоги из правил исключения — отдельным проходом: файл внутри них может
        # не подпадать ни под маркер имени, ни под расширение, но сам каталог в
        # правилах есть. Первая версия обходила только `tests`/`test_data`, поэтому
        # пять каталогов `evals/` в инвентарь не попадали, а `--prune` их не удалял.
        for d in list(dirs):
            if d in ("tests", "test_data", "evals", "eval", "fixtures", "challenges",
                     "lint_challenge", "analysis_run_challenge", "_challenge"):
                for base, subdirs, subfiles in os.walk(os.path.join(root, d)):
                    subdirs[:] = [x for x in subdirs if x != "__pycache__"]
                    for f in subfiles:
                        full = os.path.join(base, f)
                        rel_in_skill = os.path.relpath(full, root).replace(os.sep, "/")
                        items.append({"skill": rel_skill, "rel": rel_in_skill,
                                      "kind": f"каталог {d}/",
                                      "bytes": os.path.getsize(full),
                                      "referenced": referenced(text, rel_in_skill)})
    # дедупликация: файл мог попасть и по имени, и по каталогу
    uniq: dict[tuple[str, str], dict] = {}
    for it in items:
        uniq.setdefault((it["skill"], it["rel"]), it)
    rows = sorted(uniq.values(), key=lambda x: (x["skill"], x["rel"]))

    by_kind = collections.Counter(r["kind"] for r in rows)
    by_source: collections.Counter = collections.Counter()
    try:
        with open(os.path.join(ROOT, "scripts", "upstream-origin.json"), encoding="utf-8") as f:
            origin = json.load(f).get("origin", {})
    except OSError:
        origin = {}
    for r in rows:
        by_source[origin.get(r["skill"]) or origin.get(r["skill"].split("/")[0]) or "?"] += 1
    return {
        "count": len(rows),
        "bytes": sum(r["bytes"] for r in rows),
        "by_kind": dict(by_kind),
        "by_source": dict(by_source),
        "referenced": sum(1 for r in rows if r["referenced"]),
        "items": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="напечатать машинный отчёт")
    args = ap.parse_args()

    data = collect()
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=1))
        return 0

    print(f"служебных артефактов в дереве: {data['count']} "
          f"({data['bytes'] / 1024 / 1024:.1f} МБ)")
    for k, v in sorted(data["by_kind"].items(), key=lambda x: -x[1]):
        print(f"   {v:5}  {k}")
    print("по источникам:", ", ".join(f"{k}={v}" for k, v in data["by_source"].items()))
    print(f"\nна них ССЫЛАЕТСЯ текст навыка: {data['referenced']} — удалять нельзя без разбора")
    for r in [x for x in data["items"] if x["referenced"]][:15]:
        print(f"   {r['skill']}/{r['rel']}  ({r['kind']})")
    if data["referenced"] > 15:
        print(f"   … и ещё {data['referenced'] - 15}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
