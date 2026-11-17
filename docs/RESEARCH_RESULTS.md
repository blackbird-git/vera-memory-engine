# What I learned from the experiments

These are results from completed experiments, not new measurements from preparing this repository. The published artifacts are sanitized copies of the original research evidence.

## Model comparison with known evidence

I wanted to separate a model's ability to answer a question from the retrieval engine's ability to find the right source. The oracle experiments bypassed normal routing and retrieval so I could compare direct answers, model-generated evidence plans and supplied reference plans.

GPT-OSS 20B was the most promising practical experimental candidate, but the results did not justify replacing the CLI model.

| GPT-OSS 20B approach (bounded cache) | Supported | Unsupported | Ambiguous | Median / p95 seconds |
|---|---:|---:|---:|---:|
| Direct answer | 9 | 4 | 3 | 2.94 / 4.16 |
| Supplied reference plan | 13 | 2 | 1 | 3.42 / 4.37 |
| Model-generated plan | 12 | 3 | 1 | 7.99 / 16.35 |

Each arm contains 16 answers. The supplied plan gives the renderer an upstream advantage that is not available in ordinary use. It does not establish that the application can automatically verify semantic claims.

Stock Qwen3.5 27B completed four direct answers and then encountered two 300-second timeouts under memory pressure. A bounded-cache stock run was stopped by the memory guard. I also tested a text-only profile that retained the language weights but omitted the vision projector. All 48 responses completed; the direct/generated-plan/reference-plan arms had supported/unsupported/ambiguous counts of 10/3/3, 12/2/2 and 12/2/2. I found no clear conversational advantage.

The different cache and runtime conditions are not interchangeable timing samples. Reused reviews are labeled in the [oracle evidence](../evidence/oracle/).

## Conversation architecture

The first experiment compared three approaches over 20 questions and returned 60 answers. The baseline answered 13 completely and the planner 15. The planner reduced explicit exclusion failures from 1/7 to 0/7, but added eight unnecessary uncertainty disclaimers. Natural drafts had 12 unsupported, seven supported and one ambiguous answer.

I revised the experimental context handling and ran a different, fresh 16-question set:

| Approach | Supported / unsupported / nonanswer | Complete | Exclusion failures | Scope contamination |
|---|---:|---:|---:|---:|
| Baseline | 15 / 0 / 1 | 10/16 | 1/5 | 8/16 |
| Source/context planner | 14 / 0 / 2 | 9/16 | 0/5 | 3/16 |
| Natural draft | 8 / 8 / 0 | 9/16 | 1/5 | 1/16 |

All 48 responses completed without runtime errors. The revised planner reduced unwanted source material relative to the baseline in the same round, but it did not improve completeness. The two rounds used different questions, so their results are not a paired before/after comparison.

A separate eight-case boundary test improved critical-span integrity from 3/8 to 8/8. Only five answers fully covered the expected meaning. Two were incomplete unknowns, and one asked an unnecessary clarification. None of the predeclared forbidden assertions appeared, but that is not a universal hallucination guarantee.

Revision-2 median/p95 total times were 2.970/11.032 seconds for the baseline, 6.381/12.176 for the planner, and 10.167/14.673 for the natural draft including planning. These small, correlated samples are not production latency targets.

## Remaining problems

- Lexical retrieval and abbreviation splitting can lose context or broader qualifiers.
- The engine can miss important story details, actor identities and date distinctions, or ask for clarification unnecessarily.
- Conservative attributed excerpts can be awkward; more natural drafts can invent intent, reactions, chronology or identities.
- A model critic may approve unsupported claims. Valid JSON, literal quotes and expected-term coverage are not substitutes for checking meaning.

I have not approved a change to the ordinary CLI architecture or Qwen default. The results justify continuing the research, not claiming that the problem is solved.

The evaluations use fixed synthetic cohorts and development-agent reviews, not independent human studies or representative user samples. Grounding labels apply to whole answers, not individual claims. See [conversation evidence](../evidence/conversation/) and [reproduction notes](REPRODUCIBILITY.md).
