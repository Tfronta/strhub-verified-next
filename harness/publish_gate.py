"""Whether a finished run goes to the catalogue: one decision, one place.

A failure of the tool is published like a success. It is the finding a paper
reviewer, a user who cannot get the tool running at home, and the tool's owner
all came for, and hiding it would make the catalogue a list of green badges.
What is never published:

  - a failure obtained in an environment STRhub prepared, until a control
    run exists: the same preparation, with the code corrected, running;
  - a run nobody asked to publish: the dispatch says `publish: true` or the
    result stays the run's artifact (the web always sends `false`);
  - a run whose verdict is not about the tool (out of scope, or STRhub's own
    infrastructure failed: the verdict's basis is "strhub");
  - a run filed under a card that belongs to another repository. The slug
    comes from the repository's NAME, so `someone/HipSTR` would land on
    HipSTR's card, and the alias goes to the newest commit date, which the
    committer sets. The requester still gets the full report as the run's
    artifact; only the card is protected.

Pure, so the policy is testable line by line. The workflow calls `main`.

    PUBLISH=true python harness/publish_gate.py --report reports/x.json --slug x --index published_index.json
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys

PUBLISHED_VERDICTS = ("runs", "fails", "undetermined")
INFRA_BASES = ("strhub_infra", "strhub")


def normalize_repo(url: str) -> str:
    """`https://github.com/Owner/Repo.git/` → `owner/repo`. GitHub names are
    case-insensitive, so the comparison is too."""
    u = (url or "").strip().lower()
    u = re.sub(r"^(?:https?://)?(?:www\.)?github\.com[/:]", "", u)
    u = re.sub(r"^git@github\.com:", "", u)
    u = u.rstrip("/")
    if u.endswith(".git"):
        u = u[:-4]
    return u


def card_owner(index: dict, slug: str) -> str | None:
    """The repository the published card `slug` belongs to, or None if there is
    no such card."""
    for t in (index or {}).get("tools", []):
        if t.get("slug") == slug:
            return t.get("source_repo") or ""
    return None


def validated_finding(report: dict):
    """The common evidence gate, including for direct layout/alias writers."""
    import authorization
    checked = authorization.report_validation(report)
    if not checked.valid:
        return checked
    verdict = report.get("verdict") or {}
    if verdict.get("code") not in PUBLISHED_VERDICTS or verdict.get("basis") in INFRA_BASES:
        return authorization.Validation(False, "The report is not an attributable publication finding.")
    return checked


def decide(report: dict, *, slug: str, publish_requested: bool, index: dict | None) -> tuple[bool, str]:
    """(publishable, why). `why` is one sentence for the run summary. `slug`
    is the name the report was written under (reports/<slug>.json)."""
    verdict = report.get("verdict") or {}
    code = verdict.get("code", "")
    if not publish_requested:
        return False, "the dispatch did not ask for this run to be published"
    if code not in PUBLISHED_VERDICTS:
        return False, f"verdict '{code or 'none'}' is not a finding about the tool"
    if verdict.get("basis") in INFRA_BASES:
        return False, "STRhub's own infrastructure failed; the run has to be repeated"
    checked = validated_finding(report)
    if not checked.valid:
        return False, "mandatory procedure evidence rejected: " + checked.reason
    if code == "fails" and report.get("preparation") and not (report.get("preparation") or {}).get("control"):
        # A failure in an environment STRhub prepared could be the preparation's.
        # It is a finding about the tool only once the same preparation, with
        # the code corrected, has been seen to run.
        return False, ("a failure obtained with STRhub's preparation is not published without a control run "
                       "(the same preparation, with the code corrected, running)")
    if not slug:
        return False, "the report has no slug to file it under"
    if index is None:
        # Fail closed: without the catalogue we cannot tell whose card this is.
        return False, "the published catalogue could not be read to check whose card this is"
    repo = (report.get("source") or {}).get("repo", "")
    owner = card_owner(index, slug)
    if owner is not None and normalize_repo(owner) != normalize_repo(repo):
        return False, f"the card '{slug}' belongs to {owner}; a run of {repo} does not publish on it"
    return True, "published"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", required=True)
    ap.add_argument("--slug", default="", help="the slug the report was written under (default: the file's stem)")
    ap.add_argument("--index", default="", help="the published index.json, if it could be read")
    args = ap.parse_args(argv)

    path = pathlib.Path(args.report)
    report = json.loads(path.read_text())
    index = None
    ip = pathlib.Path(args.index) if args.index else None
    if ip and ip.is_file():
        try:
            index = json.loads(ip.read_text())
        except ValueError:
            index = None
    ok, why = decide(report, slug=args.slug or path.stem,
                     publish_requested=os.environ.get("PUBLISH") == "true", index=index)
    print(f"publishable={'true' if ok else 'false'}")
    print(f"publish_reason={' '.join(why.split())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
