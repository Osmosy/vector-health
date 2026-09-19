#!/usr/bin/env python3
"""Валидатор репозитория vector-health — спина, которая не даёт документации расходиться.

Один вход для CI: `python3 scripts/validate.py`. Проверки (каждая — на реальном
факте дерева, не на глаз):

  1. Навыки: frontmatter есть, `name` == имя каталога (включая вложенные).
  2. Каталог: total == число навыков в дереве, вложенные включены, описания не пусты.
  3. Карта происхождения: каждый вендоренный навык атрибутирован, источник существует.
  4. Числа в README и agent-description.md == факт дерева.
  5. Лицензии: каждый источник из NOTICE имеет файл в THIRD_PARTY_LICENSES/.
  6. Ссылки: каждая относительная ссылка в документации резолвится.
  7. Ссылки внутри навыков: у собственных навыков битых быть не должно.
  8. Диаграмма: заголовок и подписи видов из спецификации присутствуют в HTML.
  9. Секреты: живые формы ключей в дереве (кроме тестовых фикстур) отсутствуют.
 10. Свой текст репозитория — без CJK (вендоренные навыки исключены: они на языке источника).
 11. Ограниченные лицензии: числа в шести документах совпадают с деревом, списки названы в NOTICE.
 12. Диаграмма: числа в спецификации совпадают с деревом (не только подписи в HTML).
 13. Единый источник чисел: stats.json воспроизводится генератором и сходится по суммам.

Exit 0 — всё сходится; exit 1 — есть расхождения (печатаются с адресом проблемы).
Любая проверка, которая не смогла выполниться, тоже даёт exit 1: «проверка не
запустилась» не должно выглядеть как «проверка прошла».
"""
import csv
import io
import json
import os
import pathlib
import re
import subprocess
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, "skills")
DOCS = ("README.md", "INSTALL.md", "NOTICE.md", "agent-description.md", "AGENTS.md")

# Источники: метка в карте происхождения → репозиторий → файл лицензии.
# Метка короткая (OpenClaw/aipoch/Aperivue/openmed) — именно её пишет
# sync_upstreams.py, и сравнивать надо с фактом, а не с длинным именем репозитория.
SOURCES = {
    "OpenClaw": ("FreedomIntelligence/OpenClaw-Medical-Skills", None),
    "aipoch": ("aipoch/medical-research-skills", "aipoch-medical-research-skills-MIT.txt"),
    "openmed": ("maziyarpanahi/openmed", "maziyarpanahi-openmed-APACHE-2.0.txt"),
    "Aperivue": ("Aperivue/medsci-skills", "aperivue-medsci-skills-MIT.txt"),
    # RADAR — не коллекция навыков, а источник таксономии в собственном навыке
    # abdominal-ct-findings. Лицензия только на код (Apache-2.0); веса модели
    # распространяются под CC BY-NC-SA 4.0 и в репозиторий не берутся.
    "radar": ("alibaba-damo-academy/damo-radar", "alibaba-damo-academy-damo-radar-APACHE-2.0.txt"),
}
THIRD_PARTY = os.path.join(ROOT, "THIRD_PARTY_LICENSES")
OWN_SKILLS = {"dicom-vlm-analysis", "atrial-fibrillation-treatment", "abdominal-ct-findings"}

# Живые формы секретов. Тестовые фикстуры (tests/, */tests/) исключены: там
# фальшивые ключи стоят намеренно, чтобы проверять их обнаружение.
SECRET_RE = re.compile(
    r"(sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|"
    r"BEGIN [A-Z ]*PRIVATE KEY|-----BEGIN OPENSSH|AIza[0-9A-Za-z_-]{30,})"
)
SECRET_EXEMPT = ("/tests/", "/test/", "/node_modules/", "/.git/", "THIRD_PARTY_LICENSES/",
                 "/scripts/validate.py", "/scripts/broken_refs.py")  # сами образцы, не секреты

CJK_RE = re.compile(r"[\u3000-\u9fff\uff00-\uffef]")
CJK_EXEMPT = ("/skills/", "/THIRD_PARTY_LICENSES/", "/docs/broken-refs.md")


class Report:
    def __init__(self):
        self.errors: list[str] = []
        self.notes: list[str] = []

    def fail(self, check: str, msg: str) -> None:
        self.errors.append(f"[{check}] {msg}")

    def note(self, msg: str) -> None:
        self.notes.append(msg)


def walk_skills() -> list[str]:
    """Относительные пути каталогов с SKILL.md (включая вложенные)."""
    out = []
    for root, dirs, files in os.walk(SKILLS):
        dirs[:] = sorted(d for d in dirs if d != "__pycache__")
        if "SKILL.md" in files:
            out.append(os.path.relpath(root, SKILLS).replace(os.sep, "/"))
    return sorted(out)


def parse_frontmatter(text: str) -> dict:
    t = text.lstrip()
    while t.startswith("<!--"):
        end = t.find("-->")
        if end == -1:
            return {}
        t = t[end + 3:].lstrip()
    m = re.match(r"^---\s*\n(.*?)\n---", t, re.DOTALL)
    if not m:
        return {}
    fm: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith((" ", "\t", "-")):
            k, _, v = line.partition(":")
            fm[k.strip().lower()] = v.strip().strip("\"'")
    return fm


def check_skills(rep: Report) -> list[str]:
    """1. frontmatter есть; несовпадение name и каталога — учтённый факт, а не пропуск.

    Многие апстримы держат каталог и `name` врозь: OpenClaw объявляет
    `name: xlsx` в каталоге `xlsx-official`, `torch-geometric` в `torch_geometric`,
    а вложенные bio-навыки — с полным префиксом (`bio-vcf-basics` в `vcf-basics`).
    Это свойство источников, а не дефект сборки, поэтому расхождения не валят
    валидатор молча — они сверяются со списком в `scripts/name-mismatches.json`.
    Изменилось число — сигнал, что апстрим переименовал навык.
    """
    dirs = walk_skills()
    missing_fm = []
    mismatches = []
    for rel in dirs:
        path = os.path.join(SKILLS, rel, "SKILL.md")
        try:
            text = open(path, encoding="utf-8", errors="replace").read()
        except OSError as e:
            rep.fail("навыки", f"{rel}: не читается SKILL.md ({e})")
            continue
        fm = parse_frontmatter(text)
        if not fm.get("description"):
            missing_fm.append(rel)
        declared = fm.get("name")
        expected = rel.rsplit("/", 1)[-1]
        if declared and declared != expected:
            mismatches.append(rel)
    if missing_fm:
        rep.fail("навыки", f"{len(missing_fm)} навыков без description, напр. {missing_fm[:3]}")
    if not dirs:
        rep.fail("навыки", "в skills/ не найдено ни одного SKILL.md")

    known_path = os.path.join(ROOT, "scripts", "name-mismatches.json")
    if not os.path.isfile(known_path):
        rep.fail("навыки", "нет scripts/name-mismatches.json — списка расхождений name и каталога")
    else:
        with open(known_path, encoding="utf-8") as f:
            known = json.load(f)
        recorded = {x["skill"] for x in known.get("mismatches", [])}
        new = sorted(set(mismatches) - recorded)
        gone = sorted(recorded - set(mismatches))
        if new:
            rep.fail("навыки", f"новые расхождения name и каталога: {new[:5]} — обнови "
                               f"scripts/name-mismatches.json (или поправь name)")
        if gone:
            rep.fail("навыки", f"расхождения исчезли: {gone[:5]} — обнови scripts/name-mismatches.json")
        rep.note(f"навыки: {len(dirs)}; расхождений name и каталога {len(mismatches)} "
                 f"(все учтены в name-mismatches.json)")
    return dirs


def check_index(rep: Report, dirs: list[str]) -> None:
    """2. Каталог актуален и полон."""
    path = os.path.join(ROOT, "skills-index.json")
    if not os.path.isfile(path):
        rep.fail("каталог", "нет skills-index.json — собери scripts/build_index.py")
        return
    with open(path, encoding="utf-8") as f:
        idx = json.load(f)
    if idx.get("total") != len(dirs):
        rep.fail("каталог", f"total={idx.get('total')}, в дереве {len(dirs)} — пересобери build_index.py")
    entries = idx.get("skills", [])
    if len(entries) != idx.get("total"):
        rep.fail("каталог", f"записей {len(entries)} при total={idx.get('total')}")
    empty = [s["path"] for s in entries if not str(s.get("description", "")).strip()]
    if empty:
        rep.fail("каталог", f"{len(empty)} записей без описания, напр. {empty[:3]}")
    nested_idx = sum(1 for s in entries if "/" in str(s.get("path", "")))
    nested_real = sum(1 for d in dirs if "/" in d)
    if nested_idx < nested_real:
        rep.fail("каталог", f"вложенных в каталоге {nested_idx}, в дереве {nested_real} — плоский обход их теряет")
    catalogued = {str(s.get("path")) for s in entries}
    missing = [d for d in dirs if d not in catalogued]
    if missing:
        rep.fail("каталог", f"{len(missing)} навыков нет в каталоге, напр. {missing[:3]}")
    rep.note(f"каталог: {len(entries)} навыков ({nested_idx} вложенных)")


def check_origin(rep: Report) -> None:
    """3. Карта происхождения полна и ссылается на известные источники."""
    path = os.path.join(ROOT, "scripts", "upstream-origin.json")
    if not os.path.isfile(path):
        rep.fail("происхождение", "нет scripts/upstream-origin.json")
        return
    with open(path, encoding="utf-8") as f:
        origin = json.load(f).get("origin", {})
    if not origin:
        rep.fail("происхождение", "карта происхождения пуста")
        return
    known = set(SOURCES) | {"own"}
    bad = {v for v in origin.values() if v not in known}
    if bad:
        rep.fail("происхождение", f"неизвестные метки источников в карте: {sorted(bad)}")
    own = {n for n, s in origin.items() if s == "own"}
    if own != OWN_SKILLS:
        rep.fail("происхождение",
                 f"собственные навыки в карте {sorted(own)} != {sorted(OWN_SKILLS)}")
    rep.note(f"происхождение: {len(origin)} навыков, источников {len(set(origin.values()))}")


def check_doc_counts(rep: Report, dirs: list[str]) -> None:
    """4. Числа в документации == факт дерева."""
    total = len(dirs)
    readme_path = os.path.join(ROOT, "README.md")
    if not os.path.isfile(readme_path):
        rep.fail("числа", "нет README.md")
        return
    readme = open(readme_path, encoding="utf-8").read()
    m = re.search(r"\*\*(\d+)\s+навык", readme)
    if not m:
        rep.fail("числа", "README: нет утверждения о числе навыков (**N навыков**)")
    elif int(m.group(1)) != total:
        rep.fail("числа", f"README: заявлено {m.group(1)} навыков, в дереве {total}")
    # единый источник чисел: если stats.json разошёлся с деревом, документы
    # сверяются не с фактом, а с устаревшим снимком
    stats_path = os.path.join(ROOT, "scripts", "stats.json")
    if os.path.isfile(stats_path):
        with open(stats_path, encoding="utf-8") as f:
            stats = json.load(f)
        if stats.get("total") != total:
            rep.fail("числа", f"scripts/stats.json: total={stats.get('total')}, в дереве {total}")
        if stats.get("top_level") != total - stats.get("nested", 0):
            rep.fail("числа", "scripts/stats.json: top_level + nested != total")
        # Суммы по источникам обязаны сходиться с итогами. Рукописный stats.json уже
        # разошёлся так (у OpenClaw 779 при факте 777: сумма 1515 при 1513) — этого
        # не видел ни один документ и ни одна проверка, пока аудитор не сравнил.
        for key, expect in (("by_source_top", stats.get("top_level")),
                            ("by_source_all", stats.get("total"))):
            got = sum((stats.get(key) or {}).values())
            if got != expect:
                rep.fail("числа", f"scripts/stats.json: сумма {key} = {got}, "
                                  f"а всего навыков {expect} — пересобери scripts/build_stats.py")
        # состав scripts/ — тоже число в документах: было «9», а фактически 12
        # (семь .py, установщик, четыре JSON-манифеста). Считается генератором.
        sc = stats.get("scripts") or {}
        if not sc:
            rep.fail("числа", "stats.json: нет раздела scripts")
        else:
            real = {"py": 0, "sh": 0, "js": 0, "json": 0}
            for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, "scripts")):
                dirnames[:] = [d for d in dirnames if d != "__pycache__"]
                for fn in filenames:
                    if fn == "stats.json":
                        continue
                    for ext in (".py", ".sh", ".mjs", ".js", ".json"):
                        if fn.endswith(ext):
                            real["js" if ext in (".mjs", ".js") else ext[1:]] += 1
                            break
            for key, expect in real.items():
                if sc.get(key) != expect:
                    rep.fail("числа", f"stats.json: scripts.{key}={sc.get(key)}, "
                                      f"в дереве {expect} — пересобери scripts/build_stats.py")
            if not re.search(rf"(?<![\d.]){sc.get('total')}(?![\d.])",
                             open(os.path.join(ROOT, "agent-description.md"),
                                  encoding="utf-8").read()):
                rep.fail("числа", f"agent-description.md не называет число файлов "
                                  f"в scripts/ ({sc.get('total')})")
        # stats.json обязан воспроизводиться из дерева: расхождение означает, что
        # документы сверяются с устаревшим снимком
        gen = os.path.join(ROOT, "scripts", "build_stats.py")
        if os.path.isfile(gen):
            proc = subprocess.run([sys.executable, "-B", gen, "--check"],
                                  cwd=ROOT, capture_output=True, text=True)
            if proc.returncode != 0:
                rep.fail("числа", "scripts/stats.json не воспроизводится: "
                                  f"{(proc.stdout or proc.stderr).strip()[:200]}")
        else:
            rep.fail("числа", "нет scripts/build_stats.py — stats.json нечем пересобрать")
        # OpenClaw: с учётом вложенных у него больше, чем в верхнеуровневом счёте
        row = next((l for l in readme.splitlines()
                    if "OpenClaw-Medical-Skills" in l and l.startswith("|")), "")
        if row and str(stats["by_source_all"].get("OpenClaw")) not in row:
            rep.fail("числа", f"README: у OpenClaw не показано итоговое число "
                              f"с вложенными ({stats['by_source_all'].get('OpenClaw')})")
    else:
        rep.fail("числа", "нет scripts/stats.json — единого источника чисел")
    # Бейдж несёт число ДВАЖДЫ: в ссылке (badge/Skills-1540) и в тексте
    # (Skills-1540-green). Проверяем оба вхождения — расхождение между ними
    # и есть та ошибка, которую не видно глазами.
    for num in re.findall(r"badge/Skills-(\d+)", readme) + re.findall(r"Skills-(\d+)-", readme):
        if int(num) != total:
            rep.fail("числа", f"README: бейдж Skills-{num} != {total}")

    ad_path = os.path.join(ROOT, "agent-description.md")
    if os.path.isfile(ad_path):
        ad = open(ad_path, encoding="utf-8").read()
        for num in re.findall(r"\| Навыки \| (\d+)", ad):
            if int(num) != total:
                rep.fail("числа", f"agent-description: Навыки {num} != {total}")
        for num in re.findall(r"(\d+)\s+навыков? из четырёх", ad):
            if int(num) != total:
                rep.fail("числа", f"agent-description: заявлено {num}, в дереве {total}")
    else:
        rep.fail("числа", "нет agent-description.md")
    rep.note(f"числа: {total} навыков сверено с README и agent-description.md")


def check_licenses(rep: Report) -> None:
    """5. Лицензии каждого источника на месте, NOTICE их называет."""
    if not os.path.isdir(THIRD_PARTY):
        rep.fail("лицензии", "нет каталога THIRD_PARTY_LICENSES/")
        return
    files = sorted(os.listdir(THIRD_PARTY))
    if not files:
        rep.fail("лицензии", "THIRD_PARTY_LICENSES/ пуст")
    for f in files:
        p = os.path.join(THIRD_PARTY, f)
        if os.path.getsize(p) < 500:
            rep.fail("лицензии", f"{f}: подозрительно мал ({os.path.getsize(p)} байт) — текст лицензии неполный?")
    notice_path = os.path.join(ROOT, "NOTICE.md")
    if not os.path.isfile(notice_path):
        rep.fail("лицензии", "нет NOTICE.md")
        return
    notice = open(notice_path, encoding="utf-8").read()
    for label, (repo, lic_file) in SOURCES.items():
        if repo not in notice:
            rep.fail("лицензии", f"NOTICE не упоминает источник {repo}")
        # OpenClaw файла лицензии не имеет — это оговорено в NOTICE отдельным
        # пунктом, поэтому отсутствие файла для него не дефект, а факт.
        if lic_file and lic_file not in files:
            rep.fail("лицензии", f"в THIRD_PARTY_LICENSES/ нет {lic_file} (источник {label})")
    if "OpenClaw" not in notice or "LICENSE" not in notice:
        rep.fail("лицензии", "NOTICE не содержит оговорки про отсутствие файла LICENSE у OpenClaw")
    rep.note(f"лицензии: {len(files)} файлов, NOTICE называет {len(SOURCES)} источников")


def check_short_docs(rep: Report) -> None:
    """15. Короткие документы не противоречат каноническому разделу.

    Ловушка, которую нашёл внешний аудит: ограничения лицензий были описаны
    только в README и NOTICE, а AGENTS.md и INSTALL.md говорили просто
    «MIT и Apache-2.0». Агент, читающий AGENTS.md по инструкции, получал
    неверную картину — и не знал, что 308 навыков нельзя считать свободными.

    Проверяются два свойства каждого короткого документа: (а) он ссылается на
    канонический NOTICE, (б) он называет ключевые ограничения или отправляет
    за ними туда. Плюс собственные навыки перечислены полностью — пропуск
    третьего был ровно таким же дефектом.
    """
    with open(os.path.join(ROOT, "scripts", "stats.json"), encoding="utf-8") as f:
        stats = json.load(f)
    own = set(stats["own"])
    for doc in ("AGENTS.md", "INSTALL.md", "agent-description.md"):
        path = os.path.join(ROOT, doc)
        if not os.path.isfile(path):
            rep.fail("документы", f"нет {doc}")
            continue
        body = open(path, encoding="utf-8").read()
        if "NOTICE.md" not in body:
            rep.fail("документы", f"{doc}: нет ссылки на NOTICE.md (канонический раздел лицензий)")
        if "308" not in body:
            rep.fail("документы", f"{doc}: не названо ограничение (308 проприетарных навыков)")
        missing = [n for n in own if n not in body]
        if missing:
            rep.fail("документы", f"{doc}: не упомянуты собственные навыки {missing}")
    rep.note(f"документы: AGENTS/INSTALL/agent-description называют ограничения, "
             f"ссылаются на NOTICE и перечисляют {len(own)} собственных навыка")


def check_links(rep: Report) -> None:
    """6. Относительные ссылки в документации резолвятся."""
    link_re = re.compile(r"\[[^\]]+\]\(([^)#\s]+)\)")
    checked = 0
    for doc in DOCS:
        path = os.path.join(ROOT, doc)
        if not os.path.isfile(path):
            continue
        body = open(path, encoding="utf-8").read()
        for target in set(link_re.findall(body)):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            checked += 1
            if not os.path.exists(os.path.join(ROOT, target.rstrip("/"))):
                rep.fail("ссылки", f"{doc}: ссылка ведёт в никуда → {target}")
    rep.note(f"ссылки: проверено {checked} относительных ссылок в {len(DOCS)} документах")


def check_skill_refs(rep: Report) -> None:
    """7. У собственных навыков битых ссылок быть не должно."""
    ref_re = re.compile(r"`?((?:references|scripts|templates|assets|prompts|data)/[A-Za-z0-9_./-]+\.[A-Za-z0-9]+)`?")
    for name in sorted(OWN_SKILLS):
        skill_md = os.path.join(SKILLS, name, "SKILL.md")
        if not os.path.isfile(skill_md):
            rep.fail("ссылки навыков", f"нет {name}/SKILL.md")
            continue
        body = open(skill_md, encoding="utf-8", errors="replace").read()
        for ref in sorted(set(ref_re.findall(body))):
            if not os.path.exists(os.path.join(SKILLS, name, ref)):
                rep.fail("ссылки навыков", f"{name}: битая ссылка {ref}")
    rep.note(f"ссылки навыков: собственные ({', '.join(sorted(OWN_SKILLS))}) чисты")


def check_diagram(rep: Report) -> None:
    """8. Диаграмма: спецификация и артефакт согласованы."""
    spec = os.path.join(ROOT, "docs", "vector-health.architecture.json")
    html = os.path.join(ROOT, "docs", "vector-health.architecture.html")
    if not os.path.isfile(spec):
        rep.fail("диаграмма", "нет docs/vector-health.architecture.json")
        return
    if not os.path.isfile(html):
        rep.fail("диаграмма", "нет docs/vector-health.architecture.html — доставь через archify deliver")
        return
    with open(spec, encoding="utf-8") as f:
        data = json.load(f)
    body = open(html, encoding="utf-8").read()
    title = (data.get("meta") or {}).get("title")
    if not title:
        rep.fail("диаграмма", "в спецификации нет meta.title")
    elif title not in body:
        rep.fail("диаграмма", f"заголовок «{title}» из спецификации отсутствует в HTML — пересобери artifact")
    for view in (data.get("meta") or {}).get("views", []) or []:
        label = view.get("label")
        if label and label not in body:
            rep.fail("диаграмма", f"подпись вида «{label}» отсутствует в HTML — пересобери artifact")
    rep.note(f"диаграмма: заголовок и {len((data.get('meta') or {}).get('views', []) or [])} подписей видов сверены с HTML")


def check_taxonomy_completeness(rep: Report) -> None:
    """14. Таксономия КТ: колонки сверяются с апстримом, классы MERLIN полны.

    Два дефекта, которые в такой таблице не видны глазом: (а) колонки разошлись
    с источником — тогда китайский ключ перестаёт находить класс в выводе модели;
    (б) в разборе внешнего теста перечислены не все классы — тогда таблица
    выглядит полной, а часть провалов просто не показана.

    Сверка идёт с ЖИВЫМ апстримом, поэтому проверка пропускается без сети и
    сообщает об этом (молчаливый пропуск выглядел бы как успех).
    """
    base = os.path.join(SKILLS, "abdominal-ct-findings", "references")
    tax_path = os.path.join(base, "radar-taxonomy.json")
    qm_path = os.path.join(base, "quality-metrics.md")
    if not os.path.isfile(tax_path):
        rep.fail("таксономия", "нет references/radar-taxonomy.json")
        return
    with open(tax_path, encoding="utf-8") as f:
        tax = json.load(f)
    cols = [x["csv_column_zh_en"] for x in tax["findings"]]
    if len(set(cols)) != len(cols):
        dups = [c for c in set(cols) if cols.count(c) > 1]
        rep.fail("таксономия", f"колонки-дубликаты: {dups[:3]}")
    if tax.get("outside_abdomen_total") != sum(1 for o in tax.get("organs", []) if o.get("outside_abdomen")):
        rep.fail("таксономия", "outside_abdomen_total не совпадает с числом помеченных структур")

    # живая сверка с апстримом (сеть не обязательна — тогда честно сообщаем)
    try:
        url = ("https://raw.githubusercontent.com/alibaba-damo-academy/damo-radar/"
               "HEAD/results/RADAR_infer_results_demo.csv")
        req = urllib.request.Request(url, headers={"User-Agent": "vector-health-validate"})
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read().decode("utf-8-sig")
        upstream = next(csv.reader(io.StringIO(body)))[1:]
        if upstream != cols:
            only_up = [c for c in upstream if c not in cols]
            only_us = [c for c in cols if c not in upstream]
            rep.fail("таксономия",
                     f"колонки разошлись с апстримом: нет у нас {only_up[:3]}, лишние {only_us[:3]}")
        else:
            rep.note(f"таксономия: {len(cols)} колонок совпадают с апстримом побайтово и по порядку")
        # классы в разборе внешнего теста
        merlin_url = ("https://raw.githubusercontent.com/alibaba-damo-academy/"
                      "damo-radar/HEAD/docs/INFERENCE.md")
        req2 = urllib.request.Request(merlin_url, headers={"User-Agent": "vector-health-validate"})
        with urllib.request.urlopen(req2, timeout=60) as r2:
            doc = r2.read().decode("utf-8")
        classes = re.findall(r"^([a-z_]+)\s+[01]\.\d+\s*$", doc, re.MULTILINE)
        with open(qm_path, encoding="utf-8") as f:
            qm = f.read()
        missing = [c for c in classes if c not in qm]
        if missing:
            rep.fail("таксономия", f"в разборе внешнего теста нет классов: {missing[:5]} "
                                   f"({len(classes) - len(missing)} из {len(classes)})")
        else:
            rep.note(f"таксономия: все {len(classes)} классов внешнего теста разобраны поимённо")
    except Exception as e:  # noqa: BLE001 — без сети проверку не выполняем
        rep.note(f"таксономия: сверка с апстримом пропущена (нет сети: {type(e).__name__}) — "
                 f"локально проверено {len(cols)} колонок, {tax.get('findings_total')} находок")


def check_duplicates(rep: Report) -> None:
    """16. Дубли по содержимому — учтённый список, а не находка.

    Апстримы держат один навык в двух местах: «плоская» копия в корне коллекции
    плюс версия внутри каталога-контейнера (spatial-agent и
    spatial-transcriptomics-analysis/SpatialAgent — байт-в-байт одно и то же).
    Удалять одну копию нельзя: сломается ссылка из другого навыка, а
    синхронизация вернёт файл при следующем прогоне как «удалённый апстримом».

    Проверка нужна затем, чтобы НОВЫЙ дубль не появился незаметно: он означает
    либо ошибку сборки, либо переименование в апстриме.
    """
    import hashlib
    listed_path = os.path.join(ROOT, "scripts", "name-duplicates.json")
    if not os.path.isfile(listed_path):
        rep.fail("дубли", "нет scripts/name-duplicates.json — списка идентичных навыков")
        return
    with open(listed_path, encoding="utf-8") as f:
        listed = json.load(f)
    known = {tuple(sorted(d["files"])) for d in listed.get("duplicates", [])}

    def sha(path: str) -> str:
        with open(path, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()

    seen: dict[str, list[str]] = {}
    for f in sorted(pathlib.Path(SKILLS).rglob("SKILL.md")):
        seen.setdefault(sha(str(f)), []).append(str(f.relative_to(SKILLS)).replace(os.sep, "/"))
    actual = {tuple(sorted(v)) for v in seen.values() if len(v) > 1}
    new = sorted(actual - known)
    gone = sorted(known - actual)
    if new:
        rep.fail("дубли", f"новые идентичные навыки: {[n[:2] for n in new[:3]]} — "
                          f"обнови scripts/name-duplicates.json или разберись с причиной")
    if gone:
        rep.fail("дубли", f"идентичность исчезла: {[g[:2] for g in gone[:3]]} — обнови список")
    rep.note(f"дубли: {len(actual)} пар идентичных навыков, все учтены в name-duplicates.json")


def check_clinical_claims(rep: Report) -> None:
    """17. Клинический навык обязан нести оговорку и не выдавать неподтверждённое.

    `atrial-fibrillation-treatment` — тактика лечения, а не справочник: он читается
    как рекомендация. Два обязательных свойства: (а) оговорка «для специалиста, не
    для самолечения» стоит в начале, а не в конце; (б) годы публикаций испытаний
    не выдуманы — либо подтверждены (сверено с первоисточником), либо помечены
    «к сверке». Непроверяемый год в клиническом тексте выглядит как доказательство,
    которого автор не проверял.

    Проверка нужна потому, что этот навык — единственный в библиотеке, который
    предписывает действия, и ошибка в нём дороже всех остальных.
    """
    path = os.path.join(SKILLS, "atrial-fibrillation-treatment", "SKILL.md")
    if not os.path.isfile(path):
        rep.fail("клиника", "нет skills/atrial-fibrillation-treatment/SKILL.md")
        return
    body = open(path, encoding="utf-8").read()
    head = body[:3000]
    for needle in ("не для самолечения", "не заменяет клиническое решение"):
        if needle not in head:
            rep.fail("клиника", f"оговорка «{needle}» не найдена в начале навыка")
    if "## References" not in body:
        rep.fail("клиника", "нет раздела References со ссылками на рекомендации")
    # раздел References не должен содержать годов, не помеченных как подтверждённые
    refs = body.split("## References", 1)[1]
    unconfirmed = re.findall(r"\*\*(EAST-AFNET 4|EARLY-AF|STOP-AF First|CASTLE-AF|CASTLE-HTx|ADVENT|AFFIRM)\*\*\s*—\s*(?:NEJM|JACC|Nature)\s*\d{4}", refs)
    if unconfirmed:
        rep.fail("клиника", f"неподтверждённые годы в References: {unconfirmed[:3]} — "
                            f"сверь с первоисточником или пометь «к сверке»")
    rep.note("клиника: оговорка на месте, годы испытаний либо подтверждены, либо помечены")


def check_restricted_docs(rep: Report) -> None:
    """Числа ограниченных лицензий в документах совпадают с деревом.

    Проверка появилась после внешнего аудита: в шести документах стояло «8 навыков
    Anthropic» при фактических 9 — офисных навыков девять, девятый `PPTX-Skill`
    никто не заметил. Списки берутся из scripts/stats.json (генератор считает их из
    дерева), поэтому ручная правка числа в документе роняет сборку, а не расходится
    молча.
    """
    stats_path = os.path.join(ROOT, "scripts", "stats.json")
    if not os.path.isfile(stats_path):
        rep.fail("лицензии", "нет scripts/stats.json — числа ограничений неоткуда взять")
        return
    with open(stats_path, encoding="utf-8") as f:
        stats = json.load(f)
    restricted = stats.get("restricted") or {}
    named = stats.get("restricted_skills") or {}
    if not restricted:
        rep.fail("лицензии", "stats.json не содержит раздела restricted")
        return

    # Число обязано стоять В ТОЙ ЖЕ СТРОКЕ, что и название вида ограничения.
    # Искать число где угодно в документе недостаточно: мутация «заменить 9 на 8
    # в строке про Anthropic» проходила, потому что девятка встречалась в других
    # строках. Проверяем построчно, для таблиц — по строкам `| … |` и `<tr>`.
    # Маркер — ярлык вида ограничения, как он пишется в таблицах. «некоммерческой
    # лицензией» в обычном тексте (например, про веса модели RADAR) ограничением
    # НАВЫКА не является, поэтому текст вне таблиц не учитывается вовсе.
    KIND_MARKERS = {
        "proprietary_hat": ("проприетарн", "proprietary"),
        "anthropic": ("anthropic",),
        "non_commercial": ("non-commercial",),
    }
    docs = ("README.md", "NOTICE.md", "AGENTS.md", "INSTALL.md",
            "agent-description.md", os.path.join("docs", "index.html"))
    for kind, count in restricted.items():
        markers = KIND_MARKERS.get(kind, (kind.replace("_", " "),))
        for doc in docs:
            path = os.path.join(ROOT, doc)
            if not os.path.isfile(path):
                continue
            # Проверяются ВСЕ строки про этот вид ограничения, а не «хотя бы одна
            # верная»: иначе правка в таблице состава остаётся незамеченной, пока
            # в другой строке (например, в журнале изменений) случайно стоит верное
            # число. Исключение — журнал изменений: там числа зафиксированы на дату
            # записи и по определению историчны.
            rows = 0
            for num, line in enumerate(open(path, encoding="utf-8"), 1):
                stripped = line.strip()
                # только табличные строки: markdown-таблица или html-строка
                if not (stripped.startswith("|") or "<tr" in stripped):
                    continue
                low = line.lower()
                if not any(m in low for m in markers):
                    continue
                if re.match(r"\|\s*\d{4}-\d{2}-\d{2}\s*\|", stripped):
                    continue  # строка журнала изменений
                rows += 1
                plain = re.sub(r"[*_`]+", "", line)
                plain = re.sub(r"</?[a-z][^>]*>", " ", plain)
                if not re.search(rf"(?<![\d.]){count}(?![\d.])", plain):
                    rep.fail("лицензии", f"{doc}:{num}: в строке про «{kind}» нет числа "
                                         f"{count} — документ разошёлся с деревом")
            if not rows:
                # удаление строки целиком — тоже расхождение: документ обещает
                # назвать ограничение, а назвать перестал
                rep.fail("лицензии", f"{doc}: нет ни одной строки таблицы про «{kind}» — "
                                     f"раздел ограничений из документа исчез")
    notice_path = os.path.join(ROOT, "NOTICE.md")
    notice = open(notice_path, encoding="utf-8").read() if os.path.isfile(notice_path) else ""
    for kind, names in named.items():
        if kind == "proprietary_hat":
            continue  # 308 имён в NOTICE не перечисляются, там только число
        # NOTICE называет офисные навыки перечнем (`xlsx`, `pdf`, … и варианты
        # `-official`), а не поимённо каждую папку: `docx-official` покрыт записью
        # «и их `-official` варианты». Поэтому принимаем либо имя навыка, либо
        # указание на группу вариантов.
        for name in names:
            short = name.split("/")[-1]
            if short in notice or "`-official`" in notice or "-official" in notice:
                continue
            rep.fail("лицензии", f"NOTICE не называет навык с ограничением "
                                 f"«{kind}»: {name}")
    rep.note("лицензии: числа в шести документах совпадают с деревом — "
             f"проприетарных {restricted.get('proprietary_hat')}, "
             f"Anthropic {restricted.get('anthropic')}, "
             f"NC {restricted.get('non_commercial')}")


def check_diagram_numbers(rep: Report) -> None:
    """Числа в спецификации диаграммы совпадают с деревом.

    Диаграмма — тоже документ: в ней жило «1540 описаний» при фактических 1541, и
    увидеть это можно было только в живом артефакте. Проверяем, что итоговое число
    названо, и что рядом со словами «навык»/«описание» не стоит чужое четырёхзначное.
    """
    spec_path = os.path.join(ROOT, "docs", "vector-health.architecture.json")
    if not os.path.isfile(spec_path):
        rep.fail("диаграмма", "нет спецификации docs/vector-health.architecture.json")
        return
    spec_text = open(spec_path, encoding="utf-8").read()
    with open(os.path.join(ROOT, "scripts", "stats.json"), encoding="utf-8") as f:
        stats = json.load(f)
    total = stats["total"]
    for m in re.finditer(r"(\d{3,4})\s*(описан|навык|навыков|skills?)", spec_text):
        num = int(m.group(1))
        if 1000 < num < 2000 and num not in (stats["total"], stats["top_level"]):
            rep.fail("диаграмма", f"в спецификации «{num} {m.group(2)}», "
                                  f"а в дереве {total} навыков")
    if str(total) not in spec_text:
        rep.fail("диаграмма", f"спецификация не называет итоговое число навыков ({total})")
    rep.note(f"диаграмма: числа согласованы с деревом ({total})")


def check_broken_refs_report(rep: Report) -> None:
    """Числа инвентаря битых ссылок в README совпадают с самим инвентарём.

    Инвентарь — документ о дефектах; если его числа в README расходятся с отчётом,
    читатель получает неверную картину масштаба. Случай не гипотетический: после
    расширения шаблона ссылок число стало 515, а в README ещё стояло 485.
    """
    report = os.path.join(ROOT, "docs", "broken-refs.md")
    if not os.path.isfile(report):
        rep.fail("ссылки", "нет docs/broken-refs.md — инвентарь ссылок не сгенерирован")
        return
    text = open(report, encoding="utf-8").read()
    m = re.search(r"Ссылок на файлы в дереве: (\d+); на месте: (\d+); битых: (\d+)", text)
    if not m:
        rep.fail("ссылки", "docs/broken-refs.md: не найдена строка со сводкой")
        return
    total, ok, broken = (int(x) for x in m.groups())
    # Категории в отчёте обязаны сходиться с числом битых: разбор, где сумма
    # частей меньше целого, скрывает непроверенную часть.
    cats = {k.strip(): int(v) for k, v in re.findall(r"^\| ([^|]+?) \| (\d+) \|", text, re.M)}
    known = ("Пример пути в коде", "Восстановимо", "Тяжёлые данные",
             "Внешний ресурс", "В корне источника", "Унаследованное")
    s = sum(cats.get(k, 0) for k in known)
    if s != broken:
        rep.fail("ссылки", f"docs/broken-refs.md: категории дают {s}, а битых {broken} — "
                           f"часть ссылок не разобрана")
    # У каждой непустой категории должна быть своя секция со строками: сводка без
    # разбора — обещание причины, которой читатель не найдёт.
    # Короткое имя в таблице и заголовок секции различаются («В корне источника» /
    # «Файл в корне репозитория-источника (вне каталога навыка)»), поэтому сверяем по
    # соответствию ключ→короткое имя→заголовок, взятому из самого генератора: держать
    # это соответствие в двух местах — тот же дефект, который здесь и чинится.
    sections_by_short: dict[str, str] = {}
    try:
        sys.path.insert(0, os.path.join(ROOT, "scripts"))
        import broken_refs as br_mod  # noqa: PLC0415 — нужен только для имён категорий
        sections_by_short = {short: title for _key, short, title, _m in br_mod.CATEGORIES}
    except Exception:  # noqa: BLE001 — имена категорий не критичны для остальных проверок
        pass
    for name, count in cats.items():
        if name not in known or count == 0:
            continue
        title = sections_by_short.get(name)
        if title and f"## {title}" in text:
            continue
        # запасной вариант: заголовок начинается с короткого имени
        if not [h for h in re.findall(r"^## (.+)$", text, re.M) if h.startswith(name)]:
            rep.fail("ссылки", f"docs/broken-refs.md: у категории «{name}» ({count}) "
                               f"нет секции со строками")
    if ok + broken != total:
        rep.fail("ссылки", f"docs/broken-refs.md: на месте {ok} + битых {broken} != {total}")
    readme = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
    if not re.search(rf"(?<![\d.]){broken}(?![\d.])\s+битых", readme):
        rep.fail("ссылки", f"README не называет число битых ссылок ({broken}) — "
                           f"пересобери docs/broken-refs.md и обнови README")
    rep.note(f"ссылки: инвентарь {total} ссылок, битых {broken}, README согласован")


def check_secrets(rep: Report) -> None:
    """9. Живых секретов в дереве нет."""
    hits = []
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", "node_modules")]
        for fn in files:
            fp = os.path.join(root, fn)
            rel = "/" + os.path.relpath(fp, ROOT).replace(os.sep, "/")
            if any(x in rel for x in SECRET_EXEMPT):
                continue
            if os.path.getsize(fp) > 2_000_000:
                continue
            try:
                text = open(fp, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            if SECRET_RE.search(text):
                hits.append(rel)
    if hits:
        rep.fail("секреты", f"найдены живые формы секретов: {hits[:5]}")
    rep.note("секреты: живых форм ключей не найдено")


def check_language_layers(rep: Report) -> None:
    """13. Двуязычный слой: китайский оригинал — ТОЛЬКО в полях `*_zh`.

    В `references/radar-taxonomy.json` рядом лежат оригинал апстрима и наш
    перевод. Если имя поля не говорит, что это источник, читатель не может
    отличить цитату от собственного текста, а переводчик — понять, что можно
    менять. Правило: CJK-символы допустимы в `finding_zh`/`organ_zh`/
    `csv_column_zh_en` и больше нигде (плюс в самих вендоренных навыках,
    которые не переводились).
    """
    path = os.path.join(SKILLS, "abdominal-ct-findings", "references", "radar-taxonomy.json")
    if not os.path.isfile(path):
        rep.fail("языки", "нет references/radar-taxonomy.json — двуязычного списка находок")
        return
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    allowed = {"finding_zh", "organ_zh", "csv_column_zh_en"}
    bad = []
    def walk(node, field=None):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, k)
        elif isinstance(node, list):
            for v in node:
                walk(v, field)
        elif isinstance(node, str) and CJK_RE.search(node) and field not in allowed:
            bad.append((field, node[:40]))
    walk(data)
    if bad:
        rep.fail("языки", f"CJK вне полей-источников ({len(bad)}): {bad[:3]}")
    if data.get("findings_total") != len(data.get("findings", [])):
        rep.fail("языки", f"findings_total={data.get('findings_total')} при {len(data.get('findings', []))} записях")
    if data.get("organs_total") != len(data.get("organs", [])):
        rep.fail("языки", f"organs_total={data.get('organs_total')} при {len(data.get('organs', []))} органах")
    empty = [f.get("finding_ru") for f in data.get("findings", []) if not f.get("finding_ru")]
    if empty:
        rep.fail("языки", f"{len(empty)} находок без русского перевода")
    rep.note(f"языки: таксономия {data.get('findings_total')} находок × "
             f"{data.get('organs_total')} органов, CJK только в полях-источниках")

    # Таблица в SKILL.md — это то, что читает человек; JSON — то, чем пользуется
    # машина. Разойдясь, они дают два разных ответа на «какие находки бывают»,
    # и заметить это глазами нельзя: обе выглядят правдоподобно.
    skill_md = os.path.join(SKILLS, "abdominal-ct-findings", "SKILL.md")
    if not os.path.isfile(skill_md):
        rep.fail("языки", "нет SKILL.md у abdominal-ct-findings")
        return
    body = open(skill_md, encoding="utf-8").read()
    missing = [f.get("finding_ru") for f in data.get("findings", [])
               if f"| {f.get('finding_ru')} |" not in body]
    if missing:
        rep.fail("языки", f"{len(missing)} находок есть в JSON, но выпали из таблицы SKILL.md: "
                          f"{missing[:5]}")
    org_missing = [o.get("organ_ru") for o in data.get("organs", []) if o.get("organ_ru") not in body]
    if org_missing:
        rep.fail("языки", f"структуры есть в JSON, но не упомянуты в SKILL.md: {org_missing[:3]}")


def check_cjk(rep: Report) -> None:
    """10. Собственный текст репозитория — без CJK (навыки на языке источника)."""
    hits = []
    for fn in DOCS:
        path = os.path.join(ROOT, fn)
        if not os.path.isfile(path):
            continue
        text = open(path, encoding="utf-8").read()
        if CJK_RE.search(text):
            hits.append(fn)
    for root, dirs, files in os.walk(os.path.join(ROOT, "scripts")):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for fn in files:
            if not fn.endswith(".py"):
                continue
            text = open(os.path.join(root, fn), encoding="utf-8", errors="ignore").read()
            if CJK_RE.search(text):
                hits.append(f"scripts/{fn}")
    for fn in hits:
        rep.fail("язык", f"{fn}: CJK-символы в собственном тексте (навыки исключены, docs — исключены)")
    rep.note("язык: собственный текст без CJK")


def check_restricted(rep: Report) -> None:
    """11. Ограниченные лицензии зафиксированы и не выросли незаметно.

    Часть вендоренных навыков несёт проприетарную лицензию внутри своего текста
    (OpenClaw держит шапку «proprietary and confidential … All Rights Reserved»
    при MIT-бейдже в README). Это не наш дефект, но и не то, что можно потерять:
    если число таких навыков изменится, документ `NOTICE.md` перестанет
    соответствовать дереву, и его читатель получит неверную картину.
    """
    path = os.path.join(ROOT, "scripts", "restricted-licenses.json")
    if not os.path.isfile(path):
        rep.fail("лицензии", "нет scripts/restricted-licenses.json — список ограниченных лицензий")
        return
    with open(path, encoding="utf-8") as f:
        recorded = json.load(f)
    actual = []
    for root, dirs, files in os.walk(SKILLS):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        if "SKILL.md" not in files:
            continue
        text = open(os.path.join(root, "SKILL.md"), encoding="utf-8", errors="replace").read()
        low = text.lower()
        if "proprietary and confidential" in low and "all rights reserved" in low:
            actual.append(os.path.relpath(root, SKILLS).replace(os.sep, "/"))
    if len(actual) != len(recorded):
        rep.fail("лицензии",
                 f"навыков с проприетарной шапкой {len(actual)}, в списке {len(recorded)} "
                 f"— обнови scripts/restricted-licenses.json и NOTICE.md")
    notice_path = os.path.join(ROOT, "NOTICE.md")
    notice = open(notice_path, encoding="utf-8").read() if os.path.isfile(notice_path) else ""
    for needle in ("All Rights Reserved", "Non-Commercial", "Anthropic"):
        if needle not in notice:
            rep.fail("лицензии", f"NOTICE не упоминает ограничение «{needle}»")
    rep.note(f"лицензии: ограниченных навыков {len(actual)} (в списке {len(recorded)}), NOTICE их называет")


def check_assets(rep: Report) -> None:
    """12. Изображения в документации и на сайте резолвятся.

    Ловушка, на которую легко наступить при настройке Pages: файл ассета
    исключён из сборки сайта (`exclude:` в `_config.yml`), и картинка на
    опубликованной странице отдаёт 404, хотя в репозитории лежит. Локально всё
    выглядит целым, поэтому проверка нужна на уровне связи «документ ссылается
    на файл» и «файл не исключён из сайта».
    """
    img_re = re.compile(r'<img[^>]+src="([^"]+)"')
    cfg_path = os.path.join(ROOT, "_config.yml")
    excluded = []
    if os.path.isfile(cfg_path):
        text = open(cfg_path, encoding="utf-8").read()
        block = re.search(r"^exclude:\n((?:[ \t]+-.*\n)+)", text, re.MULTILINE)
        if block:
            excluded = [l.strip().lstrip("- ").rstrip("/") for l in block.group(1).splitlines()]
    for doc in DOCS:
        path = os.path.join(ROOT, doc)
        if not os.path.isfile(path):
            continue
        body = open(path, encoding="utf-8").read()
        for src in img_re.findall(body):
            if src.startswith(("http://", "https://", "data:")):
                continue
            local = os.path.join(ROOT, src)
            if not os.path.isfile(local):
                rep.fail("ассеты", f"{doc}: изображение {src} не найдено в репозитории")
                continue
            top = src.split("/")[0]
            if any(e == top or e == src for e in excluded):
                rep.fail("ассеты", f"{doc}: {src} есть в репозитории, но исключён из сайта "
                                    f"(_config.yml exclude: {top}) — на Pages будет 404")
    rep.note(f"ассеты: изображения в документах существуют и не исключены из сайта "
             f"(исключено {len(excluded)} записей)")


def main() -> int:
    rep = Report()
    dirs = check_skills(rep)
    check_index(rep, dirs)
    check_origin(rep)
    check_doc_counts(rep, dirs)
    check_licenses(rep)
    check_restricted(rep)
    check_links(rep)
    check_short_docs(rep)
    check_assets(rep)
    check_skill_refs(rep)
    check_diagram(rep)
    check_duplicates(rep)
    check_clinical_claims(rep)
    check_restricted_docs(rep)
    check_broken_refs_report(rep)
    check_diagram_numbers(rep)
    check_secrets(rep)
    check_cjk(rep)
    check_language_layers(rep)
    check_taxonomy_completeness(rep)

    for note in rep.notes:
        print(f"  · {note}")
    if rep.errors:
        print(f"\nПРОВАЛ: {len(rep.errors)} проблем")
        for e in rep.errors:
            print(f"  {e}")
        return 1
    print(f"\nOK: все проверки пройдены ({len(rep.notes)} — счёт в notes).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
