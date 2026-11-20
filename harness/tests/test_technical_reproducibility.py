"""Technical reproducibility tests for scoped Verified priorities:

1. Assembly detection in secondary non-wiki docs + common aliases (b37, hs37d5, GRCh37/38),
   blocking incompatibility while permitting internally coherent unstated hg38 trials.
2. Conflicting region schemas fail cleanly as `FAILED_AMBIGUOUS_CLI` instead of silent
   first-match-wins, while single compatible schemas proceed.
3. Multi-platform tools do not block: `supported_platforms` is preserved, a compatible
   STRhub dataset platform is chosen deterministically, and the choice is marked as a
   harness decision rather than a single-platform upstream claim.
4. Report provenance separates upstream facts, mechanically derived bindings, and
   STRhub harness choices (`_summary_md` and `_summary_html`).
"""
from __future__ import annotations

import copy
import pathlib

import detect_recipe as dr
import procedure
import propose_manifest as pm
import report
import verdict

REPOS = pathlib.Path(__file__).resolve().parents[1] / "testdata" / "repos"


def _hipstr_proposal() -> dict:
    tree, readme, repo = dr.load_offline(REPOS / "hipstr")
    return dr.detect(dr.repo_slug(repo), tree["ref"], tree, readme, "README.md")


def _synthetic_repo(readme: str, docs: list[dict] | None = None,
                    cmd_readme_extra: str = "") -> dict:
    readme_text = readme + cmd_readme_extra
    tree = {
        "ref": "a" * 40,
        "tree": [
            {"path": "Makefile", "type": "blob"},
            {"path": "README.md", "type": "blob"},
            *[{"path": d["path"], "type": "blob"} for d in (docs or []) if d.get("origin") != "wiki"],
        ],
    }
    extras = {
        "files": {"Makefile": "all:\n\techo ok\n"},
        "docs": docs or [],
    }
    return dr.detect("example/tool", tree["ref"], tree, readme_text, "README.md", extras=extras)


def test_assembly_aliases_and_secondary_non_wiki_docs_block_hg19_only():
    readme = (
        "# SampleTool\n\nDesigned for Illumina sequencing data.\n\n"
        "## Install\n\n```\nmake\n```\n\n"
        "## Run\n\n```\n./tool --bam reads.bam --fasta ref.fa --out calls.vcf\n```\n"
    )
    # 1. b37 / hs37d5 in a linked repository doc -> blocks hg38 run.
    prop_b37 = _synthetic_repo(
        readme,
        docs=[{
            "path": "docs/reference.md",
            "origin": "doc",
            "text": "Align reads to b37 (hs37d5 / GRCh37) before running.\n",
        }],
    )
    asm = prop_b37["input_type"]["assembly"]
    assert asm["declared"] == "hg19_only"
    assert asm["incompatible_with_hg38"] is True
    assert asm["hg19_evidence_source"] == "docs/reference.md:L1"

    built = pm.build(prop_b37, "tool-b37")
    assert built["procedure"]["may_say_runs"] is False
    assert any(a["code"] == "input_assembly_mismatch" for a in built["procedure"]["amendments"])
    assert built["procedure"]["status_code"] == "UNVERIFIED_INSUFFICIENT_DOCS"

    # 2. Wiki mentions of hg19 are NOT pinned source evidence and do not poison assembly detection.
    prop_wiki = _synthetic_repo(
        readme,
        docs=[{"path": "wiki/OldGuide", "origin": "wiki", "text": "Use hg19 / b37.\n"}],
    )
    assert prop_wiki["input_type"]["assembly"]["declared"] is None
    assert prop_wiki["input_type"]["assembly"]["incompatible_with_hg38"] is False


def test_assembly_explicit_hg38_in_docs_or_explicit_against_hg38():
    readme = (
        "# SampleTool\n\nDesigned for Illumina sequencing data.\n\n"
        "## Install\n\n```\nmake\n```\n\n"
        "## Run\n\n```\n./tool --bam reads.bam --fasta ref.fa --out calls.vcf\n```\n"
    )
    prop_grch38 = _synthetic_repo(
        readme,
        docs=[{"path": "docs/setup.md", "origin": "doc", "text": "Reference genome must be GRCh38.\n"}],
    )
    assert prop_grch38["input_type"]["assembly"]["declared"] == "hg38"
    assert prop_grch38["input_type"]["signals"]["hg38"] >= 1
    built_ok = pm.build(prop_grch38, "tool-grch38")
    assert built_ok["procedure"]["may_say_runs"] is True
    assert built_ok["procedure"]["provenance"]["harness_choices"]["assembly"]["basis"] == "upstream_stated"

    prop_against = _synthetic_repo(
        readme,
        docs=[{"path": "docs/faq.md", "origin": "doc", "text": "hg38 is not supported yet.\n"}],
    )
    assert prop_against["input_type"]["assembly"]["incompatible_with_hg38"] is True
    built_bad = pm.build(prop_against, "tool-no-hg38")
    assert built_bad["procedure"]["may_say_runs"] is False
    assert any(a["code"] == "input_assembly_mismatch" for a in built_bad["procedure"]["amendments"])


def test_conflicting_region_schemas_block_as_ambiguous_cli():
    readme = (
        "# AmbiguousTool\n\nDesigned for Illumina sequencing data.\n\n"
        "## Install\n\n```\nmake\n```\n\n"
        "## Usage\n\n```\n./tool --bam reads.bam --regions loci.bed --out calls.vcf\n```\n\n"
        "### BED Format\n\n"
        "CHROM | START | END | MOTIF_LEN | NUM_COPIES | NAME\n"
        "chr1 | 100 | 200 | 4 | 10 | L1\n"
    )
    # Second conflicting schema in secondary doc.
    docs = [{
        "path": "docs/alt_format.md",
        "origin": "doc",
        "text": "CHROM | START | END | MOTIF_LEN | MOTIF\nchr1 | 100 | 200 | 4 | AGAT\n",
    }]
    prop_conflict = _synthetic_repo(readme, docs=docs)
    assert prop_conflict["regions"]["ambiguous"] is True
    assert prop_conflict["regions"]["format"] is None
    assert [c["format"] for c in prop_conflict["regions"]["candidates"]] == ["hipstr", "gangstr"]

    built = pm.build(prop_conflict, "ambig-regions")
    assert built["procedure"]["may_say_runs"] is False
    assert built["procedure"]["blocker"] == "ambiguous_regions_schema"
    assert built["procedure"]["status_code"] == "FAILED_AMBIGUOUS_CLI"

    # Repeating the exact same schema across README and docs is NOT a conflict.
    same_docs = [{
        "path": "docs/format.md",
        "origin": "doc",
        "text": "CHROM | START | END | MOTIF_LEN | NUM_COPIES | NAME\n",
    }]
    prop_same = _synthetic_repo(readme, docs=same_docs)
    assert prop_same["regions"]["ambiguous"] is False
    assert prop_same["regions"]["format"] == "hipstr"
    assert pm.build(prop_same, "same-regions")["procedure"]["may_say_runs"] is True

    # If the command itself does NOT use regions, conflicting format tables elsewhere do not block execution.
    no_reg_cmd_readme = readme.replace("--regions loci.bed ", "")
    prop_no_reg_cmd = _synthetic_repo(no_reg_cmd_readme, docs=docs)
    assert prop_no_reg_cmd["regions"]["ambiguous"] is True
    assert pm.build(prop_no_reg_cmd, "no-reg-cmd")["procedure"]["may_say_runs"] is True


def test_multi_platform_tool_does_not_block_and_records_harness_choice():
    readme = (
        "# MultiPlat\n\nSupports Illumina and Oxford Nanopore sequencing data.\n\n"
        "## Install\n\n```\nmake\n```\n\n"
        "## Run\n\n```\n./tool --bam reads.bam --fasta genome.fa --out calls.vcf\n```\n"
    )
    prop = _synthetic_repo(readme)
    it = prop["input_type"]
    assert it["platform_how"] == "multi_stated"
    assert {p["platform"] for p in it["supported_platforms"]} == {"illumina", "ont"}
    assert it["platform"] == "ont"
    assert it["best"] == "ont-bam-hg38"

    built = pm.build(prop, "multi-plat")
    review = built["procedure"]
    assert review["may_say_runs"] is True
    assert review["status_code"] == "VERIFIED_PROCEDURE_READY"
    assert review["inferences"]["platform"]["selection_basis"] == "harness_choice_from_supported"
    assert set(review["inferences"]["platform"]["supported_platforms"]) == {"illumina", "ont"}
    prov = review["provenance"]
    assert {p["platform"] for p in prov["from_upstream"]["supported_platforms"]} == {"illumina", "ont"}
    assert prov["harness_choices"]["platform"]["basis"] == "harness_choice_from_supported"
    assert prov["harness_choices"]["platform"]["selected"] == "ont"

    # When PacBio HiFi and Illumina are both supported on FASTQ, STRhub lacks PacBio FASTQ
    # and must deterministically choose Illumina (`illumina-str-fastq`) rather than failing.
    readme_fq = (
        "# MultiFastq\n\nSupports PacBio HiFi and Illumina sequencing data.\n\n"
        "The input is a FASTQ file of reads.\n\n"
        "## Install\n\n```\nmake\n```\n\n"
        "## Run\n\n```\n./tool --fastq reads.fastq --out calls.vcf\n```\n"
    )
    prop_fq = _synthetic_repo(readme_fq)
    assert prop_fq["input_type"]["platform"] == "illumina"
    assert prop_fq["input_type"]["best"] == "illumina-str-fastq"
    assert prop_fq["input_type"]["platform_how"] == "multi_stated"
    assert pm.build(prop_fq, "multi-fastq")["procedure"]["may_say_runs"] is True


def test_bam_without_any_platform_still_blocks():
    readme = (
        "# AmbigBam\n\nThe input is a BAM file of sequencing reads.\n\n"
        "## Install\n\n```\nmake\n```\n\n"
        "## Run\n\n```\n./tool --bam reads.bam --out calls.vcf\n```\n"
    )
    prop = _synthetic_repo(readme)
    assert prop["input_type"]["platform_how"] == "counted"
    built = pm.build(prop, "bam-no-platform")
    assert built["procedure"]["may_say_runs"] is False
    assert any(a["code"] == "input_platform_unproven" for a in built["procedure"]["amendments"])
    assert built["procedure"]["status_code"] == "UNVERIFIED_INSUFFICIENT_DOCS"


def test_hipstr_provenance_separates_upstream_derived_and_harness_choices():
    prop = _hipstr_proposal()
    built = pm.build(prop, "hipstr-trial")
    prov = built["procedure"]["provenance"]

    # Upstream facts keep exact meanings and lines (README:L69 says BAM, not illumina-bam-hg38).
    up = prov["from_upstream"]
    assert up["input_kind"] == {"value": "bam", "evidence_source": "README.md:L69"}
    assert up["supported_platforms"] == [{"platform": "illumina", "evidence_source": "README.md:L36"}]
    assert up["assembly"] == {"declared": None, "evidence_source": None}
    assert up["regions_schema"] == {"format": "hipstr", "evidence_source": "README.md:L308-L322"}

    # Mechanical bindings & trial adaptation.
    der = prov["derived"]
    assert len(der["command_rewrites"]) == 3
    assert der["single_sample_adaptation"]["applied"] is True
    assert der["single_sample_adaptation"]["evidence_source"] == "README.md:L75"

    # STRhub trial choices.
    hc = prov["harness_choices"]
    assert hc["dataset"]["selected"] == "illumina-bam-hg38"
    assert hc["assembly"]["selected"] == "hg38"
    assert hc["assembly"]["basis"] == "harness_choice_unstated"
    assert hc["regions_layout"] == "hipstr"

    # Summary renderers show all three provenance sections clearly.
    fake_report = {
        "tool": built["manifest"]["tool"],
        "level": "content",
        "gates": dict.fromkeys(("available", "installs", "runs", "io", "content"), True),
        "source": {**built["manifest"]["source"], "ref_resolved": built["manifest"]["source"]["ref"]},
        "environment": built["manifest"]["environment"],
        "generated": "2026-11-15T00:00:00Z",
        "scope": "Test scope.",
        "verdict": verdict.decide(dict.fromkeys(("available", "installs", "runs", "io", "content"), True),
                                  procedure=built["procedure"], manifest=built["manifest"]),
        "provenance": copy.deepcopy(prov),
    }
    md = report._summary_md(fake_report, "hipstr-illumina")
    html = report._summary_html(fake_report, "hipstr-illumina")
    for heading in (
        "From upstream documentation",
        "Mechanically derived bindings",
        "Selected by STRhub for this trial",
    ):
        assert heading in md
        assert heading in html


def test_minimal_toolchain_for_make_and_cmake_only_and_declared_in_report(tmp_path, monkeypatch, capsys):
    import json
    import sys
    import yaml

    readme_make = (
        "# MakeOnly\n\nDesigned for Illumina sequencing data.\n\n"
        "## Install\n\n```\nmake\n```\n\n"
        "## Run\n\n```\n./tool --bam reads.bam --fasta genome.fa --out calls.vcf\n```\n"
    )
    prop_make = _synthetic_repo(readme_make)
    built_make = pm.build(prop_make, "make-only")
    inst = built_make["procedure"]["installation"]
    assert inst["ready"] is True
    assert inst["base_condition"]["added_packages"] == ["build-essential", "git", "ca-certificates"]
    assert inst["base_condition"]["miniforge"] is False
    assert "build-essential" in inst["base_condition"]["description"]
    assert "no tool-specific libraries" in inst["base_condition"]["description"]
    assert "apt-get install --no-install-recommends build-essential git ca-certificates" in built_make["dockerfile"]
    for lib in ("zlib1g-dev", "libhts-dev", "libbz2-dev", "liblzma-dev", "libgtest-dev", "cmake"):
        assert lib not in built_make["dockerfile"]

    # Provenance declares base_environment explicitly.
    prov = built_make["procedure"]["provenance"]
    be = prov["harness_choices"]["base_environment"]
    assert be["image"] == "ubuntu:22.04"
    assert be["added_packages"] == ["build-essential", "git", "ca-certificates"]
    assert be["miniforge"] is False

    # cmake + make without apt gets build-essential + cmake + git + ca-certificates (still zero libs).
    readme_cmake = readme_make.replace("```\nmake\n```", "```\ncmake .\nmake\n```")
    built_cmake = pm.build(_synthetic_repo(readme_cmake), "cmake-make")
    assert built_cmake["procedure"]["installation"]["base_condition"]["added_packages"] == [
        "build-essential", "cmake", "git", "ca-certificates"
    ]
    assert "apt-get install --no-install-recommends build-essential cmake git ca-certificates" in built_cmake["dockerfile"]

    # apt install make g++ + cmake .. + make gets cmake + git + ca-certificates (no redundant build-essential).
    readme_apt_cmake = readme_make.replace(
        "```\nmake\n```",
        "```\napt install make g++\nmkdir build\ncd build\ncmake ..\nmake\n```",
    )
    built_apt_cmake = pm.build(_synthetic_repo(readme_apt_cmake), "apt-cmake")
    assert built_apt_cmake["procedure"]["installation"]["base_condition"]["added_packages"] == [
        "cmake", "git", "ca-certificates"
    ]

    # HipSTR already installs make + g++ via apt: no build-essential or cmake injected.
    built_hip = pm.build(_hipstr_proposal(), "hipstr-check")
    assert built_hip["procedure"]["installation"]["base_condition"]["added_packages"] == ["git", "ca-certificates"]
    assert "build-essential" not in built_hip["dockerfile"]

    # Report renders the exact minimal toolchain in needed_beyond_repo, summary.md, and summary.html.
    manifest_data = yaml.safe_load(built_make["manifest_yml"])
    (tmp_path / "review.json").write_text(json.dumps(built_make["procedure"]))
    (tmp_path / "manifest.yml").write_text(built_make["manifest_yml"])
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(report, "ROOT", tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "report.py",
            "--manifest", "manifest.yml",
            "--available", "pass",
            "--installs", "fail",
            "--runs", "skip",
            "--io", "none",
            "--procedure-review", "review.json",
            "--mode", "trial",
        ],
    )
    assert report.main() == 0
    rep = json.loads(capsys.readouterr().out)
    assert any("build-essential" in item and "no tool-specific libraries" in item
               for item in rep.get("needed_beyond_repo") or [])
    md = (tmp_path / "reports" / f"{manifest_data['report']['slug']}.summary.md").read_text()
    html = (tmp_path / "reports" / f"{manifest_data['report']['slug']}.html").read_text()
    assert "minimal build toolchain: build-essential, git, ca-certificates (no tool-specific libraries)" in md
    assert "minimal build toolchain: build-essential, git, ca-certificates (no tool-specific libraries)" in html


def test_paired_sample_and_library_lists_reduce_consistently_with_evidence():
    readme = (
        "Long-read genotyping for Oxford Nanopore sequencing data.\n\n"
        "## Installation\n\n```\nmake\n```\n\n"
        "## Options\n\n"
        "* **--bams** : a comma-separated list of [BAM/CRAM](#bams) files\n"
        "| **bam-samps** list | Comma separated list of samples in same order as BAM files. |\n"
        "| **bam-libs** list | Comma separated list of libraries in same order as BAM files. |\n\n"
        "## Usage\n\n```\n"
        "./tool --bams run1.bam,run2.bam,run3.bam,run4.cram "
        "--fasta genome.fa --regions tr_regions.bed --tr-vcf calls.vcf.gz "
        "--bam-samps SAMPLE1,SAMPLE1,SAMPLE2,SAMPLE3 --bam-libs LIB1,LIB2,LIB3,LIB4\n"
        "```\n\n"
        "### BED\n\n"
        "CHROM | START | END | MOTIF\n"
        "chr1 | 100 | 200 | ACGT\n"
    )
    prop = _synthetic_repo(readme)
    ss = prop["single_sample_bams"]
    assert ss["allowed"] is True
    assert ss["evidence_source"] == "README.md:L11"
    assert [p["flag"] for p in ss["paired_flags"]] == ["--bam-samps", "--bam-libs"]
    assert [p["evidence_source"] for p in ss["paired_flags"]] == ["README.md:L12", "README.md:L13"]

    built = pm.build(prop, "paired-sample-lists")
    review = built["procedure"]
    assert review["may_say_runs"] is True
    assert review["status_code"] == "VERIFIED_PROCEDURE_READY"
    cmd_exec = review["command_review"]["executed"]
    assert "--bams /data/in/input.bam" in cmd_exec
    assert "--bam-samps SAMPLE1 " in cmd_exec
    assert "--bam-libs LIB1" in cmd_exec

    ssa = review["provenance"]["derived"]["single_sample_adaptation"]
    assert ssa["applied"] is True
    assert ssa["original"] == "run1.bam,run2.bam,run3.bam,run4.cram"
    assert ssa["replacement"] == "/data/in/input.bam"
    assert ssa["paired_substitutions"] == [
        {"role": "sample_list", "original": "SAMPLE1,SAMPLE1,SAMPLE2,SAMPLE3", "replacement": "SAMPLE1"},
        {"role": "library_list", "original": "LIB1,LIB2,LIB3,LIB4", "replacement": "LIB1"},
    ]
    assert ssa["paired_evidence_sources"] == ["README.md:L12", "README.md:L13"]

    fake_report = {
        "tool": built["manifest"]["tool"],
        "level": "content",
        "gates": dict.fromkeys(("available", "installs", "runs", "io", "content"), True),
        "source": {**built["manifest"]["source"], "ref_resolved": built["manifest"]["source"]["ref"]},
        "environment": built["manifest"]["environment"],
        "generated": "2026-11-16T00:00:00Z",
        "scope": "Test scope.",
        "verdict": verdict.decide(
            dict.fromkeys(("available", "installs", "runs", "io", "content"), True),
            procedure=review,
            manifest=built["manifest"],
        ),
        "provenance": copy.deepcopy(review["provenance"]),
    }
    md = report._summary_md(fake_report, "paired-sample-lists")
    assert "SAMPLE1,SAMPLE1,SAMPLE2,SAMPLE3` -> `SAMPLE1`" in md
    assert "LIB1,LIB2,LIB3,LIB4` -> `LIB1`" in md

    # Negative 1: arity mismatch -> blocked as FAILED_AMBIGUOUS_CLI.
    readme_mismatch = readme.replace("SAMPLE1,SAMPLE1,SAMPLE2,SAMPLE3", "SAMPLE1,SAMPLE2")
    built_mismatch = pm.build(_synthetic_repo(readme_mismatch), "mismatch-lists")
    assert built_mismatch["procedure"]["may_say_runs"] is False
    assert built_mismatch["procedure"]["status_code"] == "FAILED_AMBIGUOUS_CLI"

    # Negative 2: missing documentary backing for --bam-libs -> blocked as FAILED_AMBIGUOUS_CLI.
    readme_missing_doc = "\n".join(line for line in readme.splitlines() if "bam-libs" not in line or "--bam-libs" in line)
    built_missing = pm.build(_synthetic_repo(readme_missing_doc), "missing-doc-lists")
    assert built_missing["procedure"]["may_say_runs"] is False
    assert built_missing["procedure"]["status_code"] == "FAILED_AMBIGUOUS_CLI"

    # Negative 3: unsupported multi-sample flag like --samp-sex -> blocked.
    readme_sex = readme.replace(
        "--bam-libs LIB1,LIB2,LIB3,LIB4",
        "--bam-libs LIB1,LIB2,LIB3,LIB4 --samp-sex M,M,F,F",
    )
    built_sex = pm.build(_synthetic_repo(readme_sex), "samp-sex-blocked")
    assert built_sex["procedure"]["may_say_runs"] is False
    assert built_sex["procedure"]["status_code"] == "FAILED_AMBIGUOUS_CLI"


def test_environment_heading_names_exact_outside_line_and_usage_prefix_cites_cleanly():
    import fidelity

    readme = (
        "# EnvAndUsage\n\nDesigned for Oxford Nanopore reads.\n\n"
        "### Create an environment\n\n"
        "```bash\n"
        "bash setup/install_env.sh\n"
        "conda activate env\n"
        "```\n\n"
        "## Run\n\n"
        "```bash\n"
        "USAGE: ./tool --bam reads.bam --fasta genome.fa --out calls.vcf\n"
        "```\n"
    )
    prop = _synthetic_repo(readme)
    built = pm.build(prop, "env-and-usage")
    rev = built["procedure"]
    # Install fails with the exact offending line cited rather than "no install found".
    assert rev["blocker"] == "install_not_copyable"
    assert "outside this profile" in rev["reason"]
    assert "README.md, line 8: `bash setup/install_env.sh`" in rev["reason"]
    # `USAGE: ` stripped by detect_recipe still verifies against literal README line.
    assert rev["inferences"]["run_command"]["verified"] is True
    assert rev["inferences"]["run_command"]["evidence_source"] == "README.md:L15"
    assert fidelity.cite(prop, prop["commands"][0])["verified"] is True


def test_standalone_inline_backtick_install_and_usage_lines_apply_generically():
    import fidelity

    # 1. Tool whose install & run commands are single-line inline backticks passes cleanly.
    readme_pass = (
        "# AnyTool\n\nDesigned for Oxford Nanopore reads.\n\n"
        "## Installation\n\n"
        "`pip install -e .`\n\n"
        "## Run\n\n"
        "`USAGE: ./tool --bam reads.bam --fasta genome.fa --out calls.vcf`\n"
    )
    prop_pass = _synthetic_repo(readme_pass)
    prop_pass["files"] = ["README.md", "setup.py", "tool", "pyproject.toml"]
    built_pass = pm.build(prop_pass, "inline-backtick-pass")
    assert built_pass["procedure"]["may_say_runs"] is True
    assert built_pass["procedure"]["inferences"]["run_command"]["verified"] is True
    assert fidelity.cite(prop_pass, prop_pass["commands"][0])["verified"] is True

    # 2. Inline backtick outside step under environment heading cites the exact line.
    readme_outside = (
        "# AnyTool\n\nDesigned for Oxford Nanopore reads.\n\n"
        "### Conda under linux environment\n\n"
        "`wget https://example.org/Miniconda3.sh`\n\n"
        "## Run\n\n"
        "`USAGE: ./tool --bam reads.bam --fasta genome.fa --out calls.vcf`\n"
    )
    prop_out = _synthetic_repo(readme_outside)
    built_out = pm.build(prop_out, "inline-backtick-outside")
    assert built_out["procedure"]["blocker"] == "install_not_copyable"
    assert "README.md, line 7: `wget https://example.org/Miniconda3.sh`" in built_out["procedure"]["reason"]
    assert built_out["procedure"]["inferences"]["run_command"]["verified"] is True
    assert [a["code"] for a in built_out["procedure"]["amendments"]] == ["install_not_copyable"]


def test_unready_install_with_documented_regions_has_no_spurious_command_or_cwd_amendments():
    import pathlib

    src = dr.load_snapshot(pathlib.Path("harness/testdata/benchmark/gangstr"))
    slug, ref = dr.repo_slug(src["tree_resp"]["repo"]), src["tree_resp"].get("ref", "HEAD")
    prop = dr.detect(slug, ref, src["tree_resp"], src["readme"], src["readme_name"], extras=src)
    built = pm.build(prop, "gangstr")
    codes = [a["code"] for a in built["procedure"]["amendments"]]
    assert codes == ["install_profile_unsupported"]
    assert "command_changed" not in codes and "working_directory_changed" not in codes


def test_expansionhunter_and_ehdn_pass_procedure_review_without_custom_recipes():
    import pathlib

    for tool_name in ("expansionhunter", "expansionhunterdenovo"):
        src = dr.load_snapshot(pathlib.Path(f"harness/testdata/benchmark/{tool_name}"))
        slug, ref = dr.repo_slug(src["tree_resp"]["repo"]), src["tree_resp"].get("ref", "HEAD")
        prop = dr.detect(slug, ref, src["tree_resp"], src["readme"], src["readme_name"], extras=src)
        built = pm.build(prop, tool_name)
        assert built["procedure"]["may_say_runs"] is True, (tool_name, built["procedure"].get("amendments"))
        assert built["procedure"]["amendments"] == []
