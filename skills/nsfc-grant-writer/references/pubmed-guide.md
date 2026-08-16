# PubMed Literature Search Guide

## Overview

All literature cited in the grant application MUST be retrieved from PubMed using real API calls. Do NOT fabricate references.

---

## Search Workflow

### Step 1: Extract search terms from the hypothesis

From the scientific hypothesis, identify:
- **Disease/condition** (e.g., hepatocellular carcinoma, Alzheimer's disease)
- **Key molecules** (e.g., EGFR, p53, miR-21)
- **Biological process/pathway** (e.g., epithelial-mesenchymal transition, autophagy, Wnt signaling)
- **Mechanism keywords** (e.g., methylation, ubiquitination, ferroptosis)

### Step 2: Build search queries

Construct 3-5 targeted queries covering different aspects of the background:

**Query templates**:
```
{molecule}[Title/Abstract] AND {disease}[Title/Abstract]
{pathway}[Title/Abstract] AND {disease}[Title/Abstract] AND review[Publication Type]
{molecule}[Title/Abstract] AND {mechanism}[Title/Abstract]
{disease}[Title/Abstract] AND {process}[Title/Abstract] AND prognosis[Title/Abstract]
```

### Step 3: Execute PubMed API searches

Use the NCBI E-utilities API. No API key required for basic use (rate limit: 3 requests/second).

**Search endpoint**:
```
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={QUERY}&retmax=10&sort=relevance&retmode=json
```

**Fetch details endpoint** (use PMIDs from search results):
```
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={PMID1,PMID2,...}&rettype=abstract&retmode=xml
```

**Summary endpoint** (faster, for getting titles/authors/journal):
```
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={PMID1,PMID2,...}&retmode=json
```

### Step 4: Select relevant references

From search results, select references based on:
- **Relevance**: directly supports the point being made
- **Quality**: prefer high-impact journals, systematic reviews, or landmark papers
- **Recency**: prefer papers from last 5 years; seminal older papers are acceptable
- **Diversity**: cover different aspects (epidemiology, mechanism, clinical relevance)

Target: 20-30 total references for Section I.

### Step 5: Format references in APA

Extract from API response:
- Authors (LastName Initials format)
- Year
- Title
- Journal name (full name)
- Volume, Issue, Pages
- DOI (from ArticleId list, type="doi")

**APA format**:
```
[N] LastName, F. M., LastName, F. M., & LastName, F. M. (Year). Article title. Full Journal Name, Volume(Issue), start–end. https://doi.org/xxxxx
```

---

## Search Strategy by Grant Section

### For Section I paragraphs 2-4 (literature review):

| Paragraph focus | Suggested query strategy |
|----------------|--------------------------|
| Disease burden/epidemiology | `{disease} epidemiology incidence mortality` |
| Key molecule in disease | `{molecule} {disease} expression prognosis` |
| Pathway/mechanism | `{pathway} {disease} mechanism` |
| Therapeutic relevance | `{molecule} {disease} therapy target` |

### For Section I paragraph 5 (preliminary data support):

Search for papers that validate the type of preliminary work described:
- Expression profiling: `{molecule} {disease} expression clinical samples`
- Bioinformatics: `{molecule} TCGA bioinformatics {disease}`

---

## Error Handling

- If a search returns 0 results: broaden the query (remove one term, use MeSH terms)
- If API is unavailable: note this explicitly and use placeholder `[Reference pending - PubMed search required]`
- Never fabricate author names, journal names, years, or DOIs
- If uncertain about a detail, omit it rather than guess

---

## Example API Call

Search for "EGFR lung cancer prognosis":
```
GET https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=EGFR%5BTitle%2FAbstract%5D+AND+lung+cancer%5BTitle%2FAbstract%5D+AND+prognosis%5BTitle%2FAbstract%5D&retmax=5&sort=relevance&retmode=json
```

Then fetch summaries for returned PMIDs:
```
GET https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id=12345678,23456789&retmode=json
```
