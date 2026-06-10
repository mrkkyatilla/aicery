const STORAGE_KEY = "aicery_tenant_api_key";

function $(id) {
  return document.getElementById(id);
}

function show(el, visible) {
  el.classList.toggle("hidden", !visible);
}

function formatNum(n) {
  return new Intl.NumberFormat().format(Math.round(n));
}

function pct(used, limit) {
  if (!limit || limit <= 0) return 0;
  return Math.min(100, (used / limit) * 100);
}

function setBar(fillEl, used, limit) {
  const p = pct(used, limit);
  fillEl.style.width = `${p}%`;
  fillEl.classList.remove("warn", "danger");
  if (p >= 90) fillEl.classList.add("danger");
  else if (p >= 70) fillEl.classList.add("warn");
}

async function api(path, options = {}) {
  const key = localStorage.getItem(STORAGE_KEY);
  if (!key) throw new Error("No API key saved");
  const headers = {
    "Content-Type": "application/json",
    "X-Api-Key": key,
    ...(options.headers || {}),
  };
  const res = await fetch(path, { ...options, headers });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = body.detail || res.statusText;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return body;
}

function renderDashboard(data) {
  $("org-name").textContent = data.name || "Organization";
  $("org-id").textContent = data.org_id;
  const tier = data.tier || "free";
  const badge = $("tier-badge");
  badge.textContent = tier;
  badge.className = "tier-badge " + tier;

  $("sub-status").textContent = data.subscription_status || "inactive";
  $("period-end").textContent = data.current_period_end
    ? new Date(data.current_period_end).toLocaleString()
    : "—";
  $("stripe-customer").textContent = data.stripe_customer_id || "—";

  const usage = data.usage || {};
  const limits = data.limits || {};
  const agentUsed = usage.agent_run || 0;
  const agentLimit = limits.agent_run || 0;
  const tokUsed = usage.llm_tokens_out || 0;
  const tokLimit = limits.llm_tokens_out || 0;

  $("usage-agent-text").textContent = `${formatNum(agentUsed)} / ${formatNum(agentLimit)}`;
  $("usage-tokens-text").textContent = `${formatNum(tokUsed)} / ${formatNum(tokLimit)}`;
  setBar($("bar-agent"), agentUsed, agentLimit);
  setBar($("bar-tokens"), tokUsed, tokLimit);

  show($("dashboard"), true);
  show($("auth-error"), false);
}

async function loadBilling() {
  const errEl = $("auth-error");
  show(errEl, false);
  try {
    const data = await api("/billing/me");
    renderDashboard(data);
  } catch (e) {
    errEl.textContent = e.message;
    show(errEl, true);
    show($("dashboard"), false);
  }
}

async function startCheckout(tier) {
  const errEl = $("checkout-error");
  show(errEl, false);
  try {
    const { url } = await api("/billing/checkout", {
      method: "POST",
      body: JSON.stringify({ tier }),
    });
    if (url) window.location.href = url;
    else throw new Error("No checkout URL returned");
  } catch (e) {
    errEl.textContent = e.message;
    show(errEl, true);
  }
}

function init() {
  const input = $("api-key");
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved) {
    input.value = saved;
    loadBilling();
  }

  $("btn-save-key").addEventListener("click", () => {
    const key = input.value.trim();
    if (!key) return;
    localStorage.setItem(STORAGE_KEY, key);
    loadBilling();
  });

  $("btn-clear-key").addEventListener("click", () => {
    localStorage.removeItem(STORAGE_KEY);
    input.value = "";
    show($("dashboard"), false);
    show($("auth-error"), false);
  });

  $("btn-refresh").addEventListener("click", () => loadBilling());

  document.querySelectorAll("[data-tier]").forEach((btn) => {
    btn.addEventListener("click", () => startCheckout(btn.dataset.tier));
  });
}

init();
