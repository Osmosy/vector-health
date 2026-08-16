# Style Profile Extraction

When the user provides example text rather than an abstract style description, first extract an actionable style profile from the example, then use it to guide the rewriting.

## Objective

Do not deconstruct the example article into a writing structure blueprint, and do not output lengthy commentary. Only distill style characteristics that will directly influence the rewrite.

## Extraction Dimensions

Cover at least the following dimensions:

- Tone intensity: restrained, calm, assertive, sharp, provocative, persuasive
- Formality level: colloquial, semi-written, formal written, academic
- Sentence patterns: dense short sentences, elaborate long sentences, alternating long and short, parallelism, rhetorical questions, counter-questions
- Pacing: slow unfolding, continuous pushing, layered progression, abrupt switching
- Word choice tendencies: abstract/concrete, plain/ornate, editorial/expository
- Rhetorical preferences: metaphor, contrast, quotation, repetition, parallelism, leaving space
- Narrative perspective: I/we/third person/detached commentary
- Emotional display: low, moderate, high
- Paragraph habits: short paragraphs, long paragraphs, judgment-first-then-elaboration, narrative-first-then-evaluation

## Extraction Method

1. Focus on stable characteristics, not isolated sentences.
2. Write the style profile in 5 to 8 short sentences.
3. Distinguish "style" from "content."
   For example, a specific metaphor, opinion, or case study usually belongs to content and should not be directly transferred.
4. If the example's style is mixed, identify the primary style and secondary style, and retain only the primary style during rewriting.

## Output Format

Internally, use a list or brief field-based summary; no need to output JSON.

Example:

- Restrained tone, not sentimental, but with clear judgment.
- Alternating long and short sentences, frequently using short sentences to close paragraph meaning.
- Written-leaning word choice, few colloquialisms, few exclamations.
- Low rhetorical density, primarily relying on contrast and progression for force.
- Often leads with conclusion, then supplements with explanation.

After extraction is complete, proceed immediately to rewriting — do not linger in the analysis phase.
