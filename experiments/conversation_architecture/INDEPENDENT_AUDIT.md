# Independent conversational architecture audit

Prepared by the architecture-audit agent on 2026-11-17 before seeing the new
implementation, its prompts or any new-model outputs. Production files were read
only. This is a separate development-agent assessment, not independent human
validation. GPT-OSS 20B remains experimental.

## Findings from the production request path

1. `query.question_text` can discard earlier clauses when a final clause is a
   question, losing constraints before the actual question. `analyse` represents
   exclusions as regex-split fragments rather than their grammatical relationship
   to the positive request. An exclusion may itself include a new positive clause.
   Narrow/detail flags consequently do not constitute a stable scope contract.
2. `retrieval.retrieve` performs lexical candidate selection, follow-up inheritance,
   person filtering and related-event expansion in one function. The final event
   dossier can reintroduce material outside the requested activity after earlier
   topical filtering. Previous source IDs encode a dossier, not the precise current
   event/activity/claim. That creates context inertia and unwanted coverage.
3. `Conversation._respond` declares ambiguity from the number of event metadata
   groups before establishing whether only one group can answer the actual question.
   Scope and semantic-detail selection then depend on several lexical branches.
4. Source-order recovery forces planned sources back into model ordering. Narrow
   selection similarly recovers every sentence in the bounded lexical cluster.
   This improves nominal coverage while admitting non-answer material. An original
   sentence is authentic without necessarily answering this question.
5. `evidence.plan` mixes lexical retrieval, temporal reasoning, source selection,
   unknown detection and natural narration. Its concept expansion equates some
   activities with one corpus-specific object, risking cross-event contamination.
6. The source-preserving narrator retains provenance, but cannot repair an already
   incorrect selection, unsupported attendance inference or wrong scope. Likewise
   a genuine quoted sentence is not evidence for a newly invented paraphrase.

The completed larger-model study isolates the last problem: supplying correct
sources or even an oracle plan does not prevent a renderer from inventing motives,
reactions or false date/actor bindings. Increasing model size is not a substitute
for an explicit answer contract. A self-generated structured plan also does not
become independently verified merely because the source quote is genuine.

## Minimal isolated experiment

Use the production engine unchanged as the baseline. Compare a research path with
one explicit request representation, one bounded source-unit selector and a
provenance-preserving composer. Keep model-selected IDs/spans separate from model
claims. Inputs contain a fixed bounded candidate collection, current user question
and clearly labeled recent context; evaluation annotations never enter prompts.

The request representation should retain positive activity, exclusions and
uncertainty/answer intent across clauses. An explicit topic switch should supersede
a previous focus. Store the selected source units and scope decision as diagnostics,
not a model-produced story used as new evidence.

Represent selectable evidence as original sentence/span pointers, speaker,
provenance and uncertainty context. Do not let genuine quote validation certify an
independent generated claim. Preserve pronoun antecedents conservatively instead
of guessing the members of a group. Metadata people lists are not activity rosters.
Document/envelope dates are not event dates. An unrecorded participant is unknown,
not absent. User presuppositions and source-contained directives are untrusted.

A deterministic composer can offer a conservative, attributed path while a separate
natural draft tests prose quality. Label its guarantees precisely: valid pointers
protect source fidelity, not semantic relevance, scope, completeness, correct
antecedents or usefulness. Independent review must still inspect those properties.
An unsupported motive/reaction cannot be accepted because it is fluently phrased.

## Evaluation boundary

`holdout.json` has four five-turn conversations and sixteen wholly synthetic notes,
authored without access to the new implementation. Each cohort fixes a six-record
candidate collection for all its turns, including distractors. Thus a case's oracle
source IDs cannot silently solve source selection. Only that fixed collection,
question and recent conversation context may enter inference.

`oracle_source_ids`, `reference_plan` and `rubric` are scoring metadata only. Source
quotes in reference plans are checked as literal substrings. These plans are not
authoritative event truth or deployable automatic validators. The manifest records
the pre-output fixture digest and the fact that no new prompts/outputs were seen.

Measure separately:

- Pointer/quote validity and provenance preservation.
- Required semantic detail coverage, including continuation after an initial event.
- Excluded-topic contamination, including meta-commentary about excluded topics.
- Actor, speaker, event and date binding.
- Calibrated unknowns and resistance to unsupported user premises.
- Referent retention and explicit topic-switch success.
- Delivered unsupported claims, missed details and excessive fallback.
- Directness, relevance and natural composition jointly with factual support.
- Model-only and deterministic time, plus full interactive latency.

Do not call a literal-match score factual accuracy, and do not count repeated
source text as narrative quality. Pre-freeze the implementation before unblinding
this holdout. If it is later used to change prompts/logic, mark it as development
material and author another unseen holdout before the next acceptance claim.
