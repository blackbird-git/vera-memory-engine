# Runtime and platform requirements

| Profile | Reference requirements | Verification |
|---|---|---|
| Regression suite | Python 3.14.4, SQLite FTS5 | Passed locally and on GitHub-hosted Ubuntu 24.04 |
| Core CLI | Python/FTS5, Ollama 0.40.13, `qwen3:4b`, local port 11434 | Historical WSL2 reference; fresh live installation not yet verified |
| Larger model experiments | Linux/WSL2, Windows interop, NVIDIA tools and dedicated Ollama service | Host-specific research environment; not portable as currently written |

The Python standard library provides the application and test dependencies. Python 3.14.4 is the tested reference, not an established minimum version. If SQLite reports that FTS5 is unavailable, use an interpreter built with FTS5.

The core CLI is ordinary Python/SQLite, but native Windows, macOS and other platform behavior have not been independently validated. I use POSIX shell instructions and WSL on Windows.

## Ollama and models

The reference CLI uses Qwen3 4B with Qwen-specific output controls. Changing the model tag does not guarantee compatibility. GPT-OSS 20B, Qwen3.5 and Ministral candidates are experimental; see the [model inventory](../evidence/model-identities.json) and [third-party notices](../THIRD_PARTY_NOTICES.md).

The CLI permits only local endpoints on port 11434. It disables proxy forwarding and redirects. Do not expose Ollama on all interfaces to work around host/WSL networking.

## Research environment

My larger model runs used a 32 GiB host with an 8 GiB-class NVIDIA GPU and CPU offload. Some 27B runs timed out or were aborted by resource guards. That is a measurement from this environment, not a universal hardware requirement.

The separate research daemon uses port 11435, an ignored `.local_models/` store, cloud disabled, one loaded model and one worker. Its resource monitors depend on Linux `/proc`, Windows `/mnt/c` and PowerShell interop, and NVIDIA tooling.

The recorded disk policy protects at least 40 GiB of free space on the actual Windows backing drive. Virtual-disk free space is not equivalent. Review resource and process ownership guards before running these experiments; do not stop unrelated services or weaken the safeguards.

## Local storage

Records and metadata persist in SQLite. The database is not encrypted, filesystem permissions do not replace multi-user authorization, and media paths are references only. Keep real archives, model weights, backups, credentials and native research logs outside Git.
