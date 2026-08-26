# Purchase Office

A small office of autonomous agents that handles a purchase request from noticing to filing. The Watcher notices stock running low and raises a request; the Orchestrator routes the request from desk to desk; four specialist roles each issue a verdict; a Guardrail screens every verdict; everything is recorded in an Audit Trail.

## Language

**Purchase Request**:
The artifact the Watcher raises when stock runs low. Names what is needed, how much, and why. One artifact flows from desk to desk until it is filed or quarantined.
_Avoid_: order, PO, ticket

**Case File**:
The folder that follows the request: the request itself, every verdict, every write-up, and the audit trail. Every role reads it and appends to it.
_Avoid_: memory bank, state, ticket

**Watcher**:
The role that observes stock levels and raises a Purchase Request on its own — nobody tells it to.
_Avoid_: monitor, cron, stock clerk

**Orchestrator**:
The mechanism that routes the Case File from role to role in the order the Registry defines. It does no specialist work itself.
_Avoid_: workflow engine, manager

**Registry**:
The staff directory: each role's place in the route, its identity, its clearance, and its guardrail policy. The Orchestrator reads it to know who is on the team and what each may handle.
_Avoid_: config, settings

**Role**:
A desk in the office: Watcher, Procurement, Legal, Finance, Compliance.
_Avoid_: agent, department, step

**Identity**:
A role's own API key. Each role is constructed with its own, so no role holds another's.
_Avoid_: credentials, account, user

**Clearance**:
What a role may touch: its whitelisted tools and the Case File fields it may read.
_Avoid_: permissions, scopes, access rights

**Verdict**:
A role's judgement on the request — approve or reject — appended to the Case File.
_Avoid_: decision, opinion

**Guardrail**:
The checkpoint every Verdict passes through on its way into the Case File. Runs the screens; on failure, writes a Write-up and quarantines the case.
_Avoid_: security guard, validator, middleware

**Screen**:
One Guardrail check. Three exist: injection, PII, role-policy.
_Avoid_: check, test, filter

**Write-up**:
The Guardrail's incident report when a screen fails. Records what was found, where, and why it matters.
_Avoid_: flag, alert, report

**Quarantined**:
The terminal status of a case the Guardrail stopped. A case is either filed or quarantined — nothing else.
_Avoid_: blocked, halted

**Implant**:
A deliberate vulnerability seeded into demo data that the Guardrail is meant to catch. Proves the Guardrail works when the demo runs.
_Avoid_: attack, bug, easter egg

**Audit Trail**:
The immutable, timestamped record of who touched the case, in what order, and what they decided. Every verdict, screen result, and write-up is appended and never rewritten.
_Avoid_: logs, event stream
