"""Where a run's files go on gh-pages, and which commit a tool's alias points at.

The unit published is a tool AT A COMMIT, not a tool. Every run lands in its
own directory, `<slug>/<sha>/`, with its files under the names the run wrote
them (so the HTML copy's relative links and the log names inside the JSON keep
working); the root `<slug>.*` set — what the web, the badge and shields read —
is an alias of the NEWEST commit among those directories, newest by the date
the commit was made, not by when it was verified.

That one rule is what lets anyone verify any commit from the form. Before it,
a slug was one file, and a run that published wrote over whatever was there:
someone verifying the first commit of STRspy v2 from strhub.app would have
replaced the current attestation with a two-year-old one. Now it lands below.
See docs/PLAN-Version-History.md.

This engine writes one kind of run: the repository's own instructions, read
at the pinned commit. Only such a run is placed, scanned or aliased here. A
file already on gh-pages that is anything else (certificate_text.
is_documented_run says no) is history this engine did not write: it is left
where it is, never moved, never deleted, and never the alias.

What holds it (harness/tests/test_publish_layout.py): a newer commit published
later becomes the alias; an older one does not move it; the same commit
re-verified replaces its files; a root set from before this layout is folded
into its place first, with its commit date fetched when missing, and competes
as an equal; no commit directory is ever deleted.

Usage (the deploy step, from a clone of gh-pages):
    python harness/publish_layout.py <site> --reports reports --slug hipstr
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import shutil
import sys
from typing import Callable

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import upstream  # noqa: E402
from certificate_text import is_documented_run, INSTRUMENT  # noqa: E402

#: A tombstone beside a run's files: the run stays where it is and its URL
#: keeps resolving, but it is no longer a result — never the alias, never
#: the note, and the index lists it as retired with the reason. Written by
#: `retire`, by hand, for a run that was STRhub's fault. Nothing is ever deleted.
TOMBSTONE = "retired.json"

#: How a report is looked up under its directory: the same stem the run wrote.
Resolver = Callable[[str, str], "str | None"]


def report_files(folder: pathlib.Path, slug: str) -> list[pathlib.Path]:
    """Every file of one run: `<slug>.json`, `.html`, `.pdf`, `.badge.json`,
    `.summary.md`, `.log-*.txt`, `.terminal-*.txt`. Not the recipe attachment,
    which the web reads out of the run's artifact; and not another slug that happens to share a prefix
    (`hipstr-y.json` does not start with `hipstr.`)."""
    return sorted(
        p for p in folder.iterdir()
        if p.is_file() and p.name.startswith(f"{slug}.")
        and not p.name.endswith(".recipe.json")
    )


def _read(path: pathlib.Path) -> dict | None:
    try:
        r = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    return r if isinstance(r, dict) and r.get("schema") == "strhub-verified/1" else None


def sha_of(report: dict) -> str | None:
    src = report.get("source") or {}
    return src.get("ref_resolved") or src.get("ref") or None


def rank(report: dict) -> tuple:
    """Newest first when sorted descending. A report that knows when its commit
    was made outranks one that does not; among those that do, the commit date
    decides; the verification date only breaks ties (a re-verified commit is
    the same commit)."""
    src = report.get("source") or {}
    committed = src.get("committed") or ""
    return (bool(committed), committed, report.get("generated") or "")


def _backfill(report: dict, path: pathlib.Path, resolve: Resolver | None) -> None:
    """Give a report its commit date when it has none and GitHub can say.
    Written back, so it is asked once."""
    if not resolve or (report.get("source") or {}).get("committed"):
        return
    repo = (report.get("source") or {}).get("repo") or ""
    sha = sha_of(report) or ""
    when = resolve(repo, sha) if repo and sha else None
    if when:
        report.setdefault("source", {})["committed"] = when
        path.write_text(json.dumps(report, indent=2))


def _move_set(files: list[pathlib.Path], dest: pathlib.Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for f in files:
        shutil.move(str(f), str(dest / f.name))


def _copy_set(files: list[pathlib.Path], dest: pathlib.Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for f in files:
        shutil.copy2(str(f), str(dest / f.name))


def fold_root(site: pathlib.Path, slug: str, resolve: Resolver | None = None) -> str | None:
    """A root set from before this layout becomes the directory of its commit.

    It was the newest at the time, and it must compete on its commit date
    like any other — so the date is fetched if the report predates it. Nothing
    is done when its directory already exists (the root is then the alias
    this module wrote, not a stranded set). Returns the sha folded, or None."""
    root_json = site / f"{slug}.json"
    report = _read(root_json) if root_json.exists() else None
    sha = sha_of(report) if report else None
    if not report or not sha or not is_documented_run(report):
        return None
    dest = site / slug / sha
    if (dest / f"{slug}.json").exists():
        return None
    _move_set(report_files(site, slug), dest)
    _backfill(report, dest / f"{slug}.json", resolve)
    return sha


def tombstone_of(folder: pathlib.Path) -> dict | None:
    try:
        t = json.loads((folder / TOMBSTONE).read_text())
    except (OSError, json.JSONDecodeError):
        return None
    return t if isinstance(t, dict) and t.get("retired") else None


def _with_tombstone(folder: pathlib.Path, r: dict) -> dict:
    """The report as scanned, carrying its tombstone when it has one. The
    file itself is not rewritten: the run is what it was, and the tombstone
    is a separate fact about it."""
    t = tombstone_of(folder)
    return {**r, "retired": t} if t else r


def scan(site: pathlib.Path, slug: str) -> list[tuple[str, dict]]:
    """Every run of `slug`: (sha, report), newest commit first. Reads what is
    there. A retired run is listed, with its tombstone under `retired`."""
    found = []
    base = site / slug
    if base.is_dir():
        for d in sorted(base.iterdir()):
            if not d.is_dir():
                continue
            r = _read(d / f"{slug}.json")
            if r and is_documented_run(r):
                found.append((d.name, _with_tombstone(d, r)))
    found.sort(key=lambda item: rank(item[1]), reverse=True)
    return found


def alias_source(site: pathlib.Path, slug: str) -> tuple[str, dict] | None:
    """The run the root alias copies: the newest commit among the runs whose
    procedure evidence still validates."""
    import publish_gate
    # Historical files remain readable; they do not acquire authority simply
    # by being on disk.
    runs = [r for r in scan(site, slug) if not r[1].get("retired")
            and publish_gate.validated_finding(r[1]).valid]
    return runs[0] if runs else None


def place(site: pathlib.Path, reports: pathlib.Path, slug: str,
          resolve: Resolver | None = None) -> dict:
    """Land one run and point the alias at the newest commit. Returns what was
    done: the run's sha, the alias's sha, and every commit known, newest first."""
    run_json = reports / f"{slug}.json"
    report = _read(run_json)
    if not report:
        raise SystemExit(f"{run_json}: not an attestation report")
    import publish_gate
    checked = publish_gate.validated_finding(report)
    if not checked.valid:
        raise SystemExit("mandatory procedure evidence rejected before publication: " + checked.reason)
    sha = sha_of(report)
    if not sha:
        raise SystemExit(f"{run_json}: no pinned commit (source.ref_resolved)")

    fold_root(site, slug, resolve)

    # This run's files, replaced whole: a re-verification of the same commit
    # must not keep a log the new run did not write. Files only: whatever
    # else sits in a subdirectory of that commit stays.
    if not is_documented_run(report):
        raise SystemExit(f"{run_json}: not a run of the repository's own instructions")
    target = site / slug / sha
    if (target / f"{slug}.json").exists() and not is_documented_run(_read(target / f"{slug}.json") or {}):
        raise SystemExit(f"{target}: holds a report this engine did not write; it is not replaced")
    target.mkdir(parents=True, exist_ok=True)
    for f in report_files(target, slug):
        f.unlink()
    _copy_set(report_files(reports, slug), target)
    _backfill(report, target / f"{slug}.json", resolve)

    alias = write_alias(site, slug)
    return {"slug": slug, "sha": sha, "instrument": INSTRUMENT, "alias": alias,
            "versions": [v_sha for v_sha, _ in scan(site, slug)]}


def write_alias(site: pathlib.Path, slug: str) -> str | None:
    """Point the root `<slug>.*` set at the run the badge may rest on (see
    alias_source), rewritten from scratch so nothing stale survives beside it.
    Returns the sha of the alias, or None when the slug has no such run."""
    src = alias_source(site, slug)
    if not src:
        # A withdrawal must not leave the former result at the root when
        # every run is retired. A root set this engine did not write stays.
        current = _read(site / f"{slug}.json")
        if current is None or is_documented_run(current):
            for f in report_files(site, slug):
                f.unlink()
        return None
    sha, _ = src
    for f in report_files(site, slug):
        f.unlink()
    _copy_set(report_files(site / slug / sha, slug), site)
    return sha


def retire(site: pathlib.Path, slug: str, sha: str, reason: str,
           when: str | None = None) -> pathlib.Path:
    """Put a tombstone beside one run and point the alias elsewhere. The
    run's files stay, so its URL keeps resolving; what changes is that it is
    no longer a result the site rests on. Returns the tombstone's path."""
    folder = site / slug / sha
    if not (folder / f"{slug}.json").exists():
        raise SystemExit(f"{folder}: no run of {slug} at {sha[:7]}")
    if not reason.strip():
        raise SystemExit("a retirement needs a reason")
    stone = folder / TOMBSTONE
    stone.write_text(json.dumps({
        "retired": when or dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "reason": reason.strip(),
    }, indent=2))
    write_alias(site, slug)
    return stone


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("site", help="a clone of gh-pages")
    ap.add_argument("--reports", default="reports", help="the run's reports/ directory")
    ap.add_argument("--slug", help="the slug the run published as")
    ap.add_argument("--retire", metavar="SHA",
                    help="no run: put a tombstone beside the run of --slug at this commit")
    ap.add_argument("--reason", default="", help="with --retire: why, for the reader")
    args = ap.parse_args()
    if not args.slug:
        ap.error("--slug is required")
    if args.retire:
        stone = retire(pathlib.Path(args.site), args.slug, args.retire, args.reason)
        print(f"retired {args.slug} @ {args.retire[:7]}: {stone}")
        return 0
    done = place(pathlib.Path(args.site), pathlib.Path(args.reports), args.slug,
                 resolve=upstream.commit_date)
    where = "" if done["alias"] == done["sha"] else f" (alias stays at {done['alias'][:7]})"
    print(f"{done['slug']} @ {done['sha'][:7]} placed; {len(done['versions'])} run(s) known{where}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
