"""The alias points at the newest commit, whatever order things were verified in.

A slug used to be one file that every publishing run wrote over, so verifying
an old commit from the form would have replaced the current attestation with
an older one. Now every run lands in `<slug>/<sha>/` and the root set is an
alias of the newest commit — newest by when the commit was made."""
import json
import pathlib

import publish_layout as pl
from procedure_context import report as bound_report

SLUG = "hipstr"
REPO = "https://github.com/tfwillems/HipSTR"
OLD, NEW, NEWER = "a" * 40, "b" * 40, "c" * 40


def _report(sha, committed, generated, level="content", instrument="documented"):
    r = {**bound_report(repo=REPO, ref=sha), "instrument": instrument, "level": level,
         "generated": generated, "scope": "x", "logs": {"external": f"{SLUG}.log-external.txt"}}
    if committed:
        r["source"]["committed"] = committed
    return r


def _run(tmp_path, sha, committed, generated, logs=("external",), name="reports", instrument="documented"):
    """A run's reports/ directory, as the workflow leaves it."""
    d = tmp_path / name
    d.mkdir(exist_ok=True)
    for f in d.iterdir():
        f.unlink()
    (d / f"{SLUG}.json").write_text(json.dumps(_report(sha, committed, generated, instrument=instrument)))
    (d / f"{SLUG}.html").write_text(f"<html>{sha}</html>")
    (d / f"{SLUG}.pdf").write_bytes(b"%PDF " + sha.encode())
    (d / f"{SLUG}.badge.json").write_text("{}")
    (d / f"{SLUG}.summary.md").write_text(f"# {sha}")
    for leg in logs:
        (d / f"{SLUG}.log-{leg}.txt").write_text(f"log {leg} {sha}")
    (d / f"{SLUG}.recipe.json").write_text("{}")          # never published
    (d / "hipstr-y.json").write_text(json.dumps(_report(sha, committed, generated)))  # another slug
    return d


def _alias_sha(site):
    return json.loads((site / f"{SLUG}.json").read_text())["source"]["ref_resolved"]


def test_a_run_lands_in_its_commits_directory_and_becomes_the_alias(tmp_path):
    site = tmp_path / "site"; site.mkdir()
    done = pl.place(site, _run(tmp_path, NEW, "2026-02-01T00:00:00Z", "2026-09-01T00:00:00+00:00"), SLUG)
    assert done["sha"] == NEW and done["alias"] == NEW and done["instrument"] == "documented"
    assert done["versions"] == [NEW]
    assert (site / SLUG / NEW / f"{SLUG}.json").exists()
    assert (site / SLUG / NEW / f"{SLUG}.log-external.txt").read_text() == f"log external {NEW}"
    assert _alias_sha(site) == NEW
    assert (site / f"{SLUG}.pdf").read_bytes().endswith(NEW.encode())
    # The recipe attachment and the other slug's file stayed out.
    assert not (site / SLUG / NEW / f"{SLUG}.recipe.json").exists()
    assert not (site / "hipstr-y.json").exists() and not (site / SLUG / NEW / "hipstr-y.json").exists()


def test_an_older_commit_published_later_lands_below_and_does_not_move_the_alias(tmp_path):
    site = tmp_path / "site"; site.mkdir()
    pl.place(site, _run(tmp_path, NEW, "2026-02-01T00:00:00Z", "2026-09-01T00:00:00+00:00"), SLUG)
    # Verified LATER, but a commit made two years EARLIER.
    done = pl.place(site, _run(tmp_path, OLD, "2024-03-10T00:00:00Z", "2026-09-18T00:00:00+00:00"), SLUG)
    assert done["alias"] == NEW and done["versions"] == [NEW, OLD]
    assert _alias_sha(site) == NEW
    assert (site / SLUG / OLD / f"{SLUG}.json").exists()


def test_a_newer_commit_published_later_takes_the_alias(tmp_path):
    site = tmp_path / "site"; site.mkdir()
    pl.place(site, _run(tmp_path, NEW, "2026-02-01T00:00:00Z", "2026-09-01T00:00:00+00:00"), SLUG)
    done = pl.place(site, _run(tmp_path, NEWER, "2026-08-01T00:00:00Z", "2026-09-18T00:00:00+00:00"), SLUG)
    assert done["alias"] == NEWER and done["versions"] == [NEWER, NEW]
    assert _alias_sha(site) == NEWER
    assert (site / f"{SLUG}.html").read_text() == f"<html>{NEWER}</html>"


def test_the_same_commit_reverified_replaces_its_directory_whole(tmp_path):
    site = tmp_path / "site"; site.mkdir()
    pl.place(site, _run(tmp_path, NEW, "2026-02-01T00:00:00Z", "2026-06-01T00:00:00+00:00", logs=("example", "external")), SLUG)
    assert (site / SLUG / NEW / f"{SLUG}.log-example.txt").exists() and (site / f"{SLUG}.log-example.txt").exists()
    done = pl.place(site, _run(tmp_path, NEW, "2026-02-01T00:00:00Z", "2026-09-01T00:00:00+00:00", logs=("external",)), SLUG)
    assert done["versions"] == [NEW]
    # A log the new run did not write is gone from the directory AND the alias.
    assert not (site / SLUG / NEW / f"{SLUG}.log-example.txt").exists()
    assert not (site / f"{SLUG}.log-example.txt").exists()
    assert json.loads((site / f"{SLUG}.json").read_text())["generated"].startswith("2026-09")


def test_a_root_set_from_before_the_layout_is_folded_in_and_dated(tmp_path):
    """What is on gh-pages today: one flat set per slug, no directory, and a
    report that never recorded when its commit was made. It was the newest at
    the time; it has to compete as one, so its date is fetched once."""
    site = tmp_path / "site"; site.mkdir()
    legacy = _run(tmp_path, NEW, None, "2026-09-01T00:00:00+00:00", name="legacy")
    for f in pl.report_files(legacy, SLUG):
        f.rename(site / f.name)
    asked = []

    def resolve(repo, sha):
        asked.append((repo, sha))
        return "2026-02-01T00:00:00Z"

    # An OLDER commit arrives after the layout change.
    done = pl.place(site, _run(tmp_path, OLD, "2024-03-10T00:00:00Z", "2026-09-18T00:00:00+00:00"), SLUG, resolve=resolve)
    assert asked == [(REPO, NEW)]
    assert done["alias"] == NEW and done["versions"] == [NEW, OLD]
    folded = json.loads((site / SLUG / NEW / f"{SLUG}.json").read_text())
    assert folded["source"]["committed"] == "2026-02-01T00:00:00Z"
    assert _alias_sha(site) == NEW


def test_a_report_without_a_commit_date_ranks_below_every_dated_one(tmp_path):
    """No GitHub to ask (the resolver returns nothing): a dated commit wins,
    and the undated one is still kept and listed."""
    site = tmp_path / "site"; site.mkdir()
    pl.place(site, _run(tmp_path, NEW, None, "2026-09-18T00:00:00+00:00"), SLUG, resolve=lambda repo, sha: None)
    done = pl.place(site, _run(tmp_path, OLD, "2024-03-10T00:00:00Z", "2026-09-01T00:00:00+00:00"), SLUG, resolve=lambda repo, sha: None)
    assert done["versions"] == [OLD, NEW] and done["alias"] == OLD


def test_no_commit_directory_is_ever_deleted(tmp_path):
    site = tmp_path / "site"; site.mkdir()
    for sha, when in ((OLD, "2024-03-10T00:00:00Z"), (NEW, "2026-02-01T00:00:00Z"), (NEWER, "2026-08-01T00:00:00Z")):
        pl.place(site, _run(tmp_path, sha, when, "2026-09-18T00:00:00+00:00"), SLUG)
    assert sorted(p.name for p in (site / SLUG).iterdir()) == sorted([OLD, NEW, NEWER])
    assert [s for s, _ in pl.scan(site, SLUG)] == [NEWER, NEW, OLD]


def test_a_run_that_is_not_a_report_is_refused(tmp_path):
    site = tmp_path / "site"; site.mkdir()
    bad = tmp_path / "bad"; bad.mkdir()
    (bad / f"{SLUG}.json").write_text(json.dumps({"schema": "strhub-verified/index/2"}))
    try:
        pl.place(site, bad, SLUG)
    except SystemExit as exc:
        assert "not an attestation report" in str(exc)
    else:
        raise AssertionError("an index was accepted as a run")


OTHER = "something-this-engine-does-not-write"


def test_a_run_that_is_not_of_the_repository_s_instructions_is_refused(tmp_path):
    site = tmp_path / "site"; site.mkdir()
    try:
        pl.place(site, _run(tmp_path, NEW, "2026-02-01T00:00:00Z", "2026-09-01T00:00:00+00:00", instrument=OTHER), SLUG)
    except SystemExit as exc:
        assert "not a run of the repository's own instructions" in str(exc)
    else:
        raise AssertionError("a report this engine does not write was placed")
    assert not list(site.iterdir())


def test_history_this_engine_did_not_write_is_left_where_it_is_and_never_the_alias(tmp_path):
    """gh-pages may hold reports from before this engine: at the root, in a
    commit's directory, in a subdirectory of one. None is moved, deleted,
    listed as a run or aliased; a run of ours takes the root."""
    site = tmp_path / "site"; site.mkdir()
    legacy = _run(tmp_path, NEW, "2026-02-01T00:00:00Z", "2026-09-01T00:00:00+00:00", name="legacy", instrument=OTHER)
    below = site / SLUG / NEW / "elsewhere"
    pl._copy_set(pl.report_files(legacy, SLUG), below)
    pl._copy_set(pl.report_files(legacy, SLUG), site)
    kept = (below / f"{SLUG}.json").read_text()
    assert pl.scan(site, SLUG) == [] and pl.alias_source(site, SLUG) is None
    # With no run of ours, rewriting the alias leaves the root as it was.
    assert pl.write_alias(site, SLUG) is None
    assert json.loads((site / f"{SLUG}.json").read_text())["instrument"] == OTHER
    # An OLDER commit, verified by this engine, takes the alias.
    done = pl.place(site, _run(tmp_path, OLD, "2024-03-10T00:00:00Z", "2026-09-18T00:00:00+00:00"), SLUG)
    assert done["alias"] == OLD and done["versions"] == [OLD]
    assert _alias_sha(site) == OLD
    assert (below / f"{SLUG}.json").read_text() == kept


def test_a_retired_run_stays_where_it_is_but_is_never_the_alias(tmp_path):
    """A tombstone, never a deletion: the files stay, the URL resolves, the
    index says retired and why, and the alias rests on something else."""
    import build_index
    site = tmp_path / "site"; site.mkdir()
    pl.place(site, _run(tmp_path, NEW, "2026-02-01T00:00:00Z", "2026-09-01T00:00:00+00:00"), SLUG)
    pl.place(site, _run(tmp_path, OLD, "2024-03-10T00:00:00Z", "2026-09-18T00:00:00+00:00"), SLUG)
    assert _alias_sha(site) == NEW
    stone = pl.retire(site, SLUG, NEW, "the run was STRhub's fault", when="2026-09-20T00:00:00+00:00")
    assert stone == site / SLUG / NEW / pl.TOMBSTONE
    assert (site / SLUG / NEW / f"{SLUG}.json").exists()                       # nothing deleted
    assert _alias_sha(site) == OLD                                             # the alias moved
    (entry,) = build_index.build_catalogue(site)["tools"]
    assert entry["sha"] == OLD and "retired" not in entry
    new_row = next(v for v in entry["versions"] if v["sha"] == NEW)
    assert new_row["retired"] == {"retired": "2026-09-20T00:00:00+00:00", "reason": "the run was STRhub's fault"}
    assert "retired" not in next(v for v in entry["versions"] if v["sha"] == OLD)
    # A tool whose every run is retired has no alias at all.
    pl.retire(site, SLUG, OLD, "same", when="2026-09-20T00:00:00+00:00")
    assert pl.alias_source(site, SLUG) is None
    assert not pl.report_files(site, SLUG)
