# Conversation architecture experiments

I wanted to understand why Vera could find the right source but still answer an overly broad or incomplete question, particularly in a multi-turn conversation.

These experiments separate the request and context plan, source selection and response composition. I compare the existing engine with an experimental source planner and a natural-language draft. Neither experimental path replaces the reference CLI.

The frozen case sets and manifests preserve the evaluation conditions. The published results include failures as well as improvements. Existing holdouts are already consumed; use new cases to validate a subsequent refinement.

- [Research results](../../docs/RESEARCH_RESULTS.md)
- [Original architecture audit](INDEPENDENT_AUDIT.md)
- [Original review method](INDEPENDENT_REVIEW_METHOD.md)
- [Reproduction instructions](../../docs/REPRODUCIBILITY.md)

The audit and review method are preserved as historical development-agent records, not independent human validation. Native runner logs remain private, and the current live-research profile depends on WSL/Linux, Windows interop and NVIDIA tooling.
