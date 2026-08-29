# Purchase Office — Dashboard Design (M5)

**Status:** Approved
**Date:** 2026-08-29
**Companion docs:** [PRD](../../purchase-office-prd.md) · [System design spec](2026-08-26-purchase-office-design.md) · [Domain glossary](../../../CONTEXT.md)

---

## Purpose

The observability pillar (G5) made real: a live dashboard streaming every Audit Trail event over
SSE, with two views — a live office floor and a scrubbable replay timeline. Serves FR-19 and the
demo metrics: press-play autonomy, live catch, replayability.

## Decisions

| Decision | Choice | Why |
|---|---|---|
| Event source | Tail the SQLite audit DB (seq cursor) | The trail is the single system of record; server and office can be separate processes; replay reads the same store |
| Run trigger | `POST /api/runs` in M5 | Makes the live floor genuinely live; M6's `demo.py` wraps it with seed data |
| Duplicate runs | Idempotent POST (repeat id → `200 {started: false}`) | Dissolves the double-click problem instead of handling it |
| Crash contract | Synthetic `role="office", action="error", status="FAILED"` event | QUARANTINED is reserved for Guardrail catches (CONTEXT.md); NFR-3 requires failures captured in the trail |
| Replay | Client-side scrub of a case's full event list | Demo scale; no server time-travel |
| Surface | 4 routes + static mount | Synthesized from three interface variants (minimal / flexible / demo-reliability); flexible variant's grammar and projections rejected as speculative |

## API

Converged core: global `seq` cursor (AUTOINCREMENT), SSE `id:` per message → EventSource
auto-reconnect with `Last-Event-ID`, one untyped `event: audit`, 202 fire-and-forget runs,
client closes on terminal, heartbeats, no auth (demo).

| Route | Behavior |
|---|---|
| `POST /api/runs` | Body optional `{request_id?, request?}`; server generates id / canned request when omitted. Background thread → `202 {request_id, started: true}`; repeat id → `200 {request_id, started: false}`. |
| `GET /api/events?after=&request_id=` | Backlog + replay + polling fallback. `after` exclusive, default 0. `{events: [EventOut…], cursor: global max seq}`. Empty DB → `{events: [], cursor: 0}`. |
| `GET /api/stream?after=` | SSE. Backfill `seq > after`, then tail (0.25 s poll, own sqlite conn per subscriber). `Last-Event-ID` overrides `after`. `retry: 1500`, `ping=15`, `event: audit`, `id: <seq>`. Never server-closes. |
| `GET /api/health` | `{ok: true, head_seq}` |
| `/` (static) | Vanilla-JS dashboard |

Prerequisite: `AuditEvent` gains `seq: int` (the cursor); `AuditTrail.read` selects it.

## Runner

Daemon thread per run: `build_graph(registry, llm_factory, stores_factory(), audit,
checkpointer=SqliteSaver)`, `invoke(..., config={"configurable": {"thread_id": request_id}})` in
try/except → error event on crash. `create_app(registry_path, audit_path, checkpoint_path,
llm_factory=None, stores_factory=None)`; tests inject `FakeLLMClient`; default builds
`GeminiLLMClient` per role. Single uvicorn worker.

## Frontend — Records Room

One job: watch a case walk desk-to-desk and get stamped; scrub any case's story.

- Palette: floor `#232821` · folder `#D8C093` · paper `#F1EAD8` · ink `#33302A` · stamp-red
  `#A93226` · approval `#4F6B4A`. Color lives in stamps and folders, not chrome.
- Type: Oswald (stamp caps, desk labels) + IBM Plex Mono (ledger/typewriter data).
- Signature element: **the guardrail door** — folders travel desk → door → next desk; pass shows a
  green tick at the door, a fail slams the red QUARANTINED stamp. FILED stamps at the out tray.
- Motion respects `prefers-reduced-motion`; keyboard-focusable scrubber.
- Load sequence (gap-free): backlog fetch → render → `EventSource('?after=' + cursor)` →
  `lastEventId <= lastAppliedSeq` guard → terminal stamps and re-enables Run.
- Replay picker folds the case list from events (group by request_id, last status wins).

## Testing

- httpx `ASGITransport` for routes; the tail generator tested HTTP-free.
- Stream test asserts backfill frames, `id:` per message, `Last-Event-ID` resume, and the
  no-gap property (events appended between backlog read and stream open arrive exactly once).
- Runner tests: FakeLLM run produces events; repeat POST is idempotent; raising factory →
  `error`/`FAILED` event.
- Frontend: smoke test that `/` serves HTML; visuals verified against a live run.
