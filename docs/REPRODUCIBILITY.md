# Reproduction reference and outstanding work

The initial export ran no models, inference, evaluations or tests. A later private-
review preparation adds one model-independent regression run and a CI definition;
see TESTING.md for the recorded outcome. No live-model evaluation or clean-install
walkthrough was performed. Application, existing tests and fixture bytes remain
unchanged. The CI definition has not been executed on GitHub; there is no packaging
claim for this source-only candidate.
Run modules from the repository root; there is no pyproject/installable package yet.

## Source versions

The root contains the reviewed revision-2 application/experiment code from the
private source checkpoint 654505c. `research_snapshots/revision1/` is a self-contained
allowlisted source/test/fixture tree from reviewed checkpoint 9031f10. It contains
real copies, not symlinks, a Git checkout or private history. Its `SNAPSHOT.json`
records exact input/output hashes. Use that directory as the working directory for
historical revision-1 code. Do not run its old schema against current-engine
artifacts or pretend a consumed holdout is unseen.

## Runtime profiles

Previously measured Python was 3.14.4 with SQLite FTS5; Ollama was 0.40.13. The core
CLI uses the default loopback service at 11434. Research clients use a separate
11435 daemon and ignored `.local_models` store, cloud disabled, one loaded model and
one worker. Research monitors currently require Linux/WSL2, `/proc`, a Windows C:
backing mount at `/mnt/c`, Windows PowerShell and NVIDIA tooling. These are platform
interfaces, not personal paths; they remain unchanged to preserve behavior.
Do not use the research profile on an unsupported platform without review.

For a future intentional research run, first create the output/runtime directories:

```bash
mkdir -p results/model_comparison results/oracle_evidence results/conversation_architecture
mkdir -p experiments/model_comparison/runtime experiments/oracle_evidence/runtime experiments/conversation_architecture/runtime
```

Start the dedicated daemon in its own terminal (reference only):

```bash
.venv/bin/python -m experiments.oracle_evidence.start_service --cache-mib 512
```

Obtain only the intended candidate into that store using Ollama with
`OLLAMA_HOST=127.0.0.1:11435`; for example `ollama pull gpt-oss:20b` with that variable
set. Model downloads are external; inference stays loopback-only. Existing public
digests are provenance anchors, not a guarantee the mutable remote tag still points
to identical bytes. Do not bundle weights or duplicate stores casually.

The experimental callback uses native GPT-OSS low reasoning, 4096 context,1024
output tokens and fixed sampling documented in unchanged code. Earlier Qwen-only
and model-comparison profiles have different controls; do not combine their times.
Before any live study, review source-specific service PID handling, disk/memory
floors, output budgets and single-worker ownership. Cache caps must be verified in
runner logs, not assumed from environment variables.

For later intentional generation with fresh outputs and Windows memory guard:

```bash
.venv/bin/python -m experiments.conversation_architecture.run generate --cases experiments/conversation_architecture/holdout-round2.json --output results/conversation_architecture/fresh.json &
publication_evaluation_pid=$!
.venv/bin/python -m experiments.oracle_evidence.host_guard --output results/conversation_architecture/host-memory-fresh.json
wait "$publication_evaluation_pid"
```

This example reruns a consumed benchmark; it is not new acceptance evidence. Use
fresh independent data for refinement acceptance. Native runs may generate private
wire/reasoning/resource logs: they are ignored by the public `.gitignore` and must
not be published without a new privacy review. Never execute those commands merely
to validate this export. No such commands were executed during export.

The unchanged native analysis utilities expect native run/review files, not the
curated inspection format in `evidence/`. Public summaries copy saved scores and
latencies; checksums verify exported bytes, not model-output repeatability or new
semantic correctness. Fixed seeds did not preserve every answer across runtime
conditions. Retain errors, ambiguous judgments and unhelpful fallbacks.

## Still required before a publication/release claim

- Owner review of the export and an explicit code/data license decision.
- A clean-install/live-CLI walkthrough on each intended platform; see the documented
  reference profile and current restrictions in RUNTIME_REQUIREMENTS.md.
- Execution of the new no-model CI workflow in a future private repository; live
  model evaluation remains deliberately absent from ordinary CI.
- Exact runtime/model artifact availability and any new distribution-specific notices;
  the current source-only external-component inventory is in THIRD_PARTY_NOTICES.md.
- Independent human data/publication review and stronger conversational acceptance.

These remaining items were not executed by the original export or this private-
review preparation. No project license, remote repository or deployment is created.
