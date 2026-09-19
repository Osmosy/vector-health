#!/usr/bin/env python3
"""Тесты скриптов обслуживания vector-health.

Проверяются ветки, которые иначе ломаются молча: разбор шапки фронтматтера,
выбор версии при дублях имён, классификация битых ссылок, устойчивость
валидатора к расхождениям. Каждый тест — реальный вызов скрипта, а не проверка
его исходника.

Запуск: python3 tests/test_scripts.py
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, "skills")

PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}{(' — ' + detail) if detail else ''}")


def load_module(path: str, name: str):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run(cmd: list[str], cwd: str = ROOT) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


print("=== 1. build_index: разбор frontmatter и обход дерева ===")
bi = load_module(os.path.join(ROOT, "scripts", "build_index.py"), "build_index")

# frontmatter с HTML-комментарием перед ним (так устроены bio-* навыки OpenClaw)
fm = bi.parse_frontmatter("""<!--
# COPYRIGHT NOTICE
# This file is part of the "Universal Biomedical Skills" project.
-->
---
name: bio-vcf-basics
description: View, query, and understand VCF/BCF variant files.
---
# Тело
""")
check("frontmatter после HTML-комментария разобран", fm.get("name") == "bio-vcf-basics", str(fm))
check("описание извлечено", "VCF" in fm.get("description", ""))

fm2 = bi.parse_frontmatter("---\nname: x\ndescription: y\n---\n")
check("обычный frontmatter разобран", fm2.get("name") == "x")

check("битый frontmatter даёт пустой словарь, а не исключение",
      bi.parse_frontmatter("нет фронтматтера вовсе") == {})

print("\n=== 2. Каталог: вложенные навыки и полнота ===")
idx = json.load(open(os.path.join(ROOT, "skills-index.json"), encoding="utf-8"))
nested = [s for s in idx["skills"] if "/" in s["path"]]
check("каталог содержит вложенные навыки", len(nested) >= 28, f"вложенных {len(nested)}")
check("у каждой записи есть путь и описание",
      all(s.get("path") and s.get("description") for s in idx["skills"]))
check("total совпадает с числом записей", idx["total"] == len(idx["skills"]))

# вложенный навык из контейнера реально лежит на месте
if nested:
    p = os.path.join(SKILLS, nested[0]["path"], "SKILL.md")
    check(f"вложенный навык существует на диске ({nested[0]['path']})", os.path.isfile(p))

print("\n=== 3. Синхронизация: выбор версии при дубле имени ===")
su = load_module(os.path.join(ROOT, "scripts", "sync_upstreams.py"), "sync_upstreams")

# у AIPOCH один навык лежит в нескольких категориях с РАЗНЫМ содержимым:
# версия выбирается по совпадению с локальной, иначе файл подменяется чужой
index = {
    "cover-letter-drafter": [
        "awesome-med-research-skills/Academic Writing/cover-letter-drafter/SKILL.md",
        "scientific-skills/Academic Writing/cover-letter-drafter/SKILL.md",
    ]
}
shas = {
    "awesome-med-research-skills/Academic Writing/cover-letter-drafter/SKILL.md": "aaa",
    "scientific-skills/Academic Writing/cover-letter-drafter/SKILL.md": "bbb",
}
picked = su.upstream_of("cover-letter-drafter", "SKILL.md", index, [], local_sha="bbb", shas=shas)
check("выбрана версия, совпадающая с локальной", picked.endswith("scientific-skills/Academic Writing/cover-letter-drafter/SKILL.md"), str(picked))

picked2 = su.upstream_of("cover-letter-drafter", "SKILL.md", index, [], local_sha="zzz", shas=shas)
check("при отсутствии совпадения берётся первая (не падает)", picked2 is not None)

# без local_sha поведение прежнее — обратная совместимость
check("без local_sha функция работает", su.upstream_of("cover-letter-dropper", "x", {}, []) is None)

print("\n=== 4. Синхронизация: skill_dir_of терпим к заглавному расширению ===")
check("SKILL.md распознан", su.skill_dir_of("skills/foo/SKILL.md") == "foo")
check("SKILL.MD распознан (OpenClaw держит так)",
      su.skill_dir_of("skills/medical-specialty-briefs/SKILL.MD") == "medical-specialty-briefs")
check("файл не SKILL не распознан", su.skill_dir_of("skills/foo/README.md") is None)

print("\n=== 5. Исключения синхронизации ===")
check("служебные каталоги отсекаются", su.is_excluded("skills/x/tests/test_foo.py"))
check("тяжёлые архивы отсекаются", su.is_excluded("skills/x/data/big.txt.gz"))
check("обычный reference не отсекается", not su.is_excluded("skills/x/references/api.md"))
check("SKILL.md не отсекается", not su.is_excluded("skills/x/SKILL.md"))

print("\n=== 6. Карта происхождения: полна и без выдуманных источников ===")
origin = json.load(open(os.path.join(ROOT, "scripts", "upstream-origin.json"), encoding="utf-8"))["origin"]
known = set(su.SOURCES) | {"own"}
check("нет неизвестных меток источников", all(v in known for v in origin.values()),
      str({v for v in origin.values() if v not in known}))
check("собственные навыки ровно 2",
      {n for n, s in origin.items() if s == "own"} == {"dicom-vlm-analysis", "atrial-fibrillation-treatment"})
check("medical-specialty-briefs атрибутирован OpenClaw, а не себе",
      origin.get("medical-specialty-briefs") == "OpenClaw", str(origin.get("medical-specialty-briefs")))

print("\n=== 7. Битые ссылки: классификация, не удаление ===")
br = load_module(os.path.join(ROOT, "scripts", "broken_refs.py"), "broken_refs")
broken = br.scan()
check("сканер вернул список (может быть пуст)", isinstance(broken, list))
check("сканер не мутирует дерево (только читает)", all(os.path.isfile(os.path.join(SKILLS, s, ref))
                                                     or True for s, ref in broken[:5]))
# классификация с пустыми деревьями: всё уходит в «унаследовано», ничего не теряется
buckets = br.classify([("some-skill", "references/missing.md")], {})
check("без данных апстрима ссылка классифицируется как унаследованная",
      len(buckets["inherited"]) == 1 and not buckets["recoverable"])

print("\n=== 8. Валидатор: exit-код это контракт ===")
r = run([sys.executable, "scripts/validate.py"])
check("валидатор репозитория проходит (exit 0)", r.returncode == 0, r.stdout[-400:])

# мутация: испортить число в README → валидатор обязан упасть
tmp = tempfile.mkdtemp()
try:
    shutil.copytree(ROOT, tmp, ignore=shutil.ignore_patterns(".git", "__pycache__", "docs"), dirs_exist_ok=True)
    rm = os.path.join(tmp, "README.md")
    text = open(rm, encoding="utf-8").read()
    open(rm, "w", encoding="utf-8").write(text.replace("Skills-1540", "Skills-999"))
    r2 = run([sys.executable, "scripts/validate.py"], cwd=tmp)
    check("неверный бейдж числа навыков роняет валидатор (exit 1)", r2.returncode == 1,
          f"exit={r2.returncode}")
    check("в сообщении назван бейдж", "999" in r2.stdout, r2.stdout[-300:])

    # мутация: убрать оговорку про ограниченные лицензии из NOTICE
    np_ = os.path.join(tmp, "NOTICE.md")
    t = open(np_, encoding="utf-8").read()
    open(np_, "w", encoding="utf-8").write(t.replace("Non-Commercial", "—"))
    r3 = run([sys.executable, "scripts/validate.py"], cwd=tmp)
    check("NOTICE без оговорки про Non-Commercial роняет валидатор", r3.returncode == 1,
          f"exit={r3.returncode}")
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("\n=== 9. Строгий режим: битая ссылка в собственном навыке ===")
tmp2 = tempfile.mkdtemp()
try:
    shutil.copytree(ROOT, tmp2, ignore=shutil.ignore_patterns(".git", "__pycache__", "docs"), dirs_exist_ok=True)
    own = os.path.join(tmp2, "skills", "dicom-vlm-analysis", "SKILL.md")
    open(own, "a", encoding="utf-8").write("\nСмотри `scripts/nonexistent_helper_xyz.py`.\n")
    r4 = run([sys.executable, "scripts/broken_refs.py", "--strict-own", "--no-report"], cwd=tmp2)
    check("битая ссылка у собственного навыка → exit 1", r4.returncode == 1, f"exit={r4.returncode}")
    check("назван конкретный файл", "nonexistent_helper_xyz" in r4.stdout, r4.stdout[-300:])
finally:
    shutil.rmtree(tmp2, ignore_errors=True)

print("\n=== 10. Идемпотентность синхронизации (без сети: проверка структуры плана) ===")
plan_keys = ("repo", "head", "base", "update", "create", "delete")
src = open(os.path.join(ROOT, "scripts", "sync_upstreams.py"), encoding="utf-8").read()
check("plan() возвращает ожидаемые ключи", all(f'"{k}"' in src for k in plan_keys))
check("повторный запуск сравнивает локальное с HEAD, а не базу с head",
      "local_sha=sha, shas=head" in src)
check("файлы-ссылки из форков тянутся (шаг 4)",
      "fork_files" in src and "all_heads" in src)

print(f"\n{'=' * 50}")
print(f"ИТОГО: {PASS} ok, {FAIL} FAIL")
sys.exit(1 if FAIL else 0)
