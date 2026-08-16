# Citation Format Guide

This document details the citation format standards and best practices used in MedicalReviewSkill.

## Citation Format Overview

MedicalReviewSkill uses a two-stage citation system:

1. **Drafting stage**: Uses simplified `[PMID: xxx]` format
2. **Finalization stage**: Automatically converts to standard numbered format with complete reference list

## Drafting Stage Citation Format

### Basic Format

```markdown
Sentence content [PMID: 123456].
```

### Multiple Citations

**Method 1: Consecutive citations**
```markdown
Sentence content [PMID: 123456, PMID: 234567].
```

**Method 2: Separate citations**
```markdown
Sentence content [PMID: 123456][PMID: 234567].
```

### Citation Placement

**Recommended practices**:
- Place citations at the end of the sentence, before the period
- One point corresponds to one or more citations
- Keep citations closely associated with the content they support

```markdown
Correct example:
Diabetes is a common metabolic disease [PMID: 123456].

Incorrect example:
[PMID: 123456] Diabetes is a common metabolic disease.
```

## Finalization Stage Citation Format

After processing with `format_citations.py`, citations are converted to:

### Inline Citation Format

```markdown
Sentence content [[1]](https://pubmed.ncbi.nlm.nih.gov/123456/).
```

- `[[1]]`: Citation number
- Hyperlink points to PubMed original article

### Reference List

An APA-format reference list is automatically generated at the end of the document:

```markdown
## References

1. Author A, Author B, Author C. Title of the article. *Journal Name*. 2023;10(2):123-145. doi:10.1234/journal.2023.123456
2. Author D, Author E. Another article title. *Another Journal*. 2022;15(3):234-256. PMID: 234567
```

## Citation Management Best Practices

### 1. When to Cite

**Situations requiring citation**:
- Presenting specific data or statistical results
- Referencing others' research findings
- Describing specific research methods
- Mentioning controversial viewpoints
- Citing authoritative definitions or classifications

**Situations not requiring citation**:
- Universally accepted common knowledge
- Your own summaries and analyses
- Logical reasoning and discussion

### 2. Citation Quantity

**Recommendations**:
- Introduction: One citation every 2-3 sentences
- Methods/Mechanisms: Every key point needs citation
- Results/Clinical Evidence: Heavy citations, nearly every sentence needs one
- Discussion/Conclusion: Moderate citations, mainly citing key findings

### 3. Citation Quality

**Priority** (from highest to lowest):
1. Systematic reviews and meta-analyses
2. Randomized controlled trials (RCTs)
3. Cohort studies
4. Case-control studies
5. Case reports
6. Expert opinions

**Timeliness**:
- Prioritize literature from the past 5 years
- Classic foundational literature is not time-limited
- Latest developments should cite literature from 1-2 years

### 4. Citation Balance and Frequency

**Citation frequency limits** (important):
- **Principle**: Cite different references as much as possible to demonstrate research breadth.
- **Limit**: A single article should be cited **no more than 2 times**.
- **Upper bound**: Absolutely no more than 3 times. If a particular article is very important and needs to be cited multiple times, try to find other articles supporting the same viewpoint to replace some citations.

**Avoid**:
- Over-citing research from a single team
- Ignoring contrary evidence
- Only citing supportive literature

Recommendations:
- Balance literature from different viewpoints
- Include positive and negative results
- Cite work from different research teams

## format_citations.py Script Usage

### Basic Usage

```bash
python scripts/format_citations.py Review_Final.md -o Review_Final_Formatted.md
```

### Parameter Description

- First argument: Input file (required)
- `-o` or `--output`: Output file (optional, defaults to `input_filename_Formatted.md`)

### Script Workflow

1. **Scan document**: Identify all `[PMID: xxx]` format citations
2. **Deduplicate and number**: Assign a number to each unique PMID
3. **API query**: Call PubMed API to get complete citation information
4. **Replace citations**: Replace simplified format with numbered+link format
5. **Generate list**: Add complete reference list at the end of the document

### Processing Time

- Depends on citation count and network speed
- Each PMID takes approximately 0.5-1 second (API rate limit)
- 100 citations take approximately 1-2 minutes

### Error Handling

**Common errors**:

1. **PMID format error**
   ```
   Warning: Invalid PMID format: [PMID: abc123]
   ```
   Solution: Check that PMID is entirely numeric

2. **Network connection issue**
   ```
   Error: Failed to fetch PMID 123456
   ```
   Solution: Check network connection, retry later

3. **PMID does not exist**
   ```
   Warning: PMID 999999 not found in PubMed
   ```
   Solution: Verify that the PMID is correct

## Citation Format Examples

### Example 1: Single Citation

**Drafting stage**:
```markdown
The global prevalence of diabetes continues to rise, becoming an important public health issue [PMID: 12345678].
```

**Finalization stage**:
```markdown
The global prevalence of diabetes continues to rise, becoming an important public health issue [[1]](https://pubmed.ncbi.nlm.nih.gov/12345678/).
```

### Example 2: Multiple Citations

**Drafting stage**:
```markdown
Multiple studies have shown that lifestyle interventions can effectively prevent diabetes [PMID: 12345678, PMID: 23456789, PMID: 34567890].
```

**Finalization stage**:
```markdown
Multiple studies have shown that lifestyle interventions can effectively prevent diabetes [[1]](https://pubmed.ncbi.nlm.nih.gov/12345678/),[[2]](https://pubmed.ncbi.nlm.nih.gov/23456789/),[[3]](https://pubmed.ncbi.nlm.nih.gov/34567890/).
```

### Example 3: Same Article Cited Multiple Times

**Drafting stage**:
```markdown
Smith et al.'s study [PMID: 12345678] showed... Subsequent analysis further confirmed this finding [PMID: 12345678].
```

**Finalization stage**:
```markdown
Smith et al.'s study [[1]](https://pubmed.ncbi.nlm.nih.gov/12345678/) showed... Subsequent analysis further confirmed this finding [[1]](https://pubmed.ncbi.nlm.nih.gov/12345678/).
```

## APA Format Standards

### Journal Article

```
Author, A. A., Author, B. B., & Author, C. C. (Year). Title of article. *Title of Periodical*, volume(issue), pages. https://doi.org/xx.xxxx/xxxxx
```

### Online Article (No DOI)

```
Author, A. A. (Year). Title of article. *Title of Periodical*, volume(issue), pages. PMID: xxxxxxxx
```

### Book Chapter

```
Author, A. A. (Year). Title of chapter. In B. B. Editor (Ed.), *Title of book* (pp. xxx-xxx). Publisher.
```

## Quality Check Checklist

After writing is complete, check the following items:

- [ ] All key points have citation support
- [ ] PMID format is correct (all numeric)
- [ ] No duplicate or redundant citations
- [ ] Citation placement is appropriate (typically at end of sentence)
- [ ] Citation sources are diverse
- [ ] Includes recent literature (past 5 years)
- [ ] Includes high-quality evidence (meta-analyses, RCTs, etc.)

## FAQ

### Q: How to cite different parts of the same article?
A: Use the same PMID. After formatting, they will automatically be merged into the same number.

### Q: Can I manually add references?
A: Not recommended. All citations should be marked with PMIDs and the reference list generated automatically by the script.

### Q: Will too many citations affect readability?
A: Moderate citations are sufficient. Generally 2-4 citations per paragraph is adequate.

### Q: How to handle PMIDs that cannot be retrieved?
A: Check if the PMID is correct, or replace with another relevant article's PMID.

### Q: Can I modify after formatting?
A: Yes, but be careful not to break the continuity of citation numbering. It is recommended to complete all modifications before formatting.
