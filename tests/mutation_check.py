#!/usr/bin/env python3
"""Мутационная проверка: валидатор должен падать на каждой подделке.

Проверка, которая не падает на испорченных данных, ничего не проверяет. Здесь
каждая мутация — то, что аудит назвал дефектом: вернуть служебный файл, снять
причину с allowlist, подменить год испытания, разойтись числом проверок.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CASES = [
    ("M1: вернуть служебный файл в навык",
     [("skills/academic-norm-review/eval_report_x_result.json", "", "")]),
    ("M2: снять причину с allowlist",
     [("scripts/kept-service-files.json", '"reason":', '"no_reason":')]),
    ("M3: allowlist ссылается на отсутствующий файл",
     [("scripts/kept-service-files.json", '"skill": "multi-search-engine"',
       '"skill": "no-such-skill-here"')]),
    ("M4: убрать новый скрипт из дерева README",
     [("README.md", "├── service_artifacts.py", "├── removed-by-mutation.py")]),
    # M5 — ровно тот дефект, что нашёл аудит: год в таблице разошёлся с первоисточником
    ("M5a: подменить год EARLY-AF в таблице испытаний",
     [("skills/atrial-fibrillation-treatment/SKILL.md", "NEJM 2021;384(4):305–315",
       "NEJM 2022;384(4):305–315")]),
    # M5b — цифры одного испытания приписаны соседнему (реальная ошибка навыка)
    ("M5b: перенести цифры EARLY-AF в STOP-AF First",
     [("skills/atrial-fibrillation-treatment/SKILL.md", "успех за 12 мес **74.6% vs 45.0%**",
       "рецидив **42.9% vs 67.8%**")]),
    ("M6: снять PMID из таблицы испытаний",
     [("skills/atrial-fibrillation-treatment/SKILL.md", "PMID 33197158", "PMID удалён")]),
    ("M7: год в прозе, оставив PMID (форма «Испытание (год)»)",
     [("skills/atrial-fibrillation-treatment/SKILL.md",
       "у EARLY-AF это рецидив", "у EARLY-AF (2019) это рецидив")]),
    # Регресс, который прошёл зелёным: правка таблицы ограничений затёрла хвост
    # NOTICE, и три раздела со строкой для авторов исчезли. Проверка, сверявшая
    # только числа, удаление раздела не ловила.
    ("M8: удалить обязательный раздел NOTICE",
     [("NOTICE.md", "## Как обновляются навыки", "## Раздел удалён мутацией")]),
    ("M9: удалить строку для авторов из NOTICE",
     [("NOTICE.md", "создайте issue/PR", "обращайтесь в никуда")]),
    ("M10: сократить NOTICE до таблицы ограничений",
     [("NOTICE.md", "## Чего в репозитории нет и почему", "## Мутация")]),
    ("M11: лишний JSON в scripts/ (состав разошёлся с документами)",
     [("scripts/x-probe.json", "", "")]),
    ("M12: число проверок в AGENTS разошлось со stats.json",
     # число берём из stats.json, иначе якорь устаревает с каждой новой проверкой
     [("AGENTS.md", f"`python3 scripts/validate.py` ({json.load(open(os.path.join(ROOT, 'scripts', 'stats.json'), encoding='utf-8'))['validate_checks']} проверок",
       "`python3 scripts/validate.py` (21 проверка")]),
    ("M13: категория битых ссылок подменена в README",
     [("README.md", "внешний ресурс 81", "внешний ресурс 12")]),
    ("M14: «18 органов» вернулись в NOTICE",
     [("NOTICE.md", "18 анатомических структур", "18 органов")]),
    # Этап 2: правила исключения. Копия правил в любом скрипте — расхождение
    # на 24 файла, которое никто не видел.
    ("M16: служебный файл во вложенном каталоге навыка (references/)",
     [("skills/gsea/references/x_audit_result.json", "", "")]),
    ("M17: тяжёлые данные в database/ навыка без упоминания в тексте",
     [("skills/tf-target-gene-regulatory-network/database/probe.rds", "", "")]),
    ("M18: копия правил исключения вернулась в sync_upstreams.py",
     [("scripts/sync_upstreams.py", "HEAVY_SUFFIX = (",
       "EXCLUDE_MARKERS = (\"probe\",)\nHEAVY_SUFFIX = (")]),
    ("M19: рабочий скрипт помечен служебным (маркер _coverage вернулся)",
     [("scripts/exclusions.py", 'COVERAGE_NAMES = ("coverage.json"',
       'EXCLUDE_MARKERS = ("_coverage",)\nCOVERAGE_NAMES = ("coverage.json"')]),
    # Этап 4: числа и защита от чужого текста
    ("M20: чужой текст аннотации вернулся в trials-verified.json",
     [("docs/trials-verified.json", '"verified_via"',
       '"abstract": "Background Despite improvements in the management of atrial '
       'fibrillation, patients with this condition remain at increased risk for '
       'cardiovascular complications. It is unclear whether early rhythm-control '
       'therapy can reduce this risk. Methods In this international, '
       'investigator-initiated, parallel-group, open, blinded-outcome-assessment '
       'trial, we randomly assigned patients who had early atrial fibrillation", '
       '"verified_via"')]),
    ("M21: for-review.md разошёлся с деревом",
     [("docs/for-review.md", "## Ключевые числа", "## Другой раздел")],
     [["scripts/build_for_review.py", "--check"]]),
    ("M15: запись удалена из карты происхождения",
     [("scripts/upstream-origin.json", '"aav-vector-design-agent": "OpenClaw"',
       '"aav-vector-design-agent": "own"')]),
]


def run_case(name, edits, extra=None):
    tmp = tempfile.mkdtemp(prefix="vhmut_")
    try:
        for item in os.listdir(ROOT):
            if item in (".git", "__pycache__"):
                continue
            src = os.path.join(ROOT, item)
            dst = os.path.join(tmp, item)
            if os.path.isdir(src):
                shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", ".git"))
            else:
                shutil.copy2(src, dst)
        for rel, old, new in edits:
            p = os.path.join(tmp, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            if not os.path.exists(p):
                if not old:  # создаём файл — мутация «вернуть служебный артефакт»
                    with open(p, "w", encoding="utf-8") as f:
                        f.write("{}")
                    continue
                return f"{name}: ЯКОРЬ НЕ НАЙДЕН ({rel})"
            with open(p, encoding="utf-8") as f:
                t = f.read()
            if old not in t:
                return f"{name}: ЯКОРЬ НЕ НАЙДЕН ({rel}: {old[:40]})"
            with open(p, "w", encoding="utf-8") as f:
                f.write(t.replace(old, new, 1))
        # Мутация может проверяться не только валидатором: у чисел и документов
        # для внешней проверки свои проверки с флагом --check (они не дублируют
        # валидатор, а отвечают за воспроизводимость файла).
        cmd = extra or ["scripts/validate.py"]
        results = []
        for c in ([cmd] if isinstance(cmd, list) and cmd and isinstance(cmd[0], str)
                  else cmd):
            results.append(subprocess.run([sys.executable, "-B"] + c,
                                          cwd=tmp, capture_output=True, text=True))
        r = results[0]
        out = r.stdout or r.stderr
        first = [l.strip() for l in out.splitlines() if l.strip().startswith("[")
                 or "ПРОВАЛ" in l or "ОШИБКА" in l]
        caught = "ПОЙМАНО" if r.returncode else "ПРОПУЩЕНО ⚠"
        return f"{caught}  {name}  {first[0][:110] if first else ''}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    bad = 0
    for case in CASES:
        name, edits = case[0], case[1]
        extra = case[2] if len(case) > 2 else None
        res = run_case(name, edits)
        if "ПРОПУЩЕНО" in res or "ЯКОРЬ" in res:
            bad += 1
        print(res)
    print(f"\nитог: поймано {len(CASES) - bad} из {len(CASES)}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
