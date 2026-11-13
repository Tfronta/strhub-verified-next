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
