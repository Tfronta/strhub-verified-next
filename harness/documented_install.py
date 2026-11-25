"""The installation a README writes, transcribed literally. Never a recipe.

Profile `strhub-documented-install/1` admits the install commands a repository
document shows in its own code blocks, when every one of them is a plain,
whole command of a closed list: apt, conda/mamba, pip, setup.py, make, cmake,
configure, cargo, git submodule, mkdir and cd. They are executed in the order
written, in a constant base environment the evaluator declares upfront, and
nothing adaptive is added to them: no inferred package, option, compiler flag,
environment variable or second attempt.

What the evaluator provides as its constant baseline, and declares in full:

  - pinned Ubuntu 22.04 (`ubuntu:22.04@sha256:...`) with `DEBIAN_FRONTEND=noninteractive`,
    `APT::Get::Assume-Yes "true"`, `apt-get update`, and the fixed baseline
    packages `ca-certificates`, `curl`, `git`, `build-essential`, `python3`,
    `python3-pip`, `python3-venv` (no `cmake`, `pkg-config`, `python-is-python3`,
    `cargo`, `autoconf`, `automake`, `libtool` or tool-specific libraries);
  - pinned Miniforge (`Miniforge3-Linux-x86_64.sh` at a fixed version and
    verified SHA-256) added only when a documented command invokes conda/mamba;
  - git submodules are initialized ONLY when the documented procedure
    explicitly declares `git clone --recursive`/`--recurse-submodules` or
    `git submodule update`;
  - non-Debian/Ubuntu package managers (`yum`, `dnf`, `brew`) block automatic
    execution unless an explicit `apt`/`apt-get install` equivalent is
    documented alongside them;
  - a leading `sudo` is dropped (the build runs as root), and so are the
    `git clone` of this very repository and the `cd` into it: the build
    already stands in a checkout of the pinned commit;
  - the conda environment or virtualenv the block activates last stays active
    for the documented command.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re

PROFILE = "strhub-documented-install/1"
BASE_IMAGE = "ubuntu:22.04@sha256:b000e69a50ff940390233025e7a337fb8469b509e2334fa4d018ac30f3e18cdb"
MINIFORGE_VERSION = "26.9.4-2"
MINIFORGE_SHA256 = "bbaf16b3897da24c4be50315934ba74848f617b4495982841d6a0a60e0edbbdf"
MINIFORGE_URL = (
    f"https://github.com/conda-forge/miniforge/releases/download/"
    f"{MINIFORGE_VERSION}/Miniforge3-Linux-x86_64.sh"
)
BASELINE_PACKAGES = (
    "ca-certificates",
    "curl",
    "git",
    "build-essential",
    "python3",
    "python3-pip",
    "python3-venv",
)
ENVIRONMENT = {"source": "documented", "dockerfile": "Dockerfile", "os": ["ubuntu-22.04"]}
_IMG_SHORT = f"{BASE_IMAGE.split('@')[0]}@{BASE_IMAGE.split(':', 2)[2][:12]}"
BASE_PLAIN = (
    f"constant baseline {_IMG_SHORT}, noninteractive apt-get update, "
    + ", ".join(BASELINE_PACKAGES)
)
BASE_CONDA = BASE_PLAIN + f"; Miniforge {MINIFORGE_VERSION} ({MINIFORGE_SHA256[:12]})"

#: Headings under which a code block is read as installation.
SECTION = re.compile(r"install|build|compil|set ?up|requirement|prerequisite|dependenc|getting started|quick ?start|environment\b", re.I)
#: Headings that mention "install" but describe post-install checks, notes or removal.
_NON_INSTALL_HEADING = re.compile(r"\b(?:verif(?:y|ying|ication)|test(?:ing)?|uninstall|remov(?:e|ing)|troubleshoot|notes?|faq)\b", re.I)
#: A code line that is an installation step of some kind, admitted or not.
LOOKS_LIKE_INSTALL = re.compile(
    r"(?:^|[\s;&|=])(?:apt|apt-get|yum|dnf|brew|conda|mamba|pip3?|python3? -m pip|python3? -m venv|python3? setup\.py|make|cmake|\./configure|autoreconf|cargo|"
    r"wget|curl|tar|unzip|docker|git clone|git submodule|bash|sh|Rscript|nimble|go|source activate|(?:source|\.) \S+/bin/activate)(?:\s|$)")
#: Indented (non-fenced) blocks must start with an install command so tab-indented
#: prose paragraphs mentioning `apt-get` or `make` are not misread as shell blocks.
_LEADING_INSTALL = re.compile(
    r"^(?:apt|apt-get|yum|dnf|brew|conda|mamba|pip3?|python3? -m pip|python3? -m venv|python3? setup\.py|make|cmake|\./configure|autoreconf|cargo|"
    r"wget|curl|tar|unzip|docker|git clone|git submodule|bash|sh|Rscript|nimble|go|source activate|(?:source|\.) \S+/bin/activate)(?:\s|$)")
#: Documents whose filename identifies them as the repository's main or
#: installation documentation (checked before auxiliary docs like annotation guides).
_PRIMARY_INSTALL_DOC = re.compile(
    r"(?:^|/)(?:readme(?:\.[^/]+)?|\d*[-_ ]*(?:install(?:ation)?|build(?:ing)?|setup|getting[-_ ]?started|quick[-_ ]?start)[^/]*)$",
    re.I,
)
TOK = r"[\w./=:+,-]+"
#: A package, a channel, a path or a name: never an option. The options a
#: step may carry are the ones spelled out in its pattern, so nothing like
#: `--force-yes`, `--allow-unauthenticated` or `--fix-broken` gets through.
WORD = r"[A-Za-z0-9][\w./=:+,~-]*"
PATTERNS = [
    r"apt(?:-get)? update",
    rf"apt(?:-get)? install(?: (?:-y|--yes|--no-install-recommends))*(?: {WORD})+",
    rf"(?:conda|mamba) create(?: -y)? (?:-n|--name)[ =]{WORD}(?: (?:-y|-c {WORD}|{WORD}))*",
    rf"(?:conda|mamba) env create(?: (?:-n|--name|-f|--file)[ =]{WORD})+",
    rf"(?:conda|mamba) install(?: -y)?(?: (?:-c {WORD}|{WORD}))*(?: --file[ =]{WORD})?",
    rf"(?:conda|source) activate {WORD}",
    rf"python3? -m venv {WORD}",
    rf"(?:source|\.) {WORD}/bin/activate",
    r"(?:python3? -m )?pip3? install (?:--upgrade|-U) pip",
    r"(?:python3? -m )?pip3? --version",
    r"python3? --version",
    r"(?:python3? -m )?pip3? install(?: -e)? \.",
    rf"(?:python3? -m )?pip3? install -r {WORD}",
    r"python3? setup\.py install",
    r"make(?: -j ?\d+)?(?: install)?",
    rf"cmake(?: (?:-D{WORD}|\.\.?|\.\./{WORD}|{WORD}))+",
    rf"mkdir(?: -p)? {WORD}",
    rf"cd (?:\.\.|{WORD})",
    r"autoreconf(?: -[a-zA-Z]+)*",
    rf"\./configure(?: --{WORD})*",
    r"cargo build(?: --release)?(?: --locked)?",
    r"cargo install(?: --locked)? --path \.",
    rf"git submodule init(?: {WORD})*",
    rf"git submodule sync(?: --recursive)?(?: {WORD})*",
    rf"git submodule update(?: (?:--init|--recursive|-N|--depth \d+))*(?: --)?(?: {WORD})*",
]
ADMITTED = re.compile("|".join(f"(?:{p})" for p in PATTERNS))
USES_CONDA = re.compile(r"^(?:conda|mamba|source activate)\b")
_NON_UBUNTU_INSTALL = re.compile(rf"(?:yum|dnf|brew) install(?: (?:-y|--yes))*(?: {WORD})+")
#: A file a command reads, by the option that names it.
FILE_OPTION = re.compile(r"(?:^| )(?:-f|--file|-r)[ =](\S+)")


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


_STANDALONE_BACKTICK = re.compile(r"^(?:(?:[*+-]|\d+[.)])\s+)?`{1,3}([^`\s][^`]*\s[^`]*)`{1,3}$")


def _blocks(text: str) -> list[dict]:
    """Every code block of a document (fenced, indented, or standalone inline-code
    command lines), with the heading it sits under and the line of each of its rows."""
    out, heading, current, fence = [], "", None, None
    for number, row in enumerate(text.splitlines(), 1):
        marker = re.match(r"^\s*(`{3,}|~{3,})([^`]*)$", row)
        if fence:
            # Closed only by a fence of the same character, at least as long,
            # with nothing after it: a document quoted inside a longer fence
            # is one block of text, not a README of its own.
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= fence[1] and not marker[2].strip():
                fence, current = None, None
            else:
                current["rows"].append((number, row))
            continue
        m_bt = _STANDALONE_BACKTICK.match(row.strip())
        if m_bt:
            # Standalone inline-code line (`pip install -e .` or `- `apt install ...``):
            # treat as a code block row separate from surrounding indented list items.
            if current is None or current.get("indented"):
                current = {"heading": heading, "rows": [], "indented": False}
                out.append(current)
            current["rows"].append((number, m_bt.group(1).strip()))
            continue
        if marker:
            fence = (marker[1][0], len(marker[1]))
            current = {"heading": heading, "rows": [], "indented": False}
            out.append(current)
            continue
        if re.match(r"^#{1,6}\s", row):
            heading, current = row.strip(), None
            continue
        if row.startswith("    ") or row.startswith("\t"):
            if current is None or not current.get("indented"):
                current = {"heading": heading, "rows": [], "indented": True}
                out.append(current)
            current["rows"].append((number, row))
        elif row.strip():
            current = None
    return out


def _plain(row: str) -> str:
    """The command as typed: no prompt, no `sudo`, single spaces."""
    text = re.sub(r"^\$\s+", "", row.strip())
    text = re.sub(r"^sudo\s+", "", text)
    return " ".join(text.split())


_GITHUB_URL_RE = re.compile(
    r"^(?:https?://(?:www\.)?github\.com/|git@github\.com:)[\w.-]+/([\w.-]+?)(?:\.git)?/?$"
)
_TOK_RE = re.compile(rf"^{TOK}$")


def _classify_git_clone(command: str, name: str) -> str | None:
    """Classify a `git clone` command with closed safe flags.

    Returns `"given_submodules"` when cloning this repository with
    `--recursive` or `--recurse-submodules`, `"given"` when cloning it
    without submodule flags, `"outside"` when cloning another repository or
    using unsupported options, or `None` when `command` is not `git clone`.
    """
    tokens = command.split()
    if tokens[:2] != ["git", "clone"]:
        return None
    recursive = False
    positional: list[str] = []
    i = 2
    while i < len(tokens):
        tok = tokens[i]
        if tok in ("--recursive", "--recurse-submodules"):
            recursive = True
            i += 1
        elif tok in ("--shallow-submodules", "--single-branch", "-q", "--quiet"):
            i += 1
        elif tok in ("--branch", "-b"):
            if i + 1 >= len(tokens) or not _TOK_RE.fullmatch(tokens[i + 1]):
                return "outside"
            i += 2
        elif tok.startswith("--branch="):
            if not _TOK_RE.fullmatch(tok.split("=", 1)[1]):
                return "outside"
            i += 1
        elif tok == "--depth":
            if i + 1 >= len(tokens) or not tokens[i + 1].isdigit():
                return "outside"
            i += 2
        elif tok.startswith("--depth="):
            if not tok.split("=", 1)[1].isdigit():
                return "outside"
            i += 1
        elif tok.startswith("-"):
            return "outside"
        else:
            positional.append(tok)
            i += 1
    if not (1 <= len(positional) <= 2):
        return "outside"
    if len(positional) == 2 and not _TOK_RE.fullmatch(positional[1]):
        return "outside"
    m = _GITHUB_URL_RE.fullmatch(positional[0])
    if not m or m.group(1).lower() != name:
        return "outside"
    return "given_submodules" if recursive else "given"


def _kind(command: str, repo_slug: str) -> str:
    """`step` (admitted), `given` / `given_submodules` (already true of the
    checkout), `non_ubuntu_pkg` (`yum`/`dnf`/`brew` install requiring an
    explicit Debian/Ubuntu `apt` equivalent), `published` (installs a released
    copy, not this commit) or `outside`."""
    owner, name = repo_slug.lower().split("/")
    lowered = command.lower()
    # Cloning this project, over HTTPS or SSH, from wherever it lives today
    # (repositories move between owners and keep their name): the build
    # already stands in a checkout of the pinned commit.
    clone_kind = _classify_git_clone(command, name)
    if clone_kind is not None:
        return clone_kind
    if re.fullmatch(rf"cd {re.escape(name)}/?", lowered):
        return "given"
    # Non-Ubuntu OS package managers (CentOS yum/dnf, macOS brew) are never
    # silently discarded as "given": they block unless the document explicitly
    # provides an `apt` / `apt-get install` equivalent alongside them.
    if _NON_UBUNTU_INSTALL.fullmatch(command):
        return "non_ubuntu_pkg"
    # A bare self-invocation of the tool's own binary/script (with no args or
    # --help/--version) inside an install block is a usage check, not a build step.
    if re.fullmatch(
        rf"(?:python3? )?(?:\./)?{re.escape(name)}(?:\.py)?(?: (?:-h|--help|-v|--version))?",
        lowered,
    ):
        return "given"
    if re.match(r"docker (?:pull|run|build)\b", command):
        return "published"
    package = re.fullmatch(rf"(?:(?:python3? -m )?pip3? install|(?:conda|mamba) install(?: -y)?(?: -c {TOK})*) (\S+)", command)
    if package:
        pkg = package[1].lower()
        base = pkg.rsplit("/", 1)[-1]
        norm = name.replace("-", "_")
        if (pkg.split("=")[0].split("[")[0] == name
                or f"{owner}/{name}" in pkg
                or (base.endswith(".whl") and (base.startswith(f"{name}-") or base.startswith(f"{norm}-")))):
            return "published"
    return "step" if ADMITTED.fullmatch(command) else "outside"


def _steps(row: str) -> list[str]:
    """The commands of one line. `a && b` is two steps run in order, the
    second only if the first succeeded, which is what the transcript does
    with two lines; any other operator leaves the line whole, to be refused."""
    command = _plain(row)
    parts = [part.strip() for part in command.split(" && ")]
    return parts if len(parts) > 1 and all(part and not re.search(r"[;&|<>$`*?(){}\\]", part) for part in parts) else [command]


def _documents(proposal: dict) -> list[dict]:
    # A wiki is not versioned with the code, and a commented-out block is not
    # something the document shows its reader.
    return [d for d in proposal.get("source_documents") or []
            if d.get("origin") != "wiki" and isinstance(d.get("text"), str) and d.get("file")
            and "<!--" not in d["text"] and "-->" not in d["text"]]


def _scan_docs(docs: list[dict], slug: str) -> tuple[list[dict], list[dict], list[dict], bool, str | None]:
    """Scan a group of documents for installation blocks."""
    commands, published, scanned = [], [], []
    clone_submodules = False
    for doc in docs:
        scanned.append({"path": doc["file"], "sha256": digest(doc["text"])})
        doc_commands: list[dict] = []
        doc_non_ubuntu: list[tuple[int, str]] = []
        for block in _blocks(doc["text"]):
            if not SECTION.search(block["heading"]) or _NON_INSTALL_HEADING.search(block["heading"]):
                continue
            # An indented list (`* Python 2.7`) is prose, not a code block.
            if any(re.match(r"\s*(?:[*+-]|\d+[.)])\s", r) for _, r in block["rows"]):
                continue
            rows = [(n, step) for n, r in block["rows"] for step in _steps(r) if step and not step.startswith("#")]
            matcher = _LEADING_INSTALL.match if block.get("indented") else LOOKS_LIKE_INSTALL.search
            if not any(matcher(c) for _, c in rows):
                continue
            kinds = [_kind(c, slug) for _, c in rows]
            if "published" in kinds:
                # An alternative to building this commit: named, never run.
                published += [{"file": doc["file"], "line": n, "text": c}
                              for (n, c), k in zip(rows, kinds) if k == "published"]
                continue
            if "outside" in kinds:
                n, c = next((row for row, k in zip(rows, kinds) if k == "outside"))
                return commands, published, scanned, clone_submodules, (
                    f"An installation step is outside this profile ({doc['file']}, line {n}: `{c}`); "
                    "STRhub does not interpret, complete or skip it."
                )
            if "given_submodules" in kinds:
                clone_submodules = True
            doc_non_ubuntu += [(n, c) for (n, c), k in zip(rows, kinds) if k == "non_ubuntu_pkg"]
            doc_commands += [{"file": doc["file"], "line": n, "text": c, "argv": c.split()}
                             for (n, c), k in zip(rows, kinds) if k == "step"]
        if doc_non_ubuntu and not any(re.match(r"apt(?:-get)? install\b", c["text"]) for c in doc_commands):
            n, c = doc_non_ubuntu[0]
            return commands, published, scanned, clone_submodules, (
                f"An installation step uses a non-Debian/Ubuntu package manager with no documented apt equivalent "
                f"({doc['file']}, line {n}: `{c}`); STRhub does not translate or skip it."
            )
        commands += doc_commands
    return commands, published, scanned, clone_submodules, None


def discover(proposal: dict) -> dict:
    result = {"profile": PROFILE, "ready": False, "method": (proposal.get("build") or {}).get("method", "unknown"),
              "reason": "No repository document shows an installation this profile can transcribe literally; "
                        "no missing step, dependency or choice was supplied by STRhub.",
              # Whose the gap is when the plan is not ready: `commit` when the
              # documentation is what falls short of the guide (the author can
              # close it), `strhub` when it is a limit of this profile.
              "gap": "commit"}
    repo, ref = proposal.get("repo"), str(proposal.get("ref") or "")
    match = re.fullmatch(r"https://github\.com/([\w.-]+/[\w.-]+?)(?:\.git)?/?", str(repo or ""))
    if not match or not re.fullmatch(r"[0-9a-f]{40}", ref) or proposal.get("tree_truncated"):
        result["gap"] = "strhub"
        return result
    slug = match[1]
    files = set(proposal.get("tree_paths") or [])
    if ".dockerignore" in files:
        # The carrier copies the checkout whole; a .dockerignore would decide what it copies.
        result["reason"] = "The repository ships a .dockerignore, which would change what the evaluator's carrier copies."
        result["gap"] = "strhub"
        return result
    directories = {str(parent) for f in files for parent in pathlib.PurePosixPath(f).parents if str(parent) != "."}

    all_docs = _documents(proposal)
    if not all_docs:
        # Nothing was read: that is this evaluator's lack of evidence, not a gap in the documentation.
        result["gap"] = "strhub"
        return result
    primary_docs = [d for d in all_docs if _PRIMARY_INSTALL_DOC.search(d["file"])]
    other_docs = [d for d in all_docs if not _PRIMARY_INSTALL_DOC.search(d["file"])]

    commands, published, documents, clone_submodules, err = _scan_docs(primary_docs, slug)
    if err:
        result["reason"] = err
        return result
    if not commands and not published and other_docs:
        commands, published, other_scanned, clone_submodules, err = _scan_docs(other_docs, slug)
        documents += other_scanned
        if err:
            result["reason"] = err
            return result
    if not commands:
        return result
    builders = [
        c["text"] for c in commands
        if not re.match(
            r"(?:cd|mkdir|conda activate|source activate|(?:source|\.) \S+/bin/activate|"
            r"(?:python3? -m )?pip3? --version|python3? --version|git submodule (?:init|sync|update))\b",
            c["text"],
        )
    ]
    if len(set(builders)) != len(builders):
        result["reason"] = ("More than one installation is documented with the same steps; "
                            "STRhub does not choose between them.")
        return result

    # Every file and directory a step names is in the commit, from where the step stands.
    here, made = pathlib.PurePosixPath("."), set()
    venv_activate: str | None = None
    for c in commands:
        text = c["text"]
        named = [m[1] for m in FILE_OPTION.finditer(text)]
        step = re.fullmatch(r"(cd|mkdir(?: -p)?) (\S+)", text)
        if step:
            target = _resolve(here, step[2])
            if target is None:
                result["reason"] = f"An installation step leaves the repository ({c['file']}, line {c['line']}: `{text}`)."
                return result
            if step[1] == "cd":
                if str(target) != "." and str(target) not in directories and str(target) not in made:
                    result["reason"] = (f"An installation step enters a directory the commit does not hold "
                                        f"({c['file']}, line {c['line']}: `{text}`).")
                    return result
                here = target
            else:
                made.add(str(target))
            continue
        m_venv = re.fullmatch(r"python3? -m venv (\S+)", text)
        if m_venv:
            target = _resolve(here, m_venv[1])
            if target is None:
                result["reason"] = f"An installation step leaves the repository ({c['file']}, line {c['line']}: `{text}`)."
                return result
            made.add(str(target))
            continue
        m_act = re.fullmatch(r"(?:source|\.) (\S+)/bin/activate", text)
        if m_act:
            target = _resolve(here, m_act[1])
            if target is None:
                result["reason"] = f"An installation step leaves the repository ({c['file']}, line {c['line']}: `{text}`)."
                return result
            if str(target) != "." and str(target) not in directories and str(target) not in made:
                result["reason"] = (f"An installation step enters a directory the commit does not hold "
                                    f"({c['file']}, line {c['line']}: `{text}`).")
                return result
            venv_activate = f"/opt/tool/{target}/bin/activate"
            continue
        for name in named:
            target = _resolve(here, name)
            if target is None or str(target) not in files:
                result["reason"] = (f"An installation step reads a file the commit does not hold "
                                    f"({c['file']}, line {c['line']}: `{text}`).")
                return result

    uses_conda = any(USES_CONDA.match(c["text"]) for c in commands)
    submodules_documented = bool(
        clone_submodules or any(re.match(r"git submodule update\b", c["text"]) for c in commands)
    )
    activated = [c["argv"][-1] for c in commands if re.match(r"(?:conda|source) activate\b", c["text"])]
    environment = activated[-1] if activated else None
    dockerfile = carrier(commands, uses_conda, environment, venv_activate)
    base_desc = BASE_CONDA if uses_conda else BASE_PLAIN
    if submodules_documented:
        base_desc += "; git submodules"
    first = commands[0]
    result.pop("gap")
    result.update(
        ready=True, repo=repo, ref=ref, documents=documents, commands=commands,
        published_alternatives=published, conda_environment=environment,
        base_condition={
            "image": BASE_IMAGE,
            "description": base_desc,
            "role": "constant evaluator baseline",
            "baseline": {
                "env": {"DEBIAN_FRONTEND": "noninteractive"},
                "apt_assume_yes": True,
                "apt_update": True,
                "packages": list(BASELINE_PACKAGES),
                "miniforge": (
                    {"version": MINIFORGE_VERSION, "url": MINIFORGE_URL, "sha256": MINIFORGE_SHA256}
                    if uses_conda else None
                ),
            },
            "added_packages": list(BASELINE_PACKAGES),
            "miniforge": uses_conda,
            "submodules": submodules_documented,
        },
        citation={"repo": repo, "ref": ref, "path": first["file"], "line": first["line"],
                  "end_line": commands[-1]["line"], "verified": True,
                  "document_sha256": next(d["sha256"] for d in documents if d["path"] == first["file"])},
        carrier_dockerfile=dockerfile, carrier_sha256=digest(dockerfile),
        reason="Transcribe the installation commands the repository documents, unchanged and in order, "
               "into a constant evaluator baseline carrier; no adaptive step, dependency, option or choice was added.")
    return result


def _resolve(here: pathlib.PurePosixPath, name: str) -> pathlib.PurePosixPath | None:
    """`name` from `here`, inside the repository; None when it leaves it."""
    if name.startswith(("/", "~")):
        return None
    parts: list[str] = []
    for part in (here / name).parts:
        if part == "..":
            if not parts:
                return None
            parts.pop()
        elif part != ".":
            parts.append(part)
    return pathlib.PurePosixPath(*parts) if parts else pathlib.PurePosixPath(".")


def carrier(commands: list[dict], uses_conda: bool, environment: str | None,
            venv_activate: str | None = None) -> str:
    """The evaluator's envelope around the literal commands. Everything that
    is not one of them is the upfront-declared constant baseline."""
    lines = ["# Evaluator carrier: strhub-documented-install/1; not an upstream Dockerfile."]
    lines += base_lines(uses_conda)
    lines += ['COPY [".", "/opt/tool"]', "WORKDIR /opt/tool"]
    # One shell, so `cd`, `conda activate` and `source .../bin/activate` carry
    # from one documented line to the next as they would in the reader's
    # terminal; the first failure stops it.
    script = "set -eo pipefail\n" + "\n".join(c["text"] for c in commands) + "\n"
    lines.append("RUN " + json.dumps(["bash", "-lc", script]))
    if environment:
        lines.append("RUN " + json.dumps(["bash", "-c", f"echo 'conda activate {environment}' > /etc/profile.d/zz-strhub-env.sh"]))
    if venv_activate:
        lines.append("RUN " + json.dumps(["bash", "-c", f"echo 'source {venv_activate}' >> /etc/profile.d/zz-strhub-env.sh"]))
    lines.append('ENTRYPOINT ["/bin/bash", "-lc"]')
    return "\n".join(lines) + "\n"


def base_lines(uses_conda: bool) -> list[str]:
    """The constant, upfront-declared base environment every carrier starts from."""
    lines = [
        "FROM " + BASE_IMAGE,
        "ENV DEBIAN_FRONTEND=noninteractive",
        "RUN " + json.dumps([
            "bash", "-c",
            "echo 'APT::Get::Assume-Yes \"true\";' > /etc/apt/apt.conf.d/90strhub "
            "&& apt-get update "
            "&& apt-get install --no-install-recommends " + " ".join(BASELINE_PACKAGES),
        ]),
    ]
    if uses_conda:
        lines += [
            "RUN " + json.dumps([
                "bash", "-c",
                f"curl -fsSL {MINIFORGE_URL} -o /tmp/miniforge.sh && "
                f"echo '{MINIFORGE_SHA256}  /tmp/miniforge.sh' | sha256sum -c - && "
                "bash /tmp/miniforge.sh -b -p /opt/conda && rm /tmp/miniforge.sh && "
                # A login shell may reset PATH; conda stays on it either way.
                "echo 'export PATH=/opt/conda/bin:$PATH' > /etc/profile.d/00-strhub-conda.sh && "
                "ln -s /opt/conda/etc/profile.d/conda.sh /etc/profile.d/conda.sh",
            ]),
            "ENV PATH=/opt/conda/bin:$PATH",
        ]
    return lines


def installation(proposal: dict, manifest: dict) -> dict:
    result = discover(proposal)
    if manifest.get("environment") != ENVIRONMENT or manifest.get("source") != {
            "repo": proposal.get("repo"), "ref": proposal.get("ref")}:
        return {"profile": PROFILE, "ready": False, "method": result.get("method", "unknown"),
                "reason": "The effective manifest does not match the documented installation plan."}
    return result


def verify_checkout(root, install: dict) -> None:
    """Re-derive the plan from the actual source bytes, not a saved ready flag."""
    import _paths
    if not install.get("ready") or install.get("profile") != PROFILE:
        raise ValueError("no proven documented installation")
    root = pathlib.Path(root)
    documents = []
    for doc in install.get("documents") or []:
        path = _paths.confined(root, doc.get("path"))
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != doc.get("sha256"):
            raise ValueError(f"upstream evidence differs at pinned checkout: {doc.get('path')}")
        documents.append({"file": doc["path"], "origin": "repo", "text": raw.decode("utf-8")})
    tree = sorted(p.relative_to(root).as_posix() for p in root.rglob("*")
                  if ".git" not in p.relative_to(root).parts and (p.is_file() or p.is_symlink()))
    proposal = {"repo": install.get("repo"), "ref": install.get("ref"),
                "build": {"method": install.get("method")}, "tree_paths": tree, "source_documents": documents}
    if discover(proposal) != install:
        raise ValueError("documented installation plan does not match its upstream evidence")


def materialise(root, install: dict, destination) -> None:
    verify_checkout(root, install)
    with destination.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(install["carrier_dockerfile"])
    if hashlib.sha256(destination.read_bytes()).hexdigest() != install["carrier_sha256"]:
        raise ValueError("documented installation carrier digest mismatch")
