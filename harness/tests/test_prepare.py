"""Preparation tests for the descriptor a run derives from the repository."""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
PREPARE = ROOT / "harness" / "prepare.py"


def _run(args, env=None):
    out = subprocess.run([sys.executable, str(PREPARE), *args], capture_output=True, text=True, env=env)
    return out.returncode, dict(ln.split("=", 1) for ln in out.stdout.splitlines() if "=" in ln), out.stderr


def _trial(work, manifest, dockerfile):
    proposal = work / "proposal"
    proposal.mkdir(parents=True, exist_ok=True)
    (proposal / "manifest.yml").write_text(manifest)
    (proposal / "Dockerfile").write_text(dockerfile)
    return ["--work", str(work)]


def test_outputs_are_single_line(tmp_path):
    src = ROOT / "harness" / "testdata" / "fixtures" / "legacy_tools" / "hipstr"
    args = _trial(tmp_path, src.joinpath("manifest.yml").read_text(), src.joinpath("Dockerfile").read_text())
    rc, kv, err = _run(["hipstr", *args, "--plan-out", str(tmp_path / "plan.json")])
    assert rc == 0, err
    assert kv["mode"] == "trial"
    assert all("\n" not in v and "\r" not in v for v in kv.values())
    plan = json.loads((tmp_path / "plan.json").read_text())
    assert plan["tool"] == "hipstr" and plan["cmd"] == kv["cmd"]
    # Nothing STRhub invents is planned: no --help probe, no leg on a fixture of its own.
    assert "starts_cmd" not in plan and "own_ready" not in plan


def test_dispatched_recipe_argument_is_retired(tmp_path):
    rc, _, err = _run(["example", "--work", str(tmp_path), "--recipe-b64", "payload"])
    assert rc != 0 and "unrecognized arguments" in err
    assert not (tmp_path / "proposal").exists()


def test_the_tools_own_command_comes_back_out_of_the_wrapper():
    """The report names what the gates ran. The wrapper around a README command
    is STRhub's plumbing — marking the time, copying files — and a reader shown
    the whole line cannot tell which part is the tool's."""
    import prepare

    cmd = "./HipSTR --bams /data/in/input.bam --fasta /data/ref/hg38.fa --str-vcf str_calls.vcf.gz"
    wrapped = prepare.example_wrapper(cmd, "/opt/tool")
    assert prepare.unwrap_example(wrapped) == (cmd, "/opt/tool")
    # A committed manifest's command is not wrapped and comes back as it is.
    assert prepare.unwrap_example("  GangSTR --bam in.bam   --out out ") == ("  GangSTR --bam in.bam   --out out ", None)


def test_the_ont_fastq_is_handed_over_uncompressed(tmp_path):
    # Committed gzipped to keep the repository small; staged as plain FASTQ,
    # which every reader takes, under the name the run command uses.
    import input_provenance
    ds = input_provenance.stage(ROOT, tmp_path, "ont-fastq")
    assert "HG00113" in ds["name"]
    fq = tmp_path / "in_external" / "input.fastq"
    with fq.open() as f:
        head = [next(f) for _ in range(4)]
    assert head[0].startswith("@") and head[2].startswith("+") and len(head[1]) == len(head[3])
    assert sum(1 for _ in fq.open()) == 4 * 864


def test_shipped_example_cannot_bypass_absent_installation_evidence(tmp_path):
    """When the repository ships its own example (example.cmd) and states how to
    install, a STRhub reference-sample limitation (such as loci_outside_panel)
    must only disable the external leg, never the repository's own example leg."""
    src = ROOT / "harness" / "testdata" / "fixtures" / "legacy_tools" / "strsearch"
    manifest = src.joinpath("manifest.yml").read_text()
    manifest += "\nexample:\n  cmd: python3 STRsearch.py -i example/test_data/ -c example/STR.configuration.txt -o out/\n  cwd: /opt/tool\n"
    args = _trial(tmp_path, manifest, src.joinpath("Dockerfile").read_text())
    proposal = tmp_path / "proposal.json"
    proposal.write_text(json.dumps({
        "procedure": {"may_say_runs": False, "blocker": "loci_outside_panel"}
    }))
    rc, kv, err = _run(["strsearch", *args, "--proposal", str(proposal)])
    assert rc == 0, err
    assert kv["external_ready"] == "0"
    assert kv["install_ready"] == "0"
    assert kv["example_ready"] == "0"

    # When no install procedure exists at all, nothing builds so example_ready is 0.
    proposal.write_text(json.dumps({
        "procedure": {"may_say_runs": False, "blocker": "no_install_procedure"}
    }))
    rc2, kv2, err2 = _run(["strsearch", *args, "--proposal", str(proposal)])
    assert rc2 == 0, err2
    assert kv2["install_ready"] == "0"
    assert kv2["example_ready"] == "0"


def test_a_run_keeps_only_its_selected_dataset(tmp_path):
    """Without a reviewed procedure no input is staged at all, and no
    argument exists that would swap the dataset after the fact."""
    src = ROOT / "harness" / "testdata" / "fixtures" / "legacy_tools" / "hipstr"
    manifest = src.joinpath("manifest.yml").read_text()
    args = _trial(tmp_path, manifest, src.joinpath("Dockerfile").read_text())
    rc, kv, err = _run(["hipstr", *args])
    assert rc == 0, err
    assert kv["input_type"] == "illumina-bam-hg38"
    assert kv["external_ready"] == "0"
    assert not (tmp_path / "in_external").exists()

    # Old callers must fail without modifying the selected procedure.
    mf_path = tmp_path / "proposal" / "manifest.yml"
    before = mf_path.read_bytes()
    rc_prom, _, err_prom = _run(["hipstr", *args, "--dataset", "illumina-bam-hg38-y"])
    assert rc_prom != 0
    assert "unrecognized arguments" in err_prom
    assert mf_path.read_bytes() == before

