"""Assemble the report, a shields.io endpoint badge and the two prose copies.

The gate outcomes come from the engine's RunRecord (--engine-record); the
check results from the files the engine wrote beside it. Output:
  reports/<slug>.json        - the report (docs/WEB-CONTRACT.md §3)
  reports/<slug>.badge.json  - shields.io endpoint badge
  reports/<slug>.summary.md  - the report in prose
  reports/<slug>.html        - static page of the report
  reports/<slug>.log-<leg>.txt, reports/<slug>.terminal-<leg>.txt

Usage:
  python harness/report.py --manifest work/proposal/manifest.yml \
      --engine-record run_record.json --procedure-review work/procedure_review.json \
      --recipe-proposal recipe_proposal.json --ref <sha> --mode trial --run-url <ci_run_url>
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _manifest  # noqa: E402
import diagnose_log  # noqa: E402
from command_record import presentation as command_presentation  # noqa: E402
from prepare import unwrap_example  # noqa: E402
from certificate_text import (  # noqa: E402
    install_meaning, headline, AS_IS_HEADING, COLOR_HEX, INSTRUMENT,
    certificate_for, display_name, LIMITATIONS, OUT_OF_SCOPE,
    step1_says, execution_finding_established,
)
import verdict as verdict_lib  # noqa: E402
import upstream  # noqa: E402
import fork_provenance  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCOPE = ("Assessment of documented execution in the stated environment and "
         "output format. Concerns reproducible execution only; no claim of "
         "accuracy, casework fitness, or regulatory validation.")

# Highest gate cleared, in order. The badge reflects the furthest green gate.
LADDER = ["available", "installs", "runs", "io", "content"]
LABELS = {"available": "Available", "installs": "Installs",
          "runs": "Runs", "io": "Runs + Expected IO",
          "content": "Runs + Plausible output"}
# One-line plain-language meaning of each level, for the human summary.
MEANING = {
    "none": "did not clear the first gate",
    "available": "the pinned public source exists",
    "installs": "the environment builds from source",
    "runs": "it executes end-to-end without crashing",
    "io": "it produces a non-empty file in the declared format",
    "content": "its output looks like plausible genotype-bearing data "
               "(declared columns, DNA sequences, integer read counts, and "
               "enough recognisable forensic loci)",
}


#: How the summary names each evidence claim. Every kind detect_recipe emits
#: needs a line here, or the reader gets the raw id ("platform_advice").
CLAIM_LABELS = {
    "install_method": "Install method", "published_image": "Published image",
    "bioconda_package": "Bioconda package", "fallback_environment": "Fallback environment",
    "run_command": "Run command", "example_data": "Example data", "known_issue": "Known issue",
    "documented_input": "Documented input", "author_recommendation": "Author's recommendation",
    "platform_advice": "Platform advice",
}
EVIDENCE_LEAD = ("What this run's configuration rests on, each item at the verified commit. "
                 "Open any of them to check the claim it supports.")
NEEDED_LEAD = ("The result above describes a run configured as follows. Anyone "
               "repeating it needs the same things.")
# Word for word the certificate's sentence (generate_pdf), so the two renderings
# of one note stay one registered claim.
CAVEATS_LEAD = ("Recorded automatically from the tool's public files when this run was "
                "configured. Not verified by execution, and not part of the gates "
                "above. Useful for what to check by hand.")
def _status(flag: str) -> bool:
    # Accept GitHub Actions step outcomes ("success") alongside our own words.
    return str(flag).lower() in ("pass", "true", "ok", "1", "success")


# One line, on every report: what a result is and is not. Who triggered the
# run used to get a section of its own; a verification is the same fact
# whoever asked for it, and the one thing a reader must not infer is that
# the tool's author stands behind it.
RECORD_NOTE = (
    "Verified automatically, in a clean environment, on the tool's public "
    "source at the pinned commit. This is a record of what happened, not an "
    "endorsement by the tool's author."
)


LABELS.setdefault("example", "Reproduces own example")
MEANING.setdefault("example", "the README's own command produced its documented output on the repository's own data")
#: Checks outside the ladder, shown after it, when they ran.
AUX_GATES = ("example",)


def _step1_md(report: dict) -> list[str]:
    """Step 1 opens the summary, in its own words. The forensic pipeline is a
    later section and never changes this sentence (docs/PLAN-Paso-1.md)."""
    s = report.get("step1") or {}
    if not s.get("headline"):
        return []
    lines = ["", f"**Step 1, the documented run: {s['headline']}** {s['body']}"]
    if s.get("missing_text"):
        lines += ["", f"Missing from the commit, by the blocks {s['guide']} asks for:", ""]
        lines += [f"- {block}" for block in s["missing_text"]]
    return lines


RECOMMENDATIONS_HEADING = "What the README or repository could add"
RECOMMENDATIONS_LEAD = ("Read off the repository at the verified commit. None of these changes the "
                        "result above; each would make the tool easier for a new user, and for "
                        "STRhub, to run as documented.")


def recommendations_for(report: dict, proposal: dict | None) -> list[dict]:
    """What the documentation or the repository lacks that did not decide the
    verdict: said on every report, whatever the outcome, so an author who
    passed still learns that the repository ships no example data.

    Each item is {code, text}. What DID stop the run is the verdict's
    (`verdict.readme_gaps`, `verdict.blockers`) and is not repeated here."""
    if not proposal:
        return []
    told = {g.get("item") for g in (report.get("verdict") or {}).get("readme_gaps") or []}
    out = []
    for gap in (proposal.get("readme") or {}).get("gaps") or []:
        item = gap.get("item")
        if not item or item in told:
            continue
        if item == "example_data":
            out.append({"code": item, "text":
                        "The repository ships no example input. A small example the documented "
                        "command can read, with the output it should produce, would let any user "
                        "reproduce the run without outside data."})
        else:
            out.append({"code": item, "text": gap.get("text") or ""})
    # Everything STRhub had to do that the README does not say is, as it
    # stands, a recommendation to its author.
    for number, line in enumerate((report.get("preparation") or {}).get("why") or [], 1):
        out.append({"code": f"preparation_{number}", "text": line})
    reference = (report.get("mounted_inputs") or {}).get("reference")
    signals = (proposal.get("input_type") or {}).get("signals") or {}
    if reference and not signals.get("hg38"):
        out.append({"code": "reference_assembly", "text":
                    "The documented command reads a reference genome and the README does not say "
                    "which assembly it expects. STRhub mounted hg38; stating the assembly would "
                    "remove the guess."})
    return [r for r in out if r["text"]]


PREPARATION_HEADING = "What STRhub did to get it ready"
PREPARATION_LEAD = ("The repository's own instructions were not enough to install and run the tool as written. "
                    "STRhub prepared the environment by hand, as a user would have to, and then ran the "
                    "command the README shows without changing it. Nothing below is part of that command.")
INPUTS_LEAD = ("The tool was installed with the repository's own commands, unchanged. Its documented command "
               "names files the reader is expected to bring, so STRhub supplied the inputs below and ran the "
               "command the README shows without changing anything else in it.")


def _preparation_lines(prep: dict) -> list[str]:
    """What the preparation did, one line each, for both prose copies."""
    without = prep.get("without_preparation") or {}
    lines = []
    if without.get("reason"):
        lines.append(f"Without it: {without['reason']}")
    lines.append(f"Base: {prep.get('base')}.")
    if prep.get("installation") == "repository":
        lines.append("Installation: the repository's own commands, unchanged: " + "; ".join(prep.get("steps") or []) + ".")
    else:
        lines += [f"Step: {step}" for step in prep.get("steps") or []]
    lines += [f"File {'replaced' if f.get('replaces') else 'added'}: {f['path']}" for f in prep.get("files") or []]
    lines.append(f"Sample: STRhub's {prep.get('dataset')} reference data"
                 + (f", with its loci in the {prep['regions']} layout." if prep.get("regions") else "."))
    lines.append(f"Recorded in {prep.get('file')}.")
    return lines


def _provenance_groups(prov: dict | None) -> tuple[list[str], list[str], list[str]]:
    """Split trial provenance into three plain lists for reviewers:
    what came from upstream, what was mechanically derived, and what STRhub selected."""
    if not prov:
        return [], [], []
    up = prov.get("from_upstream") or {}
    der = prov.get("derived") or {}
    hc = prov.get("harness_choices") or {}
    up_lines: list[str] = []
    inst = up.get("install") or {}
    if inst.get("evidence_source"):
        up_lines.append(f"Install ({inst.get('method', '?')}): `{inst['evidence_source']}`")
    cmd = up.get("command") or {}
    if cmd.get("evidence_source"):
        up_lines.append(f"Command: `{cmd['evidence_source']}`")
    ik = up.get("input_kind") or {}
    if ik.get("value"):
        cite = f" (`{ik['evidence_source']}`)" if ik.get("evidence_source") else " (not explicitly stated)"
        up_lines.append(f"Input format: `{ik['value']}`{cite}")
    plats = up.get("supported_platforms") or []
    if plats:
        ps = ", ".join(f"{p['platform']} (`{p['evidence_source']}`)" if p.get("evidence_source") else p["platform"]
                       for p in plats)
        up_lines.append(f"Supported platforms: {ps}")
    asm = up.get("assembly") or {}
    if asm.get("declared"):
        cite = f" (`{asm['evidence_source']}`)" if asm.get("evidence_source") else ""
        up_lines.append(f"Reference assembly: `{asm['declared']}`{cite}")
    else:
        up_lines.append("Reference assembly: not specified in repository documentation")
    reg = up.get("regions_schema") or {}
    if reg.get("format"):
        up_lines.append(f"Regions schema: `{reg['format']}` (`{reg['evidence_source']}`)")

    der_lines: list[str] = []
    for s in der.get("command_rewrites") or []:
        der_lines.append(f"`{s.get('original')}` -> `{s.get('replacement')}` ({s.get('basis')})")
    rlb = der.get("regions_layout_binding") or {}
    if rlb.get("strhub_regions_layout"):
        der_lines.append(
            f"Regions layout `{rlb['strhub_regions_layout']}` matched `{rlb.get('documented_schema')}` "
            f"(`{rlb.get('evidence_source')}`)"
        )
    ssa = der.get("single_sample_adaptation") or {}
    if ssa.get("applied"):
        paired_txt = "".join(
            f"; `{p['original']}` -> `{p['replacement']}`"
            for p in (ssa.get("paired_substitutions") or [])
        )
        cites = [ssa.get("evidence_source"), *(ssa.get("paired_evidence_sources") or [])]
        cite_str = ", ".join(f"`{c}`" for c in cites if c)
        der_lines.append(
            f"Single-sample trial mount: `{ssa.get('original')}` -> `{ssa.get('replacement')}`"
            f"{paired_txt} ({cite_str})"
        )

    hc_lines: list[str] = []
    ds = hc.get("dataset") or {}
    if ds.get("selected"):
        hc_lines.append(f"Dataset selected by STRhub: `{ds['selected']}` — {ds.get('reason', '')}")
    pl = hc.get("platform") or {}
    if pl.get("selected"):
        if pl.get("basis") == "harness_choice_from_supported":
            hc_lines.append(
                f"Platform chosen by STRhub: `{pl['selected']}` from documented platforms "
                f"({', '.join(pl.get('supported_platforms') or [])})"
            )
        elif pl.get("basis") == "upstream_single_platform":
            hc_lines.append(f"Platform used: `{pl['selected']}` (single documented platform)")
    ha = hc.get("assembly") or {}
    if ha.get("selected") and ha.get("basis") == "harness_choice_unstated":
        hc_lines.append(
            f"Assembly chosen by STRhub: `{ha['selected']}` (upstream unspecified; STRhub staged coherent "
            "BAM, FASTA and regions on hg38)"
        )
    if hc.get("regions_layout"):
        hc_lines.append(f"Regions file mounted: `{hc['regions_layout']}`")
    be = hc.get("base_environment") or {}
    if be.get("image") or be.get("description"):
        pkgs = be.get("added_packages") or []
        extras = []
        if be.get("miniforge"):
            extras.append("Miniforge (conda, python, pip)")
        if pkgs:
            extras.append("minimal build toolchain: " + ", ".join(pkgs) + " (no tool-specific libraries)")
        if be.get("submodules"):
            extras.append("git submodules initialized")
        extra_str = (
            "; added beyond plain Ubuntu: " + "; ".join(extras)
            if extras else "; no extra packages added by STRhub"
        )
        hc_lines.append(f"Base environment supplied by STRhub: `{be.get('image') or 'ubuntu:22.04'}`{extra_str}")
    return up_lines, der_lines, hc_lines


def _verdict_md(report: dict) -> list[str]:
    v = report.get("verdict")
    if not v:
        return []
    lines = _step1_md(report) + ["", f"**Verdict: {v['title']}.** {v['reason']}"]
    if v.get("blockers"):
        lines += ["", "What stopped it, and what its owner can be asked:", ""]
        for b in v["blockers"]:
            lines += [f"- {b['what']}",
                      f"  - The tool's owner: open an issue, \"{b['ask_owner']['title']}\"."]
    if v.get("readme_gaps"):
        lines += ["", "What the README does not say:", ""]
        lines += [f"- {g['text']}" for g in v["readme_gaps"]]
    return lines


def _environment_line(env: dict, code=lambda t: f"`{t}`") -> str:
    """'ubuntu-22.04 (`Dockerfile`)'. `code` wraps a file name: backticks for
    markdown, <code> for HTML."""
    return f"{', '.join(env.get('os', []))} ({code(env['dockerfile'])})"


def _install_heading(inst: dict) -> str:
    # Plain words, not the mechanism: "why the pinned commit did not build"
    # told a reader who did not know what a pinned commit was that something
    # with a name they did not know had failed.
    return "It did not build from source"


def _install_lead(inst: dict, env: dict) -> str:
    tried = ("STRhub tried to build the tool from its source at the pinned commit, "
             "following the build steps the repository declares, and the build failed.")
    return f"{tried} Nothing below the Installs gate ran."




def _run_record(m: dict, outcome: str | None = None) -> dict | None:
    """Record the configured command and, when supplied, the run step outcome.

    Preserve the full wrapper as effective_cmd; cmd/cwd remain compatible
    with older readers. A command alone never establishes execution.
    """
    cmd = (m.get("run") or {}).get("cmd")
    if not cmd:
        return None
    inner, cwd = unwrap_example(cmd)
    return {"cmd": inner, **({"cwd": cwd} if cwd else {}),
            **({"effective_cmd": cmd, "step_outcome": outcome} if outcome is not None else {})}


def _summary_md(report: dict, slug: str) -> str:
    """A human-readable attestation summary: what STRhub shows the user."""
    tool = report["tool"]
    level = report["level"]
    gates = report["gates"]
    mark = {True: "PASS", False: "—"}
    label, _ = headline(report)
    reached = f"Reached **{LABELS.get(level, 'not run')}**: {MEANING.get(level, '')}."
    lines = [f"# STRhub Verified: {tool['name']} ({slug})", "", f"**{label}.**"]
    # The tool as it is in its repository: where it stopped, why, how.
    lines += ["", f"## {AS_IS_HEADING}", *_verdict_md(report), "", reached]
    lines += [
        "",
        "### Gates",
        "",
        "| Gate | Status | Meaning |",
        "|---|---|---|",
    ]
    for g in LADDER:
        lines.append(f"| {LABELS[g]} | {mark[gates.get(g, False)]} | {MEANING.get(g, '')} |")
    for g in AUX_GATES:
        if g in gates:
            lines.append(f"| {LABELS[g]} | {mark[bool(gates[g])]} | {MEANING[g]} |")

    # Why the build failed, immediately after the ladder that says it did.
    # Nothing below this point ran, so the reader needs the reason here rather
    # than at the foot of a report about a run that never happened.
    inst = report.get("install_detail") or {}
    if inst.get("diagnostics"):
        lines += ["", f"### {_install_heading(inst)}", "",
                  _install_lead(inst, report["environment"]),
                  "",
                  "What this means:", ""]
        lines += [f"- **{who}:** {what}" for who, what in
                  install_meaning(inst.get("faults") or [])]
        lines += ["", "What failed:", "",
                  "| What happened | Times | What the log establishes |",
                  "|---|---|---|"]
        for issue in inst["diagnostics"]:
            fix = issue.get("suggestion", "—").replace("\n", " ")
            lines.append(f"| {issue['title']} | {issue.get('count', 1)} | {fix} |")
        build_log = (report.get("logs") or {}).get("build")
        if build_log:
            lines += ["", f"Full build output: [`{build_log}`]({build_log})"]

    # The author's own words about their own software, before any of STRhub's
    # findings: a run that stops where the README says it stops is not news,
    # and a reader must be able to see that without opening the repository.
    # Errors the tool itself reported: the "why" of a run that stopped, next
    # to where it stopped, and a reviewer should not have to open a container
    # log to find out.
    errs = diagnose_log.summarize(report.get("diagnostics") or {})
    if errs:
        n_items = sum(len(e["items"]) for e in errs) or sum(1 for _ in errs)
        lines += ["", "### Errors reported during the run", "",
                  f"The tool reported errors on {n_items} item(s) during the run.",
                  "This does not assess whether the results produced are correct.",
                  "", "| What happened | Times | Affected |", "|---|---|---|"]
        for e in errs:
            items = ", ".join(e["items"]) if e["items"] else "—"
            lines.append(f"| {e['title']} | {e['count']} | {items} |")
        for note in diagnose_log.external_leg_notes(report.get("diagnostics") or {}):
            lines += ["", note]

        # A failure the author can fix costs nothing to re-run, and the
        # report says so rather than leaving a dead end.
        fixable = diagnose_log.author_fixable_ids(report.get("diagnostics") or {})
        if fixable:
            lines += ["", diagnose_log.configuration_fault_sentence()]

    known = report.get("author_known_issues") or []
    if known:
        lines += ["", "### Author-documented warnings and limitations", "",
                  "Quoted from the repository's README at the verified commit. "
                  "STRhub did not establish any of this by running the tool; it is "
                  "the author's own note about their own software."]
        for k in known:
            quote = k["text"] + ("…" if k.get("truncated") else "")
            lines += ["", f"**{k['heading']}** (README line {k['line']})", ""]
            lines += [f"> {ln}" for ln in quote.splitlines() if ln.strip()]

    recs = report.get("recommendations") or []
    if recs:
        lines += ["", f"### {RECOMMENDATIONS_HEADING}", "", RECOMMENDATIONS_LEAD, ""]
        lines += [f"- {r['text']}" for r in recs]

    # How: the command the gates ran, and the logs.
    run = report.get("run") or {}
    if run.get("cmd"):
        heading, lead = command_presentation(run)
        lines += ["", f"### {heading}", "", lead, "", "```", run.get("effective_cmd", run["cmd"]), "```"]
    # Right under the command it ran: what STRhub did before it could.
    if report.get("preparation"):
        lead = INPUTS_LEAD if report["preparation"].get("installation") == "repository" else PREPARATION_LEAD
        lines += ["", f"### {PREPARATION_HEADING}", "", lead, ""]
        lines += [f"- {line}" for line in _preparation_lines(report["preparation"])]
    for leg, fname in (report.get("logs") or {}).items():
        lines.append(f"- Log ({leg}): [`{fname}`]({fname})")

    # Then the context: where the run came from, and what else it established.
    lines += ["", "## Run details", "",
              f"- Source: `{report['source']['repo']}` @ `{report['source']['ref_resolved']}`",
              f"- Environment: {_environment_line(report['environment'])}",
              f"- Generated: {report['generated']}"]
    up_note = upstream.note(report.get("upstream"))
    if up_note:
        lines.append(f"- Upstream: {up_note}")
    fork_note = fork_provenance.note((report.get("source") or {}).get("fork"))
    if fork_note:
        lines.append(f"- Fork: {fork_note}")
    if report.get("ci_run"):
        lines.append(f"- CI run: {report['ci_run']}")

    # Content highlights (the genotype-plausibility evidence), if available.
    outs = report.get("content_detail", {}).get("outputs", [])
    stats = outs[0].get("stats") if outs and isinstance(outs[0], dict) else None
    if stats:
        str_loci = stats.get("str_loci", stats.get("loci", []))
        n_str = stats.get("distinct_str_loci", len(str_loci))
        n_snp = stats.get("distinct_snp_markers", 0)
        sample = ", ".join(str_loci[:18]) + (" …" if len(str_loci) > 18 else "")
        top = ", ".join(f"{l} ({d})" for l, d in stats.get("top_loci_by_depth", [])[:6])
        markers_line = f"- STR loci detected: **{n_str}**"
        if n_snp:
            markers_line += (f"  ·  identity SNPs (rsNNNN): **{n_snp}**  "
                             f"(total panel markers: {stats.get('distinct_loci', 0)})")
        lines += [
            "",
            "## Output content (plausibility evidence)",
            "",
            f"- Sequence records: **{stats.get('rows', 0)}** "
            f"(malformed: {stats.get('malformed_rows', 0)})",
            markers_line,
            f"- Total reads across calls: **{stats.get('total_reads', 0)}** "
            f"(deepest single sequence: {stats.get('max_sequence_depth', 0)})",
            f"- STR loci: {sample}" if str_loci else "",
            f"- Top markers by read depth: {top}" if top else "",
        ]

    # Verification matrix (external and example legs), if present.
    # Which legs reported errors — the matrix flags THAT, the section below says what.
    legs_with_errors = {
        leg for leg, issues in (report.get("diagnostics") or {}).items()
        if any(i.get("severity") == "error" for i in issues)
    }

    visible = report.get("datasets") or []
    if visible:
        lines += ["", "## Verification matrix", "",
                  "| Leg | Available | Result | Errors reported | Dataset |",
                  "|---|---|---|---|---|"]
        for leg in visible:
            avail = leg.get("available", True)
            status = "N/A" if not avail else ("PASS" if leg.get("passed") else "—")
            err = "yes" if leg.get("leg") in legs_with_errors else "—"
            lines.append(
                f"| {leg.get('label', leg.get('leg', '?'))} | "
                f"{'yes' if avail else 'N/A'} | {status} | {err} | "
                f"{leg.get('dataset', leg.get('type', '—'))} |"
            )

    # Notes from reading the repository. Last before the scope statement, and
    # labelled for what they are: nothing here was established by running the
    # tool, so it must not be read alongside the gates as though it had been.
    # Before the notes and the scope: what the reader needs to hold the ladder
    # against. Phrased as requirements, not as a shortfall — every tool needs
    # something, and the useful question is what.
    ev = report.get("evidence") or []
    if ev:
        lines += ["", "## Evidence", "", EVIDENCE_LEAD]
        for e in ev:
            where = f"`{e['path']}`" + (f" line {e['line']}" if e.get("line") else "")
            # Whole, not clipped: the platform advice is the one line a reader
            # most needs entire, since the run may have gone against it.
            txt = f": `{e['text']}`" if e.get("text") and e["kind"] in ("readme", "doc", "wiki") else ""
            lines.append(f"- {CLAIM_LABELS.get(e['claim'], e['claim'])}: [{where}]({e['url']}){txt}")

    up_lines, der_lines, hc_lines = _provenance_groups(report.get("provenance"))
    if up_lines or der_lines or hc_lines:
        lines += ["", "## Provenance of this trial (upstream vs. STRhub choices)"]
        if up_lines:
            lines += ["", "### From upstream documentation", ""]
            lines += [f"- {i}" for i in up_lines]
        if der_lines:
            lines += ["", "### Mechanically derived bindings", ""]
            lines += [f"- {i}" for i in der_lines]
        if hc_lines:
            lines += ["", "### Selected by STRhub for this trial", ""]
            lines += [f"- {i}" for i in hc_lines]

    needed = report.get("needed_beyond_repo") or []
    if needed:
        lines += ["", "## What this run needed beyond the repository", "", NEEDED_LEAD, ""]
        for item in needed:
            lines.append(f"- {item}")

    cav = report.get("caveats") or {}
    if cav.get("items"):
        # The model id stays in the JSON for auditing and out of the prose. A
        # reviewer reading a forensic report has no use for it, and naming it here
        # invites the impression that the report was written by one, when the gates
        # above were measured by running the tool. What matters to the reader is
        # that this was read rather than executed, which the sentence already says.
        lines += ["", "## Notes from reading the repository", "",
                  "Recorded automatically from the tool's public files when this run "
                  "was configured. **Not verified by execution**, and not part of the "
                  "gates above. Useful for what to check by hand.", ""]
        for item in cav["items"]:
            lines.append(f"- {item}")

    lines += ["", "## Out of scope", "", "This report does not evaluate any of the following:", ""]
    lines += [f"- {i}" for i in OUT_OF_SCOPE]
    lines += ["", "## Limitations", ""]
    lim_items = (report.get("certificate") or {}).get("limitations") or LIMITATIONS
    lines += [f"- {i}" for i in lim_items]
    lines += [
        "",
        "## Scope (read this)",
        "",
        report["scope"],
        "",
        "This is **not** a claim that the genotypes are correct, nor that the tool "
        "is fit for casework or meets any regulatory standard. Concordance against "
        "known truth is out of scope.",
        "",
        RECORD_NOTE,
        "",
    ]
    return "\n".join(l for l in lines if l is not None) + "\n"


def _summary_html(report: dict, slug: str) -> str:
    """A standalone, styled HTML page for one tool — navigable as a web page."""
    import html as _html

    tool = report["tool"]
    level = report["level"]
    gates = report["gates"]
    label, color = headline(report)
    badge = COLOR_HEX.get(color, "#c33")

    def esc(s):
        return _html.escape(str(s))

    rows = []
    for g in LADDER + [a for a in AUX_GATES if a in gates]:
        ok = gates.get(g, False)
        chip = ('<span class="ok">PASS</span>' if ok
                else '<span class="no">—</span>')
        rows.append(f"<tr><td>{esc(LABELS[g])}</td><td>{chip}</td>"
                    f"<td>{esc(MEANING.get(g, ''))}</td></tr>")

    # Why the build failed — see the markdown render for why it sits this high.
    install_block = ""
    inst = report.get("install_detail") or {}
    if inst.get("diagnostics"):
        irows = "".join(
            f"<tr><td>{esc(i['title'])}</td><td>{esc(i.get('count', 1))}</td>"
            f"<td>{esc(i.get('suggestion', '—'))}</td></tr>"
            for i in inst["diagnostics"]
        )
        build_log = (report.get("logs") or {}).get("build")
        log_link = (f'<p><a href="{esc(build_log)}">Full build output</a></p>'
                    if build_log else "")
        meaning = "".join(
            f"<li><b>{esc(who)}:</b> {esc(what)}</li>" for who, what in
            install_meaning(inst.get("faults") or []))
        install_block = (
            f"<h3>{esc(_install_heading(inst))}</h3>"
            f"<p>{esc(_install_lead(inst, report['environment']))}</p>"
            f"<p><b>What this means</b></p><ul class='stats'>{meaning}</ul>"
            "<p><b>What failed</b></p>"
            "<table><thead><tr><th>What happened</th><th>Times</th>"
            "<th>What the log establishes</th></tr></thead>"
            f"<tbody>{irows}</tbody></table>{log_link}"
        )

    known_block = ""
    known = report.get("author_known_issues") or []
    if known:
        quotes = "".join(
            f"<p><b>{esc(k['heading'])}</b> (README line {esc(k['line'])})</p>"
            f"<blockquote>{'<br>'.join(esc(ln) for ln in (k['text'] + ('…' if k.get('truncated') else '')).splitlines() if ln.strip())}</blockquote>"
            for k in known)
        known_block = (
            "<h3>Author-documented warnings and limitations</h3>"
            "<p>Quoted from the repository's README at the verified commit. STRhub did "
            "not establish any of this by running the tool; it is the author's own note "
            "about their own software.</p>" + quotes)

    recs = report.get("recommendations") or []
    preparation_block = ""
    if report.get("preparation"):
        prep_items = "".join("<li>" + esc(line) + "</li>" for line in _preparation_lines(report["preparation"]))
        prep_lead = INPUTS_LEAD if report["preparation"].get("installation") == "repository" else PREPARATION_LEAD
        preparation_block = (f"<h3>{esc(PREPARATION_HEADING)}</h3><p>{esc(prep_lead)}</p>"
                             f"<ul class='stats'>{prep_items}</ul>")
    rec_items = "".join("<li>" + esc(r["text"]) + "</li>" for r in recs)
    recommendations_block = (
        f"<h3>{esc(RECOMMENDATIONS_HEADING)}</h3><p>{esc(RECOMMENDATIONS_LEAD)}</p>"
        f"<ul class='stats'>{rec_items}</ul>") if recs else ""

    # The verdict the page leads with. A copy that omits it can read as a pass
    # while the page it mirrors says "Fails".
    s1 = report.get("step1") or {}
    step1_block = ""
    if s1.get("headline"):
        missing_html = ""
        if s1.get("missing_text"):
            mitems = "".join(f"<li>{esc(b)}</li>" for b in s1["missing_text"])
            missing_html = (f"<p>Missing from the commit, by the blocks "
                            f"<code>{esc(s1.get('guide', 'docs/GUIA-PASO-1.md'))}</code> asks for:</p>"
                            f"<ul class='stats'>{mitems}</ul>")
        step1_block = (f"<p><b>Step 1, the documented run: {esc(s1['headline'])}</b> "
                       f"{esc(s1.get('body', ''))}</p>{missing_html}")
    v = report.get("verdict") or {}
    verdict_block = step1_block + (
        f"<p><b>Verdict: {esc(v['title'])}.</b> {esc(v['reason'])}</p>"
        if v.get("title") and v.get("reason") else ""
    )

    # The command the gates ran — the certificate's "Exact Run Command".
    run = report.get("run") or {}
    command_heading, command_lead = command_presentation(run)
    run_block = (
        f"<h3>{esc(command_heading)}</h3><p>{esc(command_lead)}</p>"
        f"<pre><code>{esc(run.get('effective_cmd', run['cmd']))}</code></pre>"
        if run.get("cmd") else ""
    )

    content_block = ""
    outs = report.get("content_detail", {}).get("outputs", [])
    stats = outs[0].get("stats") if outs and isinstance(outs[0], dict) else None
    if stats:
        str_loci = stats.get("str_loci", stats.get("loci", []))
        n_str = stats.get("distinct_str_loci", len(str_loci))
        n_snp = stats.get("distinct_snp_markers", 0)
        markers_li = f"<li>STR loci detected: <b>{esc(n_str)}</b>"
        if n_snp:
            markers_li += (f" &middot; identity SNPs (rsNNNN): <b>{esc(n_snp)}</b> "
                           f"(total panel markers: {esc(stats.get('distinct_loci', 0))})")
        markers_li += "</li>"
        # Which file, from the IO gate: the content gate describes the same one.
        io_outs = (report.get("io_detail") or {}).get("outputs") or []
        io0 = io_outs[0] if io_outs and isinstance(io_outs[0], dict) else {}
        file_li = ""
        if io0.get("resolved") or io0.get("path"):
            fmt = f" ({esc(str(io0.get('format')).upper())})" if io0.get("format") else ""
            file_li = f"<li>Output file: <code>{esc(io0.get('resolved') or io0.get('path'))}</code>{fmt}</li>"
        given, hit = stats.get("regions_given"), stats.get("regions_hit")
        coverage_li = (f"<li>Panel loci called: <b>{esc(hit)}</b> of {esc(given)}</li>"
                       if isinstance(given, int) and isinstance(hit, int) and given > 0 else "")
        # Every locus with its depth, as the certificate's appendix has it: a
        # reader sees the shape of the output, not six names and an ellipsis.
        depth = stats.get("top_loci_by_depth") or []
        depth_table = ""
        if depth:
            mx = max((d for _, d in depth), default=0) or 1
            drows = "".join(
                f"<tr><td><code>{esc(l)}</code></td><td>{esc(d)}</td>"
                f"<td><span class=\"bar\" style=\"width:{max(1, round(100 * d / mx))}%\"></span></td></tr>"
                for l, d in depth)
            depth_table = ("<h3>Read depth per locus</h3>"
                           "<table class=\"depth\"><thead><tr><th>Locus</th><th>Reads</th><th></th></tr></thead>"
                           f"<tbody>{drows}</tbody></table>")
        content_block = f"""
    <h2>Output content (plausibility evidence)</h2>
    <ul class="stats">
      {file_li}
      <li>Sequence records: <b>{esc(stats.get('rows', 0))}</b> (malformed: {esc(stats.get('malformed_rows', 0))})</li>
      {markers_li}
      <li>Total reads across calls: <b>{esc(stats.get('total_reads', 0))}</b> (deepest single locus: {esc(stats.get('max_sequence_depth', 0))})</li>
      {coverage_li}
      {'<li>STR loci: ' + esc(", ".join(str_loci)) + '</li>' if str_loci else ''}
    </ul>{depth_table}"""

    # Verification matrix (external and example legs).
    matrix_block = ""
    # Which legs reported errors — the matrix flags THAT, the section below says what.
    all_diags = report.get("diagnostics") or {}
    legs_with_errors = {
        leg for leg, issues in all_diags.items()
        if any(i.get("severity") == "error" for i in issues)
    }

    visible_ds = report.get("datasets") or []
    if visible_ds:
        mrows = []
        for leg in visible_ds:
            avail = leg.get("available", True)
            if not avail:
                chip = '<span class="no">N/A</span>'
            elif leg.get("passed"):
                chip = '<span class="ok">PASS</span>'
            else:
                chip = '<span class="no">—</span>'
            err = ('<span class="warn">yes</span>'
                   if leg.get("leg") in legs_with_errors else '<span class="no">—</span>')
            mrows.append(
                f"<tr><td>{esc(leg.get('label', leg.get('leg', '?')))}</td>"
                f"<td>{chip}</td>"
                f"<td>{err}</td>"
                f"<td>{esc(leg.get('dataset', leg.get('type', '—')))}</td></tr>"
            )
        matrix_block = (
            "<h2>Verification matrix</h2>"
            "<table><thead><tr><th>Leg</th><th>Result</th><th>Errors reported</th>"
            "<th>Dataset</th></tr></thead>"
            f"<tbody>{''.join(mrows)}</tbody></table>"
        )

    _up_note = upstream.note(report.get("upstream"))
    upstream_li = f"<li>Upstream: {esc(_up_note)}</li>" if _up_note else ""
    _fork_note = fork_provenance.note((report.get("source") or {}).get("fork"))
    if _fork_note:
        upstream_li += f"<li>Fork: {esc(_fork_note)}</li>"

    # Errors the tool reported, in its own section: the matrix says a leg had them,
    # this says what they were, so a reviewer never has to open a container log.
    errors_block = ""
    errs = diagnose_log.summarize(all_diags)
    if errs:
        n_items = sum(len(e["items"]) for e in errs) or len(errs)
        erows = "".join(
            f"<tr><td>{esc(e['title'])}</td><td>{e['count']}</td>"
            f"<td>{esc(', '.join(e['items']) if e['items'] else '—')}</td></tr>"
            for e in errs
        )
        notes = "".join(
            f"<p>{esc(n)}</p>"
            for n in diagnose_log.external_leg_notes(all_diags)
        )
        fixable = diagnose_log.author_fixable_ids(all_diags)
        free_note = (
            f"<p>{esc(diagnose_log.configuration_fault_sentence())}</p>"
            if fixable else ""
        )
        errors_block = (
            "<h3>Errors reported during the run</h3>"
            f"<p>The tool reported errors on {n_items} item(s) during the run. "
            "This does not assess whether the results produced are correct.</p>"
            "<table><thead><tr><th>What happened</th><th>Times</th>"
            "<th>Affected</th></tr></thead>"
            f"<tbody>{erows}</tbody></table>{notes}{free_note}"
        )

    # What the run rests on, what it needed, what was read rather than run:
    # the page and the certificate carry all three, and this copy did not.
    evidence_block = ""
    ev = report.get("evidence") or []
    if ev:
        items = []
        for e in ev:
            where = esc(e["path"]) + (f" line {esc(e['line'])}" if e.get("line") else "")
            quote = (f": <code>{esc(e['text'])}</code>"
                     if e.get("text") and e.get("kind") in ("readme", "doc", "wiki") else "")
            items.append(f"<li>{esc(CLAIM_LABELS.get(e['claim'], e['claim']))}: "
                         f"<a href=\"{esc(e['url'])}\">{where}</a>{quote}</li>")
        evidence_block = (f"<h2>Evidence</h2><p>{esc(EVIDENCE_LEAD)}</p>"
                          f"<ul class='stats'>{''.join(items)}</ul>")

    provenance_block = ""
    up_lines, der_lines, hc_lines = _provenance_groups(report.get("provenance"))
    if up_lines or der_lines or hc_lines:
        parts = ["<h2>Provenance of this trial (upstream vs. STRhub choices)</h2>"]
        for heading, group in (
            ("From upstream documentation", up_lines),
            ("Mechanically derived bindings", der_lines),
            ("Selected by STRhub for this trial", hc_lines),
        ):
            if group:
                lis = "".join(f"<li>{esc(i)}</li>" for i in group)
                parts.append(f"<h3>{heading}</h3><ul class='stats'>{lis}</ul>")
        provenance_block = "".join(parts)

    needed_block = ""
    needed = report.get("needed_beyond_repo") or []
    if needed:
        needed_block = (
            f"<h2>What this run needed beyond the repository</h2><p>{esc(NEEDED_LEAD)}</p>"
            f"<ul class='stats'>{''.join(f'<li>{esc(i)}</li>' for i in needed)}</ul>")

    # The tool as it is in its repository: where it stopped, why, how.
    reached = (f"<p>Reached <b>{esc(LABELS.get(level, 'not run'))}</b>: "
               f"{esc(MEANING.get(level, ''))}.</p>")
    opening = f"<h2>{esc(AS_IS_HEADING)}</h2>{verdict_block}{reached}"
    logs_block = "".join(
        f'<p style="font-size:.85rem">Log ({esc(leg)}): <a href="{esc(fname)}">{esc(fname)}</a></p>'
        for leg, fname in (report.get("logs") or {}).items())

    caveats_block = ""
    cav = report.get("caveats") or {}
    if cav.get("items"):
        caveats_block = (
            f"<h2>Notes from reading the repository</h2><p>{esc(CAVEATS_LEAD)}</p>"
            f"<ul class='stats'>{''.join(f'<li>{esc(i)}</li>' for i in cav['items'])}</ul>")

    ci = (f'<a href="{esc(report["ci_run"])}">CI run</a>'
          if report.get("ci_run") else "")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>STRhub Verified · {esc(tool['name'])} ({esc(slug)})</title>
<style>
  body {{ font: 16px/1.6 system-ui, sans-serif; max-width: 820px; margin: 2rem auto;
          padding: 0 1rem; background:#ffffff; color:#1a1a1a; }}
  a {{ color: #2563eb; }}
  .badge {{ display:inline-block; padding:.25rem .7rem; border-radius:999px; color:#fff; font-weight:600; background:{badge}; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
  th, td {{ text-align: left; padding: .5rem .6rem; border-bottom: 1px solid #ddd; }}
  .ok {{ color:#16a34a; font-weight:700; }}
  .no {{ color:#999; }}
  .warn {{ color:#b45309; font-weight:700; }}
  .meta li, .stats li {{ margin:.15rem 0; }}
  .scope {{ background:#f3f4f6; border-left:4px solid {badge}; padding:.8rem 1rem; border-radius:6px; }}
  code {{ background:#eef0f2; padding:.1rem .3rem; border-radius:4px; }}
  pre {{ background:#eef0f2; padding:.8rem 1rem; border-radius:6px; overflow-x:auto; white-space:pre-wrap; word-break:break-all; font-size:.85rem; }}
  pre code {{ background:none; padding:0; }}
  table.depth td {{ padding:.25rem .6rem; }}
  table.depth td:nth-child(2) {{ text-align:right; font-variant-numeric:tabular-nums; width:5rem; }}
  table.depth td:nth-child(3) {{ width:50%; }}
  .bar {{ display:inline-block; height:.6rem; background:{badge}; border-radius:3px; vertical-align:middle; }}
  nav {{ margin-bottom:1rem; }}
  @media (prefers-color-scheme: dark) {{
    body {{ background:#0d1117; color:#e6edf3; }}
    a {{ color:#58a6ff; }}
    th, td {{ border-bottom:1px solid #30363d; }}
    .scope {{ background:#161b22; }}
    code, pre {{ background:#21262d; }}
  }}
</style></head><body>
<nav><a href="index.html">← All tools</a></nav>
<h1>STRhub Verified · {esc(tool['name'])}</h1>
<p><span class="badge">{esc(label)}</span></p>
{opening}
<h3>Gates</h3>
<table><thead><tr><th>Gate</th><th>Status</th><th>Meaning</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>
{install_block}
{errors_block}
{known_block}
{run_block}
{preparation_block}
{recommendations_block}
{logs_block}
<h2>Run details</h2>
<ul class="meta">
  <li>Variant: <code>{esc(slug)}</code></li>
  <li>Source: <code>{esc(report['source']['repo'])}</code> @ <code>{esc(report['source']['ref_resolved'])}</code></li>
  <li>Environment: {_environment_line({**report['environment'], 'os': [esc(o) for o in report['environment'].get('os', [])]}, code=lambda t: f"<code>{esc(t)}</code>")}</li>
  <li>Generated: {esc(report['generated'])}</li>
  {upstream_li}
  {f'<li>{ci}</li>' if ci else ''}
</ul>
{content_block}
{matrix_block}
{evidence_block}
{provenance_block}
{needed_block}
{caveats_block}
<h2>Out of scope</h2>
<p>This report does not evaluate any of the following:</p>
<ul class="stats">{''.join(f'<li>{esc(i)}</li>' for i in OUT_OF_SCOPE)}</ul>
<h2>Limitations</h2>
<ul class="stats">{''.join(f'<li>{esc(i)}</li>' for i in ((report.get('certificate') or {}).get('limitations') or LIMITATIONS))}</ul>
<h2>Scope</h2>
<p class="scope">{esc(report['scope'])}<br><br>
This is <b>not</b> a claim that the genotypes are correct, nor that the tool is
fit for casework or meets any regulatory standard. Concordance against known
truth is out of scope.</p>
<p style="color:#888;font-size:.85rem">{esc(RECORD_NOTE)}</p>
<p style="color:#888;font-size:.85rem">Machine-readable:
<a href="{esc(slug)}.json">{esc(slug)}.json</a> ·
<a href="{esc(slug)}.badge.json">badge</a> ·
<a href="{esc(slug)}.summary.md">summary.md</a></p>
</body></html>
"""


def _certificate_cfg(report: dict, m: dict) -> dict:
    """What conclusion_items_for reads, built here the way generate_pdf
    builds it, so the block in the JSON and the certificate agree."""
    name = display_name(m)
    declared = (m.get("outputs") or [{}])[0]
    outs = (report.get("content_detail") or {}).get("outputs") or []
    stats = outs[0].get("stats") or {} if outs and isinstance(outs[0], dict) else {}
    input_type = ((m.get("inputs") or {}).get("type")
                  or (report.get("procedure_review") or {}).get("input_type")
                  or "")
    ds_entry: dict = {}
    if input_type:
        try:
            index = json.loads((ROOT / "datasets" / "index.json").read_text())
            ds_entry = dict(index.get("datasets", {}).get(input_type) or {})
        except (OSError, json.JSONDecodeError):
            ds_entry = {}
    ds_name = next((d.get("dataset") for d in (report.get("datasets") or [])
                    if d.get("leg") == "external" and d.get("dataset")), None)
    if ds_name and not ds_entry.get("name"):
        ds_entry["name"] = ds_name
    return {
        "tool_display": f"{name} {m['tool'].get('version', '')}".strip(),
        "tool_name": name,
        "input_type": input_type,
        "gates": report.get("gates") or {},
        "verdict": report.get("verdict") or {},
        "execution_finding_established": execution_finding_established(report),
        "stats": stats,
        "declared_format": (declared.get("format") or "—").upper(),
        "dataset": ds_entry,
        "repo_test_data": report.get("repo_test_data") or {},
    }


def apply_engine_record(args, path: str) -> dict | None:
    """The gate outcomes from the engine's RunRecord (harness/engine), in place
    of the step outcomes the workflow used to pass one flag at a time.

    No record means the gates never ran (a step of STRhub's own failed before
    them): every outcome is "skipped", as a skipped step's would have been, and
    `--infra-failure` says why. A failed evidence check inside a gate (the
    checkout against the reviewed procedure, the mount against the registered
    dataset) is the record's `infra_failure`, taken when the workflow passed
    none of its own."""
    p = pathlib.Path(path)
    if not p.is_file():
        args.available = args.installs = args.runs = args.example_runs = "skipped"
        args.environment_built = ""
        return None
    rec = json.loads(p.read_text())
    outcomes = rec.get("outcomes") or {}
    ladder = rec.get("ladder") or {}
    args.available = outcomes.get("available", "skipped")
    args.installs = outcomes.get("installs", "skipped")
    args.example_runs = outcomes.get("runs_example", "skipped")
    args.runs = ladder.get("runs", "skipped")
    args.io = ladder.get("io") or args.io
    args.content = ladder.get("content") or args.content
    args.environment_built = rec.get("environment_built") or ""
    if not args.infra_failure.strip() and rec.get("infra_failure"):
        args.infra_failure = rec["infra_failure"]
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--available", default="pass")
    ap.add_argument("--installs", default="fail")
    ap.add_argument("--runs", default="fail")
    ap.add_argument("--io", default="io_result.json", help="path to io_result.json")
    ap.add_argument("--content", default="content_result.json",
                    help="path to content_result.json")
    ap.add_argument("--matrix", default="matrix.json",
                    help="path to matrix.json (the external and example legs)")
    ap.add_argument("--log-external", default="",
                    help="path to captured stdout+stderr from external-data run")
    ap.add_argument("--log-build", default="",
                    help="path to captured output from the docker build (Installs)")
    ap.add_argument("--engine-record", default="",
                    help="run_record.json from harness/engine: supplies --available, --installs, "
                         "--runs, --io, --content, --example-runs, --environment-built "
                         "and (when empty) --infra-failure from the record")
    ap.add_argument("--environment-built", default="", choices=["", "primary"],
                    help="which Dockerfile produced the image the gates ran on: 'primary' "
                         "(the one the review admits) or empty when nothing built")
    ap.add_argument("--check-upstream", action="store_true",
                    help="ask GitHub how far the pinned ref has fallen behind the "
                         "repository's default branch, and whether it still exists")
    ap.add_argument("--ref", default="")
    ap.add_argument("--run-url", default="")
    ap.add_argument("--infra-failure", default="",
                    help="a step of STRhub's own (reading the repository, staging the dataset, ...) "
                         "that failed before the gates ran; names it, empty when none did")
    ap.add_argument("--example-runs", default="skipped",
                    help="outcome of the own-example step (success/failure/skipped)")
    ap.add_argument("--example", default="example.json", help="path to check_example.py output")
    ap.add_argument("--log-example", default="", help="log of the own-example leg")
    ap.add_argument("--procedure-review", default="", help="recomputed pre-execution procedure review")
    ap.add_argument("--mounted-inputs", default="", help="verified provenance of the external runtime mount")
    ap.add_argument("--recipe-proposal", default="",
                    help="detect_recipe.py output, the reading of the repository this run rests "
                         "on; lets the verdict tell a documentation gap from a failure")
    ap.add_argument("--mode", default="publish", choices=["publish", "trial"],
                    help="trial: an unpublished rehearsal of a recipe; stamped into the "
                         "report so a trial can never be mistaken for an attestation")
    args = ap.parse_args()
    if args.engine_record:
        apply_engine_record(args, args.engine_record)

    m = _manifest.load(args.manifest)
    io_detail = {}
    io_pass = False
    p = pathlib.Path(args.io)
    if p.exists():
        io_detail = json.loads(p.read_text())
        io_pass = bool(io_detail.get("passed"))

    content_detail = {}
    content_pass = False
    cp = pathlib.Path(args.content)
    if cp.exists():
        content_detail = json.loads(cp.read_text())
        content_pass = bool(content_detail.get("passed"))

    # The matrix of verification legs (external and example).
    datasets = []
    mp = pathlib.Path(args.matrix)
    if mp.exists():
        try:
            loaded = json.loads(mp.read_text())
            datasets = loaded if isinstance(loaded, list) else loaded.get("legs", [])
        except Exception:  # noqa: BLE001
            datasets = []

    gates = {
        "available": _status(args.available),
        "installs": _status(args.installs),
        "runs": _status(args.runs),
        "io": io_pass,
        "content": content_pass,
    }
    # The tool's own example, outside the ladder: present only when the manifest
    # declared one, so older readers that iterate the five ladder gates see
    # nothing new and newer ones can show the reviewer's line.
    example_detail = {}
    ep = pathlib.Path(args.example)
    if ep.exists():
        try:
            example_detail = json.loads(ep.read_text())
        except Exception:  # noqa: BLE001
            example_detail = {}
    if example_detail.get("applicable"):
        # The files the example left behind count only if the example's own
        # command exited 0. The capture wrapper copies whatever was created
        # while it ran, so a command that crashed after writing a .pyc, or one
        # that did not exist, still left something for check_example to find.
        ran_ok = args.example_runs == "success"
        if example_detail.get("passed") and not ran_ok:
            example_detail["passed"] = False
            example_detail["reason"] = (
                "The example's command did not exit successfully "
                f"(step outcome: {args.example_runs}), so the files it left behind "
                "are not counted as its output.")
        gates["example"] = bool(example_detail.get("passed")) and ran_ok

    # Highest contiguous green gate from the bottom of the ladder.
    level = "none"
    for g in LADDER:
        if gates[g]:
            level = g
        else:
            break

    report = {
        "schema": "strhub-verified/1",
        # "trial" is a rehearsal: same gates, same honesty, no catalogue entry,
        # no badge anyone can cite. Readers (the web, build_index) key on it.
        "mode": args.mode,
        "tool": m["tool"],
        # Who filled in the submission, straight from the manifest. `tool` names
        # whoever answers for the software; this names whoever asked for the run,
        # and the report must not let a reader read the first as the second.
        # None on manifests written before the form asked — an absence the prose
        # handles by naming nobody.
        "submission": m.get("submission"),
        "source": {**m["source"], "ref_resolved": args.ref or m["source"]["ref"]},
        "environment": m["environment"],
        "generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "ci_run": args.run_url,
        # The configured command and the selected run step's outcome. A failed
        # build leaves a planned command, not a claim that this command ran.
        "run": _run_record(m, args.runs),
        # The one instrument there is: the repository's own instructions, as
        # propose_manifest.py read them at the pinned commit.
        "instrument": INSTRUMENT,
        "recipe": {"origin": "proposed"},
        "gates": gates,
        "input_contract": m.get("inputs", {}),
        "level": level,
        "io_detail": io_detail,
        "content_detail": content_detail,
        "example_detail": example_detail or None,
        "datasets": datasets,
        "scope": SCOPE,
    }

    # Where the pinned commit sits now. One or two API calls, no CI: it answers
    # the question a reviewer actually has — is what was verified the version I
    # am looking at — and catches the case that matters, a ref nobody can fetch
    # any more. Omitted entirely when the check could not be made: silence beats
    # a guess about how current somebody's software is.
    if args.check_upstream:
        up = upstream.check(m["source"]["repo"], args.ref or m["source"]["ref"])
        if up:
            # When the pinned commit was made: a fact about the source, not
            # about where the branch has gone since, so it lives with the
            # source. It is what orders a tool's history (docs/PLAN-Version-
            # History.md); a report that lacks it is one from before.
            committed = up.pop("committed", None)
            if committed:
                report["source"]["committed"] = committed
            report["upstream"] = up
        # A fork is not its original: say of what, and what it changes.
        fork = fork_provenance.provenance(m["source"]["repo"], args.ref or m["source"]["ref"])
        if fork and fork.get("is_fork"):
            report["source"]["fork"] = fork

    # What the run needed that the repository does not provide.
    #
    # A green ladder reads as a property of the software, and quietly folds in
    # whatever it took to get there. For STRsearch that was an 11-column hg38
    # configuration file with flanking sequences, built by hand over half a day,
    # against a repository whose only example is hg19 and covers five markers.
    # None of that appeared anywhere, so the badge claimed more than the run
    # measured. Stating the requirements is stronger than hedging the badge: each
    # line is a checkable fact, and for a reader deciding whether to adopt the
    # tool it is the practical question — what will this cost me to run.
    needed = []
    if any(d.get("leg") == "external" and d.get("available") for d in (datasets or [])):
        if gates.get("installs"):
            needed.append(
                "Test data: no sample from the repository was used, so a public "
                "reference sample stood in."
            )
        else:
            needed.append(
                "Test data: a public reference sample was selected, but was not "
                "executed because installation did not complete."
            )
    proposal = None
    if args.recipe_proposal and pathlib.Path(args.recipe_proposal).exists():
        try:
            proposal = json.loads(pathlib.Path(args.recipe_proposal).read_text())
        except Exception:  # noqa: BLE001
            proposal = None
    env_source = (m.get("environment") or {}).get("source")
    if env_source == "documented":
        # The install commands are the repository's; the machine they ran on
        # is STRhub's, and a reader repeating the run needs to know which.
        needed.append(
            "A base environment for the documented installation: STRhub ran the repository's "
            "install commands unchanged on Ubuntu 22.04 (with conda, python and pip added when "
            "a command uses them). Base-image and package versions are not frozen by the commands."
        )
    if needed:
        report["needed_beyond_repo"] = needed

    # Whether the repository ships example data, as EVIDENCE rather than as an
    # assumption. Only a run whose recipe was proposed from the repository has
    # read the tree; for a committed recipe nobody looked, and a report must
    # then say what STRhub used rather than what the author ships. The
    # certificate used to state "This tool does not include its own demo or
    # test data" unconditionally — false for STRsearch, which ships 35 files
    # including example/test_data/test.bam.
    # What the author already wrote down as wrong or incomplete, quoted from
    # their README at the pinned ref. STRspy documents that its wrapper can
    # exit without doing any work; a report on a run that died in that wrapper
    # said nothing about it, because nobody carried the section out of the
    # README. A reader deciding whether a failure is news needs this first.
    evidence = proposal
    if evidence is not None and evidence.get("known_issues"):
        report["author_known_issues"] = evidence["known_issues"]
    # Every fact the run's configuration rests on, as something a reader can
    # open: file, line, the text as read, and the URL at the pinned ref.
    # Phase B of docs/PLAN-Claims-Need-Evidence.md — a claim that cannot be
    # checked in one click cannot be challenged either.
    if evidence is not None and evidence.get("evidence"):
        report["evidence"] = evidence["evidence"]
    if evidence is not None:
        examples = evidence.get("example_data") or []
        report["repo_test_data"] = {
            "known": True,
            "present": bool(examples),
            "count": len(examples),
            "examples": [e.get("path") for e in examples[:5] if isinstance(e, dict)],
        }

    # Notes taken while reading the repository, carried straight from the manifest
    # and kept OUT of "gates" and "diagnostics" on purpose. Those two are what
    # running the tool established; this is what somebody read beforehand, and a
    # reader has to be able to tell the difference. The provenance travels with
    # the text so they can weigh it.
    if m.get("caveats", {}).get("items"):
        report["caveats"] = m["caveats"]

    # Prefer an explicit per-variant slug from the manifest (e.g. so the PowerSeq
    # and ForenSeq variants of the same tool get distinct badges); otherwise fall
    # back to a slug derived from the tool name.
    slug = m.get("report", {}).get("slug")
    if not slug:
        slug = re.sub(r"[^a-z0-9]+", "-", m["tool"]["name"].lower()).strip("-")
    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)

    import shutil
    logs = {}
    terminals = {}
    # The build log rides along with the run logs. A reader told the build failed
    # will want the same thing a reader told a run failed wants: the output.
    for leg, flag in [("external", args.log_external), ("example", args.log_example),
                      ("build", args.log_build)]:
        if not flag:
            continue
        lp = pathlib.Path(flag)
        if lp.exists() and lp.stat().st_size > 0:
            dest = f"{slug}.log-{leg}.txt"
            shutil.copy2(lp, reports / dest)
            logs[leg] = dest
        transcript = lp.with_suffix(lp.suffix + ".terminal")
        if transcript.is_file() and transcript.stat().st_size > 0:
            dest = f"{slug}.terminal-{leg}.txt"
            shutil.copy2(transcript, reports / dest)
            terminals[leg] = dest
    if logs:
        report["logs"] = logs
    if terminals:
        report["terminals"] = terminals

    # Why the environment did not build.
    #
    # Kept out of `diagnostics`, which is keyed by verification leg and means
    # "errors the tool reported while running". A build failure happens before
    # any run, so folding it in there would put it under a heading that says
    # "during the run" and count it toward a badge suffix about a run that never
    # happened. It is its own thing, and only meaningful when Installs failed:
    # a warning in a build that succeeded is not news.
    install_detail = None
    if args.log_build and not gates["installs"]:
        issues = diagnose_log.diagnose_file(args.log_build)
        install_detail = {
            "passed": False,
            "diagnostics": issues,
            # The side each cause falls on, decided by class rather than by
            # reading the text — so a fault of ours can never be published as a
            # finding about somebody's software.
            "faults": sorted({
                f for f in (diagnose_log.fault_of(i["id"]) for i in issues) if f
            }),
        }
    if install_detail is not None:
        report["install_detail"] = install_detail

    diagnostics = {}
    for leg, flag in [("external", args.log_external), ("example", args.log_example)]:
        if not flag:
            continue
        issues = diagnose_log.diagnose_file(flag)
        if issues:
            diagnostics[leg] = issues
    if diagnostics:
        report["diagnostics"] = diagnostics

    # The one sentence for a reader who does not program. Decided from the gates,
    # the diagnostics and, when the recipe was proposed from the repository, the
    # README gaps detect_recipe found (see harness/verdict.py for the policy).
    # Whether the thing that stopped this run was STRhub's rather than the
    # tool's. Only ever from a closed list: a step of ours that failed, or a
    # log line whose class is ours (diagnose_log.STRHUB_FIXABLE).
    strhub_fault = args.infra_failure.strip() or None
    if not strhub_fault and install_detail and not gates["installs"] \
            and "strhub" in (install_detail.get("faults") or []):
        strhub_fault = "the environment's build could not fetch what STRhub supplies"
    if not strhub_fault and not gates["runs"]:
        ours = {i.get("id") for issues in diagnostics.values() for i in issues} \
            & diagnose_log.STRHUB_FIXABLE
        if ours:
            strhub_fault = ", ".join(sorted(ours))
    if not strhub_fault and gates["runs"] and not gates["io"]:
        outputs = (io_detail or {}).get("outputs") or []
        files = [f for o in outputs for f in o.get("files", [o])]
        if files and all(f.get("passed") or f.get("validation_status") == "unsupported" for f in files) \
                and any(f.get("validation_status") == "unsupported" for f in files):
            strhub_fault = "the evaluator does not support a declared VCF version or feature; format validity was not established"
        elif outputs and all(o.get("format") == "vcf" and o.get("checks", {}).get("parses_as_vcf")
                             and int(o.get("uncalled_rows") or 0) > 0
                             and int(o.get("called_records", o.get("records", 0)) or 0) == 0
                             and int(o.get("records_without_gt") or 0) == 0 for o in outputs):
            strhub_fault = "the structurally valid output VCF contains no called genotypes; this run does not establish why"
    import authorization
    procedure = authorization.refusal("The mandatory pre-execution procedure review was not supplied.")
    review_validation = authorization.Validation(False, procedure["reason"])
    if args.procedure_review:
        try:
            reviewed = json.loads(pathlib.Path(args.procedure_review).read_text())
            review_validation = authorization.validate(reviewed, m)
            if review_validation.valid:
                binding = authorization.binding_validation(report, m)
                if not binding.valid:
                    review_validation = binding
            if review_validation.valid:
                procedure = review_validation.review
            else:
                procedure = authorization.refusal(review_validation.reason)
                report["rejected_procedure_review"] = reviewed
        except (OSError, ValueError, AttributeError):
            review_validation = authorization.Validation(False, "The mandatory procedure review could not be read.")
            procedure = authorization.refusal(review_validation.reason)
    report["procedure_review"] = procedure
    if procedure.get("provenance"):
        report["provenance"] = procedure["provenance"]
    base_desc = ((procedure.get("installation") or {}).get("base_condition") or {}).get("description")
    if env_source == "documented" and base_desc and report.get("needed_beyond_repo"):
        report["needed_beyond_repo"] = [
            f"A base environment for the documented installation: STRhub ran the repository's "
            f"install commands unchanged on {base_desc}. Base-image and package versions are not frozen by the commands."
            if item.startswith("A base environment for the documented installation:")
            else item
            for item in report["needed_beyond_repo"]
        ]
    report["procedure_validation"] = {"schema": authorization.SCHEMA, "valid": review_validation.valid,
                                      "reason": review_validation.reason}
    if args.mounted_inputs and args.runs in ("success", "failure", "pass", "fail"):
        try:
            receipt = json.loads(pathlib.Path(args.mounted_inputs).read_bytes())
            if (receipt.get("schema") != "strhub-mounted-inputs/1" or receipt.get("leg") != "external"
                    or receipt.get("input_type") != m.get("inputs", {}).get("type")
                    or not review_validation.valid
                    or receipt.get("procedure_evidence_sha256") != procedure["evidence_sha256"]):
                raise ValueError("the mounted inputs do not match the reviewed procedure")
            report["mounted_inputs"] = receipt
        except (OSError, ValueError, AttributeError):
            procedure = authorization.refusal("The external run has no matching mounted-input evidence.")
            report["procedure_review"] = procedure
            report["procedure_validation"] = {"schema": authorization.SCHEMA, "valid": False,
                                              "reason": procedure["reason"]}
    mounted_reference = (report.get("mounted_inputs") or {}).get("reference")
    if mounted_reference:
        # Said with the other things the run needed: the genome is a public
        # file the documentation names, and it was STRhub that supplied it.
        report.setdefault("needed_beyond_repo", []).append(
            f"A reference genome ({mounted_reference.get('assembly') or 'as documented'}): the command "
            f"names one, and STRhub mounted the public copy at {mounted_reference['mount_path']}.")
    report["verdict"] = verdict_lib.decide(
        gates, diagnostics, proposal, m.get("compatibility"),
        strhub_fault=strhub_fault,
        procedure=procedure,
        manifest=m,
    )

    # What STRhub did to get the tool ready, when the repository's own
    # instructions were not enough: every step, every file, every input.
    installed = procedure.get("installation") or {}
    if review_validation.valid and installed.get("profile") == "strhub-prepared-environment/1" and installed.get("ready"):
        report["preparation"] = {
            "file": installed["file"], "dataset": installed["dataset"], "regions": installed.get("regions"),
            # `repository`: installed with the README's own commands, and the
            # preparation supplied inputs only. `strhub`: STRhub's steps.
            "installation": installed.get("installed_by", "strhub"),
            "base": (installed.get("base_condition") or {}).get("description"),
            "steps": installed["steps"],
            "files": [{"path": f["path"], "replaces": f["replaces"]} for f in installed.get("files") or []],
            "why": installed["why"],
            "without_preparation": (proposal or {}).get("without_preparation"),
        }

    # What the README or the repository could add, whatever the verdict.
    recommendations = recommendations_for(report, proposal)
    if recommendations:
        report["recommendations"] = recommendations

    # Step 1 in the three sentences a maintainer is owed, with the block of
    # docs/GUIA-PASO-1.md that is missing when one is. Derived from the
    # classifier's blocker, not from a word search of the README: searching a
    # README for "install" never ran anything (docs/PLAN-Paso-1.md).
    report["step1"] = step1_says(report)

    # The certificate's own words, as data: what the PDF prints in its
    # executive summary, its closing lists and its conclusion, so the page can
    # print the same and a test can hold the two to it.
    report["certificate"] = certificate_for(report, _certificate_cfg(report, m))

    (reports / f"{slug}.json").write_text(json.dumps(report, indent=2))

    # The badge is the one artifact that travels alone, and it says the
    # result in words — what happens to the tool as it is in its repository —
    # rather than the rung reached: "Installs" on a run that then failed read
    # as a result, and a green from a recipe STRhub wrote read as the tool's
    # own. One rule, certificate_text.headline, for the badge, both copies,
    # the index and the certificate; it folds in the errors the tool reported
    # (a green with errors is yellow) and says "Could not be determined" for a
    # run nobody knew how to attempt.
    message, color = headline(report)
    badge = {"schemaVersion": 1, "label": "STRhub Verified",
             "message": message, "color": color}
    (reports / f"{slug}.badge.json").write_text(json.dumps(badge, indent=2))

    (reports / f"{slug}.summary.md").write_text(_summary_md(report, slug))
    (reports / f"{slug}.html").write_text(_summary_html(report, slug))

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
