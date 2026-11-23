"""Publish a mechanically recorded local manual verification bundle to gh-pages.

Strict safety guarantees:
  - Validates the bundle JSON (`instrument == "curated"`, full 40-char commit SHA,
    terminal evidence file present on disk, zero personal path/hostname leaks).
  - Places files strictly under `<slug>/<sha>-curated/`, NEVER touching the
    automatic root alias `<slug>.*`.
  - Rebuilds `index.json` + `index.html` using `harness/build_index.py`.
  - Defaults to dry-run; passes `--push` explicitly to commit & push `gh-pages`.

Usage:
    python harness/publish_manual.py --bundle /tmp/manual-bundle-strspy --slug strspy-ont --push
"""
from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import build_index  # noqa: E402
import manual_record  # noqa: E402
import publish_layout  # noqa: E402

DEFAULT_REMOTE = "https://github.com/Tfronta/strhub-verified-next.git"


def validate_bundle(bundle: pathlib.Path, slug: str) -> dict:
    if not publish_layout.SAFE_SLUG.fullmatch(slug or ""):
        raise ValueError(f"Invalid slug: {slug!r}")
    report_path = bundle / f"{slug}.json"
    if not report_path.is_file():
        raise ValueError(f"Missing report JSON: {report_path}")
    text = report_path.read_text(encoding="utf-8")
    report = json.loads(text)
    if report.get("schema") != "strhub-verified/1":
        raise ValueError(f"Unexpected schema: {report.get('schema')!r}")
    if report.get("instrument") != "curated":
        raise ValueError(f"Manual bundle must have instrument='curated', got {report.get('instrument')!r}")
    sha = publish_layout.sha_of(report)
    if not sha or not publish_layout.FULL_SHA.fullmatch(sha):
        raise ValueError(f"Missing or invalid full 40-char source.ref_resolved: {sha!r}")

    term_name = (report.get("terminals") or {}).get("external") or (report.get("logs") or {}).get("external")
    if not term_name or not (bundle / term_name).is_file():
        raise ValueError(f"Manual bundle must include recorded terminal/log evidence file: {term_name!r}")

    leaks = manual_record.find_personal_leaks(text)
    leaks += manual_record.find_personal_leaks((bundle / term_name).read_text(encoding="utf-8", errors="replace"))
    if leaks:
        raise ValueError(f"Refusing to publish: personal path/host tokens detected: {sorted(set(leaks))}")
    return report


def place_manual(site: pathlib.Path, bundle: pathlib.Path, slug: str) -> dict:
    """Copy a validated manual bundle into `<site>/<slug>/<sha>-curated/` and rebuild index."""
    report = validate_bundle(bundle, slug)
    sha = publish_layout.sha_of(report)
    assert sha is not None
    folder_name = f"{sha}-curated"
    target = site / slug / folder_name
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)
    for f in sorted(bundle.iterdir()):
        if f.is_file() and f.name.startswith(f"{slug}."):
            shutil.copy2(f, target / f.name)

    # Rebuild catalogue index without altering any documented root alias.
    (site / "index.html").write_text(build_index.render(site), encoding="utf-8")
    cat = build_index.build_catalogue(site)
    (site / "index.json").write_text(json.dumps(cat, indent=2) + "\n", encoding="utf-8")
    return {
        "slug": slug,
        "sha": sha,
        "folder": f"{slug}/{folder_name}",
        "verdict": (report.get("verdict") or {}).get("code"),
        "level": report.get("level"),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Publish a recorded manual verification bundle to gh-pages.")
    ap.add_argument("--bundle", required=True, help="Directory created by harness/manual_record.py")
    ap.add_argument("--slug", required=True, help="Catalogue slug (e.g. strspy-ont)")
    ap.add_argument("--remote", default=DEFAULT_REMOTE, help="Git remote holding gh-pages")
    ap.add_argument("--push", action="store_true", help="Actually commit and push to gh-pages (default: dry-run)")
    args = ap.parse_args(argv)

    bundle = pathlib.Path(args.bundle).resolve()
    validate_bundle(bundle, args.slug)

    tmp = pathlib.Path(tempfile.mkdtemp(prefix="publish-manual."))
    try:
        subprocess.run(
            ["git", "clone", "-q", "--depth", "1", "--branch", "gh-pages", args.remote, str(tmp)],
            check=True,
        )
        done = place_manual(tmp, bundle, args.slug)
        print(
            f"Prepared {done['folder']} (verdict={done['verdict']}, level={done['level']})."
        )
        if not args.push:
            print("Dry-run only (pass --push to publish to gh-pages).")
            return 0
        subprocess.run(["git", "-C", str(tmp), "add", "-A"], check=True)
        subprocess.run(
            [
                "git", "-C", str(tmp), "commit", "-q", "-m",
                f"manual: publish {args.slug} @ {done['sha'][:7]} ({done['verdict']})",
            ],
            check=True,
        )
        subprocess.run(["git", "-C", str(tmp), "push", "origin", "gh-pages"], check=True)
        print(f"Published {done['folder']} to gh-pages.")
        print(f"Web URL: https://strhub.app/verified/{args.slug}?at={done['sha'][:7]}&recipe=curated")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
