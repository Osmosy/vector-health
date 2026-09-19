#!/usr/bin/env python3
"""Инвентарь ссылок на файлы внутри навыков: что на месте, что бито и почему.

Навыки ссылаются на свои файлы в тексте (`references/x.md`, `scripts/y.py`).
Часть таких ссылок битая — унаследовано от апстримов, где файл лежал в
отрезанном каталоге (`tests/`, `evals/`) или не был закоммичен вовсе. Слепо
«чистить» их нельзя: правится не ссылка в чужом тексте, а знание о том, где файл
есть на самом деле.

Классификация:
  ok          — файл есть локально
  recoverable — файла нет, но он есть у одного из источников (наш пробел,
                закрывается scripts/sync_upstreams.py)
  heavy       — файл есть у источника, но это демо-датасет на мегабайты
  inherited   — файла нет ни у одного источника (дефект апстрима)

Режимы:
  (без флагов)   — напечатать сводку и записать docs/broken-refs.md
  --strict-own   — упасть (exit 1), если битые ссылки есть у СОБСТВЕННЫХ навыков;
                   унаследованные дефекты чужих навыков не валят сборку, иначе CI
                   будет красным всегда и его перестанут читать.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
import urllib.error
import urllib.parse
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, "skills")
REPORT = os.path.join(ROOT, "docs", "broken-refs.md")
ORIGIN = os.path.join(ROOT, "scripts", "upstream-origin.json")

# Собственные навыки: их качество — наша ответственность, унаследованное — нет.
OWN_SKILLS = {"dicom-vlm-analysis", "atrial-fibrillation-treatment"}

SOURCES = {
    "OpenClaw": "FreedomIntelligence/OpenClaw-Medical-Skills",
    "aipoch": "aipoch/medical-research-skills",
    "Aperivue": "Aperivue/medsci-skills",
    "openmed": "maziyarpanahi/openmed",
}

# Разбор ссылок — общий модуль: инвентарь, синхронизация и валидатор должны
# отвечать «какие файлы нужны навыку» одинаково.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import refs as refs_mod  # noqa: E402

REF_RE = refs_mod.REF_RE
HEAVY_SUFFIX = (".gz", ".tgz", ".bz2", ".xz", ".tar", ".7z", ".npy", ".bam", ".h5ad")
HEAVY_MAX = 1_500_000
ORIGIN = os.path.join(ROOT, "scripts", "upstream-origin.json")


def token() -> str:
    try:
        out = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True)
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except OSError:
        pass
    return ""


API_TOKEN = token()


def api(url: str, tries: int = 4):
    for attempt in range(tries):
        req = urllib.request.Request(url, headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "vector-health-broken-refs",
            **(({"Authorization": f"Bearer {API_TOKEN}"} if API_TOKEN else {})),
        })
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode())
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError):
            if attempt == tries - 1:
                raise
            time.sleep(1.5 * (attempt + 1))
    return {}


def upstream_blobs() -> dict[str, dict[str, int]]:
    """{источник: {путь: размер}} по HEAD каждого апстрима."""
    out: dict[str, dict[str, int]] = {}
    for label, repo in SOURCES.items():
        try:
            tree = api(f"https://api.github.com/repos/{repo}/git/trees/HEAD?recursive=1")
        except Exception as e:  # noqa: BLE001 — сеть: помечаем источник недоступным
            print(f"  ! {label}: дерево не получено ({e})", file=sys.stderr)
            out[label] = {}
            continue
        out[label] = {x["path"]: x.get("size", 0)
                      for x in tree.get("tree", []) if x.get("type") == "blob"}
    return out


def scan() -> list[tuple[str, str]]:
    """[(навык, путь, исходная ссылка)] — ссылки, файлов по которым нет.

    Ссылка сначала приводится к пути относительно навыка: апстримы пишут их
    абсолютными (`/Users/.../skills/<name>/scripts/x.py`), от корня репозитория
    (`skills/<name>/scripts/x.py`) или с `./`. Без нормализации живой файл
    попадает в отчёт как битый — и отчёт начинает врать в самую дорогую сторону
    (читатель идёт «чинить» то, что на месте).
    """
    broken: list[tuple[str, str, str]] = []
    for root, dirs, files in os.walk(SKILLS):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        if "SKILL.md" not in files:
            continue
        rel_skill = os.path.relpath(root, SKILLS).replace(os.sep, "/")
        name = rel_skill.rsplit("/", 1)[-1]
        body = open(os.path.join(root, "SKILL.md"), encoding="utf-8", errors="replace").read()
        for raw in refs_mod.find_refs(body):
            rel = refs_mod.to_skill_relative(raw, name) or raw
            rel = os.path.normpath(rel)
            if not os.path.exists(os.path.join(root, rel)):
                broken.append((rel_skill, rel, raw))
    return broken


def classify(broken, trees):
    buckets: dict[str, list[tuple[str, str, str]]] = {
        "placeholder": [], "recoverable": [], "heavy": [], "inherited": []}
    for rel_skill, ref, _raw in broken:
        name = rel_skill.rsplit("/", 1)[-1]
        # «Пример пути в коде» — не ссылка на файл, а форма пути
        # (data/fitness-logs/YYYY-MM/..., scripts/xxx.py). Требовать такой файл
        # нельзя: навык описывает, каким путём пользоваться.
        if refs_mod.is_placeholder(ref):
            buckets["placeholder"].append((rel_skill, ref, "пример пути"))
            continue
        # Ссылка может быть записана абсолютным путём или от корня репозитория:
        # нормализуем её до пути относительно навыка, прежде чем считать битой.
        found = None
        for label, paths in trees.items():
            for up, size in paths.items():
                if up.endswith(f"/{name}/{ref}") or up == f"{name}/{ref}":
                    found = (label, up, size)
                    break
            if found:
                break
        if not found:
            buckets["inherited"].append((rel_skill, ref, ""))
        elif found[1].endswith(HEAVY_SUFFIX) or found[2] > HEAVY_MAX:
            buckets["heavy"].append((rel_skill, ref, found[0]))
        else:
            buckets["recoverable"].append((rel_skill, ref, found[0]))
    return buckets


def load_origin() -> dict[str, str]:
    """Карта происхождения: имя навыка → источник. Нужна, чтобы в инвентаре у
    каждой строки был источник, а не прочерк: читатель должен видеть, чей это
    файл, не открывая второй документ."""
    if not os.path.isfile(ORIGIN):
        return {}
    with open(ORIGIN, encoding="utf-8") as f:
        return json.load(f).get("origin", {})


def write_report(buckets, total_ok: int, origin: dict[str, str]) -> None:
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    lines = [
        "# Ссылки на файлы внутри навыков: инвентарь",
        "",
        f"Сгенерировано `scripts/broken_refs.py`. Ссылок на файлы в дереве: {total_ok + sum(len(v) for v in buckets.values())}; "
        f"на месте: {total_ok}; битых: {sum(len(v) for v in buckets.values())}.",
        "",
        "Битые ссылки — унаследованное свойство апстримов: файл, который навык упоминает, "
        "у них лежал в отрезанном служебном каталоге (`tests/`, `evals/`) либо не был "
        "закоммичен. Правится не ссылка в чужом тексте, а знание о том, где файл есть.",
        "",
        "| Категория | Сколько | Что значит |",
        "|---|---|---|",
        f"| Пример пути в коде | {len(buckets['placeholder'])} | форма пути (`YYYY`, `xxx`, `<file>`), а не файл — требовать его нельзя |",
        f"| Восстановимо | {len(buckets['recoverable'])} | файл есть у источника — закрывается `scripts/sync_upstreams.py` |",
        f"| Тяжёлые данные | {len(buckets['heavy'])} | файл есть, но это демо-датасет на мегабайты — сознательно не тянем |",
        f"| Унаследованное | {len(buckets['inherited'])} | файла нет ни у одного источника — дефект апстрима |",
        "",
    ]
    for key, title in (("placeholder", "Пример пути в коде (не ссылка)"),
                       ("recoverable", "Восстановимо"),
                       ("heavy", "Тяжёлые данные (не тянем)"),
                       ("inherited", "Унаследованное (дефект источника)")):
        items = buckets[key]
        if not items:
            continue
        lines += [f"## {title}", "",
                  "| Навык | Файл | Источник |", "|---|---|---|"]
        for rel_skill, ref, src in sorted(items):
            note = src or origin.get(rel_skill, "") or "—"
            lines.append(f"| `{rel_skill}` | `{ref}` | {note} |")
        lines.append("")
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main() -> int:
    ap = argparse.ArgumentParser(description="Инвентарь ссылок внутри навыков")
    ap.add_argument("--strict-own", action="store_true",
                    help="упасть, если битые ссылки есть у собственных навыков")
    ap.add_argument("--no-report", action="store_true", help="не писать docs/broken-refs.md")
    args = ap.parse_args()

    broken = scan()
    trees = upstream_blobs()
    buckets = classify(broken, trees)

    total_refs = 0
    for root, dirs, files in os.walk(SKILLS):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        if "SKILL.md" not in files:
            continue
        body = open(os.path.join(root, "SKILL.md"), encoding="utf-8", errors="replace").read()
        total_refs += len(set(REF_RE.findall(body)))
    total_ok = total_refs - len(broken)

    print(f"ссылок на файлы: {total_refs} | на месте: {total_ok} | битых: {len(broken)}")
    print(f"  примеры путей: {len(buckets['placeholder'])}"
          f" | восстановимо: {len(buckets['recoverable'])}"
          f" | тяжёлые: {len(buckets['heavy'])}"
          f" | унаследовано: {len(buckets['inherited'])}")
    if not args.no_report:
        write_report(buckets, total_ok, load_origin())
        print(f"  отчёт: {os.path.relpath(REPORT, ROOT)}")

    own_broken = [(s, r) for s, r, _ in buckets["recoverable"] + buckets["heavy"] + buckets["inherited"]
                  if s in OWN_SKILLS]
    if args.strict_own and own_broken:
        print(f"\nБИТЫЕ ССЫЛКИ У СОБСТВЕННЫХ НАВЫКОВ: {len(own_broken)}")
        for s, r in own_broken:
            print(f"  - {s}: {r}")
        return 1
    if args.strict_own:
        print(f"\nOK: у собственных навыков битых ссылок нет "
              f"({', '.join(sorted(OWN_SKILLS))}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
