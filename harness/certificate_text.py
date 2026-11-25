"""What the certificate claims, as text derived from the gates.

Kept apart from the rendering (generate_pdf) on purpose: these sentences are
the report's claims about somebody's software, and they have to be testable
without a PDF toolchain — the CI job that gates every run installs no
renderer. The rendering decides where a sentence sits on the page; this
decides whether it may be said at all.
"""
from __future__ import annotations

import diagnose_log


#: The one instrument this engine has: the repository's own instructions,
#: read off the README and the tree at the pinned commit. Nothing else may
#: stand behind the badge.
INSTRUMENT = "documented"

#: The chapter a report opens with: what happens to the tool as it is in its
#: repository — the label, where it stopped, why, how.
AS_IS_HEADING = "As it is in the repository"
#: The label of a run whose environment STRhub prepared: the command is the
#: README's, the installation is not.
PREPARED_RUNS = "Documented command runs, with STRhub's preparation"
PREPARED_FAILS = "Documented command fails, with STRhub's preparation"
#: The label of a run installed with the README's own commands, where STRhub
#: supplied only the inputs the documented command leaves to its reader.
INPUTS_RUNS = "Runs as documented, on STRhub's inputs"
INPUTS_FAILS = "Does not run as documented, on STRhub's inputs"
#: The label of a report on gh-pages that is not a run of this instrument.
NOT_DOCUMENTED = "Not verified as documented"

#: Where a run that does not run stopped, in the label's words, by the rung
#: it reached. The rung itself stays in the ladder.
STOPS_AT = {
    "none": "source not available",
    "available": "stops at install",
    "installs": "stops at run",
    "runs": "no output",
    "io": "output not plausible",
}
#: The rung reached, for the line under the label. Same words as report.LABELS.
REACHED = {"none": "not run", "available": "Available", "installs": "Installs",
           "runs": "Runs", "io": "Runs + Expected IO", "content": "Runs + Plausible output"}
#: shields.io colour → the hex the HTML copies use.
COLOR_HEX = {"brightgreen": "#16a34a", "green": "#22a722", "yellow": "#d4a017",
             "red": "#c33", "lightgrey": "#9ca3af"}


#: What a certificate says about itself, in the same words on the cover, in
#: the executive summary, in the closing sections, and — since the report
#: carries the block below — on the web page. Policy about STRhub's scope,
#: not findings about any tool.
PURPOSE = "Evaluate whether the tool installs, runs end-to-end, and produces structurally valid output."
EXEC_SCOPE = "Installation, execution, and output structure evaluation."
NOT_EVALUATED = ["Genotype accuracy", "Concordance", "Forensic validity", "Regulatory compliance"]
SCOPE_STATEMENT = ("Independent automated evaluation of reproducible execution. It checks "
                   "whether the tool installs, runs end-to-end, and produces structurally valid "
                   "output in a standardized environment.")
SCOPE_NOT = ("This is not an analytical validation. Genotype accuracy, concordance, forensic "
             "suitability, and regulatory compliance are out of scope.")
DISCLAIMER = ("Each result is a dated snapshot, verified on the tool's public repository at a "
              "pinned commit. STRhub does not store tool source code.")
OUT_OF_SCOPE = [
    "Genotype correctness or accuracy",
    "Concordance against known truth sets",
    "Sensitivity, specificity, or stutter performance",
    "Allele calling accuracy or forensic casework suitability",
    "Regulatory compliance or ISO accreditation",
    "Multi-laboratory or multi-dataset reproducibility",
]
BASE_LIMITATIONS = [
    "Single reference dataset per input type",
    "Single containerized environment (Docker / ubuntu-22.04)",
    "No truth-set comparison or ground-truth genotypes",
    "No accuracy or concordance assessment",
    "No forensic or clinical validation of results",
]
LIMITATIONS = list(BASE_LIMITATIONS)


def limitations_for(dataset: dict | None = None, *, input_type: str | None = None,
                    executed: bool = True) -> list[str]:
    """Evidence-grounded technical limitations derived from the actual dataset
    technology and execution state, rather than a fixed short-read assumption."""
    items = list(BASE_LIMITATIONS)
    if not executed:
        items.append("No sequencing data were processed because execution did not complete")
        return items
    ds = dataset or {}
    hint = " ".join(str(x or "") for x in (
        input_type,
        ds.get("chemistry"),
        ds.get("sequencer"),
        ds.get("name"),
    )).lower()
    if any(tok in hint for tok in ("ont", "nanopore", "pacbio", "hifi", "revio", "ccs")):
        items.append(
            "Long-read sequencing characteristics apply (basecalling accuracy, homopolymers, "
            "unphased reads, or extreme repeat expansions can affect allele resolution)"
        )
    elif "illumina" in hint:
        items.append("Short-read limitations apply (very long STR alleles may not span single short reads)")
    elif any(tok in hint for tok in ("capillary", "fsa", "ce-")):
        items.append(
            "Capillary electrophoresis fragment-sizing characteristics apply "
            "(stutter artifacts and dye-channel calibration are not evaluated)"
        )
    return items
CERTIFICATE_SCHEMA = "strhub-verified/certificate/1"


def display_name(m: dict) -> str:
    """The tool's name as the project writes it: the manifest's when it has a
    capital; else the repository's segment, which keeps the author's case
    (.title() made "strspy" into "Strspy")."""
    raw = m["tool"]["name"]
    repo_name = (m.get("source", {}).get("repo") or "").rstrip("/").split("/")[-1]
    if raw != raw.lower():
        return raw
    return repo_name if repo_name.lower() == raw.lower() else raw.title()


def stage_states(gates: dict | None, *, execution_established: bool | None = True) -> list[dict]:
    """Single source of truth for the five cover verification capabilities.

    A stage downstream of a failed or unestablished gate is always
    `NOT ATTEMPTED` (never `PASS` and never `FAIL`), preventing the cover or
    summary from contradicting the gate ladder.
    """
    g = dict(gates or {})
    avail = bool(g.get("available"))
    inst = bool(g.get("installs"))
    runs = bool(g.get("runs"))
    io = bool(g.get("io"))
    content = bool(g.get("content"))

    if execution_established is False:
        return [
            {"key": "available", "label": "Source available", "status": "PASS" if avail else "FAIL"},
            {"key": "installs", "label": "Installation", "status": "PASS" if inst else "NOT ATTEMPTED"},
            {"key": "runs", "label": "End-to-end execution", "status": "PASS" if runs else "NOT ATTEMPTED"},
            {"key": "output", "label": "Output generated",
             "status": "PASS" if io else ("NOT ESTABLISHED" if runs else "NOT ATTEMPTED")},
            {"key": "content", "label": "Plausible output",
             "status": "PASS" if content else ("NOT ESTABLISHED" if io else "NOT ATTEMPTED")},
        ]

    return [
        {"key": "available", "label": "Source available", "status": "PASS" if avail else "FAIL"},
        {"key": "installs", "label": "Installation",
         "status": "NOT ATTEMPTED" if not avail else ("PASS" if inst else "FAIL")},
        {"key": "runs", "label": "End-to-end execution",
         "status": "NOT ATTEMPTED" if not inst else ("PASS" if runs else "FAIL")},
        {"key": "output", "label": "Output generated",
         "status": "NOT ATTEMPTED" if not runs else ("PASS" if io else "FAIL")},
        {"key": "content", "label": "Plausible output",
         "status": "NOT ATTEMPTED" if not io else ("PASS" if content else "FAIL")},
    ]


def certificate_for(report: dict, cfg: dict) -> dict:
    """The certificate's own words, as data in the report: the label and the
    rung, the executive summary, the closing lists and the conclusion — so
    the PDF, the copies and the web page print one text, and a test can hold
    them to it. `cfg` is what conclusion_items_for reads (tool_display, gates,
    verdict, stats, declared_format, dataset, repo_test_data)."""
    label, _ = headline(report)
    level = report.get("level", "none")
    gates = dict(report.get("gates") or {})
    n_pass = sum(1 for k in ("available", "installs", "runs", "io", "content") if gates.get(k))
    verdict = report.get("verdict") or {}
    reached, reached_long = REACHED.get(level, "not run"), f"{REACHED.get(level, 'not run')}, {n_pass}/5 gates passed"
    if verdict.get("basis") == "example":
        # The repository's own example decided. The five gates describe the
        # run on STRhub's sample, which is another matter: counting them here
        # would read "2/5" under a result that says the tool runs.
        reached = "Reproduces own example" if verdict.get("code") == "runs" else "Installs"
        reached_long = ("Installs and reproduces its own example" if verdict.get("code") == "runs"
                        else "Installs; its own example did not produce its output")
    return {
        "schema": CERTIFICATE_SCHEMA,
        "label": label,
        "reached": reached,
        "stages": stage_states(gates, execution_established=cfg.get("execution_finding_established")),
        "summary": {
            "purpose": PURPOSE,
            "result": label,
            "reached": reached_long,
            **({"why": verdict["reason"]} if verdict.get("reason") else {}),
            "scope": EXEC_SCOPE,
            "not_evaluated": list(NOT_EVALUATED),
        },
        "conclusion": [{"title": t, "body": b} for t, b in conclusion_items_for(cfg)],
        "out_of_scope": list(OUT_OF_SCOPE),
        "limitations": limitations_for(
            cfg.get("dataset"),
            input_type=cfg.get("input_type"),
            executed=bool(gates.get("installs")),
        ),
        "scope": {"statement": SCOPE_STATEMENT, "not": SCOPE_NOT, "disclaimer": DISCLAIMER},
    }


def errors_reported(report: dict) -> bool:
    return any(i.get("severity") == "error"
               for issues in (report.get("diagnostics") or {}).values() for i in issues)


#: The four blocks docs/GUIA-PASO-1.md asks for, in its words. A report that
#: says a block is missing uses the same name the guide gives it, so correcting
#: the commit is following that list rather than interpreting a paragraph.
GUIDE = "docs/GUIA-PASO-1.md"
GUIDE_BLOCKS = {
    "install": "Installation, copyable",
    "command": "One command",
    "input": "The declared input",
    "output": "The declared output",
}

#: Which block of the guide a `procedure.blocker` points at, and where the gap
#: is. `commit` is a finding about the documentation, and the author can close
#: it. `strhub` is ours: our sample shelf, or our own reader rewriting the
#: command. A gap of ours is never told as a gap of theirs.
STEP1_BLOCKERS = {
    "no_install_procedure":             ("install", "commit"),
    "install_not_copyable":             ("install", "commit"),
    "published_image":                  ("install", "commit"),
    "no_command":                       ("command", "commit"),
    "synopsis_trimmed":                 ("command", "commit"),
    "output_unnamed":                   ("output", "commit"),
    "input_guessed":                    ("input", "commit"),
    "missing_file":                     ("input", "commit"),
    "ambiguous_regions_schema":         ("input", "commit"),
    "input_platform_unproven":          ("input", "commit"),
    "input_assembly_mismatch":          ("input", "commit"),
    "unbacked_inference":               ("command", "commit"),
    "install_profile_unsupported":      ("install", "strhub"),
    "command_profile_unsupported":      ("command", "strhub"),
    "prerequisite_profile_unsupported": ("command", "strhub"),
    "working_directory_changed":        ("command", "strhub"),
    "image_invocation_unsupported":     ("install", "strhub"),
    "command_changed":                  ("command", "strhub"),
    "capture_wrapper_missing":          ("command", "strhub"),
    "capture_wrapper_changed":          ("command", "strhub"),
    "flag_injected":                    ("command", "strhub"),
    "flag_dropped":                     ("command", "strhub"),
    "input_swapped":                    ("input", "strhub"),
    "input_not_substituted":            ("input", "strhub"),
    "missing_input":                    ("input", "strhub"),
    "ssh_rewritten":                    ("install", "strhub"),
    "procedure_evidence_missing":       (None, "strhub"),
    "procedure_evidence_invalid":       (None, "strhub"),
}

#: The three sentences of step 1, and the fourth case that is ours. None of
#: them says the tool does not work: that is not what any of them observed.
#: docs/PLAN-Paso-1.md fixes this wording; the web carries it in es/en/pt.
STEP1_RUNS = (
    "A third party installed the tool with the steps this commit states and ran the command it "
    "writes, and the output file that command names appeared. This says nothing about genotypes "
    "or about concordance on any reference panel."
)
STEP1_DOES_NOT_RUN = (
    "That does not mean the tool does not work. It means a third party following the README at "
    "this commit did not reach the end. Fix the documentation, or the step that broke, and try "
    "the link again on the new commit."
)
STEP1_CANNOT_TELL = (
    "Nothing was executed. That does not mean the tool does not work: what the guide asks for is "
    "missing from the README at this commit. Add it and try the link again on the new commit."
)
STEP1_OURS = "The limitation is ours. Nothing here is a finding about the tool."


def step1_says(report: dict) -> dict:
    """The step 1 result in the three sentences a maintainer is owed, plus the
    block of the guide that is missing when one is.

    `code` is `runs`, `does_not_run`, `cannot_tell` or `ours`. The first two
    are findings about the commit; `cannot_tell` is a finding about its
    documentation; `ours` is a limitation of STRhub's reference data or of its
    own reader, and must not be rendered as the tool failing.

    `missing` carries the guide's block keys, not their English names, so the
    web can say them in es/en/pt without parsing a sentence. `missing_text` is
    the same list in the words this repository prints.
    """
    verdict = report.get("verdict") or {}
    code = verdict.get("code")
    review = report.get("procedure_review") or {}
    blocker = review.get("blocker") or ""
    # The blocker decides whose the gap is, and the verdict's `basis` only
    # stands in when the blocker is one this table does not know. They disagree
    # on purpose for two of them: trimming a usage synopsis, or accepting an
    # unnamed output, would be STRhub amending the procedure, which is why the
    # classifier calls the amendment ours. But what the author can act on is
    # that the commit states no command and names no output, so the reader is
    # owed the block of the guide, not a sentence about our machinery
    # (docs/PLAN-Paso-1.md).
    block, whose = STEP1_BLOCKERS.get(blocker, (None, "")) if blocker in STEP1_BLOCKERS \
        else (None, "strhub" if verdict.get("basis") in ("strhub_infra", "scope", "strhub") else "commit")

    def said(code, headline, body, missing=()):
        return {"code": code, "headline": headline, "body": body, "missing": list(missing),
                "missing_text": [GUIDE_BLOCKS[b] for b in missing], "guide": GUIDE}

    if code == "runs":
        return said("runs", "As documented, it runs.", STEP1_RUNS)
    if code == "fails":
        return said("does_not_run", "As documented, it does not run.",
                    " ".join(x for x in (verdict.get("reason"), STEP1_DOES_NOT_RUN) if x))
    if code != "undetermined":
        return said(code or "none", "", "")

    reason = (review.get("reason") if blocker != "ready" else None) or verdict.get("reason") or ""
    if whose == "strhub":
        return said("ours", "STRhub could not attempt the documented run.",
                    " ".join(x for x in (reason, STEP1_OURS) if x))
    missing = [block] if block else _gap_blocks(verdict.get("readme_gaps") or [])
    return said("cannot_tell", "As documented, a third party cannot tell how to run it.",
                " ".join(x for x in (reason, STEP1_CANNOT_TELL) if x), missing)


#: The README gaps detect_recipe reports, mapped onto the guide's blocks.
#: They never decide whether a commit is runnable; here they only put a name
#: on a gap the classifier already found.
_GAP_BLOCK = {"install": "install", "install_steps": "install", "command": "command",
              "usage": "command", "input": "input", "input_type": "input",
              "output": "output", "output_format": "output"}


def _gap_blocks(gaps: list) -> list[str]:
    out = []
    for gap in gaps:
        block = _GAP_BLOCK.get(gap.get("item") or "")
        if block and block not in out:
            out.append(block)
    return out


def headline(report: dict) -> tuple[str, str]:
    """The label, in words, and its shields colour: what the run says about
    the tool AS IT IS in its repository. The badge, both summaries, the
    index and the certificate all print this and nothing else as the result;
    the rung reached is a detail under it.

      Runs as documented                          the documented run produced its output
      Runs as documented (errors reported)        … and the tool's log reported errors
      Does not run as documented: stops at run   the documented run did not, and where
      Could not be determined                     nobody knew how to attempt it (the README)
      Out of scope                                the free runner cannot provide something
      Not verified as documented                  not a run of the repository's instructions
    """
    if not is_documented_run(report):
        return NOT_DOCUMENTED, "lightgrey"
    code = (report.get("verdict") or {}).get("code")
    level = report.get("level", "none")
    if code == "undetermined":
        return "Could not be determined", "lightgrey"
    if code == "out_of_scope":
        return "Out of scope", "lightgrey"
    runs = code == "runs" if code else level in ("io", "content")
    # A run STRhub prepared says so in the label itself: the badge travels
    # alone, and "as documented" would claim the installation for the README.
    if report.get("preparation"):
        own_install = report["preparation"].get("installation") == "repository"
        ran, failed = (INPUTS_RUNS, INPUTS_FAILS) if own_install else (PREPARED_RUNS, PREPARED_FAILS)
        if runs:
            return (ran + " (errors reported)", "yellow") if errors_reported(report) else (ran, "green")
        return failed, "red"
    if runs:
        if errors_reported(report):
            return "Runs as documented (errors reported)", "yellow"
        # Content (a file that looks like genotypes) does not strengthen the
        # colour. Phase 1 claims execution, not analytical validity.
        return "Runs as documented", "green"
    return f"Does not run as documented: {STOPS_AT.get(level, 'stops at ' + level)}", "red"


def is_documented_run(report: dict) -> bool:
    """Whether a report is a run of the repository's own instructions, which
    is all this engine writes. A report already on gh-pages that is anything
    else (another instrument, a record that is not a run) is history this
    engine did not produce: it is never the badge. Reports from before the
    `instrument` field are recognised by the proposal that wrote them."""
    if report.get("record_type"):
        return False
    instrument = report.get("instrument")
    if instrument:
        return instrument == INSTRUMENT
    return ((report.get("recipe") or {}).get("origin") == "proposed"
            or (report.get("caveats") or {}).get("source") == "detect_recipe")


def test_data_item(cfg: dict, ds_name: str) -> tuple[str, str]:
    """What the run used (or selected, when installation stopped before execution)
    for input, and — only on evidence — whether the repository ships any of its own."""
    gates = dict(cfg.get("gates") or {})
    attempted = bool(gates.get("installs"))
    td = cfg.get("repo_test_data") or {}
    if not attempted:
        selected = (f"STRhub Verified selected {ds_name} as the reference dataset, "
                    "but it was not processed because the installation did not complete.")
        if not td.get("known"):
            return ("Reference dataset selected (not executed)", selected)
        if td.get("present"):
            n = td.get("count") or 0
            return ("Repository test data not used",
                    f"The repository ships example data ({n} file(s)), which was not used. {selected}")
        return ("No bundled demo data",
                f"{cfg['tool_name']} ships no test or demo data of its own. {selected}")

    used = (f"STRhub Verified supplied {ds_name} as the reference input for this "
            "verification run. Users replicating this result should use the same or "
            "equivalent publicly available reference material.")
    if not td.get("known"):
        return ("Reference input", used)
    if td.get("present"):
        n = td.get("count") or 0
        return ("Repository test data not used",
                f"The repository ships example data ({n} file(s)), which this run did not "
                f"use: the gates above ran on STRhub's reference dataset. {used}")
    return ("No bundled demo data",
            f"{cfg['tool_name']} ships no test or demo data of its own. {used}")


def execution_finding_established(report: dict) -> bool | None:
    """Presentation status for new reports; historical blocks remain unchanged.

    This is not authorization. The engine/publisher separately revalidate the
    full evidence; a rendering flag never grants permission to execute.
    """
    if "procedure_validation" not in report:
        return None
    review, verdict = report.get("procedure_review") or {}, report.get("verdict") or {}
    reviewed = (review.get("may_say_runs") is True
                or (review.get("example_ready") is True and verdict.get("basis") == "example"))
    return bool((report.get("procedure_validation") or {}).get("valid") and reviewed
                and verdict.get("code") in ("runs", "fails")
                and verdict.get("basis") not in ("strhub_infra", "scope", "strhub"))


def conclusion_items_for(cfg: dict) -> list[tuple[str, str]]:
    """The certificate's closing claims, each one derived from a gate.

    This used to be four fixed paragraphs asserting success with the numbers
    interpolated, so a run that stopped at Installs was certified as "installs
    and executes without error ... generated a structurally valid output file",
    with "0 loci" and a read depth of "0 at —" as the only hint that nothing
    had run. A PDF travels on its own, detached from the page and the log; it
    may not say the opposite of the report it renders.
    """
    if cfg.get("execution_finding_established") is False:
        items = [("Procedure not established",
                  "The recorded gate observations do not establish whether the documented procedure succeeded or failed."),
                 ("Observations retained",
                  "The supplied run and output observations remain in the report; they do not replace procedure evidence.")]
        verdict = cfg.get("verdict") or {}
        if verdict.get("title") and verdict.get("reason"):
            items.append((f"Verdict: {verdict['title']}", verdict["reason"]))
        items.append(("Reproducibility not established",
                      "These observations are insufficient to establish a reproducible documented execution finding."))
        return items
    verdict = cfg.get("verdict") or {}
    if verdict.get("basis") == "example":
        # The repository's own example decided: nothing here is about
        # STRhub's sample, so nothing here speaks of loci or reference data.
        ok = verdict.get("code") == "runs"
        items = [("Reproduces its own example" if ok else "Does not reproduce its own example",
                  f"{cfg['tool_display']} installs with the commands its repository documents, in a clean "
                  "ubuntu-22.04 environment at the pinned commit. The example its documentation shows, run on "
                  "the data the repository ships, "
                  + ("produced its output." if ok else
                     "stopped before producing its output. The messages it printed are in the execution log."))]
        if verdict.get("title") and verdict.get("reason"):
            items.append((f"Verdict: {verdict['title']}", verdict["reason"]))
        items.append(("Reproducibility statement",
                      "The documented installation and the documented example command, executed at the "
                      "pinned commit in the described environment, are sufficient to reproduce this "
                      "verification result independently."))
        return items
    stats = cfg.get("stats") or {}
    top_loci = stats.get("top_loci_by_depth", [])
    n_loci = stats.get("distinct_str_loci", 0)
    max_depth = stats.get("max_sequence_depth", 0)
    deepest_locus = top_loci[0][0] if top_loci else "—"
    fmt = (cfg.get("declared_format") or "").strip()
    fmt_label = f"{fmt} " if fmt and fmt != "—" else ""
    ds_name = (cfg.get("dataset") or {}).get("name") or "a public reference dataset"
    where = "a clean ubuntu-22.04 environment at the pinned commit"
    gates = dict(cfg.get("gates") or {})
    verdict = cfg.get("verdict") or {}

    if gates.get("runs"):
        ran = ("Runs end-to-end",
               f"{cfg['tool_display']} installs and executes without error in {where}.")
    elif gates.get("installs"):
        ran = ("Does not run end-to-end",
               f"{cfg['tool_display']} installs in {where}, but the documented command "
               "stopped with an error before finishing. The messages it printed are in "
               "the execution log; Section 4 shows how far it got.")
    else:
        ran = ("Does not install",
               f"The environment for {cfg['tool_display']} could not be built from the "
               "declared install steps, so nothing further was attempted.")

    if gates.get("content"):
        input_type = str(cfg.get("input_type") or "").lower()
        panel_label = (cfg.get("dataset") or {}).get("panel_label")
        if not panel_label:
            if input_type.endswith("-med"):
                panel_label = "disease-associated STR loci"
            elif input_type.endswith("-y"):
                panel_label = "Y-STR loci"
            else:
                panel_label = "target forensic STR loci"
        produced = ("Produces plausible output",
                    f"The tool generated a structurally valid {fmt_label}output file containing "
                    f"{n_loci} distinct recognizable loci ({panel_label}); structural plausibility "
                    f"checks verify output format and locus presence, not genotype validity or "
                    f"completeness across every listed locus.")
    elif gates.get("io"):
        produced = ("Produces output in the declared format",
                    f"The tool wrote a non-empty {fmt_label}file. Output generated; STR content "
                    "not verified automatically.")
    else:
        produced = ("No output produced",
                    "No file in the declared format was written, so nothing could be checked "
                    "for structure or content. This says the run did not get that far; it is "
                    "not a finding about the quality of the software.")

    items = [ran, produced]
    # The one sentence the web leads with, in the certificate too.
    if verdict.get("title") and verdict.get("reason"):
        items.append((f"Verdict: {verdict['title']}", verdict["reason"]))
    if gates.get("installs"):
        repro = (
            "Repeatability of this verification run",
            "The pinned commit, declared base environment, executed installation and "
            "analysis commands, reference input metadata, and CI logs recorded in this "
            "report document the procedure attempted. Base image and unpinned package "
            "versions can change over time, so exact reproduction requires matching "
            "those dependency versions.",
        )
    else:
        repro = (
            "Repeatability of this build attempt",
            "The pinned commit, declared base environment, executed installation "
            "commands, carrier Dockerfile, and CI build log recorded in this report "
            "document the build attempt. Because base image and system package versions "
            "are not pinned by the commands, exact long-term reproduction is not "
            "guaranteed; the documented analysis command was not executed.",
        )

    items += [
        test_data_item(cfg, ds_name),
        repro,
    ]
    return items


def install_meaning(faults: list[str]) -> list[tuple[str, str]]:
    """What a failed build means for each reader, in their own terms."""
    run = ("A build from source at this commit stopped in a clean environment; the "
           "observed build log lines are cited below.")
    review = ("Nothing ran, so this says nothing about the software's output. It "
              "records that this build attempt stopped at the Installs stage and "
              "cites the observed build log lines below.")
    return [("If you are trying to run it", run),
            ("If you are reviewing a paper", review),
            ("If you maintain it", diagnose_log.install_fault_sentence(faults))]
