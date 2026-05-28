import React, { useEffect, useMemo, useRef, useState } from "https://esm.sh/react@18.3.1";
import { createRoot } from "https://esm.sh/react-dom@18.3.1/client?deps=react@18.3.1";
import * as THREE from "https://esm.sh/three@0.165.0";
import {
  Activity,
  ArrowUpRight,
  BrainCircuit,
  Download,
  Github,
  Loader2,
  ScanSearch,
  ShieldCheck,
  Sparkles,
} from "https://esm.sh/lucide-react@0.468.0?deps=react@18.3.1";

const API_BASE = localStorage.getItem("skillproof_api_base") || "https://skillproof-ai-9u61.onrender.com";
const USE_BROWSER_SCANNER_FIRST = location.hostname.endsWith("github.io") && !localStorage.getItem("skillproof_api_base");
const e = React.createElement;

const SKILL_KEYS = [
  "AI / ML",
  "Cybersecurity",
  "Frontend",
  "Backend",
  "Data Science",
  "Documentation",
  "Deployment",
  "Project Complexity",
  "Consistency",
];

function cx(...parts) {
  return parts.filter(Boolean).join(" ");
}

function clamp(value) {
  return Math.max(0, Math.min(100, Math.round(value)));
}

function includesAny(text, words) {
  const lower = text.toLowerCase();
  return words.some((word) => lower.includes(word));
}

async function fetchJson(url) {
  const response = await fetch(url, { headers: { Accept: "application/vnd.github+json" } });
  if (!response.ok) throw new Error(`GitHub request failed: ${response.status}`);
  return response.json();
}

async function fetchReadme(owner, repo) {
  try {
    const data = await fetchJson(`https://api.github.com/repos/${owner}/${repo}/readme`);
    if (!data.content) return "";
    return atob(data.content.replace(/\n/g, ""));
  } catch {
    return "";
  }
}

async function fetchTree(owner, repo, branch) {
  try {
    const data = await fetchJson(`https://api.github.com/repos/${owner}/${repo}/git/trees/${branch}?recursive=1`);
    return (data.tree || []).filter((item) => item.type === "blob").map((item) => item.path).slice(0, 350);
  } catch {
    return [];
  }
}

function scanRepo(repo, paths, readme) {
  const lowerPaths = paths.map((path) => path.toLowerCase());
  const blob = [
    repo.name,
    repo.description || "",
    repo.language || "",
    ...(repo.topics || []),
    readme.slice(0, 5000),
    lowerPaths.join(" "),
  ].join(" ");
  const hasPackage = lowerPaths.includes("package.json");
  const hasPythonDeps = lowerPaths.includes("requirements.txt") || lowerPaths.includes("pyproject.toml");
  const hasReadme = readme.trim().length > 0;
  const hasAi = includesAny(blob, ["ai", "ml", "model", "dataset", "training", "inference", "sklearn", "torch", "tensorflow", "llm", "rag", "embedding"]) || lowerPaths.some((path) => path.endsWith(".ipynb"));
  const hasSecurity = includesAny(blob, ["security", "cyber", "ctf", "crypto", "pwn", "forensics", "exploit", "scanner", "vulnerability", "audit", "writeup"]);
  const hasFrontend = hasPackage || includesAny(blob, ["react", "vite", "next", "vue", "tailwind", "component", "responsive"]) || lowerPaths.some((path) => path.endsWith(".html") || path.endsWith(".css") || path.endsWith(".jsx") || path.endsWith(".tsx"));
  const hasBackend = hasPythonDeps || includesAny(blob, ["fastapi", "flask", "django", "express", "api", "endpoint", "server", "database"]);
  const hasTests = lowerPaths.some((path) => path.startsWith("tests/") || path.includes("/tests/") || path.startsWith(".github/workflows/"));
  const hasDocker = lowerPaths.includes("dockerfile") || lowerPaths.includes("docker-compose.yml");
  const hasLiveDemo = Boolean(repo.homepage) || includesAny(readme, ["vercel.app", "netlify.app", "github.io", "render.com", "railway.app"]);
  const recentlyUpdated = repo.updated_at ? (Date.now() - new Date(repo.updated_at).getTime()) / 86400000 <= 180 : false;
  const projectTypes = [];
  if (hasAi) projectTypes.push("AI / ML");
  if (hasSecurity) projectTypes.push("Cybersecurity");
  if (hasFrontend) projectTypes.push("Frontend");
  if (hasBackend) projectTypes.push("Backend");
  if (hasFrontend && hasBackend) projectTypes.push("Full-stack");
  if (!projectTypes.length) projectTypes.push("General Project");

  let score = 40;
  if (hasReadme) score += 15;
  if (readme.length >= 500) score += 10;
  if (hasLiveDemo) score += 10;
  if (hasPackage || hasPythonDeps) score += 10;
  if (paths.length >= 8) score += 10;
  if (hasBackend || hasFrontend) score += 15;
  if (hasAi || hasSecurity) score += 15;
  if (recentlyUpdated) score += 10;
  if (lowerPaths.some((path) => path.startsWith("license")) || lowerPaths.includes(".gitignore")) score += 5;
  if (repo.fork) score -= 15;

  return {
    name: repo.name,
    url: repo.html_url,
    description: repo.description,
    language: repo.language,
    stars: repo.stargazers_count || 0,
    forks: repo.forks_count || 0,
    updated_at: repo.updated_at,
    created_at: repo.created_at,
    has_readme: hasReadme,
    has_live_demo: hasLiveDemo,
    has_backend: hasBackend,
    has_frontend: hasFrontend,
    has_ai: hasAi,
    has_security: hasSecurity,
    has_tests: hasTests,
    has_docker: hasDocker,
    is_fork: Boolean(repo.fork),
    project_types: projectTypes,
    score: clamp(score),
  };
}

function makeSkillMap(repos) {
  const totals = Object.fromEntries(SKILL_KEYS.map((key) => [key, 0]));
  if (!repos.length) return Object.fromEntries(SKILL_KEYS.map((key) => [key, 0]));
  repos.forEach((repo) => {
    if (repo.has_ai) totals["AI / ML"] += 26;
    if (repo.has_security) totals.Cybersecurity += 26;
    if (repo.has_frontend) totals.Frontend += 24;
    if (repo.has_backend) totals.Backend += 24;
    if ((repo.language || "").toLowerCase() === "python" && repo.has_ai) totals["Data Science"] += 16;
    if (repo.has_readme) totals.Documentation += 18;
    if (repo.has_live_demo || repo.has_docker) totals.Deployment += 20;
    totals["Project Complexity"] += Math.min(35, Math.round(repo.score / 3));
    if (!repo.is_fork) totals.Consistency += 8;
    if (repo.updated_at && (Date.now() - new Date(repo.updated_at).getTime()) / 86400000 <= 180) totals.Consistency += 14;
  });
  return Object.fromEntries(SKILL_KEYS.map((key) => [key, clamp(totals[key] / repos.length)]));
}

function makeClientReport(user, repos) {
  const skillMap = makeSkillMap(repos);
  const builderScore = clamp(
    repos.reduce((sum, repo) => sum + repo.score, 0) / Math.max(repos.length, 1) * 0.55 +
    ((skillMap.Backend + skillMap.Frontend + skillMap["AI / ML"] + skillMap.Cybersecurity) / 4) * 0.45
  );
  const ranked = Object.entries(skillMap).sort((a, b) => b[1] - a[1]);
  const strong = ranked.filter(([, value]) => value >= 35).slice(0, 5).map(([key]) => key);
  const weak = ranked.filter(([, value]) => value < 25).slice(0, 5).map(([key]) => key);
  const identity = ranked[0]?.[1] >= 25 ? `${ranked[0][0]} Builder` : "Project Builder";
  const topRepos = repos.slice(0, 3).map((repo) => repo.name).join(", ") || "public repositories";
  return {
    id: `client-${Date.now()}`,
    source: "client",
    username: user.login,
    avatar_url: user.avatar_url,
    github_url: user.html_url,
    builder_score: builderScore,
    main_identity: identity,
    skill_map: skillMap,
    strong_areas: strong,
    weak_areas: weak,
    suggested_roles: [identity, "Junior Full-Stack Developer", "MVP Developer"],
    repos,
    ai_summary: `${user.login}'s public GitHub evidence was scanned directly in the browser. The strongest visible signals are ${strong.slice(0, 3).join(", ") || "still emerging"}, with representative repositories including ${topRepos}. This report is based on public repo metadata, README files, and project structure, so private work and hidden contributions are not included.`,
    improvement_plan: [
      "Pin the strongest 3 repositories on GitHub.",
      "Add setup, usage, screenshots, and architecture notes to key README files.",
      "Deploy at least one flagship project publicly.",
      "Add tests or CI workflows to show quality discipline.",
      "Add LICENSE and .gitignore files to portfolio repositories.",
      "Keep one main project active for the next 30 days.",
    ],
    created_at: new Date().toISOString(),
  };
}

async function analyzeInBrowser(username) {
  const user = await fetchJson(`https://api.github.com/users/${username}`);
  const rawRepos = await fetchJson(`https://api.github.com/users/${username}/repos?per_page=5&sort=updated&type=owner`);
  const repos = [];
  for (const repo of rawRepos.filter((item) => !item.private).slice(0, 5)) {
    const [readme, paths] = await Promise.all([
      fetchReadme(user.login, repo.name),
      fetchTree(user.login, repo.name, repo.default_branch || "main"),
    ]);
    repos.push(scanRepo(repo, paths, readme));
  }
  return makeClientReport(user, repos);
}

function markdownForReport(report) {
  const lines = [
    `# SkillProof Report - ${report.username}`,
    "",
    `Builder Score: ${report.builder_score}/100`,
    `Main Identity: ${report.main_identity}`,
    `GitHub: ${report.github_url}`,
    "",
    "## Skill Map",
    "",
    ...Object.entries(report.skill_map).sort((a, b) => b[1] - a[1]).map(([key, value]) => `- ${key}: ${value}/100`),
    "",
    "## Strong Areas",
    "",
    ...(report.strong_areas.length ? report.strong_areas : ["No strong public signal yet"]).map((item) => `- ${item}`),
    "",
    "## Weak Areas",
    "",
    ...(report.weak_areas.length ? report.weak_areas : ["No major weak signal flagged"]).map((item) => `- ${item}`),
    "",
    "## AI Summary",
    "",
    report.ai_summary,
    "",
    "## 30-Day Improvement Plan",
    "",
    ...report.improvement_plan.map((item, index) => `${index + 1}. ${item}`),
  ];
  return lines.join("\n");
}

function IconButton({ children, className = "", ...props }) {
  return e("button", { className: cx("icon-button interactive", className), ...props }, children);
}

function CursorFX() {
  const dotRef = useRef(null);
  const ringRef = useRef(null);

  useEffect(() => {
    const dot = dotRef.current;
    const ring = ringRef.current;
    if (!dot || !ring) return undefined;

    let mouseX = window.innerWidth / 2;
    let mouseY = window.innerHeight / 2;
    let ringX = mouseX;
    let ringY = mouseY;
    let frameId = 0;

    function move(event) {
      mouseX = event.clientX;
      mouseY = event.clientY;
      document.documentElement.style.setProperty("--cursor-x", `${mouseX}px`);
      document.documentElement.style.setProperty("--cursor-y", `${mouseY}px`);
      dot.style.transform = `translate(${mouseX}px, ${mouseY}px) translate(-50%, -50%)`;
    }

    function enterInteractive() {
      document.body.classList.add("cursor-hover");
    }

    function leaveInteractive() {
      document.body.classList.remove("cursor-hover");
    }

    function bindInteractive() {
      document.querySelectorAll("a, button, input, .interactive").forEach((node) => {
        node.addEventListener("mouseenter", enterInteractive);
        node.addEventListener("mouseleave", leaveInteractive);
      });
    }

    function animate() {
      ringX += (mouseX - ringX) * 0.18;
      ringY += (mouseY - ringY) * 0.18;
      ring.style.transform = `translate(${ringX}px, ${ringY}px) translate(-50%, -50%)`;
      frameId = requestAnimationFrame(animate);
    }

    window.addEventListener("mousemove", move);
    bindInteractive();
    const observer = new MutationObserver(bindInteractive);
    observer.observe(document.body, { childList: true, subtree: true });
    animate();

    return () => {
      window.removeEventListener("mousemove", move);
      observer.disconnect();
      cancelAnimationFrame(frameId);
      document.body.classList.remove("cursor-hover");
    };
  }, []);

  return e(
    React.Fragment,
    null,
    e("div", { className: "spotlight", "aria-hidden": "true" }),
    e("div", { className: "cursor-dot", ref: dotRef, "aria-hidden": "true" }),
    e("div", { className: "cursor-ring", ref: ringRef, "aria-hidden": "true" })
  );
}

function AtomScene({ report, scanning }) {
  const mountRef = useRef(null);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return undefined;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 100);
    camera.position.set(0, 0.8, 8.8);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setClearColor(0xffffff, 0);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    mount.appendChild(renderer.domElement);

    const root = new THREE.Group();
    scene.add(root);

    const ambient = new THREE.AmbientLight(0xffffff, 2.5);
    scene.add(ambient);
    const light = new THREE.DirectionalLight(0xffffff, 3);
    light.position.set(3, 4, 5);
    scene.add(light);

    const coreGeometry = new THREE.SphereGeometry(0.42, 48, 48);
    const coreMaterial = new THREE.MeshStandardMaterial({
      color: 0x111827,
      roughness: 0.42,
      metalness: 0.18,
    });
    const core = new THREE.Mesh(coreGeometry, coreMaterial);
    root.add(core);

    const orbitMaterial = new THREE.LineBasicMaterial({ color: 0x111827, transparent: true, opacity: 0.17 });
    const nodeMaterials = [
      new THREE.MeshStandardMaterial({ color: 0x0ea5e9, roughness: 0.25 }),
      new THREE.MeshStandardMaterial({ color: 0x22c55e, roughness: 0.25 }),
      new THREE.MeshStandardMaterial({ color: 0xa855f7, roughness: 0.25 }),
      new THREE.MeshStandardMaterial({ color: 0xf59e0b, roughness: 0.25 }),
    ];
    const lineMaterial = new THREE.LineBasicMaterial({ color: 0x111827, transparent: true, opacity: 0.22 });
    const dotGeometry = new THREE.SphereGeometry(0.105, 24, 24);

    const groups = [];
    const labels = report ? Object.entries(report.skill_map || {}).slice(0, 9) : [
      ["AI / ML", 78],
      ["Cybersecurity", 68],
      ["Frontend", 84],
      ["Backend", 73],
      ["Documentation", 64],
      ["Deployment", 59],
    ];

    labels.forEach(([label, value], index) => {
      const branch = new THREE.Group();
      const angle = (index / labels.length) * Math.PI * 2;
      const radius = 1.65 + (value / 100) * 1.45;
      const y = Math.sin(index * 1.9) * 0.9;
      const end = new THREE.Vector3(Math.cos(angle) * radius, y, Math.sin(angle) * radius * 0.55);

      const points = [new THREE.Vector3(0, 0, 0), end];
      const branchLine = new THREE.Line(new THREE.BufferGeometry().setFromPoints(points), lineMaterial);
      branch.add(branchLine);

      const node = new THREE.Mesh(dotGeometry, nodeMaterials[index % nodeMaterials.length]);
      node.position.copy(end);
      node.userData = { label, value, speed: 0.35 + index * 0.035 };
      branch.add(node);

      for (let child = 0; child < 2; child += 1) {
        const childAngle = angle + (child === 0 ? 0.42 : -0.42);
        const childEnd = end.clone().add(new THREE.Vector3(Math.cos(childAngle) * 0.62, child === 0 ? 0.32 : -0.25, Math.sin(childAngle) * 0.34));
        const childLine = new THREE.Line(new THREE.BufferGeometry().setFromPoints([end, childEnd]), lineMaterial);
        branch.add(childLine);
        const childNode = new THREE.Mesh(new THREE.SphereGeometry(0.055, 16, 16), nodeMaterials[(index + child + 1) % nodeMaterials.length]);
        childNode.position.copy(childEnd);
        branch.add(childNode);
      }

      groups.push(branch);
      root.add(branch);
    });

    [0, 1, 2].forEach((orbitIndex) => {
      const curve = new THREE.EllipseCurve(0, 0, 2.75 + orbitIndex * 0.42, 0.88 + orbitIndex * 0.24, 0, Math.PI * 2, false, 0);
      const points = curve.getPoints(180).map((point) => new THREE.Vector3(point.x, point.y, 0));
      const orbit = new THREE.Line(new THREE.BufferGeometry().setFromPoints(points), orbitMaterial);
      orbit.rotation.x = orbitIndex * 0.72 + 0.35;
      orbit.rotation.y = orbitIndex * 0.55 + 0.25;
      root.add(orbit);
    });

    function resize() {
      const rect = mount.getBoundingClientRect();
      const width = Math.max(320, rect.width);
      const height = Math.max(320, rect.height);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height, false);
    }

    let frameId = 0;
    const clock = new THREE.Clock();
    function animate() {
      const time = clock.getElapsedTime();
      root.rotation.y = time * (scanning ? 0.3 : 0.16);
      root.rotation.x = Math.sin(time * 0.4) * 0.08;
      core.scale.setScalar(1 + Math.sin(time * 2.2) * 0.035);
      groups.forEach((branch, index) => {
        branch.rotation.z = Math.sin(time * 0.55 + index) * 0.025;
      });
      renderer.render(scene, camera);
      frameId = requestAnimationFrame(animate);
    }

    resize();
    animate();
    const observer = new ResizeObserver(resize);
    observer.observe(mount);

    return () => {
      observer.disconnect();
      cancelAnimationFrame(frameId);
      renderer.dispose();
      mount.removeChild(renderer.domElement);
      scene.traverse((item) => {
        if (item.geometry) item.geometry.dispose();
        if (item.material) {
          if (Array.isArray(item.material)) item.material.forEach((material) => material.dispose());
          else item.material.dispose();
        }
      });
    };
  }, [report, scanning]);

  return e("div", { className: "atom-stage", ref: mountRef, "aria-label": "Skill graph visualization" });
}

function SkillBars({ skillMap = {} }) {
  const entries = Object.entries(skillMap).sort((a, b) => b[1] - a[1]);
  return e(
    "div",
    { className: "skill-bars" },
    entries.map(([label, value]) =>
      e(
        "div",
        { className: "skill-row", key: label },
        e("span", null, label),
        e("div", { className: "bar-track interactive" }, e("div", { className: "bar-fill", style: { width: `${value}%` } })),
        e("strong", null, value)
      )
    )
  );
}

function EvidenceList({ title, items, tone }) {
  return e(
    "section",
    { className: "evidence-panel hover-tilt interactive" },
    e("h3", null, title),
    e(
      "ul",
      null,
      (items?.length ? items : ["No strong public signal yet"]).map((item) =>
        e("li", { key: item, className: tone }, e("span", null), item)
      )
    )
  );
}

function RepoList({ repos = [] }) {
  return e(
    "section",
    { className: "repo-section" },
    e("div", { className: "section-title" }, e("h3", null, "Repository Evidence"), e("span", null, `${repos.length} scanned`)),
    e(
      "div",
      { className: "repo-list" },
      repos.map((repo) =>
        e(
          "article",
          { className: "repo-item hover-tilt interactive", key: repo.url || repo.name },
          e(
            "div",
            { className: "repo-main" },
            e(
              "a",
              { href: repo.url, target: "_blank", rel: "noreferrer" },
              repo.name,
              e(ArrowUpRight, { size: 14 })
            ),
            e("p", null, repo.description || "No description provided."),
            e(
              "div",
              { className: "repo-tags" },
              [...(repo.project_types || []), repo.language || "n/a", repo.has_tests ? "Tests" : "No tests", repo.has_live_demo ? "Live" : null]
                .filter(Boolean)
                .slice(0, 6)
                .map((tag) => e("span", { key: `${repo.name}-${tag}` }, tag))
            )
          ),
          e("strong", { className: "repo-score" }, repo.score)
        )
      )
    )
  );
}

function EmptyState({ onExample }) {
  return e(
    "section",
    { className: "empty-state hover-tilt" },
    e("div", { className: "empty-icon" }, e(BrainCircuit, { size: 28 })),
    e("h2", null, "Project evidence turns into a living skill map."),
    e("p", null, "Enter a GitHub username to scan public repositories, generate a builder score, and export a portfolio-ready report."),
    e("button", { className: "interactive", type: "button", onClick: onExample }, "Try BeBecpp")
  );
}

function App() {
  const [username, setUsername] = useState("");
  const [report, setReport] = useState(null);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [scanning, setScanning] = useState(false);

  const topSkill = useMemo(() => {
    const entries = Object.entries(report?.skill_map || {});
    return entries.sort((a, b) => b[1] - a[1])[0]?.[0] || "Skill map";
  }, [report]);

  async function analyze(nextUsername = username) {
    const clean = nextUsername.trim();
    if (!clean) {
      setError("Enter a GitHub username first.");
      return;
    }

    setScanning(true);
    setError("");
    setStatus("Scanning repositories and generating the AI report...");
    try {
      if (USE_BROWSER_SCANNER_FIRST) {
        const browserReport = await analyzeInBrowser(clean);
        setReport(browserReport);
        setStatus(`Live browser scan complete. Scanned ${browserReport.repos.length} repositories.`);
        return;
      }
      const response = await fetch(`${API_BASE}/analyze/github`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: clean }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || "Analyze request failed.");
      setReport(payload);
      setStatus(`Scanned ${payload.repos.length} repositories.`);
    } catch (err) {
      try {
        setStatus("Backend is waking up, using browser scanner now...");
        const fallbackReport = await analyzeInBrowser(clean);
        setReport(fallbackReport);
        setStatus(`Live browser scan complete. Scanned ${fallbackReport.repos.length} repositories.`);
      } catch (fallbackError) {
        setError(`${err.message}. Browser fallback also failed: ${fallbackError.message}`);
        setStatus("");
      }
    } finally {
      setScanning(false);
    }
  }

  function useExample() {
    setUsername("BeBecpp");
    analyze("BeBecpp");
  }

  function exportMarkdown() {
    if (!report) return;
    if (report.source === "client") {
      const blob = new Blob([markdownForReport(report)], { type: "text/markdown" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `skillproof-${report.username}.md`;
      link.click();
      URL.revokeObjectURL(url);
      return;
    }
    window.open(`${API_BASE}/report/${report.id}/markdown`, "_blank", "noreferrer");
  }

  return e(
    "main",
    { className: "app-shell" },
    e(CursorFX),
    e(AtomScene, { report, scanning }),
    e(
      "section",
      { className: "control-band" },
      e(
        "div",
        { className: "brand-block hover-tilt interactive" },
        e("div", { className: "mark" }, e(Sparkles, { size: 18 })),
        e("div", null, e("h1", null, "SkillProof AI"), e("p", null, "Your projects speak louder than your resume."))
      ),
      e(
        "form",
        {
          className: "scan-form interactive",
          onSubmit: (event) => {
            event.preventDefault();
            analyze();
          },
        },
        e(Github, { size: 18 }),
        e("input", {
          value: username,
          onChange: (event) => setUsername(event.target.value),
          placeholder: "GitHub username",
          autoComplete: "off",
        }),
        e(
          "button",
          { className: "interactive", type: "submit", disabled: scanning },
          scanning ? e(Loader2, { className: "spin", size: 18 }) : e(ScanSearch, { size: 18 }),
          scanning ? "Scanning" : "Analyze"
        )
      ),
      e(
        "div",
        { className: "status-line hover-tilt" },
        error ? e("span", { className: "error" }, error) : e("span", null, status || "Ready")
      )
    ),
    e(
      "section",
      { className: "dashboard" },
      report
        ? [
            e(
              "section",
              { className: "identity-panel hover-tilt", key: "identity" },
              e("img", { src: report.avatar_url, alt: "" }),
              e(
                "div",
                null,
                e("p", null, "SkillProof Report"),
                e("h2", null, report.username),
                e("a", { href: report.github_url, target: "_blank", rel: "noreferrer" }, report.main_identity, e(ArrowUpRight, { size: 15 }))
              ),
              e("div", { className: "score-ring" }, e("strong", null, report.builder_score), e("span", null, "Builder Score"))
            ),
            e(
              "section",
              { className: "metric-grid", key: "metrics" },
              e("article", { className: "hover-tilt interactive" }, e(Activity, { size: 20 }), e("span", null, "Top Signal"), e("strong", null, topSkill)),
              e("article", { className: "hover-tilt interactive" }, e(ShieldCheck, { size: 20 }), e("span", null, "Repos"), e("strong", null, report.repos.length)),
              e("article", { className: "hover-tilt interactive" }, e(BrainCircuit, { size: 20 }), e("span", null, "Identity"), e("strong", null, report.main_identity))
            ),
            e(
              "section",
              { className: "map-panel hover-tilt", key: "map" },
              e("div", { className: "section-title" }, e("h3", null, "Skill Map"), e("span", null, "Public evidence score")),
              e(SkillBars, { skillMap: report.skill_map })
            ),
            e(
              "div",
              { className: "evidence-grid", key: "evidence" },
              e(EvidenceList, { title: "Strong Areas", items: report.strong_areas, tone: "good" }),
              e(EvidenceList, { title: "Weak Areas", items: report.weak_areas, tone: "warn" })
            ),
            e(RepoList, { repos: report.repos, key: "repos" }),
            e(
              "section",
              { className: "summary-panel hover-tilt", key: "summary" },
              e(
                "div",
                { className: "section-title" },
                e("h3", null, "AI Summary"),
                e(IconButton, { type: "button", onClick: exportMarkdown, title: "Export Markdown" }, e(Download, { size: 18 }))
              ),
              e("p", null, report.ai_summary),
              e("ol", null, report.improvement_plan.map((step) => e("li", { key: step }, step)))
            ),
          ]
        : e(EmptyState, { onExample: useExample })
    )
  );
}

createRoot(document.getElementById("root")).render(e(App));
