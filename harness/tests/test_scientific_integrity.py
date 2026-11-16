"""Hard scientific integrity rules for STRhub Verified:

1. Read-only repository mount (`-v <repo_path>:/app:ro`) when the Docker
   container executes the evaluated tool.
2. Mandatory documentary traceability (`evidence_source`) on every inference,
   producing `UNVERIFIED_INSUFFICIENT_DOCS` or `FAILED_AMBIGUOUS_CLI` whenever
   a parameter lacks direct backing in the repository's documentation.
3. Zero AI / LLM calls at evaluation time (100% deterministic Python code) and
   zero tool-specific lookup tables.
"""
from __future__ import annotations

import ast
import copy
import pathlib
import sys

import detect_recipe as dr
import fidelity
import prepare
import procedure
import propose_manifest as pm
import verdict
from engine import runner, stages
from test_engine import Fake, base_plan

ROOT = pathlib.Path(__file__).resolve().parents[2]
HARNESS = ROOT / "harness"
REPOS = HARNESS / "testdata" / "repos"

FORBIDDEN_AI_MODULES = {
    "openai", "anthropic", "genai", "google.generativeai", "google.genai",
    "vertexai", "litellm", "langchain", "llama_index", "ollama", "cohere",
    "mistralai", " dspy", "dspy", " groq", "groq",
}
FORBIDDEN_AI_ENDPOINTS = (
    "api.openai.com",
    "api.anthropic.com",
    "generativelanguage.googleapis.com",
    "openrouter.ai/api",
)


def _load_proposal(name: str) -> dict:
    tree, readme, repo = dr.load_offline(REPOS / name)
    return dr.detect(dr.repo_slug(repo), tree["ref"], tree, readme, "README.md")


def test_hard_rule_1_container_mounts_cloned_repo_read_only_at_app_ro(tmp_path):
    """When the Docker container executes the tool, it mounts the cloned
    repository directory as read-only (`-v /path/to/repo:/app:ro`)."""
    fake = Fake(tmp_path)
    plan = base_plan(example_ready="1", example_cmd="cd . && ./run.sh")
    (tmp_path / "work").mkdir(exist_ok=True)
    runner.run(plan, pathlib.Path("work"), tmp_path, exe=fake, python=sys.executable)

    expected_repo_mount = f"{tmp_path / 'work' / 'ctx' / 'Tool'}:/app:ro"
    container_calls = [c for c in fake.calls if c[0] == "bash" and c[1].endswith("run_container.sh")]
    assert len(container_calls) == 2  # example + external
    for call in container_calls:
        assert expected_repo_mount in call
        idx = call.index(expected_repo_mount)
        assert call[idx - 1] == "-v"
        # Ensure /app is never mounted read-write.
        assert not any(arg.endswith(":/app") or arg.endswith(":/app:rw") for arg in call)


def test_hard_rule_2_every_inference_carries_verified_evidence_source():
    """Every parameter deduced by detect_recipe.py or propose_manifest.py
    carries its exact documentary citation (`evidence_source`), verified against
    the repository's source documents."""
    assert not (ROOT / "preparations" / "hipstr.yml").exists()
    prop = _load_proposal("hipstr")
    inferences = prop["inferences"]
    assert inferences["build"] == "repo_file:Makefile"
    assert inferences["run_command"] == "README.md:L69"
    assert inferences["input_type"] == "README.md:L69"
    assert inferences["platform"] == "README.md:L36"
    assert inferences["regions"] == "README.md:L308-L322"
    assert inferences["single_sample_bams"] == "README.md:L75"
    assert inferences["output"] == "README.md:L69"

    for key in ("build", "run_command", "input_type", "platform", "regions", "single_sample_bams", "output"):
        ver = fidelity.verify_evidence_source(prop, inferences[key])
        assert ver["verified"], f"{key} citation {inferences[key]!r} failed verification"

    built = pm.build(prop, "hipstr-trial")
    review = built["procedure"]
    assert review["may_say_runs"] is True
    assert review["status_code"] == "VERIFIED_PROCEDURE_READY"
    assert review["unbacked_inferences"] == []
    for key, entry in review["inferences"].items():
        assert entry["verified"] is True, key
        assert entry["evidence_source"], key


def test_hard_rule_2_unbacked_or_ambiguous_parameters_fail_cleanly_with_status_code():
    """If a parameter lacks direct documentary backing in the repository, the
    engine refuses to guess it and marks the tool as
    `UNVERIFIED_INSUFFICIENT_DOCS` or `FAILED_AMBIGUOUS_CLI`."""
    prop = _load_proposal("hipstr")

    # 1. Remove documentary backing for the regions BED format -> cannot substitute regions,
    #    blocked as missing_file / UNVERIFIED_INSUFFICIENT_DOCS.
    prop_no_regions = copy.deepcopy(prop)
    prop_no_regions["regions"] = {"format": None, "file": None, "line": None,
                                  "end_line": None, "text": None, "evidence_source": None}
    built_no_reg = pm.build(prop_no_regions, "hipstr-no-regions")
    assert built_no_reg["procedure"]["may_say_runs"] is False
    assert built_no_reg["procedure"]["blocker"] == "missing_file"
    assert built_no_reg["procedure"]["status_code"] == "UNVERIFIED_INSUFFICIENT_DOCS"
    v_no_reg = verdict.decide(
        dict.fromkeys(["available", "installs", "runs", "io", "content"], True),
        procedure=built_no_reg["procedure"], manifest=built_no_reg["manifest"],
    )
    assert v_no_reg["code"] == "undetermined"
    assert v_no_reg["status_code"] == "UNVERIFIED_INSUFFICIENT_DOCS"

    # 2. Forged regions format in manifest without verified evidence_source -> rejected.
    forged_manifest = copy.deepcopy(built_no_reg["manifest"])
    forged_manifest["inputs"]["regions"] = "hipstr"
    forged_review = procedure.classify(prop_no_regions, forged_manifest, [], [])
    assert forged_review["may_say_runs"] is False
    assert "regions" in forged_review["unbacked_inferences"]
    assert any(a["code"] == "unbacked_inference" for a in forged_review["amendments"])

    # 3. Remove documentary backing for single-sample BAM list -> cannot reduce
    #    run1.bam,run2.bam,run3.bam,run4.bam, blocked as FAILED_AMBIGUOUS_CLI.
    prop_no_ss = copy.deepcopy(prop)
    prop_no_ss["single_sample_bams"] = {"allowed": False, "file": None, "line": None,
                                        "text": None, "evidence_source": None}
    built_no_ss = pm.build(prop_no_ss, "hipstr-no-single-sample")
    assert built_no_ss["procedure"]["may_say_runs"] is False
    assert built_no_ss["procedure"]["status_code"] == "FAILED_AMBIGUOUS_CLI"
    v_no_ss = verdict.decide(
        dict.fromkeys(["available", "installs", "runs", "io", "content"], True),
        procedure=built_no_ss["procedure"], manifest=built_no_ss["manifest"],
    )
    assert v_no_ss["code"] == "undetermined"
    assert v_no_ss["status_code"] == "FAILED_AMBIGUOUS_CLI"

    # 4. Multi-sample `--bam-samps` prevents collapsing `--bams` when arity mismatches
    #    or when the README lacks explicit 1-to-1 ordering documentation.
    mismatch_cmd = (
        "./HipSTR --bams run1.bam,run2.bam --bam-samps S1,S2,S3 "
        "--fasta genome.fa --regions str_regions.bed --str-vcf str_calls.vcf.gz"
    )
    ss_mismatch = dr.detect_single_sample_bams(prop["readme_text"], [], "README.md", mismatch_cmd)
    assert ss_mismatch["allowed"] is False and ss_mismatch["evidence_source"] is None

    multi_samp_cmd = (
        "./HipSTR --bams run1.bam,run2.bam --bam-samps S1,S2 "
        "--fasta genome.fa --regions str_regions.bed --str-vcf str_calls.vcf.gz"
    )
    readme_no_samps_doc = "\n".join(
        line for line in prop["readme_text"].splitlines() if "bam-samps" not in line
    )
    ss_undoc = dr.detect_single_sample_bams(readme_no_samps_doc, [], "README.md", multi_samp_cmd)
    assert ss_undoc["allowed"] is False and ss_undoc["evidence_source"] is None


def test_hard_rule_3_zero_ai_or_llm_calls_in_harness():
    """No file in harness/ may import an LLM SDK or call an AI endpoint at
    evaluation time."""
    py_files = [p for p in HARNESS.rglob("*.py") if "tests" not in p.parts]
    assert py_files
    for path in py_files:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root_mod = alias.name.split(".")[0]
                    assert alias.name not in FORBIDDEN_AI_MODULES and root_mod not in FORBIDDEN_AI_MODULES, (
                        f"{path}: forbidden AI import {alias.name!r}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                root_mod = node.module.split(".")[0]
                assert node.module not in FORBIDDEN_AI_MODULES and root_mod not in FORBIDDEN_AI_MODULES, (
                    f"{path}: forbidden AI import from {node.module!r}")
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                for endpoint in FORBIDDEN_AI_ENDPOINTS:
                    assert endpoint not in node.value, (
                        f"{path}: forbidden AI endpoint {endpoint!r}")
