# Vera — Local AI Memory Engine

[![Regression tests](https://github.com/blackbird-git/vera-memory-engine/actions/workflows/tests.yml/badge.svg)](https://github.com/blackbird-git/vera-memory-engine/actions/workflows/tests.yml)

## Why I built this

I wanted to explore how a locally hosted AI application could remember information over time without treating everything the model says as fact. I started with the idea of preserving family stories and memories, which turned out to be an interesting engineering problem in its own right.

How do you attribute a recollection to the person who told it? What happens when two sources disagree? How do you correct an old memory without losing its history? And how do you prevent a model from inventing details or writing its own assumptions back into the archive?

I built Vera with Python, SQLite and Ollama to work through those questions. I used ChatGPT and Codex for AI-assisted development, with a focus on understanding the architecture, running the experiments, and evaluating what actually works.

## What I built

- A local SQLite archive with full-text search (FTS5) and attributed source records.
- A conversational retrieval engine that maintains context across questions.
- Source selection and validation that distinguish original records from generated text.
- Explicit confirmation before conversational memory writes, with correction history.
- A local Ollama integration with bounded context and output handling.
- Isolated model comparisons, conversational evaluations and 122 automated regression tests.

## How it works

~~~mermaid
flowchart LR
    U[User question] --> C[Conversation context]
    C --> R[Retrieve relevant records]
    D[(SQLite archive)] --> R
    R --> P[Select evidence]
    P --> M[Local Ollama model]
    M --> V[Validate source references]
    V --> A[Attributed answer]
    U --> W[Propose memory change]
    W --> Y[Explicit confirmation]
    Y --> D
~~~

The archive is the source of truth. Earlier assistant replies are not evidence, and a correction preserves the original record rather than treating a model's summary as a new fact.

The reference CLI uses `qwen3:4b`. I evaluated several other open-weight models, including GPT-OSS 20B, in a separate research environment. None of those experiments has replaced the CLI's default model.

## Interesting problems I encountered

### Retrieving the right record isn't enough

A model can quote an actual source and still answer the wrong question. During testing I found that a retrieved event could include people or activities that were outside the scope of a follow-up question.

I experimented with separating request interpretation, evidence selection and answer composition. On the second conversational holdout, the experimental planner respected all five explicit topic exclusions, but answered only 9 of 16 questions completely, compared with 10 for the baseline. It improved scope control without improving overall completeness.

### More natural answers can be less reliable

Free-form drafts were often easier to read, but they sometimes added motives, reactions and dates that were not in the original records. Eight of sixteen natural drafts in the second holdout contained unsupported claims.

Even model-generated source plans and critic approval were not reliable substitutes for verifying what the evidence actually says. I kept that approach experimental rather than introducing it into the main engine.

### Context and uncertainty matter

A name appearing in a record does not prove that person participated in every activity. A date written on a photo envelope does not establish when the photo was taken. The engine needs to preserve these distinctions across multiple turns, and it does not always do so correctly yet.

[Research findings and limitations](docs/RESEARCH_RESULTS.md) · [Evaluation methodology](experiments/conversation_architecture/README.md)

## Try it yourself

The reference environment is Python 3.14.4 with SQLite FTS5. The Python code uses the standard library and runs directly from the repository; no pip packages are required.

~~~bash
git clone https://github.com/blackbird-git/vera-memory-engine.git
cd vera-memory-engine
python3 --version
python3 -m venv .venv
.venv/bin/python -m vera --db data/demo.sqlite3 init
.venv/bin/python -m vera --db data/demo.sqlite3 seed-demo
.venv/bin/python -m vera --db data/demo.sqlite3 list
.venv/bin/python -m vera --db data/demo.sqlite3 show 2
~~~

This creates a local archive using synthetic records. The above commands do not need a model. Use a new database path, not an existing personal archive.

For the conversational demo, install [Ollama](https://docs.ollama.com/quickstart), make sure the local service is running, and download the reference model:

~~~bash
ollama pull qwen3:4b
.venv/bin/python -m vera --db data/demo.sqlite3 --model qwen3:4b chat
~~~

Try asking about the Oregon coast trip, what happened after crabbing, who remembers it, and whether the year is certain. Compare the answers with the original records. These are example questions, not a claim that the current model answers all of them correctly.

Use `/quit` to exit. In a synthetic chat, `/remember` proposes a JSON record, `/confirm` saves it, and `/cancel` discards it.

Model downloads require internet access. Inference is restricted to the local Ollama service on port 11434. See the [runtime requirements](docs/RUNTIME_REQUIREMENTS.md) for platform and model limitations.

## Testing and evidence

~~~bash
.venv/bin/python -B scripts/run_unit_tests.py
~~~

The test runner blocks live network and child-process operations during tests. It uses synthetic data and mocked model responses, so Ollama and a GPU are not needed.

The initial public candidate passed all 122 tests locally and in [GitHub Actions](https://github.com/blackbird-git/vera-memory-engine/actions/runs/44184727744), with no failures, errors, skips or blocked live-I/O attempts. This verifies the tested behavior, not the factual accuracy of live model responses.

- [Test coverage and verification](docs/TESTING.md)
- [Research results](docs/RESEARCH_RESULTS.md)
- [Reproducing the experiments](docs/REPRODUCIBILITY.md)
- [Synthetic data and evidence provenance](docs/DATA_PROVENANCE.md)
- [Third-party notices](THIRD_PARTY_NOTICES.md)

## Project structure

| Directory | Purpose |
|---|---|
| `vera/` | CLI, memory archive, retrieval and conversation engine |
| `tests/` | Model-independent regression tests |
| `samples/` | Synthetic memory and evaluation fixtures |
| `experiments/` | Isolated model and conversational architecture experiments |
| `evidence/` | Sanitized results, reviews and verification records |
| `research_snapshots/` | Historical source snapshots for reproducing earlier experiments |

## Limitations

Vera is a research prototype. Conversational recall is still inconsistent, and the engine can miss relevant details, ask unnecessary clarifying questions or compose unnatural responses. The experimental models are not approved replacements for the current CLI.

The database is not encrypted and there is no multi-user authorization system. Photo and recording notes are text references, not media processing. No voice interface, cloud synchronization or remote messaging is implemented.

All records and published conversations are synthetic. The repository excludes private archives, native inference logs and model weights. A clean live-model installation on other platforms has not been verified; the larger experiments were conducted using a WSL/Linux and NVIDIA reference environment.

No project license has been selected. See [licensing status](docs/LICENSING_STATUS.md).
