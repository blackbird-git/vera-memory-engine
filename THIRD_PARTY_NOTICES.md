# Third-party notices

This document identifies external components used by the reference runtime,
optional experiments and CI. **It does not select or apply a license to Vera's code,
fixtures or saved evidence.** No third-party binaries, model weights, Python
packages or GitHub Action implementations are vendored in this candidate.

## Interpreter, database and inference runtime

| Component | Reference / use | Upstream attribution and terms |
|---|---|---|
| CPython and standard library | Python 3.14.4; application and regression tests | Python Software Foundation and historical contributors. PSF License Agreement v2 and historical notices in the [CPython license file](https://github.com/python/cpython/blob/v3.14.4/LICENSE). |
| SQLite / FTS5 | Local regression build 3.46.1, supplied by Python `sqlite3`; persistent archive and synthetic tests | SQLite authors dedicate the deliverable code/documentation to the [public domain](https://www.sqlite.org/copyright.html). The actual SQLite build version is recorded with the local test result. |
| Ollama | Historical model experiments used 0.40.13; separately installed local server | Copyright (c) Ollama; [MIT license](https://github.com/ollama/ollama/blob/main/LICENSE). Model licenses are separate from the server license. |

No pip runtime or test dependency is declared. Installed Python/Ollama distributions
can contain additional components with their own notices; retain the notices in
those upstream distributions. If this project later bundles binaries, containers
or other third-party code, inventory that exact distribution and its notices first.
This source-only inventory does not authorize redistribution of a runtime image.

## Optional local models

These model references document the existing work, not a request to download or
run anything. No model weights are shipped. Quantization and content identity are
recorded in [the sanitized model inventory](evidence/model-identities.json).
An Ollama tag is mutable; its spelling alone does not reproduce a measured model.

| Recorded tag / profile | Role | Upstream attribution and licensing reference |
|---|---|---|
| `qwen3:4b` / Q4_K_M | Reference CLI model and prior baseline | Qwen authors; [Qwen3-4B Apache-2.0 license](https://huggingface.co/Qwen/Qwen3-4B/blob/main/LICENSE). |
| `qwen3.5:4b` / Q4_K_M | Experimental candidate | Qwen authors; [Qwen3.5-4B model card and Apache-2.0 declaration](https://huggingface.co/Qwen/Qwen3.5-4B). |
| `qwen3.5:27b` / Q4_K_M | Experimental candidate, including unsuccessful sustained runs | Qwen authors; [Qwen3.5-27B license](https://huggingface.co/Qwen/Qwen3.5-27B/blob/main/LICENSE). |
| `qwen3.5:27b-text-oracle` | Local experimental profile, not an independently published model | Same Qwen3.5-27B language weights, with the vision projector omitted; see [profile provenance](evidence/oracle/text-profile.json). Upstream model terms still apply. |
| `ministral-3:3b-instruct-2512-q4_K_M` | Experimental candidate | Mistral AI authors; [Ministral 3 3B Instruct 2512 model card and Apache-2.0 declaration](https://huggingface.co/mistralai/Ministral-3-3B-Instruct-2512). The Ollama artifact is quantized; it is not the unmodified tensor distribution in the model card. |
| `gpt-oss:20b` / MXFP4 | Leading experimental candidate, not an approved production replacement | OpenAI authors; [Apache-2.0 license](https://github.com/openai/gpt-oss/blob/main/LICENSE) and separate [upstream usage policy](https://github.com/openai/gpt-oss/blob/main/USAGE_POLICY). |

Preserve the applicable license and any required notices, attribution and change
identification if redistributing or modifying upstream material. Do not infer that
a model's license licenses this application, its synthetic data or all generated
outputs. No ownership or redistribution decision for this project's outputs is made
here. No vendor endorsement, affiliation or model approval is implied.

## GitHub Actions used by the regression workflow

Both actions are provided by GitHub, Inc. and contributors under their respective
MIT licenses. Their implementations are fetched by GitHub when the workflow runs;
only references are stored here. They are pinned to immutable commit IDs:

| Action | Pinned revision | Upstream notice |
|---|---|---|
| `actions/checkout` | `3d3c42e5aac5ba805825da76410c181273ba90b1` (`v7.0.1`) | [License at pinned revision](https://github.com/actions/checkout/blob/3d3c42e5aac5ba805825da76410c181273ba90b1/LICENSE) |
| `actions/setup-python` | `a309ff8b426b58ec0e2a45f0f869d46889d02405` (`v6.2.0`) | [License at pinned revision](https://github.com/actions/setup-python/blob/a309ff8b426b58ec0e2a45f0f869d46889d02405/LICENSE) |

The upstream action copyright notice identifies GitHub, Inc. and contributors.
The selected action generations use Node 24; the workflow targets GitHub-hosted
Ubuntu 24.04, not the workstation that runs models. Setup/check-out networking is
separate from the regression runner, which blocks live network/process operations.
The workflow does not use third-party test packages or upload test artifacts.

## Optional platform tooling

The unchanged live-research monitors call Linux `/proc`, Windows `powershell.exe`,
`ps` and NVIDIA `nvidia-smi`; the test suite mocks the relevant probes. No operating
system, driver, CUDA toolkit or PowerShell distribution is included. Those installed
products remain subject to their own distribution terms. Model licenses do not
replace the terms of GPU drivers, Windows or other runtime software.

Upstream references were consulted while preparing these notices. Exact installed
artifacts and future dependency changes still need review; this is not a license
choice for the project or a bundled-runtime compliance inventory.
