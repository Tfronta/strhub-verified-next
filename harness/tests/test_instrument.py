"""The one instrument, and what each rendering says about it.

The engine runs the repository's own instructions and nothing else. A report
that is not such a run (history already on gh-pages that this engine did not
write) is never the badge: its label says it was not verified as documented."""
import html
import json
import pathlib
import subprocess
import sys

import yaml

import certificate_text as ct
import report

ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_only_a_run_of_the_repository_s_instructions_is_a_documented_run():
    assert ct.is_documented_run({"instrument": "documented"})
    # Before the `instrument` field: the proposal that wrote the report says so.
    assert ct.is_documented_run({"recipe": {"origin": "proposed"}})
    assert ct.is_documented_run({"caveats": {"source": "detect_recipe"}})
    # Anything else is not this engine's, whatever it is called.
    assert not ct.is_documented_run({"instrument": "something-else"})
    assert not ct.is_documented_run({"instrument": "documented", "record_type": "a-record-that-is-not-a-run"})
    assert not ct.is_documented_run({"submission": {"by": "third_party"}})
    assert not ct.is_documented_run({})


def test_the_schema_admits_no_recipe_that_was_not_read_off_the_repository():
    import _manifest
    import pytest
    from jsonschema import ValidationError
    m = {"tool": {"name": "x", "version": "1"}, "source": {"repo": "https://github.com/a/b", "ref": "a" * 40},
         "environment": {"dockerfile": "Dockerfile"}, "run": {"cmd": "x"},
         "outputs": [{"path": "out.txt", "format": "text"}], "recipe": {"origin": "proposed"}}
    _manifest.validate(m)
    for recipe in ({"origin": "hand-written"}, {"origin": "proposed", "workarounds": [{"what": "a", "instead_of": "b"}]}):
        with pytest.raises(ValidationError):
            _manifest.validate({**m, "recipe": recipe})


def _report(instrument="documented"):
    return {"schema": "strhub-verified/1", "tool": {"name": "STRspy", "version": "v2.0"}, "level": "io",
         "gates": {"available": True, "installs": True, "runs": True, "io": True, "content": False},
         "source": {"repo": "https://github.com/unique379r/strspy", "ref_resolved": "dafdee7"},
         "environment": {"dockerfile": "Dockerfile", "os": ["ubuntu-22.04"]},
         "generated": "2026-09-18T13:38:00+00:00", "scope": report.SCOPE,
         "instrument": instrument, "recipe": {"origin": "proposed"}}


def test_a_report_opens_with_the_tool_as_it_is():
    r = _report("documented")
    for text in (report._summary_md(r, "strspy-ont"), html.unescape(report._summary_html(r, "strspy-ont"))):
        assert ct.AS_IS_HEADING in text and ct.NOT_DOCUMENTED not in text
        assert "Runs as documented" in text


def test_the_label_says_the_result_in_words_not_the_rung():
    """One rule for the badge, both copies, the index and the certificate."""
    doc = lambda level, code, **k: {**_report("documented"), "level": level,
                                    "verdict": {"code": code, "title": "", "reason": ""}, **k}
    # Looking like genotypes does not strengthen the claim. Both rungs are
    # the same sentence and the same colour.
    assert ct.headline(doc("content", "runs")) == ("Runs as documented", "green")
    assert ct.headline(doc("io", "runs")) == ("Runs as documented", "green")
    assert ct.headline(doc("io", "runs", diagnostics={"external": [{"id": "cannot_open", "severity": "error"}]})) \
        == ("Runs as documented (errors reported)", "yellow")
    assert ct.headline(doc("installs", "fails")) == ("Does not run as documented: stops at run", "red")
    assert ct.headline(doc("available", "fails")) == ("Does not run as documented: stops at install", "red")
    assert ct.headline(doc("runs", "fails")) == ("Does not run as documented: no output", "red")
    assert ct.headline(doc("installs", "undetermined")) == ("Could not be determined", "lightgrey")
    assert ct.headline(doc("installs", "out_of_scope")) == ("Out of scope", "lightgrey")
    # Not a run of the repository's instructions, whatever it reached.
    assert ct.headline({**_report("something-else"), "level": "content"}) == (ct.NOT_DOCUMENTED, "lightgrey")
    # A report from before the verdict: read off the rung.
    old = {**_report("documented")}; old.pop("verdict", None)
    assert ct.headline({**old, "level": "content"})[0] == "Runs as documented"
    assert ct.headline({**old, "level": "installs"})[0] == "Does not run as documented: stops at run"
