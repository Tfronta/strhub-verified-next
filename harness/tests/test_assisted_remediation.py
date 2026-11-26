"""Unit and integration tests for Track 2 (`assisted_remediation.py`), canonical
report/index/PDF fields, and strict Track 1 non-mutation invariants."""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "harness"))

import assisted_remediation as ar  # noqa: E402
import authorization  # noqa: E402
import build_index  # noqa: E402
import certificate_text as ct  # noqa: E402
import detect_recipe as dr  # noqa: E402
import propose_manifest as pm  # noqa: E402
import publish_gate  # noqa: E402
from engine import runner, stages  # noqa: E402


def _eval_snapshot(name: str) -> tuple[dict, dict, dict]:
    snap = ROOT / "harness" / "testdata" / "benchmark" / name
    src = dr.load_snapshot(snap)
    slug = dr.repo_slug(src["tree_resp"]["repo"])
    ref = src["tree_resp"]["ref"]
    proposal = dr.detect(slug, ref, src["tree_resp"], src["readme"], src["readme_name"], extras=src)
    built = pm.build(proposal, f"trial-{name}", submitted_by="third_party", ref_label=src.get("tag", ""))
    proposal["limitations"] = built["limitations"]
    review = authorization.prepare_review(
        proposal,
        built["manifest"],
        built["limitations"],
        (built["manifest"].get("caveats") or {}).get("items") or [],
    )
    return proposal, built["manifest"], review


def test_straglr_positional_bam_triggers_rule5_and_stages_reference_genome():
    proposal, manifest, review = _eval_snapshot("straglr")
    # Track 1 stays strictly unable to substitute the positional BAM argument
    assert review["install_ready"] is True
    assert review["may_say_runs"] is False
    assert review["blocker"] == "input_not_substituted"

    # prepare.py's helper detects that Track 2's rewritten command needs hg38.fa
    ref = ar.needs_reference_genome(proposal, manifest)
    assert ref is not None and ref.get("filename") == "hg38.fa"

    # Track 2 binds positional `sample.mm2.bam` -> `/data/in/input.bam` and reuses Track 1's image
    plan = ar.plan_assisted_run(
        proposal,
        manifest,
        review,
        installs_passed=True,
        installs_attempted=True,
        runs_passed=False,
        io_passed=False,
    )
    assert plan is not None
    assert plan["needs_rebuild"] is False
    assert plan["needs_reference"] is True
    assert "/data/in/input.bam" in plan["unwrapped_run_cmd"]
    assert "/data/ref/hg38.fa" in plan["unwrapped_run_cmd"]
    rule_ids = [a["rule_id"] for a in plan["adjustments"]]
    assert "positional_reads_arg" in rule_ids


def test_longtr_build_failure_triggers_missing_apt_and_submodules():
    proposal, manifest, review = _eval_snapshot("longtr")
    assert review["install_ready"] is True
    build_log = "/bin/sh: 1: autoreconf: not found\nfatal error: zlib.h: No such file or directory\n"
    # 1. LongTR snapshot (without .gitmodules) remediates missing autotools + zlib1g-dev
    plan = ar.plan_assisted_run(
        proposal,
        manifest,
        review,
        installs_passed=False,
        installs_attempted=True,
        runs_passed=False,
        io_passed=False,
        build_log_text=build_log,
    )
    assert plan is not None
    assert plan["needs_rebuild"] is True
    assert {"autoconf", "automake", "libtool", "zlib1g-dev"} <= set(plan["extra_apt"])
    assert "missing_apt_build_tool" in {a["rule_id"] for a in plan["adjustments"]}

    # 2. When a repository tree also carries `.gitmodules` and README omitted `--recursive`,
    #    Rule 2 (`uninitialized_submodules`) triggers automatically alongside Rule 1.
    proposal_with_sub = {**proposal, "tree_paths": [*(proposal.get("tree_paths") or []), ".gitmodules"]}
    plan_sub = ar.plan_assisted_run(
        proposal_with_sub,
        manifest,
        review,
        installs_passed=False,
        installs_attempted=True,
        runs_passed=False,
        io_passed=False,
        build_log_text=build_log,
    )
    assert plan_sub is not None
    assert plan_sub["init_submodules"] is True
    assert {"missing_apt_build_tool", "uninitialized_submodules"} <= {a["rule_id"] for a in plan_sub["adjustments"]}


def test_expansionhunter_cmake_and_dev_headers_remediated_generically():
    proposal, manifest, review = _eval_snapshot("expansionhunter")
    build_log = (
        "bash: line 2: cmake: command not found\n"
        "CMake Error: Could NOT find ZLIB (missing: ZLIB_LIBRARY ZLIB_INCLUDE_DIR)\n"
        "CMake Error: Could NOT find BZip2 (missing: BZIP2_LIBRARIES)\n"
        "fatal error: curl/curl.h: No such file or directory\n"
    )
    plan = ar.plan_assisted_run(
        proposal,
        manifest,
        review,
        installs_passed=False,
        installs_attempted=True,
        runs_passed=False,
        io_passed=False,
        build_log_text=build_log,
    )
    assert plan is not None
    assert {"cmake", "zlib1g-dev", "libbz2-dev", "libcurl4-openssl-dev"} <= set(plan["extra_apt"])
    assert "apt-get install -y --no-install-recommends" in plan["dockerfile"]


def test_python_floor_upgrade_and_refusal_on_unresolved_placeholders():
    # 1. Pure helper upgrades python=3.8 -> python=3.10 when PyPI metadata requires >=3.9
    cmds = ["conda create -n demo python=3.8 -y", "conda activate demo", "pip install ."]
    log = "ERROR: Package 'pyminimap2' requires a different Python: 3.8.20 not in '>=3.9'\nRequires-Python >=3.9\n"
    upgraded, adj = ar._detect_python_floor_upgrade(cmds, log)
    assert adj is not None and adj["rule_id"] == "python_floor_conflict"
    assert upgraded[0] == "conda create -n demo python=3.10 -y"

    # 2. Real NanoRepeat snapshot still has unbound `path/to/...` placeholders in its synopsis,
    #    so plan_assisted_run refuses to guess/force an invented command!
    proposal, manifest, review = _eval_snapshot("nanorepeat")
    assert ar.plan_assisted_run(
        proposal,
        manifest,
        review,
        installs_passed=False,
        installs_attempted=True,
        runs_passed=False,
        io_passed=False,
        build_log_text=log,
    ) is None


def test_fdstools_root_packaging_manifest_and_strspy_manual_routing():
    # FDSTools has setup.py in root when README has no literal install block
    proposal_fds, manifest_fds, review_fds = _eval_snapshot("fdstools")
    if not review_fds["install_ready"]:
        plan_fds = ar.plan_assisted_run(
            proposal_fds,
            manifest_fds,
            review_fds,
            installs_passed=False,
            installs_attempted=False,
            runs_passed=False,
            io_passed=False,
        )
        # If its command also binds to a dataset, standard_manifest_in_root triggers;
        # otherwise it cleanly abstains without forcing.
        if plan_fds is not None:
            assert any(a["rule_id"] == "standard_manifest_in_root" for a in plan_fds["adjustments"])

    # STRspy requires custom internal config files / code edits -> NEVER forced in Track 2 (goes to Manual)
    proposal_spy, manifest_spy, review_spy = _eval_snapshot("strspy")
    plan_spy = ar.plan_assisted_run(
        proposal_spy,
        manifest_spy,
        review_spy,
        installs_passed=False,
        installs_attempted=False,
        runs_passed=False,
        io_passed=False,
    )
    assert plan_spy is None


def test_end_to_end_assisted_report_preserves_authorization_and_renders_pdf(tmp_path, monkeypatch):
    """When Track 1 is `undetermined` (like straglr) and Track 2 passes `runs + io + content`:
      - Root `gates` and `verdict` remain Track 1's (`undetermined`), so `authorization.report_validation`
        and `publish_gate.decide` pass 100% unchanged!
      - `headline(report)` and `index.json` emit `'Runs with adjustments'` (`yellow` / `assisted_runs: True`).
      - `report.py` and `generate_pdf.py` embed the full `assisted_run` adjustments, commands, and output preview.
    """
    proposal, manifest, review = _eval_snapshot("straglr")
    manifest["report"] = {"slug": "trial-straglr-e2e"}

    work = tmp_path / "work"
    prop_dir = work / "proposal"
    prop_dir.mkdir(parents=True)
    mf_path = prop_dir / "manifest.yml"
    df_path = prop_dir / "Dockerfile"
    mf_path.write_text(yaml.safe_dump(manifest, sort_keys=False))
    df_path.write_text("# carrier\n")

    prop_json = tmp_path / "recipe_proposal.json"
    prop_json.write_text(json.dumps(proposal, indent=2))

    # Run prepare.py: verify external_ready=0 (Track 1 untouched) AND reference_ready=1 (for Track 2!)
    prep = subprocess.run(
        [sys.executable, str(ROOT / "harness" / "prepare.py"), "trial-straglr-e2e",
         "--work", str(work), "--proposal", str(prop_json), "--plan-out", str(work / "plan.json")],
        cwd=str(ROOT), capture_output=True, text=True, check=True,
    )
    kv = dict(ln.split("=", 1) for ln in prep.stdout.splitlines() if "=" in ln)
    assert kv["procedure_ready"] == "0"
    assert kv["external_ready"] == "0"
    assert kv["reference_ready"] == "1"
    assert kv["ref_genome_filename"] == "hg38.fa"

    # Stage dummy hg38.fa in work/ref so execute_assisted_run sees it
    ref_dir = work / "ref"
    ref_dir.mkdir(parents=True, exist_ok=True)
    (ref_dir / "hg38.fa").write_text(">chr1\nACGT\n")

    # Symlink datasets and harness into tmp_path so runner.run executes hermetically
    (tmp_path / "datasets").symlink_to(ROOT / "datasets")
    (tmp_path / "harness").symlink_to(ROOT / "harness")

    class AssistedFake:
        def __init__(self):
            self.calls = []

        def run(self, argv, *, log=None, timeout=None, cwd=None, env=None):
            self.calls.append(list(argv))
            if argv[0] == "git" and "clone" in argv:
                dst = pathlib.Path(cwd) / argv[-1]
                dst.mkdir(parents=True, exist_ok=True)
            elif argv[0] == "bash" and argv[1].endswith("run_container.sh"):
                # Assisted container run! Verify `/app:ro` and `/data/in/input.bam`
                joined = " ".join(argv)
                assert ":/app:ro" in joined
                assert "/data/in/input.bam" in argv[-1]
                log_p = pathlib.Path(cwd) / argv[4]
                log_p.parent.mkdir(parents=True, exist_ok=True)
                log_p.write_text("straglr assisted run completed\n")
                out_dir = work / "assisted" / "out_external"
                out_dir.mkdir(parents=True, exist_ok=True)
                (out_dir / "output_prefix.tsv").write_text(
                    "#chrom\tstart\tend\tlocus\trepeat_unit\tcopy_number\n"
                    "chr4\t3074876\t3074933\tHTT\tCAG\t19.0\n"
                )
            elif len(argv) >= 2 and argv[1].endswith("check_io.py") and "assisted" in " ".join(argv):
                j_out = pathlib.Path(argv[argv.index("--json") + 1])
                j_out.write_text(json.dumps({
                    "passed": True,
                    "outputs": [{"path": "*.tsv", "format": "tsv", "resolved": "output_prefix.tsv",
                                 "checks": {"exists": True, "non_empty": True, "confined": True}}],
                }))
            elif len(argv) >= 2 and argv[1].endswith("check_content.py") and "assisted" in " ".join(argv):
                j_out = pathlib.Path(argv[argv.index("--json") + 1])
                j_out.write_text(json.dumps({
                    "passed": True,
                    "outputs": [{"resolved": "output_prefix.tsv", "stats": {
                        "rows": 1, "malformed_rows": 0, "distinct_str_loci": 1,
                        "str_loci": ["HTT"], "total_reads": 25, "max_sequence_depth": 25,
                        "top_loci_by_depth": [["HTT", 25]],
                    }}],
                }))
            if log:
                pathlib.Path(log).parent.mkdir(parents=True, exist_ok=True)
                with open(log, "a") as fh:
                    fh.write(f"$ {' '.join(argv)}\n")
            return 0

        def output(self, argv, cwd=None):
            self.calls.append(list(argv))
            if argv[0] == "git" and "rev-parse" in argv:
                return 0, manifest["source"]["ref"] + "\n"
            return 0, ""

    plan_doc = json.loads((work / "plan.json").read_text())
    # Make manifest & proposal paths relative to tmp_path for runner
    plan_doc["manifest"] = str(mf_path)
    plan_doc["proposal"] = str(prop_json)

    fake = AssistedFake()
    # Skip fidelity.py subprocess check on dummy empty git clone by returning 0 in Fake (already returns 0!)
    rec = runner.run(plan_doc, pathlib.Path("work"), tmp_path, exe=fake, results=tmp_path / "results")
    assert "assisted" in rec
    assert rec["assisted"]["attempted"] is True
    assert rec["assisted"]["passed"] is True
    assert rec["assisted"]["level"] == "content"
    # Notice docker build ran ONLY ONCE (Track 1 built image, Track 2 reused it!)
    docker_builds = [c for c in fake.calls if c[0] == "bash" and c[1].endswith("record_terminal.sh")]
    assert len(docker_builds) == 1

    rec_path = tmp_path / "run_record.json"
    rec_path.write_text(json.dumps(rec, indent=2))

    # Run report.py
    rep_cmd = [
        sys.executable, str(ROOT / "harness" / "report.py"),
        "--manifest", str(mf_path),
        "--engine-record", str(rec_path),
        "--procedure-review", str(work / "procedure_review.json"),
        "--matrix", str(tmp_path / "results" / "matrix.json"),
        "--example", str(tmp_path / "results" / "example.json"),
        "--log-build", str(work / "log_build.txt"),
        "--recipe-proposal", str(prop_json),
        "--ref", manifest["source"]["ref"],
        "--mode", "trial",
    ]
    subprocess.run(rep_cmd, cwd=str(ROOT), check=True, capture_output=True, text=True)

    reports_dir = ROOT / "reports"
    try:
        written = json.loads((reports_dir / "trial-straglr-e2e.json").read_text())
        badge = json.loads((reports_dir / "trial-straglr-e2e.badge.json").read_text())
        md = (reports_dir / "trial-straglr-e2e.summary.md").read_text()
        html = (reports_dir / "trial-straglr-e2e.html").read_text()

        # 1. Track 1 verdict & cryptographic procedure validation remain 100% intact
        assert written["verdict"]["code"] == "undetermined"
        val = authorization.report_validation(written)
        assert val.valid, val.reason
        pub_ok, pub_why = publish_gate.decide(
            written, slug="trial-straglr-e2e", publish_requested=True, index={"tools": []},
        )
        assert pub_ok is True, pub_why

        # 2. Headline, badge, summary, HTML, and index all carry "Runs with adjustments"
        assert ct.headline(written) == ("Runs with adjustments", "yellow")
        assert badge["message"] == "Runs with adjustments" and badge["color"] == "yellow"
        assert written["assisted_run"]["passed"] is True
        assert written["assisted_run"]["output_preview"]["file"] == "output_prefix.tsv"
        assert "HTT" in "\n".join(written["assisted_run"]["output_preview"]["lines"])
        assert "Automated verification with adjustments" in md
        assert "Automated verification with adjustments" in html

        # 3. build_index surfaces assisted_runs & assisted_level
        site_tmp = tmp_path / "site"
        site_tmp.mkdir()
        (site_tmp / "trial-straglr-e2e.json").write_text(json.dumps(written))
        cat = build_index.build_catalogue(site_tmp)
        entry = cat["tools"][0]
        assert entry["label"] == "Runs with adjustments"
        assert entry["assisted_runs"] is True
        assert entry["assisted_level"] == "content"

        # 4. PDF renders cleanly with ReportLab when installed
        pytest.importorskip("reportlab")
        pdf_out = tmp_path / "report.pdf"
        subprocess.run(
            [sys.executable, str(ROOT / "harness" / "generate_pdf.py"),
             "--manifest", str(mf_path), "--datasets", str(ROOT / "datasets" / "index.json"),
             "--publishable", "false", "--out", str(pdf_out)],
            cwd=str(ROOT), check=True, capture_output=True, text=True,
        )
        assert pdf_out.is_file() and pdf_out.read_bytes().startswith(b"%PDF-")
    finally:
        for f in reports_dir.glob("trial-straglr-e2e*"):
            f.unlink(missing_ok=True)
