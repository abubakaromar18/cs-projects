#!/usr/bin/env python3
"""Build the cs-projects showcase site into an output folder (default: _site).

For every folder in projects/ it works out how the project can be shown:

  static   - has an index.html and no build step: copied as-is
  build    - has an index.html and an npm "build" script: npm ci + build, then
             copies dist/ (Vite) or the folder (tsc writes next to the page)
  pyodide  - pure-Python CLI (no runtime deps + a [project.scripts] entry):
             runs in the browser through Pyodide
  code     - everything else: source link + "Open in Codespaces"

Metadata comes from PROJECTS.md and the project README. An optional
project.json in a project folder overrides any of it (see
site/project.template.json). Standard library only.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

REPO = "abubakaromar18/cs-projects"
ROOT = Path(__file__).resolve().parent.parent
PROJECTS = ROOT / "projects"
SITE_SRC = ROOT / "site"

SKIP_DIRS = {"node_modules", ".git", "dist", "build", "target", "__pycache__",
             ".venv", "venv", ".pytest_cache", "build-test", ".next"}
PY_SKIP_DIRS = {"tests", "test", "__pycache__", ".pytest_cache"}


def log(msg: str) -> None:
    print(msg, flush=True)


# --------------------------------------------------------------- metadata

def queue_metadata() -> dict[str, dict]:
    """Parse '- [x] NNN | Title | Lang | Level | Area | Description' lines."""
    meta: dict[str, dict] = {}
    path = ROOT / "PROJECTS.md"
    if not path.exists():
        return meta
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"-\s*\[[ xX]\]\s*(\d{3})\s*\|(.+)", line)
        if not m:
            continue
        parts = [p.strip() for p in m.group(2).split("|")]
        if len(parts) < 5:
            continue
        desc = re.sub(r"\s*→\s*\[folder\].*$", "", parts[4]).strip()
        meta[m.group(1)] = {"title": parts[0], "language": parts[1],
                            "level": parts[2], "area": parts[3],
                            "description": desc}
    return meta


def readme_info(folder: Path) -> tuple[str | None, str | None, list[str]]:
    """Return (title, first paragraph, '$ cmd' example lines) from README.md."""
    readme = folder / "README.md"
    if not readme.exists():
        return None, None, []
    text = readme.read_text(encoding="utf-8", errors="ignore")
    title = None
    m = re.search(r"^#\s+(.+)$", text, re.M)
    if m:
        title = re.sub(r"^\d{3}\s*·\s*", "", m.group(1)).strip()
    para = None
    for block in re.split(r"\n\s*\n", text):
        b = block.strip()
        if b and not b.startswith(("#", "```", ">", "|", "!", "-", "*")):
            para = re.sub(r"\s+", " ", b)
            break
    examples = re.findall(r"^\$ (.+)$", text, re.M)
    return title, para, examples


def strip_md(s: str) -> str:
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
    return re.sub(r"[*_`]", "", s)


# --------------------------------------------------------------- detection

def package_json(folder: Path) -> dict:
    p = folder / "package.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def python_cli(folder: Path) -> dict | None:
    """Return {'command', 'module', 'pure'} for a pyproject CLI, else None."""
    p = folder / "pyproject.toml"
    if not p.exists():
        return None
    try:
        data = tomllib.loads(p.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return None
    proj = data.get("project", {})
    scripts = proj.get("scripts", {})
    if not scripts:
        return None
    command, target = next(iter(scripts.items()))
    module = target.split(":")[0]           # e.g. todo_cli.cli
    package = module.split(".")[0]          # e.g. todo_cli
    return {"command": command, "package": package,
            "pure": not proj.get("dependencies")}


def detect_run(folder: Path) -> str:
    if (folder / "index.html").exists():
        scripts = package_json(folder).get("scripts", {})
        return "build" if "build" in scripts else "static"
    cli = python_cli(folder)
    if cli and cli["pure"]:
        return "pyodide"
    return "code"


# --------------------------------------------------------------- builders

def copy_tree(src: Path, dst: Path) -> None:
    shutil.copytree(src, dst, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns(*SKIP_DIRS))


def run(cmd: list[str], cwd: Path) -> None:
    log(f"    $ {' '.join(cmd)}")
    subprocess.run(cmd, cwd=cwd, check=True)


def build_static(folder: Path, dest: Path) -> None:
    copy_tree(folder, dest)


def build_npm(folder: Path, dest: Path) -> None:
    lock = (folder / "package-lock.json").exists()
    run(["npm", "ci" if lock else "install", "--no-audit", "--no-fund"], folder)
    pkg = package_json(folder)
    build_script = pkg.get("scripts", {}).get("build", "")
    if "vite" in build_script:
        # Relative base so the app works under /cs-projects/p/<slug>/
        run(["npx", "vite", "build", "--base", "./"], folder)
        copy_tree(folder / "dist", dest)
    else:
        # e.g. tsc writing dist/ next to index.html: ship the whole folder
        run(["npm", "run", "build"], folder)
        shutil.copytree(folder, dest, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("node_modules", ".git",
                                                      "build-test", "test",
                                                      "tests"))


def build_pyodide(folder: Path, dest: Path, cli: dict) -> list[str]:
    """Copy the package's source (not tests) and return the file list."""
    src = folder / "src"
    base = src if (src / cli["package"]).exists() else folder
    pkg_dir = base / cli["package"]
    files: list[str] = []
    for f in sorted(pkg_dir.rglob("*")):
        if not f.is_file() or set(f.relative_to(base).parts) & PY_SKIP_DIRS:
            continue
        if f.suffix in {".pyc"}:
            continue
        rel = f.relative_to(base).as_posix()
        (dest / "py" / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, dest / "py" / rel)
        files.append(rel)
    return files


# Imports that Pyodide ships as separate packages (loaded on demand)
PYODIDE_PACKAGES = {"sqlite3": "sqlite3", "numpy": "numpy", "pandas": "pandas",
                    "matplotlib": "matplotlib", "scipy": "scipy"}


def pyodide_packages(py_root: Path) -> list[str]:
    found: set[str] = set()
    for f in py_root.rglob("*.py"):
        text = f.read_text(encoding="utf-8", errors="ignore")
        for mod in re.findall(r"^\s*(?:import|from)\s+([A-Za-z_]\w*)", text, re.M):
            if mod in PYODIDE_PACKAGES:
                found.add(PYODIDE_PACKAGES[mod])
    return sorted(found)


# --------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default="_site", help="output folder")
    ap.add_argument("--skip-builds", action="store_true",
                    help="don't run npm builds (fast local preview)")
    args = ap.parse_args()

    out = (ROOT / args.out).resolve()
    if out.exists():
        shutil.rmtree(out)
    copy_tree(SITE_SRC, out)
    (out / "project.template.json").unlink(missing_ok=True)

    queue = queue_metadata()
    entries, failures = [], []

    for folder in sorted(p for p in PROJECTS.iterdir() if p.is_dir()):
        slug = folder.name
        num = slug[:3]
        log(f"• {slug}")
        override = {}
        if (folder / "project.json").exists():
            override = json.loads((folder / "project.json").read_text("utf-8"))

        title, para, examples = readme_info(folder)
        q = queue.get(num, {})
        entry = {
            "slug": slug,
            "number": num,
            "title": q.get("title") or title or slug,
            "language": q.get("language", ""),
            "level": q.get("level", ""),
            "area": q.get("area", ""),
            "summary": q.get("description", ""),
            "description": strip_md(para) if para else q.get("description", ""),
            "run": detect_run(folder),
            "source": f"https://github.com/{REPO}/tree/main/projects/{slug}",
        }
        cli = python_cli(folder)
        if cli:
            entry["command"] = cli["command"]
            entry["package"] = cli["package"]
            entry["examples"] = [e[len(cli["command"]):].strip()
                                 for e in examples
                                 if e.split(" ")[0] == cli["command"]][:6]
        entry.update(override)

        dest = out / "p" / slug
        try:
            if entry["run"] == "static":
                build_static(folder, dest)
            elif entry["run"] == "build":
                if args.skip_builds:
                    log("    (skipped build)")
                    entry["run"] = "code"
                else:
                    build_npm(folder, dest)
            elif entry["run"] == "pyodide":
                if not cli:
                    raise RuntimeError("run=pyodide needs a [project.scripts] entry")
                dest.mkdir(parents=True, exist_ok=True)
                entry["files"] = build_pyodide(folder, dest, cli)
                if "packages" not in override:
                    entry["packages"] = pyodide_packages(dest / "py")
        except Exception as exc:  # one broken project must not sink the site
            log(f"    ! {exc}; falling back to source-only")
            failures.append(slug)
            entry["run"] = "code"
            shutil.rmtree(dest, ignore_errors=True)

        entry["codespaces"] = f"https://codespaces.new/{REPO}?quickstart=1"
        entries.append(entry)
        log(f"    → {entry['run']}")

    (out / "projects.json").write_text(
        json.dumps({"repo": REPO, "projects": entries}, indent=2), "utf-8")
    (out / ".nojekyll").write_text("")
    counts = {k: sum(e["run"] == k for e in entries)
              for k in ("static", "build", "pyodide", "code")}
    log(f"\nBuilt {len(entries)} projects into {out}: {counts}")
    if failures:
        log(f"Fell back to source-only: {', '.join(failures)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
