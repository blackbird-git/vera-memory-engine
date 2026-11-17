# Interpreting the source reviews

These are development-agent reviews, unblinded to model identity. The case rubrics
and evidence were frozen before outputs. This explanatory guide was written during
analysis; it is not a preregistered independent evaluation protocol.

Review the delivered answer against the original source content, including which
person remembers which event. A source's mention of someone on a trip does not
establish that person's participation in each activity. A photograph's envelope or
handwritten label is not an independently established event date. An absent name
is not evidence of nonattendance. Attributed uncertainty must survive paraphrasing.
Do not accept additional reactions, motives, dialogue, props or relationships just
because they would be plausible. User history supplies referents, not facts.

Whole-answer grounding has three values:

- `supported`: no clear unsupported factual assertion or unresolved source binding
  was identified in that review. It does not certify universal factual correctness.
- `unsupported`: at least one clear unsupported assertion, false denial, attribution
  error or unjustified certainty was identified. Quoted examples are literal answer
  substrings and lower bounds; they are not exhaustive atomic-claim annotations.
- `needs_review`: a phrase has an ambiguous role, location, date or identity binding.
  Keep these separate from both supported answers and clear errors.

Diagnostic scores are 1–5, with 5 meeting the question well, 3 usable with substantial
weakness and 1 failing it. Intermediate values express smaller/larger shortcomings:

| Dimension | What the reviewer assesses |
|---|---|
| Directness | Answers the requested question immediately and usefully |
| Relevance | Includes appropriate detail without padding or unrelated sources |
| Instruction following | Respects topic exclusions, length, uncertainty and source-use rules |
| Context retention | Resolves the recent referent and switches topics when asked |
| Completeness | Supplies the important requested facts with correct attribution |
| Naturalness | Fluent, composed conversation or a short story when requested |

A fluent invented story may have good surface directness but still fails grounding.
A completely grounded answer may be incomplete or stilted. Do not collapse these
into a single overall score. Story quality must be evaluated jointly with support.
A renderer receiving a gold plan has easier upstream inputs than direct generation.

`exclusion_compliant` is a semantic source-review judgment on applicable turns;
merely avoiding an excluded keyword is insufficient. `unknown_calibration` separates
an appropriately unknown attendance answer, categorical denial and ambiguous
phrasing. High averages cannot compensate for unsafe categorical denials.

Each review includes the original answer SHA256. Reusing a review in another runtime
condition is permitted only when model, strategy, cohort, turn and answer bytes
match exactly; changed answers require a new review. Any reuse is documented in the
new review artifact. Review disagreements and ambiguity should be resolved by an
independent human before using this research for deployment.

The fixture is small: two eight-turn conversations, one seed per completed
condition. Context is limited to recent user questions, not full assistant history.
It does not cover arbitrary archives, adversarial documents, retrieval recall,
confirmation writes, long-session drift or a representative user population.
