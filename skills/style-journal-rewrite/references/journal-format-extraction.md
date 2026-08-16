# Journal Format Extraction

When the user provides the target journal's submission guidelines, author instructions, or published articles, first extract "actionable explicit format requirements," then use them to guide the rewriting of the draft.

## Objective

Extract rules that can directly influence the rewriting result. Do not produce vague summaries. Do not fabricate journal standards that were not provided.

## Priority Extraction Items

Scan and record in the following priority order:

- Article components and their order
  Example: title, abstract, keywords, introduction, methods, results, discussion, conclusion, acknowledgments, references.
- Abstract requirements
  Example: single-paragraph abstract or structured abstract, whether it must be divided into `Objective/Methods/Results/Conclusion`, word or character count limits.
- Keyword requirements
  Example: quantity range, whether specific formatting rules apply.
- Body structure
  Example: whether first- and second-level headings are numbered, whether IMRaD structure is required, whether section names are fixed.
- References
  Example: whether in-text citations use numeric superscripts, bracketed numbers, or author-year format; reference list entry order, author formatting rules, journal abbreviation style; numbering format is `[1]`, `1.`, or `¹`; whether DOI/PubMed links are included.
- Other explicit formatting
  Example: figure/table caption placement, unit of measurement notation, abbreviation first-use rules, acknowledgment or funding statement placement.

## Evidence Priority

Determine rule strength according to the following priority:

1. Rules explicitly stated in submission guidelines
2. Rules that appear consistently across multiple sample articles
3. Local patterns in a single sample article — can only be treated as weak hints

If a rule is supported only by a single sample article, do not characterize it as "mandatory." It can only be treated as a style to "preferably follow."

## Output Format

Internally organize into a minimal format profile that includes at least:

- Explicit rules that must be satisfied
- Weak rules that can be preferably followed
- Aspects that cannot be confirmed

Example:

- Mandatory: abstract is 1 paragraph, limited to 300 words; 3 to 5 keywords; references use bracketed numbering.
- Mandatory: body uses `Introduction/Methods/Results/Discussion` four-section structure.
- Weak rule: sample articles mostly use third-level headings, numbering not enforced.
- Unconfirmed: figure caption placement, funding statement template.

## Implementation Principles

1. Change what can be changed directly first.
   For example: abstract paragraph count, section order, keyword count, reference display format.
2. Do not fabricate when additional information is needed.
   For example: author affiliations, ethics approval, funding numbers.
3. When format requirements conflict with the original draft's information, prioritize preserving facts, then approximate the journal format as closely as possible.
4. If reference source information is insufficient for full format conversion, conservatively adjust available fields — do not fabricate missing fields.
