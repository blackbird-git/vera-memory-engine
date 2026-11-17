# Publication checks

I prepared this repository from a sanitized copy of the original development project. The private source, work history and original research evidence were left unchanged.

## Verification

- 170 regular files in the initial GitHub commit; no symlinks.
- Python 3.14.4 local regression run: 122 passed, no failures, errors or skips.
- The test runner recorded no live network or child-process attempts.
- [Initial GitHub Actions run](https://github.com/blackbird-git/vera-memory-engine/actions/runs/44184727744): 122 passed, with no blocked live-I/O attempts.
- No model was downloaded or run as part of publication preparation.
- Application code, original tests and fixture data were preserved.

See [local verification](evidence/verification/local-regression-result.json) and [test log](evidence/verification/local-regression-tests.txt).

## Data review

I excluded personal archives, recovery material, raw inference transcripts, generated reasoning, runtime files, model stores and the original Git history. The allowlist records the files admitted to the export, and the publication manifest preserves the relationship between public evidence and private originals.

The local check covered inventory, checksums, symlinks, documentation links and obvious credential or personal-path patterns. A subsequent GitHub review examined the inventory, core code, documentation and selected evidence. Neither is a guarantee that every possible sensitive datum has been identified.

`PUBLIC_CHECKSUMS.sha256` covers the repository files other than itself. Historical private hashes and published output hashes have different meanings.

## Remaining work

The project is publicly available as a research prototype. I have not selected a code or data license, verified a fresh live-model installation across platforms, or met conversational acceptance criteria. No deployment or production-readiness claim is made.
