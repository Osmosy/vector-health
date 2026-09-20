#!/usr/bin/env python3
"""Синхронизация vector-health с обновлениями апстримов.

Сравнивает вендоренные навыки с текущим состоянием исходных репозиториев и
обновляет только то, что апстрим реально изменил:

  - SKILL.md, изменённый апстримом → заменяется;
  - новый навык апстрима → добавляется целиком;
  - вспомогательные файлы (references/, scripts/, templates/, assets/) внутри
    затронутых навыков → добавляются/обновляются;
  - файл, удалённый апстримом у НАШЕГО источника → удаляется локально.

Что НЕ трогается:
  - коллизии имён: если навык с таким именем в библиотеке пришёл из другого
    источника, апстрим не перезаписывает его молча;
  - собственные навыки (dicom-vlm-analysis, atrial-fibrillation-treatment);
  - тяжёлые служебные каталоги (evals/, fixtures/, repo/, node_modules/) и
    крупные бинарные датасеты — при сборке они отрезались сознательно.

Происхождение каждого навыка определяется по `scripts/upstream-origin.json`
(имя → источник), который генерируется скриптом `--build-origin` при первой
нужной сверке: он сопоставляет blob SHA локального SKILL.md с деревом апстрима
на дату сборки. Это компактно (несколько сотен килобайт) и не хранит полные
деревья апстримов в репозитории.

Запуск: python3 scripts/sync_upstreams.py --help
Только stdlib; сеть — api.github.com и raw.githubusercontent.com.
"""

from __future__ import annotations

import argparse
import http.client
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, "skills")
ORIGIN = os.path.join(ROOT, "scripts", "upstream-origin.json")

# Дата сборки библиотеки: апстримы сравниваются с их состоянием на этот момент.
ASSEMBLED = "2026-08-16"
ASSEMBLED_UNTIL = "2026-08-17T00:00:00Z"

# Источники: репозиторий, префиксы вендоренных путей и корень пути навыка.
SOURCES = {
    "OpenClaw": {"repo": "FreedomIntelligence/OpenClaw-Medical-Skills", "roots": ["skills"]},
    "aipoch": {"repo": "aipoch/medical-research-skills",
               "roots": ["scientific-skills", "awesome-med-research-skills", "skill-auditor"]},
    "Aperivue": {"repo": "Aperivue/medsci-skills", "roots": ["skills"]},
    "openmed": {"repo": "maziyarpanahi/openmed", "roots": ["skills"]},
}

# Отрезанные при сборке каталоги и тяжёлые форматы: не тянем их обратно.
EXCLUDE_PARTS = ("/evals/", "/eval/", "/fixtures/", "/repo/", "/node_modules/", "/.git/",
                 "/tests/", "/test_data/", "/.github/", "/docs/", "/challenges/",
                 "/lint_challenge/", "/analysis_run_challenge/", "/_challenge/")
EXCLUDE_SUFFIX = (".npy", ".xlsx", ".parquet", ".h5ad", ".rds", ".bam", ".zip", ".whl")
# Тяжёлые архивы: файл есть в апстриме и на него ссылается SKILL.md, но это
# демо-данные на мегабайты (выгрузки 23andMe по 4.9 МБ), а не материал навыка.
# Держать их в библиотеке навыков — удвоить репозиторий ради одного примера.
HEAVY_SUFFIX = (".gz", ".tgz", ".bz2", ".xz", ".tar", ".7z")
HEAVY_MAX = 1_500_000  # байт: крупнее — демо-датасет, а не материал навыка
# Служебные артефакты апстримов: отчёты прогонов, аудиты, changelog'и. При сборке
# они не вендорились; тянуть их обратно — удвоить библиотеку мусором.
EXCLUDE_MARKERS = ("_audit_result", "audit_result", "eval_report", "POLISH_CHANGELOG",
                   "CHANGELOG", "_coverage", "coverage.json", "conftest.py")
# Разбор ссылок на файлы — общий модуль (scripts/refs.py): синхронизация,
# инвентарь и валидатор должны отвечать на вопрос «какие файлы нужны навыку»
# одинаково, иначе один тянет одно, а другой ругает.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import refs as refs_mod  # noqa: E402

REF_RE = refs_mod.REF_RE

# Что имеет смысл вендорить кроме SKILL.md: контент навыка, а не его CI.
AUX_PREFIXES = ("references/", "scripts/", "templates/", "assets/", "prompts/", "data/",
                "requirements.txt", "skill.yml", "LICENSE")
MAX_FILE = 5 * 1024 * 1024

_HEADS_CACHE: tuple[dict[str, dict[str, str]], dict[str, int]] | None = None


def token() -> str:
    """Токен для API. Приоритет — gh CLI: он обновляется сам, а GITHUB_TOKEN
    в ~/.hermes/.env истекает и молча даёт 401."""
    try:
        out = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True)
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except FileNotFoundError:
        pass
    env_path = os.path.expanduser("~/.hermes/.env")
    if os.path.isfile(env_path):
        for line in open(env_path, encoding="utf-8"):
            if line.startswith("GITHUB_TOKEN="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


API_TOKEN = token()


def api(url: str, tries: int = 4):
    for attempt in range(tries):
        req = urllib.request.Request(url, headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "vector-health-sync",
            **({"Authorization": f"Bearer {API_TOKEN}"} if API_TOKEN else {}),
        })
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                raw = resp.read()
        except (http.client.IncompleteRead, ConnectionError, TimeoutError) as exc:
            # Крупные деревья (20k файлов) обрываются по сети: читаем повторно,
            # иначе синхронизация падает на ровном месте и план теряется.
            if attempt < tries - 1:
                time.sleep(3 * (attempt + 1))
                continue
            raise RuntimeError(f"api: сеть не отдала ответ — {exc}") from None
        try:
            return json.loads(raw)
        except ValueError:
            if attempt < tries - 1:
                time.sleep(3 * (attempt + 1))
                continue
            raise RuntimeError("api: ответ не JSON — вероятно, обрезан") from None
        except urllib.error.HTTPError as exc:
            # 403 у анонимного доступа — это лимит, а не запрет: ждём и повторяем.
            # Истёкший токен даёт 401 и не повторяется — это конфигурация, а не сеть.
            if exc.code in (403, 429) and attempt < tries - 1:
                time.sleep(10 * (attempt + 1))
                continue
            raise
    raise RuntimeError("api: исчерпаны попытки")  # pragma: no cover


def fetch_bytes(repo: str, path: str, ref: str) -> bytes | None:
    url = f"https://raw.githubusercontent.com/{repo}/{ref}/{urllib.parse.quote(path)}"
    req = urllib.request.Request(url, headers={"User-Agent": "vector-health-sync"})
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def blob_map(repo: str, ref: str) -> dict[str, str]:
    tree = api(f"https://api.github.com/repos/{repo}/git/trees/{ref}?recursive=1")
    if tree.get("truncated"):
        print(f"  ! дерево {repo}@{ref[:7]} усечено API — часть файлов не увидим", file=sys.stderr)
    return {x["path"]: x["sha"] for x in tree.get("tree", []) if x.get("type") == "blob"}


def blob_sizes(repo: str, ref: str) -> dict[str, int]:
    """Путь → размер в байтах. Размер нужен, чтобы не тянуть мегабайтные
    демо-датасеты, на которые ссылается SKILL.md (выгрузки 23andMe по 4.9 МБ)."""
    tree = api(f"https://api.github.com/repos/{repo}/git/trees/{ref}?recursive=1")
    return {x["path"]: x.get("size", 0) for x in tree.get("tree", []) if x.get("type") == "blob"}


def head_of(repo: str) -> str:
    return api(f"https://api.github.com/repos/{repo}/commits?per_page=1")[0]["sha"]


def assembled_ref(repo: str) -> str:
    return api(f"https://api.github.com/repos/{repo}/commits"
               f"?until={ASSEMBLED_UNTIL}&per_page=1")[0]["sha"]


def is_excluded(path: str) -> bool:
    low = "/" + path
    if any(part in low for part in EXCLUDE_PARTS) or path.endswith(EXCLUDE_SUFFIX):
        return True
    if path.endswith(HEAVY_SUFFIX):
        return True
    base = path.rsplit("/", 1)[-1]
    return any(marker in base for marker in EXCLUDE_MARKERS)


def rel_of(up_path: str, name: str) -> str:
    """Путь относительно каталога навыка.

    Через split по `/<name>/`, а не по индексу строки: у aipoch навыки лежат в
    `<root>/<Категория>/<навык>/`, и смещение по длине префикса давало лишний слэш
    («3d-molecule-ray-tracer//scripts/main.py»).
    """
    marker = f"/{name}/"
    idx = up_path.find(marker)
    return up_path[idx + len(marker):] if idx >= 0 else ""


def skill_dir_of(path: str) -> str | None:
    """Имя навыка для пути внутри апстрима: каталог, содержащий SKILL.md.

    Расширение бывает заглавным: OpenClaw держит один навык как `SKILL.MD`, и
    сравнение по точной строке теряло его — навык попадал в «собственные».
    """
    low = path.lower()
    if low.endswith("/skill.md"):
        return path.rsplit("/", 1)[0].split("/")[-1]
    return None


def build_origin() -> dict:
    """Карта «локальный навык → источник» по blob SHA на дату сборки."""
    # Все каталоги с SKILL.md, включая ВЛОЖЕННЫЕ. Раньше брались только верхние:
    # в карте не было 26 навыков внутри каталогов-контейнеров (variant-interpretation-acmg/
    # bioSkills/*, spatial-transcriptomics-analysis/SpatialAgent и др.), и проверка
    # «каждый навык из skills-index.json есть в карте происхождения» не сходилась.
    found: list[str] = []
    for dirpath, dirnames, filenames in os.walk(SKILLS):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        if "SKILL.md" in filenames or "SKILL.MD" in filenames:
            found.append(os.path.relpath(dirpath, SKILLS).replace(os.sep, "/"))
    local_names = sorted(found)
    origin: dict[str, str] = {}
    sha_by_source: dict[str, dict[str, str]] = {}
    # Два состояния апстрима: HEAD (что там сейчас) и дата сборки (что было
    # взято вендорингом). HEAD первым: после синхронизации часть навыков ушла
    # вперёд, и по одному устаревшему дереву они ошибочно числились бы «своими».
    for label, cfg in SOURCES.items():
        by_sha: dict[str, str] = {}
        for ref in (head_of(cfg["repo"]), assembled_ref(cfg["repo"])):
            try:
                tree = blob_map(cfg["repo"], ref)
            except Exception:  # noqa: BLE001 — сеть: дерево просто не учитываем
                continue
            for path, sha in tree.items():
                name = skill_dir_of(path)
                if name:
                    by_sha.setdefault(sha, name)
        sha_by_source[label] = by_sha
        print(f"  {label:9}: навыков в дереве {len(by_sha)}")

    for name in local_names:
        smd = os.path.join(SKILLS, name, "SKILL.md")
        sha = subprocess.run(["git", "hash-object", smd], cwd=ROOT,
                             capture_output=True, text=True).stdout.strip()
        # имя, встречающееся у нескольких источников, разрешаем в порядке приоритета
        # сборки: так карта воспроизводит то, что реально лежит в дереве.
        for label in ("aipoch", "Aperivue", "openmed", "OpenClaw"):
            if sha_by_source[label].get(sha):
                origin[name] = label
                break
        else:
            origin[name] = "own"
    out = {"assembled": ASSEMBLED, "origin": origin}
    with open(ORIGIN, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, sort_keys=True)
    counts: dict[str, int] = {}
    for label in origin.values():
        counts[label] = counts.get(label, 0) + 1
    print("карта происхождения:", counts)
    return origin


def load_origin() -> dict:
    if not os.path.isfile(ORIGIN):
        print("нет карты происхождения — строю (это разовая операция)…", file=sys.stderr)
        return build_origin()
    with open(ORIGIN, encoding="utf-8") as f:
        return json.load(f)["origin"]


def git_blob_sha(path: str) -> str:
    """blob SHA файла — так же, как его считает git (для сверки с деревом апстрима)."""
    return subprocess.run(["git", "hash-object", path], cwd=ROOT,
                          capture_output=True, text=True).stdout.strip()


def local_tree(name: str) -> dict[str, str]:
    """Относительный путь → blob SHA для всех файлов навыка (кроме мусора)."""
    base = os.path.join(SKILLS, name)
    out: dict[str, str] = {}
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in ("__pycache__",)]
        for fn in files:
            fp = os.path.join(root, fn)
            out[os.path.relpath(fp, base)] = git_blob_sha(fp)
    return out


def all_heads() -> tuple[dict[str, dict[str, str]], dict[str, int]]:
    """Деревья всех источников: {источник: {путь: sha}} и {путь: размер}.

    Нужно для случая «гибридного» навыка: SKILL.md из одного апстрима, а его
    references/scripts — только в другом. Кэш на процесс: деревья по 20k путей
    дёргать на каждый навык нельзя.
    """
    global _HEADS_CACHE
    if _HEADS_CACHE is None:
        trees: dict[str, dict[str, str]] = {}
        sizes: dict[str, int] = {}
        for label, cfg in SOURCES.items():
            ref = head_of(cfg["repo"])
            trees[label] = blob_map(cfg["repo"], ref)
            sizes.update(blob_sizes(cfg["repo"], ref))
        _HEADS_CACHE = (trees, sizes)
    return _HEADS_CACHE


def fork_files(name: str, trees: dict[str, dict[str, str]], sizes: dict[str, int],
               origin: dict[str, str], label: str) -> list[tuple[str, str, str]]:
    """Файлы навыка, на которые ссылается SKILL.md, но лежащие у ДРУГОГО источника.

    Часть навыков — гибрид: SKILL.md пришёл из одного апстрима, а его references/
    и scripts/ существуют только в другом (gwas-database, pathml, pydicom, shap,
    hypothesis-generation: SKILL.md от aipoch, остальное — в форке OpenClaw,
    который содержит более полную версию). Такие файлы не докачивались, и ссылки
    в навыке оставались битыми, хотя файл доступен.

    Возвращает [(rel, upstream_path, repo)] для файлов, отсутствующих локально.
    """
    out: list[tuple[str, str, str]] = []
    skill_md = os.path.join(SKILLS, name, "SKILL.md")
    if not os.path.isfile(skill_md):
        return out
    body = open(skill_md, encoding="utf-8", errors="replace").read()
    for rel in refs_mod.find_refs(body):
        rel = os.path.normpath(rel)
        if rel.startswith("..") or rel.startswith("/"):
            continue
        if os.path.exists(os.path.join(SKILLS, name, rel)):
            continue
        for tree_label, paths in trees.items():
            if tree_label == label:
                continue  # свой источник уже проверен шагом 2
            for up, _sha in paths.items():
                if up.endswith(f"/{name}/{rel}"):
                    if is_excluded(up) or sizes.get(up, 0) > HEAVY_MAX:
                        break
                    out.append((rel, up, SOURCES[tree_label]["repo"]))
                    break
            else:
                continue
            break
    return out


def index_by_skill(head_paths: set[str], local_names: set[str]) -> dict[str, list[str]]:
    """Апстрим-пути, сгруппированные по имени навыка (известные локальные имена).

    Индекс строится один раз: без него поиск апстрим-пути для каждого файла
    пробегает всё дерево (20k путей) и превращает планирование в минуты.
    """
    idx: dict[str, list[str]] = {}
    for path in head_paths:
        for part in path.split("/"):
            if part in local_names:
                idx.setdefault(part, []).append(path)
                break
    return idx


def upstream_of(name: str, rel: str, index: dict[str, list[str]], roots: list[str],
                local_sha: str | None = None, shas: dict[str, str] | None = None) -> str | None:
    """Апстрим-путь для файла навыка: [<root>/][<категория>/]<навык>/<rel>.

    Три случая, каждый ломал поиск по-своему:
      1. навык в категории: `skills/<name>/<rel>` или
         `scientific-skills/Data Analysis/<name>/<rel>`;
      2. навык В КОРНЕ репозитория: `<name>/<rel>` без префикса категории
         (так у AIPOCH лежит skill-auditor) — проверка «путь начинается с
         известного корня» его отбрасывала, и файлы навыка не докачивались;
      3. один навык в нескольких категориях с РАЗНЫМ содержимым (aipoch:
         «Data Analysis» и «Evidence Insight»). При переданном local_sha берётся
         версия, совпадающая с локальной, — иначе файл подменяется чужим.

    Совпадение проверяется по концу пути, а корни (roots) задают только
    приоритет, а не жёсткий фильтр: иначе случай 2 теряется.
    """
    target = f"/{name}/{rel}"
    cands = [p for p in index.get(name, []) if p.endswith(target)]
    if not cands:
        # Навык в КОРНЕ репозитория: путь не «.../<name>/<rel>», а «<name>/<rel>» —
        # без ведущего слэша, поэтому поиск по «/<name>/<rel>» его не находит
        # (так у AIPOCH лежит skill-auditor). Проверяем точное совпадение начала.
        head_target = f"{name}/{rel}"
        cands = [p for p in index.get(name, []) if p == head_target]
    if not cands:
        return None
    # приоритет: сначала пути под известными корнями, потом остальные (корень репо)
    preferred = [p for p in cands if any(p.startswith(r + "/") for r in roots)]
    ordered = preferred + [p for p in cands if p not in preferred]
    if local_sha and shas:
        exact = [p for p in ordered if shas.get(p) == local_sha]
        if exact:
            return exact[0]
    return ordered[0]


def plan(label: str, cfg: dict, origin: dict[str, str]) -> dict:
    """План приводится локальное дерево к HEAD апстрима.

    Сравнивается ЛОКАЛЬНЫЙ файл с версией апстрима, а не база с HEAD: только так
    повторный запуск без изменений в апстриме показывает ноль. Сравнение «база →
    head» каждый раз возвращало одну и ту же дельту и не давало понять, применена
    ли она.
    """
    repo, roots = cfg["repo"], cfg["roots"]
    head_ref = head_of(repo)
    head = blob_map(repo, head_ref)
    sizes = blob_sizes(repo, head_ref)

    local_names = {n for n in os.listdir(SKILLS) if os.path.isdir(os.path.join(SKILLS, n))}
    up_skill_names = {n for n in (skill_dir_of(p) for p in head) if n}
    index = index_by_skill(set(head), local_names | up_skill_names)

    update, create, delete = [], [], []
    # Имена всех навыков, уже присутствующих в дереве (включая вложенные): часть
    # навыков апстрима лежит внутри каталогов-контейнеров
    # (spatial-transcriptomics-analysis/bioSkills/…), они вендорены вместе с
    # контейнером, и «добавлять» их заново нельзя — получим дубли.
    known_anywhere = set()
    for root, dirs, files in os.walk(SKILLS):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        if "SKILL.md" in files:
            known_anywhere.add(os.path.basename(root))

    # 1. Новые навыки апстрима: их у нас ещё нет — забираем SKILL.md,
    #    вспомогательные файлы подтянутся шагом 2.
    for path in sorted(head):
        name = skill_dir_of(path)
        if not name or is_excluded(path) or name in known_anywhere:
            continue
        create.append((name, "SKILL.md", path, repo))

    # 2. Наши навыки этого источника: сверить каждый файл с апстримом.
    def is_ours(name: str) -> bool:
        if origin.get(name) == label:
            return True
        # навык появился локально после сборки карты — владельцем считаем тот
        # источник, в дереве которого нашёлся его SKILL.md
        return name not in origin and upstream_of(name, "SKILL.md", index, roots) is not None

    owned = sorted(n for n in local_names if is_ours(n))
    for name in owned:
        local = local_tree(name)
        for rel, sha in sorted(local.items()):
            up = upstream_of(name, rel, index, roots, local_sha=sha, shas=head)
            if up is None or is_excluded(up):
                continue
            if head[up] != sha:
                update.append((name, rel, up, repo))

        # Файлы, на которые ССЫЛАЕТСЯ сам SKILL.md, но которых у нас нет.
        # Тянем не всё подряд: полный набор апстрима — это десятки тысяч
        # декоративных шаблонов (ppt-master: 11 765 логотипов брендов), к
        # медицине отношения не имеющих. Нужное определяется ссылкой в тексте.
        skill_md = os.path.join(SKILLS, name, "SKILL.md")
        if not os.path.isfile(skill_md):
            continue
        body = open(skill_md, encoding="utf-8", errors="replace").read()
        for raw_ref in refs_mod.find_refs(body):
            # Ссылка может быть записана абсолютным путём или от корня репозитория
            # (`/Users/.../skills/<name>/scripts/main.py`, `skills/<name>/...`) —
            # приводим её к пути относительно навыка, иначе файл считается
            # отсутствующим навсегда, хотя лежит в апстриме.
            rel = refs_mod.to_skill_relative(raw_ref, name) or raw_ref
            rel = os.path.normpath(rel)
            if rel.startswith("..") or rel.startswith("/"):
                continue
            lp = os.path.join(SKILLS, name, rel)
            if os.path.exists(lp):
                continue
            # Версию выбираем по ссылке из самого навыка: у aipoch один навык
            # лежит в нескольких категориях, и файл из чужой категории — не тот.
            up = upstream_of(name, rel, index, roots)
            if up is None or is_excluded(up):
                continue
            # Размер известен из дерева: не тянем мегабайтные датасеты, даже если
            # на них ссылается SKILL.md — это демо-примеры, а не материал навыка.
            if sizes.get(up, 0) > HEAVY_MAX:
                continue
            create.append((name, rel, up, repo))

    # 3. Файлы, удалённые апстримом у нашего источника (были на базе сборки — нет в HEAD).
    base_ref = assembled_ref(repo)
    base = blob_map(repo, base_ref)
    base_index = index_by_skill(set(base), local_names)
    for name in owned:
        for rel in local_tree(name):
            if upstream_of(name, rel, index, roots) is None and \
                    upstream_of(name, rel, base_index, roots) is not None:
                delete.append((name, rel))

    # 4. Апстрим-форки: у ряда навыков SKILL.md пришёл из одного источника, а файлы,
    #    на которые он ссылается, есть только в ДРУГОМ (напр. gwas-database,
    #    pathml, pydicom: SKILL.md от aipoch, а references/ и scripts/ — только в
    #    форке OpenClaw). Без этого шага ссылки в таких навыках остаются битыми,
    #    хотя файл лежит в апстриме и стоит одну закачку.
    #    Ссылка на файл чужого источника — это пробел библиотеки, а не подмена
    #    содержимого: SKILL.md, владельческий файл, никогда не трогается.
    other_trees, other_sizes = all_heads()
    for name in owned:
        for rel, up, up_repo in fork_files(name, other_trees, other_sizes, origin, label):
            create.append((name, rel, up, up_repo))
    return {"repo": repo, "head": head_ref, "base": base_ref,
            "update": update, "create": create, "delete": delete}


def apply(plan_data: dict) -> tuple[int, int]:
    """Записать файлы плана. Для каждого — свой репозиторий и его HEAD: файл из
    форка лежит в другом репозитории, и его нельзя тянуть по ref основного."""
    written = skipped = 0
    refs: dict[str, str] = {}

    def ref_for(repo: str) -> str:
        if repo not in refs:
            refs[repo] = head_of(repo)
        return refs[repo]

    for name, rel, up, repo in plan_data["update"] + plan_data["create"]:
        data = fetch_bytes(repo, up, ref_for(repo))
        if data is None or len(data) > MAX_FILE:
            skipped += 1
            continue
        dst = os.path.join(SKILLS, name, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "wb") as f:
            f.write(data)
        written += 1
    for name, rel in plan_data["delete"]:
        fp = os.path.join(SKILLS, name, rel)
        if os.path.isfile(fp):
            os.remove(fp)
    return written, skipped


KEPT = os.path.join(ROOT, "scripts", "kept-service-files.json")


def _prune_allowlist() -> set[tuple[str, str]]:
    """Файлы, которые правила исключают, но которые сохранены по причине.

    Два источника: явный список `kept-service-files.json` (там причина обязательна)
    и правило для каталогов `tests/` — файл сохраняется, если его имя или путь
    встречается в материале навыка (SKILL.md и справочных каталогах). Правило вместо
    списка: таких файлов 147, и перечислить их поимённо значит завести список,
    который разъедется при первом же обновлении апстрима.
    """
    kept: set[tuple[str, str]] = set()
    if os.path.isfile(KEPT):
        try:
            with open(KEPT, encoding="utf-8") as f:
                for item in json.load(f).get("kept", []):
                    kept.add((item["skill"], item["rel"]))
        except (OSError, json.JSONDecodeError, KeyError):
            pass
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import service_artifacts as sa  # noqa: PLC0415 — нужен только здесь
    for item in sa.collect()["items"]:
        if item["referenced"]:
            kept.add((item["skill"], item["rel"]))
    return kept


PRUNE_DIR_NAMES = ("tests", "test_data", "evals", "eval", "fixtures", "challenges",
                    "lint_challenge", "analysis_run_challenge", "_challenge")


def prune_empty_dirs(apply: bool) -> int:
    """Убрать опустевшие служебные каталоги.

    После удаления файлов остаются пустые `tests/`, `evals/`, `fixtures/`: 67 штук.
    Каталог без файлов — след уборки, а не материал навыка, и в дереве он читается
    как «здесь что-то было» (плюс мешает проверке «нет каталогов tests/»).
    """
    removed = 0
    # снизу вверх: сначала вложенные, потом родитель
    for root, dirs, _files in os.walk(os.path.join(SKILLS), topdown=False):
        for d in dirs:
            path = os.path.join(root, d)
            if not os.path.isdir(path):
                continue
            if not any(os.scandir(path)) and d in PRUNE_DIR_NAMES:
                if apply:
                    os.rmdir(path)
                removed += 1
    return removed


def prune_files(apply: bool) -> tuple[int, int, list[tuple[str, str]]]:
    """Удалить служебные артефакты, на которые НЕ ссылается материал навыка.

    Правила синхронизации применялись только к приёму файлов: то, что успело
    попасть в сборку до их появления, оставалось в дереве навсегда — 1248 файлов,
    18.7 МБ. Возвращает (сколько удалено, сколько оставлено по allowlist, пробу).
    """
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import service_artifacts as sa  # noqa: PLC0415
    kept = _prune_allowlist()
    removed, skipped, sample = 0, 0, []
    for item in sa.collect()["items"]:
        key = (item["skill"], item["rel"])
        if key in kept:
            skipped += 1
            continue
        full = os.path.join(SKILLS, item["skill"], item["rel"])
        if not os.path.isfile(full):
            continue
        sample.append(key)
        if apply:
            os.remove(full)
        removed += 1
    return removed, skipped, sample[:10]


def main() -> int:
    ap = argparse.ArgumentParser(description="Синхронизация vector-health с апстримами")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", help="OpenClaw|aipoch|Aperivue|openmed")
    ap.add_argument("--build-origin", action="store_true", help="пересобрать карту происхождения")
    ap.add_argument("--prune", action="store_true",
                    help="удалить служебные артефакты, на которые не ссылается навык "
                         "(с учётом scripts/kept-service-files.json)")
    args = ap.parse_args()

    if args.build_origin:
        build_origin()
        return 0

    if args.prune:
        n, kept_n, sample = prune_files(apply=not args.dry_run)
        dirs_n = prune_empty_dirs(apply=not args.dry_run)
        verb = "удалено бы" if args.dry_run else "удалено"
        dverb = "убрано бы" if args.dry_run else "убрано"
        print(f"служебные артефакты: {verb} {n} | сохранено по allowlist: {kept_n}")
        print(f"опустевших каталогов {dverb}: {dirs_n}")
        for skill, rel in sample:
            print(f"   {skill}/{rel}")
        if args.dry_run:
            print("(dry-run: файлы не изменялись)")
        return 0

    origin = load_origin()

    labels = [args.only] if args.only else sorted(SOURCES)
    total = {"update": 0, "create": 0, "delete": 0, "written": 0, "skipped": 0}
    for label in labels:
        if label not in SOURCES:
            print(f"неизвестный источник «{label}»", file=sys.stderr)
            return 1
        p = plan(label, SOURCES[label], origin)
        print(f"=== {label} ({p['repo']})  база {p['base'][:7]} → head {p['head'][:7]}")
        print(f"   обновить: {len(p['update'])} | добавить: {len(p['create'])} "
              f"| удалить: {len(p['delete'])}")
        for name, rel, _up, _r in p["update"][:10]:
            print(f"      обновить: {name}/{rel}")
        for name, rel, _up, src in p["create"][:10]:
            mark = "" if src == p["repo"] else f"  (+ {src})"
            print(f"      добавить: {name}/{rel}{mark}")
        for name, rel in p["delete"][:5]:
            print(f"      удалить:  {name}/{rel}")
        for key in ("update", "create", "delete"):
            total[key] += len(p[key])
        if not args.dry_run:
            w, s = apply(p)
            total["written"] += w
            total["skipped"] += s
    print(f"\nИТОГО: обновить {total['update']}, добавить {total['create']}, "
          f"удалить {total['delete']}")
    if args.dry_run:
        print("(dry-run: файлы не изменялись)")
    else:
        print(f"записано файлов: {total['written']} (пропущено {total['skipped']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
