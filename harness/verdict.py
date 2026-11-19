"""One of four verdicts, for a reader who does not program.

The gate ladder is exact and stays; this is the sentence on top of it that a
paper reviewer, or somebody who could not get the tool running at home, can
act on without reading a log:

  runs           it installed and produced its documented output: its own
                 example on its own data when the repository documents one,
                 else the documented command on STRhub's sample
  fails          it did not, and the evidence says the tool (or its recipe)
                 is what failed
  undetermined   STRhub could not work out how to run it, and says what the
                 README did not tell it; a finding about documentation
  out_of_scope   it needs something the runner cannot give (GPU, a
                 display, a licence, network at run time, another OS)

The order of the checks IS the policy. A tool that produced its output is
"runs" whatever else the log grumbled about; anything the runner structurally
cannot do beats a failure it caused; a recipe that was proposed from the
repository and could not be completed is the documentation's finding, not the
tool's; only then is a failure attributed to the tool.

Pure function, no I/O, so the policy is testable line by line.
"""
from __future__ import annotations

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import diagnose_log  # noqa: E402

TITLES = {
    "runs": "Runs",
    "fails": "Fails",
    "undetermined": "Could not be determined",
    "out_of_scope": "Out of scope for automated verification",
}


LIMITATION_TEXT = {
    "no_command": "no command line invoking the tool was found in the README",
    "install_method_unknown": "no install method was found in the repository",
    "no_reference_dataset": "STRhub holds no reference sample of the kind this tool reads and "
                            "the repository ships no example to run, so nothing was executed",
    "input_type_guessed": "no sentence in the README says what the tool takes as input, so "
                          "the reference data was chosen on the strength of mentions alone",
    "documented_file_missing": "the documented command reads a file that neither the repository nor "
                               "STRhub holds",
}

#: What stopped the run. Each blocker names the thing that was missing
#: (`what`) and what to ask the tool's owner for (`ask_owner`: the issue to
#: open). There is deliberately no "fix it yourself and retry" entry: the
#: harness audits the procedure as documented and never invites a reader to
#: change the recipe under test (docs/NO-ADAPTIVE-RETRIES.md). The web renders
#: the owner issue as a button; the codes are the contract.
BLOCKERS = {
    "documented_file_missing": {
        "what": "The documented command reads a file that is not in the repository at this commit and "
                "that STRhub does not hold, so the command cannot run as written.",
        "ask_owner": {
            "title": "Ship, or link from the README, the file the documented command reads",
            "body": "STRhub Verified tried to run the command the documentation shows, in a clean "
                    "environment at the pinned commit. The command reads a file that is not in the "
                    "repository at that commit. Shipping it, or a documented step that fetches it, would "
                    "let a new user run the command as written.",
        },
    },
    "no_reference_dataset": {
        "what": "STRhub has no reference sample of the kind this tool reads, and the repository "
                "ships no example to run, so nothing was executed.",
        "ask_owner": {
            "title": "Ship a small example dataset",
            "body": "STRhub Verified could not run the tool: it holds no public reference sample "
                    "of the input type the README describes, and the repository ships no example "
                    "data. A small example (a few reads and the expected output) would let a new "
                    "user, and STRhub, run it end-to-end.",
        },
    },
    "no_command": {
        "what": "No command line invoking the tool was found in the README.",
        "ask_owner": {
            "title": "Document the command that runs the tool",
            "body": "STRhub Verified could not find, in the README, a command line that invokes the "
                    "tool. A one-line example with an input file and the output it writes would let "
                    "a new user run it and let STRhub verify it automatically.",
        },
    },
    "install_method_unknown": {
        "what": "No way to install the tool was found: no Dockerfile, environment file, "
                "requirements, setup script, Makefile or CMake, and no install command in the README.",
        "ask_owner": {
            "title": "Document how to install the tool",
            "body": "STRhub Verified could not work out how to install the tool from the repository: "
                    "no Dockerfile, environment.yml, requirements.txt, setup script, Makefile or "
                    "CMakeLists, and no install command in the README. Any one of those would let a "
                    "stranger build it and let STRhub verify it automatically.",
        },
    },
    "install_not_copyable": {
        # `what` is replaced by the review's own sentence, which names the
        # file and line; this one stands when there is none.
        "what": "The installation the repository documents is not written as commands that can be "
                "copied and run, so it was not attempted.",
        "ask_owner": {
            "title": "Write the installation as commands that can be copied and run",
            "body": "STRhub Verified reads the installation from the repository's documentation and runs it "
                    "exactly as written, adding nothing. At this commit it could not follow it. Writing the "
                    "installation as plain commands in one code block (apt, conda, pip, make or cmake, with "
                    "the files they name in the repository) lets a new user, a reviewer and STRhub install "
                    "the tool by copying it. The forms it can follow are listed in the guide: "
                    "https://github.com/Tfronta/strhub-verified-next/blob/main/docs/GUIA-PASO-1.md",
        },
    },
    "build_failed": {
        "what": "The environment did not build from the install steps found in the repository.",
        "ask_owner": {
            "title": "Build fails from a clean checkout",
            "body": "STRhub Verified tried to build the tool from a clean checkout at the pinned "
                    "commit, following the repository's own install steps, and the build failed. "
                    "The build log is linked from the run.",
        },
    },
    "run_failed": {
        "what": "The tool was installed but exited with an error when run.",
        "ask_owner": {
            "title": "Documented command fails on a public reference sample",
            "body": "STRhub Verified installed the tool from a clean checkout at the pinned commit "
                    "and ran the command the README documents on a public hg38 reference sample; "
                    "it exited with an error. The log is linked from the run.",
        },
    },
    "run_stopped": {
        "what": "The tool was installed, and its run was stopped at the time limit before it produced its "
                "documented output.",
        "ask_owner": {
            "title": "Documented command does not finish on a public reference sample",
            "body": "STRhub Verified installed the tool from a clean checkout at the pinned commit "
                    "and ran the command the README documents on a public hg38 reference sample; "
                    "it had not finished when the run's time limit stopped it. The log is linked "
                    "from the run.",
        },
    },
    "no_output": {
        "what": "The tool ran to completion but produced no output file in the documented format.",
        "ask_owner": {
            "title": "Document the output the tool writes",
            "body": "STRhub Verified ran the tool to completion in a clean environment, but no output "
                    "file in the documented format appeared. Documenting the output file name and "
                    "format would let a user find the result and let STRhub verify it automatically.",
        },
    },
}


def blockers_for(gates: dict, limits: list[str], gaps: list[dict], ids: set[str]) -> list[dict]:
    """The blockers that apply, most actionable first, at most three."""
    out: list[str] = []
    for l in limits:
        if l in BLOCKERS:
            out.append(l)
    gap_items = {g.get("item") for g in gaps}
    if "install" in gap_items and "install_method_unknown" not in out:
        out.append("install_method_unknown")
    if "command" in gap_items and "no_command" not in out:
        out.append("no_command")
    if gates.get("available") and not gates.get("installs") and "install_method_unknown" not in out:
        out.append("build_failed")
    elif gates.get("installs") and not gates.get("runs") and "no_command" not in out:
        out.append("run_stopped" if "run_timeout" in ids else "run_failed")
    elif gates.get("runs") and not gates.get("io"):
        out.append("no_output")
    seen: list[str] = []
    for code in out:
        if code not in seen:
            seen.append(code)
    return [{"code": c, **BLOCKERS[c]} for c in seen[:3]]


def _ids(diagnostics: dict[str, list[dict]] | None) -> set[str]:
    return {i.get("id") for issues in (diagnostics or {}).values() for i in issues}


def _raised(diagnostics: dict[str, list[dict]] | None) -> str:
    """The Python exception the tool's log shows it raised ("TypeError: only
    0-dimensional arrays ..."), or "". NanoRepeat raised one in each worker
    process and then waited on them until the time limit; the verdict said
    only that time ran out, which is the one thing its author cannot act on."""
    for issues in (diagnostics or {}).values():
        for i in issues:
            if i.get("id") == "python_exception":
                return (i.get("title") or "").removeprefix("The tool raised ").strip()
    return ""


def _procedure_block(procedure: dict | None, gaps: list) -> dict | None:
    """An amended procedure, or one we cannot feed, is not a result about the
    tool — including when the gates came back green. Success does not confirm
    a guess. See docs/PLAN-Unamended-Procedure.md."""
    if isinstance(procedure, dict) and procedure.get("may_say_runs") is True:
        return None
    procedure = procedure or {}
    return {"code": "undetermined", "title": TITLES["undetermined"],
            "basis": procedure.get("basis") or "procedure",
            "reason": procedure.get("reason")
            or "STRhub did not attempt a run it could attribute to the tool.",
            "readme_gaps": gaps}


def _decide(gates: dict, diagnostics: dict[str, list[dict]] | None = None,
            recipe_proposal: dict | None = None,
            declared_compatibility: dict | None = None,
            strhub_fault: str | None = None, procedure: dict | None = None,
            manifest: dict | None = None) -> dict:
    """Return {code, title, reason, readme_gaps, basis}."""
    import authorization
    checked = authorization.validate(procedure, manifest)
    if not checked.valid:
        return {"code": "undetermined", "title": TITLES["undetermined"], "basis": "strhub",
                "reason": checked.reason, "readme_gaps": []}
    procedure = checked.review
    recipe_proposal = procedure["evidence"]["proposal"]
    recipe_proposal = {**recipe_proposal, "limitations": procedure["evidence"]["limitations"]}
    declared_compatibility = manifest.get("compatibility")
    gates = gates or {}
    if any(type(gates.get(key)) is not bool for key in ("available", "installs", "runs", "io", "content")):
        return {"code": "undetermined", "title": TITLES["undetermined"], "basis": "strhub",
                "reason": "The execution gate observations are missing or malformed.", "readme_gaps": []}
    if gates["runs"] and not (gates["available"] and gates["installs"]):
        return {"code": "undetermined", "title": TITLES["undetermined"], "basis": "strhub",
                "reason": "The execution gate observations contradict the installation or source availability.", "readme_gaps": []}
    proposal = recipe_proposal or {}
    gaps = [g for g in (proposal.get("readme") or {}).get("gaps", []) if g.get("item") != "example_data"]
    ids = _ids(diagnostics)
    # Output counts only from a run that finished. A tool that printed its usage
    # to the redirected output file and exited 1 left a non-empty file behind;
    # that file is the evidence it did NOT run, and counting it published a
    # crash as "Runs as documented". The example leg is a separate claim: a
    # file the repository's own example wrote does not satisfy the run on the
    # reference sample.
    ran = bool(gates.get("runs")) and bool(gates.get("io"))
    produced = ran

    # The repository's own example decides when there is one: its documented
    # command, on its own data, in the documented installation, with nothing
    # of STRhub's. What happened on STRhub's sample is a second observation,
    # kept in the matrix and never set against this one.
    if procedure.get("example_ready") is True and gates["installs"] and type(gates.get("example")) is bool:
        if gates["example"]:
            return {"code": "runs", "title": TITLES["runs"], "basis": "example",
                    "reason": "The tool installed with the commands its repository documents, and its "
                              "own documented example produced its output.",
                    "readme_gaps": []}
        of_example = {"example": (diagnostics or {}).get("example") or []}
        beyond = _ids(of_example) & diagnose_log.HARNESS_INCOMPATIBLE
        if beyond:
            return {"code": "out_of_scope", "title": TITLES["out_of_scope"], "basis": "environment",
                    "reason": "The tool's own example needs something the automated runner cannot provide: "
                              + ", ".join(sorted(beyond)) + ".",
                    "readme_gaps": []}
        raised = _raised(of_example)
        return {"code": "fails", "title": TITLES["fails"], "basis": "example",
                "reason": "The tool installed with the commands its repository documents, and its own "
                          "documented example " + (f"raised {raised}" if raised else "exited with an error")
                          + " before producing its output.",
                "readme_gaps": gaps}

    blocked = _procedure_block(procedure, gaps)
    if blocked:
        return blocked

    # A proposed recipe that already knows it is incomplete did not test the
    # tool, even if a file appeared. A guess confirmed by that file is how an
    # invented input used to become "Runs".
    auto = proposal.get("schema", "").startswith("strhub-verified/recipe-proposal")
    if auto and not (proposal.get("readme") or {}).get("sufficient_to_attempt", True):
        return {"code": "undetermined", "title": TITLES["undetermined"], "basis": "readme",
                "reason": "STRhub could not work out how to install or run this tool from "
                          "its repository. The README does not say enough for a stranger to "
                          "run it; each missing item is listed below.",
                "readme_gaps": gaps}
    limits = [l for l in proposal.get("limitations", []) if l in LIMITATION_TEXT]
    if auto and limits:
        return {"code": "undetermined", "title": TITLES["undetermined"], "basis": "recipe",
                "reason": "STRhub could not complete a way to run this tool: "
                          + "; ".join(LIMITATION_TEXT[l] for l in limits) + ".",
                "readme_gaps": gaps}

    if produced:
        return {"code": "runs", "title": TITLES["runs"], "basis": "gates",
                "reason": "The tool installed and its run produced its documented output.",
                "readme_gaps": []}

    # STRhub's own machinery broke before the tool had its turn: the reference
    # genome did not download, a registry refused the pull. That is not a fact
    # about the software, so it must never read as "Does not run". A failure
    # of the TOOL is the finding a reviewer, a stuck user and the owner all
    # came for; this one is ours, says so, and is not published.
    if strhub_fault:
        return {"code": "undetermined", "title": TITLES["undetermined"], "basis": "strhub",
                "reason": "STRhub's own infrastructure failed before the tool could be tested ("
                          + strhub_fault + "). Nothing here is a finding about the software; "
                          "the run has to be repeated.",
                "readme_gaps": []}

    declared = {k for k, v in (declared_compatibility or {}).items() if v}
    incompatible = ids & diagnose_log.HARNESS_INCOMPATIBLE
    if declared or incompatible:
        what = sorted(declared | incompatible)
        return {"code": "out_of_scope", "title": TITLES["out_of_scope"], "basis": "environment",
                "reason": "The tool needs something the automated runner cannot provide: "
                          + ", ".join(what) + ".",
                "readme_gaps": []}

    # It was run, and did not produce. If the recipe was auto-proposed and the
    # failure is one an author fixes by naming the right flag or file, the
    # proposal may be what is wrong, not the tool.
    fixable = ids & diagnose_log.AUTHOR_FIXABLE
    if auto and fixable and not gates.get("runs"):
        return {"code": "undetermined", "title": TITLES["undetermined"], "basis": "recipe",
                "reason": "The proposed way of running this tool did not work ("
                          + ", ".join(sorted(fixable)) + "). That may be STRhub's reading "
                          "of the README rather than the tool.",
                "readme_gaps": gaps}

    if not gates.get("available"):
        reason = "The pinned source could not be fetched."
    elif not gates.get("installs"):
        reason = "The environment did not build from the declared install steps."
    elif not gates.get("runs") and "run_timeout" in ids:
        raised = _raised(diagnostics)
        reason = (f"The tool raised {raised}, then did not finish within the run's time limit, so it "
                  "was stopped." if raised else
                  "The tool did not finish within the run's time limit, so it was stopped.")
    elif not gates.get("runs"):
        # Not "on the reference data": a tool can exit before it reads any,
        # as STRspy's wrapper does when its self-check fails.
        raised = _raised(diagnostics)
        reason = (f"The tool raised {raised} before producing its documented output." if raised else
                  "The tool exited with an error before producing its documented output.")
    else:
        reason = "The tool ran to completion but produced no output in the documented format."
    return {"code": "fails", "title": TITLES["fails"], "basis": "gates", "reason": reason,
            "readme_gaps": gaps}


def _status_code(verdict_dict: dict, procedure: dict | None) -> str:
    code = verdict_dict.get("code")
    if code == "runs":
        return "PASSED"
    if code == "out_of_scope":
        return "OUT_OF_SCOPE"
    if code == "fails":
        return "FAILED_EXECUTION"
    proc_status = procedure.get("status_code") if isinstance(procedure, dict) else None
    if proc_status in ("FAILED_AMBIGUOUS_CLI", "UNVERIFIED_INSUFFICIENT_DOCS"):
        return proc_status
    return "UNVERIFIED_INSUFFICIENT_DOCS"


def decide(gates: dict, diagnostics: dict[str, list[dict]] | None = None,
           recipe_proposal: dict | None = None,
           declared_compatibility: dict | None = None,
           strhub_fault: str | None = None, procedure: dict | None = None,
           manifest: dict | None = None) -> dict:
    """The verdict, plus the blockers a reader can act on when it is not 'runs'."""
    v = _decide(gates, diagnostics, recipe_proposal, declared_compatibility,
                strhub_fault, procedure, manifest)
    v["status_code"] = _status_code(v, procedure)
    if v.get("basis") == "strhub":
        v["blockers"] = []
        return v
    g = gates or {}
    if v["code"] == "undetermined" and g.get("example"):
        v["reason"] += " The repository's own documented example ran and produced its output."
    # No blockers for a fault of ours: every blocker carries an issue to open
    # on the author's tracker, and there is nothing to ask them.
    if v["code"] in ("runs", "out_of_scope") or v.get("basis") == "strhub":
        v["blockers"] = []
        return v
    evidence = (procedure or {}).get("evidence") or {}
    proposal = evidence.get("proposal") or {}
    limits = [l for l in evidence.get("limitations", []) if l in LIMITATION_TEXT]
    gaps = [g for g in (proposal.get("readme") or {}).get("gaps", []) if g.get("item") != "example_data"]
    v["blockers"] = blockers_for(gates or {}, limits, gaps, _ids(diagnostics))
    if (procedure or {}).get("blocker") == "install_not_copyable":
        # Nothing was built, so nothing failed to build: what stopped the run
        # is how the installation is written, and the review says where.
        lead = {"code": "install_not_copyable", **BLOCKERS["install_not_copyable"]}
        found = (procedure.get("reason") or "").strip()
        if found:
            lead = {**lead, "what": found,
                    "ask_owner": {**lead["ask_owner"],
                                  "body": lead["ask_owner"]["body"] + " What stopped it: " + found}}
        v["blockers"] = [lead] + [b for b in v["blockers"] if b["code"] not in ("build_failed", "install_method_unknown")][:2]
    raised = _raised(diagnostics)
    if raised:
        # What to fix, in the issue the author is asked to read.
        for b in v["blockers"]:
            if b["code"] in ("run_failed", "run_stopped"):
                b["ask_owner"] = {**b["ask_owner"],
                                  "body": b["ask_owner"]["body"] + f" The log shows the tool raised {raised}."}
    return v
