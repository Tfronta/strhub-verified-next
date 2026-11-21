"""General scientific consistency tests across all report sections.

Covers the 8 generic verification outcomes using synthetic fixtures (never
tool-specific recipes) and verifies that cover stages, scope statement,
dataset matrix state, test-data wording, diagnostics, and repeatability
statements never contradict the recorded gates.
"""
import certificate_text as ct
import diagnose_log as dl


def _base_report(gates, *, level, verdict_code, verdict_reason,
                 execution_established=True, repo_test_data=None,
                 dataset_name="Illumina BAM (hg38), NA12878"):
    report = {
        "tool": {"name": "ExampleTool", "version": "1.0.0"},
        "source": {"repo": "https://github.com/org/exampletool", "ref": "a" * 40},
        "gates": dict(gates),
        "level": level,
        "verdict": {
            "code": verdict_code,
            "title": verdict_code.title(),
            "reason": verdict_reason,
        },
        "datasets": [
            {"leg": "external", "available": True, "passed": bool(gates.get("io"))}
        ],
    }
    cfg = {
        "tool_name": "ExampleTool",
        "tool_display": "ExampleTool 1.0.0",
        "gates": dict(gates),
        "verdict": report["verdict"],
        "stats": {"distinct_str_loci": 20 if gates.get("content") else 0},
        "declared_format": "VCF",
        "dataset": {"name": dataset_name},
        "repo_test_data": repo_test_data or {"known": True, "present": True, "count": 2},
        "execution_finding_established": execution_established,
    }
    return report, cfg


def test_1_repository_unavailable():
    gates = {"available": False, "installs": False, "runs": False, "io": False, "content": False}
    rep, cfg = _base_report(gates, level="none", verdict_code="fails", verdict_reason="Source could not be fetched.")
    cert = ct.certificate_for(rep, cfg)
    stages = {s["key"]: s["status"] for s in cert["stages"]}
    assert stages == {"available": "FAIL", "installs": "NOT ATTEMPTED", "runs": "NOT ATTEMPTED", "output": "NOT ATTEMPTED"}
    assert "checks whether" in cert["scope"]["statement"].lower()
    assert "confirms the tool installs" not in cert["scope"]["statement"].lower()


def test_2_installation_failed_never_claims_dataset_ran_or_exact_reproducibility():
    gates = {"available": True, "installs": False, "runs": False, "io": False, "content": False}
    rep, cfg = _base_report(gates, level="available", verdict_code="fails",
                            verdict_reason="The environment did not build from the declared install steps.")
    cert = ct.certificate_for(rep, cfg)
    stages = {s["key"]: s["status"] for s in cert["stages"]}
    assert stages == {"available": "PASS", "installs": "FAIL", "runs": "NOT ATTEMPTED", "output": "NOT ATTEMPTED"}
    full_text = " ".join(c["title"] + " " + c["body"] for c in cert["conclusion"])
    assert "ran on STRhub's reference dataset" not in full_text
    assert "not processed because the installation did not complete" in full_text
    assert "sufficient to reproduce" not in full_text
    assert "analysis command was not executed" in full_text
    assert "Section 3" not in full_text


def test_3_install_succeeded_and_execution_failed():
    gates = {"available": True, "installs": True, "runs": False, "io": False, "content": False}
    rep, cfg = _base_report(gates, level="installs", verdict_code="fails",
                            verdict_reason="The tool exited with an error before producing its documented output.")
    cert = ct.certificate_for(rep, cfg)
    stages = {s["key"]: s["status"] for s in cert["stages"]}
    assert stages == {"available": "PASS", "installs": "PASS", "runs": "FAIL", "output": "NOT ATTEMPTED"}
    titles = [c["title"] for c in cert["conclusion"]]
    assert "Does not run end-to-end" in titles
    assert "Repeatability of this verification run" in titles


def test_4_execution_succeeded_without_output_files():
    gates = {"available": True, "installs": True, "runs": True, "io": False, "content": False}
    rep, cfg = _base_report(gates, level="runs", verdict_code="fails",
                            verdict_reason="The tool ran to completion but produced no output in the documented format.")
    cert = ct.certificate_for(rep, cfg)
    stages = {s["key"]: s["status"] for s in cert["stages"]}
    assert stages == {"available": "PASS", "installs": "PASS", "runs": "PASS", "output": "FAIL"}
    titles = [c["title"] for c in cert["conclusion"]]
    assert "Runs end-to-end" in titles
    assert "No output produced" in titles


def test_5_execution_succeeded_with_structurally_invalid_or_unplausible_output():
    gates = {"available": True, "installs": True, "runs": True, "io": True, "content": False}
    rep, cfg = _base_report(gates, level="io", verdict_code="runs",
                            verdict_reason="The tool installed and its run produced its documented output.")
    cert = ct.certificate_for(rep, cfg)
    stages = {s["key"]: s["status"] for s in cert["stages"]}
    assert stages == {"available": "PASS", "installs": "PASS", "runs": "PASS", "output": "PASS"}
    titles = [c["title"] for c in cert["conclusion"]]
    assert "Produces output in the declared format" in titles
    assert "Produces plausible output" not in titles


def test_6_all_five_gates_passed():
    gates = {"available": True, "installs": True, "runs": True, "io": True, "content": True}
    rep, cfg = _base_report(gates, level="content", verdict_code="runs",
                            verdict_reason="The tool installed and its run produced its documented output.")
    cert = ct.certificate_for(rep, cfg)
    stages = {s["key"]: s["status"] for s in cert["stages"]}
    assert stages == {"available": "PASS", "installs": "PASS", "runs": "PASS", "output": "PASS"}
    titles = [c["title"] for c in cert["conclusion"]]
    assert "Runs end-to-end" in titles
    assert "Produces plausible output" in titles
    assert "Repeatability of this verification run" in titles


def test_7_insufficient_evidence_marks_downstream_not_attempted_and_neutral_fault_text():
    gates = {"available": True, "installs": False, "runs": False, "io": False, "content": False}
    rep, cfg = _base_report(gates, level="none", verdict_code="undetermined",
                            verdict_reason="No copyable installation.", execution_established=False)
    cert = ct.certificate_for(rep, cfg)
    stages = {s["key"]: s["status"] for s in cert["stages"]}
    assert stages == {"available": "PASS", "installs": "NOT ATTEMPTED", "runs": "NOT ATTEMPTED", "output": "NOT ATTEMPTED"}
    # Neutral attribution sentence never blames software or author categorically.
    sent = dl.install_fault_sentence(["author"])
    assert "Observed in the build log" in sent
    assert "not automatically determined" in sent
    assert "They are faults in how the tool was set up here" not in sent


def test_8_dataset_selected_but_never_processed():
    gates = {"available": True, "installs": False, "runs": False, "io": False, "content": False}
    for td in ({"known": False}, {"known": True, "present": False, "count": 0}, {"known": True, "present": True, "count": 3}):
        _, cfg = _base_report(gates, level="available", verdict_code="fails",
                              verdict_reason="Build failed.", repo_test_data=td)
        title, body = ct.test_data_item(cfg, "Illumina BAM (hg38), NA12878")
        assert "ran on" not in body.lower()
        assert "not processed" in body.lower()


def test_9_undetermined_after_install_and_run_preserves_passed_stages():
    # When a tool installs and runs end-to-end, but output validity could not
    # be established (e.g. basis='strhub' panel mismatch -> undetermined),
    # stage_states must preserve PASS for the gates that actually passed.
    gates = {"available": True, "installs": True, "runs": True, "io": False, "content": False}
    rep, cfg = _base_report(gates, level="runs", verdict_code="undetermined",
                            verdict_reason="Output VCF contains no called genotypes.",
                            execution_established=False)
    cert = ct.certificate_for(rep, cfg)
    stages = {s["key"]: s["status"] for s in cert["stages"]}
    assert stages == {
        "available": "PASS",
        "installs": "PASS",
        "runs": "PASS",
        "output": "NOT ESTABLISHED",
    }


def test_10_generic_catalog_panel_matching_medical_vs_forensic():
    import detect_recipe as dr

    # Generic medical BED coordinates overlapping datasets/ont-bam-hg38-med/loci.bed
    med_bed = "\n".join([
        "chr4\t3074876\t3074933\tHTT",
        "chr9\t27573528\t27573546\tC9orf72",
        "chrX\t147912050\t147912110\tFMR1",
        "chr6\t16327635\t16327722\tATXN1",
    ])
    # Generic forensic CODIS BED coordinates overlapping datasets/ont-bam-hg38/loci.bed
    forensic_bed = "\n".join([
        "chr11\t2171088\t2171115\tTH01",
        "chr2\t1489653\t1489684\tTPOX",
        "chr5\t150076324\t150076375\tCSF1PO",
        "chr4\t154587736\t154587823\tFGA",
    ])

    # 1. Command uses symbolic keyword (--loci hg38) + repo ships hg38 medical BED -> switches to -med.
    res = dr.detect_panel_from_catalogs(
        "ont-bam-hg38",
        {"src/pkg/data/loci.hg38.bed": med_bed},
        "tool --bam sample.bam --ref reference.fasta --loci hg38 --out out",
        {"src/pkg/data/loci.hg38.bed"},
    )
    assert res is not None
    assert res["panel"] == "medical"
    assert res["dataset"] == "ont-bam-hg38-med"
    assert res["forensic_overlap"] == 0
    assert res["medical_overlap"] >= 4

    # 2. Command takes an external regions placeholder -> STRhub supplies regions, keep forensic.
    res_placeholder = dr.detect_panel_from_catalogs(
        "illumina-bam-hg38",
        {"catalogs/hg38/loci.bed": med_bed},
        "tool --reads sample.bam --ref hg38.fa --regions <regions.bed> --out out.vcf",
        {"catalogs/hg38/loci.bed"},
    )
    assert res_placeholder is None

    # 3. Repo catalog overlaps forensic loci -> keep forensic.
    res_forensic = dr.detect_panel_from_catalogs(
        "ont-bam-hg38",
        {"data/codis.hg38.bed": forensic_bed},
        "tool --bam sample.bam --ref reference.fasta --out out",
        {"data/codis.hg38.bed"},
    )
    assert res_forensic is None

    # 4. Genome-wide / mixed catalog overlapping both forensic and medical -> keep forensic.
    res_mixed = dr.detect_panel_from_catalogs(
        "ont-bam-hg38",
        {"data/all.hg38.bed": med_bed + "\n" + forensic_bed},
        "tool --bam sample.bam --ref reference.fasta --out out",
        {"data/all.hg38.bed"},
    )
    assert res_mixed is None

    # 5. Non-hg38 catalog filename (hg19) is ignored.
    res_hg19 = dr.detect_panel_from_catalogs(
        "ont-bam-hg38",
        {"data/loci.hg19.bed": med_bed},
        "tool --bam sample.bam --ref reference.fasta --loci hg38 --out out",
        {"data/loci.hg19.bed"},
    )
    assert res_hg19 is None


def test_11_technology_aware_limitations_and_medical_conclusion():
    # ONT and PacBio HiFi must never emit short-read limitations.
    ont_lims = ct.limitations_for(input_type="ont-bam-hg38-med", executed=True)
    assert not any("short-read" in x.lower() for x in ont_lims)
    assert any("long-read" in x.lower() for x in ont_lims)

    hifi_lims = ct.limitations_for(input_type="pacbio-hifi-bam-hg38", executed=True)
    assert not any("short-read" in x.lower() for x in hifi_lims)
    assert any("long-read" in x.lower() for x in hifi_lims)

    # Illumina short-read retains short-read limitations.
    ill_lims = ct.limitations_for(input_type="illumina-bam-hg38", executed=True)
    assert any("short-read" in x.lower() for x in ill_lims)

    # Unexecuted run (failed build) emits neither short-read nor long-read limitations.
    not_run_lims = ct.limitations_for(input_type="ont-bam-hg38", executed=False)
    assert not any("short-read" in x.lower() or "long-read" in x.lower() for x in not_run_lims)
    assert any("no sequencing data were processed" in x.lower() for x in not_run_lims)

    # Medical panel conclusion never labels loci as forensic and avoids claiming every locus has valid genotypes.
    gates = {"available": True, "installs": True, "runs": True, "io": True, "content": True}
    rep, cfg = _base_report(gates, level="content", verdict_code="runs",
                            verdict_reason="The tool installed and its run produced its documented output.")
    cfg["input_type"] = "ont-bam-hg38-med"
    cfg["dataset"] = {"name": "1000 Genomes ONT, hg38 medical STR slice (R10 SUP)",
                      "panel_label": "disease-associated STR loci"}
    cfg["stats"] = {"distinct_str_loci": 74}
    cert = ct.certificate_for(rep, cfg)
    produced = next(c["body"] for c in cert["conclusion"] if c["title"] == "Produces plausible output")
    assert "disease-associated STR loci" in produced
    assert "forensic" not in produced.lower()
    assert "not genotype validity" in produced.lower()
    assert not any("short-read" in x.lower() for x in cert["limitations"])
