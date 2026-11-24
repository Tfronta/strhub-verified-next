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
    for raw_p, target in ((checkout, "/work"), (input_dir, "/data/in"), (output_dir, "/data/out")):
        if raw_p is None:
            continue
        for candidate in (str(raw_p.resolve()), str(raw_p)):
            if candidate and (candidate, target) not in pairs:
                pairs.append((candidate, target))

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
        if not item:
            continue
        if "=" in item:
            src, dst = item.split("=", 1)
            src = src.strip()
            dst = dst.strip() or "<redacted>"
        else:
            src, dst = item, "<redacted>"
        if src:
            if src.startswith("/"):
                try:
                    resolved = str(pathlib.Path(src).resolve())
                    if resolved and resolved != src:
                        pairs.append((resolved, dst))
                except Exception:
                    pass
            pairs.append((src, dst))

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
    regions = content_auto.read_regions(regions_file) if regions_file else []
    panel_names = {r[3] for r in regions} if regions else set()
    stats = content_auto.analyze_table(target, fmt=fmt, panel_names=panel_names, regions=regions)
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
    checks = content_auto.judge(stats, fmt, len(regions))
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


def _wrap_pre(text: str, width: int = 100, max_lines: int | None = None, *, drop_wrap_space: bool = False) -> str:
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
                drop_whitespace=drop_wrap_space,
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
    """Generate a streamlined 4-section Manual Verification PDF matching STRhub's brand identity."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            KeepTogether,
            PageBreak,
            Paragraph,
            Preformatted,
            SimpleDocTemplate,
            Table,
            TableStyle,
        )
        import generate_pdf as gp
    except ImportError:
        return False

    passed = (report.get("verdict") or {}).get("code") == "runs"
    tool_name = str(report["tool"].get("name", ""))
    tool_ver = str(report["tool"].get("version") or "")
    tool_display = f"{tool_name} {tool_ver}".strip()
    ver_date = str(report.get("generated") or "")[:10]

    source = report.get("source") or {}
    repo = str(source.get("repo") or "").rstrip("/")
    sha = str(source.get("ref_resolved") or source.get("ref") or "")
    commit_url = f"{repo}/commit/{sha}" if repo.startswith("https://github.com/") and sha else repo

    gates = report.get("gates") or {}
    gates_passed = sum(1 for k in ("available", "installs", "runs", "io", "content") if gates.get(k))
    status_text = f"Manual · Verified ({gates_passed}/5)" if passed else f"Manual · Fails ({gates_passed}/5)"
    res_color = "#00909c" if passed else "#ef4444"
    level_label = LEVEL_LABELS.get(str(report.get("level") or ""), "Not run")

    cert_summary = (report.get("certificate") or {}).get("summary") or {}
    prep = report.get("preparation") or {}
    ds = (report.get("datasets") or [{}])[0]
    dataset_type = str(ds.get("type") or prep.get("dataset") or "")
    panel_label = gp.PANEL_MAP.get(dataset_type, "")

    def esc(val: object) -> str:
        return html_lib.escape(str(val or ""))

    s_term = ParagraphStyle(
        "manual_term",
        fontName="Courier",
        fontSize=6.8,
        leading=9.2,
        textColor=colors.HexColor("#e2e8f0"),
    )
    s_cmd = ParagraphStyle(
        "manual_cmd",
        fontName="Courier",
        fontSize=7.4,
        leading=10.5,
        textColor=gp.INK,
    )

    def dark_terminal_box(raw_text: str, *, max_lines: int = 68) -> Table:
        formatted = _wrap_pre(raw_text, width=96, max_lines=max_lines)
        box = Table([[Preformatted(formatted, s_term)]], colWidths=[gp.CW])
        box.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor("#0f172a")),
            ("BOX",           (0, 0), (-1, -1), 0.5, colors.HexColor("#334155")),
            ("TOPPADDING",    (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING",   (0, 0), (-1, -1), 10),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
        ]))
        return box

    def light_cmd_box(raw_text: str) -> Table:
        formatted = _wrap_pre(raw_text, width=90, drop_wrap_space=True)
        box = Table([[Preformatted(formatted, s_cmd)]], colWidths=[gp.CW])
        box.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), gp.GRAY_LIGHT),
            ("BOX",           (0, 0), (-1, -1), 0.5, gp.BORDER),
            ("TOPPADDING",    (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING",   (0, 0), (-1, -1), 12),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 12),
        ]))
        return box

    def build_manual_header_inner() -> Table:
        logo_h = 25
        logo_img = gp.logo_image(logo_h)
        logo_w = logo_img.drawWidth
        title = Paragraph(
            '<font name="Helvetica-Bold" size="11" color="#3d3d3d">STRhub</font>'
            '<font name="Helvetica" size="11" color="#00909c"> Verified</font>',
            gp.S("miht", leading=14),
        )
        sub = Paragraph(
            f"{esc(tool_display)}  ·  Manual Verification Report  ·  {esc(ver_date)}",
            gp.S("mihs", fontSize=7.5, textColor=gp.GRAY, leading=11),
        )
        text_w = gp.CW - logo_w
        right = Table([[title], [sub]], colWidths=[text_w - gp.LOGO_TEXT_GAP_INNER])
        right.setStyle(TableStyle([
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING",   (0, 0), (-1, -1), 0),
            ("TOPPADDING",    (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ]))
        outer = Table([[logo_img, right]], colWidths=[logo_w, text_w])
        outer.setStyle(TableStyle([
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING",   (0, 0), (0, -1),  0),
            ("LEFTPADDING",   (1, 0), (1, -1),  gp.LOGO_TEXT_GAP_INNER),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
            ("TOPPADDING",    (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        return outer

    story: list = []

    # ── Page 1: Cover (exact STRhub Verified visual identity) ────────────────
    story.append(gp.build_header_cover())
    story.append(gp.HR(gp.TEAL, thickness=1.5, spaceB=10, spaceA=14))

    story.append(Paragraph("Manual Verification Report", gp.ST["report_title"]))
    story.append(gp.vspace(2))
    story.append(Paragraph(esc(tool_name), gp.ST["tool_name"]))
    if tool_ver:
        story.append(Paragraph(f"Version {esc(tool_ver)}", gp.ST["tool_sub"]))
    if panel_label:
        story.append(Paragraph(esc(panel_label), gp.ST["tool_sub"]))
    story.append(gp.vspace(5))
    story.append(gp.HR(spaceB=4, spaceA=10))

    meta_rows: list[tuple[str, str]] = [
        ("Verification date", esc(ver_date)),
        ("Repository", gp.link(repo, esc(repo)) if repo else "-"),
        ("Repository commit", gp.link(commit_url, esc(sha)) if sha else "-"),
        ("Mode", "Manual verification (unmodified upstream code in prepared environment)"),
        ("Result", f'<font color="{res_color}"><b>{esc(status_text)}</b></font>'),
        ("Reached", f"{esc(level_label)}, {gates_passed}/5 gates passed"),
    ]
    if prep.get("base"):
        meta_rows.append(("Environment", _inline_code(prep["base"])))
    if ds.get("dataset"):
        meta_rows.append(("Dataset", esc(ds["dataset"])))
    if cert_summary.get("why"):
        meta_rows.append(("Why", _inline_code(cert_summary["why"])))
    meta_rows.append(("STRhub", gp.link("https://strhub.app")))

    story.append(gp.kv_table(meta_rows))
    story.append(gp.HR(spaceB=5, spaceA=5))

    story.append(gp.section_title("SCOPE OF THIS REPORT"))
    story.append(gp.vspace(0.5))
    scope_text = (
        "Independent manual verification of reproducible execution on the tool's unmodified public "
        "repository at the pinned commit. It confirms whether the software installs, runs end-to-end, "
        "and produces structurally valid output after preparing the required environment.<br/><br/>"
        "This is <b>not</b> an analytical validation. Genotype accuracy, concordance, forensic "
        "suitability, and regulatory compliance are out of scope."
    )
    story.append(gp.boxed([Paragraph(scope_text, gp.ST["body"])], pad=8))
    story.append(gp.vspace(2))

    def col_block(items: list[str], title_col, label: str) -> list:
        dash_hex = f"#{gp.GRAY.hexval()[2:]}"
        out = [Paragraph(label, gp.S(
            "mbl", fontName="Helvetica-Bold", fontSize=8,
            textColor=title_col, leading=11, spaceAfter=3.5,
        ))]
        for item in items:
            out.append(Paragraph(
                f'<font color="{dash_hex}">–</font>  {item}',
                gp.S("mbi", fontSize=8.3, textColor=gp.INK, leading=12, leftIndent=8, spaceAfter=1.2),
            ))
        return out

    stages = gp.stage_states(gates, execution_established=True)
    status_colors = {"PASS": "#00909c", "FAIL": "#dc2626", "NOT ATTEMPTED": "#6b7280"}
    status_items = [
        f'{st["label"]}: <font color="{status_colors.get(st["status"], "#6b7280")}"><b>{st["status"]}</b></font>'
        for st in stages
    ]
    v_col = col_block(status_items, gp.TEAL, "VERIFICATION STATUS")
    nv_col = col_block(list(gp.NOT_EVALUATED), gp.GRAY, "NOT EVALUATED")

    half = gp.CW / 2
    verify_tbl = Table([[v_col, nv_col]], colWidths=[half, half])
    verify_tbl.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND",    (0, 0), (0, 0),   gp.TEAL_LIGHT),
        ("BACKGROUND",    (1, 0), (1, 0),   gp.GRAY_LIGHT),
        ("BOX",           (0, 0), (0, 0),   0.5, gp.TEAL_MID),
        ("BOX",           (1, 0), (1, 0),   0.5, gp.BORDER),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING",   (0, 0), (-1, -1), 14),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 14),
    ]))
    story.append(verify_tbl)
    story.append(PageBreak())

    # ── Page 2+: Compact Inner Header + 4 Streamlined Sections ───────────────
    story.append(build_manual_header_inner())
    story.append(gp.HR(gp.TEAL, thickness=1.2, spaceB=4, spaceA=8))

    # Section 1: Execution on unmodified upstream code + Gates + Terminal
    story.append(gp.section_num("1", "Execution on Unmodified Upstream Code"))
    sec1_box_els: list = []
    if prep.get("without_preparation"):
        sec1_box_els.append(Paragraph(
            f"<b>Why manual verification was used:</b> {_inline_code(prep['without_preparation'])}",
            gp.ST["body"],
        ))
        sec1_box_els.append(gp.vspace(2))
    reason_text = (report.get("verdict") or {}).get("reason", "")
    if reason_text:
        sec1_box_els.append(Paragraph(_inline_code(reason_text), gp.ST["body"]))
    if sec1_box_els:
        story.append(gp.boxed(sec1_box_els, pad=10))
        story.append(gp.vspace(3))

    # Gates ladder table matching generate_pdf.py
    gdata = []
    stopped_found = False
    for key, gate_name, gate_desc in gp.GATE_DISPLAY:
        ok = bool(gates.get(key, False))
        if ok:
            st = "pass"
            desc_text = gate_desc
        elif not stopped_found:
            st = "stopped"
            stopped_found = True
            desc_text = f'{gate_desc} &nbsp; <font color="#ef4444"><b>The run stopped here.</b></font>'
        else:
            st = "na"
            desc_text = f'{gate_desc} &nbsp; <font color="#9ca3af"><i>Not attempted, because the run had already stopped.</i></font>'
        gdata.append([
            Paragraph(gate_name, gp.ST["gate_name"]),
            Paragraph(desc_text, gp.ST["gate_desc"]),
            gp.pass_badge(st),
        ])
    gt = Table(gdata, colWidths=[46 * mm, gp.CW - 46 * mm - 18 * mm, 18 * mm])
    gt.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [gp.WHITE, gp.GRAY_LIGHT]),
        ("LINEBELOW",     (0, 0), (-1, -2), 0.3, gp.BORDER),
        ("BOX",           (0, 0), (-1, -1), 0.5, gp.BORDER),
    ]))
    story.append(gt)
    story.append(gp.vspace(4))

    story.append(KeepTogether([
        Paragraph("<b>Recorded terminal output</b>", gp.ST["tbl_cell"]),
        gp.vspace(2),
        dark_terminal_box(terminal_text, max_lines=68),
    ]))

    sec = 2

    # Section: Output Content (Plausibility Evidence) when output was validated
    io_out = ((report.get("io_detail") or {}).get("outputs") or [None])[0]
    content_out = ((report.get("content_detail") or {}).get("outputs") or [None])[0]
    c_stats = (content_out or {}).get("stats") or {}
    if io_out or c_stats:
        out_rows: list[tuple[str, str]] = []
        if io_out:
            fname = io_out.get("resolved") or io_out.get("path") or "-"
            fmt = str(io_out.get("format") or "").upper()
            out_rows.append(("Output file", f'<font name="Courier" size="8">{esc(fname)}</font>' + (f" ({esc(fmt)})" if fmt else "")))
            if io_out.get("validation_status"):
                st_str = str(io_out["validation_status"]).upper()
                st_col = "#00909c" if io_out["validation_status"] == "valid" else "#ef4444"
                out_rows.append(("Structural validation", f'<font color="{st_col}"><b>{esc(st_str)}</b></font>'))
            if isinstance(io_out.get("records"), int):
                called = io_out.get("called_records")
                rec_desc = f"{io_out['records']} data rows"
                if isinstance(called, int):
                    rec_desc += f" ({called} with called genotypes)"
                rec_label = "VCF records" if fmt == "VCF" else "Data records"
                out_rows.append((rec_label, esc(rec_desc)))
        if c_stats:
            n_loci = c_stats.get("distinct_str_loci", c_stats.get("distinct_loci"))
            if isinstance(n_loci, int):
                out_rows.append(("STR loci detected", f"<b>{n_loci}</b> distinct recognizable forensic STR loci"))
            n_snps = c_stats.get("distinct_snp_markers")
            if isinstance(n_snps, int) and n_snps > 0:
                out_rows.append(("Identity SNPs", f"<b>{n_snps}</b> recognizable SNP markers (rsNNNN)"))
            loci_list = c_stats.get("str_loci") or c_stats.get("loci") or []
            if loci_list:
                out_rows.append(("Loci called", f'<font name="Courier" size="7.5">{esc(", ".join(str(x) for x in loci_list))}</font>'))
        if out_rows:
            ot = Table(
                [[Paragraph(k, gp.ST["meta_label"]), Paragraph(v, gp.ST["tbl_cell"])] for k, v in out_rows],
                colWidths=[42 * mm, gp.CW - 42 * mm],
            )
            ot.setStyle(TableStyle([
                ("VALIGN",        (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING",   (0, 0), (-1, -1), 10),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
                ("TOPPADDING",    (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [gp.WHITE, gp.GRAY_LIGHT]),
                ("LINEBELOW",     (0, 0), (-1, -2), 0.3, gp.BORDER),
                ("BOX",           (0, 0), (-1, -1), 0.5, gp.BORDER),
            ]))
            story.append(KeepTogether([
                gp.section_num(str(sec), "Output Content (Plausibility Evidence)"),
                ot,
            ]))
            sec += 1

    # Section: Verification Data when a reference dataset is recorded
    if ds.get("dataset") or dataset_type:
        ds_rows: list[tuple[str, str]] = []
        if ds.get("dataset"):
            ds_rows.append(("Dataset", esc(ds["dataset"])))
        if dataset_type:
            ds_rows.append(("Dataset ID", f'<font name="Courier" size="8">{esc(dataset_type)}</font>'))
        if panel_label:
            ds_rows.append(("Panel", esc(panel_label)))
        ds_rows.append(("Scope note", "Open-access regional reference slice staged by STRhub for execution verification only."))
        dt_tbl = Table(
            [[Paragraph(k, gp.ST["meta_label"]), Paragraph(v, gp.ST["tbl_cell"])] for k, v in ds_rows],
            colWidths=[42 * mm, gp.CW - 42 * mm],
        )
        dt_tbl.setStyle(TableStyle([
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING",   (0, 0), (-1, -1), 10),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [gp.WHITE, gp.GRAY_LIGHT]),
            ("LINEBELOW",     (0, 0), (-1, -2), 0.3, gp.BORDER),
            ("BOX",           (0, 0), (-1, -1), 0.5, gp.BORDER),
        ]))
        story.append(KeepTogether([
            gp.section_num(str(sec), "Verification Data"),
            dt_tbl,
        ]))
        sec += 1

    # Section: Step-by-step setup (and proposed fix when applicable)
    has_steps = bool(prep.get("steps") or prep.get("run_cmd") or prep.get("pr_url") or prep.get("fork_url"))
    if has_steps:
        sec2_title = (
            "Step-by-Step Setup and Proposed Fix"
            if (not passed or prep.get("pr_url") or prep.get("fork_url"))
            else "Step-by-Step Setup"
        )
        sec2_lead: list = [gp.section_num(str(sec), sec2_title)]
        sec += 1
        if not passed:
            sec2_lead.append(Paragraph(
                "<b>Proposed fix / temporary workaround (requires code changes):</b> "
                "Shared as a suggestion for the author and temporary reference for users. "
                "It does not mark the official upstream commit as passing.",
                gp.ST["body"],
            ))
            sec2_lead.append(gp.vspace(2))
        if prep.get("steps"):
            sec2_lead.append(Paragraph("<b>Preparation commands</b>", gp.ST["tbl_cell"]))
            sec2_lead.append(gp.vspace(1.5))
            sec2_lead.append(light_cmd_box("\n".join(prep["steps"])))
            sec2_lead.append(gp.vspace(3))
            story.append(KeepTogether(sec2_lead))
        elif prep.get("run_cmd"):
            sec2_lead.append(Paragraph("<b>Verified run command</b>", gp.ST["tbl_cell"]))
            sec2_lead.append(gp.vspace(1.5))
            sec2_lead.append(light_cmd_box(str(prep["run_cmd"])))
            sec2_lead.append(gp.vspace(3))
            story.append(KeepTogether(sec2_lead))
        else:
            story.append(KeepTogether(sec2_lead))

        if prep.get("steps") and prep.get("run_cmd"):
            story.append(KeepTogether([
                Paragraph("<b>Verified run command</b>", gp.ST["tbl_cell"]),
                gp.vspace(1.5),
                light_cmd_box(str(prep["run_cmd"])),
                gp.vspace(3),
            ]))

        links_els: list = []
        if prep.get("pr_url"):
            links_els.append(Paragraph(
                f"<b>Proposed fix (PR):</b> {gp.link(prep['pr_url'], esc(prep['pr_url']))}",
                gp.ST["tbl_cell"],
            ))
        if prep.get("fork_url"):
            links_els.append(Paragraph(
                f"<b>Suggested fix (fork):</b> {gp.link(prep['fork_url'], esc(prep['fork_url']))}",
                gp.ST["tbl_cell"],
            ))
        fix_note = prep.get("proposed_fix_note") or prep.get("fork_note")
        if fix_note:
            if links_els:
                links_els.append(gp.vspace(2))
            links_els.append(Paragraph(_inline_code(fix_note), gp.ST["body"]))
        if links_els:
            story.append(KeepTogether([gp.boxed(links_els, pad=10)]))

    # Section: Suggestions for the author
    recs = report.get("recommendations") or []
    if recs:
        rec_els = [
            Paragraph(
                f'<font color="#9ca3af">–</font>  {_inline_code(item)}',
                gp.S("mrec", fontSize=8.5, textColor=gp.INK, leading=13.5, leftIndent=10, spaceAfter=3),
            )
            for item in recs
        ]
        story.append(KeepTogether([
            gp.section_num(str(sec), "Suggestions for the Author"),
            gp.boxed(rec_els, pad=10),
        ]))
        sec += 1

    # Section: Scope and Limitations (matches generate_pdf.py)
    cert_block = report.get("certificate") or {}
    lim_items = cert_block.get("limitations") or []
    disclaimer = (cert_block.get("scope") or {}).get("disclaimer", "")
    lim_els: list = [
        Paragraph(
            "Concerns reproducible execution only; no claim of genotype accuracy, "
            "concordance, forensic casework suitability, or regulatory validation.",
            gp.ST["body"],
        ),
        gp.vspace(2),
    ]
    for item in lim_items:
        lim_els.append(Paragraph(
            f'<font color="#9ca3af">–</font>  {esc(item)}',
            gp.S("mlim", fontSize=8.5, textColor=gp.GRAY, leading=13.5, leftIndent=10, spaceAfter=1.5),
        ))
    if disclaimer:
        lim_els.extend([gp.vspace(2), Paragraph(esc(disclaimer), gp.ST["body"])])
    story.append(KeepTogether([
        gp.section_num(str(sec), "Scope and Limitations"),
        gp.boxed(lim_els, pad=10),
    ]))
    sec += 1

    # Section: Conclusion (exact teal conclusion card from generate_pdf.py)
    raw_con = cert_block.get("conclusion") or []
    con_items: list[tuple[str, str]] = [
        (esc(c.get("title", "")), _inline_code(c.get("body", "")))
        for c in raw_con
        if isinstance(c, dict) and c.get("title") and c.get("body")
    ]
    if not con_items:
        short_sha = sha[:7]
        conclusion_lead = cert_summary.get("why") or reason_text
        con_items = [(f"Outcome: {esc(status_text)} (commit {esc(short_sha)})", _inline_code(conclusion_lead))]

    con_content = []
    for c_title, c_body in con_items:
        con_content.append(Paragraph(
            f'<font color="#00909c">◆</font>  <b>{c_title}</b>',
            gp.S("mct", fontSize=9, textColor=gp.INK, leading=14, fontName="Helvetica-Bold", spaceAfter=2),
        ))
        con_content.append(Paragraph(
            c_body,
            gp.S("mcb", fontSize=8.5, textColor=gp.GRAY, leading=13, leftIndent=14, spaceAfter=6),
        ))
    con_box = Table([[con_content]], colWidths=[gp.CW])
    con_box.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), gp.TEAL_LIGHT),
        ("BOX",           (0, 0), (-1, -1), 0.8, gp.TEAL_MID),
        ("TOPPADDING",    (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("LEFTPADDING",   (0, 0), (-1, -1), 14),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 14),
    ]))
    story.append(KeepTogether([gp.section_num(str(sec), "Conclusion"), con_box]))

    canvas_cfg = {"tool_display": tool_display, "ver_date": ver_date}
    doc = SimpleDocTemplate(
        str(out_pdf),
        pagesize=gp.A4,
        leftMargin=gp.ML,
        rightMargin=gp.MR,
        topMargin=gp.MT,
        bottomMargin=gp.MB,
        title=f"{tool_display} · STRhub Manual Verification",
    )
    doc.build(story, canvasmaker=gp._make_canvas_class(canvas_cfg))
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

    display_ver = version or notes.get("version") or verified["sha"][:7]
    tool_display = f"{tool_name} {display_ver}".strip()
    manual_limitations = [
        "Results apply exclusively to the exact Git commit SHA and manually prepared environment recorded in this report.",
        "Single regional reference slice per input type; low-coverage warnings on sliced BAMs do not imply defects on whole-genome data.",
        "Plausible Output checks verify structural format and recognizable STR loci, not biological genotype truth.",
        "Verification is a point-in-time snapshot; upstream repository changes after this commit are not covered until re-verification.",
        "No truth-set concordance, forensic casework validation, or regulatory compliance assessment was performed.",
    ]

    manual_conclusion: list[dict[str, str]] = []
    if runs:
        manual_conclusion.append({
            "title": f"{tool_display} executes end-to-end",
            "body": (
                f"{tool_display} ran to completion without code modifications in the prepared environment "
                f"at unmodified upstream commit {verified['sha'][:7]}."
            ),
        })
    elif installs:
        manual_conclusion.append({
            "title": f"{tool_display} did not complete its run",
            "body": (
                f"Even after preparing the environment manually, unmodified upstream commit {verified['sha'][:7]} "
                f"stopped during execution (exit {rc}). See Section 1 for the recorded terminal output."
            ),
        })
    else:
        manual_conclusion.append({
            "title": f"{tool_display} did not install in the prepared environment",
            "body": f"Installation of unmodified upstream commit {verified['sha'][:7]} failed before execution could start.",
        })

    if content_passed:
        c_stats_rec = ((content_detail or {}).get("outputs") or [{}])[0].get("stats") or {}
        n_loci = c_stats_rec.get("distinct_str_loci", c_stats_rec.get("distinct_loci", 0))
        out_fmt = str(((io_detail or {}).get("outputs") or [{}])[0].get("format") or "").upper()
        fmt_str = f"{out_fmt} " if out_fmt else ""
        manual_conclusion.append({
            "title": "Output passes plausibility checks",
            "body": (
                f"The run produced a structurally valid, non-empty {fmt_str}output containing {n_loci} "
                "distinct recognizable STR loci; structural plausibility checks verify output format and "
                "locus presence, not genotype accuracy."
            ),
        })
    elif io_passed:
        manual_conclusion.append({
            "title": "Output file produced; plausibility check not passed",
            "body": "A non-empty output file was written, but it did not pass the STR plausibility check.",
        })
    elif gates["runs"]:
        manual_conclusion.append({
            "title": "Output failed structural validation",
            "body": (
                "Execution completed, but the expected output file was either missing "
                "or failed structural validation for its declared format."
            ),
        })
    else:
        manual_conclusion.append({
            "title": "No expected output produced",
            "body": "No validated output file was produced because execution did not complete.",
        })

    if dataset_type:
        manual_conclusion.append({
            "title": "Verification used STRhub reference data",
            "body": f"Verification used open-access STRhub reference dataset {dataset_label} ({dataset_type}).",
        })

    fix_note_rec = prep_block.get("proposed_fix_note") or prep_block.get("fork_note")
    if fix_note_rec:
        manual_conclusion.append({
            "title": "Proposed fix / temporary workaround",
            "body": str(fix_note_rec),
        })

    manual_conclusion.append({
        "title": "Repeatability of this manual run",
        "body": (
            "The pinned upstream commit, prepared environment description, exact commands executed, "
            "and sanitized terminal output recorded in this report document the procedure for independent reproduction."
        ),
    })

    generated = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    report: dict = {
        "schema": "strhub-verified/1",
        "instrument": "curated",
        "mode": "publish",
        "generated": generated,
        "tool": {
            "name": tool_name,
            "version": display_ver,
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
            "conclusion": manual_conclusion,
            "out_of_scope": ["Genotype accuracy and concordance", "Forensic casework accreditation"],
            "limitations": manual_limitations,
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
    if isinstance(notes.get("i18n"), dict):
        i18n_out: dict[str, dict] = {}
        for lang, raw_loc in notes["i18n"].items():
            if lang not in ("es", "en", "pt") or not isinstance(raw_loc, dict):
                continue
            loc_clean: dict = {}
            plain_val = raw_loc.get("plain_why") or raw_loc.get("plain_summary")
            if plain_val:
                loc_clean["plain_why"] = str(plain_val).strip()
            if raw_loc.get("without_preparation"):
                loc_clean["without_preparation"] = str(raw_loc["without_preparation"]).strip()
            reason_val = raw_loc.get("reason") or raw_loc.get("failure_summary") or raw_loc.get("summary")
            if reason_val:
                loc_clean["reason"] = str(reason_val).strip()
            if raw_loc.get("base"):
                loc_clean["base"] = str(raw_loc["base"]).strip()
            fix_val = raw_loc.get("proposed_fix_note") or raw_loc.get("fork_note")
            if fix_val:
                loc_clean["proposed_fix_note"] = str(fix_val).strip()
            if isinstance(raw_loc.get("recommendations"), list) and raw_loc["recommendations"]:
                loc_clean["recommendations"] = [str(x).strip() for x in raw_loc["recommendations"] if str(x).strip()]
            if isinstance(raw_loc.get("files"), list) and raw_loc["files"]:
                loc_clean["files"] = raw_loc["files"]
            if loc_clean:
                i18n_out[lang] = loc_clean
        if i18n_out:
            report["i18n"] = i18n_out

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
