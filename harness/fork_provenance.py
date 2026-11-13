"""When the repository under test is a fork: of what, and what it changes.

A fork is how documentation, example data or a fix gets added to a tool
without touching its author's repository. A report on a fork must not read as
a report on the original, and must not leave the reader to find out what the
fork did. So the report says which repository it is a fork of, and sorts every
file the pinned commit changes against the original into three kinds:

  documentation  README and other prose, the docs folder, licence, images
  data           sequence, alignment, variant and region files
  code           everything else: sources, scripts, build files, configuration

`kind` is the one word a reader needs: `documentation_only`,
`documentation_and_data` (the code is the original author's) or `code` (the
fork changes how the tool behaves). Anything not recognised counts as code.

The original's branch compared against is the one the fork's commit differs
least from, so a fork of a release branch is not charged with that branch's
own commits. Costs a few API calls; every failure returns None and the report
then says nothing rather than guess.
"""
from __future__ import annotations

import os
import re

import upstream

MAX_BRANCHES = 12
#: GitHub lists at most this many files in a comparison.
FILE_LIMIT = 300
LISTED = 25

DOCUMENTATION = re.compile(
    r"(?:^|/)(?:README|LICEN[CS]E|COPYING|CITATION|CHANGELOG|CHANGES|NEWS|AUTHORS|CONTRIBUTING)[^/]*$"
    r"|\.(?:md|rst|markdown|adoc|pdf|png|jpe?g|gif|svg)$"
    r"|^(?:docs?|documentation)/", re.I)
DATA = re.compile(
    r"\.(?:bam|bai|cram|crai|sam|fastq|fq|fasta|fa|fna|fai|vcf|bcf|tbi|csi|bed|gff3?|gtf)(?:\.gz|\.bgz)?$", re.I)


def classify(path: str) -> str:
    if DOCUMENTATION.search(path):
        return "documentation"
    if DATA.search(path):
        return "data"
    return "code"


def provenance(repo_url: str, sha: str, token: str | None = None, get=None) -> dict | None:
    """What `sha` of `repo_url` changes against the repository it is a fork
    of; `{"is_fork": False}` for a repository that is nobody's fork; None
    when GitHub could not say."""
    get = get or upstream._get
    slug = upstream.repo_slug(repo_url)
    if not slug or not re.fullmatch(r"[0-9a-f]{40}", sha or ""):
        return None
    token = token or os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    repo = get(f"/repos/{slug}", token)
    if not repo or repo.get("__status__") == 404:
        return None
    if not repo.get("fork"):
        return {"is_fork": False}
    parent = repo.get("parent") or {}
    full, owner = parent.get("full_name"), (parent.get("owner") or {}).get("login")
    if not full or not owner:
        return None
    listed = get(f"/repos/{full}/branches?per_page={MAX_BRANCHES}", token)
    names = [b.get("name") for b in listed] if isinstance(listed, list) else []
    default = parent.get("default_branch")
    branches = [default] + [n for n in names if n and n != default] if default else [n for n in names if n]

    best = None
    for branch in branches[:MAX_BRANCHES]:
        compared = get(f"/repos/{slug}/compare/{owner}:{branch}...{sha}", token)
        if not compared or compared.get("__status__") == 404 or not isinstance(compared.get("files"), list):
            continue
        key = (len(compared["files"]), compared.get("ahead_by") or 0)
        if best is None or key < best[0]:
            best = (key, branch, compared)
    if best is None:
        return None
    _, branch, compared = best
    changed: dict[str, list[str]] = {"documentation": [], "data": [], "code": []}
    for f in compared["files"]:
        changed[classify(f.get("filename") or "")].append(f.get("filename") or "")
    counts = {kind: len(paths) for kind, paths in changed.items()}
    truncated = len(compared["files"]) >= FILE_LIMIT
    if counts["code"] or truncated:
        # Past the listing limit the rest is unseen, and unseen counts as code.
        kind = "code"
    elif counts["data"]:
        kind = "documentation_and_data"
    else:
        kind = "documentation_only"
    return {
        "is_fork": True,
        "parent": full,
        "parent_url": f"https://github.com/{full}",
        "base_branch": branch,
        "merge_base": (compared.get("merge_base_commit") or {}).get("sha"),
        "ahead_by": compared.get("ahead_by"),
        "behind_by": compared.get("behind_by"),
        "files_changed": len(compared["files"]),
        "truncated": truncated,
        "counts": counts,
        "changed": {kind_: sorted(paths)[:LISTED] for kind_, paths in changed.items()},
        "kind": kind,
        "compare_url": compared.get("html_url"),
    }


def note(fork: dict | None) -> str:
    """One sentence for the prose copies; empty for a repository that is not a fork."""
    if not fork or not fork.get("is_fork"):
        return ""
    c = fork.get("counts") or {}
    what = {"documentation_only": "It changes documentation only: the code is the original's.",
            "documentation_and_data": "It changes documentation and data files, not code: the code is the original's.",
            "code": "It changes code, so this result is about the fork and not about the original."}[fork["kind"]]
    more = " The listing reached GitHub's limit, so further changes are not shown and are counted as code." \
        if fork.get("truncated") else ""
    return (f"This repository is a fork of {fork['parent']} (compared with its branch {fork['base_branch']}): "
            f"{fork.get('files_changed', 0)} file(s) differ, {c.get('documentation', 0)} documentation, "
            f"{c.get('data', 0)} data, {c.get('code', 0)} code. {what}{more}")
