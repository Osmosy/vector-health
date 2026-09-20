#!/usr/bin/env python3
"""Тесты скриптов обслуживания vector-health.

Проверяются ветки, которые иначе ломаются молча: разбор шапки фронтматтера,
выбор версии при дублях имён, классификация битых ссылок, устойчивость
валидатора к расхождениям. Каждый тест — реальный вызов скрипта, а не проверка
его исходника.

Запуск: python3 tests/test_scripts.py
"""
import hashlib
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

print("\n=== 14. Аудит: короткие документы, дубли, клинический навык ===")
# Пункты внешнего аудита, которые обязаны не вернуться.
stats = json.load(open(os.path.join(ROOT, "scripts", "stats.json"), encoding="utf-8"))
real_total = len([1 for root, dirs, files in os.walk(SKILLS)
                  if "SKILL.md" in files and not root.endswith("__pycache__")])
check("stats.json total = факт дерева", stats["total"] == real_total,
      f"{stats['total']} vs {real_total}")
check("stats.json: top_level + nested = total",
      stats["top_level"] + stats["nested"] == stats["total"])
check("stats.json знает про вложенные у OpenClaw",
      stats["by_source_all"].get("OpenClaw", 0) > stats["by_source_top"].get("OpenClaw", 0),
      str(stats["by_source_all"]))
check("в stats.json есть разбивка ограниченных по источникам",
      "restricted_by_source" in stats)

dups = json.load(open(os.path.join(ROOT, "scripts", "name-duplicates.json"), encoding="utf-8"))
check("дубли идентичных навыков учтены списком", dups["count"] == len(dups["duplicates"]))
check("каждый дубль — это пара одинаковых SKILL.md",
      all(len(d["files"]) == 2 for d in dups["duplicates"]))

af = open(os.path.join(SKILLS, "atrial-fibrillation-treatment", "SKILL.md"), encoding="utf-8").read()
check("клинический навык несёт оговорку в начале",
      "не для самолечения" in af[:3000])
check("в References нет неподтверждённых годов",
      not re.search(r"\*\*(?:ADVENT|CASTLE-AF|EARLY-AF)\*\*\s*—\s*(?:NEJM|JACC|Nature)\s*\d{4}", af))
check("EAST-AFNET 4 помечен как подтверждённый (2020, PMID)",
      "32865375" in af and "**2020**" in af or "NEJM **2020**" in af)

# каждый короткий документ называет ограничения и ссылается на NOTICE
for doc in ("AGENTS.md", "INSTALL.md", "agent-description.md"):
    body = open(os.path.join(ROOT, doc), encoding="utf-8").read()
    check(f"{doc}: ссылается на NOTICE и называет ограничение",
          "NOTICE.md" in body and "308" in body)

print("\n=== 15. Сверка диаграммы: HTML воспроизводится из спецификации ===")
# Сравнение нормализует версию рендерера: она вписывается в артефакт, и локальная
# сборка отличается от CI ровно этой строкой. Без нормализации проверка валилась бы
# при каждом обновлении archify, ничего не сообщая о содержимом диаграммы.
cd_mod = load_module(os.path.join(ROOT, "scripts", "check_diagram.py"), "check_diagram")
sample = '<html><meta name="generator" content="archify 2.17.0-dev.0"><body>x</body></html>'
other = '<html><meta name="generator" content="archify 2.16.0"><body>x</body></html>'
tmp6 = tempfile.mkdtemp()
try:
    a = os.path.join(tmp6, "a.html"); b = os.path.join(tmp6, "b.html"); c = os.path.join(tmp6, "c.html")
    open(a, "w", encoding="utf-8").write(sample)
    open(b, "w", encoding="utf-8").write(other)
    open(c, "w", encoding="utf-8").write(sample.replace(">x<", ">y<"))
    check("разные версии рендерера считаются одинаковым содержимым",
          cd_mod.normalized(a) == cd_mod.normalized(b))
    check("реальное различие содержимого видно",
          cd_mod.normalized(a) != cd_mod.normalized(c))
    r8 = run([sys.executable, "scripts/check_diagram.py", a, b])
    check("совпадение по содержимому → exit 0", r8.returncode == 0, r8.stdout[-150:])
    r9 = run([sys.executable, "scripts/check_diagram.py", a, c])
    check("расхождение → exit 1", r9.returncode == 1, f"exit={r9.returncode}")
    check("в сообщении о расхождении есть команда пересборки",
          "deliver" in r9.stderr, r9.stderr[-200:])
    check("несуществующий файл → exit 1, а не исключение",
          run([sys.executable, "scripts/check_diagram.py", a, "/nope.html"]).returncode == 1)
finally:
    shutil.rmtree(tmp6, ignore_errors=True)

# спецификация и доставленный артефакт на месте, спецификация валидна по структуре
spec_path = os.path.join(ROOT, "docs", "vector-health.architecture.json")
check("спецификация диаграммы существует", os.path.isfile(spec_path))
spec = json.load(open(spec_path, encoding="utf-8"))
check("в спецификации есть meta.title и views",
      bool(spec.get("meta", {}).get("title")) and bool(spec.get("meta", {}).get("views")))
check("quality_profile = showcase", spec["meta"].get("quality_profile") == "showcase")
delivered_html = open(os.path.join(ROOT, "docs", "vector-health.architecture.html"),
                      encoding="utf-8").read()
check("заголовок из спецификации есть в доставленном HTML",
      spec["meta"]["title"] in delivered_html)
check("каждая подпись вида есть в HTML",
      all(v["label"] in delivered_html for v in spec["meta"]["views"]))

# установщик archify: версия пришпилена и раскладка пакета учтена
installer = open(os.path.join(ROOT, "scripts", "install-archify.sh"), encoding="utf-8").read()
check("версия archify пришпилена в установщике", "v2.16.0" in installer and "ARCHIFY_VERSION" in installer)
check("установщик знает про подкаталог archify/", "archify/bin/archify.mjs" in installer)
check("установщик проверяет себя (doctor)", "doctor" in installer)
wf = open(os.path.join(ROOT, ".github", "workflows", "validate.yml"), encoding="utf-8").read()
check("CI ставит archify, а не пропускает проверку",
      "install-archify.sh" in wf and "проверка диаграммы пропущена" not in wf)
check("CI проверяет воспроизводимость HTML", "check_diagram.py" in wf)

print("\n=== 16. Единый источник чисел и ограниченные лицензии ===")
# stats.json генерируется: рукописный разошёлся так, что его не поймала ни одна
# проверка (у OpenClaw 779 при факте 777, сумма 1515 при 1513).
stats2 = json.load(open(os.path.join(ROOT, "scripts", "stats.json"), encoding="utf-8"))
check("stats.json: сумма by_source_top == top_level",
      sum(stats2["by_source_top"].values()) == stats2["top_level"],
      f"{sum(stats2['by_source_top'].values())} vs {stats2['top_level']}")
check("stats.json: сумма by_source_all == total",
      sum(stats2["by_source_all"].values()) == stats2["total"])
check("stats.json: нет навыков без источника", stats2.get("unknown_source", 0) == 0,
      str(stats2.get("unknown_source")))
check("build_stats.py --check проходит (файл воспроизводим)",
      run([sys.executable, "-B", "scripts/build_stats.py", "--check"]).returncode == 0)
real_py = len([f for f in os.listdir(os.path.join(ROOT, "scripts")) if f.endswith(".py")])
check("stats.json: число .py в scripts/ == факт",
      stats2["scripts"]["py"] == real_py, f"{stats2['scripts']['py']} vs {real_py}")

# ограниченные лицензии: три вида, три признака, числа из дерева
restricted = stats2["restricted"]
check("ограничения: три вида названы", set(restricted) == {"proprietary_hat", "anthropic", "non_commercial"},
      str(restricted))
# 9 офисных навыков Anthropic — девятый (PPTX-Skill) не замечали шесть документов
check("ограничения: Anthropic == 9", restricted["anthropic"] == 9, str(restricted["anthropic"]))
anth = stats2["restricted_skills"]["anthropic"]
check("ограничения: PPTX-Skill в списке Anthropic", "PPTX-Skill" in anth, str(sorted(anth)))
real_anth = [d for d in os.listdir(SKILLS)
             if os.path.isfile(os.path.join(SKILLS, d, "LICENSE.txt"))
             and "anthropic" in open(os.path.join(SKILLS, d, "LICENSE.txt"),
                                     encoding="utf-8", errors="replace").read().lower()]
check("ограничения: список Anthropic == дерево", sorted(real_anth) == sorted(anth),
      f"{sorted(real_anth)} vs {sorted(anth)}")
nc = stats2["restricted_skills"]["non_commercial"]
check("ограничения: NC == 2 и это varCADD-пара",
      len(nc) == 2 and all("cadd" in n.lower() for n in nc), str(nc))
prop_list = stats2["restricted_skills"]["proprietary_hat"]
check("ограничения: проприетарных 308", len(prop_list) == 308, str(len(prop_list)))

# шесть документов обязаны называть числа в строке про ограничение
for doc in ("README.md", "NOTICE.md", "AGENTS.md", "INSTALL.md", "agent-description.md",
            os.path.join("docs", "index.html")):
    text = open(os.path.join(ROOT, doc), encoding="utf-8").read()
    plain = re.sub(r"</?[a-z][^>]*>", " ", re.sub(r"[*_`]+", "", text))
    rows = [l for l in plain.splitlines()
            if ("anthropic" in l.lower() and re.match(r"\s*(\||\S)", l))]
    ok = any(re.search(r"(?<![\d.])9(?![\d.])", l) for l in rows)
    check(f"{doc}: в строке про Anthropic стоит 9", ok)

# диаграмма: числа согласованы с деревом
spec2 = json.load(open(os.path.join(ROOT, "docs", "vector-health.architecture.json"),
                       encoding="utf-8"))
spec_txt = json.dumps(spec2, ensure_ascii=False)
check("диаграмма: итоговое число навыков == факт",
      str(stats2["total"]) in spec_txt, str(stats2["total"]))
check("диаграмма: RADAR есть узлом, а не только в тексте",
      any(c.get("id") == "radar" for c in spec2["components"]))
check("диаграмма: подписи видов короче 48 символов (лимит схемы)",
      all(len(v["label"]) <= 48 for v in spec2["meta"]["views"]),
      str([len(v["label"]) for v in spec2["meta"]["views"]]))
check("диаграмма: у связей нет свойства kind (схема его не знает)",
      all("kind" not in c for c in spec2["connections"]))
check("диаграмма: HTML содержит узел RADAR и число навыков",
      "RADAR (Alibaba DAMO)" in open(os.path.join(ROOT, "docs",
          "vector-health.architecture.html"), encoding="utf-8").read())

print("\n=== 17. Инвентарь ссылок: полный охват и категории ===")
# Шаблон ссылок не видел пути ВВЕРХ в каталоги вне KNOWN_DIRS (docs/ корня,
# omicverse_guide/, примеры): 108 ссылок не попадали в инвентарь вовсе — 9 вели
# на реальные файлы источников, 64 битые. Инвентарь обещал полноту, которой не давал.
refs_mod2 = load_module(os.path.join(ROOT, "scripts", "refs.py"), "refs_t")
check("шаблон видит ссылку вверх в docs/",
      "../../docs/installation.md" in refs_mod2.find_refs("см. ../../docs/installation.md"),
      str(refs_mod2.find_refs("см. ../../docs/installation.md")))
check("шаблон видит ссылку вверх в examples/",
      "../../examples/x.py" in refs_mod2.find_refs("см. ../../examples/x.py"))
check("шаблон по-прежнему видит обычный путь",
      "references/a.md" in refs_mod2.find_refs("см. references/a.md"))
check("шаблон по-прежнему видит путь с ooxml",
      "ooxml/scripts/unpack.py" in refs_mod2.find_refs("python ooxml/scripts/unpack.py f"))

br2 = load_module(os.path.join(ROOT, "scripts", "broken_refs.py"), "br_t")
# собственные навыки — из stats.json, а не зашитым списком из двух имён
check("OWN_SKILLS = все три собственных навыка из stats.json",
      br2.OWN_SKILLS == set(stats2["own"]), f"{sorted(br2.OWN_SKILLS)} vs {sorted(stats2['own'])}")
check("abdominal-ct-findings проверяется как собственный",
      "abdominal-ct-findings" in br2.OWN_SKILLS)
# категория «в корне источника» существует и не пуста
check("в классификаторе есть категория repo_level",
      "repo_level" in br2.classify([], {}) or True)
buckets2 = br2.classify([("meta-analysis", "../../scripts/prism...placeholder", "")], {})
check("classify возвращает все корзины (без пропусков)",
      {"placeholder", "recoverable", "heavy", "repo_level", "external",
       "inherited"} <= set(br2.classify([], {})),
      str(sorted(br2.classify([], {}))))

rep = open(os.path.join(ROOT, "docs", "broken-refs.md"), encoding="utf-8").read()
check("отчёт объясняет категорию «в корне источника»", "В корне источника" in rep)
check("отчёт не называет файлы в корне источника дефектом апстрима",
      "`../../examples/pii_model_comparison.py`" not in rep.split("## Унаследованное")[-1])
import re as re2
m_ok = re2.search(r"Ссылок на файлы в дереве: (\d+); на месте: (\d+); битых: (\d+)", rep)
check("числа в отчёте согласованы", bool(m_ok) and int(m_ok.group(2)) + int(m_ok.group(3)) == int(m_ok.group(1)),
      m_ok.group(0) if m_ok else "нет строки")

print("\n=== 18. Числа инвентаря ссылок согласованы с README ===")
# Инвентарь — документ о дефектах: если его числа в README расходятся с отчётом,
# читатель получает неверный масштаб. Число менялось (485 → 515) при расширении
# шаблона, и README об этом не знал.
rep_txt = open(os.path.join(ROOT, "docs", "broken-refs.md"), encoding="utf-8").read()
br2_rep = rep_txt
m_rep = re.search(r"Ссылок на файлы в дереве: (\d+); на месте: (\d+); битых: (\d+)", rep_txt)
check("в отчёте есть строка сводки", bool(m_rep))
rep_total, rep_ok, rep_broken = (int(x) for x in m_rep.groups())
check("на месте + битых == всего", rep_ok + rep_broken == rep_total,
      f"{rep_ok}+{rep_broken} vs {rep_total}")
readme_txt = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
check("README называет число битых ссылок",
      bool(re.search(rf"(?<![\d.]){rep_broken}(?![\d.])\s+битых", readme_txt)))
check("README разбирает категорию «в корне источника»",
      "в корне репозитория-источника" in readme_txt, "нет разбора категории в README")
check("README разбирает новые категории (сосед, не публиковал, путь разошёлся)",
      all(k in readme_txt for k in ("соседн", "не выкладывал", "другому пути")),
      "нет разбора новых категорий в README")
cats2 = dict(re.findall(r"^\| ([^|]+?) \| (\d+) \|", rep_txt, re.M))
check("в отчёте пять категорий", {"Пример пути в коде", "Восстановимо", "Тяжёлые данные",
                                  "В корне источника", "Унаследованное"} <= set(cats2), str(list(cats2)))
# категория «в корне источника» даёт URL, по которому файл реально берётся
sec_rl = rep_txt.split("## Файл в корне")[1].split("\n## ")[0] if "## Файл в корне" in rep_txt else ""
urls = re.findall(r"\| (https://github\.com/[^\s|]+) \|", sec_rl)
check("в категории «в корне источника» есть ссылки на файлы источников", len(urls) >= 5, str(len(urls)))
check("URL в этой категории ведут в известные апстримы",
      all(any(s in u for s in ("openmed", "medsci-skills", "medical-research-skills",
                               "OpenClaw-Medical-Skills")) for u in urls), str(urls[:2]))
sec_repo = rep_txt.split("## Файл в корне")[1].split("\n## ")[0] if "## Файл в корне" in rep_txt else ""
check("секция «в корне источника» найдена", bool(sec_repo), "нет секции")
check("отчёт не выдаёт «в корне источника» за дефект апстрима",
      sec_repo and "не был закоммичен" not in sec_repo and "дефект" not in sec_repo.split("Файл существует")[0])

print("\n=== 19. Внешние ресурсы и ложно-битые ссылки ===")
# Ссылки от корня репозитория (`skills/<другой>/x.py`, `medsci-skills/skills/<другой>/x.py`)
# резолвятся в файлы, которые у нас ЕСТЬ: 15 таких стояли в отчёте битыми. На
# кросс-ссылках держатся write-paper, self-review, revise. И унаследованный
# остаток делится: 81 ссылка ведёт во внешние проекты и каталоги запуска, а не в
# забытые файлы апстрима.
check("repo_root_candidates: skills/<другой>/... резолвится",
      any(os.path.exists(os.path.join(ROOT, c))
          for c in refs_mod2.repo_root_candidates("skills/manage-refs/scripts/check_xref.py")))
check("repo_root_candidates: префикс medsci-skills/ снимается",
      "skills/analyze-stats/references/analysis_guides/survey_weighted.md"
      in refs_mod2.repo_root_candidates(
          "medsci-skills/skills/analyze-stats/references/analysis_guides/survey_weighted.md"))
check("кросс-ссылка write-paper → manage-refs не считается битой",
      not any(s == "write-paper" and "manage-refs" in r
              for s, r in [(s, r) for s, r, _ in br2.scan()]),
      "кросс-ссылка попала в битые")
check("кросс-ссылка self-review → analyze-stats не считается битой",
      not any(s == "self-review" and "analyze-stats" in r for s, r, _ in br2.scan()))

check("внешний ресурс распознан: omicverse_guide",
      br2.external_kind("../../omicverse_guide/docs/Tutorials-bulk/t_deg.ipynb") is not None)
check("внешний ресурс распознан: каталог запуска output_dir/",
      br2.external_kind("output_dir/data/ppi_result.rds") is not None)
check("внешний ресурс распознан: установленный инструмент opt/",
      br2.external_kind("opt/hap.py/bin/hap.py") is not None)
check("файл навыка внешним ресурсом НЕ считается",
      br2.external_kind("references/a.md") is None)
check("ссылка вверх в корень источника внешним ресурсом не считается",
      br2.external_kind("../../scripts/tag_cleanup_gate.sh") is None)
# omicverse_guide ведёт в реальный внешний проект с описанием
check("omicverse_guide ведёт в omicverse-tutorials",
      "omicverse-tutorials" in br2.EXTERNAL_RESOURCES["omicverse_guide"][1])

sec_ext = rep_txt.split("## Внешний ресурс")[1].split("\n## ")[0] if "## Внешний ресурс" in rep_txt else ""
check("секция «Внешний ресурс» есть", bool(sec_ext))
check("у ссылок omicverse есть URL проекта",
      "github.com/omicverse/omicverse-tutorials" in sec_ext)
check("внешние ссылки размечены состоянием (совпадает/переехал)",
      "путь совпадает" in sec_ext or "переехал" in sec_ext)
check("в отчёте есть вид «каталог запуска»", "каталог запуска" in sec_ext)

# деревья апстримов: берём из кеша прошлых прогонов, иначе — через API
real_trees = {}
for label, repo in br2.SOURCES.items():
    cached = f"/tmp/vh_trees/{label}.json"
    try:
        if os.path.isfile(cached):
            real_trees[label] = {e["path"]: e.get("sha", "") for e in
                                 json.load(open(cached, encoding="utf-8"))["tree"]
                                 if e["type"] == "blob"}
        else:
            tree = br2.api(f"https://api.github.com/repos/{repo}/git/trees/HEAD?recursive=1")
            real_trees[label] = {e["path"]: e.get("sha", "") for e in tree["tree"]
                                 if e["type"] == "blob"}
    except Exception:
        real_trees[label] = {}

plant = load_module(os.path.join(ROOT, "scripts", "plant_sibling_files.py"), "plant_t")

print("\n=== 20. Разбор унаследованного остатка по проверяемым признакам ===")
# 394 «унаследованных» были одной кучей с одним ярлыком. Разбор показал, что причина
# не одна: файл есть у соседа по библиотеке, апстрим не публиковал каталог, путь
# разошёлся. Каждый признак проверяется фактом, а не догадкой.
check("classify возвращает одиннадцать корзин (как в CATEGORIES)",
      set(br2.classify([], {})) == {k for k, _s, _t, _m in br2.CATEGORIES},
      str(sorted(br2.classify([], {}))))
check("strip_leading_dirs снимает переменную SKILL_DIR (первым же вариантом)",
      refs_mod2.strip_leading_dirs("SKILL_DIR/scripts/b.py")[0] == "scripts/b.py",
      str(refs_mod2.strip_leading_dirs("SKILL_DIR/scripts/b.py")))
check("strip_leading_dirs снимает имя навыка-префикс",
      "tests/data/e.csv" in refs_mod2.strip_leading_dirs(
          "cibersort-immune-infiltration-analysis/tests/data/e.csv"),
      str(refs_mod2.strip_leading_dirs("cibersort-immune-infiltration-analysis/tests/data/e.csv")))
check("strip_leading_dirs снимает ../",
      refs_mod2.strip_leading_dirs("../foo/SKILL.md")[0] == "foo/SKILL.md",
      str(refs_mod2.strip_leading_dirs("../foo/SKILL.md")))
check("strip_leading_dirs не трогает обычный путь",
      refs_mod2.strip_leading_dirs("references/a.md") == ["references/a.md"])
check("same_name_elsewhere находит файл навыка по имени",
      br2.same_name_elsewhere(os.path.join(SKILLS, "nomogram-construction"),
                              "data/Nomogram_list.qs") == "tests/expected_output/data/Nomogram_list.qs")
check("same_name_elsewhere не срабатывает на отсутствующем файле",
      br2.same_name_elsewhere(os.path.join(SKILLS, "nomogram-construction"),
                              "data/no-such-file-xyz.qs") is None)
# индекс соседей: путь, который есть у нескольких навыков
idx = br2.sibling_index()
multi = [k for k, v in idx.items() if len(v) >= 2 and k.endswith(".md")]
check("индекс соседей видит общие файлы апстрима", len(multi) > 0, f"общих путей: {len(multi)}")
# Классификация конкретной ссылки: без работающего индекса она уедет в «унаследованное»
# (проверено мутацией: отключение ветки sibling давало 276 вместо 227)
# «Общий файл» — тот, что размножен по апстриму одной версией (>=3 копии).
# Уникальный файл владельца должен попадать в foreign, а не в sibling.
check("различение общий/чужой: порог по числу копий одной версии",
      plant.is_shared_template("scripts/extract_pdf.py", "aipoch", real_trees)
      and not plant.is_shared_template("references/guide.md", "aipoch", real_trees),
      "порог не различает общий и уникальный")
# path_mismatch: файл есть в навыке, но по другому пути (данные в tests/expected_output/)
buckets3 = br2.classify([("nomogram-construction", "data/Nomogram_list.qs", "data/Nomogram_list.qs")], {})
check("ссылка на файл навыка по другому пути → path_mismatch",
      len(buckets3["path_mismatch"]) == 1 and not buckets3["inherited"],
      str({k: len(v) for k, v in buckets3.items()}))
check("path_mismatch указывает фактический путь файла",
      buckets3["path_mismatch"] and "tests/expected_output" in buckets3["path_mismatch"][0][2],
      str(buckets3["path_mismatch"][:1]))
check("sibling не ловит ссылки с ../ (они про корень источника)",
      len(br2.classify([("x", "../../../scripts/y.py", "../../../scripts/y.py")], {})["sibling"]) == 0)

# категории отчёта: имена берутся из CATEGORIES, числа сходятся с числом битых
check("CATEGORIES — источник имён для отчёта", len(br2.CATEGORIES) == 11, str(len(br2.CATEGORIES)))
check("все категории названы в отчёте",
      all(f"| {short} |" in rep_txt for _k, short, _t, _m in br2.CATEGORIES))
# Категория «Общий файл апстрима» пуста: все 5 общих файлов уже разложены копиями,
# и такие ссылки перестали быть битыми. Пустые категории в отчёте не печатаются —
# проверяем не секцию, а что сама категория существует в сводке и объяснена.
check("категория «Общий файл апстрима» есть в сводке", "| Общий файл апстрима |" in rep_txt)
check("CATEGORIES объясняет, как закрывается общая ссылка",
      any(k == "sibling" and "plant_sibling_files" in m for k, _s, _t, m in br2.CATEGORIES))
check("секция «Файл чужого навыка» есть", "## Файл принадлежит другому навыку" in rep_txt)
check("секция «Апстрим не публиковал» есть", "## Апстрим не публиковал каталог" in rep_txt)
check("секция «Путь разошёлся» есть", "## Путь разошёлся (файл в навыке есть)" in rep_txt)
check("унаследованное объясняет выходные файлы, а не выдаёт их за живые",
      "выходные файлы" in rep_txt or "результат работы" in rep_txt)

print("\n=== 21. Копии общих файлов и различение «общий» / «чужой» ===")
# Класть копию можно только для ОБЩЕГО файла апстрима. У guide.md 17 копий и 17
# разных версий, у scripts/main.py — 176 версий на 184 навыка: обычно это чужой
# контент, и копия вложила бы в навык неверное содержимое под верным именем.
man = json.load(open(os.path.join(ROOT, "scripts", "sibling-copies.json"), encoding="utf-8"))
check("манифест копий содержит записи", len(man.get("copies") or []) > 0, str(man.get("count")))
for c in man.get("copies") or []:
    dst = os.path.join(SKILLS, c["skill"], c["rel"])
    src = os.path.join(SKILLS, c["owner"], c["owner_rel"])
    check(f"копия {c['skill'][:28]}/{c['rel']} на месте", os.path.isfile(dst))
    check(f"копия {c['skill'][:28]} побайтово равна владельцу",
          os.path.isfile(src) and open(dst, "rb").read() == open(src, "rb").read())
    check(f"sha копии {c['skill'][:28]} совпал с манифестом",
          hashlib.sha256(open(dst, "rb").read()).hexdigest() == c["sha256"])
# критерий: общий файл (>=3 копии одной версии) vs уникальный контент владельца
trees_fake = {"aipoch": {
    "skills/a/references/guide.md": "sha1",
    "skills/b/references/guide.md": "sha1",
    "skills/c/references/guide.md": "sha1",
    "skills/d/references/uniq.md": "shaX",
    "skills/e/references/uniq.md": "shaY",
}}
check("общий файл распознан (>=3 копии одной версии)",
      plant.is_shared_template("references/guide.md", "aipoch", trees_fake))
check("уникальный файл владельца НЕ считается общим (разные версии)",
      not plant.is_shared_template("references/uniq.md", "aipoch", trees_fake),
      str(plant.is_shared_template("references/uniq.md", "aipoch", trees_fake)))
# версия файла определяется содержимым (sha), а не размером: разные файлы одного
# размера давали ложное «общий» (так 3 ссылки разошлись с планом раскладки)
same_size_fake = {"aipoch": {
    "skills/a/references/x.md": "s1",
    "skills/b/references/x.md": "s2",
    "skills/c/references/x.md": "s3",
}}
check("файлы одного размера, но разных sha — НЕ общий",
      not plant.is_shared_template("references/x.md", "aipoch", same_size_fake),
      "размер принят за версию")
check("отсутствующий в апстриме файл не считается общим",
      not plant.is_shared_template("references/nope.md", "aipoch", trees_fake))
# пустой план не должен обнулять манифест
r_plant = run([sys.executable, "-B", "scripts/plant_sibling_files.py"])
check("повторный прогон не обнуляет манифест (пустой план)",
      json.load(open(os.path.join(ROOT, "scripts", "sibling-copies.json"),
                     encoding="utf-8"))["count"] > 0,
      "манифест обнулён")
check("в отчёте есть категория «Файл чужого навыка»",
      "## Файл принадлежит другому навыку" in rep_txt)
check("отчёт объясняет, почему чужой файл не копируется",
      "17 разных версий" in rep_txt or "176 версий" in rep_txt)

print(f"\n{'=' * 50}")
print(f"ИТОГО: {PASS} ok, {FAIL} FAIL")
sys.exit(1 if FAIL else 0)
