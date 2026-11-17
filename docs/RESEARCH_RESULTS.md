# Saved findings and limitations

These are sanitized projections of previously completed private experiments, not
new tests or evaluations. Original artifacts remain private and unchanged.

## Model capability

Oracle-evidence experiments bypassed production routing/retrieval. GPT-OSS 20B was
the practical research lead, not an approved production model. In the bounded-cache
condition its direct arm had 9 supported / 4 unsupported / 3 ambiguous answers out
of 16 (median/p95 2.94/4.16 s). Gold-plan rendering had 13/2/1 (3.42/4.37 s), and
model-generated planning 12/3/1 (7.99/16.35 s). Gold plans are an upstream oracle
advantage, not a proven automatic verifier.

Stock Qwen3.5 27B completed four direct answers then hit two 300-second timeouts
under memory pressure; that partial run is not a full quality comparison. A cache-
bounded stock load was stopped by the memory guard. A separately labeled text-only
profile reused the exact language weights while omitting the vision projector;
all 48 answers completed. Its direct/plan/gold-plan cells had respectively
10/3/3, 12/2/2 and 12/2/2 supported/unsupported/ambiguous answers. It did not establish
material conversational superiority. See `evidence/oracle/` for existing aggregates
and final-answer/review projections. The default and bounded cache conditions are
not interchangeable latency samples; reused reviews are explicitly identified.

## Conversational architecture

Revision 1: 20 questions, three arms, 60 completed answers. The existing-engine
baseline had 13 complete answers; the source planner 15. Explicit exclusion failures
were 1/7 and 0/7 respectively, but the planner added eight unnecessary uncertainty
disclaimers. Natural drafts had 12 unsupported, seven supported and one ambiguous
answer. Quote fidelity was not semantic acceptance.

Revision 2: 16 fresh questions, three arms, 48 completed answers. No runtime errors:

| Arm | Supported / unsupported / nonanswer | Complete answers | Explicit exclusion failures | Scope contamination |
|---|---:|---:|---:|---:|
| Existing-engine research baseline | 15 / 0 / 1 | 10/16 | 1/5 | 8/16 |
| Source/context planner | 14 / 0 / 2 | 9/16 | 0/5 | 3/16 |
| Unreleased natural draft | 8 / 8 / 0 | 9/16 | 1/5 | 1/16 |

Grounding labels classify whole answers, not atomic claims. A supported irrelevant
or incomplete quotation can fail the user's request. The planner improved scope
relative to its same-round baseline, but did not improve complete coverage. Different
round cohorts prevent a paired causal before/after improvement claim.

A separate eight-case boundary challenge improved critical-span integrity from
3/8 with the original splitter to 8/8 with revision 2. Only five answers fully
covered expected meaning; two were generic/incomplete unknowns and one needlessly
asked for clarification. No predeclared forbidden assertions were observed. That
is not eight semantic passes or a universal zero-hallucination result.

Saved revision-2 median/p95 total seconds were 2.970/11.032 baseline, 6.381/12.176
source plan and 10.167/14.673 natural draft including planning. Inference timing and
deterministic processing are separate in the published summaries; small correlated
samples do not establish production service levels.

## Remaining limitations

- Model-selected context is not independently semantically certified. Abbreviation
  segmentation is heuristic and can merge material or lose broader qualification.
- Story setup/replacement details, unknown individual actors, decisive negative
  qualifiers and document/event date distinctions can still be missed.
- Precise questions can produce unnecessary clarification or incomplete unknowns.
- Conservative attributed excerpts are not consistently natural stories. Free
  drafts still invent intent, idea origin, chronology, identities or canonical dates.
- Earlier model critics sometimes approved unsupported drafts; literal quotes,
  expected-term coverage and critic approval are not sufficient factual checks.
- Fixed candidate sets, one-seed conditions and development-agent reviews do not
  validate arbitrary archives, long conversations or independent human quality.

No model or conversational architecture switch is approved by these findings.
The ordinary CLI retains its existing Qwen default and confirmation safeguards.
