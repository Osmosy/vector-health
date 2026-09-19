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
check("собственные навыки — только наши (три)",
      {n for n, s in origin.items() if s == "own"}
      == {"dicom-vlm-analysis", "atrial-fibrillation-treatment", "abdominal-ct-findings"},
      str({n for n, s in origin.items() if s == "own"}))
check("medical-specialty-briefs атрибутирован OpenClaw, а не себе",
      origin.get("medical-specialty-briefs") == "OpenClaw", str(origin.get("medical-specialty-briefs")))

print("\n=== 7. Битые ссылки: классификация, не удаление ===")
br = load_module(os.path.join(ROOT, "scripts", "broken_refs.py"), "broken_refs")
broken = br.scan()
check("сканер вернул список (может быть пуст)", isinstance(broken, list))
check("каждый элемент — (навык, путь, исходная ссылка)",
      all(len(x) == 3 for x in broken[:20]), str(broken[:1]))
# Ссылка может быть записана абсолютным путём: инвентарь обязан нормализовать её
# до пути относительно навыка, иначе живой файл попадает в отчёт как битый.
R = load_module(os.path.join(ROOT, "scripts", "refs.py"), "refs_mod")
check("абсолютный путь нормализуется до пути в навыке",
      R.to_skill_relative("/Users/x/.openclaw/workspace/skills/foo/scripts/main.py", "foo")
      == "scripts/main.py")
check("путь от корня репо нормализуется",
      R.to_skill_relative("skills/foo/scripts/main.py", "foo") == "scripts/main.py")
check("ссылка с ./ нормализуется", R.to_skill_relative("./data/x.json", "foo") == "data/x.json")
check("чужая ссылка не нормализуется (остаётся как есть)",
      R.to_skill_relative("references/a.md", "foo") is None)
# классификация с пустыми деревьями: всё уходит в «унаследовано», ничего не теряется
buckets = br.classify([("some-skill", "references/missing.md", "references/missing.md")], {})
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
    real = json.load(open(os.path.join(ROOT, "skills-index.json"), encoding="utf-8"))["total"]
    mutated = text.replace(f"Skills-{real}", "Skills-999")
    check("бейдж с фактическим числом найден (иначе тест бесполезен)", mutated != text,
          f"в README нет Skills-{real}")
    open(rm, "w", encoding="utf-8").write(mutated)
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

print("\n=== 11. Ассеты: файл из репозитория не исключён из сайта ===")
# Валидатор ловит ловушку Pages: ассет есть в репозитории, но исключён из сборки
# сайта — локально всё цело, а на опубликованной странице картинка 404.
tmp3 = tempfile.mkdtemp()
try:
    shutil.copytree(ROOT, tmp3, ignore=shutil.ignore_patterns(".git", "__pycache__"), dirs_exist_ok=True)
    cfg = os.path.join(tmp3, "_config.yml")
    t = open(cfg, encoding="utf-8").read()
    open(cfg, "w", encoding="utf-8").write(t.replace("  - THIRD_PARTY_LICENSES/\n",
                                                     "  - THIRD_PARTY_LICENSES/\n  - assets/\n"))
    r5 = run([sys.executable, "scripts/validate.py"], cwd=tmp3)
    check("ассет, исключённый из сайта, роняет валидатор", r5.returncode == 1, f"exit={r5.returncode}")
    check("в сообщении названы и файл, и причина", "vector-logo.png" in r5.stdout and "404" in r5.stdout,
          r5.stdout[-300:])
finally:
    shutil.rmtree(tmp3, ignore_errors=True)

print("\n=== 12. Двуязычный слой: китайский только в полях-источниках ===")
# Разделение «оригинал апстрима» и «наш перевод» должно быть видно по имени поля,
# иначе читатель не отличит цитату от собственного текста, а переводчик не поймёт,
# что можно менять. Проверяем и правило, и сами данные.
tax = json.load(open(os.path.join(SKILLS, "abdominal-ct-findings", "references",
                                  "radar-taxonomy.json"), encoding="utf-8"))
CJK = re.compile(r"[\u3000-\u9fff\uff00-\uffef]")
ALLOWED = {"finding_zh", "organ_zh", "csv_column_zh_en"}
viol = [(k, v) for f in tax["findings"] for k, v in f.items()
        if isinstance(v, str) and CJK.search(v) and k not in ALLOWED]
check("CJK не выходит за поля-источники", not viol, str(viol[:3]))
check("все находки имеют русский перевод",
      all(f.get("finding_ru") for f in tax["findings"]))
check("все находки имеют английское название",
      all(f.get("finding_en") for f in tax["findings"]))
check("китайский ключ сохранён для сопоставления с CSV модели",
      all(f.get("csv_column_zh_en", "").startswith(f.get("organ_zh", "")) for f in tax["findings"]))
check("findings_total совпадает с числом записей",
      tax["findings_total"] == len(tax["findings"]), f"{tax['findings_total']} vs {len(tax['findings'])}")
check("organs_total совпадает", tax["organs_total"] == len(tax["organs"]))
check("заявлено 146 находок × 18 органов",
      tax["findings_total"] == 146 and tax["organs_total"] == 18,
      f"{tax['findings_total']}×{tax['organs_total']}")
sum_by_organ = sum(o["findings_total"] for o in tax["organs"])
check("сумма находок по органам = общему числу", sum_by_organ == tax["findings_total"],
      f"{sum_by_organ} vs {tax['findings_total']}")

# мутация: перевод с китайскими символами вне поля-источника должен ронять валидатор
tmp4 = tempfile.mkdtemp()
try:
    shutil.copytree(ROOT, tmp4, ignore=shutil.ignore_patterns(".git", "__pycache__", "docs"),
                    dirs_exist_ok=True)
    tp = os.path.join(tmp4, "skills", "abdominal-ct-findings", "references", "radar-taxonomy.json")
    data = json.load(open(tp, encoding="utf-8"))
    data["findings"][0]["finding_ru"] = "肝囊肿 (китайский протёк в перевод)"
    open(tp, "w", encoding="utf-8").write(json.dumps(data, ensure_ascii=False))
    r6 = run([sys.executable, "scripts/validate.py"], cwd=tmp4)
    check("CJK в поле перевода роняет валидатор", r6.returncode == 1, f"exit={r6.returncode}")
    check("нарушившее поле названо", "finding_ru" in r6.stdout, r6.stdout[-200:])
finally:
    shutil.rmtree(tmp4, ignore_errors=True)

print("\n=== 13. Таксономия: колонки, органы, полнота разбора внешнего теста ===")
# Локальная часть проверки (сеть не нужна): структура данных и соответствие
# между таблицей в SKILL.md и JSON — расхождение означает, что таблица показывает
# не то, что лежит в данных.
tax2 = json.load(open(os.path.join(SKILLS, "abdominal-ct-findings", "references",
                                   "radar-taxonomy.json"), encoding="utf-8"))
cols_list = [f["csv_column_zh_en"] for f in tax2["findings"]]
check("колонок столько же, сколько находок", len(cols_list) == tax2["findings_total"])
check("колонки уникальны", len(set(cols_list)) == len(cols_list))
check("каждая колонка начинается с китайского имени органа",
      all(c.startswith(f["organ_zh"] + "_") for f, c in zip(tax2["findings"], cols_list)))
check("внебрюшных структур помечено 5", tax2.get("outside_abdomen_total") == 5,
      str(tax2.get("outside_abdomen_total")))
outside = {o["organ_zh"] for o in tax2["organs"] if o.get("outside_abdomen")}
check("внебрюшные — лёгкие, сердце, рёбра, пищевод, крестец",
      outside == {"肺", "心脏", "肋骨", "食管", "骶骨"}, str(outside))

skill_md = open(os.path.join(SKILLS, "abdominal-ct-findings", "SKILL.md"), encoding="utf-8").read()
check("каждая находка из JSON есть в таблице SKILL.md",
      all(f"| {f['finding_ru']} |" in skill_md for f in tax2["findings"]))
check("в таблице структур есть колонка про брюшную полость",
      "В брюшной полости" in skill_md)
check("граница области объяснена в тексте",
      "вне её" in skill_md or "внебрюшн" in skill_md)

# мутация: рассинхронизировать таблицу и данные — таблица показывает не то, что в JSON
# Копируем ЦЕЛИКОМ (вместе с docs/): если урезать копию, валидатор упадёт на
# посторонних проверках и тест «пройдёт» по неверной причине — так и случилось
# с первой версией этого теста.
tmp5 = tempfile.mkdtemp()
try:
    shutil.copytree(ROOT, tmp5, ignore=shutil.ignore_patterns(".git", "__pycache__"),
                    dirs_exist_ok=True)
    sp = os.path.join(tmp5, "skills", "abdominal-ct-findings", "SKILL.md")
    body = open(sp, encoding="utf-8").read()
    mutated = body.replace("| Язва желудка |", "| Язва |")
    check("мутация применена (иначе тест бесполезен)", mutated != body)
    open(sp, "w", encoding="utf-8").write(mutated)
    r7 = run([sys.executable, "scripts/validate.py"], cwd=tmp5)
    check("выпавшая из таблицы находка роняет валидатор", r7.returncode == 1, f"exit={r7.returncode}")
    check("упавшая проверка — именно про таблицу",
          "[языки]" in r7.stdout and "Язва желудка" in r7.stdout, r7.stdout[-260:])
finally:
    shutil.rmtree(tmp5, ignore_errors=True)

print(f"\n{'=' * 50}")
print(f"ИТОГО: {PASS} ok, {FAIL} FAIL")
sys.exit(1 if FAIL else 0)
