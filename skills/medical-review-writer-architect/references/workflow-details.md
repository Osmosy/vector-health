# Workflow Detailed Description

This document provides detailed descriptions and best practices for the six-step workflow of MedicalReviewSkill.

## Phase 1: Outline Construction (Outline)

### Objective
Create a clear, structured review outline to lay the foundation for subsequent work.

### Detailed Steps

1. **Analyze the topic**
   - Understand the research topic provided by the user
   - Identify key research questions
   - Determine the scope and boundaries of the review

2. **Create the outline.md file**
   - Use markdown format
   - Ensure clear hierarchical structure

3. **Outline content requirements**

   **Title**:
   - Clearly express the review topic
   - Include keywords for searchability
   - Moderate length (recommended 15-25 characters)

   **Introduction**:
   - Research background: Why is this topic important?
   - Current status analysis: What stage has the research reached?
   - Problem statement: What knowledge gaps or controversies exist?

   **Body Sections**:
   - Plan 3-5 major sections (second-level headings `##`).
   - **Mandatory requirement**: The outline design **must go to the sub-heading level** (third-level headings `###`). Each section must include 2-4 specific sub-headings that show how the section will be logically decomposed. It is strictly forbidden to stay at the coarse level of only section headings.
   - Ensure logical flow: from basic to applied, from problem to solution.

   **Conclusion**:
   - Pre-set the direction and key points of the conclusion
   - Consider future research directions

### Best Practices
- Confirm the outline with the user before proceeding to the next step
- The outline should be flexible and adjustable based on literature in later stages
- Ensure clear logical relationships between sections

---

## Phase 2: Data Retrieval & Database Construction (Retrieval & Database)

### Objective
Collect sufficient, high-quality literature evidence for each section.

### Detailed Steps

1. **Generate search terms**
   - For each major section in outline.md
   - **Special reminder**: Search terms must be specifically designed for the **Introduction** (such as disease epidemiology, pathogenesis reviews, etc.)
   - Use a combination of MeSH terms and free-text words
   - Consider synonyms and related concepts

2. **Execute search and automatic database entry**

   **Command format**:
   ```bash
   python scripts/pubmed_search.py "YOUR QUERY" --section "SectionName"
   ```

   **Parameter description**:
   - `YOUR QUERY`: PubMed search expression
   - `--section`: Section name (**strictly follow the filename convention**)
     - Must use: `introduction`, `section_1`, `section_2`, `section_3`...
     - **Prohibited**: `Section1_History`, `Intro`, `part1` or other custom names
     - Reason: The subsequent `read_references.py` needs to automatically match citations by filename
   - `--max`: Maximum number of results (optional, default 20)
   - `--file`: Output file path (optional, default `references.json`)

   **Important reminders**:
   - `references.json` should be saved in the **project directory** (e.g., `TP53/references.json`), not the skill directory
   - If running the script from the skill directory, use `--file ../ProjectName/references.json` to specify the correct path
   - This ensures each project's literature database is independently managed

   **Examples**:
   ```bash
   python scripts/pubmed_search.py "diabetes mellitus[MeSH] AND complications" --section "introduction" --max 20
   python scripts/pubmed_search.py "metformin mechanism" --section "section_1" --max 20
   ```

3. **Iterative cycling and quantity check**
   - **Check command**: `python scripts/count_references.py`
   - **Quantity requirement**: Total deduplicated PMID count must be **> 150 articles**
   - **Recommendations**:
     - If the count is insufficient, use broader keywords or synonyms to search again
     - Increase the `--max` parameter (e.g., set to 20 or 50) to get more results
   - The script automatically appends new results without adding duplicate PMIDs

4. **Search strategy recommendations**
   - Introduction: Review articles, epidemiological data
   - Methods/Mechanisms: Mechanism studies, experimental research
   - Clinical sections: Clinical trials, meta-analyses
   - Future directions: Latest research, reviews

### Notes
- The goal is to build a large literature database (>200 articles) so there is ample choice during writing
- Prioritize high-quality literature from the past 5 years
- Include some classic foundational literature

---

## Phase 3: Chapter-by-Chapter Drafting (Drafting)

### Objective
Based on literature evidence, write detailed content for each section while ensuring citation diversity.

### Detailed Steps

1. **Read section-specific literature**


   **Command example**:
   ```bash
   python scripts/read_references.py "Introduction"
   ```

   This script filters all literature tagged as "Introduction" from references.json and displays:
   - PMID
   - Title
   - Abstract
   - Year
   - Search expression (for traceability)

2. **Write section content**

   **File naming convention**:
   - `introduction.md` - Corresponds to the Introduction section in the outline
   - `section_1.md` - Corresponds to the first major section in the outline
   - `section_2.md` - Corresponds to the second major section in the outline
   - And so on

   **Writing requirements**:
   - Every viewpoint needs literature support
   - Use `[PMID: 123456]` format to annotate citations
   - Maintain objective, rigorous academic language
   - Use tables and diagrams as appropriate to explain complex concepts
   - **Important**: Use complete paragraphs, avoid simple bullet-point lists
     - Incorrect example: "1. **Mutation heterogeneity**: Over 1000 different TP53 mutations..."
     - Correct example: "The primary challenge is the high heterogeneity of TP53 mutations. Over 1000 different TP53 mutations..."
     - Refer to the complete paragraph writing style in `assets/Review_Final.md`

   **Format and structure requirements** (**commonly violated points**):
   - Section main heading: second-level heading `## 1. Section Name`
   - Sub-heading: third-level heading `### 1.1 Sub-heading Name`
   - **Mandatory requirement**: **It is strictly forbidden to write an entire Section as a single super-long paragraph**. Each main section (`##`) must consist of 2-4 sub-headings (`###`) with logically differentiated content.
   - **Citation density requirement**: **The maximum number of citations per single sentence must not exceed 2** (i.e., at most `[PMID: 111] [PMID: 222]`). If multiple articles have similar conclusions, split them into progressive independent clauses described at different levels — never stack references at the end of a sentence without substance.
   - Refer to `assets/Review_Final.md`: Observe how its sub-headings decompose a large topic into structured discussion.
   
3. **Search-While-Writing**
   - **Scenario**: During writing, you discover that a specific point lacks literature support, or existing literature is too outdated.
   - **Action**: Do not stop — immediately conduct a micro-search.
   - **Command**:
     ```bash
     python scripts/pubmed_search.py "specific mechanism or recent data" --section "section_1"
     ```
   - **Integration**: Newly retrieved literature is automatically added to `references.json`; run `read_references.py "section_1"` again to view.

4. **Post-Writing Check and Literature Supplementation**
   - After completing a chapter, run the validation script to check objective metrics:
     ```bash
     python scripts/check_section.py "section_1.md"
     ```
   - Focus on the state machine output's **reference count** and **next step suggestions**.
   - If the number of cited PMIDs is too low (e.g., <10), execute a supplementary search with the `--post-write` parameter:
     ```bash
     python scripts/pubmed_search.py "Your Query" --section "section_1" --post-write
     ```
   - Based on the status prompts after supplementary search, read new literature and add to the section.

5. **Manual quality check**
   - Does each paragraph have sufficient literature support?
   - Is the logic coherent?
   - Does it answer the questions set in the outline?

### Writing Tips
- Write the main content first, then supplement with details
- Keep paragraph length moderate (3-5 sentences)
- Use transitional sentences to connect paragraphs

---

## Phase 4: Conclusion Writing (Conclusion)

### Objective
Summarize the core findings of the entire article, echo the introduction, and look to the future.

### Detailed Steps

1. **Review completed sections**
   - Quickly browse all section_*.md files
   - Extract key findings from each section
   - Identify themes running throughout the article

2. **Write conclusion.md**

   **Suggested content structure**:
   - **Summarize core findings**: Concisely summarize the main conclusions
   - **Echo introduction questions**: Answer the questions raised in the Introduction
   - **Identify research limitations**: Honestly point out deficiencies in current research
   - **Future research directions**: Propose valuable research suggestions
   - **Important rule**: The conclusion section **should not include references** — this is a common convention in review writing

   **Format requirements**:
   - Main heading: second-level heading `## Conclusion`
   - Sub-headings: third-level headings `### Summarize Core Findings` etc.
   - Refer to the conclusion section of `assets/Review_Final.md`

### Writing Principles
- Avoid introducing new content or literature
- Maintain echo with the introduction
- The conclusion should be concise and powerful

---

## Phase 5: Abstract & Final Assembly (Abstract & Final Assembly)

### Objective
Write the abstract, merge all parts, and generate the complete review document.

### Detailed Steps

1. **Write abstract.md**

   **Content requirements**:
   - Research background (1-2 sentences)
   - Main content overview (3-4 sentences)
   - Core findings (2-3 sentences)
   - Conclusion and outlook (1-2 sentences)
   - **Do not include citations**: The abstract is typically a standalone text that should not depend on references
   - Keywords: 5-7 terms, separated by Chinese semicolons ";"

   **Format requirements**:
   - First line: Complete title (first-level heading `#`)
   - Second heading: "Abstract" (second-level heading `##`)
   - Third heading: "Keywords" (third-level heading `###`)
   - Refer to the beginning of `assets/Review_Final.md`

   **Common errors**:
   - **Forgetting to add the review title**: The first line of `abstract.md` must be the complete review title (first-level heading)
   - **Wrong keyword separator**: Must use Chinese semicolons (;) not English semicolons (;)

2. **Merge and finalize**

   **Command example**:
   ```bash
   python scripts/merge_review.py abstract.md introduction.md section_1.md section_2.md section_3.md conclusion.md -o Review_Final.md
   ```

   **Notes**:
   - List all files in the correct order
   - **Do not include `outline.md`**: The outline is only for planning and should not appear in the final document
   - Output file is uniformly named Review_Final.md

3. **Format verification**
   - Open Review_Final.md and assets/Review_Final.md
   - Verify that the heading hierarchy structure is consistent
   - Check that the overall format conforms to the template standards

---

## Phase 6: Format Citations (Format Citations)

### Objective
Convert PMID citations to standard format and generate the reference list.

### Detailed Steps

1. **Run the formatting script**

   **Command example**:
   ```bash
   python scripts/format_citations.py Review_Final.md -o Review_Final_Formatted.md
   ```

   **Script functions**:
   - Replaces `[PMID: 123456]` with `[[n]](https://pubmed.ncbi.nlm.nih.gov/123456/)`
   - Automatically numbers citations
   - Calls PubMed API to get complete citation information
   - Generates an APA-format reference list at the end of the document

2. **Verify output**
   - Check that all citation links are correct
   - Confirm the reference list is complete
   - Verify numbering sequence

3. **Content Revision and Citation Revert (Revising Content)**
   - **Scenario**: If you discover the formatted final version (with `[[1]](link)` style) needs major revision or supplementation.
   - **Mandatory requirement**: **Never directly modify the final version with links** — this will cause citation numbering chaos.
   - **Step 1 (Revert)**: Run the revert script to convert the formatted citation format back to the original `[PMID: xxx]` form and automatically remove the reference list at the end.
     ```bash
     python scripts/revert_citations.py "Review_Final_Formatted.md" -o "Review_Final_Draft.md"
     ```
   - **Step 2 (Modify)**: Make all content deletions or additions on the newly generated `Review_Final_Draft.md`. You can use `pubmed_search.py` at any time to supplement new literature, continuing to follow the `[PMID: xxx]` original annotation format.
   - **Step 3 (Re-format)**: After all modifications are complete, run the formatting script again to generate a new final version.
     ```bash
     python scripts/format_citations.py "Review_Final_Draft.md" -o "Review_Final_Formatted_v2.md"
     ```

### Notes
- Network connection must be stable (calls PubMed API)
- Processing time depends on the number of citations
- If certain PMIDs cannot be retrieved, there will be warning messages

---

## FAQ and Solutions

### Q1: What if the retrieved literature is not relevant enough?
A: Optimize search terms, use more precise MeSH terms, or adjust the search strategy.

### Q2: How to handle duplicate PMIDs?
A: The script automatically detects and skips duplicate PMIDs within the same section.

### Q3: What if the file order is wrong during merging?
A: Re-run merge_review.py, specifying files in the correct order.

### Q4: Errors during citation formatting?
A: Check the network connection, confirm all PMIDs are in the correct format.

### Q5: Where should references.json be placed?
A: **It must be placed in the project directory** (e.g., `TP53/references.json`), not the skill directory. If running the script from the skill directory, use `--file ../ProjectName/references.json` to specify the correct path.

### Q6: What if abstract.md is missing the title?
A: The first line of `abstract.md` must be the complete review title (first-level heading `#`), followed by the `## Abstract` section. Refer to the format of `assets/Review_Final.md`.