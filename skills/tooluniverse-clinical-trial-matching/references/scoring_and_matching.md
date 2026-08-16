# Scoring and Matching Detail Reference

Detailed scoring algorithms, matching rules, and evidence tier classification for the Clinical Trial Matching workflow.

---

## Trial Match Score Calculation (0-100)

### Composite Score Formula

```
Trial Match Score = Molecular Match (0-40) + Clinical Eligibility (0-25) + Evidence Strength (0-20) + Trial Phase (0-10) + Geographic Feasibility (0-5)
```

---

## Molecular Match Scoring (0-40 points)

### Scoring Table

| Criterion | Points | Description |
|-----------|--------|-------------|
| Exact biomarker match | 40 | Trial requires patient's specific variant |
| Gene-level match | 30 | Trial requires gene mutation, patient has specific variant |
| Pathway match | 20 | Trial targets same pathway as patient's biomarker |
| No molecular criteria | 10 | General disease trial |
| Excluded biomarker | 0 | Patient's biomarker is in exclusion criteria |

### Detailed Matching Logic

**Exact Biomarker Match (40 points)**:
- Trial inclusion criteria explicitly names the patient's specific variant (e.g., trial requires "EGFR L858R" and patient has EGFR L858R)
- Variant text found in eligibility context via case-insensitive substring match
- Example: Patient has "KRAS G12C", trial requires "KRAS G12C mutation" → 40 points

**Gene-Level Match (30 points)**:
- Trial requires any mutation in the same gene, but patient's specific variant not explicitly named
- Example: Patient has "EGFR L858R", trial requires "EGFR mutation" (any) → 30 points
- This is the most common match type for broad eligibility criteria

**Pathway Match (20 points)**:
- Trial targets the same signaling pathway but a different gene
- Requires domain knowledge mapping (e.g., EGFR pathway includes RAS/RAF/MEK/ERK)
- Example: Patient has "BRAF V600E", trial targets "MEK inhibitor" → 20 points

**No Molecular Criteria (10 points)**:
- Trial has no specific biomarker requirements
- Open to any patient with the disease
- Still potentially relevant as a clinical option

**Excluded Biomarker (0 points)**:
- Patient's biomarker appears in trial exclusion criteria
- Should be flagged as likely ineligible
- Example: Patient has "EGFR mutation", trial excludes "EGFR-mutated NSCLC" → 0 points

### Molecular Match Algorithm

```python
def score_molecular_match(patient_biomarkers, trial_requirements):
    """Score molecular match between patient and trial (0-40 points)."""
    if not trial_requirements['required_biomarkers'] and not trial_requirements['excluded_biomarkers']:
        return 10, 'No specific molecular criteria (general trial)'

    patient_genes = {b['gene'].upper() for b in patient_biomarkers}
    required_genes = {b['gene'].upper() for b in trial_requirements['required_biomarkers']}
    excluded_genes = {b['gene'].upper() for b in trial_requirements['excluded_biomarkers']}

    # Check exclusions first (highest priority)
    excluded_match = patient_genes & excluded_genes
    if excluded_match:
        return 0, f'Patient biomarker(s) {excluded_match} are in exclusion criteria'

    if not required_genes:
        return 10, 'No specific biomarker requirements found'

    # Check for gene match
    matched_genes = patient_genes & required_genes
    if matched_genes:
        # Check for specific variant match in eligibility context
        exact_variant_match = False
        for req in trial_requirements['required_biomarkers']:
            for pb in patient_biomarkers:
                if pb['gene'].upper() == req['gene'].upper():
                    alt = pb.get('alteration', '').upper()
                    if alt and alt in req.get('context', '').upper():
                        exact_variant_match = True
                        break

        if exact_variant_match:
            return 40, f'Exact biomarker match: {matched_genes} with specific variant'
        else:
            return 30, f'Gene-level match: {matched_genes} (specific variant match unclear)'

    return 5, 'No direct biomarker match found'
```

---

## Clinical Eligibility Scoring (0-25 points)

| Criterion | Points | Description |
|-----------|--------|-------------|
| All criteria met | 25 | Disease, stage, prior treatment all match |
| Most criteria met | 18 | 1-2 criteria unclear |
| Some criteria met | 10 | Several criteria unclear |
| Clearly ineligible | 0 | Fails major criterion |

### Eligibility Assessment Dimensions

Evaluate each dimension independently:

1. **Disease type match**: Does the trial target the patient's cancer type?
2. **Stage match**: Does the trial include the patient's disease stage?
3. **Prior treatment match**: Does the trial align with patient's treatment history?
4. **Performance status**: Does the patient meet ECOG/Karnofsky requirements?
5. **Age requirements**: Does patient fall within age range?
6. **Organ function**: Are lab value requirements likely met?

### Scoring Heuristic

- If all verifiable dimensions match → 25 points
- If 1-2 dimensions are unclear (cannot verify from available data) → 18 points
- If 3+ dimensions are unclear → 10 points
- If any dimension is a clear mismatch → 0 points
- Prior treatment exclusion is a hard stop (e.g., trial excludes patients who received drug X)

---

## Evidence Strength Scoring (0-20 points)

### Evidence Tier System

| Tier | Symbol | Criteria | Score |
|------|--------|----------|-------|
| **T1** | [T1] | FDA-approved biomarker-drug, NCCN guideline | 20 points |
| **T2** | [T2] | Phase III positive, clinical evidence | 15 points |
| **T3** | [T3] | Phase I/II results, preclinical | 10 points |
| **T4** | [T4] | Computational, mechanism inference | 5 points |

### Tier Assignment Rules

**T1 (20 points)** - Assign when:
- Drug has FDA approval for the specific biomarker-disease combination
- NCCN guideline recommends the biomarker-drug pairing
- FDA pharmacogenomic biomarker table lists the combination
- Verified via `FDA_get_indications_by_drug_name` or `fda_pharmacogenomic_biomarkers`

**T2 (15 points)** - Assign when:
- Phase III clinical trial shows positive results for the biomarker-drug pairing
- Robust clinical evidence from multiple studies
- Drug is approved for related indication (same biomarker, different disease)
- Verified via `PubMed_search_articles` or `get_clinical_trial_outcome_measures`

**T3 (10 points)** - Assign when:
- Phase I/II trial results available for the biomarker-drug pairing
- Preclinical evidence supporting the mechanism
- Drug is in Phase II/III development for this indication
- Verified via `PubMed_search_articles` or `civic_get_variants_by_gene`

**T4 (5 points)** - Assign when:
- Only computational/in silico evidence
- Mechanism of action suggests potential efficacy
- No clinical data available
- Drug targets the pathway but no direct evidence

### FDA Approval Check

```python
def check_fda_approval(tu, drug_name, disease_name):
    """Check FDA approval status and labeled indications."""
    result = tu.tools.FDA_get_indications_by_drug_name(drug_name=drug_name, limit=3)

    indications = result.get('results', [])
    for ind in indications:
        ind_text = str(ind.get('indications_and_usage', ''))
        if any(term.lower() in ind_text.lower() for term in disease_name.split()):
            return {
                'approved': True,
                'indication_text': ind_text[:500],
                'brand_name': ind.get('openfda.brand_name', []),
                'evidence_tier': 'T1'
            }

    return {'approved': False, 'indication_text': '', 'brand_name': [], 'evidence_tier': 'T3'}
```

---

## Drug-Biomarker Alignment

### Alignment Check Algorithm

```python
def score_drug_biomarker_alignment(patient_gene_symbols, drug_mechanisms):
    """Check if trial drug targets patient's biomarkers."""
    patient_genes_upper = {g.upper() for g in patient_gene_symbols}

    for mech in drug_mechanisms:
        target_genes = {g.upper() for g in mech.get('target_genes', [])}
        if patient_genes_upper & target_genes:
            return True, f"Drug targets {patient_genes_upper & target_genes} via {mech.get('mechanism')}"

    return False, "No direct target overlap with patient biomarkers"
```

### Drug Mechanism Resolution

1. Resolve drug name → ChEMBL ID via `OpenTargets_get_drug_id_description_by_name`
2. Get mechanisms of action via `OpenTargets_get_drug_mechanisms_of_action_by_chemblId`
3. Extract target gene symbols from mechanism rows
4. Compare target genes against patient's biomarker genes
5. If any overlap exists → drug aligns with patient's biomarkers

### Drug Classification

| Category | Examples | Alignment Impact |
|----------|----------|-----------------|
| Targeted therapy (TKI) | Osimertinib, Erlotinib, Sotorasib | Direct gene target match |
| Monoclonal antibody | Trastuzumab, Cetuximab | Direct protein target |
| Immunotherapy (ICI) | Pembrolizumab, Nivolumab | Indirect (PD-L1/TMB biomarker) |
| Chemotherapy | Carboplatin, Paclitaxel | No biomarker alignment |
| Combination | Various | Check each component |

---

## Trial Phase Scoring (0-10 points)

| Phase | Points | Rationale |
|-------|--------|-----------|
| Phase III | 10 | Established efficacy, regulatory pathway |
| Phase II | 8 | Preliminary efficacy data |
| Phase I/II | 6 | Early efficacy signals |
| Phase I | 4 | Safety/dose-finding only |
| Phase IV | 9 | Post-market, established safety |

### Phase Interpretation Notes

- Phase III trials have the strongest evidence and highest chance of regulatory approval
- Phase II trials may offer early access to promising therapies
- Phase I trials are primarily dose-finding but may be the only option for rare mutations
- Some trials are listed as "Phase I/II" which bridges safety and efficacy
- Phase IV (post-marketing surveillance) offers access to approved drugs with additional data collection

---

## Geographic Feasibility Scoring (0-5 points)

| Criterion | Points | Rationale |
|-----------|--------|-----------|
| Trial sites in patient's state/city | 5 | Minimal travel burden |
| Trial sites within 100 miles | 3 | Manageable travel |
| Trial sites in same country | 1 | International travel required |
| No location info or far away | 0 | Likely impractical |

### Location Analysis

```python
def analyze_trial_locations(locations_data, patient_location=None):
    """Analyze trial site locations and proximity."""
    if not locations_data:
        return {'total_sites': 0, 'countries': [], 'us_states': [], 'nearest': None}

    locations = locations_data.get('locations', [])
    countries = list(set(loc.get('country', '') for loc in locations if loc.get('country')))
    us_states = list(set(loc.get('state', '') for loc in locations if loc.get('country') == 'United States' and loc.get('state')))

    return {
        'total_sites': len(locations),
        'countries': countries,
        'us_states': us_states,
        'has_us_sites': 'United States' in countries,
        'locations': locations[:10]
    }
```

### Geographic Scoring Notes

- If patient provides a location, check for sites in same city/state first
- Multiple sites increase practical feasibility
- Consider whether trial requires frequent site visits (some trials allow local monitoring)
- International sites may still be relevant for patients willing to travel

---

## Recommendation Tiers

### Tier Assignment Rules

| Score Range | Tier | Label | Action |
|-------------|------|-------|--------|
| **80-100** | Tier 1 | Optimal Match | Strongly recommend - contact site immediately |
| **60-79** | Tier 2 | Good Match | Recommend - discuss with care team |
| **40-59** | Tier 3 | Possible Match | Consider - needs further eligibility review |
| **0-39** | Tier 4 | Exploratory | Backup option - consider if Tier 1-3 unavailable |

### Tier 1 (Optimal Match) Requirements

To achieve Tier 1, a trial typically needs:
- Exact biomarker match (30-40 points molecular)
- Clinical eligibility largely met (18-25 points)
- At least T2 evidence (15-20 points evidence)
- Phase II or later (6-10 points phase)

### Tier 2 (Good Match) Requirements

- Gene-level biomarker match (25-30 points molecular)
- Most clinical criteria met (15-18 points)
- At least T3 evidence (10-15 points evidence)
- Any phase (4-10 points phase)

### Special Cases

- **Molecular exclusion override**: If patient's biomarker is in exclusion criteria (0 molecular), the trial should not be recommended regardless of other scores
- **Evidence premium**: FDA-approved combinations (T1) significantly boost total score and should be highlighted
- **Geographic bonus**: Only 5 points max but can shift tier boundary for borderline scores

---

## CIViC Search Rules

### Critical Limitations

1. **`civic_search_variants` does NOT filter by query parameter** - returns alphabetically sorted results regardless of query
2. **`civic_search_evidence_items` does NOT filter by query parameter** - returns evidence alphabetically

### Recommended CIViC Workflow

1. Use known CIViC Gene IDs for direct lookups (see table below)
2. Call `civic_get_variants_by_gene(gene_id=<ID>, limit=100)` to get all variants for a gene
3. Filter results locally by variant name
4. For genes not in the known ID table, use `civic_search_variants` and filter results manually

### Known CIViC Gene IDs

| Gene | CIViC ID | Gene | CIViC ID |
|------|----------|------|----------|
| ALK | 1 | MET | 52 |
| ABL1 | 4 | PIK3CA | 37 |
| BRAF | 5 | ROS1 | 118 |
| EGFR | 19 | RET | 122 |
| ERBB2 | 20 | NTRK1 | 197 |
| KRAS | 30 | NTRK2 | 560 |
| TP53 | 45 | NTRK3 | 561 |
| BRCA1 | 2370 | BRCA2 | 2371 |
