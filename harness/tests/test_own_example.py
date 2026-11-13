"""The repository's own example is the result when there is one.

Its documented command, on the data the repository ships, in the documented
installation: nothing of STRhub's is in that run. It does not wait for the run
on STRhub's sample to be possible, and that second run never overrules it."""
import json
import pathlib
import subprocess
import sys

import yaml

import authorization
import certificate_text as ct
import documented_install as di
import fidelity
import prepare
import verdict

ROOT = pathlib.Path(__file__).resolve().parents[2]
# A command a README shows on STRhub-shaped placeholders, which this profile
# cannot point at a sample (a list), and one on the repository's own data.
CITED = "tool --reads run1.bam,run2.bam --output out.vcf"
EXAMPLE = "tool --reads example/sample.bam --output example/out.vcf"


def case(with_example=True):
    install = "```bash\npip install .\n```"
    text = ("# Tool\n\n## Installation\n\n" + install + "\n\n## Usage\n\n```sh\n" + CITED + "\n```\n\n"
            "## Example\n\n```sh\n" + EXAMPLE + "\n```\n")
    line = lambda cmd: next(i for i, row in enumerate(text.splitlines(), 1) if row == cmd)
    source = {"repo": "https://github.com/example/tool", "ref": "a" * 40}
    p = {**source, "build": {"method": "pip", "file": "setup.py"}, "tree_truncated": False,
         "tree_paths": ["README.md", "setup.py", "example/sample.bam"],
         "source_documents": [{"file": "README.md", "origin": "readme", "text": text}],
         "commands": [{"cmd": CITED, "file": "README.md", "line": line(CITED), "origin": "readme"},
                      {"cmd": EXAMPLE, "file": "README.md", "line": line(EXAMPLE), "origin": "readme"}]}
    m = {"tool": {"name": "Tool", "version": "test"}, "source": source, "environment": dict(di.ENVIRONMENT),
         "inputs": {"type": "illumina-bam-hg38"},
         "run": {"cmd": prepare.example_wrapper(fidelity.rewrite(CITED, "illumina-bam-hg38")["command"], ".")},
         "outputs": [{"path": "out.vcf", "format": "vcf", "min_records": 1}]}
    if with_example:
        m["example"] = {"cmd": EXAMPLE, "cwd": ".", "source": "detected"}
    return p, m


def gates(example=None, runs=False, installs=True):
    g = {"available": True, "installs": installs, "runs": runs, "io": runs, "content": False}
    if example is not None:
        g["example"] = example
    return g


def decide(g, p, m, diagnostics=None, **kw):
    review = authorization.prepare_review(p, m, [], [])
    return verdict.decide(g, diagnostics, procedure=review, manifest=m, **kw), review


def test_the_example_is_ready_when_the_run_on_strhub_s_sample_is_not():
    p, m = case()
    review = authorization.prepare_review(p, m, [], [])
    assert review["install_ready"] and review["example_ready"] and not review["may_say_runs"]
    # Without an example block, or with one the commit does not cite, it is not.
    assert not authorization.prepare_review(*case(with_example=False), [], [])["example_ready"]
    p2, m2 = case()
    m2["example"]["cmd"] = EXAMPLE + " --extra"
    assert not authorization.prepare_review(p2, m2, [], [])["example_ready"]


def test_an_example_that_produced_its_output_is_runs_whatever_the_other_leg_could_do():
    v, _ = decide(gates(example=True), *case())
    assert (v["code"], v["basis"]) == ("runs", "example") and v["blockers"] == []
    assert "its own documented example produced its output" in v["reason"]


def test_an_example_that_stopped_is_fails_and_names_what_the_tool_raised():
    diagnostics = {"example": [{"id": "python_exception", "severity": "error", "title": "The tool raised KeyError"}]}
    v, _ = decide(gates(example=False), *case(), diagnostics=diagnostics)
    assert (v["code"], v["basis"]) == ("fails", "example")
    assert "raised KeyError before producing its output" in v["reason"]
    assert [b["code"] for b in v["blockers"]] == ["run_failed"]


def test_a_runner_ceiling_in_the_example_is_out_of_scope_not_a_failure():
    diagnostics = {"example": [{"id": "requires_gpu", "severity": "error", "title": "Tool requires a GPU"}]}
    v, _ = decide(gates(example=False), *case(), diagnostics=diagnostics)
    assert v["code"] == "out_of_scope" and "requires_gpu" in v["reason"]


def test_no_example_leg_no_example_verdict():
    # The example never ran (no image): what is said is about the install or the procedure.
    v, _ = decide(gates(installs=False), *case())
    assert v.get("basis") != "example"
    # A manifest with no cited example: the gate is ignored even if something set it.
    v, _ = decide(gates(example=True), *case(with_example=False))
    assert v["code"] == "undetermined" and v.get("basis") != "example"


def test_prepare_plans_the_example_without_the_external_leg(tmp_path):
    p, m = case()
    proposal = tmp_path / "proposal.json"
    proposal.write_text(json.dumps(p))
    descriptor = tmp_path / "work" / "proposal"
    descriptor.mkdir(parents=True)
    (descriptor / "manifest.yml").write_text(yaml.safe_dump(m))
    (descriptor / "Dockerfile").write_text("# descriptor only\n")
    out = subprocess.run([sys.executable, str(ROOT / "harness" / "prepare.py"), "test", "--work", str(tmp_path / "work"),
                          "--proposal", str(proposal)], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    kv = dict(ln.split("=", 1) for ln in out.stdout.splitlines() if "=" in ln)
    assert kv["install_ready"] == "1" and kv["example_ready"] == "1"
    assert kv["procedure_ready"] == "0" and kv["external_ready"] == "0"
    # The README's command, untouched, inside the capture wrapper, from the root of the checkout.
    assert kv["example_cmd"].startswith("cd '.' && touch /tmp/.strhub_mark && ( " + EXAMPLE + " ); rc=$?")
    assert not (tmp_path / "work" / "in_external").exists()


def test_the_certificate_and_the_label_say_it_ran_its_example():
    p, m = case()
    v, review = decide(gates(example=True), p, m)
    report = {"verdict": v, "procedure_review": review, "procedure_validation": {"valid": True},
              "instrument": "documented", "level": "installs", "gates": gates(example=True)}
    assert ct.execution_finding_established(report) is True
    assert ct.headline(report) == ("Runs as documented", "green")
    items = ct.conclusion_items_for({"tool_display": "Tool test", "tool_name": "Tool", "gates": report["gates"],
                                     "verdict": v, "execution_finding_established": True})
    assert items[0][0] == "Reproduces its own example" and "produced its output" in items[0][1]
    assert not any("loci" in body or "reference" in body.lower() for _, body in items)
    v, review = decide(gates(example=False), p, m)
    items = ct.conclusion_items_for({"tool_display": "Tool test", "tool_name": "Tool", "gates": gates(example=False),
                                     "verdict": v, "execution_finding_established": True})
    assert items[0][0] == "Does not reproduce its own example"
