"""Record a local manual verification run with mechanical integrity and privacy hygiene.

Manual verification runs on a real workstation (including GPU / high-RAM / Conda /
interactive setups) against an unmodified checkout of the official upstream repo
at a pinned commit. This tool guarantees:

  1. Identity integrity: checks `git remote get-url origin`, full commit SHA
     (`HEAD`), and `git status --porcelain` so modified source files or a fork
     can NEVER be recorded as an official upstream commit.
  2. Privacy hygiene: runs via subprocess (no shell prompt) and strips local
     paths ($HOME, checkout path, input/output dirs), local username, and
     machine hostname (including macOS ComputerName) before writing any file.
  3. Mechanical evidence: captures verbatim sanitized terminal output, exit
     code, and runs the same VCF/TSV output validators (`vcf_structure` /
     `content_auto`) to set `gates`, `level`, and `verdict` mechanically.
  4. Author-first editorial notes: reads optional human notes from a YAML file
     (environment description, why manual was needed, suggestions for the
     author, and optional `pr_url` / `fork_url` / `proposed_fix_note`).

Usage:
    python harness/manual_record.py \\
      --slug strspy-ont \\
      --repo https://github.com/unique379r/strspy \\
      --checkout /tmp/upstream-strspy \\
      --cmd "bash ./STRspy_run_v2.0_Args.sh config/InputConfig.txt config/ToolsConfig.txt" \\
      --notes manual_notes/strspy.yml \\
      --out-dir /tmp/manual-bundle-strspy
"""
from __future__ import annotations

import argparse
import datetime as dt
import getpass
import html as html_lib
import json
import pathlib
import platform
import re
import socket
import subprocess
import sys
from typing import Iterable

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import content_auto  # noqa: E402
import publish_gate  # noqa: E402
import vcf_structure  # noqa: E402

FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
PERSONAL_PATH_RE = re.compile(r"(?:/Users/[A-Za-z0-9._-]+|/home/[A-Za-z0-9._-]+|MacBook[^/\s]*)", re.I)

LEVEL_LABELS = {
    "none": "Not run",
    "available": "Available",
    "installs": "Installs",
    "runs": "Runs",
    "io": "Runs + Expected IO",
    "content": "Runs + Plausible output",
}


def _git(checkout: pathlib.Path, *args: str, strip: bool = True) -> str:
    res = subprocess.run(
        ["git", "-C", str(checkout), *args],
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        raise ValueError(f"git {' '.join(args)} failed in {checkout}: {res.stderr.strip()}")
    return res.stdout.strip() if strip else res.stdout


def verify_checkout(
    checkout: pathlib.Path,
    expected_repo: str,
    expected_sha: str | None = None,
    allow_untracked: Iterable[str] = (),
) -> dict:
    """Verify the checkout matches the official repo + pinned commit with no tracked edits."""
    checkout = checkout.resolve()
    if not (checkout / ".git").exists():
        raise ValueError(f"{checkout} is not a git repository")

    origin = _git(checkout, "remote", "get-url", "origin")
    if publish_gate.normalize_repo(origin) != publish_gate.normalize_repo(expected_repo):
        raise ValueError(
            f"Checkout origin ({origin}) does not match --repo ({expected_repo}). "
            "Never record a fork as an official upstream commit."
        )

    sha = _git(checkout, "rev-parse", "HEAD").lower()
    if not FULL_SHA_RE.match(sha):
        raise ValueError(f"Could not resolve full 40-char HEAD SHA in {checkout}: {sha!r}")
    if expected_sha and not sha.startswith(expected_sha.strip().lower()):
        raise ValueError(f"Checkout HEAD ({sha}) does not match expected --sha ({expected_sha})")

    committed = _git(checkout, "show", "-s", "--format=%cI", "HEAD")

    # Refuse any modified/staged/deleted tracked file. Untracked files are allowed
    # only if explicitly listed via --allow-untracked (e.g. a generated config file).
    allowed_set = {p.strip().lstrip("./") for p in allow_untracked if p.strip()}
    status_lines = _git(checkout, "status", "--porcelain", "--untracked-files=all", strip=False).splitlines()
    bad: list[str] = []
    for line in status_lines:
        if not line.strip():
            continue
        code = line[:2]
        rel = line[3:].strip().strip('"').lstrip("./")
        if code == "??" and rel in allowed_set:
            continue
        bad.append(f"{code} {rel}")
    if bad:
        raise ValueError(
            "Checkout has modified or unexpected files (upstream code must be unmodified): "
            + ", ".join(bad)
        )

    return {
        "repo": f"https://github.com/{publish_gate.normalize_repo(expected_repo)}",
        "repo_display": expected_repo.rstrip("/"),
        "sha": sha,
        "committed": committed,
    }


def _macos_computer_names() -> list[str]:
    if sys.platform != "darwin":
        return []
    names: list[str] = []
    for key in ("ComputerName", "LocalHostName", "HostName"):
        try:
            res = subprocess.run(["scutil", "--get", key], capture_output=True, text=True, timeout=2)
            if res.returncode == 0 and res.stdout.strip():
                names.append(res.stdout.strip())
        except Exception:
            pass
    return names


def build_redactions(
    checkout: pathlib.Path,
    *,
    input_dir: pathlib.Path | None = None,
    output_dir: pathlib.Path | None = None,
    extra_redact: Iterable[str] = (),
) -> list[tuple[str, str]]:
    """Build ordered (needle, replacement) pairs to strip all local paths & machine identity."""
    pairs: list[tuple[str, str]] = []
    pairs.append((str(checkout.resolve()), "/work"))
    if input_dir is not None:
        pairs.append((str(input_dir.resolve()), "/data/in"))
    if output_dir is not None:
        pairs.append((str(output_dir.resolve()), "/data/out"))

    home = str(pathlib.Path.home().resolve())
    if home and home != "/":
        pairs.append((home, "<HOME>"))

    user = getpass.getuser()
    if user and len(user) >= 3:
        pairs.append((user, "<user>"))

    host_candidates = {
        socket.gethostname(),
        platform.node(),
        *_macos_computer_names(),
    }
    for h in host_candidates:
        h = (h or "").strip()
        if h and len(h) >= 3:
            pairs.append((h, "<host>"))
            if "." in h:
                short = h.split(".")[0]
                if len(short) >= 3:
                    pairs.append((short, "<host>"))

    for item in extra_redact:
        item = (item or "").strip()
        if item:
            pairs.append((item, "<redacted>"))

    # Longest needles first so /Users/tfronta/project becomes /work before /Users/tfronta -> <HOME>.
    seen: set[str] = set()
    ordered: list[tuple[str, str]] = []
    for needle, repl in sorted(pairs, key=lambda kv: len(kv[0]), reverse=True):
        if needle not in seen:
            seen.add(needle)
            ordered.append((needle, repl))
    return ordered


def sanitize_text(text: str, redactions: list[tuple[str, str]]) -> str:
    out = text
    for needle, repl in redactions:
        if not needle:
            continue
        if repl == "<host>":
            out = re.sub(re.escape(needle), repl, out, flags=re.I)
        else:
            out = out.replace(needle, repl)
    return out


def find_personal_leaks(text: str) -> list[str]:
    return sorted(set(PERSONAL_PATH_RE.findall(text or "")))


def _validate_outputs(
    output_dir: pathlib.Path | None,
    output_glob: str | None,
    regions_file: pathlib.Path | None = None,
) -> tuple[bool, bool, dict | None, dict | None]:
    """Validate outputs produced by a successful local run using STRhub's own validators."""
    if not output_dir or not output_dir.exists():
        return False, False, None, None

    patterns = [output_glob] if output_glob else ["**/*.vcf.gz", "**/*.vcf", "**/*.tsv", "**/*.txt", "**/*.csv"]
    matches: list[pathlib.Path] = []
    for pat in patterns:
        found = [p for p in sorted(output_dir.glob(pat)) if p.is_file() and p.stat().st_size > 0]
        if found:
            matches = found
            break

    if not matches:
        return False, False, {"gate": "io", "passed": False, "outputs": []}, None

    target = matches[0]
    rel = str(target.relative_to(output_dir))
    name_low = target.name.lower()
    is_vcf = name_low.endswith(".vcf") or name_low.endswith(".vcf.gz")
    fmt = "vcf" if is_vcf else ("csv" if name_low.endswith(".csv") else "tsv")

    if is_vcf:
        try:
            summary = vcf_structure.validate(vcf_structure.read(target))
            io_passed = summary.records > 0 and (summary.uncalled_rows == 0 or summary.called_records > 0)
            io_entry = {
                "path": output_glob or "**/*.vcf*",
                "format": "vcf",
                "resolved": rel,
                "validation_profile": vcf_structure.PROFILE,
                "validation_status": "valid",
                "records": summary.records,
                "called_records": summary.called_records,
                "uncalled_rows": summary.uncalled_rows,
                "records_without_gt": summary.records_without_gt,
                "checks": {
                    "exists": True,
                    "non_empty": True,
                    "parses_as_vcf": True,
                    "min_records": summary.records > 0,
                    "has_called_genotypes": summary.uncalled_rows == 0 or summary.called_records > 0,
                },
                "passed": io_passed,
            }
            regions = content_auto.read_regions(regions_file) if regions_file else []
            stats = content_auto.analyze_vcf(target, regions)
            checks = content_auto.judge(stats, "vcf", len(regions))
            content_passed = io_passed and all(checks.values())
            content_detail = {
                "gate": "content",
                "applicable": True,
                "passed": content_passed,
                "outputs": [{"path": io_entry["path"], "resolved": rel, "mode": "auto", "checks": checks, "stats": stats}],
            }
            return io_passed, content_passed, {"gate": "io", "passed": io_passed, "outputs": [io_entry]}, content_detail
        except Exception as exc:
            io_entry = {
                "path": output_glob or "**/*.vcf*",
                "format": "vcf",
                "resolved": rel,
                "validation_status": "invalid",
                "parse_error": str(exc),
                "checks": {"exists": True, "non_empty": True, "parses_as_vcf": False},
                "passed": False,
            }
            return False, False, {"gate": "io", "passed": False, "outputs": [io_entry]}, None

    # Tabular output (TSV/CSV/TXT)
    stats = content_auto.analyze_table(target, fmt=fmt, panel_names=set())
    records = int(stats.get("rows", 0))
    io_passed = records > 0
    io_entry = {
        "path": output_glob or f"**/*.{fmt}",
        "format": fmt,
        "resolved": rel,
        "records": records,
        "checks": {"exists": True, "non_empty": True, f"parses_as_{fmt}": True, "min_records": io_passed},
        "passed": io_passed,
    }
    checks = content_auto.judge(stats, fmt, 0)
    content_passed = io_passed and all(checks.values())
    content_detail = {
        "gate": "content",
        "applicable": True,
        "passed": content_passed,
        "outputs": [{"path": io_entry["path"], "resolved": rel, "mode": "auto", "checks": checks, "stats": stats}],
    }
    return io_passed, content_passed, {"gate": "io", "passed": io_passed, "outputs": [io_entry]}, content_detail


def _render_static_html(report: dict, terminal_text: str) -> str:
    tool = report["tool"]
    verdict = report["verdict"]
    title = html_lib.escape(f"{tool.get('name', 'Tool')} {tool.get('version') or ''} — STRhub Manual Verification".strip())
    return (
        "<!doctype html>\n<html lang='en'><head><meta charset='utf-8'>"
        f"<title>{title}</title>"
        "<style>body{font:15px/1.6 system-ui,sans-serif;max-width:860px;margin:2rem auto;padding:0 1rem;color:#1f2937}"
        "pre{background:#111827;color:#f3f4f6;padding:1rem;border-radius:8px;overflow:auto;font-size:12px}"
        ".pill{display:inline-block;padding:2px 10px;border-radius:999px;background:#eef2ff;color:#312e81;font-weight:600;font-size:12px}</style>"
        f"</head><body><span class='pill'>Manual Verification · {html_lib.escape(verdict.get('code', ''))}</span>"
        f"<h1>{html_lib.escape(tool.get('name', ''))} {html_lib.escape(str(tool.get('version') or ''))}</h1>"
        f"<p><strong>Commit:</strong> <code>{html_lib.escape(report['source']['ref_resolved'])}</code></p>"
        f"<p>{html_lib.escape(verdict.get('reason', ''))}</p>"
        f"<h2>Recorded Terminal</h2><pre>{html_lib.escape(terminal_text)}</pre></body></html>\n"
    )


def record_manual_run(
    *,
    slug: str,
    repo: str,
    checkout: pathlib.Path,
    cmd: str,
    out_dir: pathlib.Path,
    version: str | None = None,
    expected_sha: str | None = None,
    allow_untracked: Iterable[str] = (),
    input_dir: pathlib.Path | None = None,
    output_dir: pathlib.Path | None = None,
    output_glob: str | None = None,
    regions_file: pathlib.Path | None = None,
    notes_path: pathlib.Path | None = None,
    install_failed: bool = False,
    timeout_seconds: int = 1800,
    extra_redact: Iterable[str] = (),
) -> dict:
    """Execute `cmd` against an unmodified verified checkout and write a clean manual report bundle."""
    verified = verify_checkout(
        checkout,
        expected_repo=repo,
        expected_sha=expected_sha,
        allow_untracked=allow_untracked,
    )

    notes: dict = {}
    if notes_path:
        loaded = yaml.safe_load(notes_path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            notes = loaded

    redactions = build_redactions(
        checkout,
        input_dir=input_dir,
        output_dir=output_dir,
        extra_redact=extra_redact,
    )

    clean_cmd = sanitize_text(cmd, redactions)
    proc = subprocess.run(
        cmd,
        shell=True,
        cwd=str(checkout),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
        timeout=timeout_seconds,
    )
    rc = proc.returncode
    clean_output = sanitize_text(proc.stdout or "", redactions)
    terminal_text = f"$ {clean_cmd}\n\n{clean_output.rstrip()}\n\n[exit {rc}]\n"

    # Mechanical gate evaluation
    available = True
    installs = not install_failed
    runs = installs and (rc == 0)
    io_passed = False
    content_passed = False
    io_detail = None
    content_detail = None
    if runs:
        io_passed, content_passed, io_detail, content_detail = _validate_outputs(
            output_dir, output_glob, regions_file=regions_file
        )

    gates = {
        "available": available,
        "installs": installs,
        "runs": runs,
        "io": io_passed,
        "content": content_passed,
    }
    if content_passed:
        level = "content"
    elif io_passed:
        level = "io"
    elif runs:
        level = "runs"
    elif installs:
        level = "installs"
    else:
        level = "available"

    passed = io_passed
    verdict_code = "runs" if passed else "fails"
    default_reason = (
        f"Manual verification against unmodified upstream commit {verified['sha'][:7]} succeeded "
        f"({LEVEL_LABELS[level]})."
        if passed
        else (
            f"Manual verification against unmodified upstream commit {verified['sha'][:7]} failed "
            f"at {'Installs' if not installs else ('Runs (exit ' + str(rc) + ')' if not runs else 'Expected IO')}."
        )
    )
    reason = str(notes.get("failure_summary") or notes.get("summary") or default_reason).strip()

    tool_name = str(notes.get("tool_name") or verified["repo_display"].split("/")[-1])
    dataset_type = notes.get("dataset_type")
    dataset_label = notes.get("dataset_label") or dataset_type or "Local reference sample"
    datasets = (
        [
            {
                "leg": "external",
                "label": "External data",
                "available": True,
                "type": dataset_type,
                "dataset": dataset_label,
                "io": io_passed,
                "content": content_passed,
                "passed": passed,
            }
        ]
        if dataset_type
        else []
    )

    prep_block: dict = {
        "file": str(notes_path.name) if notes_path else "manual-local-record",
        "dataset": dataset_type,
        "installation": "strhub",
        "base": notes.get("base") or f"Local workstation ({platform.system()} {platform.machine()})",
        "without_preparation": notes.get("without_preparation"),
        "why": notes.get("why") or [],
        "steps": [sanitize_text(s, redactions) for s in (notes.get("steps") or [])],
        "run_cmd": sanitize_text(str(notes.get("run_cmd") or clean_cmd), redactions),
        "files": notes.get("files") or [],
    }
    for opt_key in ("pr_url", "fork_url", "guide_url", "proposed_fix_note", "fork_note"):
        if notes.get(opt_key):
            prep_block[opt_key] = notes[opt_key]

    generated = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    report: dict = {
        "schema": "strhub-verified/1",
        "instrument": "curated",
        "mode": "publish",
        "generated": generated,
        "tool": {
            "name": tool_name,
            "version": version or notes.get("version") or verified["sha"][:7],
            "contact": f"{verified['repo_display']}/issues",
        },
        "source": {
            "repo": verified["repo_display"],
            "ref": verified["sha"],
            "ref_resolved": verified["sha"],
            "committed": verified["committed"],
        },
        "environment": {
            "os": [notes.get("os") or f"{platform.system()} {platform.machine()} (manual workstation)"],
            "source": "prepared",
        },
        "preparation": prep_block,
        "recommendations": notes.get("recommendations") or [],
        "gates": gates,
        "level": level,
        "verdict": {
            "code": verdict_code,
            "title": "Runs in manual verification" if passed else "Fails in manual verification",
            "basis": "gates",
            "reason": reason,
            "readme_gaps": [],
        },
        "run": {
            "cmd": clean_cmd,
            "cwd": ".",
            "step_outcome": "success" if rc == 0 else "failure",
        },
        "datasets": datasets,
        "logs": {"external": f"{slug}.log-external.txt"},
        "terminals": {"external": f"{slug}.terminal-external.txt"},
        "certificate": {
            "schema": "strhub-verified/certificate/1",
            "label": "Manual verification: verified" if passed else "Manual verification: fails",
            "reached": LEVEL_LABELS[level],
            "summary": {
                "purpose": "Independent manual verification of reproducible execution on unmodified upstream source.",
                "result": reason,
                "reached": LEVEL_LABELS[level],
                "scope": "Reproducible execution only; does not evaluate genotype concordance or forensic casework fitness.",
                "not_evaluated": ["Genotype accuracy", "Concordance against truth", "Forensic casework fitness"],
            },
            "conclusion": [{"title": "Manual verification finding", "body": reason}],
            "out_of_scope": ["Genotype accuracy and concordance", "Forensic casework accreditation"],
            "limitations": [],
            "scope": {
                "statement": "This report records a manual execution against the pinned upstream commit.",
                "not": "It does not establish genotype accuracy or forensic casework fitness.",
                "disclaimer": (
                    "Each result is a fixed, dated attestation verified on the tool's public repository at an "
                    "immutable commit. It evaluates reproducible execution only, not genotype accuracy or forensic fitness."
                ),
            },
        },
        "scope": "Manual verification of reproducible execution against unmodified upstream commit.",
    }
    if io_detail is not None:
        report["io_detail"] = io_detail
    if content_detail is not None:
        report["content_detail"] = content_detail
    if notes.get("ci_run"):
        report["ci_run"] = notes["ci_run"]

    # Write bundle
    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    report_json = json.dumps(report, indent=2) + "\n"
    (out_dir / f"{slug}.json").write_text(report_json, encoding="utf-8")
    (out_dir / f"{slug}.terminal-external.txt").write_text(terminal_text, encoding="utf-8")
    (out_dir / f"{slug}.log-external.txt").write_text(clean_output, encoding="utf-8")
    (out_dir / f"{slug}.html").write_text(_render_static_html(report, terminal_text), encoding="utf-8")

    leaks = find_personal_leaks(report_json) + find_personal_leaks(terminal_text)
    if leaks:
        print(f"WARNING: possible personal path/host tokens found after redaction: {sorted(set(leaks))}", file=sys.stderr)

    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Record a local manual verification run with integrity and privacy checks.")
    ap.add_argument("--slug", required=True, help="Catalogue slug (e.g. strspy-ont)")
    ap.add_argument("--repo", required=True, help="Official GitHub repository URL")
    ap.add_argument("--checkout", required=True, help="Path to clean local git checkout of --repo")
    ap.add_argument("--cmd", required=True, help="Exact command to run against unmodified upstream code")
    ap.add_argument("--out-dir", required=True, help="Directory where the recorded bundle will be written")
    ap.add_argument("--version", default=None, help="Version or tag label (e.g. v2.0)")
    ap.add_argument("--sha", default=None, help="Optional expected commit SHA prefix to assert")
    ap.add_argument("--allow-untracked", action="append", default=[], help="Allow specific untracked config file(s)")
    ap.add_argument("--input-dir", default=None, help="Optional input data directory (redacted to /data/in)")
    ap.add_argument("--output-dir", default=None, help="Optional tool output directory (validated & redacted to /data/out)")
    ap.add_argument("--output-glob", default=None, help="Optional output file glob inside --output-dir")
    ap.add_argument("--regions-file", default=None, help="Optional BED regions file for VCF content validation")
    ap.add_argument("--notes", default=None, help="Optional editorial notes YAML file")
    ap.add_argument("--install-failed", action="store_true", help="Mark Installs gate as failed")
    ap.add_argument("--timeout", type=int, default=1800, help="Command timeout in seconds (default: 1800)")
    ap.add_argument("--redact", action="append", default=[], help="Additional literal string to redact")
    args = ap.parse_args(argv)

    report = record_manual_run(
        slug=args.slug,
        repo=args.repo,
        checkout=pathlib.Path(args.checkout),
        cmd=args.cmd,
        out_dir=pathlib.Path(args.out_dir),
        version=args.version,
        expected_sha=args.sha,
        allow_untracked=args.allow_untracked,
        input_dir=pathlib.Path(args.input_dir) if args.input_dir else None,
        output_dir=pathlib.Path(args.output_dir) if args.output_dir else None,
        output_glob=args.output_glob,
        regions_file=pathlib.Path(args.regions_file) if args.regions_file else None,
        notes_path=pathlib.Path(args.notes) if args.notes else None,
        install_failed=args.install_failed,
        timeout_seconds=args.timeout,
        extra_redact=args.redact,
    )
    print(
        f"Recorded manual verification for {args.slug} @ {report['source']['ref_resolved'][:7]}: "
        f"verdict={report['verdict']['code']} level={report['level']} -> {args.out_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
