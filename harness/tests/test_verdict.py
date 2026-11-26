"""The four verdicts, one policy line each."""
import verdict
from procedure_context import decide

G_OK = {"available": True, "installs": True, "runs": True, "io": True, "content": True}
G_INSTALL_FAIL = {"available": True, "installs": False, "runs": False, "io": False, "content": False}
G_RUN_FAIL = {"available": True, "installs": True, "runs": False, "io": False, "content": False}
G_NO_OUTPUT = {"available": True, "installs": True, "runs": True, "io": False, "content": False}
PROPOSAL_OK = {"schema": "strhub-verified/recipe-proposal/1", "readme": {"gaps": [], "sufficient_to_attempt": True}}
PROPOSAL_GAPS = {"schema": "strhub-verified/recipe-proposal/1",
                 "readme": {"gaps": [{"item": "command", "text": "no command"}], "sufficient_to_attempt": False}}


def test_output_produced_is_runs_whatever_the_log_said():
    v = decide(G_OK, {"external": [{"id": "cannot_open"}]})
    assert v["code"] == "runs"


def test_example_output_alone_is_not_the_reference_run():
    # The repository's own example is a separate claim. A file it wrote does
    # not make the reference-sample run a pass.
    v = decide({**G_NO_OUTPUT, "example": True})
    assert v["code"] == "fails"
    assert "no output" in v["reason"]


def test_gpu_in_log_is_out_of_scope():
    v = decide(G_RUN_FAIL, {"external": [{"id": "requires_gpu"}]})
    assert v["code"] == "out_of_scope" and "requires_gpu" in v["reason"]


def test_declared_incompatibility_is_out_of_scope():
    v = decide(G_RUN_FAIL, declared_compatibility={"requires_gui": True})
    assert v["code"] == "out_of_scope"


def test_incomplete_proposal_is_undetermined_with_gaps():
    v = decide(G_INSTALL_FAIL, recipe_proposal=PROPOSAL_GAPS)
    assert v["code"] == "undetermined"
    assert v["basis"] == "readme"
    assert [g["item"] for g in v["readme_gaps"]] == ["command"]


def test_auto_recipe_with_fixable_failure_is_undetermined_not_fails():
    v = decide(G_RUN_FAIL, {"external": [{"id": "bad_option"}]}, recipe_proposal=PROPOSAL_OK)
    assert v["code"] == "undetermined" and v["basis"] == "recipe"


def test_submitted_recipe_with_fixable_failure_is_fails():
    v = decide(G_RUN_FAIL, {"external": [{"id": "bad_option"}]})
    assert v["code"] == "fails"


def test_install_failure_is_fails_with_the_reason():
    v = decide(G_INSTALL_FAIL)
    assert v["code"] == "fails" and "did not build" in v["reason"]


def test_ran_but_no_output_is_fails():
    v = decide(G_NO_OUTPUT)
    assert v["code"] == "fails" and "no output" in v["reason"]


def test_example_data_gap_is_never_a_reason():
    p = {"schema": "strhub-verified/recipe-proposal/1",
         "readme": {"gaps": [{"item": "example_data", "text": "none"}], "sufficient_to_attempt": True}}
    v = decide(G_INSTALL_FAIL, recipe_proposal=p)
    assert v["code"] == "fails" and v["readme_gaps"] == []


def test_proposal_with_known_limitations_is_undetermined():
    p = {**PROPOSAL_OK, "limitations": ["input_type_guessed"]}
    v = decide(G_RUN_FAIL, recipe_proposal=p)
    assert v["code"] == "undetermined"


def test_blockers_follow_the_gate_that_failed():
    assert [b["code"] for b in decide(G_INSTALL_FAIL)["blockers"]] == ["build_failed"]
    assert [b["code"] for b in decide(G_RUN_FAIL)["blockers"]] == ["run_failed"]
    assert [b["code"] for b in decide(G_NO_OUTPUT)["blockers"]] == ["no_output"]


def test_runs_has_no_blockers():
    assert decide(G_OK)["blockers"] == []


def test_readme_gaps_become_blockers_without_duplicates():
    v = decide(G_INSTALL_FAIL, recipe_proposal=PROPOSAL_GAPS)
    assert [b["code"] for b in v["blockers"]] == ["no_command", "build_failed"]



def test_nothing_executed_is_undetermined_with_an_ask_for_example_data():
    proposal = {**PROPOSAL_OK, "limitations": ["no_reference_dataset"]}
    v = decide(G_RUN_FAIL, recipe_proposal=proposal)
    assert v["code"] == "undetermined" and v["basis"] == "recipe"
    assert "nothing was executed" in v["reason"]
    assert v["blockers"][0]["code"] == "no_reference_dataset"
    # A blocker says what stopped the run and what to ask the owner; it proposes no fix.
    assert set(v["blockers"][0]) == {"code", "what", "ask_owner"}
    assert v["blockers"][0]["ask_owner"]["title"] == "Ship a small example dataset"



# --- Output counts only from a run that finished ------------------------------
# str8rzr printed its usage to the redirected output file and exited 1: a
# non-empty file with a digit in it, so IO passed. That file is the evidence the
# tool did NOT run, and it was published as "Runs as documented".

G_CRASH_LEFT_A_FILE = {"available": True, "installs": True, "runs": False, "io": True, "content": False}


def test_output_left_by_a_crashed_run_is_not_runs():
    v = decide(G_CRASH_LEFT_A_FILE)
    assert v["code"] == "fails"
    assert "exited with an error" in v["reason"]


def test_a_crash_does_not_confirm_a_guessed_input_type():
    proposal = {**PROPOSAL_OK, "limitations": ["input_type_guessed"]}
    v = decide(G_CRASH_LEFT_A_FILE, recipe_proposal=proposal)
    assert v["code"] == "undetermined" and v["basis"] == "recipe"


# --- A fault of STRhub's is never the tool's ---------------------------------

def test_strhub_fault_is_undetermined_and_asks_nothing_of_the_owner():
    v = decide(G_INSTALL_FAIL, strhub_fault="the reference genome download")
    assert v["code"] == "undetermined"
    assert v["basis"] == "strhub_infra"
    assert "reference genome download" in v["reason"]
    assert v["blockers"] == []


def test_output_still_wins_over_a_strhub_fault():
    assert decide(G_OK, strhub_fault="anything")["code"] == "runs"


RAISED = {"id": "python_exception",
          "title": "The tool raised TypeError: only 0-dimensional arrays can be converted to Python scalars"}
TIMEOUT = {"id": "run_timeout", "title": "The run did not finish within its time limit (20 minutes)"}


def test_an_exception_before_a_hang_is_named_not_only_the_time_limit():
    # NanoRepeat raised a TypeError in each worker process and then waited on
    # them until the time limit. "Did not finish in time" was all the verdict
    # said, the one thing its author could not act on.
    v = decide(G_RUN_FAIL, {"external": [RAISED, TIMEOUT]}, recipe_proposal=PROPOSAL_OK)
    assert v["code"] == "fails"
    assert v["reason"].startswith("The tool raised TypeError: only 0-dimensional arrays")
    assert "time limit" in v["reason"]
    (b,) = v["blockers"]
    assert b["code"] == "run_stopped" and "exited with an error" not in b["what"]
    assert b["ask_owner"]["body"].endswith("The log shows the tool raised TypeError: only 0-dimensional "
                                           "arrays can be converted to Python scalars.")


def test_an_exception_that_ends_the_run_is_named():
    v = decide(G_RUN_FAIL, {"external": [RAISED]}, recipe_proposal=PROPOSAL_OK)
    assert v["reason"] == ("The tool raised TypeError: only 0-dimensional arrays can be converted to Python "
                           "scalars before producing its documented output.")
    assert v["blockers"][0]["code"] == "run_failed" and "TypeError" in v["blockers"][0]["ask_owner"]["body"]


def test_a_run_stopped_at_the_limit_without_an_exception_says_only_that():
    v = decide(G_RUN_FAIL, {"external": [TIMEOUT]}, recipe_proposal=PROPOSAL_OK)
    assert v["reason"] == "The tool did not finish within the run's time limit, so it was stopped."
    assert v["blockers"][0]["code"] == "run_stopped"
    assert "raised" not in v["blockers"][0]["ask_owner"]["body"]
    # The table is not edited in place: the next verdict gets the plain text.
    assert "raised" not in verdict.BLOCKERS["run_failed"]["ask_owner"]["body"]


def test_io_only_vs_content_verified_is_explicit_and_never_silent():
    g_io_only = {"available": True, "installs": True, "runs": True, "io": True, "content": False}
    v_io = decide(g_io_only)
    v_full = decide(G_OK)
    assert v_io["code"] == "runs" and v_full["code"] == "runs"
    assert v_io["content_verified"] is False
    assert v_io["output_status"] == "output_only_content_unverified"
    assert "Output generated; STR content not verified automatically." in v_io["reason"]
    assert v_full["content_verified"] is True
    assert v_full["output_status"] == "content_verified"
    assert v_io["reason"] != v_full["reason"]


def test_authorized_external_run_is_not_masked_by_passing_own_example():
    import authorization
    from procedure_context import context

    ex_cmd = "./tool --reads test/demo.bam --output demo.vcf"
    doc_text = (
        "# Tool\n\n## Installation (Ubuntu 22.04)\n\n```sh\n"
        "apt-get update\napt-get install -y make g++\nmake\n```\n\n"
        "## Usage\n\n```sh\ntool --reads sample.bam --output result.vcf\n```\n\n"
        f"## Example\n\n```sh\n{ex_cmd}\n```\n"
    )
    doc_lines = doc_text.splitlines()
    line_of = lambda target: next(i for i, ln in enumerate(doc_lines, 1) if ln == target)
    p, m, _ = context(
        proposal_fields={
            "source_documents": [{"file": "README.md", "origin": "readme", "text": doc_text}],
            "tree_paths": ["Makefile", "README.md", "test/demo.bam"],
            "commands": [
                {"cmd": "tool --reads sample.bam --output result.vcf", "file": "README.md",
                 "line": line_of("tool --reads sample.bam --output result.vcf"), "origin": "readme"},
                {"cmd": ex_cmd, "file": "README.md", "line": line_of(ex_cmd), "origin": "readme"},
            ],
            "example": {"cmd": ex_cmd, "file": "README.md", "line": line_of(ex_cmd)},
        },
        manifest_fields={"example": {"cmd": ex_cmd, "cwd": ".", "source": "detected"}},
    )
    reviewed = authorization.prepare_review(p, m, [], [])
    assert reviewed["may_say_runs"] is True and reviewed["example_ready"] is True

    # External failed while own example passed -> verdict MUST reflect external failure, not mask it as 'runs'
    v_fail = verdict.decide({**G_RUN_FAIL, "example": True}, procedure=reviewed, manifest=m)
    assert v_fail["code"] == "fails" and v_fail["basis"] == "gates"
    assert v_fail["failure_phase"] == "runtime"
    assert "installed as documented, then exited with an error" in v_fail["reason"]
    assert "own documented example ran on its shipped data" in v_fail["reason"]

    # External passed IO but content=False while own example passed -> content_verified stays False
    v_unver = verdict.decide({"available": True, "installs": True, "runs": True, "io": True, "content": False, "example": True},
                             procedure=reviewed, manifest=m)
    assert v_unver["code"] == "runs" and v_unver["basis"] == "gates"
    assert v_unver["content_verified"] is False
    assert v_unver["output_status"] == "output_only_content_unverified"


def test_failed_authorized_build_is_not_masked_by_downstream_command_gap():
    """NanoRepeat regression: when `install_ready` is True and `docker build`
    actually ran and failed (`installs: False`), a downstream run-command gap
    (`may_say_runs: False`) must not mask the observed build failure as
    `undetermined` / `pre_execution`."""
    import json
    import pathlib
    import subprocess
    import sys
    import certificate_text
    import propose_manifest

    root = pathlib.Path(__file__).resolve().parents[2]
    snap = root / "harness" / "testdata" / "benchmark" / "nanorepeat"
    r = subprocess.run(
        [sys.executable, str(root / "harness" / "detect_recipe.py"), "--offline", str(snap)],
        capture_output=True, text=True, check=True,
    )
    prop = json.loads(r.stdout)
    built = propose_manifest.build(prop, "nanorepeat")
    prop["limitations"] = built["limitations"]
    prop["procedure"] = built["procedure"]
    reviewed = built["procedure"]
    assert reviewed["install_ready"] is True
    assert reviewed["may_say_runs"] is False

    gates = {"available": True, "installs": False, "runs": False, "io": False, "content": False}
    v = verdict.decide(gates, recipe_proposal=prop, procedure=reviewed, manifest=built["manifest"])
    assert v["code"] == "fails"
    assert v["basis"] == "gates"
    assert v["failure_phase"] == "build"
    assert "did not build" in v["reason"]
    assert v["blockers"][0]["code"] == "build_failed"

    rep = {
        "procedure_validation": {"valid": True},
        "procedure_review": reviewed,
        "verdict": v,
        "gates": gates,
    }
    assert certificate_text.execution_finding_established(rep) is True
    stages = {s["key"]: s["status"] for s in certificate_text.stage_states(gates, execution_established=True)}
    assert stages["installs"] == "FAIL"
    assert stages["runs"] == "NOT ATTEMPTED"


def test_vcf_output_preview_elides_long_meta_headers_to_show_calls(tmp_path):
    import report as report_mod

    vcf_lines = [
        "##fileformat=VCFv4.3",
        "##source=mahi_mahi-v1.0.0",
        "##reference=/data/ref/hg38.fa",
        "##mahi_mahiCommand=mahi-mahi --bam /data/in/input.bam",
    ] + [f"##INFO=<ID=F{i},Number=1,Type=String,Description=\"Field {i}\">" for i in range(25)] + [
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE",
        "chr4\t3074876\tHTT\tC\t<STR17>\t.\tPASS\tEND=3074933\tGT:DP\t0/1:52",
        "chr9\t27573528\tC9orf72\tG\t<STR8>\t.\tPASS\tEND=27573546\tGT:DP\t0/0:34",
    ]
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    (out_dir / "SAMPLE.vcf").write_text("\n".join(vcf_lines) + "\n")

    prev = report_mod.build_output_preview(out_dir, ["SAMPLE.vcf"], leg="external")
    assert prev is not None
    assert prev["truncated"] is True
    assert any("VCF meta-header lines omitted" in ln for ln in prev["lines"])
    assert any(ln.startswith("#CHROM\tPOS") for ln in prev["lines"])
    assert any("HTT" in ln for ln in prev["lines"])

