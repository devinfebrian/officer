# Purchase Office — Product Requirements Document

**Status:** Draft v1
**Date:** 2026-08-26
**Companion docs:** [Technical design spec](superpowers/specs/2026-08-26-purchase-office-design.md) · [Domain glossary](../../CONTEXT.md)

---

## 1. Overview

Purchase Office is an autonomous procurement system: a small office of specialist agents that takes a purchase request from noticing to filing with no human in the loop. A Watcher role notices when stock is running low and raises a Purchase Request on its own. An Orchestrator routes the request desk-to-desk through four specialist Roles — Procurement, Legal, Finance, Compliance — each of which issues an approve/reject Verdict. A Guardrail screens every Verdict for prompt injection, PII leakage, and role-policy violations before it enters the Case File. Every action is appended to an immutable Audit Trail that can be replayed end to end.

The product's three pillars:

1. **Autonomous** — the office works while the humans sleep; nobody needs to prompt it.
2. **Least-privilege by construction** — each Role has its own Identity (API key) and Clearance (tools + data it may touch), so no department can see what it shouldn't.
3. **Auditable** — every touch, decision, and security catch is recorded and replayable.

## 2. Problem Statement

Procurement today is slow, manual, and opaque:

- **Slow.** A stock-out notice waits for a human to notice, draft a request, and chase approvals across departments.
- **Opaque.** When a purchase is approved, nobody can easily answer *"how did this get approved, and who decided what?"* The trail lives in inboxes, spreadsheets, and memory.
- **Unsafe.** Multi-agent AI systems are vulnerable to prompt injection — a malicious instruction hidden in vendor-supplied text — and to accidental leakage of sensitive data between departments.
- **Uncontrolled.** Departments routinely see more than they should. Legal has no business reading budget figures; Finance has no business in sanctions data. In a real company, that is a compliance risk.

Purchase Office addresses all four: it notices needs automatically, routes work deterministically, screens every message at the door, and records the whole story.

## 3. Target Users / Personas

| Persona | Who they are | What they need |
|---|---|---|
| **Operations Lead** (the Watcher's user) | Owns inventory and continuity | Stock never silently runs out; replenishment is triggered automatically, not when someone happens to check |
| **Finance Lead** | Owns budget and spend control | No purchase lands without a budget check; every approved purchase is traceable to a quote and a budget line |
| **Compliance Officer** | Owns vendor risk | No business is done with a vendor on the do-not-do-business list; guardrail catches are recorded as incident write-ups |
| **Internal Auditor** | Owns the paper trail | Can replay *exactly* how any purchase was approved: who touched it, in what order, what they decided |
| **Engineering / Platform team** | Integrates and runs the office | Clear contracts between roles, deterministic behavior, and a system that is testable and re-runnable |

## 4. User Stories

- As an **Operations Lead**, I want the Watcher to notice low stock and raise a Purchase Request on its own, so replenishment starts without me monitoring dashboards.
- As a **Finance Lead**, I want every purchase checked against the budget before it is approved, so no spend exceeds the envelope.
- As a **Compliance Officer**, I want every vendor checked against the do-not-do-business list, so we never transact with a sanctioned party.
- As an **Internal Auditor**, I want to replay the full trail of any purchase, so I can answer "how did this get approved?" without digging through email.
- As an **Engineering team**, I want each Role constructed with its own Identity and Clearance, so Legal literally cannot reach Finance's data.
- As a **Security team**, I want every message between roles screened for injection, PII, and policy violations, so a poisoned vendor document cannot steer the office.

## 5. Goals & Non-Goals

**Goals (v1):**

- G1. A single purchase request flows end to end autonomously: Watcher → Procurement → Legal → Finance → Compliance.
- G2. Each Role is isolated by Identity (own API key) and Clearance (own tools + readable Case File fields).
- G3. Every inter-role message passes the Guardrail's three screens: injection, PII, role-policy.
- G4. A guardrail catch produces a Write-up and a Quarantined terminal state.
- G5. The full lifecycle is recorded in an immutable Audit Trail and replayable on a live dashboard.

**Non-Goals (v1):**

- Human-in-the-loop approval (a person approving each step).
- Rework loops (a REJECT routes back for a new vendor).
- Real purchasing integrations (no actual money moves).
- Multi-request concurrency or load.
- Multi-tenant auth or user accounts.

## 6. Success Metrics

**Product metrics:**

- **Run-to-completion rate:** ≥95% of Purchase Requests filed (all four Verdicts approve) with zero human intervention.
- **Guardrail recall on implants:** 100% of seeded attacks (the Implant) caught by a Screen.
- **Guardrail precision:** <5% false positives on clean vendor documents.
- **Audit coverage:** 100% of state transitions, Verdicts, and Screen results recorded in the Audit Trail.
- **Time-to-file:** a request goes from raised to filed in minutes, not days.

**Demo metrics (hackathon):**

- **Press-play autonomy:** the entire run completes with no human input.
- **Live catch:** the Implant is flagged on screen the moment it reaches Legal.
- **Replayability:** a judge can scrub the timeline and see who touched the case, in what order, and what they decided.

## 7. Functional Requirements

### 7.1 The Watcher (noticing)

- **FR-1.** The Watcher polls inventory (a seeded store) and detects when an item's stock is at or below its reorder threshold.
- **FR-2.** On detection, the Watcher raises a Purchase Request naming the item, quantity, and trigger reason, and places it on the office floor — nobody instructed it to.

### 7.2 The Orchestrator & Registry (routing)

- **FR-3.** The Registry is a declarative config defining each Role's place in the route, its Identity, its Clearance, and the Guardrail policy.
- **FR-4.** The Orchestrator builds the route from the Registry — never from hardcoded logic — and routes the Case File desk-to-desk in the defined order.
- **FR-5.** The route is `watcher → procurement → legal → finance → compliance → done`.

### 7.3 The Specialist Roles (verdicts)

- **FR-6.** Procurement selects a vendor and appends the vendor + quote to the Case File.
- **FR-7.** Legal reads the contract, checks it against standard clauses, and issues a Verdict.
- **FR-8.** Finance checks the quote against the budget and issues a Verdict.
- **FR-9.** Compliance checks the vendor against the do-not-do-business list and issues a Verdict.
- **FR-10.** A Verdict is strictly approve or reject. The first REJECT ends the case with REJECTED status.

### 7.4 Identity & Clearance (isolation)

- **FR-11.** Each Role is constructed with its own Gemini API key (env: `AGENT_WATCHER_KEY`, `AGENT_PROCUREMENT_KEY`, …). No Role holds another's key.
- **FR-12.** Each Role receives only its whitelisted tools and a state projection — the Case File restricted to the fields its Clearance permits.
- **FR-13.** A Role can write only to its own `verdicts[<role>]` slot. Isolation is enforced at construction time.

### 7.5 The Guardrail (the door)

- **FR-14.** Every inter-role message passes through the Guardrail before entering the Case File.
- **FR-15.** The Guardrail runs three Screens in order: **injection** (blocklist + LLM classifier), **PII** (regex/entity detection), **role-policy** (declarative content-category table).
- **FR-16.** On a Screen failure, the Guardrail writes a **Write-up** (what, where, why) into the Case File and transitions the case to **QUARANTINED**.

### 7.6 Memory Bank & Observability (the record)

- **FR-17.** The Case File is persisted (LangGraph checkpointer), so the run can resume across days and every Role sees prior Verdicts.
- **FR-18.** Every event — state transition, message, Screen result, Verdict, Write-up — is appended to a SQLite Audit Trail: `{timestamp, role, action, status, detail}`. Append-only.
- **FR-19.** A live dashboard streams events over SSE with two views: a live office floor and a scrubbable replay timeline.

### 7.7 The Implant (demo proof)

- **FR-20.** Demo seed data includes a poisoned vendor proposal containing a hidden injected instruction and a stray PII field. The Guardrail must catch it when it reaches Legal.

## 8. Non-Functional Requirements

- **NFR-1 Security.** Least privilege by construction; no Role can read or invoke another Role's tools or data. Keys are environment-injected, never committed.
- **NFR-2 Observability.** 100% audit coverage of state transitions, Verdicts, and Screen results.
- **NFR-3 Reliability.** LLM/tool failures retry with backoff, then transition to FAILED with the failure captured in the Audit Trail. The run is re-runnable from the last checkpoint.
- **NFR-4 Performance.** A full run completes in minutes (demo target); the dashboard stays responsive streaming events live.
- **NFR-5 Portability.** The LLM layer is provider-agnostic behind a thin interface so keys can be swapped on demo day.

## 9. Scope & Out of Scope

**In scope (v1):** the five-role office, Registry-driven routing, Identity + Clearance isolation, three-screen Guardrail, Case File persistence, Audit Trail, live dashboard, seeded Implant, seed script.

**Out of scope (v1):** human approvals, rework loops, real money movement, concurrency, multi-tenancy, model fine-tuning, mobile UI.

## 10. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| LLM variance → flaky demo Verdicts | Deterministic seed data, tightly-scoped prompts, fake-LLM integration tests, retry/backoff |
| Guardrail false positives on clean docs | Deterministic checks run first; LLM classifier only for ambiguous text; precision metric tracked |
| Demo fails on live network/API | Seed script pre-loads everything; LLM is the only live dependency; provider-agnostic key swap |
| Gemini rate limits | Retry with backoff; small number of LLM calls per run |
| Scope creep into "real" procurement | Non-goals explicitly listed; v1 is a demo of the architecture, not a purchasing system |

## 11. Milestones (build order)

1. **M1 — Registry + graph skeleton.** Registry config, typed Case File state, LangGraph graph with the five-role route wired from the Registry.
2. **M2 — Roles with Identity & Clearance.** Per-role key injection, tool whitelists, state projections, verdict writing.
3. **M3 — Guardrail screens.** Injection, PII, role-policy checkers; Write-up + QUARANTINED transition.
4. **M4 — Memory Bank & Audit Trail.** Checkpointer persistence, SQLite event log.
5. **M5 — Dashboard.** FastAPI + SSE, live office floor, replay timeline.
6. **M6 — Implant, seed, polish.** Poisoned vendor, seed script, end-to-end demo run, `python demo.py` press-play.

## 12. Glossary

Domain terms are defined in [CONTEXT.md](../../CONTEXT.md). Key ones: Purchase Request, Case File, Role, Identity, Clearance, Verdict, Guardrail, Screen, Write-up, Quarantined, Implant, Audit Trail.
