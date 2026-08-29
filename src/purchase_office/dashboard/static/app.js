"use strict";

/* Records Room client: folds the audit trail into a live office floor and a
   scrubbable timeline. The server stream is the only live input. */

const ROUTE = ["watcher", "procurement", "legal", "finance", "compliance"];
const TERMINAL_ACTIONS = ["status", "error"];

const state = {
  bySeq: new Map(),
  cases: new Map(), // request_id -> { seqs: [], terminal: event|null }
  currentCase: null,
  live: true,
  scrubIndex: 0,
};

const $ = (sel) => document.querySelector(sel);

function setConnection(state_name) {
  $("#connection").dataset.state = state_name;
  $("#connection").textContent = state_name.toUpperCase();
}

function ingest(event) {
  if (state.bySeq.has(event.seq)) return;
  state.bySeq.set(event.seq, event);
  let entry = state.cases.get(event.request_id);
  if (!entry) {
    entry = { seqs: [], terminal: null };
    state.cases.set(event.request_id, entry);
  }
  entry.seqs.push(event.seq);
  if (TERMINAL_ACTIONS.includes(event.action)) entry.terminal = event;
  if (!state.currentCase) state.currentCase = event.request_id;
}

function caseEvents(entry) {
  return entry.seqs.map((seq) => state.bySeq.get(seq));
}

function asOfEvents() {
  const entry = state.cases.get(state.currentCase);
  if (!entry) return [];
  const events = caseEvents(entry);
  return state.live ? events : events.slice(0, state.scrubIndex + 1);
}

/* ---- floor ---- */

function buildFloor() {
  const floor = $("#floor");
  floor.innerHTML = "";
  ROUTE.forEach((role) => {
    const desk = document.createElement("div");
    desk.className = "desk";
    desk.dataset.role = role;
    desk.dataset.label = "desk";
    desk.textContent = role;
    floor.append(desk);

    const door = document.createElement("div");
    door.className = "door";
    door.dataset.after = role;
    door.title = "guardrail screen";
    floor.append(door);
  });
  const tray = document.createElement("div");
  tray.className = "tray";
  tray.id = "tray";
  tray.textContent = "out tray";
  floor.append(tray);
}

function renderFloor(events) {
  let folderAt = null;
  let rejected = false;
  const doors = {};
  const verdicts = {};

  for (const e of events) {
    if (e.action === "enter") folderAt = e.role;
    if (e.action === "screen" && folderAt) doors[folderAt] = e.status;
    if (e.action === "verdict") verdicts[e.role] = e.status;
    if (e.action === "status" && e.status === "FILED") folderAt = "tray";
    if (e.action === "verdict" && e.status === "reject") rejected = true;
  }

  document.querySelectorAll(".desk").forEach((desk) => {
    const role = desk.dataset.role;
    desk.classList.toggle("active", folderAt === role);
    const cleared = verdicts[role] === "approve" || doors[role] === "pass";
    desk.classList.toggle("done", cleared);
    desk.classList.toggle("rejected", verdicts[role] === "reject");
  });

  document.querySelectorAll(".door").forEach((door) => {
    const status = doors[door.dataset.after];
    door.classList.toggle("pass", status === "pass");
    door.classList.toggle("fail", status === "fail");
    door.textContent = status === "pass" ? "✓" : status === "fail" ? "✕" : "";
  });

  $("#tray").classList.toggle("lit", folderAt === "tray");
  return { rejected };
}

/* ---- case file folder ---- */

function renderFolder(events) {
  const body = $("#folder-body");
  const empty = $("#folder-empty");
  const stamp = $("#stamp");
  const entry = state.cases.get(state.currentCase);

  if (!entry || events.length === 0) {
    body.hidden = true;
    empty.hidden = false;
    empty.textContent = state.currentCase
      ? "Raising a request…"
      : "The floor is quiet. Run a case.";
    stamp.hidden = true;
    $("#case-ref").textContent = state.currentCase ? `№ ${state.currentCase}` : "";
    return;
  }

  empty.hidden = true;
  body.hidden = false;
  $("#case-ref").textContent = `№ ${state.currentCase}`;

  const raised = events.find((e) => e.action === "enter" && e.role === "watcher");
  $("#request-line").textContent = raised ? raised.detail : "";

  const slips = $("#slips");
  slips.innerHTML = "";
  for (const e of events) {
    if (e.action === "verdict") {
      const slip = document.createElement("div");
      slip.className = `slip verdict-${e.status}`;
      slip.innerHTML =
        `<span class="slip-role">${e.role}</span>` +
        `<span class="verdict">${e.status === "approve" ? "APPROVED" : "REJECTED"}</span>` +
        (e.detail ? ` — ${e.detail}` : "");
      slips.append(slip);
    }
    if (e.action === "writeup") {
      const slip = document.createElement("div");
      slip.className = "slip writeup";
      slip.innerHTML =
        `<span class="slip-role">write-up</span>` +
        `<span>${e.detail || "screen failed"}</span>`;
      slips.append(slip);
    }
  }

  const terminal = events.find((e) => TERMINAL_ACTIONS.includes(e.action));
  if (terminal) {
    const kind = terminal.status.toLowerCase();
    stamp.className = `stamp ${kind}`;
    stamp.textContent = terminal.status;
    stamp.hidden = false;
  } else {
    stamp.hidden = true;
  }
}

/* ---- timeline ---- */

function renderLedger(events) {
  const ledger = $("#ledger");
  ledger.innerHTML = "";
  for (const e of events) {
    const li = document.createElement("li");
    const when = new Date(e.ts);
    const clock = isNaN(when) ? e.ts : when.toTimeString().slice(0, 8);
    li.innerHTML =
      `<span class="seq">${e.seq}</span>` +
      `<span class="when">${clock}</span>` +
      `<span class="who">${e.role}</span>` +
      `<span class="what ${e.status.toLowerCase()}">${e.action}</span>` +
      `<span class="note">${e.detail || ""}</span>`;
    ledger.append(li);
  }
  ledger.scrollTop = ledger.scrollHeight;
}

function renderPicker() {
  const picker = $("#case-picker");
  picker.innerHTML = "";
  const ids = [...state.cases.keys()].reverse();
  for (const id of ids) {
    const entry = state.cases.get(id);
    const option = document.createElement("option");
    option.value = id;
    const mark = entry.terminal ? entry.terminal.status : "in progress";
    option.textContent = `${id} — ${mark}`;
    picker.append(option);
  }
  if (state.currentCase && ids.includes(state.currentCase)) {
    picker.value = state.currentCase;
  }
}

function renderScrubber(events) {
  const scrubber = $("#scrubber");
  scrubber.disabled = events.length === 0;
  scrubber.max = Math.max(events.length - 1, 0);
  if (state.live) {
    scrubber.value = scrubber.max;
  } else {
    scrubber.value = Math.min(state.scrubIndex, scrubber.max);
  }
}

function render() {
  renderPicker();
  const events = asOfEvents();
  renderFloor(events);
  renderFolder(events);
  renderLedger(events);
  renderScrubber(events);
  const entry = state.cases.get(state.currentCase);
  const busy = entry ? !entry.terminal : false;
  $("#run").disabled = busy && state.live;
}

/* ---- controls ---- */

let runInFlight = false;

$("#run").addEventListener("click", async () => {
  if (runInFlight) return;
  runInFlight = true;
  $("#run").disabled = true;
  const response = await fetch("/api/runs", { method: "POST" });
  const body = await response.json();
  state.currentCase = body.request_id;
  state.live = true;
  $("#live-btn").setAttribute("aria-pressed", "true");
  runInFlight = false;
  render();
});

$("#live-btn").addEventListener("click", () => {
  state.live = !state.live;
  $("#live-btn").setAttribute("aria-pressed", String(state.live));
  if (!state.live) {
    const events = caseEvents(state.cases.get(state.currentCase));
    state.scrubIndex = Math.max(events.length - 1, 0);
  }
  render();
});

$("#scrubber").addEventListener("input", (e) => {
  state.live = false;
  $("#live-btn").setAttribute("aria-pressed", "false");
  state.scrubIndex = Number(e.target.value);
  render();
});

$("#case-picker").addEventListener("change", (e) => {
  state.currentCase = e.target.value;
  state.live = true;
  $("#live-btn").setAttribute("aria-pressed", "true");
  render();
});

/* ---- boot ---- */

function connectStream(cursor) {
  const source = new EventSource(`/api/stream?after=${cursor}`);
  source.addEventListener("audit", (e) => {
    setConnection("live");
    ingest(JSON.parse(e.data));
    render();
  });
  source.onerror = () => setConnection("reconnecting");
}

async function boot() {
  buildFloor();
  const response = await fetch("/api/events");
  const backlog = await response.json();
  backlog.events.forEach(ingest);
  setConnection("live");
  connectStream(backlog.cursor);
  render();
}

boot();
