"""What the README or the repository could add, said on every report.

A run that passed still tells its author that the repository ships no
example data; a run that stopped does not repeat, as a recommendation, the
gap that stopped it."""
import html

import report

GAPS = [{"item": "example_data", "text": "The repository ships no example input a stranger could run on."},
        {"item": "output", "text": "The README does not describe the output file or its format."}]


def _proposal(**input_type):
    return {"readme": {"gaps": GAPS}, "input_type": input_type}


def test_a_run_that_passed_still_gets_its_recommendations():
    recs = report.recommendations_for({"verdict": {"code": "runs", "readme_gaps": []}}, _proposal())
    assert [r["code"] for r in recs] == ["example_data", "output"]
    assert "small example" in recs[0]["text"]


def test_what_stopped_the_run_is_the_verdict_s_and_is_not_repeated():
    r = {"verdict": {"code": "undetermined", "readme_gaps": [GAPS[1]]}}
    assert [x["code"] for x in report.recommendations_for(r, _proposal())] == ["example_data"]


def test_an_unstated_assembly_is_recommended_only_when_strhub_mounted_the_reference():
    mounted = {"verdict": {"code": "runs"}, "mounted_inputs": {"reference": {"mount_path": "/data/ref/hg38.fa"}}}
    assert "reference_assembly" in [r["code"] for r in report.recommendations_for(mounted, _proposal(signals={}))]
    assert "reference_assembly" not in [r["code"] for r in report.recommendations_for(mounted, _proposal(signals={"hg38": 2}))]
    assert "reference_assembly" not in [r["code"] for r in report.recommendations_for({"verdict": {}}, _proposal(signals={}))]


def test_no_reading_of_the_repository_means_no_recommendations():
    assert report.recommendations_for({"verdict": {"code": "runs"}}, None) == []


def test_both_copies_print_them():
    r = {"schema": "strhub-verified/1", "tool": {"name": "Tool", "version": "1"}, "level": "io",
         "gates": {"available": True, "installs": True, "runs": True, "io": True, "content": False},
         "source": {"repo": "https://github.com/a/b", "ref_resolved": "abc"},
         "environment": {"dockerfile": "Dockerfile", "os": ["ubuntu-22.04"]},
         "generated": "2026-11-13T00:00:00+00:00", "scope": report.SCOPE, "instrument": "documented",
         "recommendations": [{"code": "example_data", "text": "The repository ships no example input."}]}
    for text in (report._summary_md(r, "tool"), html.unescape(report._summary_html(r, "tool"))):
        assert report.RECOMMENDATIONS_HEADING in text and "The repository ships no example input." in text
    r.pop("recommendations")
    assert report.RECOMMENDATIONS_HEADING not in report._summary_md(r, "tool")


def test_shared_regions_catalog_triggers_recommendation_and_output_preview_sanitizes(tmp_path):
    import gzip

    r = {
        "verdict": {"code": "runs", "readme_gaps": []},
        "input_contract": {"type": "illumina-bam-hg38", "regions": "hipstr"},
    }
    recs = report.recommendations_for(r, _proposal())
    codes = [x["code"] for x in recs]
    assert "ship_regions_catalog" in codes
    cat_rec = next(x for x in recs if x["code"] == "ship_regions_catalog")
    assert "hipstr schema" in cat_rec["text"]

    # Bounded, sanitized output preview: strips ANSI codes, caps lines, handles .gz, rejects binary.
    out_dir = tmp_path / "out_external"
    out_dir.mkdir()
    vcf_gz = out_dir / "calls.vcf.gz"
    lines_in = ["##fileformat=VCFv4.2", "#CHROM\tPOS\tID\tREF\tALT"] + [
        f"\x1b[31mchr11\x1b[0m\t{2171000 + i}\tTH01_{i}\tAATG\tA" for i in range(30)
    ]
    with gzip.open(vcf_gz, "wt") as fh:
        fh.write("\n".join(lines_in) + "\n")
    prev = report.build_output_preview(out_dir, ["calls.vcf.gz"], leg="external", max_lines=18)
    assert prev is not None
    assert prev["file"] == "calls.vcf.gz" and prev["binary"] is False and prev["truncated"] is True
    assert len(prev["lines"]) == 18
    assert "\x1b" not in "\n".join(prev["lines"])
    assert prev["lines"][2].startswith("chr11\t2171000\tTH01_0")

    # Binary files with NUL bytes are flagged binary and never dump raw bytes.
    bin_dir = tmp_path / "out_bin"
    bin_dir.mkdir()
    (bin_dir / "raw.bam").write_bytes(b"BAM\x01\x00\x00\x00\xff\xfe")
    bprev = report.build_output_preview(bin_dir, ["raw.bam"], leg="external")
    assert bprev is not None and bprev["binary"] is True and bprev["lines"] == []

    # Output verification + slice scope note render clearly in both prose copies.
    ov = report._output_verification_block(
        {"available": True, "installs": True, "runs": True, "io": True, "content": False},
        {"code": "runs", "content_verified": False, "output_status": "output_only_content_unverified"},
    )
    assert ov["content_verified"] is False
    assert "STR content not verified automatically" in ov["note"]
    assert "contenido STR no verificado automáticamente" in ov["note_es"]
    rep_doc = {
        "schema": "strhub-verified/1",
        "tool": {"name": "Tool", "version": "1"},
        "level": "io",
        "gates": {"available": True, "installs": True, "runs": True, "io": True, "content": False},
        "source": {"repo": "https://github.com/a/b", "ref_resolved": "abc"},
        "environment": {"dockerfile": "Dockerfile", "os": ["ubuntu-22.04"]},
        "generated": "2026-11-13T00:00:00+00:00",
        "scope": report.SCOPE,
        "instrument": "documented",
        "output_verification": ov,
        "output_preview": prev,
        "slice_scope_note": report.SLICE_SCOPE_NOTE,
    }
    for rendered in (report._summary_md(rep_doc, "tool"), html.unescape(report._summary_html(rep_doc, "tool"))):
        assert "STR content not verified automatically" in rendered
        assert "calls.vcf.gz" in rendered
        assert "bounded genomic slice" in rendered
