# Model comparison experiments

I compared local models and response strategies using fixed synthetic records and evaluation cases. The goal was to understand the tradeoff between factual support, relevance, conversational usefulness and resource requirements rather than pick a model based on a single score.

The code here is separate from the ordinary CLI. Model adapters, candidate records, prompts and evaluation cases are retained for reproducibility. Published summaries are in [the evidence directory](../../evidence/model_comparison/); raw inference logs are excluded.

See [research findings](../../docs/RESEARCH_RESULTS.md), [runtime requirements](../../docs/RUNTIME_REQUIREMENTS.md) and [reproduction instructions](../../docs/REPRODUCIBILITY.md). The current experiment runner is host-specific, and previously used cases should not be treated as unseen holdouts.
