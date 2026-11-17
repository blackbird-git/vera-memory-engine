# Private-review preparation check

The initial export underwent a bounded static privacy/inventory check without
executing models, tests or evaluations. This subsequent preparation is distinct:
it adds public documentation/notices, CI and exclusions, then runs the existing
model-independent regression suite exactly once.

## Current verification

- Python 3.14.4; 122 tests passed, zero failures/errors/skips.
- Test-only live network/child-process guard recorded no violations.
- No Ollama service/model launch, model download or evaluation occurred.
- No application modules, existing tests, synthetic fixtures, curated prior model
  evidence or historical source snapshots changed. No test failure was repaired.
- No original repository access, Git initialization, remote creation or push.
- No project license selected or applied. THIRD_PARTY_NOTICES.md identifies external
  dependencies without licensing Vera's own code/data.

See evidence/verification/local-regression-result.json and its sanitized log. The
GitHub Actions definition has not run on GitHub. Live installation/inference and
conversational acceptance remain unverified in this candidate.

## Publication integrity and privacy

The public allowlist records the new documentation/test-infrastructure paths.
PUBLICATION_MANIFEST.json retains original-source provenance and describes later
private-review changes separately. PUBLIC_CHECKSUMS.sha256 covers every regular
file except itself; it covers the publication manifest, which is not self-hashed.
No original private artifact or historical review was edited.

The bounded final inventory/checksum review covers candidate files only. It checks
for symlinks, missing/unexpected inventory entries, stale hashes, broken local
Markdown links and obvious credential/personal-path patterns. Excluded native
wire/reasoning/resource logs, archives, model stores and runtime files do not belong
in the candidate. Future native results are private by default under .gitignore.
This check does not prove the absence of every possible sensitive datum.

Remaining blockers are owner review and code/data licensing decisions, execution
of the workflow in a future private repository, clean-install/live-model/platform
verification where intended, and the documented factual/conversational limitations.
No automatic publication or deployment is authorized.
