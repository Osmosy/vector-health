#!/usr/bin/env python3
"""Разложить рядом с навыком копии общих файлов апстрима, на которые он ссылается.

Запуск: python3 scripts/plant_sibling_files.py [--dry-run|--apply]

Зачем. У AIPOCH и Aperivue один и тот же файл размножен по десяткам навыков
(`references/guide.md`, `scripts/extract_pdf.py`), и навык, который на него
ссылается, часто своей копии не имеет: ссылка ведёт в пустоту, хотя файл лежит в
соседнем навыке библиотеки и он ТОТ ЖЕ (проверено сверкой blob SHA с деревом
апстрима — совпали все 80). Скрипт кладёт копию туда, где на неё ссылаются, чтобы
ссылка стала рабочей.

Почему копия, а не правка ссылки: `SKILL.md` — владельческий файл апстрима, и
переписывать в нём чужой текст нельзя (синхронизация вернёт исходный при
следующем обновлении). Копия же — операция над нашей сборкой, а не над чужой
документацией.

Манифест `scripts/sibling-copies.json` фиксирует, какие копии созданы и откуда
взяты. Валидатор по нему проверяет, что копия побайтово равна файлу владельца, —
иначе «копия» со временем разойдётся с источником и станет отдельной версией.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, "skills")
MANIFEST = os.path.join(ROOT, "scripts", "sibling-copies.json")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import broken_refs as br  # noqa: E402
import refs as refs_mod  # noqa: E402


def sha256(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def upstream_sha_map() -> dict[str, dict[str, str]]:
    """{источник: {путь: blob sha}} по HEAD — тот же приём, что в других скриптах."""
    out: dict[str, dict[str, str]] = {}
    for label, repo in br.SOURCES.items():
        try:
            tree = br.api(f"https://api.github.com/repos/{repo}/git/trees/HEAD?recursive=1")
        except Exception as e:  # noqa: BLE001 — сеть
            print(f"  ! {label}: дерево не получено ({e})", file=sys.stderr)
            out[label] = {}
            continue
        out[label] = {x["path"]: x.get("sha", "") for x in tree.get("tree", [])
                      if x.get("type") == "blob"}
    return out


def is_shared_template(rel: str, owner_label: str, trees: dict[str, dict[str, str]]) -> bool:
    """Это ОБЩИЙ файл апстрима (размножен по навыкам) или уникальный файл владельца?

    Критерий обязателен, и вот почему. У `references/guide.md` в апстриме 17 копий
    и 17 РАЗНЫХ версий — у каждого навыка свой текст под свою задачу. Положить
    чужой `guide.md` рядом с навыком значит вложить в него неверное содержимое:
    файл с именем нужного, но с содержанием другой задачи. Так же у
    `scripts/main.py` (176 разных версий на 184 навыка) и `references/troubleshooting.md`
    (40 копий, 40 версий). Копировать можно только то, что в апстриме действительно
    одно и то же: одну версию файла делят три и более навыков.
    """
    paths = trees.get(owner_label) or {}
    same = [p for p in paths if p.endswith("/" + rel)]
    if not same:
        return False
    from collections import Counter
    versions = Counter(paths[p] for p in same)
    return versions.most_common(1)[0][1] >= 3


def plan(trees: dict[str, dict[str, str]] | None = None) -> list[dict]:
    """Что скопировать: [(навык-получатель, путь, навык-владелец)].

    Считается из дерева, а не из отчёта: отчёт — производный документ, и брать
    из него исходные данные значило бы зависеть от порядка запуска скриптов.
    """
    trees = trees if trees is not None else upstream_sha_map()
    index = br.sibling_index()
    out: list[dict] = []
    skipped: list[tuple[str, str, str, str]] = []
    for root, dirs, files in os.walk(SKILLS):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        if "SKILL.md" not in files:
            continue
        rel_skill = os.path.relpath(root, SKILLS).replace(os.sep, "/")
        body = open(os.path.join(root, "SKILL.md"), encoding="utf-8", errors="replace").read()
        for raw in refs_mod.find_refs(body):
            rel = refs_mod.to_skill_relative(raw, rel_skill.rsplit("/", 1)[-1]) or raw
            rel = os.path.normpath(rel)
            if rel.startswith("..") or rel.startswith("/"):
                continue          # не файл этого навыка — другой случай
            if os.path.exists(os.path.join(root, rel)):
                continue          # на месте
            # ссылка, приведённая от корня/с префиксом, тоже имеет право на копию
            candidates = [rel] + refs_mod.strip_leading_dirs(raw)[1:]
            for cand in candidates:
                owners = [o for o in index.get(cand, []) if o != rel_skill]
                if not owners:
                    continue
                # владелец выбирается по совпадению апстрима: у файла один источник,
                # и копия должна быть его копией, а не одноимённого файла соседа
                src = os.path.join(SKILLS, owners[0], cand)
                if not os.path.isfile(src):
                    continue
                # Общий ли это файл апстрима (иначе — уникальный контент владельца)
                owner_label = (br.load_origin().get(owners[0])
                               or br.load_origin().get(owners[0].split("/")[0]))
                if not owner_label or not is_shared_template(cand, owner_label, trees):
                    skipped.append((rel_skill, cand, owners[0], "уникальный файл владельца"))
                    continue
                # Есть ли у получателя СВОЯ версия файла в апстриме
                rec_label = (br.load_origin().get(rel_skill)
                             or br.load_origin().get(rel_skill.split("/")[0]))
                rec_paths = trees.get(rec_label) or {}
                own_versions = [p for p in rec_paths if p.endswith(f"/{rel_skill}/{cand}")]
                if own_versions:
                    skipped.append((rel_skill, cand, owners[0], "у получателя своя версия"))
                    continue
                out.append({
                    "skill": rel_skill,
                    "rel": cand,
                    "ref": raw,
                    "owner": owners[0],
                    "owner_rel": cand,
                    "sha256": sha256(src),
                    "size": os.path.getsize(src),
                })
                break
            else:
                continue
            break
    # дедупликация: одна и та же пара может встретиться через разные формы ссылки
    uniq: dict[tuple[str, str], dict] = {}
    for item in out:
        uniq.setdefault((item["skill"], item["rel"]), item)
    # пропуски печатаются: критерий должен быть виден, а не молчать
    for s in skipped[:5]:
        print(f"   пропуск: {s[0]}/{s[1]} ← {s[2]} — {s[3]}", file=sys.stderr)
    if len(skipped) > 5:
        print(f"   … пропущено всего {len(skipped)}", file=sys.stderr)
    return sorted(uniq.values(), key=lambda x: (x["skill"], x["rel"]))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true",
                    help="записать копии и обновить манифест (без флага — только показать)")
    args = ap.parse_args()

    items = plan()
    to_write = [i for i in items
                if not os.path.isfile(os.path.join(SKILLS, i["skill"], i["rel"]))]
    print(f"к разложению: {len(to_write)} копий (всего найдено ссылок на файлы соседей: {len(items)})")
    for i in to_write[:12]:
        print(f"   {i['skill']}/{i['rel']}  ←  {i['owner']}  ({i['size']} Б)")
    if len(to_write) > 12:
        print(f"   … и ещё {len(to_write) - 12}")

    if not args.apply:
        print("\n(dry-run: файлы не изменялись)")
        return 0

    written = 0
    for i in to_write:
        src = os.path.join(SKILLS, i["owner"], i["owner_rel"])
        dst = os.path.join(SKILLS, i["skill"], i["rel"])
        if not os.path.isfile(src):
            print(f"   ! владелец не найден: {i['owner']}/{i['owner_rel']}", file=sys.stderr)
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(src, "rb") as f:
            data = f.read()
        with open(dst, "wb") as f:
            f.write(data)
        if sha256(dst) != i["sha256"]:
            print(f"   ! копия не совпала по sha256: {i['skill']}/{i['rel']}", file=sys.stderr)
            continue
        written += 1

    # манифест — единственное место, где сказано, какие копии наши, а какие из
    # апстрима: синхронизация такие файлы не тянет и не удаляет (в апстриме пути
    # `<навык>/<rel>` нет), поэтому без манифеста они потерялись бы при разборе.
    # Защита от обнуления: пустой план не означает, что копий нет. Причина пустого
    # плана — уже разложенные файлы (ссылка перестала быть битой и в отчёт не
    # попадает). Если записать пустой манифест, валидатор потеряет пары
    # «получатель → владелец» и копии станут безымянными файлами неизвестного
    # происхождения.
    if not items and os.path.isfile(MANIFEST):
        with open(MANIFEST, encoding="utf-8") as f:
            old_manifest = json.load(f)
        if old_manifest.get("copies"):
            print(f"\nплан пуст, но манифест содержит {len(old_manifest['copies'])} записей — "
                  f"не перезаписываю (копии уже разложены).", file=sys.stderr)
            return 0

    manifest = {
        "generated_from": "scripts/plant_sibling_files.py — копии файлов апстрима, "
                          "разложенные к навыку, который на них ссылается",
        "note": "Каждая копия побайтово равна файлу владельца (проверяется валидатором). "
                "Файлы апстрима не правятся: копия — операция над сборкой.",
        "count": len(items),
        "copies": items,
    }
    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1, sort_keys=False)
        f.write("\n")
    print(f"\nзаписано копий: {written} | манифест: {os.path.relpath(MANIFEST, ROOT)} ({len(items)} записей)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
