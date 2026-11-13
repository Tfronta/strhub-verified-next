"""The reference genome the documentation names is STRhub's to supply.

A README says `--fasta hg38.fa`; no repository ships a 3 GB genome. When the
registered dataset is aligned to one, the token that names it becomes that
genome's read-only mount, the workflow downloads it, and the engine mounts it
at /data/ref. Nothing else is supplied this way: no regions, no catalog."""
import json
import pathlib
import subprocess
import sys

import pytest
import yaml

import authorization
import fidelity
import input_provenance
import prepare
import propose_manifest as pm
from engine import stages
from engine.executor import Executor
from engine.record import StageResult

ROOT = pathlib.Path(__file__).resolve().parents[2]
MOUNT = "/data/ref/hg38.fa"
CITED = "tool --reads x.bam --fasta genome.fa --output out.vcf"
DOCKERFILE = 'FROM scratch\nENTRYPOINT ["/bin/bash", "-lc"]\n'


def case(cited=CITED):
    doc = f"# Tool\n```sh\ndocker build -t upstream .\n{cited}\n```\n"
    source = {"repo": "https://github.com/example/tool", "ref": "a" * 40}
    proposal = {**source, "build": {"method": "dockerfile", "file": "Dockerfile"},
                "commands": [{"cmd": cited, "file": "README.md", "line": 4, "origin": "readme"}],
                "source_documents": [{"file": "README.md", "origin": "readme", "text": doc}],
                "upstream_files": {"Dockerfile": DOCKERFILE}, "tree_paths": ["Dockerfile", "README.md"]}
    manifest = {"tool": {"name": "Tool", "version": "test"}, "source": source,
                "environment": {"source": "repository", "from_repo": "Dockerfile", "dockerfile": "Dockerfile"},
                "inputs": {"type": "illumina-bam-hg38"},
                "run": {"cmd": prepare.example_wrapper(fidelity.rewrite(cited, "illumina-bam-hg38")["command"], ".")},
                "outputs": [{"path": "out.vcf", "format": "vcf", "min_records": 1}]}
    return proposal, manifest


@pytest.mark.parametrize("cited,expected", [
    ("tool --reads x.bam --fasta genome.fa --output out.vcf", f"tool --reads /data/in/input.bam --fasta {MOUNT} --output out.vcf"),
    ("tool --reads x.bam --ref 'ref/GRCh38.fasta' --output out.vcf", f"tool --reads /data/in/input.bam --ref '{MOUNT}' --output out.vcf"),
    ("tool --reads x.bam --reference <reference.fa> --output out.vcf", f"tool --reads /data/in/input.bam --reference {MOUNT} --output out.vcf"),
    # Positional, when the file's own name says which genome it is.
    ("tool --reads x.bam hg38.fa out", f"tool --reads /data/in/input.bam {MOUNT} out"),
])
def test_the_reference_the_command_names_becomes_the_registered_mount(cited, expected):
    r = fidelity.rewrite(cited, "illumina-bam-hg38")
    assert r["command"] == expected and not r["limitations"]
    (sub,) = [s for s in r["substitutions"] if s["role"] == "reference_path"]
    assert sub["basis"] == "registered reference genome mount"


@pytest.mark.parametrize("cited", [
    "tool --reads x.bam --fasta hg19.fa --output out.vcf",          # another assembly
    "tool --reads x.bam --fasta hg38.fa.gz --output out.vcf",       # a form STRhub does not mount
    "tool --reads x.bam --genome hg38.2bit --output out.vcf",
    "tool --reads x.bam --fasta /data/ref/hg38.fa --output out.vcf",  # a README cannot name our mount itself
])
def test_a_reference_strhub_cannot_supply_is_a_limitation_and_nothing_is_substituted(cited):
    r = fidelity.rewrite(cited, "illumina-bam-hg38")
    assert r["limitations"]
    assert not [s for s in r["substitutions"] if s["role"] == "reference_path"]


def test_nothing_but_the_reference_is_supplied_this_way():
    r = fidelity.rewrite("tool --reads x.bam --fasta genome.fa --regions panel.bed --catalog cat.json", "illumina-bam-hg38")
    assert "--regions panel.bed --catalog cat.json" in r["command"]
    assert [s["role"] for s in r["substitutions"]] == ["read_path", "reference_path"]
    # A dataset aligned to no genome has none to give.
    r = fidelity.rewrite("tool --fastq reads.fastq --ref genome.fa", "illumina-str-fastq")
    assert "genome.fa" in r["command"] and any("none is registered" in l for l in r["limitations"])
    # The repository's own example keeps its own files.
    assert fidelity.rewrite("tool --reads x.bam --fasta test/ref.fa", None)["command"] == "tool --reads x.bam --fasta test/ref.fa"


def test_a_missing_reference_genome_is_never_a_file_to_ask_the_author_for():
    caveats = []
    for cmd in ("tool --bam /data/in/input.bam --fasta genome.fa --regions str_regions.bed",
                "tool --bam /data/in/input.bam --ref hg38.fa.gz --regions str_regions.bed",
                "tool input=/data/in/input.bam ref=genome.fa --regions str_regions.bed"):
        lims = pm.check_documented_files(cmd, {"tree_paths": []}, "illumina-bam-hg38", caveats)
        assert lims == ["documented_file_missing"]
    assert caveats and all("str_regions.bed" in c for c in caveats)


def test_the_review_admits_the_command_and_prepare_plans_the_reference(tmp_path):
    p, m = case()
    review = authorization.prepare_review(p, m, [], [])
    assert review["may_say_runs"] and review["install_ready"], review.get("reason")
    proposal = tmp_path / "proposal.json"
    proposal.write_text(json.dumps(p))
    descriptor = tmp_path / "work" / "proposal"
    descriptor.mkdir(parents=True)
    (descriptor / "manifest.yml").write_text(yaml.safe_dump(m))
    (descriptor / "Dockerfile").write_text("# descriptor only\n")
    out = subprocess.run([sys.executable, str(ROOT / "harness" / "prepare.py"), "test", "--work", str(tmp_path / "work"),
                          "--proposal", str(proposal), "--plan-out", str(tmp_path / "plan.json")],
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    plan = json.loads((tmp_path / "plan.json").read_text())
    assert plan["external_ready"] == "1" and plan["reference_ready"] == "1"
    assert plan["ref_genome_filename"] == "hg38.fa"
    assert plan["ref_genome_url"].endswith("/hg38.fa.gz") and plan["ref_genome_md5_url"].endswith("/md5sum.txt")
    # Nothing is downloaded or staged by prepare: only the dataset is on disk.
    assert not (tmp_path / "work" / "ref").exists()


def test_a_command_that_names_no_reference_gets_none(tmp_path):
    p, m = case("tool --reads x.bam --output out.vcf")
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
    assert kv["external_ready"] == "1" and kv["reference_ready"] == "0" and kv["ref_genome_url"] == ""


def _staged(tmp_path):
    p, m = case()
    review = authorization.prepare_review(p, m, [], [])
    work = tmp_path / "work"
    input_provenance.stage(ROOT, work, m["inputs"]["type"])
    return m, review, work


def test_the_receipt_records_the_reference_that_is_mounted(tmp_path):
    m, review, work = _staged(tmp_path)
    (work / "ref").mkdir()
    (work / "ref" / "hg38.fa").write_text(">chr1\nACGT\n")
    (work / "ref" / "hg38.fa.fai").write_text("chr1\t4\t6\t4\t5\n")
    receipt = input_provenance.verify(ROOT, work, m, review, m["run"]["cmd"])
    ref = receipt["reference"]
    assert ref["mount_path"] == MOUNT and ref["index_mount_path"] == MOUNT + ".fai"
    assert ref["size_bytes"] == 11 and len(ref["sha256"]) == 64
    assert ref["source_url"].endswith("/hg38.fa.gz") and ref["assembly"] == "GRCh38 / hg38"
    # The dataset mount is still exactly the dataset.
    assert [f["mount_path"] for f in receipt["files"]] == ["/data/in/input.bam", "/data/in/input.bam.bai"]


@pytest.mark.parametrize("missing", ["everything", "index", "empty"])
def test_a_reference_that_was_not_staged_stops_the_leg_before_launch(tmp_path, missing):
    m, review, work = _staged(tmp_path)
    if missing != "everything":
        (work / "ref").mkdir()
        (work / "ref" / "hg38.fa").write_text("" if missing == "empty" else ">chr1\nACGT\n")
        if missing == "empty":
            (work / "ref" / "hg38.fa.fai").write_text("")
    with pytest.raises(ValueError, match="reference genome"):
        input_provenance.verify(ROOT, work, m, review, m["run"]["cmd"])


def test_the_engine_mounts_the_reference_read_only_only_when_the_plan_says_so(tmp_path):
    class Recorder(Executor):
        def __init__(self):
            self.calls = []

        def run(self, argv, log=None, timeout=None, cwd=None):
            self.calls.append(list(argv))
            return 0

        def output(self, argv, cwd=None):
            self.calls.append(list(argv))
            return 0, ""

    passed = StageResult(stage="installs", status="passed", exit_code=0)
    for ready, mounted in (("1", True), ("0", False)):
        exe = Recorder()
        plan = {"cmd": "tool", "timeout": "1", "step_timeout": "4", "external_ready": "1",
                "manifest": "m.yml", "reference_ready": ready}
        ctx = stages.Ctx(plan=plan, work=pathlib.Path("work"), root=tmp_path, exe=exe)
        stages.runs_external(ctx, passed)
        run = " ".join(next(c for c in exe.calls if c[1].endswith("run_container.sh")))
        assert (f"{tmp_path / 'work' / 'ref'}:/data/ref:ro" in run) is mounted
        assert f"{tmp_path / 'work' / 'in_external'}:/data/in:ro" in run
    # The repository's own example never gets it.
    exe = Recorder()
    ctx = stages.Ctx(plan={"example_ready": "1", "example_cmd": "x", "timeout": "1", "step_timeout": "4",
                           "reference_ready": "1"}, work=pathlib.Path("work"), root=tmp_path, exe=exe)
    stages.runs_example(ctx, passed)
    assert "/data/ref" not in " ".join(exe.calls[0])


def test_the_report_says_strhub_supplied_the_reference(tmp_path, monkeypatch, capsys):
    import report as report_module
    m, review, work = _staged(tmp_path)
    (work / "ref").mkdir()
    (work / "ref" / "hg38.fa").write_text(">chr1\nACGT\n")
    (work / "ref" / "hg38.fa.fai").write_text("chr1\t4\t6\t4\t5\n")
    receipt = input_provenance.verify(ROOT, work, m, review, m["run"]["cmd"])
    (tmp_path / "mounted.json").write_text(json.dumps(receipt))
    (tmp_path / "review.json").write_text(json.dumps(review))
    (tmp_path / "manifest.yml").write_text(yaml.safe_dump(m))
    (tmp_path / "io.json").write_text('{"passed": true}')
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(report_module, "ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["report.py", "--manifest", "manifest.yml", "--available", "pass",
        "--installs", "pass", "--runs", "pass", "--io", "io.json", "--procedure-review", "review.json",
        "--mounted-inputs", "mounted.json", "--mode", "trial"])
    assert report_module.main() == 0
    result = json.loads(capsys.readouterr().out)
    assert result["verdict"]["code"] == "runs"
    assert result["mounted_inputs"]["reference"]["mount_path"] == MOUNT
    assert any("reference genome" in n and MOUNT in n for n in result["needed_beyond_repo"])
