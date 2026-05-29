const stateUrl = "/api/state";
const rulesUrl = "/api/rules";
const settingsUrl = "/api/settings";
const weeklyAnalyticsUrl = "/api/analytics/weekly";
const monthlyAnalyticsUrl = "/api/analytics/monthly";
const todayTasksUrl = "/api/tasks/today";
const taskSummaryUrl = "/api/tasks/summary";
let analyticsRange = "weekly";
const svgNamespace = "http://www.w3.org/2000/svg";

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
      if (input.type === "checkbox") {
        input.checked = Boolean(Number(value));
      } else {
        input.value = value;
      }
    }
  });
}

function renderStrictStatus(settings) {
  const enabled = Boolean(Number(settings.strict_earned_access_enabled));
  const startMinutes = Number(settings.strict_daily_start_balance_minutes || 0);
  document.getElementById("strict-status").textContent = enabled
    ? `Strict mode: today starts at ${startMinutes} min.`
    : "Strict mode is off: unused balance can carry over.";
}

function shortDateLabel(dateText) {
  const date = new Date(`${dateText}T00:00:00`);
  return date.toLocaleDateString(undefined, { weekday: "short" });
}

function compactDateLabel(dateText) {
  const date = new Date(`${dateText}T00:00:00`);
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function renderWeeklyChart(days) {
  const svg = document.getElementById("weekly-chart");
  const labels = document.getElementById("weekly-chart-labels");
  const width = 700;
  const height = 220;
  const padding = 28;
  const values = days.map((day) => Number(day.productive_hours || 0));
  const max = Math.max(1, ...values);
  const step = days.length > 1 ? (width - padding * 2) / (days.length - 1) : 0;

  const points = values.map((value, index) => {
    const x = padding + index * step;
    const y = height - padding - (value / max) * (height - padding * 2);
    return { x, y, value };
  });

  const pointString = points.map((point) => `${point.x},${point.y}`).join(" ");
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.replaceChildren();

  [0, 0.5, 1].forEach((ratio) => {
    const y = height - padding - ratio * (height - padding * 2);
    const line = document.createElementNS(svgNamespace, "line");
    line.setAttribute("class", "chart-grid");
    line.setAttribute("x1", padding);
    line.setAttribute("y1", y);
    line.setAttribute("x2", width - padding);
    line.setAttribute("y2", y);
    svg.appendChild(line);
  });

  const polyline = document.createElementNS(svgNamespace, "polyline");
  polyline.setAttribute("class", "chart-line");
  polyline.setAttribute("points", pointString);
  svg.appendChild(polyline);

  const pointGroup = document.createElementNS(svgNamespace, "g");
  pointGroup.setAttribute("class", "chart-points");
  points.forEach((point) => {
    const circle = document.createElementNS(svgNamespace, "circle");
    const title = document.createElementNS(svgNamespace, "title");
    circle.setAttribute("cx", point.x);
    circle.setAttribute("cy", point.y);
    circle.setAttribute("r", 4);
    title.textContent = `${point.value.toFixed(2)} hours`;
    circle.appendChild(title);
    pointGroup.appendChild(circle);
  });
  svg.appendChild(pointGroup);

  const labelEvery = days.length > 10 ? 5 : 1;
  labels.style.gridTemplateColumns = `repeat(${days.length}, 1fr)`;
  labels.replaceChildren();
  days.forEach((day, index) => {
    const showLabel = index === 0 || index === days.length - 1 || index % labelEvery === 0;
    const label = days.length > 10 ? compactDateLabel(day.date) : shortDateLabel(day.date);
    const span = document.createElement("span");
    span.textContent = showLabel ? label : "";
    labels.appendChild(span);
  });
}

function renderWeeklyAnalytics(analytics) {
  const isMonthly = analyticsRange === "monthly";
  document.getElementById("analytics-title").textContent = isMonthly
    ? "Monthly Study Hours"
    : "Weekly Study Hours";
  document.getElementById("analytics-subtitle").textContent = isMonthly
    ? "Last 30 days of productive browser time."
    : "Last 7 days of productive browser time.";
  renderWeeklyChart(analytics.days);
  document.getElementById("weekly-productive").textContent = format(analytics.totals.productive_hours);
  document.getElementById("weekly-timepass").textContent = format(analytics.totals.timepass_hours);
  document.getElementById("weekly-neutral").textContent = format(analytics.totals.neutral_hours);
}

function renderTasks(tasks) {
  const list = document.getElementById("task-list");
  list.innerHTML = "";
  tasks.tasks.forEach((task) => {
    const item = document.createElement("li");
    const label = document.createElement("label");
    const checkbox = document.createElement("input");
    const title = document.createElement("span");
    checkbox.type = "checkbox";
    checkbox.checked = task.completed;
    checkbox.addEventListener("change", async () => {
      await requestJson(todayTasksUrl, {
        method: "POST",
        body: JSON.stringify({ task_id: task.id, completed: checkbox.checked }),
      });
      await refreshTasks();
    });
    title.textContent = task.title;
    label.append(checkbox, title);
    item.appendChild(label);
    list.appendChild(item);
  });

  document.getElementById("task-progress").textContent = `${tasks.completed_count} / ${tasks.total_count}`;
  document.getElementById("task-percent").textContent = `${tasks.completion_percent}%`;
  document.getElementById("completion-fill").style.width = `${tasks.completion_percent}%`;
}

function renderTaskSummary(summary) {
  document.getElementById("best-day").textContent = shortDateLabel(summary.best_day.date);
  document.getElementById("weekly-task-percent").textContent = `${summary.weekly_completion_percent}%`;
}

async function refreshTasks() {
  const [tasks, summary] = await Promise.all([
    requestJson(todayTasksUrl),
    requestJson(taskSummaryUrl),
  ]);
  renderTasks(tasks);
  renderTaskSummary(summary);
}

async function refresh() {
  try {
    const analyticsUrl = analyticsRange === "monthly" ? monthlyAnalyticsUrl : weeklyAnalyticsUrl;
    const [state, analytics, tasks, summary] = await Promise.all([
      requestJson(stateUrl),
      requestJson(analyticsUrl),
      requestJson(todayTasksUrl),
      requestJson(taskSummaryUrl),
    ]);
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
    renderStrictStatus(state.settings);
    renderWeeklyAnalytics(analytics);
    renderTasks(tasks);
    renderTaskSummary(summary);
  } catch (error) {
    console.error(error);
    document.getElementById("active-site").textContent = `Dashboard refresh failed: ${error.message}`;
  }
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
  const form = event.currentTarget;
  new FormData(form).forEach((value, key) => {
    payload[key] = Number(value);
  });
  payload.strict_earned_access_enabled = form.elements.strict_earned_access_enabled.checked ? 1 : 0;
  await requestJson(settingsUrl, {
    method: "POST",
    body: JSON.stringify(payload),
  });
  await refresh();
});

document.querySelectorAll(".range-toggle button").forEach((button) => {
  button.addEventListener("click", async () => {
    analyticsRange = button.dataset.range;
    document.querySelectorAll(".range-toggle button").forEach((item) => {
      item.classList.toggle("active", item.dataset.range === analyticsRange);
    });
    await refresh();
  });
});

refresh();
setInterval(refresh, 15000);
