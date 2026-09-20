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
import collections
import pathlib
import posixpath
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
# Список берётся из scripts/stats.json, а не зашит здесь: в зашитом было ДВА имени
# из трёх, и третий навык (abdominal-ct-findings) не проверялся на битые ссылки —
# режим --strict-own молча считал его чужим. Один источник, как и везде.
def own_skills() -> set[str]:
    path = os.path.join(ROOT, "scripts", "stats.json")
    if os.path.isfile(path):
        try:
            with open(path, encoding="utf-8") as f:
                own = json.load(f).get("own") or []
            if own:
                return set(own)
        except (OSError, json.JSONDecodeError):
            pass
    return {"dicom-vlm-analysis", "atrial-fibrillation-treatment"}


OWN_SKILLS = own_skills()

# Для категории «в корне источника»: путь файла в дереве апстрима —
# чтобы отчёт давал не только диагноз, но и место, откуда файл брать.
REPO_LEVEL_PATHS: dict[tuple[str, str], str] = {}
EXTERNAL_URLS: dict[tuple[str, str], str] = {}
EXTERNAL_STATE: dict[tuple[str, str], tuple[str, str]] = {}

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


def upstream_blobs() -> dict[str, dict[str, tuple[str, int]]]:
    """{источник: {путь: (blob sha, размер)}} по HEAD каждого апстрима.

    Нужны ОБА поля, и sha — не украшение. Раньше здесь был только размер, и в
    классификации «общий файл / чужой» версии считались ПО РАЗМЕРУ: разные файлы
    одного размера выглядели одной версией, из-за чего 3 ссылки на
    `references/audit-reference.md` (63 копии, 60 разных sha) попали в «общий файл»
    и разошлись с планом раскладки, который считает по sha. Одинаковый размер не
    значит один файл — сравнивать надо содержимое.
    """
    out: dict[str, dict[str, int]] = {}
    for label, repo in SOURCES.items():
        try:
            tree = api(f"https://api.github.com/repos/{repo}/git/trees/HEAD?recursive=1")
        except Exception as e:  # noqa: BLE001 — сеть: помечаем источник недоступным
            print(f"  ! {label}: дерево не получено ({e})", file=sys.stderr)
            out[label] = {}
            continue
        out[label] = {x["path"]: (x.get("sha", ""), x.get("size", 0))
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
            if os.path.exists(os.path.join(root, rel)):
                continue
            # Ссылка могла писаться не от каталога навыка, а от КОРНЯ репозитория
            # (`skills/<другой>/x.py`, `medsci-skills/skills/<другой>/x.py`). Тогда
            # файл лежит в чужом каталоге и находится — ссылка живая. Без этой
            # проверки 15 живых ссылок стояли в отчёте битыми: среди них
            # кросс-ссылки, на которых держатся write-paper, self-review и revise.
            if any(os.path.exists(os.path.join(ROOT, c))
                   for c in refs_mod.repo_root_candidates(raw)):
                continue
            # Ссылка на СВОЙ файл, записанная с обёрткой в начале пути: имя чужого
            # навыка как префикс, `Skills/<их-раскладка>/…`, переменная SKILL_DIR.
            # Файл при этом лежит внутри навыка и находится — ссылка живая.
            if any(os.path.exists(os.path.join(root, c))
                   for c in refs_mod.strip_leading_dirs(raw)[1:]):
                continue
            broken.append((rel_skill, rel, raw))
    return broken


def upstream_dir_of(name: str, label: str, trees: dict[str, dict[str, int]]) -> str | None:
    """Каталог навыка в дереве апстрима (`skills/<name>` или `scientific-skills/Data Analysis/<name>`).

    Нужен, чтобы отличить битую ссылку от ЖИВОЙ В ИСХОДНОЙ РАСКЛАДКЕ: навык пишет
    `../../scripts/x.py` — в репозитории-источнике это путь от каталога навыка на
    два уровня вверх, и файл там есть. У нас навыки лежат плоско (все в `skills/`),
    поэтому тот же `../../` выводит за пределы репозитория.
    """
    paths = trees.get(label) or {}
    suffix = f"/{name}/SKILL.md"
    for up in paths:
        if up.endswith(suffix) or up == f"{name}/SKILL.md":
            return posixpath.dirname(up)
    return None


# Внешние ресурсы: путь ведёт не в репозиторий навыка и не в его апстрим, а в
# сторонний проект или в каталог, который создаётся при работе навыка. Отличать
# их от «файла нет нигде» обязательно: у каждой такой ссылки есть место, откуда
# ресурс берётся или в котором он появится, — и читатель должен это видеть, а не
# читать «дефект апстрима» там, где дефекта нет.
#
# Проверено фактом (19.09.2026):
#   omicverse_guide — git-подмодуль пакета omicverse, ведёт в
#     github.com/omicverse/omicverse-tutorials: 24 из 34 ссылок совпадают точно,
#     8 переехали (docs/Tutorials-single/a.ipynb → docs/Tutorials-single/anno-zoo/a.ipynb
#     либо docs/Tutorials-Multi-Omics/...), 2 отсутствуют;
#   opt/ — каталог установленного инструмента (/opt/bin, /opt/hap.py): путь
#     появляется после установки, в репозитории его быть не может;
#   src/, output_dir/, tests/, repo/, .claude/ — каталоги, создаваемые при запуске
#     навыка (код проекта, выходные данные, тесты), а не файлы навыка.
EXTERNAL_RESOURCES = {
    "omicverse_guide": ("внешний проект", "https://github.com/omicverse/omicverse-tutorials"),
    "opt": ("установленный инструмент", "—"),
    "src": ("каталог запуска", "—"),
    "output_dir": ("каталог запуска", "—"),
    "tests": ("каталог запуска", "—"),
    "test_output": ("каталог запуска", "—"),
    "output": ("каталог запуска", "—"),
    "repo": ("каталог запуска", "—"),
    ".claude": ("каталог запуска", "—"),
    "scientific-packages": ("внешний пакет", "—"),
    "sample": ("данные примера", "—"),
}


def external_kind(ref: str) -> tuple[str, str] | None:
    """Внешний ресурс ли это — и какого рода. None, если ссылка на файл навыка."""
    r = re.sub(r"^(\.\./)+", "", ref)
    top = r.split("/")[0]
    return EXTERNAL_RESOURCES.get(top)


EXTERNAL_TREES: dict[str, set[str]] = {}


def resolve_external(project_url: str, ref: str, subdir: str) -> tuple[str, str]:
    """Где файл внешнего проекта лежит НА САМОМ ДЕЛЕ.

    Возвращает (состояние, путь): `точный` (путь совпадает), `переехал` (файл с
    таким именем есть в другом подкаталоге проекта) или `нет` (файла в проекте
    больше нет). Нужно потому, что ссылка в чужом тексте — единственный след
    ресурса, и без этой сверки читатель не знает, работает ли она.

    Один запрос дерева на проект, результат кэшируется в EXTERNAL_TREES.
    """
    if project_url in EXTERNAL_TREES:
        paths = EXTERNAL_TREES[project_url]
    else:
        repo = project_url.removeprefix("https://github.com/").removesuffix(".git")
        try:
            tree = api(f"https://api.github.com/repos/{repo}/git/trees/HEAD?recursive=1")
            paths = {x["path"] for x in tree.get("tree", []) if x.get("type") == "blob"}
        except Exception:  # noqa: BLE001 — сеть: помечаем как непроверенное
            paths = set()
        EXTERNAL_TREES[project_url] = paths
    if not paths:
        return ("не проверено", "")
    clean = re.sub(rf"^(\.\./)*{re.escape(subdir)}/", "", ref)
    if clean in paths:
        return ("точный", clean)
    same_name = [x for x in paths if x.endswith("/" + clean.split("/")[-1])]
    if same_name:
        return ("переехал", sorted(same_name)[0])
    return ("нет", "")


_SIBLING_INDEX: dict[str, list[str]] | None = None


def sibling_index() -> dict[str, list[str]]:
    """Относительный путь внутри навыка → какие навыки его содержат.

    Нужен для ссылок, ведущих на общий шаблон апстрима: у AIPOCH один и тот же
    `references/guide.md` скопирован во множество навыков, и навык, который на него
    ссылается, может не иметь своей копии. Файл при этом есть в библиотеке —
    у соседа, и он ТОТ ЖЕ (сверено по blob SHA в апстриме у 12 из 13 проверенных).
    Строится один раз: поиск по 1541 навыку на каждую ссылку превратил бы прогон
    в десятки минут.
    """
    global _SIBLING_INDEX
    if _SIBLING_INDEX is None:
        idx: dict[str, list[str]] = {}
        for root, dirs, files in os.walk(SKILLS):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            if "SKILL.md" not in files:
                continue
            rel_skill = os.path.relpath(root, SKILLS).replace(os.sep, "/")
            for sub, subdirs, subfiles in os.walk(root):
                subdirs[:] = [d for d in subdirs if d != "__pycache__"]
                for fn in subfiles:
                    rel = os.path.relpath(os.path.join(sub, fn), root).replace(os.sep, "/")
                    idx.setdefault(rel, []).append(rel_skill)
        _SIBLING_INDEX = idx
    return _SIBLING_INDEX


def same_name_elsewhere(skill_dir: str, ref: str) -> str | None:
    """Файл с таким ИМЕНЕМ есть в навыке, но по ДРУГОМУ пути.

    Ссылка не сработает, однако файл у читателя перед глазами — это не «файла нет»,
    а расхождение пути. Типичный случай: апстрим держит данные в
    `tests/expected_output/data/x.rds`, а текст ссылается на `data/x.rds`;
    результат тот же файл, что лежит рядом.
    """
    base = ref.split("/")[-1]
    if not base or len(base) < 4:
        return None
    for path in pathlib.Path(skill_dir).rglob(base):
        if path.is_file():
            return str(path.relative_to(skill_dir))
    return None


def upstream_skill_is_thin(name: str, label: str, trees) -> bool:
    """В апстриме каталог навыка есть, но подкаталогов в нём нет.

    Значит ссылка ведёт на `references/`, `scripts/`, `data/` — каталог, который
    апстрим НЕ опубликовал (у него лежит только SKILL.md и служебные файлы).
    Это не «файл потеряли при сборке», а «файла в источнике не было».
    """
    paths = trees.get(label) or {}
    suffix = f"/{name}/SKILL.md"
    d = next((posixpath.dirname(p) for p in paths
              if p.endswith(suffix) or p == f"{name}/SKILL.md"), None)
    if not d:
        return False
    inside = [p[len(d) + 1:] for p in paths if p.startswith(d + "/")]
    return len([f for f in inside if "/" in f]) == 0


def classify(broken, trees):
    buckets: dict[str, list[tuple[str, str, str]]] = {
        "placeholder": [], "recoverable": [], "heavy": [], "repo_level": [],
        "external": [], "path_mismatch": [], "own_version": [], "sibling": [],
        "foreign": [], "unpublished": [], "inherited": []}
    origin = load_origin()
    for rel_skill, ref, _raw in broken:
        name = rel_skill.rsplit("/", 1)[-1]
        # «Пример пути в коде» — не ссылка на файл, а форма пути
        # (data/fitness-logs/YYYY-MM/..., scripts/xxx.py). Требовать такой файл
        # нельзя: навык описывает, каким путём пользоваться.
        if refs_mod.is_placeholder(ref):
            buckets["placeholder"].append((rel_skill, ref, "пример пути"))
            continue
        # Внешний ресурс: место есть, файла в репозитории быть не может
        ext = external_kind(ref)
        if ext:
            state, where = ("", "")
            if ext[1].startswith("http"):
                top_dir = re.sub(r"^(\.\./)+", "", ref).split("/")[0]
                state, where = resolve_external(ext[1], ref, top_dir)
            buckets["external"].append((rel_skill, ref, f"{ext[0]}"))
            EXTERNAL_URLS[(rel_skill, ref)] = ext[1]
            EXTERNAL_STATE[(rel_skill, ref)] = (state, where)
            continue
        # Ссылка может быть записана абсолютным путём или от корня репозитория:
        # нормализуем её до пути относительно навыка, прежде чем считать битой.
        found = None
        for label, paths in trees.items():
            for up, meta in paths.items():
                if up.endswith(f"/{name}/{ref}") or up == f"{name}/{ref}":
                    found = (label, up, meta)
                    break
            if found:
                break
        if not found:
            # Вторая попытка: ссылка ведёт ВВЕРХ от каталога навыка к файлу в корне
            # репозитория-источника (`scripts/`, `examples/`, `docs/`). Файл
            # существует и доступен по blob SHA — это не дефект апстрима, а
            # следствие того, что мы складываем навыки плоско. Отдельная категория:
            # смешивать с «файла нет нигде» значит прятать восстановимые ссылки
            # среди неисправимых и обещать читателю больше, чем есть.
            label = origin.get(rel_skill) or origin.get(rel_skill.split("/")[0])
            up_dir = upstream_dir_of(name, label, trees) if label else None
            if up_dir and ref.startswith(("../", "./")):
                cand = posixpath.normpath(posixpath.join(up_dir, ref))
                meta = (trees.get(label) or {}).get(cand)
                if meta is not None:
                    found = (label, cand, meta)
        if not found:
            # Файл с таким именем есть в самом навыке, но по другому пути
            skill_dir = os.path.join(SKILLS, rel_skill)
            other = same_name_elsewhere(skill_dir, ref) if os.path.isdir(skill_dir) else None
            if other:
                buckets["path_mismatch"].append((rel_skill, ref, other))
                continue
            # Файл лежит в ДРУГОМ навыке библиотеки под тем же относительным путём.
            # Важно, ЧТО это за файл, и по имени тут судить нельзя: у
            # `references/guide.md` в апстриме 17 копий и 17 РАЗНЫХ версий, у
            # `scripts/main.py` — 176 версий на 184 навыка. Значит обычно это не
            # общий файл, а чужой контент другого навыка, и положить его копию
            # рядом — значит вложить в навык неверное содержимое под верным именем.
            # Различаем три случая, каждый — по факту из апстрима.
            if not ref.startswith("../"):
                owners = [o for o in sibling_index().get(ref, []) if o != rel_skill]
                if owners:
                    label = origin.get(rel_skill) or origin.get(rel_skill.split("/")[0])
                    o_label = origin.get(owners[0]) or origin.get(owners[0].split("/")[0])
                    # (а) у получателя в апстриме есть СВОЯ версия файла
                    own = [p for p in (trees.get(label) or ()) if p.endswith(f"/{rel_skill}/{ref}")]
                    if own:
                        buckets["own_version"].append((rel_skill, ref, label or ""))
                        continue
                    # (б) общий файл: одну версию делят три и более навыков апстрима
                    paths = trees.get(o_label) or {}
                    same = [p for p in paths if p.endswith("/" + ref)]
                    # версия = содержимое (sha), а не размер
                    versions = collections.Counter(paths[p][0] for p in same)
                    if same and versions.most_common(1)[0][1] >= 3:
                        buckets["sibling"].append((rel_skill, ref, owners[0]))
                        continue
                    # (в) уникальный файл чужого навыка
                    buckets["foreign"].append((rel_skill, ref, owners[0]))
                    continue
            # В апстриме навык без подкаталогов — значит он их не публиковал
            label = origin.get(rel_skill) or origin.get(rel_skill.split("/")[0])
            if label and upstream_skill_is_thin(name, label, trees):
                buckets["unpublished"].append((rel_skill, ref, label))
                continue
            buckets["inherited"].append((rel_skill, ref, ""))
        elif found[1].endswith(HEAVY_SUFFIX) or found[2][1] > HEAVY_MAX:
            buckets["heavy"].append((rel_skill, ref, found[0]))
        else:
            # «в корне источника» = цель лежит вне каталога навыка
            target_dir = posixpath.dirname(found[1])
            skill_dir = upstream_dir_of(name, found[0], trees) or ""
            if skill_dir and not target_dir.startswith(skill_dir):
                buckets["repo_level"].append((rel_skill, ref, found[0]))
                REPO_LEVEL_PATHS[(rel_skill, ref)] = found[1]
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


# Единый источник имён: одно место задаёт и строку таблицы, и заголовок секции.
# Держать их порознь означало бы тот же дефект, что чинится весь этот отчёт:
# название в сводке расходится с названием в разборе, и проверка «у каждой
# непустой категории есть секция» падает на ровном месте.
CATEGORIES = (
    ("placeholder", "Пример пути в коде", "Пример пути в коде (не ссылка)",
     "форма пути (`YYYY`, `xxx`, `<file>`), а не файл — требовать его нельзя"),
    ("recoverable", "Восстановимо", "Восстановимо",
     "файл есть у источника — закрывается `scripts/sync_upstreams.py`"),
    ("external", "Внешний ресурс", "Внешний ресурс (не файл этого репозитория)",
     "путь ведёт в сторонний проект (git-подмодуль) или в каталог, создаваемый при работе "
     "(`src/`, `output_dir/`, `/opt`) — в репозитории такого файла быть не может"),
    ("repo_level", "В корне источника", "Файл в корне репозитория-источника (вне каталога навыка)",
     "файл ЕСТЬ в репозитории-источнике, но вне каталога навыка (`scripts/`, `examples/`, "
     "`docs/`) — ссылка писалась под их раскладку, где навыки лежат глубже"),
    ("path_mismatch", "Путь разошёлся", "Путь разошёлся (файл в навыке есть)",
     "файл с таким именем есть в самом навыке, но по другому пути — ссылка не сработает, "
     "однако файл у читателя перед глазами (типично: данные лежат в `tests/expected_output/`)"),
    ("own_version", "Своя версия в апстриме", "У апстрима своя версия файла",
     "у навыка в апстриме ЕСТЬ файл по этому пути, но он не попал в сборку — свой "
     "контент навыка, копия из соседа подошла бы неверно"),
    ("sibling", "Общий файл апстрима", "Общий файл апстрима (одну версию делят ≥3 навыка)",
     "ссылку можно закрыть копией: файл размножен по навыкам апстрима и одинаков у них, "
     "`scripts/plant_sibling_files.py` кладёт копию рядом"),
    ("foreign", "Файл чужого навыка", "Файл принадлежит другому навыку",
     "у навыка в апстриме своего файла нет, а найденный — уникальный контент чужого "
     "навыка (у `guide.md` — 17 копий и 17 разных версий); копировать его нельзя, "
     "текст ссылается на файл соседа"),
    ("unpublished", "Апстрим не публиковал", "Апстрим не публиковал каталог",
     "каталог навыка в источнике есть, но подкаталогов в нём нет: `references/`, `scripts/`, "
     "`data/` апстрим не выкладывал — файла не было и в момент сборки"),
    ("heavy", "Тяжёлые данные", "Тяжёлые данные (не тянем)",
     "файл есть, но это демо-датасет на мегабайты — сознательно не тянем"),
    ("inherited", "Унаследованное", "Унаследованное (файла нет в источнике)",
     "файла нет ни в источнике, ни у соседнего навыка: апстрим его не выложил. Часть "
     "таких ссылок описывает РЕЗУЛЬТАТ работы навыка (выходные файлы `data/*.vcf.gz`), "
     "и требовать их не нужно — но отличить это автоматически нельзя: признак только "
     "в тексте, поэтому файлы остаются здесь, а не выдаются за «создаётся при работе»"),
)


def write_report(buckets, total_ok: int, origin: dict[str, str]) -> None:
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    total = total_ok + sum(len(v) for v in buckets.values())
    lines = [
        "# Ссылки на файлы внутри навыков: инвентарь",
        "",
        f"Сгенерировано `scripts/broken_refs.py`. Ссылок на файлы в дереве: {total}; "
        f"на месте: {total_ok}; битых: {total - total_ok}.",
        "",
        "Битые ссылки — унаследованное свойство апстримов: файл, который навык упоминает, "
        "у них лежал в отрезанном служебном каталоге (`tests/`, `evals/`) либо не был "
        "закоммичен. Правится не ссылка в чужом тексте, а знание о том, где файл есть.",
        "",
        "| Категория | Сколько | Что значит |",
        "|---|---|---|",
    ]
    for key, short, _title, meaning in CATEGORIES:
        lines.append(f"| {short} | {len(buckets[key])} | {meaning} |")
    lines.append("")

    for key, short, title, _meaning in CATEGORIES:
        items = buckets[key]
        if not items:
            continue
        if key == "external":
            lines += [f"## {title}", "",
                      "Путь ведёт **не** в репозиторий навыка: в сторонний проект или в "
                      "каталог, который создаётся при работе. Файла здесь быть не может — "
                      "ссылка описывает, где ресурс лежит или появится.", "",
                      "| Навык | Ссылка в тексте | Что это | Где взять | Состояние |",
                      "|---|---|---|---|---|"]
            kinds: dict[str, list[tuple[str, str]]] = {}
            for rel_skill, ref, kind in items:
                kinds.setdefault(kind, []).append((rel_skill, ref))
            for kind in sorted(kinds):
                for rel_skill, ref in sorted(kinds[kind]):
                    url = EXTERNAL_URLS.get((rel_skill, ref), "—")
                    state, where = EXTERNAL_STATE.get((rel_skill, ref), ("", ""))
                    note = {"точный": "путь совпадает",
                            "переехал": f"переехал → `{where}`",
                            "нет": "**в проекте нет**"}.get(state, "—")
                    lines.append(f"| `{rel_skill}` | `{ref}` | {kind} | {url} | {note} |")
            lines.append("")
            continue
        if key == "repo_level":
            lines += [f"## {title}", "",
                      "Файл существует в репозитории-источнике, но **вне каталога навыка** — "
                      "в его корне (`scripts/`, `examples/`, `docs/`). Навык писал ссылку под "
                      "исходную раскладку, где каталоги навыков лежат глубже; мы складываем "
                      "навыки плоско, поэтому та же ссылка (`../../`) выводит за пределы "
                      "репозитория. Ссылка не станет рабочей от простой закачки файла в "
                      "навык: путь в тексте останется прежним. Брать файл — по URL ниже, "
                      "требовать его внутри репозитория нельзя.", "",
                      "| Навык | Ссылка в тексте | Файл в источнике | Взять |",
                      "|---|---|---|---|"]
            for rel_skill, ref, src in sorted(items):
                note = src or origin.get(rel_skill, "") or "—"
                up = REPO_LEVEL_PATHS.get((rel_skill, ref), "")
                url = (f"https://github.com/{SOURCES[note]}/blob/HEAD/{up}"
                       if note in SOURCES and up else "—")
                lines.append(f"| `{rel_skill}` | `{ref}` | `{up or '—'}` | {url} |")
            lines.append("")
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
          f" | внешних ресурсов: {len(buckets['external'])}"
          f" | в корне источника: {len(buckets['repo_level'])}"
          f" | тяжёлые: {len(buckets['heavy'])}"
          f" | унаследовано: {len(buckets['inherited'])}")
    if not args.no_report:
        write_report(buckets, total_ok, load_origin())
        print(f"  отчёт: {os.path.relpath(REPORT, ROOT)}")

    own_broken = [(s, r) for s, r, _ in buckets["recoverable"] + buckets["repo_level"]
                  + buckets["heavy"] + buckets["inherited"]
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
