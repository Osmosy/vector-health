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

Exit 0 — всё сходится; exit 1 — есть расхождения (печатаются с адресом проблемы).
Любая проверка, которая не смогла выполниться, тоже даёт exit 1: «проверка не
запустилась» не должно выглядеть как «проверка прошла».
"""
import json
import os
import re
import subprocess
import sys

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
    check_assets(rep)
    check_skill_refs(rep)
    check_diagram(rep)
    check_secrets(rep)
    check_cjk(rep)
    check_language_layers(rep)

    for note in rep.notes:
        print(f"  · {note}")
    if rep.errors:
        print(f"\nПРОВАЛ: {len(rep.errors)} проблем")
        for e in rep.errors:
            print(f"  {e}")
        return 1
    print(f"\nOK: все проверки пройдены ({len(rep.notes)} проверок).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
