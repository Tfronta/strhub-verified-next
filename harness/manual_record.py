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
import textwrap
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

    committed_raw = _git(checkout, "show", "-s", "--format=%cI", "HEAD")
    try:
        committed = (
            dt.datetime.fromisoformat(committed_raw)
            .astimezone(dt.timezone.utc)
            .strftime("%Y-%m-%dT%H:%M:%SZ")
        )
    except ValueError:
        committed = committed_raw

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


_INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")


def _inline_code(val: object) -> str:
    """Escape HTML and render Markdown inline backticks as ReportLab Courier."""
    escaped = html_lib.escape(str(val or ""))
    return _INLINE_CODE_RE.sub(r'<font name="Courier" size="8.5">\1</font>', escaped)


def _wrap_pre(text: str, width: int = 100, max_lines: int | None = None) -> str:
    """Normalize tabs, collapse excess blank lines, and wrap lines for ReportLab Preformatted."""
    raw = str(text or "").replace("\r\n", "\n").replace("\r", "\n").expandtabs(4)
    wrapped: list[str] = []
    blank_run = 0
    for line in raw.split("\n"):
        cleaned = line.rstrip()
        if not cleaned:
            blank_run += 1
            if blank_run <= 1 and wrapped:
                wrapped.append("")
            continue
        blank_run = 0
        if len(cleaned) <= width:
            wrapped.append(cleaned)
        else:
            chunks = textwrap.wrap(
                cleaned,
                width=width,
                expand_tabs=False,
                replace_whitespace=False,
                drop_whitespace=False,
                break_long_words=True,
                break_on_hyphens=False,
            )
            wrapped.extend(c.rstrip() for c in chunks)
    while wrapped and not wrapped[-1]:
        wrapped.pop()
    if max_lines is not None and len(wrapped) > max_lines:
        head = max_lines // 2
        tail = max_lines - head
        omitted = len(wrapped) - head - tail
        wrapped = (
            wrapped[:head]
            + [f"... ({omitted} lines omitted; see full terminal log file) ..."]
            + wrapped[-tail:]
        )
    return "\n".join(wrapped)


def _render_manual_pdf(report: dict, terminal_text: str, out_pdf: pathlib.Path) -> bool:
    """Generate a streamlined 4-section Manual Verification PDF matching the web layout."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            HRFlowable,
            KeepTogether,
            Paragraph,
            Preformatted,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError:
        return False

    passed = (report.get("verdict") or {}).get("code") == "runs"
    accent = colors.HexColor("#4338ca") if passed else colors.HexColor("#b45309")
    accent_bg = colors.HexColor("#eef2ff") if passed else colors.HexColor("#fffbeb")
    accent_border = colors.HexColor("#c7d2fe") if passed else colors.HexColor("#fde68a")
    ink = colors.HexColor("#1f2937")
    muted = colors.HexColor("#4b5563")
    border = colors.HexColor("#d1d5db")
    teal = colors.HexColor("#0f766e")

    doc = SimpleDocTemplate(
        str(out_pdf),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=f"{report['tool'].get('name', '')} Manual Verification",
    )

    s_banner_l = ParagraphStyle("banner_l", fontName="Helvetica-Bold", fontSize=10, leading=13, textColor=accent)
    s_banner_r = ParagraphStyle("banner_r", fontName="Helvetica", fontSize=8.5, leading=13, textColor=muted, alignment=2)
    s_title = ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=ink, spaceBefore=6, spaceAfter=4)
    s_badge = ParagraphStyle("badge", fontName="Helvetica-Bold", fontSize=10, textColor=accent, spaceAfter=8)
    s_h2 = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=11.5, textColor=teal, spaceBefore=12, spaceAfter=5)
    s_body = ParagraphStyle("body", fontName="Helvetica", fontSize=9.5, leading=13.5, textColor=ink, spaceAfter=5)
    s_muted = ParagraphStyle("muted", fontName="Helvetica", fontSize=8.5, leading=12, textColor=muted, spaceAfter=4)
    s_label = ParagraphStyle("label", fontName="Helvetica-Bold", fontSize=8.5, textColor=muted)
    s_val = ParagraphStyle("val", fontName="Helvetica", fontSize=8.5, leading=12, textColor=ink)
    s_code = ParagraphStyle("code", fontName="Courier", fontSize=7.2, leading=9.8, textColor=colors.HexColor("#111827"))

    def esc(val: object) -> str:
        return html_lib.escape(str(val or ""))

    def code_box(raw_text: str, *, max_lines: int | None = None) -> Table:
        formatted = _wrap_pre(raw_text, width=100, max_lines=max_lines)
        box = Table([[Preformatted(formatted, s_code)]], colWidths=[174 * mm])
        box.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f9fafb")),
            ("BOX", (0, 0), (-1, -1), 0.5, border),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        return box

    gates = report.get("gates") or {}
    gates_passed = sum(1 for k in ("available", "installs", "runs", "io", "content") if gates.get(k))
    status_text = f"Manual · Verified ({gates_passed}/5)" if passed else f"Manual · Fails ({gates_passed}/5)"

    story: list = []
    banner = Table(
        [[Paragraph("MANUAL VERIFICATION REPORT", s_banner_l), Paragraph("STRhub Verified", s_banner_r)]],
        colWidths=[124 * mm, 50 * mm],
    )
    banner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), accent_bg),
        ("BOX", (0, 0), (-1, -1), 0.6, accent_border),
        ("LINEABOVE", (0, 0), (-1, 0), 2.2, accent),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(banner)
    tool_name = report["tool"].get("name", "")
    tool_ver = report["tool"].get("version") or ""
    story.append(Paragraph(f"{esc(tool_name)} {esc(tool_ver)}".strip(), s_title))
    story.append(Paragraph(esc(status_text), s_badge))

    cert_summary = (report.get("certificate") or {}).get("summary") or {}
    prep = report.get("preparation") or {}
    ds = (report.get("datasets") or [{}])[0]

    cover_rows = [
        [Paragraph("VERIFICATION DATE", s_label), Paragraph(esc((report.get("generated") or "")[:10]), s_val)],
        [Paragraph("REPOSITORY", s_label), Paragraph(esc((report.get("source") or {}).get("repo", "")), s_val)],
        [Paragraph("PINNED COMMIT", s_label), Paragraph(f'<font name="Courier" size="8">{esc((report.get("source") or {}).get("ref_resolved", ""))}</font>', s_val)],
        [Paragraph("MODE", s_label), Paragraph("Manual verification (unmodified upstream code in prepared environment)", s_val)],
        [Paragraph("ENVIRONMENT", s_label), Paragraph(_inline_code(prep.get("base", "")), s_val)],
    ]
    if ds.get("dataset"):
        cover_rows.append([Paragraph("DATASET", s_label), Paragraph(esc(ds["dataset"]), s_val)])
    if cert_summary.get("why"):
        cover_rows.append([Paragraph("WHY", s_label), Paragraph(_inline_code(cert_summary["why"]), s_val)])

    t_cover = Table(cover_rows, colWidths=[38 * mm, 136 * mm])
    t_cover.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, border),
        ("BACKGROUND", (0, 0), (-1, 0), accent_bg),
    ]))
    story.append(t_cover)
    story.append(Spacer(1, 4 * mm))

    # Section 1: Execution on unmodified upstream code + Gates + Terminal
    sec1_head: list = [
        Paragraph("1. Execution on unmodified upstream code", s_h2),
        HRFlowable(width="100%", thickness=0.6, color=teal, spaceAfter=4),
    ]
    if prep.get("without_preparation"):
        sec1_head.append(Paragraph(f"<b>Why manual verification was used:</b> {_inline_code(prep['without_preparation'])}", s_body))
    sec1_head.append(Paragraph(_inline_code((report.get("verdict") or {}).get("reason", "")), s_body))
    story.append(KeepTogether(sec1_head))

    gate_names = [
        ("Available", gates.get("available")),
        ("Installs", gates.get("installs")),
        ("Runs", gates.get("runs")),
        ("Expected IO", gates.get("io")),
        ("Plausible output", gates.get("content")),
    ]
    stopped_seen = False
    gate_rows = [[Paragraph("GATE", s_label), Paragraph("RESULT", s_label)]]
    for gname, gval in gate_names:
        if gval:
            st = "PASS"
        elif not stopped_seen:
            st = "FAIL (stopped here)"
            stopped_seen = True
        else:
            st = "NOT REACHED"
        gate_rows.append([Paragraph(esc(gname), s_val), Paragraph(esc(st), s_val)])
    t_gates = Table(gate_rows, colWidths=[60 * mm, 114 * mm])
    t_gates.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, border),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
    ]))
    story.append(t_gates)
    story.append(Spacer(1, 3 * mm))

    # Sanitized terminal excerpt (tabs expanded, lines wrapped, head+tail preserved)
    story.append(code_box(terminal_text, max_lines=68))

    # Section 2: Step-by-step setup / Proposed fix
    has_steps = bool(prep.get("steps") or prep.get("run_cmd") or prep.get("pr_url") or prep.get("fork_url"))
    if has_steps:
        sec2_lead: list = [
            Paragraph("2. Step-by-step setup and proposed fix", s_h2),
            HRFlowable(width="100%", thickness=0.6, color=teal, spaceAfter=4),
        ]
        if not passed:
            sec2_lead.append(Paragraph(
                "<b>Proposed fix / temporary workaround (requires code changes):</b> "
                "Shared as a suggestion for the author and temporary reference for users; "
                "does not mark the official commit as passing.",
                s_muted,
            ))
        if prep.get("steps"):
            sec2_lead.extend([
                Paragraph("<b>Preparation commands:</b>", s_body),
                code_box("\n".join(prep["steps"])),
                Spacer(1, 2.5 * mm),
            ])
            story.append(KeepTogether(sec2_lead))
        elif prep.get("run_cmd"):
            sec2_lead.extend([
                Paragraph("<b>Verified run command:</b>", s_body),
                code_box(str(prep["run_cmd"])),
                Spacer(1, 2.5 * mm),
            ])
            story.append(KeepTogether(sec2_lead))
        else:
            story.append(KeepTogether(sec2_lead))

        if prep.get("steps") and prep.get("run_cmd"):
            story.append(KeepTogether([
                Paragraph("<b>Verified run command:</b>", s_body),
                code_box(str(prep["run_cmd"])),
                Spacer(1, 2.5 * mm),
            ]))
        links_block: list = []
        if prep.get("pr_url"):
            links_block.append(Paragraph(f"<b>Proposed PR:</b> {esc(prep['pr_url'])}", s_body))
        if prep.get("fork_url"):
            links_block.append(Paragraph(f"<b>Suggested fix (fork):</b> {esc(prep['fork_url'])}", s_body))
        fix_note = prep.get("proposed_fix_note") or prep.get("fork_note")
        if fix_note:
            links_block.append(Paragraph(_inline_code(fix_note), s_body))
        if links_block:
            story.append(KeepTogether(links_block))

    # Section 3: Suggestions for the author
    recs = report.get("recommendations") or []
    if recs:
        sec3_first = [
            Paragraph("3. Suggestions for the author", s_h2),
            HRFlowable(width="100%", thickness=0.6, color=teal, spaceAfter=4),
            Paragraph(f"&bull; {_inline_code(recs[0])}", s_body),
        ]
        story.append(KeepTogether(sec3_first))
        for item in recs[1:]:
            story.append(Paragraph(f"&bull; {_inline_code(item)}", s_body))

    # Section 4: Conclusion and scope (concise executive takeaway, no verbatim repeat of Section 1)
    short_sha = ((report.get("source") or {}).get("ref_resolved") or "")[:7]
    conclusion_lead = cert_summary.get("why") or (report.get("verdict") or {}).get("reason", "")
    sec4: list = [
        Paragraph("4. Conclusion and scope", s_h2),
        HRFlowable(width="100%", thickness=0.6, color=teal, spaceAfter=4),
        Paragraph(f"<b>Outcome:</b> {esc(status_text)} on unmodified upstream commit <font name=\"Courier\" size=\"8.5\">{esc(short_sha)}</font>.", s_body),
        Paragraph(_inline_code(conclusion_lead), s_body),
    ]
    disclaimer = ((report.get("certificate") or {}).get("scope") or {}).get("disclaimer", "")
    if disclaimer:
        sec4.append(Paragraph(esc(disclaimer), s_muted))
    story.append(KeepTogether(sec4))

    doc.build(story)
    return out_pdf.is_file()


def _render_static_html(report: dict, terminal_text: str) -> str:
    tool = report["tool"]
    verdict = report["verdict"]
    title = html_lib.escape(f"{tool.get('name', 'Tool')} {tool.get('version') or ''} · STRhub Manual Verification".strip())
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
    default_plain_why = (
        "Automated verification could not run because the repository's installation or environment steps "
        "could not be executed automatically. In manual verification, after preparing the environment, "
        "the original software ran end-to-end without code changes (see Section 2 for reproducible steps)."
        if passed
        else (
            "Automated verification could not run because the repository's installation instructions could not "
            "be executed automatically. In manual verification, the original software failed to execute due to "
            "an error in its own code or environment definition (see Section 1 for details)."
        )
    )
    plain_why = str(notes.get("plain_summary") or default_plain_why).strip()

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
                "why": plain_why,
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
    _render_manual_pdf(report, terminal_text, out_dir / f"{slug}.pdf")

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
