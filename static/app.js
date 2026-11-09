// SecondLang front-end: talks to the FastAPI backend under /api.
const $ = (sel) => document.querySelector(sel);

const els = {
  input: $("#input"), context: $("#context"), count: $("#count"), refine: $("#refine"),
  error: $("#error"), empty: $("#empty"), output: $("#output"), refined: $("#refined"),
  diff: $("#diff"), corrections: $("#corrections"), ccount: $("#ccount"), tip: $("#tip"),
  badge: $("#tone-badge"), copy: $("#copy"), provider: $("#provider"),
  stats: $("#stats"), history: $("#history"), clear: $("#clear"),
};

const store = {
  get(key, fallback) { try { return localStorage.getItem(key) ?? fallback; } catch { return fallback; } },
  set(key, value) { try { localStorage.setItem(key, value); } catch { /* storage unavailable */ } },
};

let tone = store.get("secondlang.tone", "formal");

// ---------- helpers ----------
async function api(path, options = {}) {
  const res = await fetch(path, { headers: { "Content-Type": "application/json" }, ...options });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    let msg = data.detail ?? `Request failed (${res.status})`;
    if (Array.isArray(msg)) msg = msg.map((d) => d.msg.replace(/^Value error, /, "")).join(" ");
    throw new Error(msg);
  }
  return data;
}

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v;
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v);
  }
  for (const c of children) if (c != null) node.append(c);
  return node;
}

function showError(msg) {
  els.error.textContent = msg;
  els.error.hidden = !msg;
}

function timeAgo(iso) {
  const s = (Date.now() - new Date(iso).getTime()) / 1000;
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)} min ago`;
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`;
  return new Date(iso).toLocaleDateString();
}

const label = (type) => type.replace("_", " ");

// ---------- tone ----------
function setTone(next) {
  tone = next;
  store.set("secondlang.tone", tone);
  document.body.classList.toggle("tone-family", tone === "family");
  document.querySelectorAll(".tone").forEach((b) =>
    b.setAttribute("aria-checked", String(b.dataset.tone === tone)));
}
document.querySelectorAll(".tone").forEach((b) => b.addEventListener("click", () => setTone(b.dataset.tone)));

// ---------- rendering ----------
function renderResult(r) {
  els.empty.hidden = true;
  els.output.hidden = false;
  els.refined.textContent = r.refined;
  els.badge.textContent = r.tone;
  els.badge.style.background = r.tone === "family" ? "var(--family-soft)" : "var(--formal-soft)";
  els.badge.style.color = r.tone === "family" ? "var(--family)" : "var(--formal)";

  els.diff.replaceChildren(...r.diff.map((s) =>
    s.op === "equal" ? document.createTextNode(s.text) : el(s.op === "insert" ? "ins" : "del", {}, s.text)));

  els.ccount.textContent = r.corrections.length ? `(${r.corrections.length})` : "";
  els.corrections.replaceChildren(...(r.corrections.length
    ? r.corrections.map((c) => el("li", {},
        el("div", { class: "change" },
          el("span", { class: "tag" }, label(c.type)),
          ...(c.original
            ? [el("del", {}, c.original), " → ", el("ins", {}, c.corrected)]
            : [el("span", { class: "rule" }, c.corrected)])),
        c.explanation ? el("p", {}, c.explanation) : null))
    : [el("li", {}, "No mistakes found. Nicely written!")]));

  els.tip.hidden = !r.tip;
  els.tip.textContent = r.tip || "";
}

function renderStats(s) {
  const entries = Object.entries(s.by_type);
  if (!entries.length) {
    els.stats.replaceChildren(el("p", { class: "muted" },
      s.total ? "No mistakes recorded yet." : "No data yet."));
    return;
  }
  const max = Math.max(...entries.map(([, n]) => n));
  els.stats.replaceChildren(...entries.slice(0, 6).map(([type, n]) =>
    el("div", { class: "bar" },
      el("span", {}, label(type)),
      el("div", { class: "bar-track" }, el("div", { class: "bar-fill", style: `width:${(n / max) * 100}%` })),
      el("span", { class: "bar-n" }, String(n)))));
}

function renderHistory(items) {
  if (!items.length) {
    els.history.replaceChildren(el("li", { class: "muted", style: "cursor:default" }, "Nothing yet."));
    return;
  }
  els.history.replaceChildren(...items.map((item) => el("li", {
      title: "Open",
      onclick: () => {
        els.input.value = item.original;
        els.context.value = item.context || "";
        updateCount();
        setTone(item.tone);
        renderResult(item);
      },
    },
    el("span", { class: `dot ${item.tone}` }),
    el("div", { class: "h-body" },
      el("div", { class: "h-text" }, item.refined),
      el("div", { class: "h-meta" },
        `${item.tone} · ${item.corrections.length} fix${item.corrections.length === 1 ? "" : "es"} · ${timeAgo(item.created_at)}`)),
    el("button", {
      class: "del-btn", "aria-label": "Delete", title: "Delete",
      onclick: async (e) => {
        e.stopPropagation();
        await api(`/api/history/${item.id}`, { method: "DELETE" }).catch((err) => showError(err.message));
        refreshSide();
      },
    }, "×"))));
}

async function refreshSide() {
  try {
    const [history, stats] = await Promise.all([api("/api/history?limit=50"), api("/api/stats")]);
    renderHistory(history);
    renderStats(stats);
  } catch (err) {
    showError(err.message);
  }
}

// ---------- actions ----------
function updateCount() {
  els.count.textContent = `${els.input.value.length} / 5000`;
}

async function refine() {
  const text = els.input.value.trim();
  if (!text) { showError("Please type some text to refine."); els.input.focus(); return; }
  showError("");
  els.refine.disabled = true;
  els.refine.firstChild.textContent = "Refining… ";
  try {
    const result = await api("/api/refine", {
      method: "POST",
      body: JSON.stringify({ text, tone, context: els.context.value.trim() || null }),
    });
    renderResult(result);
    refreshSide();
  } catch (err) {
    showError(err.message);
  } finally {
    els.refine.disabled = false;
    els.refine.firstChild.textContent = "Refine ";
  }
}

els.refine.addEventListener("click", refine);
els.input.addEventListener("input", updateCount);
els.input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); refine(); }
});

els.copy.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(els.refined.textContent);
    els.copy.textContent = "Copied!";
  } catch {
    els.copy.textContent = "Copy failed";
  }
  setTimeout(() => (els.copy.textContent = "Copy"), 1500);
});

els.clear.addEventListener("click", async () => {
  if (!els.history.querySelector(".del-btn")) return;
  els.clear.textContent = els.clear.dataset.armed ? "Clear all" : "Click again to confirm";
  if (!els.clear.dataset.armed) {
    els.clear.dataset.armed = "1";
    setTimeout(() => { delete els.clear.dataset.armed; els.clear.textContent = "Clear all"; }, 3000);
    return;
  }
  delete els.clear.dataset.armed;
  await api("/api/history", { method: "DELETE" }).catch((err) => showError(err.message));
  refreshSide();
});

// ---------- start ----------
setTone(tone);
updateCount();
api("/api/health")
  .then((h) => {
    els.provider.textContent = `${h.provider} · ${h.model}`;
    if (h.provider === "offline") {
      els.provider.classList.add("warn");
      els.provider.title = "Offline mode fixes only common mistakes. Set LLM_PROVIDER in .env for full rewrites.";
    }
  })
  .catch(() => { els.provider.textContent = "backend not reachable"; els.provider.classList.add("warn"); });
refreshSide();
