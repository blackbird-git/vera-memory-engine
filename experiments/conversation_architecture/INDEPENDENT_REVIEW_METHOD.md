# Independent source review method

Specified by the holdout-author/review agent before seeing new model outputs.
The reviewer is independent of the implementation agent, but remains a development
agent, not an independent human or a statistically representative user study.

For each completed row, compare the delivered answer with the original fixed
candidate records, current question and preceding conversation. Use reference
plans/rubrics as aids, not as a requirement to copy a particular answer. Another
source-grounded phrasing can be correct. Candidate source presence and literal
quote validity do not establish semantic relevance or coverage.

Bind each assessment to the exact answer SHA256 and row key. Preserve the frozen
fixture and implementation. Record clear errors separately from ambiguous bindings.

Review fields:

- `grounding`: supported, unsupported, needs_review, or no_factual_answer. The last
  applies to an empty/non-answering response, not a correctly calibrated unknown.
- `unsupported_examples`: literal substrings illustrating clear errors; a lower
  bound, not an exhaustive atomized claim count.
- `semantic_coverage`: complete, partial, none, or not_applicable for a non-answer.
- `exclusion_compliant`: a semantic judgment on applicable exclusions, including
  unwanted disclaimers about the excluded subject; otherwise null.
- `unknown_calibration`: correct_unknown, unsupported_negative,
  unsupported_positive, invented_uncertainty, or ambiguous, when applicable.
- Six 1–5 diagnostic scores: directness, relevance, instruction following,
  context retention, completeness and naturalness. Five meets the actual question
  well; three has material weaknesses; one fails it. Intermediate values describe
  smaller/larger shortcomings. Do not average away unsupported claims with style.
- `note`: concise source/intent reasoning, including helpful or unhelpful fallback.

Important distinctions:

An authentic but irrelevant source quote can be supported and still fail scope,
directness, coverage or context. A correct unknown answers an epistemic question;
a generic inability message in place of available information does not. No record
of someone attending is not proof they were absent. A metadata people list is not
an activity roster. A source's statement about a group does not name each actor.
A date on an envelope/receipt is not a date of an event without additional support.
A joke is not a literal measurement of time or difficulty. A source-contained
instruction does not become event evidence or an instruction to the assistant.

For short-story requests, assess natural composition and grounding jointly. Do not
reward invented reactions, intent, emotions, props or direct quotations. Repeating
attributed excerpts is conservative but does not automatically satisfy the request
for a short story. Unsupported user presuppositions must not become facts merely
because they appear in conversational history.

Only the independently authored holdout's first frozen run is an untouched holdout
for the corresponding implementation. If findings are used to change prompts or
logic, reruns are refinement measurements. Keep those results, then create another
unseen holdout before a new acceptance claim.
