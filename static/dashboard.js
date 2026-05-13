const stateUrl = "/api/state";
const rulesUrl = "/api/rules";
const settingsUrl = "/api/settings";

function format(value) {
  return Number(value || 0).toFixed(1);
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

function renderRules(category, domains) {
  const list = document.getElementById(`${category}-rules`);
  list.innerHTML = "";
  domains.forEach((domain) => {
    const item = document.createElement("li");
    const label = document.createElement("span");
    const button = document.createElement("button");
    label.textContent = domain;
    button.type = "button";
    button.textContent = "x";
    button.title = `Remove ${domain}`;
    button.addEventListener("click", async () => {
      await requestJson(rulesUrl, {
        method: "DELETE",
        body: JSON.stringify({ domain }),
      });
      await refresh();
    });
    item.append(label, button);
    list.appendChild(item);
  });
}

function renderSettings(settings) {
  const form = document.getElementById("settings-form");
  Object.entries(settings).forEach(([key, value]) => {
    const input = form.elements[key];
    if (input) {
      input.value = value;
    }
  });
}

async function refresh() {
  const state = await requestJson(stateUrl);
  document.getElementById("balance").textContent = format(state.balance_minutes);
  document.getElementById("productive").textContent = format(state.today.productive_minutes);
  document.getElementById("timepass").textContent = format(state.today.timepass_minutes);
  document.getElementById("neutral").textContent = format(state.today.neutral_minutes);

  const active = state.active;
  const activeText = active && active.domain
    ? `${active.domain} is ${state.active_category}`
    : "Waiting for browser activity";
  document.getElementById("active-site").textContent = activeText;

  renderRules("productive", state.rules.productive);
  renderRules("timepass", state.rules.timepass);
  renderSettings(state.settings);
}

document.querySelectorAll(".rule-form").forEach((form) => {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const domain = form.elements.domain.value.trim();
    if (!domain) {
      return;
    }
    await requestJson(rulesUrl, {
      method: "POST",
      body: JSON.stringify({ domain, category: form.dataset.category }),
    });
    form.reset();
    await refresh();
  });
});

document.getElementById("settings-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = {};
  new FormData(event.currentTarget).forEach((value, key) => {
    payload[key] = Number(value);
  });
  await requestJson(settingsUrl, {
    method: "POST",
    body: JSON.stringify(payload),
  });
  await refresh();
});

refresh();
setInterval(refresh, 15000);
