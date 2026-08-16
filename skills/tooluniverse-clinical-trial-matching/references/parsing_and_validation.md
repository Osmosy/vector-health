# Parsing and Validation Detail Reference

Biomarker parsing rules, eligibility text parsing, gene resolution, edge case handling, and common use patterns for the Clinical Trial Matching workflow.

---

## Biomarker Parsing Rules

### Regex Patterns for Biomarker Extraction

| Pattern | Regex | Example Input | Parsed Output |
|---------|-------|--------------|---------------|
| Gene + amino acid change | `r'(\w+)\s+([A-Z]\d+[A-Z])'` | "EGFR L858R" | `{gene: "EGFR", alteration: "L858R", type: "mutation"}` |
| Gene + exon notation | `r'(\w+)\s+exon\s+(\d+)\s+(\w+)'` | "EGFR exon 19 deletion" | `{gene: "EGFR", alteration: "exon 19 deletion", type: "exon_alteration"}` |
| Gene fusion | `r'(\w+)[-/](\w+)\s*(fusion)?'` | "EML4-ALK fusion" | `{gene: "ALK", alteration: "EML4-ALK", type: "fusion", partner: "EML4"}` |
| Gene amplification | `r'(\w+)\s+amplification'` | "HER2 amplification" | `{gene: "HER2", alteration: "amplification", type: "amplification"}` |
| Expression level | `r'([\w-]+)\s+(\d+%&#124;high&#124;low&#124;positive&#124;negative)'` | "PD-L1 50%" | `{gene: "PD-L1", alteration: "50%", type: "expression"}` |
| Status biomarker | `r'(MSI&#124;TMB&#124;dMMR&#124;MMR)[-\s]*(high&#124;low&#124;stable&#124;deficient&#124;proficient)'` | "MSI-high" | `{gene: "MSI", alteration: "high", type: "status"}` |

### Full Parsing Function

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

## Gene Symbol Normalization

### Alias Mapping Table

| Common Alias | Official Symbol | Search Strategy |
|-------------|----------------|-----------------|
| HER2 | ERBB2 | Search both in trials |
| HER-2 | ERBB2 | Search both in trials |
| PD-L1 | CD274 | Often searched as "PD-L1" in trials |
| PDL1 | CD274 | Search as "PD-L1" in trials |
| PD-1 | PDCD1 | Search as "PD-1" in trials |
| PD1 | PDCD1 | Search as "PD-1" in trials |
| VEGF | VEGFA | Often searched as "VEGF" |
| BRCA | BRCA1/BRCA2 | Specify which BRCA gene |

### Gene Resolution Function

```python
def resolve_gene(tu, gene_symbol):
    """Resolve gene symbol to cross-database IDs."""
    alias_map = {
        'HER2': 'ERBB2', 'HER-2': 'ERBB2',
        'PD-L1': 'CD274', 'PDL1': 'CD274',
        'PD-1': 'PDCD1', 'PD1': 'PDCD1',
        'VEGF': 'VEGFA',
    }
    normalized = alias_map.get(gene_symbol.upper(), gene_symbol)

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

### Dual-Search Strategy for Aliases

When searching ClinicalTrials.gov for genes with common aliases, always search using BOTH terms:
- Example: For HER2 → search "HER2" AND "ERBB2" separately, then merge results
- Example: For PD-L1 → search "PD-L1" (more common in trial descriptions) AND "CD274"

---

## Eligibility Text Parsing

### Inclusion/Exclusion Splitting

```python
def split_eligibility_sections(eligibility_text):
    """Split eligibility text into inclusion and exclusion sections."""
    if 'Exclusion Criteria' in eligibility_text:
        parts = eligibility_text.split('Exclusion Criteria')
        return {
            'inclusion': parts[0],
            'exclusion': parts[1] if len(parts) > 1 else ''
        }
    return {
        'inclusion': eligibility_text,
        'exclusion': ''
    }
```

### Biomarker Requirement Extraction

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

### Basket Trial Detection Terms

The following terms in eligibility text indicate a basket/tumor-agnostic trial:
- "tumor-agnostic"
- "histology-independent"
- "basket"
- "any solid tumor"
- "all comers"
- "biomarker-selected"

---

## Biomarker Actionability Classification

### Classification Function

```python
def classify_biomarker_actionability(tu, gene_symbol, alteration):
    """Classify biomarker as FDA-approved, guideline, or investigational."""
    fda_result = tu.tools.fda_pharmacogenomic_biomarkers()
    fda_biomarkers = fda_result.get('results', [])

    fda_match = [b for b in fda_biomarkers if gene_symbol.upper() in str(b.get('Biomarker', '')).upper()]

    if fda_match:
        return {
            'level': 'FDA-approved',
            'drugs': [b.get('Drug') for b in fda_match],
            'labeling_sections': [b.get('LabelingSection') for b in fda_match]
        }

    return {'level': 'investigational', 'drugs': [], 'labeling_sections': []}
```

### Actionability Levels

| Level | Meaning | Scoring Impact |
|-------|---------|---------------|
| FDA-approved | Biomarker-drug combination has FDA labeling | Evidence Strength = T1 (20 pts) |
| Guideline | NCCN or other guideline recommends | Evidence Strength = T1-T2 |
| Investigational | No regulatory approval, research only | Evidence Strength = T3-T4 |

---

## Edge Case Handling

### No Matching Trials Found

If no trials match the patient's biomarker:
1. **Broaden search** - Remove specific variant, search gene-level (e.g., "EGFR mutation" instead of "EGFR L858R")
2. **Search pathway-level** - Look for trials targeting the same signaling pathway
3. **Search basket trials** - Look for tumor-agnostic/biomarker-driven studies
4. **Suggest additional biomarker testing** - Identify tests that could unlock more trial options
5. **Report alternative options** - Include off-label and compassionate use programs

### Rare Biomarkers

For uncommon mutations (e.g., unusual EGFR variants):
1. **Search gene-level trials** - Any EGFR mutation trial
2. **Search mechanism-level trials** - TKI trials broadly
3. **Check CIViC** - Any evidence on this specific variant
4. **Note variant rarity** - Flag in report as rare finding
5. **Suggest molecular tumor board** - Recommend expert consultation

### Multiple Biomarkers

For complex molecular profiles:
1. **Search independently** - Run separate searches for each biomarker
2. **Search combinations** - Look for trials requiring multiple biomarkers
3. **Identify multi-biomarker trials** - Some trials require specific co-mutations
4. **Score by most actionable** - Use the highest-value biomarker for primary scoring
5. **Flag synergistic targets** - Note potential combination benefit (e.g., EGFR + MET)

### Conflicting Eligibility

When patient meets some criteria but not others:
1. **Score partial match transparently** - Show exactly which criteria match/don't match
2. **Highlight met/unmet criteria** - Clear visual distinction in report
3. **Note waivable criteria** - Some criteria may be waived by PI
4. **Suggest contacting PI** - For edge cases, direct contact may resolve ambiguity
5. **Provide alternatives** - Trials without conflicting criteria

### Common Pitfalls

1. **ClinicalTrials.gov query complexity** - Overly specific queries (e.g., "NTRK fusion tumor agnostic") often return zero results. Start with simpler queries and combine.
2. **CIViC search limitations** - `civic_search_variants` and `civic_search_evidence_items` do NOT filter by the `query` parameter — they return alphabetically sorted results. Always use `civic_get_variants_by_gene` with the gene ID instead.
3. **Eligibility text inconsistency** - Some trials have poorly formatted eligibility criteria; use flexible parsing.
4. **Drug name variants** - Same drug may appear under different names (brand vs generic); normalize before matching.

---

## Common Use Patterns

### Pattern 1: Targeted Therapy Matching (Most Common)

**Input**: "NSCLC patient with EGFR L858R, failed platinum chemotherapy"

1. Resolve: NSCLC -> EFO_0003060, EGFR -> ENSG00000146648
2. Search: "non-small cell lung cancer" + "EGFR mutation" + "EGFR L858R"
3. Filter: Recruiting trials with EGFR molecular requirements
4. Match: Score trials by EGFR L858R specificity
5. Drugs: Identify TKIs (osimertinib, erlotinib, etc.) in trial arms
6. Evidence: Check FDA approval of EGFR TKIs for NSCLC
7. Report: Prioritize targeted therapy trials, include immunotherapy options

### Pattern 2: Immunotherapy Selection

**Input**: "Melanoma, TMB-high, PD-L1 positive, failed ipilimumab"

1. Resolve: Melanoma -> EFO_0000756
2. Search: "melanoma" + "TMB" + "PD-L1" + "immunotherapy"
3. Filter: Trials requiring PD-L1 or TMB testing
4. Match: Score by TMB/PD-L1 requirements
5. Drugs: Identify checkpoint inhibitors (pembrolizumab, nivolumab)
6. Evidence: Check FDA approval for TMB-high indications
7. Report: Focus on anti-PD-1/PD-L1 trials, combination immunotherapy

### Pattern 3: Basket Trial Identification

**Input**: "Any solid tumor with NTRK fusion"

1. Resolve: NTRK genes (NTRK1, NTRK2, NTRK3)
2. Search: "NTRK fusion" + "tumor agnostic" + "basket"
3. Filter: Biomarker-agnostic trials
4. Match: Score by NTRK-specific inclusion criteria
5. Drugs: Identify larotrectinib, entrectinib
6. Evidence: FDA tissue-agnostic approval for larotrectinib
7. Report: Highlight tumor-agnostic approval, broad eligibility

### Pattern 4: Post-Progression Options

**Input**: "Breast cancer, failed CDK4/6 inhibitors, ESR1 mutation"

1. Resolve: Breast cancer -> EFO_0000305, ESR1 -> ENSG00000091831
2. Search: "breast cancer" + "ESR1" + "CDK4/6 resistance"
3. Filter: Trials for post-CDK4/6 setting
4. Match: Score by ESR1 mutation and prior treatment requirements
5. Drugs: Identify novel endocrine agents, SERDs, ESR1-targeting drugs
6. Evidence: Check clinical data for post-CDK4/6 options
7. Report: Focus on resistance-overcoming strategies

### Pattern 5: Geographic Search

**Input**: "Lung cancer trials within 100 miles of Boston"

1. Search: "lung cancer" (broad)
2. Get locations for all candidate trials
3. Filter: Sites in Massachusetts and nearby states
4. Score: High geographic feasibility for Boston-area sites
5. Report: Prioritize by proximity, include contact info
