"""Unit tests for the local manual verification recorder and publisher."""
import json
import pathlib
import subprocess

import pytest

import manual_record as mr
import publish_layout as pl
import publish_manual as pm
from test_publish_layout import NEW, SLUG, _run


def _init_repo(path: pathlib.Path, origin: str = "https://github.com/unique379r/strspy.git") -> str:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)
    subprocess.run(["git", "remote", "add", "origin", origin], cwd=path, check=True)
    (path / "run.sh").write_text("#!/bin/bash\necho 'hello'\n", encoding="utf-8")
    subprocess.run(["git", "add", "run.sh"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "initial"], cwd=path, check=True)
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=path, text=True).strip()


def test_refuses_fork_origin_mismatch(tmp_path):
    checkout = tmp_path / "fork-checkout"
    _init_repo(checkout, origin="https://github.com/Tfronta/strspy.git")
    with pytest.raises(ValueError, match="does not match --repo"):
        mr.verify_checkout(checkout, expected_repo="https://github.com/unique379r/strspy")


def test_refuses_modified_tracked_source_files(tmp_path):
    checkout = tmp_path / "upstream"
    _init_repo(checkout)
    (checkout / "run.sh").write_text("#!/bin/bash\necho 'patched'\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unmodified"):
        mr.verify_checkout(checkout, expected_repo="https://github.com/unique379r/strspy")


def test_allows_explicitly_whitelisted_untracked_config(tmp_path):
    checkout = tmp_path / "upstream"
    sha = _init_repo(checkout)
    (checkout / "config").mkdir()
    (checkout / "config" / "UserToolsConfig.txt").write_text("SAMTOOLS=samtools\n", encoding="utf-8")
    info = mr.verify_checkout(
        checkout,
        expected_repo="https://github.com/unique379r/strspy",
        allow_untracked=["config/UserToolsConfig.txt"],
    )
    assert info["sha"] == sha


def test_sanitizes_home_user_hostname_and_checkout_paths(tmp_path):
    checkout = tmp_path / "upstream"
    checkout.mkdir()
    redactions = mr.build_redactions(checkout, extra_redact=["MacBook-de-Tama", "/Users/tfronta"])
    raw = (
        f"Running in {checkout.resolve()} on MacBook-de-Tama as /Users/tfronta/data/sample.bam"
    )
    clean = mr.sanitize_text(raw, redactions)
    assert "MacBook-de-Tama" not in clean
    assert "/Users/tfronta" not in clean
    assert str(checkout.resolve()) not in clean
    assert "/work" in clean
    assert mr.find_personal_leaks(clean) == []


def test_records_manual_failure_mechanically_with_real_terminal(tmp_path):
    checkout = tmp_path / "upstream"
    sha = _init_repo(checkout)
    notes = tmp_path / "notes.yml"
    notes.write_text(
        "base: 'Ubuntu 22.04 + Conda'\n"
        "dataset_type: 'ont-bam-hg38'\n"
        "without_preparation: 'README used wget Miniconda'\n"
        "failure_summary: 'Wrapper script checks wrong directory and exits 1.'\n"
        "pr_url: 'https://github.com/unique379r/strspy/pull/99'\n"
        "recommendations:\n"
        "  - 'Fix path check in wrapper'\n",
        encoding="utf-8",
    )
    bundle = tmp_path / "bundle"
    report = mr.record_manual_run(
        slug="strspy-ont",
        repo="https://github.com/unique379r/strspy",
        checkout=checkout,
        cmd="echo 'please make sure you are in the same directory of STRspy' && exit 1",
        out_dir=bundle,
        version="v2.0",
        notes_path=notes,
    )
    assert report["instrument"] == "curated"
    assert report["source"]["ref_resolved"] == sha
    assert report["verdict"]["code"] == "fails"
    assert report["level"] == "installs"
    assert report["gates"] == {
        "available": True, "installs": True, "runs": False, "io": False, "content": False
    }
    assert report["preparation"]["pr_url"] == "https://github.com/unique379r/strspy/pull/99"
    term = (bundle / "strspy-ont.terminal-external.txt").read_text(encoding="utf-8")
    assert "please make sure you are in the same directory of STRspy" in term
    assert "[exit 1]" in term
    assert report["certificate"]["summary"]["why"]
    pdf_path = bundle / "strspy-ont.pdf"
    assert pdf_path.is_file() and pdf_path.read_bytes().startswith(b"%PDF")


def test_records_manual_pass_and_validates_tabular_output(tmp_path):
    checkout = tmp_path / "upstream"
    _init_repo(checkout)
    tool_out = tmp_path / "tool-out"
    tool_out.mkdir()
    tsv_script = (
        f"printf 'Locus\\tAllele\\tReads\\n"
        f"CSF1PO\\t10\\t42\\n"
        f"TH01\\t7\\t55\\n"
        f"TPOX\\t8\\t61\\n"
        f"FGA\\t22\\t38\\n"
        f"vWA\\t16\\t74\\n"
        f"D3S1358\\t15\\t63\\n' > '{tool_out}/summary.tsv'"
    )
    bundle = tmp_path / "bundle"
    report = mr.record_manual_run(
        slug="demo-tool",
        repo="https://github.com/unique379r/strspy",
        checkout=checkout,
        cmd=tsv_script,
        out_dir=bundle,
        output_dir=tool_out,
        output_glob="**/*.tsv",
    )
    assert report["verdict"]["code"] == "runs"
    assert report["level"] == "content"
    assert report["gates"] == {
        "available": True, "installs": True, "runs": True, "io": True, "content": True
    }
    assert report["content_detail"]["outputs"][0]["stats"]["distinct_str_loci"] == 6


def test_publish_manual_places_curated_without_overwriting_documented_alias(tmp_path):
    site = tmp_path / "site"
    site.mkdir()
    pl.place(site, _run(tmp_path, NEW, "2026-02-01T00:00:00Z", "2026-09-01T00:00:00+00:00"), SLUG)

    bundle = tmp_path / "bundle"
    bundle.mkdir()
    curated_report = {
        "schema": "strhub-verified/1",
        "instrument": "curated",
        "generated": "2026-11-23T12:00:00+00:00",
        "tool": {"name": "HipSTR", "version": "v0.7"},
        "source": {
            "repo": "https://github.com/tfwillems/HipSTR",
            "ref": NEW,
            "ref_resolved": NEW,
            "committed": "2026-02-01T00:00:00Z",
        },
        "gates": {"available": True, "installs": True, "runs": False, "io": False, "content": False},
        "level": "installs",
        "verdict": {"code": "fails", "title": "Fails", "reason": "Upstream script failed."},
        "terminals": {"external": f"{SLUG}.terminal-external.txt"},
    }
    (bundle / f"{SLUG}.json").write_text(json.dumps(curated_report), encoding="utf-8")
    (bundle / f"{SLUG}.terminal-external.txt").write_text("$ tool\nerror\n[exit 1]\n", encoding="utf-8")

    done = pm.place_manual(site, bundle, SLUG)
    assert done["folder"] == f"{SLUG}/{NEW}-curated"
    assert (site / SLUG / f"{NEW}-curated" / f"{SLUG}.json").exists()

    # Root alias remains strictly documented.
    root = json.loads((site / f"{SLUG}.json").read_text(encoding="utf-8"))
    assert root["instrument"] == "documented"

    cat = json.loads((site / "index.json").read_text(encoding="utf-8"))
    (entry,) = cat["tools"]
    assert entry["instrument"] == "documented"
    assert len(entry["versions"]) == 2
    assert any(v["instrument"] == "curated" and v["verdict"] == "fails" for v in entry["versions"])


def test_wrap_pre_expands_tabs_wraps_long_lines_and_preserves_tail():
    raw = "\t\tbanner\tline\n" + ("A" * 130) + "\n\n\n\n" + "\n".join(f"line {i}" for i in range(80)) + "\n[exit 1]\n"
    out = mr._wrap_pre(raw, width=90, max_lines=20)
    assert "\t" not in out
    assert all(len(line) <= 90 for line in out.splitlines())
    assert "[exit 1]" in out
    assert "omitted" in out


def test_inline_code_renders_backticks_as_courier_and_escapes_html():
    rendered = mr._inline_code("Fix `[[ -f \"src/a.sh\" ]]` & `python>=3.9`")
    assert "`" not in rendered
    assert '<font name="Courier" size="8.5">[[ -f &quot;src/a.sh&quot; ]]</font>' in rendered
    assert "&amp;" in rendered


def test_records_optional_i18n_editorial_translations(tmp_path):
    checkout = tmp_path / "upstream"
    _init_repo(checkout)
    notes = tmp_path / "notes.yml"
    notes.write_text(
        "summary: 'Ran cleanly.'\n"
        "i18n:\n"
        "  es:\n"
        "    plain_summary: 'Corrió sin cambios.'\n"
        "    summary: 'El código original corrió sin errores.'\n"
        "    recommendations:\n"
        "      - 'Agregar bloque `make` en el README.'\n",
        encoding="utf-8",
    )
    bundle = tmp_path / "bundle"
    report = mr.record_manual_run(
        slug="demo-i18n",
        repo="https://github.com/unique379r/strspy",
        checkout=checkout,
        cmd="echo ok",
        out_dir=bundle,
        notes_path=notes,
    )
    assert report["i18n"]["es"]["plain_why"] == "Corrió sin cambios."
    assert report["i18n"]["es"]["reason"] == "El código original corrió sin errores."
    assert report["i18n"]["es"]["recommendations"] == ["Agregar bloque `make` en el README."]


def test_genomic_coordinate_tsv_passes_plausible_output_by_coordinates(tmp_path):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    (out_dir / "sample.locus.tsv").write_text(
        "contig\tstart\tend\tmotif\tnum_anc_irrs\tnorm_num_anc_irrs\thet_str_size\n"
        "chr16\t17470284\t17470669\tCCG\t5\t15684.29\t51633\n",
        encoding="utf-8",
    )
    panel = tmp_path / "loci.bed"
    panel.write_text("chr16\t17469908\t17471922\tXYLT1\t52\n", encoding="utf-8")
    io_ok, content_ok, io_detail, content_detail = mr._validate_outputs(
        out_dir, "*.locus.tsv", regions_file=panel
    )
    assert io_ok is True
    assert content_ok is True
    stats = content_detail["outputs"][0]["stats"]
    assert stats["genomic_str_table"] is True
    assert stats["str_loci"] == ["XYLT1"]
    assert stats["regions_hit"] == 1
