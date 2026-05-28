const API_BASE = localStorage.getItem("skillproof_api_base") || "http://127.0.0.1:8000";

const form = document.querySelector("#analyze-form");
const usernameInput = document.querySelector("#username");
const button = document.querySelector("#analyze-button");
const statusEl = document.querySelector("#status");
const resultEl = document.querySelector("#result");
const exportButton = document.querySelector("#export-button");

let currentReport = null;

function setStatus(message, isError = false) {
  statusEl.textContent = message;
  statusEl.style.color = isError ? "#ff8d8d" : "";
}

function listItems(id, items) {
  const el = document.querySelector(id);
  el.innerHTML = "";
  (items.length ? items : ["No public signal yet"]).forEach((item) => {
    const li = document.createElement("li");
    li.textContent = item;
    el.appendChild(li);
  });
}

function renderSkillMap(skillMap) {
  const el = document.querySelector("#skill-map");
  el.innerHTML = "";
  Object.entries(skillMap)
    .sort((a, b) => b[1] - a[1])
    .forEach(([label, value]) => {
      const row = document.createElement("div");
      row.className = "bar";
      row.innerHTML = `
        <span>${label}</span>
        <span class="track"><span class="fill" style="width:${value}%"></span></span>
        <strong>${value}</strong>
      `;
      el.appendChild(row);
    });
}

function renderRepos(repos) {
  const el = document.querySelector("#repos");
  el.innerHTML = "";
  repos.forEach((repo) => {
    const card = document.createElement("div");
    card.className = "repo";
    const tags = [
      ...(repo.project_types || []),
      repo.has_readme ? "README" : "No README",
      repo.has_tests ? "Tests" : "No tests",
      repo.has_live_demo ? "Demo" : null,
      repo.has_docker ? "Docker" : null,
    ].filter(Boolean);
    card.innerHTML = `
      <header>
        <div>
          <h4><a href="${repo.url}" target="_blank" rel="noreferrer">${repo.name}</a></h4>
          <p>${repo.description || "No description provided."}</p>
        </div>
        <strong>${repo.score}/100</strong>
      </header>
      <p>${repo.language || "n/a"} · ${repo.stars} stars · ${repo.forks} forks</p>
      <div class="tags">${tags.map((tag) => `<span class="tag">${tag}</span>`).join("")}</div>
    `;
    el.appendChild(card);
  });
}

function renderReport(report) {
  currentReport = report;
  resultEl.classList.remove("hidden");
  document.querySelector("#avatar").src = report.avatar_url;
  document.querySelector("#result-title").textContent = `SkillProof Report: ${report.username}`;
  document.querySelector("#identity").textContent = report.main_identity;
  document.querySelector("#github-link").href = report.github_url;
  document.querySelector("#score").textContent = report.builder_score;
  document.querySelector("#summary-text").textContent = report.ai_summary;

  renderSkillMap(report.skill_map);
  listItems("#strong-areas", report.strong_areas);
  listItems("#weak-areas", report.weak_areas);
  listItems("#plan", report.improvement_plan);
  renderRepos(report.repos || []);
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const username = usernameInput.value.trim();
  if (!username) {
    setStatus("Enter a GitHub username first.", true);
    return;
  }

  button.disabled = true;
  setStatus("Scanning GitHub repos, then asking AI to write the report. This can take 10-25 seconds...");
  try {
    const response = await fetch(`${API_BASE}/analyze/github`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Analyze request failed.");
    }
    renderReport(payload);
    setStatus(`Done. Scanned ${payload.repos.length} public repo(s).`);
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    button.disabled = false;
  }
});

exportButton.addEventListener("click", () => {
  if (!currentReport) return;
  window.open(`${API_BASE}/report/${currentReport.id}/markdown`, "_blank", "noreferrer");
});
