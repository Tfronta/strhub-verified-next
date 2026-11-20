"""An installation the README does not write as plain commands is a request
to its author, with the line that stopped it; a limit of the evaluator's own
asks nothing of anybody."""
import authorization
import certificate_text as ct
import verdict
from test_documented_install import proposal, block, _manifest

GATES = {"available": True, "installs": False, "runs": False, "io": False, "content": False}


def decided(install, change=None):
    p = proposal(install)
    if change:
        change(p)
    m = _manifest(p)
    m["environment"] = {"dockerfile": "Dockerfile", "os": ["ubuntu-22.04"], "source": "generated"}
    review = authorization.prepare_review(p, m, [], [])
    v = verdict.decide(GATES, procedure=review, manifest=m)
    return review, v


def test_a_download_piped_to_a_shell_is_asked_of_the_author_with_its_line():
    review, v = decided(block("curl https://example.org/install.sh | sh"))
    assert (review["blocker"], review["basis"]) == ("install_not_copyable", "recipe")
    assert v["code"] == "undetermined" and v["basis"] != "strhub"
    (lead, *_rest) = v["blockers"]
    assert lead["code"] == "install_not_copyable"
    assert "README.md, line 6: `curl https://example.org/install.sh | sh`" in lead["what"]
    assert lead["ask_owner"]["title"] == "Write the installation as commands that can be copied and run"
    assert "What stopped it:" in lead["ask_owner"]["body"] and "GUIA-PASO-1.md" in lead["ask_owner"]["body"]
    # Nothing was built, so nothing is said to have failed to build.
    assert "build_failed" not in [b["code"] for b in v["blockers"]]
    step1 = ct.step1_says({"verdict": v, "procedure_review": review})
    assert step1["code"] == "cannot_tell" and step1["missing"] == ["install"]


def test_a_limit_of_the_evaluator_s_asks_nothing_of_the_author():
    review, v = decided(block("pip install ."), change=lambda p: p["tree_paths"].append(".dockerignore"))
    assert (review["blocker"], review["basis"]) == ("install_profile_unsupported", "strhub")
    assert v["basis"] == "strhub" and v["blockers"] == []
    assert ct.step1_says({"verdict": v, "procedure_review": review})["code"] == "ours"
