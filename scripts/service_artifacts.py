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

# Правила берутся из общего модуля: единственная копия определения служебного
# артефакта. Раньше здесь были свои копии констант, и они разошлись с
# синхронизацией на 24 файла (синхронизация помечала 173, инвентарь видел 149):
# обход ограничивался корнем навыка и именованными служебными каталогами, а
# служебный файл лежит и в `references/`, и в `scripts/`, и в `database/`.
import exclusions as excl  # noqa: E402
# Тяжёлые архивы: то же правило, что в синхронизации
HEAVY_SUFFIX = (".gz", ".tgz", ".bz2", ".xz", ".tar", ".7z")
# Каталоги-результаты прогонов: внутри них файлы сохраняются только через
# allowlist с причиной, даже если имя файла упомянуто в тексте навыка.
RESULT_DIR_RE = __import__("re").compile(r"/tests/(?:audit|verify|output|case|run|legacy)[^/]*/")


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
    """Ссылается ли текст навыка на файл — по ПУТИ, а не по одному имени.

    Правило по имени было слишком широким и сохраняло результаты прогонов: у
    `tf-target-gene-regulatory-network` так остались 18 файлов в каталогах
    `tests/audit_v2_case_*/` (`tf_network.xlsx`, `tf.Rdata`, `session_info.txt`) —
    потому что имя выходного файла упомянуто в `SKILL.md`, а сами каталоги
    `audit_*`/`verify_*` — это следы прогонов, а не материал.

    Теперь так:
    - путь (с `tests/`) встречается в тексте — файл материал, сохраняется;
    - файл лежит в каталоге-результате (`audit_*`, `verify_*`, `output_*`,
      `case_*`, `run_*`) — сохраняется только через allowlist с причиной;
    - иначе — по имени, но лишь для `tests/data/` и `tests/expected_output/`:
      там лежат входные данные, и на них ссылаются именно по имени файла.
    """
    rel = rel_to_skill.replace(os.sep, "/")
    if rel in text:
        return True
    if RESULT_DIR_RE.search(rel):
        return False          # только allowlist
    base = os.path.basename(rel)
    if not base:
        return False
    if "/tests/data/" in "/" + rel or "/tests/expected_output/" in "/" + rel:
        return base in text
    return base in text


def collect() -> dict:
    """Все файлы под skills/, которые правила считают служебными.

    Обход РЕКУРСИВНЫЙ по каждому навыку: служебный файл лежит не только в корне,
    но и в `references/`, `scripts/`, `database/`, `assets/`. Пока обход
    ограничивался корнем и именованными служебными каталогами, инвентарь не видел
    24 файла из 173, которые помечает синхронизация, — в том числе
    `gsea/assets/ssGSEA.rds` и `*_audit_result.json` в `references/`.

    Вложенный навык (каталог со своим `SKILL.md`) относится к самому себе, а не к
    контейнеру: у него свои правила и свой материал.
    """
    items: list[dict] = []
    # Каталоги навыков: и верхние, и вложенные (со своим SKILL.md)
    skill_dirs: list[str] = []
    for root, dirs, files in os.walk(SKILLS):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        if "SKILL.md" in files or "SKILL.MD" in files:
            skill_dirs.append(root)
    skill_set = set(skill_dirs)

    def nearest_skill(path: str) -> str:
        """Ближайший каталог навыка для файла (вложенный выигрывает у контейнера)."""
        cur = path
        while len(cur) > len(SKILLS):
            if cur in skill_set:
                return cur
            cur = os.path.dirname(cur)
        return path

    for skill_root in skill_dirs:
        rel_skill = os.path.relpath(skill_root, SKILLS).replace(os.sep, "/")
        text = owner_files(skill_root)
        for base, dirs, files in os.walk(skill_root):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            # не заходим во вложенный навык дважды: он обойдётся сам
            dirs[:] = [d for d in dirs
                       if os.path.join(base, d) not in skill_set
                       and nearest_skill(os.path.join(base, d)) == skill_root]
            for f in files:
                full = os.path.join(base, f)
                if nearest_skill(base) != skill_root:
                    continue
                rel_in_skill = os.path.relpath(full, skill_root).replace(os.sep, "/")
                kind = excl.classify(rel_in_skill)
                if not kind:
                    # Тяжёлые архивы синхронизация тоже не тянет (HEAVY_SUFFIX):
                    # файл в апстриме есть и на него ссылаются, но это демо-данные
                    # на мегабайты. В инвентаре они видны с отдельным видом, иначе
                    # счёт синхронизации и инвентаря расходится на 2 файла.
                    if rel_in_skill.endswith(HEAVY_SUFFIX):
                        kind = "тяжёлый архив"
                    else:
                        continue
                items.append({"skill": rel_skill, "rel": rel_in_skill, "kind": kind,
                              "bytes": os.path.getsize(full) if os.path.isfile(full) else 0,
                              "referenced": referenced(text, rel_in_skill)})
    # дедупликация: файл мог попасть и по имени, и по каталогу
    uniq: dict[tuple[str, str], dict] = {}
    for it in items:
        uniq.setdefault((it["skill"], it["rel"]), it)
    rows = sorted(uniq.values(), key=lambda x: (x["skill"], x["rel"]))
    by_kind: collections.Counter = collections.Counter(r["kind"] for r in rows)
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
