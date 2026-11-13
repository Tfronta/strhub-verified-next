"""A report on a fork says of what, and whether the fork touches code."""
import fork_provenance as fp

SHA = "a" * 40
FORK = "https://github.com/someone/tool"


def api(files_by_branch, fork=True, default="main"):
    def get(path, token):
        if path == "/repos/someone/tool":
            return {"fork": fork, "parent": {"full_name": "author/tool", "owner": {"login": "author"},
                                             "default_branch": default}}
        if path.startswith("/repos/author/tool/branches"):
            return [{"name": n} for n in files_by_branch]
        for branch, files in files_by_branch.items():
            if path == f"/repos/someone/tool/compare/author:{branch}...{SHA}":
                if files is None:
                    return {"__status__": 404}
                return {"files": [{"filename": f} for f in files], "ahead_by": len(files), "behind_by": 0,
                        "merge_base_commit": {"sha": "b" * 40}, "html_url": f"https://github.com/someone/tool/compare/{branch}"}
        return None
    return get


def test_paths_are_sorted_into_documentation_data_and_code_and_the_unknown_is_code():
    kinds = {p: fp.classify(p) for p in (
        "README.md", "docs/usage.txt", "LICENSE", "figures/overview.png",
        "example/sample.bam", "example/sample.bam.bai", "test/regions.bed", "db/TH01.fa", "calls.vcf.gz",
        "src/main.c", "Makefile", "environment.yml", "config/InputConfig.txt", "run.sh", "notes.txt")}
    assert [k for p, k in kinds.items() if k == "documentation"] == ["documentation"] * 4
    assert kinds["example/sample.bam"] == kinds["test/regions.bed"] == kinds["db/TH01.fa"] == kinds["calls.vcf.gz"] == "data"
    for path in ("src/main.c", "Makefile", "environment.yml", "config/InputConfig.txt", "run.sh", "notes.txt"):
        assert kinds[path] == "code", path


def test_a_fork_that_adds_documentation_and_example_data_leaves_the_code_the_author_s():
    r = fp.provenance(FORK, SHA, get=api({"main": ["README.md", "example/sample.bam", "example/regions.bed"]}))
    assert r["is_fork"] and r["parent"] == "author/tool" and r["kind"] == "documentation_and_data"
    assert r["counts"] == {"documentation": 1, "data": 2, "code": 0}
    assert "not code: the code is the original's" in fp.note(r)
    only_docs = fp.provenance(FORK, SHA, get=api({"main": ["README.md"]}))
    assert only_docs["kind"] == "documentation_only"


def test_a_fork_that_changes_a_script_is_about_the_fork():
    r = fp.provenance(FORK, SHA, get=api({"main": ["README.md", "src/run.sh"]}))
    assert r["kind"] == "code" and r["changed"]["code"] == ["src/run.sh"]
    assert "about the fork and not about the original" in fp.note(r)


def test_the_branch_compared_is_the_one_the_commit_differs_least_from():
    # Forked from a release branch: against `main` it would be charged with that branch's work.
    get = api({"main": ["README.md"] + [f"src/f{i}.c" for i in range(40)], "release-2": ["README.md"]})
    r = fp.provenance(FORK, SHA, get=get)
    assert r["base_branch"] == "release-2" and r["kind"] == "documentation_only" and r["files_changed"] == 1


def test_a_listing_at_github_s_limit_is_counted_as_code():
    r = fp.provenance(FORK, SHA, get=api({"main": [f"docs/p{i}.md" for i in range(fp.FILE_LIMIT)]}))
    assert r["truncated"] and r["kind"] == "code" and "limit" in fp.note(r)


def test_not_a_fork_and_nothing_known():
    assert fp.provenance(FORK, SHA, get=api({"main": []}, fork=False)) == {"is_fork": False}
    assert fp.note({"is_fork": False}) == "" and fp.note(None) == ""
    assert fp.provenance(FORK, SHA, get=lambda path, token: None) is None
    assert fp.provenance(FORK, "main", get=api({"main": []})) is None           # not a pinned commit
    assert fp.provenance(FORK, SHA, get=api({"main": None})) is None            # nothing comparable
