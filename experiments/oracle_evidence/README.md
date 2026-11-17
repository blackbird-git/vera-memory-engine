# Oracle evidence experiments

To distinguish retrieval problems from generation problems, I tested what happens when a model receives known evidence or a supplied reference plan instead of relying on Vera's normal retrieval path.

A good answer under oracle conditions does not mean the application can select or verify that evidence automatically. I retained the comparison between direct generation, model-generated plans and supplied plans, including unsupported answers and resource-related failures.

Read the [source-review guide](REVIEW_GUIDE.md), [saved results](../../docs/RESEARCH_RESULTS.md) and [reproduction instructions](../../docs/REPRODUCIBILITY.md). The original guide is preserved as a historical development-agent record. Curated results are in [evidence](../../evidence/oracle/).

Live runners depend on the documented WSL/Linux, Windows and NVIDIA environment. GPT-OSS remains experimental and no model change has been approved for the CLI.
