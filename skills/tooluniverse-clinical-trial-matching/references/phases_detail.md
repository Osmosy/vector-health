# Phases Detail Reference

Detailed execution code, tool parameters, and report templates for all 10 phases of the Clinical Trial Matching workflow.

---

## Phase 0: Tool Parameter Reference (CRITICAL)

**BEFORE calling ANY tool**, verify its parameters from this reference table.

### Clinical Trial Tools

| Tool | Parameters | Notes |
|------|-----------|-------|
| `search_clinical_trials` | `query_term` (REQUIRED str), `condition` (str), `intervention` (str), `pageSize` (int, default 10), `pageToken` (str) | Main search. Returns `{studies: [{NCT ID, brief_title, brief_summary, overall_status, condition, phase}], nextPageToken, total_count}` |
| `clinical_trials_search` | `action` (REQUIRED, must be `"search_studies"`), `condition` (str), `intervention` (str), `limit` (int) | Alternative search. Returns `{total_count, studies: [{nctId, title, status, conditions}]}` |
| `clinical_trials_get_details` | `action` (REQUIRED, must be `"get_study_details"`), `nct_id` (REQUIRED str) | Full trial details. Returns `{nctId, title, summary, eligibility: {eligibilityCriteria}, ...}` |
| `get_clinical_trial_eligibility_criteria` | `nct_ids` (REQUIRED array), `eligibility_criteria` (REQUIRED str, use `"all"`) | Returns `[{NCT ID, eligibility_criteria}]` |
| `get_clinical_trial_locations` | `nct_ids` (REQUIRED array), `location` (REQUIRED str, use `"all"`) | Returns `[{NCT ID, locations: [{facility, city, state, country}]}]` |
| `get_clinical_trial_descriptions` | `nct_ids` (REQUIRED array), `description_type` (REQUIRED str: `"brief"` or `"full"`) | Returns `[{NCT ID, brief_title, official_title, brief_summary, detailed_description}]` |
| `get_clinical_trial_status_and_dates` | `nct_ids` (REQUIRED array), `status_and_date` (REQUIRED str, use `"all"`) | Returns `[{NCT ID, overall_status, start_date, primary_completion_date, completion_date}]` |
| `get_clinical_trial_conditions_and_interventions` | `nct_ids` (REQUIRED array), `condition_and_intervention` (REQUIRED str, use `"all"`) | Returns `[{NCT ID, condition, arm_groups, interventions}]` |
| `get_clinical_trial_outcome_measures` | `nct_ids` (REQUIRED array), `outcome_measures` (str: `"primary"`, `"secondary"`, `"all"`) | Returns `[{NCT ID, primary_outcomes, secondary_outcomes}]` |
| `extract_clinical_trial_outcomes` | `nct_ids` (REQUIRED array), `outcome_measure` (str) | Returns trial outcome results |
| `extract_clinical_trial_adverse_events` | `nct_ids` (REQUIRED array), `adverse_event_type` (str) | Returns adverse event data |

### Molecular/Disease Tools

| Tool | Parameters | Notes |
|------|-----------|-------|
| `MyGene_query_genes` | `query` (str), `species` (str) | Returns `{hits: [{symbol, entrezgene, ensembl: {gene}, name}]}` |
| `OpenTargets_get_target_id_description_by_name` | `targetName` (str) | Returns `{data: {search: {hits: [{id, name, description}]}}}` |
| `OpenTargets_get_disease_id_description_by_name` | `diseaseName` (str) | Returns `{data: {search: {hits: [{id, name, description}]}}}` |
| `OpenTargets_get_associated_drugs_by_target_ensemblID` | `ensemblId` (str), `size` (int) | Returns `{data: {target: {knownDrugs: {count, rows: [{drug: {id, name, isApproved}, phase, mechanismOfAction, disease: {id, name}}]}}}}` |
| `OpenTargets_get_associated_drugs_by_disease_efoId` | `efoId` (str), `size` (int) | Returns `{data: {disease: {knownDrugs: {count, rows: [...]}}}}` |
| `OpenTargets_get_drug_id_description_by_name` | `drugName` (str) | Returns `{data: {search: {hits: [{id, name, description}]}}}` |
| `OpenTargets_get_drug_mechanisms_of_action_by_chemblId` | `chemblId` (str) | Returns `{data: {drug: {mechanismsOfAction: {rows: [{mechanismOfAction, actionType, targetName, targets}]}}}}` |
| `OpenTargets_get_approved_indications_by_drug_chemblId` | `chemblId` (str) | Returns `{data: {drug: {approvedIndications: [efoIds]}}}` |
| `OpenTargets_target_disease_evidence` | `ensemblId` (str), `efoId` (str), `size` (int) | Returns target-disease evidence rows |

### CIViC Tools

| Tool | Parameters | Notes |
|------|-----------|-------|
| `civic_search_variants` | `query` (str), `limit` (int) | Does NOT filter by query. Returns alphabetically sorted variants |
| `civic_get_variants_by_gene` | `gene_id` (int, CIViC gene ID), `limit` (int) | Returns `{data: {gene: {variants: {nodes: [{id, name}]}}}}`. Max 100 per call |
| `civic_search_evidence_items` | `query` (str), `limit` (int) | Does NOT filter by query. Returns evidence alphabetically |
| `civic_get_variant` | `variant_id` (int) | Returns `{data: {variant: {id, name}}}` |
| `civic_search_therapies` | `query` (str), `limit` (int) | Search therapies |
| `civic_search_diseases` | `query` (str), `limit` (int) | Search diseases |

**Known CIViC Gene IDs**: EGFR=19, BRAF=5, ALK=1, ABL1=4, KRAS=30, TP53=45, ERBB2=20, NTRK1=197, NTRK2=560, NTRK3=561, PIK3CA=37, MET=52, ROS1=118, RET=122, BRCA1=2370, BRCA2=2371

### Drug Information Tools

| Tool | Parameters | Notes |
|------|-----------|-------|
| `drugbank_get_targets_by_drug_name_or_drugbank_id` | `query`, `case_sensitive`, `exact_match`, `limit` (ALL REQUIRED) | Returns `{results: [{drug_name, drugbank_id, targets: [{name, organism, actions}]}]}` |
| `drugbank_get_indications_by_drug_name_or_drugbank_id` | `query`, `case_sensitive`, `exact_match`, `limit` (ALL REQUIRED) | Returns drug indications |
| `ChEMBL_search_drugs` | `query` (str), `limit` (int) | Returns `{status, data: {drugs: [...]}}` |
| `ChEMBL_get_drug_mechanisms` | `drug_chembl_id__exact` (str) | Returns drug mechanisms |
| `fda_pharmacogenomic_biomarkers` | `drug_name` (opt str), `biomarker` (opt str), `limit` (opt int, default 10) | Returns `{count, shown, results: [{Drug, TherapeuticArea, Biomarker, LabelingSection}]}`. Use `limit=1000` to get all. |
| `FDA_get_indications_by_drug_name` | `drug_name` (str), `limit` (int) | Returns FDA indications text |
| `FDA_get_mechanism_of_action_by_drug_name` | `drug_name` (str), `limit` (int) | Returns FDA MoA text |
| `FDA_get_clinical_studies_info_by_drug_name` | `drug_name` (str), `limit` (int) | Returns FDA clinical study info |
| `FDA_get_adverse_reactions_by_drug_name` | `drug_name` (str), `limit` (int) | Returns adverse reactions |

### Disease Ontology Tools

| Tool | Parameters | Notes |
|------|-----------|-------|
| `ols_search_efo_terms` | `query` (str), `limit` (int) | Returns `{data: {terms: [{iri, obo_id, short_form, label, description}]}}` |
| `ols_get_efo_term` | `term_id` (str) | Get specific EFO term details |
| `ols_get_efo_term_children` | `term_id` (str) | Get child terms |

### Literature Tools

| Tool | Parameters | Notes |
|------|-----------|-------|
| `PubMed_search_articles` | `query` (str), `max_results` (int) | Returns list of `{pmid, title, abstract, authors, journal, pub_date}` |
| `openalex_literature_search` | `query` (str), `limit` (int) | Returns literature results |

### PharmGKB Tools

| Tool | Parameters | Notes |
|------|-----------|-------|
| `PharmGKB_search_genes` | `query` (str) | Returns gene pharmacogenomics data |
| `PharmGKB_get_clinical_annotations` | `query` (str) | Returns clinical annotations |

---

## Phase 1: Patient Profile Standardization

**Goal**: Resolve all patient inputs to standardized identifiers for cross-database queries.

### 1.1 Disease Resolution

```python
def resolve_disease(tu, disease_name):
    """Resolve disease name to EFO ID and standard terminology."""
    # OpenTargets disease search
    result = tu.tools.OpenTargets_get_disease_id_description_by_name(diseaseName=disease_name)
    hits = result.get('data', {}).get('search', {}).get('hits', [])

    if hits:
        disease_info = hits[0]
        return {
            'efo_id': disease_info.get('id'),
            'name': disease_info.get('name'),
            'description': disease_info.get('description'),
            'original_input': disease_name
        }

    # Fallback: OLS EFO search
    ols_result = tu.tools.ols_search_efo_terms(query=disease_name, limit=5)
    ols_terms = ols_result.get('data', {}).get('terms', [])
    if ols_terms:
        term = ols_terms[0]
        return {
            'efo_id': term.get('short_form'),
            'name': term.get('label'),
            'description': term.get('description', [''])[0] if term.get('description') else '',
            'original_input': disease_name
        }

    return {'efo_id': None, 'name': disease_name, 'description': '', 'original_input': disease_name}
```

**Response**: `{efo_id: "EFO_0003060", name: "non-small cell lung carcinoma", description: "...", original_input: "..."}`

### 1.2 Gene/Biomarker Resolution

```python
def resolve_gene(tu, gene_symbol):
    """Resolve gene symbol to cross-database IDs."""
    # Normalize common aliases
    alias_map = {
        'HER2': 'ERBB2', 'HER-2': 'ERBB2',
        'PD-L1': 'CD274', 'PDL1': 'CD274',
        'PD-1': 'PDCD1', 'PD1': 'PDCD1',
        'VEGF': 'VEGFA',
    }
    normalized = alias_map.get(gene_symbol.upper(), gene_symbol)

    # MyGene resolution
    result = tu.tools.MyGene_query_genes(query=normalized, species='human')
    hits = result.get('hits', [])

    gene_hit = None
    for hit in hits:
        if hit.get('symbol', '').upper() == normalized.upper():
            gene_hit = hit
            break
    if not gene_hit and hits:
        gene_hit = hits[0]

    if gene_hit:
        ensembl = gene_hit.get('ensembl', {})
        ensembl_id = ensembl.get('gene') if isinstance(ensembl, dict) else (ensembl[0].get('gene') if isinstance(ensembl, list) and ensembl else None)
        return {
            'symbol': gene_hit.get('symbol'),
            'entrez_id': gene_hit.get('entrezgene'),
            'ensembl_id': ensembl_id,
            'name': gene_hit.get('name'),
            'original_input': gene_symbol
        }

    return {'symbol': gene_symbol, 'entrez_id': None, 'ensembl_id': None, 'name': None, 'original_input': gene_symbol}
```

### 1.3 Biomarker Actionability Classification

Classify each biomarker using FDA pharmacogenomic biomarkers list:

```python
def classify_biomarker_actionability(tu, gene_symbol, alteration):
    """Classify biomarker as FDA-approved, guideline, or investigational."""
    # Check FDA pharmacogenomic biomarkers
    fda_result = tu.tools.fda_pharmacogenomic_biomarkers()
    fda_biomarkers = fda_result.get('results', [])

    fda_match = [b for b in fda_biomarkers if gene_symbol.upper() in str(b.get('Biomarker', '')).upper()]

    if fda_match:
        return {
            'level': 'FDA-approved',
            'drugs': [b.get('Drug') for b in fda_match],
            'labeling_sections': [b.get('LabelingSection') for b in fda_match]
        }

    # Check OpenTargets for drugs targeting this gene
    # (done in Phase 5)

    return {'level': 'investigational', 'drugs': [], 'labeling_sections': []}
```

### 1.4 Parse Molecular Alterations

```python
def parse_biomarker(biomarker_text):
    """Parse free-text biomarker into structured components."""
    import re

    # Pattern: "GENE VARIANT" (e.g., "EGFR L858R")
    mutation_match = re.match(r'(\w+)\s+([A-Z]\d+[A-Z])', biomarker_text, re.IGNORECASE)
    if mutation_match:
        return {'gene': mutation_match.group(1), 'alteration': mutation_match.group(2), 'type': 'mutation'}

    # Pattern: "GENE exon N deletion/insertion"
    exon_match = re.match(r'(\w+)\s+exon\s+(\d+)\s+(\w+)', biomarker_text, re.IGNORECASE)
    if exon_match:
        return {'gene': exon_match.group(1), 'alteration': f'exon {exon_match.group(2)} {exon_match.group(3)}', 'type': 'exon_alteration'}

    # Pattern: "GENE1-GENE2 fusion" or "GENE1/GENE2"
    fusion_match = re.match(r'(\w+)[-/](\w+)\s*(fusion)?', biomarker_text, re.IGNORECASE)
    if fusion_match:
        return {'gene': fusion_match.group(2), 'alteration': f'{fusion_match.group(1)}-{fusion_match.group(2)}', 'type': 'fusion', 'partner': fusion_match.group(1)}

    # Pattern: "GENE amplification"
    amp_match = re.match(r'(\w+)\s+amplification', biomarker_text, re.IGNORECASE)
    if amp_match:
        return {'gene': amp_match.group(1), 'alteration': 'amplification', 'type': 'amplification'}

    # Pattern: "PD-L1 XX%"
    expression_match = re.match(r'([\w-]+)\s+(\d+%|high|low|positive|negative)', biomarker_text, re.IGNORECASE)
    if expression_match:
        return {'gene': expression_match.group(1), 'alteration': expression_match.group(2), 'type': 'expression'}

    # Pattern: "MSI-high", "TMB-high"
    status_match = re.match(r'(MSI|TMB|dMMR|MMR)[-\s]*(high|low|stable|deficient|proficient)', biomarker_text, re.IGNORECASE)
    if status_match:
        return {'gene': status_match.group(1), 'alteration': status_match.group(2), 'type': 'status'}

    # Fallback: treat as gene name
    return {'gene': biomarker_text.split()[0], 'alteration': ' '.join(biomarker_text.split()[1:]), 'type': 'unknown'}
```

---

## Phase 2: Broad Trial Discovery

**Goal**: Cast a wide net to find all potentially relevant clinical trials.

### 2.1 Disease-Based Trial Search

```python
def search_trials_by_disease(tu, disease_name, status_filter=None, phase_filter=None, page_size=20):
    """Search ClinicalTrials.gov by disease/condition."""
    query_parts = []
    if status_filter:
        query_parts.append(f'AREA[OverallStatus]{status_filter}')
    if phase_filter:
        query_parts.append(phase_filter)

    query_term = ' AND '.join(query_parts) if query_parts else disease_name

    result = tu.tools.search_clinical_trials(
        condition=disease_name,
        query_term=query_term if query_parts else disease_name,
        pageSize=page_size
    )

    if isinstance(result, str):
        return []

    return result.get('studies', [])
```

### 2.2 Biomarker-Specific Trial Search

```python
def search_trials_by_biomarker(tu, gene_symbol, alteration, disease_name=None, page_size=15):
    """Search trials mentioning specific biomarkers."""
    biomarker_query = f'{gene_symbol} {alteration}' if alteration else gene_symbol

    result = tu.tools.search_clinical_trials(
        condition=disease_name if disease_name else '',
        query_term=biomarker_query,
        pageSize=page_size
    )

    if isinstance(result, str):
        return []

    return result.get('studies', [])
```

### 2.3 Intervention-Based Trial Search

```python
def search_trials_by_intervention(tu, drug_name, disease_name=None, page_size=10):
    """Search trials by intervention/drug name."""
    result = tu.tools.search_clinical_trials(
        condition=disease_name if disease_name else '',
        intervention=drug_name,
        query_term=drug_name,
        pageSize=page_size
    )

    if isinstance(result, str):
        return []

    return result.get('studies', [])
```

### 2.4 Alternative Search (clinical_trials_search)

```python
def search_trials_alternative(tu, condition, intervention=None, limit=10):
    """Alternative trial search with different API endpoint."""
    params = {
        'action': 'search_studies',
        'condition': condition,
        'limit': limit
    }
    if intervention:
        params['intervention'] = intervention

    result = tu.tools.clinical_trials_search(**params)

    return result.get('studies', [])
```

### 2.5 Deduplication

```python
def deduplicate_trials(trial_lists):
    """Merge and deduplicate trials from multiple searches."""
    seen_ncts = set()
    unique_trials = []

    for trials in trial_lists:
        for trial in trials:
            nct = trial.get('NCT ID') or trial.get('nctId', '')
            if nct and nct not in seen_ncts:
                seen_ncts.add(nct)
                unique_trials.append(trial)

    return unique_trials
```

---

## Phase 3: Trial Characterization

**Goal**: Get detailed information for the top candidate trials.

### 3.1 Get Eligibility Criteria (Batch)

```python
def get_trial_eligibility(tu, nct_ids):
    """Get eligibility criteria for multiple trials."""
    all_criteria = []
    for i in range(0, len(nct_ids), 10):
        batch = nct_ids[i:i+10]
        result = tu.tools.get_clinical_trial_eligibility_criteria(
            nct_ids=batch,
            eligibility_criteria='all'
        )
        if isinstance(result, list):
            all_criteria.extend(result)

    return all_criteria
    # Returns: [{NCT ID, eligibility_criteria: "Inclusion Criteria:\n...\nExclusion Criteria:\n..."}]
```

### 3.2 Get Conditions and Interventions (Batch)

```python
def get_trial_interventions(tu, nct_ids):
    """Get conditions, arm groups, and interventions for multiple trials."""
    all_interventions = []
    for i in range(0, len(nct_ids), 10):
        batch = nct_ids[i:i+10]
        result = tu.tools.get_clinical_trial_conditions_and_interventions(
            nct_ids=batch,
            condition_and_intervention='all'
        )
        if isinstance(result, list):
            all_interventions.extend(result)

    return all_interventions
    # Returns: [{NCT ID, condition, arm_groups, interventions}]
```

### 3.3 Get Locations (Batch)

```python
def get_trial_locations(tu, nct_ids):
    """Get trial site locations."""
    all_locations = []
    for i in range(0, len(nct_ids), 10):
        batch = nct_ids[i:i+10]
        result = tu.tools.get_clinical_trial_locations(
            nct_ids=batch,
            location='all'
        )
        if isinstance(result, list):
            all_locations.extend(result)

    return all_locations
```

### 3.4 Get Status and Dates (Batch)

```python
def get_trial_status(tu, nct_ids):
    """Get enrollment status and key dates."""
    all_status = []
    for i in range(0, len(nct_ids), 10):
        batch = nct_ids[i:i+10]
        result = tu.tools.get_clinical_trial_status_and_dates(
            nct_ids=batch,
            status_and_date='all'
        )
        if isinstance(result, list):
            all_status.extend(result)

    return all_status
```

### 3.5 Get Full Descriptions (Batch)

```python
def get_trial_descriptions(tu, nct_ids):
    """Get detailed trial descriptions."""
    all_descriptions = []
    for i in range(0, len(nct_ids), 10):
        batch = nct_ids[i:i+10]
        result = tu.tools.get_clinical_trial_descriptions(
            nct_ids=batch,
            description_type='full'
        )
        if isinstance(result, list):
            all_descriptions.extend(result)

    return all_descriptions
```

---

## Phase 4: Molecular Eligibility Matching

**Goal**: Determine how well the patient's molecular profile matches each trial's requirements.

### 4.1 Parse Eligibility Text for Biomarker Requirements

```python
def extract_biomarker_requirements(eligibility_text):
    """Extract biomarker requirements from eligibility criteria text."""
    import re

    requirements = {
        'required_biomarkers': [],
        'excluded_biomarkers': [],
        'biomarker_agnostic': False
    }

    if not eligibility_text:
        return requirements

    text_upper = eligibility_text.upper()

    inclusion_section = eligibility_text.split('Exclusion Criteria')[0] if 'Exclusion Criteria' in eligibility_text else eligibility_text
    exclusion_section = eligibility_text.split('Exclusion Criteria')[1] if 'Exclusion Criteria' in eligibility_text else ''

    gene_patterns = [
        r'(?:EGFR|KRAS|BRAF|ALK|ROS1|RET|MET|NTRK|HER2|ERBB2|PIK3CA|BRCA|PD-?L1|MSI|TMB|dMMR)',
    ]

    for pattern in gene_patterns:
        for match in re.finditer(pattern, inclusion_section, re.IGNORECASE):
            gene = match.group(0).upper()
            context = inclusion_section[max(0, match.start()-100):match.end()+100]
            requirements['required_biomarkers'].append({
                'gene': gene,
                'context': context.strip()
            })

        for match in re.finditer(pattern, exclusion_section, re.IGNORECASE):
            gene = match.group(0).upper()
            context = exclusion_section[max(0, match.start()-100):match.end()+100]
            requirements['excluded_biomarkers'].append({
                'gene': gene,
                'context': context.strip()
            })

    basket_terms = ['tumor-agnostic', 'histology-independent', 'basket', 'any solid tumor', 'all comers', 'biomarker-selected']
    if any(term in text_upper.lower() for term in basket_terms):
        requirements['biomarker_agnostic'] = True

    return requirements
```

### 4.2 Score Molecular Match

```python
def score_molecular_match(patient_biomarkers, trial_requirements):
    """Score molecular match between patient and trial (0-40 points)."""
    if not trial_requirements['required_biomarkers'] and not trial_requirements['excluded_biomarkers']:
        return 10, 'No specific molecular criteria (general trial)'

    patient_genes = {b['gene'].upper() for b in patient_biomarkers}
    required_genes = {b['gene'].upper() for b in trial_requirements['required_biomarkers']}
    excluded_genes = {b['gene'].upper() for b in trial_requirements['excluded_biomarkers']}

    excluded_match = patient_genes & excluded_genes
    if excluded_match:
        return 0, f'Patient biomarker(s) {excluded_match} are in exclusion criteria'

    if not required_genes:
        return 10, 'No specific biomarker requirements found'

    matched_genes = patient_genes & required_genes
    if matched_genes:
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

## Phase 5: Drug-Biomarker Alignment

**Goal**: Verify that trial drugs actually target the patient's biomarkers.

### 5.1 Identify Trial Drugs and Mechanisms

```python
def get_drug_mechanism_info(tu, drug_name):
    """Get drug mechanism, targets, and approval status."""
    result = tu.tools.OpenTargets_get_drug_id_description_by_name(drugName=drug_name)
    hits = result.get('data', {}).get('search', {}).get('hits', [])

    if not hits:
        return {'drug_name': drug_name, 'chembl_id': None, 'mechanisms': [], 'is_approved': False}

    drug_info = hits[0]
    chembl_id = drug_info.get('id')

    moa_result = tu.tools.OpenTargets_get_drug_mechanisms_of_action_by_chemblId(chemblId=chembl_id)
    moa_rows = moa_result.get('data', {}).get('drug', {}).get('mechanismsOfAction', {}).get('rows', [])

    mechanisms = []
    for row in moa_rows:
        targets = row.get('targets', [])
        mechanisms.append({
            'mechanism': row.get('mechanismOfAction'),
            'action_type': row.get('actionType'),
            'target_name': row.get('targetName'),
            'target_genes': [t.get('approvedSymbol') for t in targets]
        })

    approval_result = tu.tools.OpenTargets_get_drug_approval_status_by_chemblId(chemblId=chembl_id)

    return {
        'drug_name': drug_name,
        'chembl_id': chembl_id,
        'description': drug_info.get('description'),
        'mechanisms': mechanisms,
        'is_approved': 'approved' in drug_info.get('description', '').lower()
    }
```

### 5.2 Score Drug-Biomarker Alignment

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

---

## Phase 6: Evidence Assessment

**Goal**: Assess evidence strength for drug efficacy in similar patient populations.

### 6.1 FDA Approval Evidence

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

### 6.2 Literature Evidence

```python
def get_literature_evidence(tu, gene, alteration, drug_name, disease_name):
    """Search PubMed for evidence of drug efficacy for this biomarker."""
    query = f'{gene} {alteration} {drug_name} {disease_name} clinical trial'
    result = tu.tools.PubMed_search_articles(query=query, max_results=5)

    articles = result if isinstance(result, list) else result.get('articles', [])
    return articles
```

### 6.3 CIViC Evidence (if available)

```python
def get_civic_evidence(tu, gene_symbol, civic_gene_id):
    """Get CIViC clinical evidence for gene variants."""
    if not civic_gene_id:
        return []

    result = tu.tools.civic_get_variants_by_gene(gene_id=civic_gene_id, limit=100)
    variants = result.get('data', {}).get('gene', {}).get('variants', {}).get('nodes', [])
    return variants
```

### 6.4 Evidence Tier Classification

| Tier | Symbol | Criteria | Score Impact |
|------|--------|----------|-------------|
| **T1** | [T1] | FDA-approved biomarker-drug, NCCN guideline | 20 points |
| **T2** | [T2] | Phase III positive, clinical evidence | 15 points |
| **T3** | [T3] | Phase I/II results, preclinical | 10 points |
| **T4** | [T4] | Computational, mechanism inference | 5 points |

---

## Phase 7: Geographic & Feasibility Analysis

**Goal**: Assess practical feasibility of trial enrollment.

### 7.1 Location Analysis

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

### 7.2 Geographic Scoring

| Criterion | Points |
|-----------|--------|
| Trial sites in patient's state/city | 5 |
| Trial sites within 100 miles | 3 |
| Trial sites in same country | 1 |
| No location info or far away | 0 |

---

## Phase 8: Alternative Options

**Goal**: Identify basket trials, expanded access, and related studies.

### 8.1 Basket Trial Search

**IMPORTANT**: ClinicalTrials.gov search is sensitive to query complexity. Overly specific queries like "NTRK fusion tumor agnostic" may return zero results. Use simpler queries and combine results.

```python
def search_basket_trials(tu, biomarker, page_size=10):
    """Search for basket/biomarker-driven trials.

    NOTE: Use simpler queries first (e.g., 'NTRK solid tumor'),
    then more specific ones. Complex multi-word queries often fail.
    """
    query_terms = [
        f'{biomarker} solid tumor',
        f'{biomarker}',
        f'{biomarker} basket',
    ]

    all_trials = []
    for query in query_terms:
        result = tu.tools.search_clinical_trials(
            query_term=query,
            pageSize=page_size
        )
        if not isinstance(result, str):
            all_trials.extend(result.get('studies', []))

    return deduplicate_trials([all_trials])
```

### 8.2 Expanded Access Search

```python
def search_expanded_access(tu, drug_name):
    """Search for expanded access / compassionate use programs."""
    result = tu.tools.search_clinical_trials(
        query_term=f'{drug_name} expanded access',
        pageSize=5
    )

    if isinstance(result, str):
        return []

    return result.get('studies', [])
```

---

## Execution Strategy

### Parallelization Opportunities

Many tool calls can be executed in parallel to speed up the workflow:

**Parallel Group 1** (Phase 1 - can all run simultaneously):
- `MyGene_query_genes` for each gene
- `OpenTargets_get_disease_id_description_by_name` for disease
- `ols_search_efo_terms` for disease
- `fda_pharmacogenomic_biomarkers` (no params)

**Parallel Group 2** (Phase 2 - can all run simultaneously):
- `search_clinical_trials` with disease condition
- `search_clinical_trials` with biomarker query
- `search_clinical_trials` with intervention query
- `clinical_trials_search` as alternative

**Parallel Group 3** (Phase 3 - can all run simultaneously):
- `get_clinical_trial_eligibility_criteria` for all NCT IDs
- `get_clinical_trial_conditions_and_interventions` for all NCT IDs
- `get_clinical_trial_locations` for all NCT IDs
- `get_clinical_trial_status_and_dates` for all NCT IDs
- `get_clinical_trial_descriptions` for all NCT IDs

**Parallel Group 4** (Phases 5-6 - for each drug):
- `OpenTargets_get_drug_id_description_by_name` for drug
- `OpenTargets_get_drug_mechanisms_of_action_by_chemblId` for drug
- `FDA_get_indications_by_drug_name` for drug
- `PubMed_search_articles` for evidence

### Error Handling

For each tool call:
1. Wrap in try/except
2. Check for empty results
3. Use fallback tools when primary fails
4. Document what failed in completeness checklist
5. Never let one failure block the entire analysis

### Performance Optimization

- Batch NCT IDs in groups of 10 for detail tools
- Limit initial search to 20-30 trials per search strategy
- Focus detailed analysis on top 15-20 candidates after initial filtering
- Cache gene/disease resolution results for reuse across phases

---

## Phase 10: Report Synthesis

### Full Report Template

```markdown
# Clinical Trial Matching Report

**Patient**: [Disease type] with [biomarker(s)]
**Date**: [Current date]
**Trials Analyzed**: [N total] | **Top Matches**: [N with score >= 60]

---

## Executive Summary

**Top 3 Trial Recommendations**:

1. **[NCT ID]** - [Brief title] (Score: XX/100, Tier N)
   - Phase: [Phase], Status: [Status]
   - Why: [Key reason for match]

2. **[NCT ID]** - [Brief title] (Score: XX/100, Tier N)
   ...

3. **[NCT ID]** - [Brief title] (Score: XX/100, Tier N)
   ...

---

## Patient Profile Summary

| Parameter | Value | Standardized |
|-----------|-------|-------------|
| Disease | [input] | [EFO name] (EFO_XXXX) |
| Biomarker(s) | [input] | [gene: variant, type] |
| Stage | [input] | [standardized] |
| Prior Treatment | [input] | [standardized] |
| Performance Status | [input] | [ECOG score] |
| Location | [input] | [city, state] |

### Biomarker Actionability
| Biomarker | Actionability Level | FDA-Approved Drugs | Evidence |
|-----------|--------------------|--------------------|----------|
| [gene variant] | [FDA-approved/investigational] | [drugs] | [T1/T2/T3/T4] |

---

## Ranked Trial Matches

### Trial 1: [NCT ID] - [Title]

**Trial Match Score: XX/100** (Tier N: [Label])

| Component | Score | Details |
|-----------|-------|---------|
| Molecular Match | XX/40 | [explanation] |
| Clinical Eligibility | XX/25 | [explanation] |
| Evidence Strength | XX/20 | [explanation] |
| Trial Phase | XX/10 | [phase] |
| Geographic | XX/5 | [location info] |

**Trial Details**:
- **Phase**: [Phase]
- **Status**: [Recruiting/Active/etc.]
- **Sponsor**: [Sponsor]
- **Start Date**: [Date]
- **Estimated Completion**: [Date]

**Interventions**:
- [Drug name]: [Mechanism] | [Dosing info if available]
- [Comparator]: [Description]

**Molecular Eligibility Match**:
- Required biomarkers: [list]
- Patient match: [Exact/Gene-level/Pathway/None]
- Notes: [details]

**Clinical Eligibility Assessment**:
- Disease type: [Match/Mismatch]
- Stage: [Match/Mismatch/Unclear]
- Prior treatment: [Match/Mismatch/Unclear]
- Performance status: [Match/Mismatch/Unclear]

**Evidence for Efficacy**:
- FDA approval: [Yes/No for this indication]
- Clinical results: [Phase III/II/I data if available]
- Mechanism alignment: [Drug targets patient's biomarker: Yes/No]
- Literature: [Key references]

**Trial Sites** (first 5):
- [City, State, Country]
- ...

**Next Steps**: [Contact info, enrollment instructions]

[Repeat for each matched trial]

---

## Trials by Category

### Targeted Therapy Trials
[List trials with targeted agents matching patient's biomarkers]

### Immunotherapy Trials
[List immunotherapy trials, noting PD-L1/TMB/MSI requirements]

### Combination Therapy Trials
[List trials with drug combinations]

### Basket/Platform Trials
[List biomarker-agnostic or multi-arm trials]

---

## Additional Testing Recommendations

If the patient has not been tested for certain biomarkers, these trials would become relevant:

| Biomarker | Test Needed | Trials Unlocked | Priority |
|-----------|-------------|----------------|----------|
| [e.g., TMB] | [NGS panel] | [NCT IDs] | [High/Medium/Low] |

---

## Alternative Options

### Expanded Access Programs
[List any expanded access or compassionate use programs]

### Off-Label Options
[FDA-approved drugs for other indications with same biomarker]

---

## Evidence Grading Summary

| Evidence Tier | Count | Description |
|--------------|-------|-------------|
| T1 (FDA/Guideline) | N | FDA-approved biomarker-drug, clinical guideline |
| T2 (Clinical) | N | Phase III data, robust clinical evidence |
| T3 (Emerging) | N | Phase I/II, preclinical evidence |
| T4 (Exploratory) | N | Computational, mechanism inference |

---

## Completeness Checklist

| Analysis Step | Status | Source |
|--------------|--------|--------|
| Disease standardization | [Done/Partial/Failed] | [OpenTargets/OLS] |
| Gene resolution | [Done/Partial/Failed] | [MyGene] |
| Biomarker actionability | [Done/Partial/Failed] | [FDA biomarkers] |
| Disease trial search | [Done/Partial/Failed] | [ClinicalTrials.gov] |
| Biomarker trial search | [Done/Partial/Failed] | [ClinicalTrials.gov] |
| Intervention trial search | [Done/Partial/Failed] | [ClinicalTrials.gov] |
| Eligibility parsing | [Done/Partial/Failed] | [ClinicalTrials.gov] |
| Drug mechanism analysis | [Done/Partial/Failed] | [OpenTargets/ChEMBL] |
| Evidence assessment | [Done/Partial/Failed] | [FDA/PubMed/CIViC] |
| Location analysis | [Done/Partial/Failed] | [ClinicalTrials.gov] |
| Basket trial search | [Done/Partial/Failed] | [ClinicalTrials.gov] |
| Expanded access search | [Done/Partial/Failed] | [ClinicalTrials.gov] |
| Scoring & ranking | [Done/Partial/Failed] | [Composite] |

---

## Disclaimer

This report is for informational and research purposes only. Clinical trial eligibility is ultimately determined by the trial investigators based on complete medical records. Patients should discuss all options with their healthcare team. Trial availability and status may change; verify current status at [ClinicalTrials.gov](https://clinicaltrials.gov).

## Sources

All data sourced from:
- ClinicalTrials.gov (trial search, eligibility, locations, status)
- OpenTargets Platform (drug-target associations, disease ontology)
- CIViC (clinical variant interpretations)
- ChEMBL (drug mechanisms, targets)
- FDA (approved indications, pharmacogenomic biomarkers, drug labels)
- DrugBank (drug targets, indications)
- PharmGKB (pharmacogenomics)
- PubMed/NCBI (literature evidence)
- OLS/EFO (disease ontology)
- MyGene (gene identifier resolution)
```
