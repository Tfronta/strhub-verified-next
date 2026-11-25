"""The installation a README writes, transcribed literally, and nothing else.

`strhub-documented-install/1` runs the install commands a repository document
shows, in order, inside a base the evaluator declares. It adds no step,
package, option or choice; what it cannot transcribe literally it refuses,
and says which line."""
import pathlib

import pytest

import authorization
import documented_install as di
import fidelity
import prepare

ROOT = pathlib.Path(__file__).resolve().parents[2]
COMMAND = "tool --reads sample.bam --output result.vcf"


def proposal(install, usage=COMMAND, tree=("README.md", "environment.yml", "requirements.txt", "setup.py", "src/main.c")):
    text = "# Tool\n\n## Installation\n\n" + install + "\n\n## Usage\n\n```sh\n" + usage + "\n```\n"
    line = next(i for i, row in enumerate(text.splitlines(), 1) if row == usage)
    source = {"repo": "https://github.com/example/tool", "ref": "a" * 40}
    return {**source, "build": {"method": "conda", "file": "environment.yml"}, "tree_paths": list(tree),
            "tree_truncated": False, "source_documents": [{"file": "README.md", "origin": "readme", "text": text}],
            "commands": [{"cmd": usage, "file": "README.md", "line": line, "origin": "readme"}]}


def block(*lines):
    return "```bash\n" + "\n".join(lines) + "\n```"


CONDA = block("conda env create -f environment.yml", "conda activate tool", "pip install .")


def test_the_documented_commands_are_transcribed_unchanged_and_in_order():
    plan = di.discover(proposal(CONDA))
    assert plan["ready"] and plan["profile"] == di.PROFILE
    assert [c["text"] for c in plan["commands"]] == ["conda env create -f environment.yml", "conda activate tool", "pip install ."]
    assert [c["line"] for c in plan["commands"]] == [6, 7, 8] and plan["citation"]["line"] == 6
    carrier = plan["carrier_dockerfile"]
    assert carrier.startswith(f"# Evaluator carrier: strhub-documented-install/1; not an upstream Dockerfile.\nFROM {di.BASE_IMAGE}\n")
    assert "@sha256:" in di.BASE_IMAGE
    assert di.MINIFORGE_VERSION in di.MINIFORGE_URL and "latest" not in di.MINIFORGE_URL
    assert f"{di.MINIFORGE_SHA256}  /tmp/miniforge.sh' | sha256sum -c -" in carrier
    # The three lines, as written, in one shell that stops at the first failure.
    assert "set -eo pipefail\\nconda env create -f environment.yml\\nconda activate tool\\npip install .\\n" in carrier
    # The environment the block activates stays active for the documented command.
    assert plan["conda_environment"] == "tool" and "conda activate tool' > /etc/profile.d/zz-strhub-env.sh" in carrier
    assert carrier.rstrip().endswith('ENTRYPOINT ["/bin/bash", "-lc"]')
    assert "Miniforge" in plan["base_condition"]["description"]


def test_a_plain_build_gets_a_plain_base_and_nothing_it_did_not_ask_for():
    plan = di.discover(proposal(block("sudo apt install make g++ zlib1g-dev", "make")))
    assert plan["ready"]
    # `sudo` is dropped (the build runs as root); the packages are the README's.
    assert [c["text"] for c in plan["commands"]] == ["apt install make g++ zlib1g-dev", "make"]
    carrier = plan["carrier_dockerfile"]
    assert "miniforge" not in carrier.lower()
    assert plan["base_condition"]["added_packages"] == list(di.BASELINE_PACKAGES)
    for forbidden in ("cmake", "pkg-config", "python-is-python3", "cargo", "autoconf", "automake", "libtool"):
        assert forbidden not in carrier and forbidden not in plan["base_condition"]["added_packages"]
    assert "Miniforge" not in plan["base_condition"]["description"]


def test_cloning_this_repository_is_already_done_and_blocks_are_read_in_order():
    install = (block("apt install make g++") + "\n\nThen:\n\n"
               + block("git clone git@github.com:someone/Tool.git", "cd Tool", "mkdir build && cd build", "cmake ..", "make"))
    plan = di.discover(proposal(install))
    assert plan["ready"]
    assert [c["text"] for c in plan["commands"]] == ["apt install make g++", "mkdir build", "cd build", "cmake ..", "make"]


def test_a_published_copy_is_an_alternative_that_is_named_and_never_run():
    install = CONDA + "\n\nOr from PyPI:\n\n" + block("pip install tool") + "\n\nOr Docker:\n\n" + block("docker pull example/tool:latest")
    plan = di.discover(proposal(install))
    assert plan["ready"] and "pip install tool" not in plan["carrier_dockerfile"]
    assert [a["text"] for a in plan["published_alternatives"]] == ["pip install tool", "docker pull example/tool:latest"]


@pytest.mark.parametrize("lines,why", [
    (["apt install -y --force-yes make", "make"], "outside this profile"),
    (["make || true"], "outside this profile"),
    (["CXXFLAGS=-O0 make"], "outside this profile"),
    (["wget https://example.org/tool.tar.gz", "tar -xzf tool.tar.gz", "make"], "outside this profile"),
    (["curl https://example.org/install.sh | sh"], "outside this profile"),
    (["tar -xzvf Tool-X.X.tar.gz", "make"], "outside this profile"),
    (["cd tool*/src/ && make"], "outside this profile"),
    (["git clone https://github.com/other/dependency", "make"], "outside this profile"),
    (["pip install -r missing.txt"], "reads a file the commit does not hold"),
    (["conda env create -f envs/other.yml"], "reads a file the commit does not hold"),
    (["cd build", "make"], "enters a directory the commit does not hold"),
    (["cd ..", "make"], "leaves the repository"),
    (["make", "make"], "does not choose"),
])
def test_what_cannot_be_transcribed_literally_is_refused_and_named(lines, why):
    plan = di.discover(proposal(block(*lines)))
    assert not plan["ready"] and why in plan["reason"]
    assert "carrier_dockerfile" not in plan


@pytest.mark.parametrize("change", [
    lambda p: p["tree_paths"].append(".dockerignore"),
    lambda p: p.update(ref="main"),
    lambda p: p.update(tree_truncated=True),
    lambda p: p["source_documents"][0].update(origin="wiki"),
    lambda p: p["source_documents"][0].update(text="<!--\n" + p["source_documents"][0]["text"] + "\n-->"),
])
def test_evidence_that_is_not_a_pinned_plain_repository_document_admits_nothing(change):
    p = proposal(CONDA)
    change(p)
    assert not di.discover(p)["ready"]


def test_submodules_autotools_cargo_and_cleaner_doc_filtering():
    # Undocumented .gitmodules in the tree NEVER triggers automatic submodule rescue.
    p_sub = proposal(CONDA)
    p_sub["tree_paths"].append(".gitmodules")
    plan_sub = di.discover(p_sub)
    assert plan_sub["ready"]
    assert plan_sub["base_condition"]["submodules"] is False
    assert "submodules" not in plan_sub["base_condition"]["description"]

    # Documented `git clone --recursive` / `--recurse-submodules` and `git submodule update` ARE accepted.
    for clone_line in (
        "git clone --recursive https://github.com/example/tool.git",
        "git clone --recurse-submodules https://github.com/example/tool",
        "git clone -b v1.0 --recursive --depth 1 git@github.com:someone/Tool.git",
    ):
        p_rec = proposal(block(clone_line, "cd tool", "make"))
        p_rec["tree_paths"].append(".gitmodules")
        plan_rec = di.discover(p_rec)
        assert plan_rec["ready"], clone_line
        assert [c["text"] for c in plan_rec["commands"]] == ["make"]
        assert plan_rec["base_condition"]["submodules"] is True
        assert "git submodules" in plan_rec["base_condition"]["description"]

    for sub_cmds in (
        ["git clone https://github.com/example/tool.git", "cd tool", "git submodule update --init --recursive", "make"],
        ["git submodule init && git submodule update", "make"],
        ["git submodule update --recursive --init", "make"],
    ):
        p_exp = proposal(block(*sub_cmds))
        p_exp["tree_paths"].append(".gitmodules")
        plan_exp = di.discover(p_exp)
        assert plan_exp["ready"], sub_cmds
        assert plan_exp["base_condition"]["submodules"] is True

    # Autotools (./configure) and Cargo NEVER inject hidden adaptive packages (`autoconf`, `cargo`, `pkg-config`).
    plan_auto = di.discover(proposal(block("autoreconf -fi", "./configure", "make")))
    assert plan_auto["ready"]
    assert plan_auto["base_condition"]["added_packages"] == list(di.BASELINE_PACKAGES)
    for pkg in ("autoconf", "automake", "libtool", "pkg-config", "cargo", "python-is-python3", "cmake"):
        assert pkg not in plan_auto["carrier_dockerfile"]
        assert pkg not in plan_auto["base_condition"]["added_packages"]

    plan_cargo = di.discover(proposal(block("cargo build --release")))
    assert plan_cargo["ready"]
    assert plan_cargo["base_condition"]["added_packages"] == list(di.BASELINE_PACKAGES)
    assert "apt-get install" in plan_cargo["carrier_dockerfile"]
    for pkg in ("cargo", "rustc", "autoconf", "automake", "libtool", "python-is-python3", "cmake", "pkg-config"):
        # `cargo` appears only in the literal author command `cargo build --release`, never in `apt-get install`.
        apt_line = next(l for l in plan_cargo["carrier_dockerfile"].splitlines() if "apt-get install" in l)
        assert pkg not in apt_line
        assert pkg not in plan_cargo["base_condition"]["added_packages"]

    # Non-Ubuntu package managers (`brew`, `yum`, `dnf`) are NEVER silently discarded as "given".
    for pm_cmd in ("brew install htslib", "yum install zlib-devel", "dnf install zlib-devel"):
        assert di._kind(pm_cmd, "example/tool") != "given"
        plan_pm_only = di.discover(proposal(block(pm_cmd, "make")))
        assert not plan_pm_only["ready"], pm_cmd
        assert "no documented apt equivalent" in plan_pm_only["reason"]

    # Tab-indented prose paragraph mentioning apt-get or yum is ignored, not rejected.
    prose = "\tIf you are on Linux you can use apt-get or yum to get g++.\n\n" + block("make")
    plan_prose = di.discover(proposal(prose))
    assert plan_prose["ready"] and [c["text"] for c in plan_prose["commands"]] == ["make"]

    # Bare self-invocation (./tool.py) inside an install block is treated as a usage check.
    plan_self = di.discover(proposal(block("conda env create -f environment.yml", "conda activate tool", "./tool.py")))
    assert plan_self["ready"]
    assert [c["text"] for c in plan_self["commands"]] == ["conda env create -f environment.yml", "conda activate tool"]

    # Auxiliary doc (documentation/08_Annotation.md) does not poison a valid install doc.
    p_aux = proposal(block("make"))
    p_aux["source_documents"].append({
        "file": "documentation/08_Annotation.md",
        "origin": "repo",
        "text": "# Annotate\n\n## Setup ANNOVAR\n\n```bash\ntar xvfz annovar.latest.tar.gz\n```\n",
    })
    plan_aux = di.discover(p_aux)
    assert plan_aux["ready"] and [c["text"] for c in plan_aux["commands"]] == ["make"]

    # Standard Python venv + wheel alternative + Installation Verification section.
    venv_install = (
        block("python3 -m venv tool-env", "source tool-env/bin/activate", "python -m pip --version")
        + "\n\n### Install from wheel\n\n"
        + block("pip install ./tool-1.0.0-py3-none-any.whl")
        + "\n\n### Install from source\n\n"
        + block("python -m pip install .")
        + "\n\n## Installation Verification\n\n"
        + block("tar -xzf verify.tar.gz")
    )
    plan_venv = di.discover(proposal(venv_install))
    assert plan_venv["ready"]
    assert [c["text"] for c in plan_venv["commands"]] == [
        "python3 -m venv tool-env",
        "source tool-env/bin/activate",
        "python -m pip --version",
        "python -m pip install .",
    ]
    assert [a["text"] for a in plan_venv["published_alternatives"]] == ["pip install ./tool-1.0.0-py3-none-any.whl"]
    assert "source /opt/tool/tool-env/bin/activate' >> /etc/profile.d/zz-strhub-env.sh" in plan_venv["carrier_dockerfile"]
    # Plain venv/pip without Conda uses Ubuntu 22.04 native python3 (3.10), not Miniforge, and NEVER python-is-python3.
    assert plan_venv["base_condition"]["miniforge"] is False
    assert "miniforge" not in plan_venv["carrier_dockerfile"].lower()
    assert plan_venv["base_condition"]["added_packages"] == list(di.BASELINE_PACKAGES)
    assert "python-is-python3" not in plan_venv["carrier_dockerfile"]
    assert "python-is-python3" not in plan_venv["base_condition"]["added_packages"]


def test_prose_lists_and_usage_blocks_are_not_installation():
    install = "Requirements:\n\n    * Python 3\n    * make\n\n" + block("make")
    plan = di.discover(proposal(install))
    assert plan["ready"] and [c["text"] for c in plan["commands"]] == ["make"]
    # A block under a heading that is not about installing is not read at all.
    p = proposal("Nothing to install.")
    assert not di.discover(p)["ready"]


def _manifest(p):
    return {"tool": {"name": "Tool", "version": "test"}, "source": {"repo": p["repo"], "ref": p["ref"]},
            "environment": dict(di.ENVIRONMENT), "inputs": {"type": "illumina-bam-hg38"},
            "run": {"cmd": prepare.example_wrapper(fidelity.rewrite(COMMAND, "illumina-bam-hg38")["command"], ".")},
            "outputs": [{"path": "result.vcf", "format": "vcf", "min_records": 1}]}


def test_the_review_admits_it_and_the_checkout_is_held_to_it(tmp_path):
    p = proposal(CONDA)
    m = _manifest(p)
    review = authorization.prepare_review(p, m, [], [])
    assert review["install_ready"] and review["may_say_runs"], review["reason"]
    assert review["installation"]["profile"] == di.PROFILE
    for name in p["tree_paths"]:
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(p["source_documents"][0]["text"] if name == "README.md" else "x\n")
    fidelity.verify_checkout(tmp_path, review, m)
    target = tmp_path.parent / "carrier.Dockerfile"
    di.materialise(tmp_path, review["installation"], target)
    assert target.read_text() == review["installation"]["carrier_dockerfile"]
    # A Dockerfile the author ships sits in the checkout and is never what is built.
    (tmp_path / "Dockerfile").write_text("FROM attacker\n")
    fidelity.verify_checkout(tmp_path, review, m)
    assert "attacker" not in review["installation"]["carrier_dockerfile"]
    # The document changed after the review: the build does not happen.
    (tmp_path / "README.md").write_text(p["source_documents"][0]["text"].replace("pip install .", "pip install . --pre"))
    with pytest.raises(ValueError, match="evidence differs"):
        fidelity.verify_checkout(tmp_path, review, m)


def test_a_file_the_install_names_that_vanished_from_the_checkout_stops_the_build(tmp_path):
    p = proposal(CONDA)
    m = _manifest(p)
    review = authorization.prepare_review(p, m, [], [])
    (tmp_path / "README.md").write_text(p["source_documents"][0]["text"])
    with pytest.raises(ValueError, match="does not match"):
        fidelity.verify_checkout(tmp_path, review, m)
