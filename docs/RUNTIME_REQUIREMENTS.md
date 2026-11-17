# Runtime requirements and platform restrictions

| Profile | Requirements | What has and has not been verified |
|---|---|---|
| Model-independent regression suite | Python 3.14.4; standard-library SQLite with FTS5; writable project-local scratch directory | One local invocation is recorded in the verification artifact. CI is configured for Ubuntu 24.04; its hosted job has not run yet. No model/service/GPU is needed. |
| Existing CLI | Same Python/FTS5; separately installed local Ollama; `qwen3:4b`; loopback port 11434 | Historical reference was Ubuntu under WSL2, Ollama 0.40.13. This preparation does not run a fresh live-model demonstration. |
| Isolated model/conversation experiments | Linux/WSL2 `/proc`, POSIX process tools, Windows backing drive at `/mnt/c`, working `powershell.exe` interop, NVIDIA driver/tooling including `nvidia-smi`, native Ollama executable | Host-specific monitors are unchanged; native Windows, macOS, CPU-only and non-NVIDIA research profiles are not validated. Do not treat the core test result as research-platform support. |

Python 3.14.4 is a reference version, not a demonstrated minimum version. The
stdlib `sqlite3` module must be built with FTS5. Tests exercise FTS5; an
`OperationalError` about the FTS5 module indicates an unsuitable interpreter build.
No additional Python packages are declared or needed. `requirements.txt` is
intentionally comments-only. Create your own virtual environment; none is bundled.

The core code is ordinary Python/SQLite but cross-platform CLI behavior, file
permissions and backup semantics have not been validated on every OS. The examples
use POSIX shell paths; WSL is the documented Windows route. A Windows-native Ollama
service is not necessarily available as WSL loopback in every network configuration.
Do not expose a server on all interfaces to work around that mismatch.

## Local model requirements

The CLI defaults to Qwen3 4B. Its client has Qwen-specific reasoning controls;
setting `--model` to an arbitrary candidate does not constitute compatibility or
production approval. GPT-OSS 20B and the Qwen3.5/Ministral candidates belong to the
separate experimental clients. Model cards, tags, quantizations and recorded digests
are documented in THIRD_PARTY_NOTICES.md and evidence/model-identities.json.

Historical larger-model measurements used a 32 GiB host and an 8 GiB-class NVIDIA
GPU with CPU offload. Some stock 27B attempts stalled or were safely aborted;
these are observations, not universal minimum hardware requirements. More RAM/VRAM
does not fix the documented semantic failures. Context, output budget, prompt cache,
Windows commit headroom and other workloads all affect capacity and latency.

The research service is isolated at 11435 with `.local_models/`, cloud disabled,
one loaded model and one worker. Models must unload between candidates. Resource
monitors depend on the current host and inspect only their owned service. Do not
trust stale PID files, weaken safety thresholds or stop unrelated applications.
The recorded disk policy protects at least 40 GiB of actual Windows backing-drive
free space; Linux virtual-disk free space is not equivalent. No reboot, paging
change, forced application closure or hardware setup is part of installation or CI.

## Storage and privacy

Archive content and metadata persist in local SQLite. Media paths are references,
not processed or bundled media. The database is not encrypted, and local filesystem
permissions are not a complete authorization or family-access-control system.
Keep personal archives, backups, weights, credentials and unreviewed native logs
outside Git. The `.gitignore` defaults native `results/` and runtime output to
private; deliberately curated evidence is kept separately in `evidence/`.
