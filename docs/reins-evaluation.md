# Reins Evaluation (Controlled Front-End Experiment)

## Purpose

Evaluate whether Reins can provide a lower-friction, more reliable mobile interaction loop with Colossus than the current Element/Matrix path.

This is an operational usability/reliability experiment only. Reins is evaluated as a **candidate front-end adapter** to CCE, not as a substrate replacement.

Read first:

- `docs/architectural-invariants.md`
- `docs/frontend-adapter-boundary.md`
- `docs/near-term-architecture.md`
- `docs/decision-log.md`

## Non-negotiable invariants (must hold during evaluation)

- CCE is the substrate.
- Front ends are replaceable.
- Operational semantics are authoritative; interfaces are not.
- Workspace truth, grounding rules, PEM continuity, and completion semantics must remain outside the front end.

## What Reins is (as built today)

Based on repository inspection (Flutter app):

- Reins is a multi-platform client designed to talk directly to an Ollama server over HTTP.
- It stores chats and messages locally (SQLite via `sqflite`), and stores settings locally (Hive).
- It supports per-chat configuration: model selection, system prompt, and generation options.
- It supports streaming responses from `/api/chat` and `/api/generate`.
- It includes capabilities that change Ollama-side state (e.g., create/delete models via `/api/create` and `/api/delete`).

Implication: Reins is architected primarily as a **direct Ollama chat client**.

## Transport / session model

- Transport is direct HTTP to an Ollama base URL (default `http://localhost:11434`; configurable).
- Server address is persisted locally and can be updated live.
- The app includes a “Search Local Network” feature that scans local IPv4 ranges for an Ollama server on port `11434`.

Operational notes:

- The local-network scan is aggressive (tries many addresses). This may be useful on a LAN, but it is a battery/latency risk on mobile networks and does not map cleanly to a Tailscale-first workflow.

## Ollama interaction model

- Reins uses Ollama’s `/api/chat` with `messages` and inserts `system` prompt as the first message when configured.
- Streaming is handled by reading newline-delimited JSON chunks from the response stream.
- Errors are surfaced via HTTP status mapping and a socket-level “network lost” message.

Core implication for CCE:

Reins’ default semantic unit is “chat history + system prompt + options -> model response”. That is exactly the context ownership CCE must keep **outside** the front end.

## State handling and persistence

Reins persists locally:

- Chat list and per-chat configuration (model, title, system prompt, options) in `chats` table.
- Full message history in `messages` table, ordered by timestamp.
- Server settings (e.g., server address) via Hive.

CCE compatibility concern:

- For CCE integration, the front end must not become the authority for continuity semantics. Reins’ local chat database is acceptable only as **adapter-local UI convenience** and must not be treated as the semantic source of model context.

## Reconnect behavior and failure visibility

What can be seen from code inspection:

- The app attempts to connect to the configured server and indicates success/error.
- Streaming operations catch socket errors and surface a human-readable message.
- There is no evidence (from inspection alone) of durable delivery guarantees (e.g., acked message queueing) across app suspension, OS backgrounding, or flaky networks.

What requires lived testing:

- iOS backgrounding behavior during streaming.
- Recovery behavior after network drops mid-stream.
- Behavior under captive portals / switching Wi-Fi <-> cellular.
- Whether prompts are ever “lost” silently vs retriable.

## Architectural compatibility against the CCE front-end adapter boundary

Reference: `docs/frontend-adapter-boundary.md`.

### Where Reins aligns well (strengths)

- Clear transport boundary: it is already a thin(ish) network client to a single endpoint.
- Mobile-first UX: designed for quick interaction loops.
- Streaming support: reduces perceived latency and supports conversational flow.
- Local settings storage: adapter-local state is explicit.
- Failure surfacing exists (at least at socket and HTTP levels).

### Primary mismatches / risks for CCE (UI capture risk)

Reins, as-designed, tends to own semantics that must remain substrate-owned in CCE:

- **History-as-context default**: it sends full message history to Ollama as the core mechanism.
- **Per-chat system prompts and options**: encourages interface ownership of context shaping.
- **Model switching and “save custom models”**: can drift into interface-owned behavior and substrate bypass.
- **Local durable chat store**: risks becoming the de facto continuity layer unless explicitly constrained.

Additional operational concerns:

- **Local network scanning**: may be inappropriate or surprising in some environments.
- **Ollama-side state mutation** (`/api/create`, `/api/delete`): must not be enabled in a CCE-adapter mode unless explicitly governed by the substrate.

## Explicit distinction: two different uses of Reins

### A) Reins as a direct Ollama mobile client

- Topology: `iPhone/iPad -> (LAN or Tailscale) -> Ollama on Colossus`
- Semantics: Reins owns chat history, system prompt, options, model selection.
- Value: quickest way to test whether Reins reduces mobile friction and improves reliability for *direct* local-model use.

This can be a valid operational experiment, but it is not a CCE adapter.

### B) Reins as a future CCE front-end adapter

- Topology: `iPhone/iPad -> Reins(adapter mode) -> CCE gateway -> workspace runtime -> local model`
- Semantics: CCE owns workspace truth, grounding eligibility, context assembly, and completion semantics.
- Adapter obligations: preserve intent, preserve error fidelity, preserve identity, avoid hidden rewriting.

This would require deliberate constraints/changes so Reins does not:

- send its local chat history as model context
- own system prompts/options as semantic controls
- mutate Ollama-side state outside substrate governance

## What must remain externalized in CCE (non-movable)

Even if Reins becomes an adapter later, these remain substrate-owned:

- active workspace selection and persistence
- manifest parsing and declared-source policy
- grounded QA context assembly (ordering, budgets, truncation behavior)
- completion semantics and error taxonomy
- PEM continuity/governance (if/when present)

## Recommendation category

- **Suitable as-is for operational experimentation** as a *direct Ollama mobile client* (to learn about mobile friction, latency, and reconnect behavior).
- **Suitable only with adapter constraints** for any future *CCE front-end adapter* work.

In other words: promising for the goal (mobile reliability loop), but requires architectural isolation to avoid UI capture of CCE semantics.

## Minimal experimental topology (non-invasive)

Keep the verified CCE path intact:

- `Element/Matrix -> CCE gateway -> workspace runtime -> local model`

Run a parallel experiment:

- `iPhone/iPad -> Reins -> Tailscale -> Ollama on Colossus`

Rules for the experiment:

- Treat Reins outcomes as operational signals (friction, interruption, reconnection, trust failures).
- Do not infer substrate requirements from UI convenience features.
- Do not migrate workspace semantics into Reins.

## What to test via lived use (can’t be learned from code inspection)

- time-to-interact on mobile (unlock -> response)
- reliability under interruption (calls, app switch, sleep/wake)
- reconnect behavior under real network changes
- failure clarity (can you tell auth vs network vs server-down vs model-not-found?)
- whether it reduces operational babysitting compared to Element
- whether the interaction loop supports habit formation and trust

## What architecture inspection can decide (without lived use)

- whether Reins is natively “chat-history-centric” (it is)
- where state lives (local SQLite/Hive)
- what semantics the UI tends to capture by default (system prompt/options/history)
- whether it mutates Ollama-side state (it can)

## Explicit non-goals of this phase

- no Reins integration into CCE
- no changes to the Matrix/CCE operational path
- no new runtime behavior, model behavior, embeddings, web access, or autonomy

