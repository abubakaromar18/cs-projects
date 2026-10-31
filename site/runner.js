// Runs a project's Python CLI in the browser with Pyodide.
// The build script copies the package source to p/<slug>/py/ and lists the
// files in projects.json; we mount them, then run `python -m <package> ARGS`
// for each command typed. Files the program writes persist for the session.
(async function () {
  const $ = (id) => document.getElementById(id);
  const out = $("out");
  const history = [];
  let histPos = 0;

  const esc = (s) => String(s ?? "").replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));

  function write(text, cls) {
    const span = document.createElement("span");
    if (cls) span.className = cls;
    span.textContent = text;
    out.appendChild(span);
    out.scrollTop = out.scrollHeight;
  }

  function setBusy(busy, status) {
    $("cmd").disabled = busy;
    $("go").disabled = busy;
    $("status").textContent = status;
    if (!busy) $("cmd").focus({ preventScroll: true });
  }

  const slug = new URLSearchParams(location.search).get("p");
  const data = await fetch("projects.json").then((r) => r.json());
  const p = data.projects.find((x) => x.slug === slug);
  if (!p || p.run !== "pyodide") {
    $("title").textContent = "Project not found";
    $("status").textContent = "nothing to run";
    return;
  }

  document.title = `${p.title} · CS Projects`;
  $("title").textContent = p.title;
  $("desc").textContent = p.description || p.summary || "";
  $("meta").innerHTML = [p.language, p.level, p.area].filter(Boolean).map((m) => `<span>${esc(m)}</span>`).join("");
  $("source").href = p.source;
  $("prompt").textContent = `$ ${p.command}`;

  (p.examples || []).forEach((ex) => {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = `${p.command} ${ex}`;
    b.title = "Run this example";
    b.addEventListener("click", () => { $("cmd").value = ex; runCommand(ex); });
    $("examples").appendChild(b);
  });

  write(`Loading Python in your browser (first visit downloads ~10 MB)…\n`, "dim");

  let pyodide;
  try {
    pyodide = await loadPyodide();
    if (p.packages && p.packages.length) {
      setBusy(true, `loading ${p.packages.join(", ")}…`);
      await pyodide.loadPackage(p.packages);
    }
    const root = "/home/pyodide/app";
    await Promise.all(p.files.map(async (rel) => {
      const buf = await fetch(`p/${slug}/py/${rel}`).then((r) => r.arrayBuffer());
      const dir = `${root}/${rel}`.split("/").slice(0, -1).join("/");
      pyodide.FS.mkdirTree(dir);
      pyodide.FS.writeFile(`${root}/${rel}`, new Uint8Array(buf));
    }));
    pyodide.FS.mkdirTree("/home/pyodide/work");
    pyodide.runPython(`
import os, sys, warnings, getpass
warnings.simplefilter("ignore", getpass.GetPassWarning)
sys.path.insert(0, ${JSON.stringify(root)})
os.chdir("/home/pyodide/work")
os.environ.setdefault("COLUMNS", "80")
os.environ["HOME"] = "/home/pyodide/work"
`);
  } catch (err) {
    write(`Couldn't start Python: ${err}\n`, "err");
    $("status").textContent = "failed to load";
    return;
  }

  // Unbuffered output so prompts like "> " show up before input is read
  const outDec = new TextDecoder(), errDec = new TextDecoder();
  pyodide.setStdout({ write: (buf) => { write(outDec.decode(buf, { stream: true })); return buf.length; } });
  pyodide.setStderr({ write: (buf) => { write(errDec.decode(buf, { stream: true }), "err"); return buf.length; } });
  // Programs that call input() get a browser prompt; Cancel sends EOF.
  pyodide.setStdin({
    stdin: () => {
      const v = window.prompt(`${p.title} is waiting for input:`);
      if (v === null) { write("^D\n", "dim"); return undefined; }
      write(v + "\n", "cmd");
      return v + "\n";
    },
  });

  write(`Ready. Type arguments for \`${p.command}\` below, or tap an example. Try --help.\n\n`, "dim");
  setBusy(false, "ready");

  async function runCommand(line) {
    line = line.trim();
    if (line.startsWith(p.command + " ") || line === p.command) line = line.slice(p.command.length).trim();
    if (history[history.length - 1] !== line) history.push(line);
    histPos = history.length;
    write(`$ ${p.command}${line ? " " + line : ""}\n`, "cmd");
    setBusy(true, "running…");
    // Yield so the UI paints before Python takes the main thread
    await new Promise((r) => setTimeout(r, 20));
    try {
      pyodide.globals.set("__argline", line);
      const code = await pyodide.runPythonAsync(`
import runpy, shlex, sys
sys.argv = [${JSON.stringify(p.command)}] + shlex.split(__argline)
_code = 0
try:
    runpy.run_module(${JSON.stringify(p.package)}, run_name="__main__", alter_sys=True)
except SystemExit as e:
    _code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
    if e.code not in (None, 0) and not isinstance(e.code, int):
        print(e.code, file=sys.stderr)
except KeyboardInterrupt:
    _code = 130
sys.stdout.flush(); sys.stderr.flush()
_code
`);
      if (code) write(`[exit ${code}]\n`, "dim");
    } catch (err) {
      write(String(err.message || err).trim() + "\n", "err");
    }
    write("\n");
    $("cmd").value = "";
    setBusy(false, "ready");
  }

  $("form").addEventListener("submit", (e) => { e.preventDefault(); if (!$("cmd").disabled) runCommand($("cmd").value); });
  $("cmd").addEventListener("keydown", (e) => {
    if (e.key === "ArrowUp" && histPos > 0) { histPos--; $("cmd").value = history[histPos]; e.preventDefault(); }
    if (e.key === "ArrowDown") { histPos = Math.min(history.length, histPos + 1); $("cmd").value = history[histPos] ?? ""; e.preventDefault(); }
  });
  $("clear").addEventListener("click", () => { out.textContent = ""; });
})();
