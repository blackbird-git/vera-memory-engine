# Model-independent testing and verification

## Existing suite

From the publication-candidate root, with Python 3.14.4 and SQLite FTS5:

```bash
python3 -B scripts/run_unit_tests.py
```

The new test-only runner discovers the unchanged root `tests/test*.py` suite once.
It adds the project root to the import path and uses project-local `.test-tmp/`
for temporary synthetic files. It blocks live socket operations and child-process
execution, and reports any blocked attempt as an overall failure even if a test
catches the exception. It neither launches services nor alters application modules.

Covered areas include SQLite/FTS5 integrity, retrieval and source state, deliberate
memory confirmation/cancellation/correction/deletion, intent/scope regressions,
output filtering/retry behavior, source pointers/context bindings and safeguards
against misleading benchmark summaries. Model responses and external host/service
probes are mocked. Tests never need real family data, Ollama, weights, a GPU or
Windows PowerShell. A successful regression run does not prove conversational
quality, real-model compatibility or the absence of hallucinations.

## GitHub Actions

[The workflow](../.github/workflows/tests.yml) runs the same command on GitHub-hosted
Ubuntu 24.04 / Python 3.14.4 for pushes, pull requests and manual dispatch. It uses
SHA-pinned checkout/setup actions, `contents: read`, no persisted checkout credentials,
a ten-minute timeout and no package/model installation or artifact upload.
It does not use `pull_request_target` or self-hosted model machines.

Checkout and Python provisioning require GitHub networking before tests start.
The runner then blocks live network/process operations for test execution. The
workflow definition is provided for a future private repository; no remote was
created and the GitHub workflow has not been executed as part of this task.

## Recorded local verification

The current one-run outcome is recorded in
[the local result](../evidence/verification/local-regression-result.json) and
[the sanitized test log](../evidence/verification/local-regression-tests.txt).
The files distinguish the current run from
[the older private-project result](../evidence/prior-test-status.json).

No test failures are repaired automatically during publication preparation. If the
run fails, preserve the failure and report it. Do not silently change fixtures,
gold targets, application behavior or the suite to obtain a passing checkpoint.
Model-dependent research and consumed holdout evaluations are separate opt-in work;
none is run by this command or by the CI workflow.

The authorized local run completed once with **122 tests passed, zero failures,
zero errors and zero skips**, using Python 3.14.4. Unittest reported 3.368 seconds.
The live-I/O guard recorded no violations. SQLite/build details are in the result
JSON. No application/test behavior was changed, no failures were repaired and no
second run was performed. GitHub-hosted CI and live inference remain unexecuted.
