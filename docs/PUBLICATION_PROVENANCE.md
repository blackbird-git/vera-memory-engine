# How I prepared this repository

I exported a reviewed subset of my original development checkpoint `654505c` into a new repository with fresh Git history. The original source and evidence remain private and unchanged. The first public-edition commit was `cc1d823`.

The [allowlist](../PUBLICATION_ALLOWLIST.json) and [publication manifest](../PUBLICATION_MANIFEST.json) record the files admitted to the export. Application code, tests and synthetic fixtures were copied without behavioral changes. The historical revision-1 tree comes from checkpoint `9031f10`.

## Evidence and checksums

Some research evidence was reduced to selected fields before publication. Each derivative records its original private path, revision and SHA-256, together with the transformation applied. The original hash identifies the private artifact, not the sanitized copy.

I preserved the original scores, answer text and review judgments. Published checksums are computed separately. The checksum file covers every tracked regular file except itself, including the publication manifest. The manifest does not hash itself.

## What I left out

Private operational notes, recovery logs, raw requests and responses, generated reasoning, host inventories, process IDs, detailed resource logs, a model-pilot file containing personal paths, archives, backups, credentials, model stores and original Git metadata were excluded.

Generic platform paths such as `/proc` and `/mnt/c` remain in the research code because those platform interfaces are part of the reference environment. Aggregate GPU/memory capacities and measured timings remain useful research context.

## Verification history

The initial export did not run tests or inference. A later local preparation added the test runner, CI and documentation and recorded one successful 122-test local run. The older private-project test result is retained as a separate historical record.

The initial GitHub Actions run also completed successfully with 122 tests. See [testing](TESTING.md). The subsequent documentation edit changes the public presentation, not the application, fixtures, existing tests or research results.
