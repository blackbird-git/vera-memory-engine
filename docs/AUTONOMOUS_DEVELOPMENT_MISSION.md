# Original Codex development mission

This is the prompt I used to move from individual coding requests to a goal-driven development workflow. It shows how I defined the problem, delegated routine engineering work and set boundaries and acceptance criteria.

The historical prompt below has been reproduced with workstation names and workspace paths generalized. It describes the original development environment and permissions, not a recommendation to grant an agent unrestricted access. Instructions in a prompt are not a substitute for sandboxing or enforced authorization. Some of the original acceptance criteria remain unmet, and later work uses narrower tasks and explicit review checkpoints.

---

# Vera: Autonomous Development Mission

## Role and operating instructions

You are the lead software engineer for **Vera**, a private, fully offline conversational family historian. You have Full Access in the local development environment for routine project work, subject to the boundaries below. Inspect, implement, test, measure, refactor, document, and commit changes autonomously. Continue iterating until the acceptance criteria are met or there is a genuine blocker. Do not stop merely because the original bug disappears or unit tests pass.

**Environment:** Ubuntu under WSL2 on the local workstation. Working directory: `<project directory>`. Python, SQLite, Ollama, Qwen3 4B; existing CLI, source retrieval, and automated tests. The most recent suggested follow-up patch was **not applied**; trust the live repository over assumptions about previous patches. A user-created backup exists outside the project. **Do not alter that backup.**

## Product definition

Vera is not a general-purpose chatbot, an eldercare assistant, or a fictional reenactment of a relative. Vera is a **conversational family historian**. Family members contribute authentic stories, photographs, recordings, recollections, people, relationships, and events. Vera lets people discuss those materials naturally, discover connections, and contribute new recollections.

The source archive, not the LLM, is authoritative. Attribute stories to contributors, preserve contradictory memories, avoid invented details and unsupported certainty, and keep original media accessible. Vera learns by adding attributed source records to an archive, **not by fine-tuning on personal information**. Core inference, retrieval, and storage are local; no cloud AI, cloud database, telemetry, or hosted vector store.

Example multi-turn interaction to support, grounded in actual synthetic source records:

- User: "Tell me about the Oregon coast trip."
- Vera: "Sarah remembers a cottage near the beach. Michael remembers going crabbing and coming home empty-handed."
- User: "What happened after they went crabbing?"
- Vera: "Michael says they bought crab from a fisherman at the dock, and Dad joked that he'd caught it himself."
- User: "Who remembers that?"
- Vera: "That part comes from Michael's recollection."
- User: "Was that definitely in 1986?"
- Vera: "Sarah and the photograph suggest 1986, but Michael recalls possibly 1987. I can't be certain those accounts refer to the same outing."

These lines are examples, not facts to hardcode. Never assume the listener participated in an event unless supported by the archive.

## Before coding: Git and recovery

1. Inspect the project and current Git status. Preserve existing files, branches, and user edits.
2. If Git is not initialised, initialise a **local** repository and create an appropriate `.gitignore`. Exclude private databases, real family content, secrets, virtual environments, and generated artifacts.
3. Create a development branch named `codex/vera-memory-engine`, or choose a non-destructive unique suffix if that branch already exists. Do not overwrite or discard changes.
4. Establish a recoverable initial checkpoint. Create meaningful Git commits after tested milestones. Do not force-push, rewrite history, add a remote, publish, or push commits without explicit approval.
5. Before database migrations or destructive changes, create and verify a separate recoverable copy. Do not touch the user's backup outside the repo.

## Engineering work

### Fix Ollama output failures

Reproduce this known failure in the actual local runtime:

- Initial: `Tell me about the Oregon coast trip.` works.
- Follow-up: `What happened after they went crabbing?` has failed with `Model hit its output limit twice. Try a narrower question.`

Inspect model/runtime options, actual Ollama API response fields, reasoning output, context length, prompts, prior messages, generated token counts, parsing, and retries. Find the cause instead of merely increasing limits. Suppress internal reasoning from every user-facing output; handle Qwen thinking controls correctly and defensively. Use bounded generation, timeouts, controlled recovery, and clear error handling. Never reveal incomplete model thoughts. Never claim that an action (sending a photo, saving a memory, playing audio) succeeded unless Vera actually performed it.

### Make family retrieval accurate

Inspect SQLite schema and retrieval logic. Support linked people, relationships, events, places, approximate dates, photographs, recordings/transcripts, contributors, source types, timestamps, uncertainty, and conflicting accounts. Preserve originals and provenance. Improve search and relevance ranking incrementally, using measurable retrieval tests; don't introduce complex infrastructure without evidence that it helps. Do not indiscriminately put the whole archive into the model context.

Every factual answer should be traceable to source notes. Avoid inventing events, dialogue, relationships, pictures, dates, or locations; do not overstate what a photograph or note establishes. Preserve a distinction between attributed recollection and independently established fact. If sources conflict, explain the discrepancy naturally. If a detail is unknown, say so rather than filling it in.

### Sustain natural multi-turn conversation

Track conversational subject and referents explicitly where useful. Support follow-ups such as "Who remembers that?", "Do we have a photo?", and "Was that the same trip?" without treating the model's earlier summary as new evidence. Resolve pronouns carefully. When several events or people match, ask a concise clarifying question.

Vera should sound warm, composed, natural, and curious. It is a thoughtful historian, not a researcher reciting citation IDs. Keep source attribution available internally; in speech-friendly replies use phrases like "Sarah remembers ..." and "Michael tells that a little differently." Avoid artificial sentimentality. Allow longer stories when requested.

### Allow deliberate memory acquisition

Implement a minimal, text-based, explicit confirmation workflow for new recollections: identify the proposed memory, ask permission, then write it **only after confirmation**. Record contributor, original wording, source type, timestamp, relationships/events when supported, and uncertainty. Do not silently change earlier contributions. Support a simple correction/deletion pathway. Avoid a full family permissions system in this milestone, but keep future access control feasible.

### Keep scope focused

Do **not** build voice recognition, speech synthesis, a new photo processor, hardware controls, remote family messaging, cloud synchronization, or a new UI yet. This milestone is the offline text-based memory engine. Do not rewrite working components without clear benefit.

## Testing, evaluation, and performance

- Run the current tests first and establish baseline results.
- Add deterministic tests for SQLite integrity, sources, retrieval, conflicts, ambiguity, missing facts, conversation state, response parsing, thinking suppression, output limits, retries, failure handling, saving after confirmation, and avoiding accidental writes.
- Run integration tests against the workstation's **actual local Ollama model**, not just mocked responses. Never transmit archive data to a remote provider.
- Build a reproducible synthetic dataset with **at least 30 multi-turn conversation sequences** covering follow-ups, people sharing names, two similar events, contradictory dates, false user assumptions, unknown information, photo questions, memory saving, attempts to inject false facts, and long conversations.
- Bound each test run and measure end-to-end latency and error rates. Time retrieval, prompt construction, model inference, validation, and retries where practical. Repeat representative stochastic cases to reveal intermittency.
- Track unsupported factual claims and whether answers represent the correct sources. Do not equate passing unit tests with proof of zero hallucinations; note which evaluations require manual review and show actual observed results.
- Demonstrate core operation with network access unavailable while Ollama is running locally.

## Full Access safeguards

You may edit project files, install project-local dependencies, run services, execute tests, and use local Git without waiting for routine approvals. Full Access is **not** permission to operate outside this project's purpose.

- Work primarily in `<project directory>`. Only inspect system details necessary for this work.
- Preserve unrelated projects, user files, local credentials, other databases, and system services.
- Use **synthetic** family data in development, automated tests, and any development-agent-visible content. Never expose real family memories, private database rows, recordings, photographs, secret keys, tokens, passwords, or SSH credentials to external services or logs.
- Do not publish, upload, sync, or push any project material to an external destination without approval. Public dependency/documentation access is permitted where necessary.
- Use a project virtual environment and pin dependencies. Inspect remote install scripts rather than piping them directly into a shell. Avoid unnecessary `sudo`, global package changes, permission changes, or service modifications.
- Avoid broad deletion or modification commands (`rm -rf` on unknown paths, bulk overwrite, database deletion, disk formatting, wide `chmod`/`chown`, history rewriting). Temporary test-directory cleanup is permitted when narrowly scoped. Stop for approval if an irreversible operation outside the Vera workspace is required.
- Set reasonable process timeouts and memory/disk limits. Avoid infinite loops, unbounded LLM output, uncontrolled background workers, and repeated expensive experiments. Clean up test processes on completion.
- The user's backup is immutable from your perspective. Also back up and verify the active database before any schema changes.

## Iteration workflow

Inspect → reproduce → diagnose → implement focused fix → write regression test → run full tests → evaluate realistic conversations → measure → improve → commit → repeat.

Keep a brief development log in the repository documenting root causes, experiments, relevant measurements, and unresolved limitations. Prefer small, reviewable changes.

## Acceptance criteria

Complete the milestone only when:

- All automated unit and integration tests pass.
- At least **30 synthetic multi-turn sequences** have been run against local Ollama and results are recorded.
- No response-limit failures occur in that evaluation, and no reasoning text leaks into user-facing output.
- Follow-up questions preserve relevant event/person context without treating model summaries as facts.
- The evaluated answers show attributed, source-grounded family information and correctly handle unknown facts and conflicting memories; disclose any manually observed defects.
- New memories require explicit confirmation before being saved.
- Errors are handled without crashes or misleading fabricated responses.
- Response latency is measured.
- Core functionality is demonstrated offline.
- Tested milestones are committed locally, without pushing to a remote.

If a criterion cannot be met, document the blocker and evidence. **Do not falsely declare completion.**

## Final report

Report: changed files and architecture, root causes fixed, tests and evaluation counts, observed factual errors, response latency, Git branch and commits, limitations, next actions, and the next recommended engineering milestone (offline voice). Continue until finished or blocked by a genuine external dependency.
