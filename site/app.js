// Gallery page: loads projects.json (written by scripts/build_site.py) and
// renders filterable cards.
(function () {
  const $ = (id) => document.getElementById(id);
  const state = { q: "", area: "", lang: "", run: "" };
  let projects = [];

  const RUN = {
    static: { label: "Runs in browser", cls: "web", group: "web" },
    build: { label: "Runs in browser", cls: "web", group: "web" },
    pyodide: { label: "Python in browser", cls: "py", group: "pyodide" },
    code: { label: "Source", cls: "code", group: "code" },
  };

  const esc = (s) =>
    String(s ?? "").replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  // "Python (NumPy)" -> "Python", "SQL + Python" -> "SQL"
  const baseLang = (l) => (l || "Other").split(/[ (+/]/)[0] || "Other";

  function primaryAction(p) {
    if (p.run === "static" || p.run === "build")
      return `<a class="btn primary" href="p/${esc(p.slug)}/" target="_blank" rel="noopener">Open app ↗</a>`;
    if (p.run === "pyodide")
      return `<a class="btn primary" href="run.html?p=${encodeURIComponent(p.slug)}">Run it →</a>`;
    return `<a class="btn primary" href="${esc(p.codespaces)}" target="_blank" rel="noopener">Open in Codespaces ↗</a>`;
  }

  function card(p) {
    const r = RUN[p.run] || RUN.code;
    const blurb = p.summary || p.description;
    return `<article class="card">
      <div class="card-top"><span class="num">#${esc(p.number)}</span><span class="badge ${r.cls}">${r.label}</span></div>
      <h2>${esc(p.title)}</h2>
      <p>${esc(blurb)}</p>
      <div class="meta">${[p.language, p.level, p.area].filter(Boolean).map((m) => `<span>${esc(m)}</span>`).join("")}</div>
      <div class="actions">${primaryAction(p)}<a class="btn" href="${esc(p.source)}" target="_blank" rel="noopener">Code</a></div>
    </article>`;
  }

  function matches(p) {
    if (state.area && p.area !== state.area) return false;
    if (state.lang && baseLang(p.language) !== state.lang) return false;
    if (state.run && (RUN[p.run] || RUN.code).group !== state.run) return false;
    if (state.q) {
      const hay = [p.title, p.language, p.area, p.level, p.summary, p.description, p.number]
        .join(" ").toLowerCase();
      return state.q.toLowerCase().split(/\s+/).every((w) => hay.includes(w));
    }
    return true;
  }

  function render() {
    const list = projects.filter(matches);
    $("grid").innerHTML = list.length
      ? list.map(card).join("")
      : `<div class="empty">No projects match those filters.</div>`;
  }

  function fillSelect(el, values) {
    [...new Set(values)].filter(Boolean).sort().forEach((v) => {
      const o = document.createElement("option");
      o.value = o.textContent = v;
      el.appendChild(o);
    });
  }

  function stats() {
    const runnable = projects.filter((p) => p.run !== "code").length;
    const langs = new Set(projects.map((p) => baseLang(p.language))).size;
    const areas = new Set(projects.map((p) => p.area).filter(Boolean)).size;
    $("stats").innerHTML = [
      [projects.length, "projects"], [runnable, "run in browser"],
      [langs, "languages"], [areas, "areas"],
    ].map(([n, l]) => `<div><b>${n}</b><span>${l}</span></div>`).join("");
  }

  $("q").addEventListener("input", (e) => { state.q = e.target.value.trim(); render(); });
  $("area").addEventListener("change", (e) => { state.area = e.target.value; render(); });
  $("lang").addEventListener("change", (e) => { state.lang = e.target.value; render(); });
  document.querySelectorAll(".chip").forEach((chip) =>
    chip.addEventListener("click", () => {
      document.querySelectorAll(".chip").forEach((c) => c.setAttribute("aria-pressed", "false"));
      chip.setAttribute("aria-pressed", "true");
      state.run = chip.dataset.run;
      render();
    }));

  fetch("projects.json")
    .then((r) => r.json())
    .then((data) => {
      // Newest first, so the latest twice-daily build is at the top
      projects = data.projects.sort((a, b) => b.number.localeCompare(a.number));
      fillSelect($("area"), projects.map((p) => p.area));
      fillSelect($("lang"), projects.map((p) => baseLang(p.language)));
      stats();
      render();
    })
    .catch(() => {
      $("grid").innerHTML = `<div class="empty">Couldn't load projects.json.</div>`;
    });
})();
