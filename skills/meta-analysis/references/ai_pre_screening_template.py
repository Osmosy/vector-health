"""AI-Assisted Pre-Screening Template for R3 Adjudication.

PURPOSE
-------
For systematic review screening, the methodologically sound workflow requires
TWO independent human reviewers with Cohen's kappa, followed by adjudication
of disagreements (R3) by the first reviewer. R3 commonly involves 100+ records
and is the bottleneck.

This template generates AI-assisted *suggestions* (NOT decisions). The first
reviewer must still confirm or overturn each suggestion. This preserves
methodological integrity while compressing R3 from 2-3 hours x 2-3 days to
~30-60 minutes.

NOT a replacement for human reviewer. Methods boilerplate is provided below.

INPUT
-----
TSV with at minimum these columns:
    uid, title, abstract_preview, journal, doi, round2_tag, round2_reason

`round2_tag` values expected:
    INCLUDE   -> AI default = CONFIRM-INCLUDE; flag review/conf abstract patterns
    MAYBE     -> AI requires per-uid manual decisions (UNCERTAIN if not pre-coded)
    EXCLUDE   -> typically not in R3 sheet; if present, AI default = CONFIRM-EXCLUDE

OUTPUT
------
Same TSV plus columns:
    ai_suggestion : INCLUDE / EXCLUDE / UNCERTAIN / CONFIRM-INCLUDE / CONFIRM-EXCLUDE
    ai_reason     : one-sentence justification

USAGE
-----
1. Copy this file to your project's `1_Code/` directory.
2. Customize:
   - `PROJECT_PECOS` (eligibility criteria summary)
   - `MAYBE_DECISIONS` (per-uid manual judgments after reading each abstract)
   - `EXCLUDE_PATTERNS` (project-specific keyword patterns)
3. Run; review priority-sorted output (use companion `make_review_priority_view.py`).

METHODS BOILERPLATE
-------------------
"Round 3 adjudication of records flagged as 'maybe' by either reviewer was
performed by the first reviewer (initials) with AI-assisted pre-screening
(model name and version). The AI model was prompted with the prespecified
PECOS criteria and produced a suggestion plus brief justification for each
record; the first reviewer independently confirmed or overturned every
suggestion against the title, abstract, and (when needed) full text. AI
suggestions were not used as final inclusion decisions."

CITATION
--------
Inspired by emerging AI-assisted screening practice (e.g., Khalil et al.,
Syst Rev 2022). Document model and version in the manuscript.
"""
from __future__ import annotations
import csv
from pathlib import Path

# ============================================================================
# 1. PROJECT CONFIGURATION — customize per project
# ============================================================================

PROJECT_PECOS = """
Replace this string with a one-paragraph summary of your PECOS criteria.
Used as documentation only; the AI logic below must be coded explicitly.
"""

# Per-uid MAYBE decisions. Fill after reading each MAYBE abstract.
# Format: uid -> (suggestion, one-sentence reason)
# Suggestion values: INCLUDE / EXCLUDE / UNCERTAIN
MAYBE_DECISIONS: dict[str, tuple[str, str]] = {
    # "study_0042": ("INCLUDE", "Title confirms target population + intervention; design = RCT."),
    # "study_0099": ("EXCLUDE", "Conference abstract without full publication."),
    # "study_0123": ("UNCERTAIN", "Abstract truncated; full text needed to confirm intervention arm."),
}

# ============================================================================
# 2. INCLUDE-row heuristic classifier — common patterns; tune for your project
# ============================================================================

# Hard EXCLUDE keyword patterns (title or first 300 chars of abstract)
REVIEW_KEYWORDS = [
    "systematic review", "meta-analysis", "narrative review",
    " review of ", "scoping review", "review article",
    "editorial", "commentary", "letter to the editor",
]

# Conference abstract / supplement detection
CONF_JOURNAL_KEYWORDS = ["abstracts", "supplement"]
# Common DOI markers for supplements (tune to your field)
CONF_DOI_PATTERNS = ["suppl_", "/circ.144.suppl", "/circ.146.suppl",
                     ".abstract.", "-snis.", "-esmint."]

# Single case report markers
CASE_KEYWORDS = ["case report", "case series"]


def classify_include_row(uid: str, title: str, abstract: str, journal: str,
                         doi: str, reason: str,
                         topic_keywords: list[str] | None = None) -> tuple[str, str]:
    """Heuristic AI suggestion for INCLUDE-tagged rows.

    Default = CONFIRM-INCLUDE. Returns EXCLUDE for clear review/conference/
    case-report patterns, or when no topic keyword appears in title or abstract.

    Args:
        topic_keywords: list of lowercase keywords; if NONE found in title or
            abstract, suggest EXCLUDE. Pass project topic terms (e.g., for an
            aneurysm SR: ["aneurysm", "intracranial", "cerebral", "vasc"]).
    """
    t = title.lower()
    a = abstract.lower()
    j = journal.lower()
    d = doi.lower()

    # Review / editorial filter
    if (any(k in t for k in REVIEW_KEYWORDS) or
            any(k in a[:300] for k in REVIEW_KEYWORDS)):
        if "primary" not in a[:500] and "we developed" not in a[:500]:
            return ("EXCLUDE", "Likely review/editorial based on title/abstract keywords.")

    # Conference abstract filter
    if (any(k in j for k in CONF_JOURNAL_KEYWORDS) or
            any(k in d for k in CONF_DOI_PATTERNS)):
        return ("EXCLUDE",
                "Conference abstract / supplement; likely no full peer-reviewed publication.")

    # Single case report
    if any(k in t for k in CASE_KEYWORDS):
        if "single" in t or "single case" in a[:300]:
            return ("EXCLUDE", "Single case report -- excluded by study design criterion.")

    # Off-topic check
    if topic_keywords:
        if (not any(k in t for k in topic_keywords) and
                not any(k in a[:500] for k in topic_keywords)):
            return ("EXCLUDE", "No topic keyword in title or abstract.")

    return ("CONFIRM-INCLUDE",
            "Title/abstract consistent with PECOS; default include, verify at full-text extraction.")


# ============================================================================
# 3. Main pipeline
# ============================================================================

def run_pre_screening(src_tsv: Path, dst_tsv: Path,
                      topic_keywords: list[str] | None = None) -> None:
    """Read screening TSV, add ai_suggestion/ai_reason columns, write output."""
    rows = list(csv.DictReader(src_tsv.open(encoding="utf-8"), delimiter="\t"))
    if not rows:
        raise SystemExit(f"No rows in {src_tsv}")

    in_fields = list(rows[0].keys())
    extra = [c for c in ("ai_suggestion", "ai_reason") if c not in in_fields]
    out_fields = ["uid", "ai_suggestion", "ai_reason"] + [
        c for c in in_fields if c not in ("uid", "ai_suggestion", "ai_reason")
    ]

    counts: dict[str, int] = {}
    with dst_tsv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=out_fields, delimiter="\t",
                           quoting=csv.QUOTE_MINIMAL)
        w.writeheader()

        for r in rows:
            uid = r["uid"]
            tag = r.get("round2_tag", "").upper()

            if tag == "MAYBE":
                if uid in MAYBE_DECISIONS:
                    sug, why = MAYBE_DECISIONS[uid]
                else:
                    sug, why = ("UNCERTAIN",
                                "MAYBE row without pre-coded decision; full review needed.")
            elif tag == "INCLUDE":
                sug, why = classify_include_row(
                    uid,
                    r.get("title", ""),
                    r.get("abstract_preview", ""),
                    r.get("journal", ""),
                    r.get("doi", ""),
                    r.get("round2_reason", ""),
                    topic_keywords=topic_keywords,
                )
            elif tag == "EXCLUDE":
                sug, why = ("CONFIRM-EXCLUDE",
                            "Round 2 EXCLUDE; reviewer to confirm with brief check.")
            else:
                sug, why = ("UNCERTAIN", f"Unexpected round2_tag={tag!r}")

            counts[sug] = counts.get(sug, 0) + 1
            r["ai_suggestion"] = sug
            r["ai_reason"] = why
            w.writerow({k: r.get(k, "") for k in out_fields})

    print(f"Wrote {dst_tsv} ({len(rows)} rows)")
    print("AI suggestion distribution:")
    for k in sorted(counts):
        print(f"  {k}: {counts[k]}")


# ============================================================================
# 4. Companion: priority-sorted view
# ============================================================================

PRIORITY_ORDER = {
    "UNCERTAIN": 0,
    "EXCLUDE": 1,
    "INCLUDE": 2,
    "CONFIRM-EXCLUDE": 3,
    "CONFIRM-INCLUDE": 4,
}


def write_priority_view(src_tsv: Path, dst_tsv: Path) -> None:
    """Sort AI-pre-screened TSV by review priority."""
    rows = list(csv.DictReader(src_tsv.open(encoding="utf-8"), delimiter="\t"))
    rows.sort(key=lambda r: (PRIORITY_ORDER.get(r["ai_suggestion"], 9), r["uid"]))
    fields = list(rows[0].keys())
    with dst_tsv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter="\t",
                           quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote priority view: {dst_tsv}")


# ============================================================================
# 5. Example invocation
# ============================================================================

if __name__ == "__main__":
    # Customize these paths and topic keywords for your project.
    PROJECT_ROOT = Path(__file__).resolve().parent
    SRC = PROJECT_ROOT / "round3_adjudication_TEMPLATE.tsv"
    AI = PROJECT_ROOT / "round3_adjudication_AI_TEMPLATE.tsv"
    PRIORITY = PROJECT_ROOT / "round3_priority_TEMPLATE.tsv"

    TOPIC_KEYWORDS = ["TOPIC1", "TOPIC2"]  # e.g., ["aneurysm", "intracranial"]

    run_pre_screening(SRC, AI, topic_keywords=TOPIC_KEYWORDS)
    write_priority_view(AI, PRIORITY)
