# Development and contribution notes

This is an independent research project. If you want to contribute, please keep the following in mind.

- Use synthetic data only. Keep personal records, media, credentials and machine-specific paths out of the repository, issues and test output.
- Preserve source attribution and uncertainty. A literal quote is not proof that an answer is relevant or that a paraphrase is supported.
- Run `python -B scripts/run_unit_tests.py` from the root before submitting changes. No model is needed. Keep live-model experiments separate from CI.
- Record failures as well as successes. Don't change expected answers or weaken tests just to make a run pass.
- Freeze new evaluation cases before testing an implementation. Once a holdout has been used to refine it, it is development evidence rather than an unseen test.
- Review new research evidence before committing it, and update the publication manifest and checksums when appropriate. Raw inference logs are ignored by default.

Live experiments require the platform and resource precautions described in [reproduction](docs/REPRODUCIBILITY.md). The independent reviews in this repository were conducted by separate development agents, not human reviewers.

There is no project license yet. Contact me before redistributing or incorporating the code or data into another project.
