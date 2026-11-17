# Private review and contribution guidance

No project code/data license has been selected. Discuss ownership and licensing
with the repository owner before redistribution or incorporation elsewhere.

Use synthetic records only. Do not put personal memories, documents, media, secrets
or host paths in commits, issues, test logs or CI artifacts. Keep original source
wording, contributor attribution and uncertainty intact. A valid source quote is
not proof that an answer is relevant or that a paraphrase is supported.

Run the existing model-independent suite from the root with
`python -B scripts/run_unit_tests.py`. It needs no Ollama or model weights. Record
failures rather than silently changing gold answers or weakening checks. Keep
model-dependent evaluations separate and opt-in; never add them to ordinary CI.

Live research requires the documented platform, resource guards and one owned model
slot. Preserve failed results. Freeze new synthetic holdouts before using them for
acceptance; a consumed holdout is development evidence, not an unseen test. Independent
agent reviews must not be described as independent human validation.

Review files before publication. Native result/wire/reasoning logs are excluded by
default; sanitize and explicitly admit any new evidence. Refresh public checksum
and provenance manifests after an intentional change. Do not copy the private Git
history or operational data, and do not use a model-quality average as a release gate.
