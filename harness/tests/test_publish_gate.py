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
    ok, why = decide(report("undetermined", basis="strhub"))
    assert not ok and "infrastructure" in why


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
