"""The job that executes a stranger's code cannot write, and the job that can
write executes nothing of the stranger's.

Installing and running a tool as its author documents means running the
author's Dockerfile, Makefile and program. That happens in `verify`, whose
token only reads. `publish` holds the one write permission (gh-pages) and
handles the report as data."""
import json
import pathlib

import pytest
import yaml

import publish_layout as pl
from test_publish_layout import SLUG, NEW, _run

ROOT = pathlib.Path(__file__).resolve().parents[2]
WORKFLOW = yaml.safe_load((ROOT / ".github" / "workflows" / "verify.yml").read_text())
JOBS = WORKFLOW["jobs"]
#: Anything that reads, builds or runs what the author's repository holds.
EXECUTES_UPSTREAM = ("harness.engine", "detect_recipe.py", "propose_manifest.py", "prepare.py",
                     "docker ", "report.py", "generate_pdf.py", "pytest")


def _runs(job):
    return "\n".join(s.get("run", "") for s in JOBS[job]["steps"])


def test_no_permission_is_granted_outside_a_job():
    assert WORKFLOW["permissions"] == {}


def test_the_job_that_runs_the_tool_can_only_read():
    assert JOBS["verify"]["permissions"] == {"contents": "read"}
    assert "harness.engine run" in _runs("verify")
    # It pushes nothing and names no remote with a token.
    assert "git push" not in _runs("verify") and "x-access-token" not in _runs("verify")
    for step in JOBS["verify"]["steps"]:
        assert step.get("with", {}).get("persist-credentials", False) is False


def test_only_the_publish_job_can_write_and_it_executes_nothing_upstream():
    writers = [name for name, job in JOBS.items()
               if any(v == "write" for v in (job.get("permissions") or {}).values())]
    assert writers == ["publish"]
    assert JOBS["publish"]["permissions"] == {"contents": "write"}
    assert JOBS["publish"]["needs"] == "verify"
    runs = _runs("publish")
    for marker in EXECUTES_UPSTREAM:
        assert marker not in runs, marker
    uses = [s["uses"].split("@")[0] for s in JOBS["publish"]["steps"] if "uses" in s]
    assert uses == ["actions/checkout", "actions/setup-python", "actions/download-artifact"]


def test_publication_is_decided_again_where_the_write_token_is():
    condition = JOBS["publish"]["if"]
    assert "inputs.publish == 'true'" in condition and "refs/heads/main" in condition
    gate = next(s for s in JOBS["publish"]["steps"] if s.get("id") == "gate")
    assert "harness/publish_gate.py" in gate["run"]
    deploy = JOBS["publish"]["steps"][-1]
    assert deploy["if"] == "steps.gate.outputs.publishable == 'true'"
    assert "harness/publish_layout.py" in deploy["run"]


@pytest.mark.parametrize("slug", ["../outside", "a/b", ".git", "", "Hipstr"])
def test_a_report_cannot_choose_its_place_through_its_slug(tmp_path, slug):
    site = tmp_path / "site"; site.mkdir()
    reports = _run(tmp_path, NEW, "2026-02-01T00:00:00Z", "2026-09-01T00:00:00+00:00")
    with pytest.raises(SystemExit, match="not a slug"):
        pl.place(site, reports, slug)
    assert not list(site.iterdir())


@pytest.mark.parametrize("sha", ["../../outside", "abc1234", "A" * 40])
def test_a_report_cannot_choose_its_place_through_its_commit(tmp_path, sha):
    site = tmp_path / "site"; site.mkdir()
    reports = _run(tmp_path, NEW, "2026-02-01T00:00:00Z", "2026-09-01T00:00:00+00:00")
    r = json.loads((reports / f"{SLUG}.json").read_text())
    r["source"]["ref_resolved"] = sha
    (reports / f"{SLUG}.json").write_text(json.dumps(r))
    with pytest.raises(SystemExit):
        pl.place(site, reports, SLUG)
    assert not list(site.iterdir())


def test_a_link_in_the_reports_directory_is_not_published(tmp_path):
    site = tmp_path / "site"; site.mkdir()
    secret = tmp_path / "secret.txt"
    secret.write_text("not for publication")
    reports = _run(tmp_path, NEW, "2026-02-01T00:00:00Z", "2026-09-01T00:00:00+00:00")
    (reports / f"{SLUG}.log-build.txt").symlink_to(secret)
    pl.place(site, reports, SLUG)
    assert not (site / SLUG / NEW / f"{SLUG}.log-build.txt").exists()
    assert not (site / f"{SLUG}.log-build.txt").exists()
