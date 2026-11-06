"""Policy tests for the workflow files themselves.

Workflows are code, so we test them: parse the YAML and assert the pipeline
shape and security conventions hold. These run in milliseconds, without GitHub.
"""

import re
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

WORKFLOWS = Path(__file__).resolve().parent.parent / ".github" / "workflows"
ACTION_REF = re.compile(r"^[\w.-]+/[\w.-]+(/[\w./-]+)?@(v\d+(\.\d+){0,2}|[0-9a-f]{40})$")


def load(name):
    data = yaml.safe_load((WORKFLOWS / name).read_text())
    # YAML 1.1 parses the bare key `on` as boolean True.
    data["on"] = data.pop(True, data.get("on"))
    return data


def all_workflows():
    return sorted(p.name for p in WORKFLOWS.glob("*.yml"))


def needs_of(job):
    needs = job.get("needs", [])
    return [needs] if isinstance(needs, str) else needs


def test_expected_workflows_exist():
    assert {"ci.yml", "release.yml"} <= set(all_workflows())


@pytest.mark.parametrize("name", all_workflows())
def test_top_level_permissions_are_read_only(name):
    assert load(name)["permissions"] == {"contents": "read"}


@pytest.mark.parametrize("name", all_workflows())
def test_every_job_has_timeout_and_name(name):
    for job_id, job in load(name)["jobs"].items():
        assert "timeout-minutes" in job, f"{name}:{job_id} has no timeout"
        assert job["timeout-minutes"] <= 30
        assert "name" in job


@pytest.mark.parametrize("name", all_workflows())
def test_actions_are_pinned(name):
    for job_id, job in load(name)["jobs"].items():
        for step in job["steps"]:
            if "uses" in step:
                assert ACTION_REF.match(step["uses"]), f"{name}:{job_id} unpinned {step['uses']}"


@pytest.mark.parametrize("name", all_workflows())
def test_needs_reference_real_jobs_and_are_acyclic(name):
    jobs = load(name)["jobs"]
    for job in jobs.values():
        for dep in needs_of(job):
            assert dep in jobs
    # Topological sort (Kahn's algorithm) must consume every job.
    indegree = {j: len(needs_of(job)) for j, job in jobs.items()}
    ready = [j for j, d in indegree.items() if d == 0]
    seen = 0
    while ready:
        current = ready.pop()
        seen += 1
        for j, job in jobs.items():
            if current in needs_of(job):
                indegree[j] -= 1
                if indegree[j] == 0:
                    ready.append(j)
    assert seen == len(jobs), "dependency cycle between jobs"


def test_ci_pipeline_shape():
    ci = load("ci.yml")
    assert "pull_request" in ci["on"] and "push" in ci["on"]
    assert ci["concurrency"]["cancel-in-progress"] is True
    jobs = ci["jobs"]
    assert needs_of(jobs["test"]) == ["lint"]
    assert set(needs_of(jobs["build"])) == {"lint", "test"}
    matrix = jobs["test"]["strategy"]["matrix"]
    assert len(matrix["python-version"]) >= 2
    assert jobs["test"]["strategy"]["fail-fast"] is False


def test_release_only_on_semver_tags_and_scopes_write_permission():
    rel = load("release.yml")
    assert rel["on"]["push"]["tags"] == ["v*.*.*"]
    assert rel["concurrency"]["cancel-in-progress"] is False
    writers = [j for j, job in rel["jobs"].items() if "permissions" in job]
    assert writers == ["release"]
    assert rel["jobs"]["release"]["permissions"] == {"contents": "write"}
    steps = " ".join(s.get("run", "") for s in rel["jobs"]["verify"]["steps"])
    assert "check_version.py" in steps


@pytest.mark.parametrize("name", all_workflows())
def test_no_untrusted_input_interpolated_into_run(name):
    # Script-injection guard: PR titles/bodies/branch names must never be
    # expanded with ${{ }} directly inside a shell `run:` block.
    risky = re.compile(r"\$\{\{\s*github\.(event\.(pull_request|issue|comment)|head_ref)")
    for job in load(name)["jobs"].values():
        for step in job["steps"]:
            assert not risky.search(step.get("run", ""))
