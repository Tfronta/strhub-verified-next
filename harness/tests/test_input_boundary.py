"""Runner-boundary regressions with inert files; never Docker or STR software."""
import builtins
import json
import pathlib
import sys

import pytest
import yaml
from jsonschema import ValidationError

import _manifest
import _paths
import prepare

CASES = json.loads((pathlib.Path(__file__).parents[1] / "testdata/input_path_cases.json").read_text())


@pytest.mark.parametrize("case", CASES)
def test_manifest_path_contract_matches_web_cases(case):
    for field in ("fixture", "regions", "dockerfile", "from_repo"):
        m = manifest()
        if field in ("fixture", "regions"):
            m["inputs"] = {field: case["path"]}
        else:
            m["environment"][field] = case["path"]
        if case["valid"]:
            _manifest.validate(m)
        else:
            with pytest.raises((ValueError, ValidationError)):
                _manifest.validate(m)


def manifest():
    return {"tool": {"name": "example", "version": "1"},
            "source": {"repo": "https://github.com/example/tool", "ref": "a" * 40},
            "environment": {"dockerfile": "Dockerfile"},
            "run": {"cmd": "not executed"},
            "outputs": [{"path": "result.txt", "format": "text"}]}


def proposed(tmp_path, monkeypatch, m=None):
    """A run's descriptor where prepare reads it: <work>/proposal."""
    work = tmp_path / "work"
    tool = work / "proposal"
    tool.mkdir(parents=True)
    (tool / "manifest.yml").write_text(yaml.safe_dump(m or manifest()))
    (tool / "Dockerfile").write_text("FROM scratch\n")
    monkeypatch.setattr(sys, "argv", ["prepare.py", "example", "--work", str(work)])
    return tool, work


@pytest.mark.parametrize("tool", ["../outside", "/tmp/outside", "a/b", ".git"])
def test_tool_identifier_cannot_select_another_root(tmp_path, monkeypatch, tool):
    work = tmp_path / "work"
    monkeypatch.setattr(sys, "argv", ["prepare.py", tool, "--work", str(work)])
    with pytest.raises(ValueError, match="safe directory"):
        prepare.main()
    assert not work.exists()


def test_dataset_index_cannot_introduce_an_external_source(tmp_path, monkeypatch):
    m = manifest()
    m["inputs"] = {"type": "test"}
    _, work = proposed(tmp_path, monkeypatch, m)
    monkeypatch.setattr(prepare.datasets_lib, "load_index", lambda: {
        "datasets": {"test": {"data": "../outside.bam", "canonical_input": "input.bam"}}})
    with pytest.raises(ValueError):
        prepare.main()
    assert not (work / "in_external").exists()


def test_missing_validator_cannot_turn_off_manifest_validation(monkeypatch):
    real_import = builtins.__import__
    def absent(name, *args, **kwargs):
        if name == "jsonschema":
            raise ImportError("synthetic missing dependency")
        return real_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", absent)
    with pytest.raises(RuntimeError, match="validation cannot be skipped"):
        _manifest.validate(manifest())


@pytest.mark.parametrize("kind", ["assets", "dockerfile", "destination"])
def test_entire_preparation_checks_all_paths_before_any_staging(tmp_path, monkeypatch, kind):
    m = manifest()
    m["inputs"] = {"type": "illumina-bam-hg38"}
    tool, work = proposed(tmp_path, monkeypatch, m)
    sentinel = tmp_path / "outside"
    sentinel.mkdir()
    (sentinel / "private").write_text("never read")
    if kind == "assets":
        (tool / "assets").symlink_to(sentinel, target_is_directory=True)
    elif kind == "dockerfile":
        (tool / "Dockerfile").unlink()
        (tool / "Dockerfile").symlink_to(sentinel / "private")
    else:
        (work / "in_external").symlink_to(sentinel, target_is_directory=True)
    def forbidden(*args, **kwargs):
        raise AssertionError("staging started before input validation")
    monkeypatch.setattr(prepare.input_provenance, "stage", forbidden)
    with pytest.raises((ValueError, ValidationError)):
        prepare.main()
    assert [p.name for p in sentinel.iterdir()] == ["private"]
    assert (sentinel / "private").read_text() == "never read"


def test_remote_url_quotes_literals_without_url_traversal_or_query():
    url = _paths.raw_url({"repo": "https://github.com/example/tool.git", "ref": "release/v1",
                          "path": "examples/a b?x#y.bam"})
    assert url == "https://raw.githubusercontent.com/example/tool/release%2Fv1/examples/a%20b%3Fx%23y.bam"
    with pytest.raises(ValueError):
        _paths.raw_url({"repo": "https://github.com/example/tool", "ref": "main", "path": "../other"})

