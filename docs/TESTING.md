# Testing and verification

## Running the tests

From the repository root, using Python 3.14.4 with SQLite FTS5:

~~~bash
python3 -B scripts/run_unit_tests.py
~~~

I use the same model-independent suite locally and in CI. It discovers the root tests once and keeps temporary synthetic data under `.test-tmp/`. A Python audit hook blocks live networking and child-process operations; any recorded attempt causes the run to fail, even if a test catches the exception.

The tests cover:

- SQLite/FTS5 integrity, retrieval and source state.
- Confirmation, cancellation, correction and deletion of memories.
- Conversational intent, scope and context regression cases.
- Model response parsing, output filtering and retries.
- Source pointers, context bindings and benchmark summary safeguards.

Model responses and host/service probes are mocked. No GPU, Ollama, model weights or personal data is required. The guard is test infrastructure, not a production security sandbox.

## Results

| Environment | Tests | Failures | Errors | Skips | Blocked live I/O |
|---|---:|---:|---:|---:|---:|
| Local reference environment | 122 | 0 | 0 | 0 | 0 |
| Initial GitHub Actions run | 122 | 0 | 0 | 0 | 0 |

The local run took 3.368 seconds. The hosted run took 1.707 seconds in unittest. These are regression runtimes, not model inference benchmarks.

[Local result](../evidence/verification/local-regression-result.json) · [Local log](../evidence/verification/local-regression-tests.txt) · [Hosted CI run](https://github.com/blackbird-git/vera-memory-engine/actions/runs/44184727744)

The [older private-project result](../evidence/prior-test-status.json) remains a separate historical record.

## CI configuration

The [workflow](../.github/workflows/tests.yml) runs on Ubuntu 24.04 with Python 3.14.4, on pushes, pull requests and manual dispatch. Checkout and Python setup are SHA-pinned, permissions are read-only, checkout credentials are not persisted, and the job has a ten-minute timeout.

GitHub networking is used for checkout and interpreter provisioning before the guarded tests. No model download, live-model evaluation, self-hosted model machine or artifact upload is involved.

A passing test suite does not establish live-model compatibility or conversational acceptance. I keep live experiments separate and opt-in, and retain failures without silently changing the expected answers.
