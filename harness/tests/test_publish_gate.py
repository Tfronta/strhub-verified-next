"""What goes to the catalogue. A failure of the tool does; a fault of ours, a
run nobody asked to publish, and a run landing on another repository's card do not."""
import publish_gate
from procedure_context import report as bound_report

INDEX = {"tools": [{"slug": "hipstr", "source_repo": "https://github.com/tfwillems/HipSTR"}]}


def report(code="fails", basis="gates", slug="hipstr", repo="https://github.com/tfwillems/HipSTR"):
    result = bound_report("runs" if code == "runs" else "fails", repo=repo)
    result["verdict"].update(code=code, basis=basis)
    return result, slug


def decide(case, **kw):
    r, slug = case
    args = dict(slug=slug, publish_requested=True, index=INDEX)
    args.update(kw)
    return publish_gate.decide(r, **args)


def test_a_failure_of_the_tool_is_published():
    ok, _ = decide(report("fails"))
    assert ok


def test_strhub_fault_is_not_published():
    ok, why = decide(report("undetermined", basis="strhub_infra"))
    assert not ok and "infrastructure" in why


def test_evaluator_scope_limit_with_valid_review_publishes_as_undetermined():
    import authorization
    from test_documented_install import proposal, block, _manifest as di_manifest
    import certificate_text
    import prepare
    import verdict

    p = proposal(block("pip install ."))
    p["tree_paths"].append(".dockerignore")
    m = di_manifest(p)
    m["environment"] = {"dockerfile": "Dockerfile", "os": ["ubuntu-22.04"], "source": "generated"}
    reviewed = authorization.prepare_review(p, m, [], [])
    gates = {"available": True, "installs": False, "runs": False, "io": False, "content": False}
    inner, cwd = prepare.unwrap_example(m["run"]["cmd"])
    rep = {
        "schema": "strhub-verified/1",
        "tool": m["tool"],
        "source": {**m["source"], "ref_resolved": m["source"]["ref"]},
        "environment": m["environment"],
        "input_contract": m["inputs"],
        "gates": gates,
        "instrument": certificate_text.INSTRUMENT,
        "recipe": {"origin": "proposed"},
        "procedure_review": reviewed,
        "run": {"cmd": inner, "effective_cmd": m["run"]["cmd"], "cwd": cwd, "step_outcome": "skipped"},
        "verdict": verdict.decide(gates, procedure=reviewed, manifest=m),
    }
    assert rep["verdict"]["code"] == "undetermined"
    assert rep["verdict"]["basis"] == "scope"
    ok, why = publish_gate.decide(rep, slug="example-tool", publish_requested=True, index={"tools": []})
    assert ok and why == "published"


def test_out_of_scope_is_not_published():
    ok, _ = decide(report("out_of_scope", basis="environment"))
    assert not ok


def test_a_run_nobody_asked_to_publish_stays_private():
    ok, why = decide(report("runs"), publish_requested=False)
    assert not ok and "did not ask" in why


def test_the_slug_is_the_one_the_report_was_written_under(tmp_path, monkeypatch, capsys):
    """The report does not carry its slug; the card it would land on is read
    off the file's name, so the ownership check is never vacuous."""
    import json
    r, _ = report("fails", repo="https://github.com/someone/HipSTR")
    (tmp_path / "hipstr.json").write_text(json.dumps(r))
    (tmp_path / "index.json").write_text(json.dumps(INDEX))
    monkeypatch.setenv("PUBLISH", "true")
    publish_gate.main(["--report", str(tmp_path / "hipstr.json"), "--index", str(tmp_path / "index.json")])
    out = capsys.readouterr().out
    assert "publishable=false" in out and "belongs to" in out


def test_another_repository_named_like_a_card_does_not_take_it():
    ok, why = decide(report("fails", repo="https://github.com/someone/HipSTR"))
    assert not ok and "belongs to" in why


def test_same_repository_in_another_spelling_is_the_same_card():
    ok, _ = decide(report("runs", repo="https://github.com/TFWillems/hipstr.git/"))
    assert ok


def test_a_new_card_is_published():
    ok, _ = decide(report("fails", slug="longtr", repo="https://github.com/gymrek-lab/LongTR"))
    assert ok


def test_unreadable_catalogue_fails_closed():
    ok, why = decide(report("runs"), index=None)
    assert not ok and "catalogue" in why
