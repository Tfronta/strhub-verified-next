"""The installation a README writes, transcribed literally. Never a recipe.

Profile `strhub-documented-install/1` admits the install commands a repository
document shows in its own code blocks, when every one of them is a plain,
whole command of a closed list: apt, conda/mamba, pip, setup.py, make, cmake,
configure, cargo, mkdir and cd. They are executed in the order written, in a
fixed base environment the evaluator declares, and nothing is added to them:
no package, option, compiler flag, environment variable or second attempt.

What the evaluator does around them, and says it does:

  - the base is Ubuntu 22.04 with its package lists refreshed and apt set to
    answer yes; Miniforge (conda, python, pip) is added only when a command
    uses conda, pip or python; a minimal generic build toolchain
    (build-essential, git/ca-certificates, cmake, autotools/pkg-config, or
    cargo, each only when invoked without already being installed via apt)
    never includes tool-specific libraries;
  - when the repository declares `.gitmodules`, its pinned submodules are
    initialized during checkout;
  - a leading `sudo` is dropped (the build runs as root), and so are the
    `git clone` of this very repository and the `cd` into it: the build
    already stands in a checkout of the pinned commit;
  - the conda environment the block activates last stays active for the
    documented command.

What stays outside, and makes the plan not ready rather than approximate: a
command with shell operators, globs, variables or placeholders; a download; a
file the command names that the commit does not hold; and two
installations of which STRhub would have to pick one. A block that installs a
PUBLISHED copy of the tool (PyPI, Bioconda, a Docker image) is an alternative
to building this commit and is left out, by name, in the plan.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re

PROFILE = "strhub-documented-install/1"
BASE_IMAGE = "ubuntu:22.04"
MINIFORGE_URL = "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh"
ENVIRONMENT = {"source": "documented", "dockerfile": "Dockerfile", "os": ["ubuntu-22.04"]}
BASE_PLAIN = "Ubuntu 22.04, package lists refreshed, apt answering yes"
BASE_CONDA = BASE_PLAIN + ", plus Miniforge (conda, python, pip)"

#: Headings under which a code block is read as installation.
SECTION = re.compile(r"install|build|compil|set ?up|requirement|prerequisite|dependenc|getting started|quick ?start|environment\b", re.I)
#: Headings that mention "install" but describe post-install checks, notes or removal.
_NON_INSTALL_HEADING = re.compile(r"\b(?:verif(?:y|ying|ication)|test(?:ing)?|uninstall|remov(?:e|ing)|troubleshoot|notes?|faq)\b", re.I)
#: A code line that is an installation step of some kind, admitted or not.
LOOKS_LIKE_INSTALL = re.compile(
    r"(?:^|[\s;&|=])(?:apt|apt-get|conda|mamba|pip3?|python3? -m pip|python3? -m venv|python3? setup\.py|make|cmake|\./configure|autoreconf|cargo|"
    r"wget|curl|tar|unzip|docker|git clone|bash|sh|Rscript|nimble|go|source activate|(?:source|\.) \S+/bin/activate)(?:\s|$)")
#: Indented (non-fenced) blocks must start with an install command so tab-indented
#: prose paragraphs mentioning `apt-get` or `make` are not misread as shell blocks.
_LEADING_INSTALL = re.compile(
    r"^(?:apt|apt-get|conda|mamba|pip3?|python3? -m pip|python3? -m venv|python3? setup\.py|make|cmake|\./configure|autoreconf|cargo|"
    r"wget|curl|tar|unzip|docker|git clone|bash|sh|Rscript|nimble|go|source activate|(?:source|\.) \S+/bin/activate)(?:\s|$)")
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
]
ADMITTED = re.compile("|".join(f"(?:{p})" for p in PATTERNS))
USES_CONDA = re.compile(r"^(?:conda|mamba|source activate|pip3?|python3?)\b")
_USES_BUILD_ESSENTIAL = re.compile(r"^(?:make|\./configure|autoreconf|cmake)\b")
_USES_CMAKE = re.compile(r"^cmake\b")
_USES_AUTOTOOLS = re.compile(r"^(?:\./configure|autoreconf)\b")
_USES_CARGO = re.compile(r"^cargo\b")
_APT_INSTALL = re.compile(r"^apt(?:-get)? install\b(.*)$")
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


def _kind(command: str, repo_slug: str) -> str:
    """`step` (admitted), `given` (already true of the checkout), `published`
    (installs a released copy, not this commit) or `outside`."""
    owner, name = repo_slug.lower().split("/")
    lowered = command.lower()
    # Cloning this project, over HTTPS or SSH, from wherever it lives today
    # (repositories move between owners and keep their name): the build
    # already stands in a checkout of the pinned commit.
    clone = re.fullmatch(rf"git clone(?: (?:--branch|-b) {TOK})?(?: --single-branch)?(?: --depth \d+)? "
                         rf"(?:https://github\.com/|git@github\.com:)[\w.-]+/([\w.-]+?)(?:\.git)?/?(?: {TOK})?", command)
    if clone:
        return "given" if clone[1].lower() == name else "outside"
    if re.fullmatch(rf"cd {re.escape(name)}/?", lowered):
        return "given"
    # Non-Ubuntu OS package managers (CentOS yum/dnf, macOS brew) listed alongside
    # Ubuntu instructions do not apply to the declared Ubuntu 22.04 base image.
    if re.match(r"(?:yum|dnf|brew)\s+install\b", lowered):
        return "given"
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


def _has_compiler_and_make(apt_pkgs: set[str]) -> bool:
    if "build-essential" in apt_pkgs:
        return True
    has_make = "make" in apt_pkgs
    has_compiler = any(
        p in ("gcc", "g++", "clang") or p.startswith(("gcc-", "g++-", "clang-"))
        for p in apt_pkgs
    )
    return has_make and has_compiler


def _minimal_toolchain(commands: list[dict]) -> list[str]:
    """Generic compiler/build-system packages supplied only when a documented
    command invokes make, ./configure, autoreconf, cmake or cargo without an
    earlier apt install of them. Never includes tool-specific libraries."""
    apt_pkgs: set[str] = set()
    need_build_essential = False
    need_git = False
    need_ca = False
    need_cmake = False
    need_autotools = False
    need_cargo = False
    for cmd in commands:
        text = cmd["text"]
        apt_match = _APT_INSTALL.match(text)
        if apt_match:
            for tok in apt_match[1].split():
                if not tok.startswith("-"):
                    apt_pkgs.add(tok)
            continue
        if _USES_BUILD_ESSENTIAL.match(text):
            if not _has_compiler_and_make(apt_pkgs):
                need_build_essential = True
            if "git" not in apt_pkgs:
                need_git = True
            if "ca-certificates" not in apt_pkgs:
                need_ca = True
        if _USES_CMAKE.match(text) and "cmake" not in apt_pkgs:
            need_cmake = True
        if _USES_AUTOTOOLS.match(text):
            need_autotools = True
        if _USES_CARGO.match(text):
            if "cargo" not in apt_pkgs and "rustc" not in apt_pkgs:
                need_cargo = True
            if "ca-certificates" not in apt_pkgs:
                need_ca = True
    out: list[str] = []
    if need_build_essential:
        out.append("build-essential")
    if need_cmake:
        out.append("cmake")
    if need_autotools:
        for pkg in ("autoconf", "automake", "libtool", "pkg-config"):
            if pkg not in apt_pkgs:
                out.append(pkg)
    if need_cargo:
        out.append("cargo")
    if need_git:
        out.append("git")
    if need_ca:
        out.append("ca-certificates")
    return out


def _scan_docs(docs: list[dict], slug: str) -> tuple[list[dict], list[dict], list[dict], str | None]:
    """Scan a group of documents for installation blocks."""
    commands, published, scanned = [], [], []
    for doc in docs:
        scanned.append({"path": doc["file"], "sha256": digest(doc["text"])})
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
                return commands, published, scanned, (
                    f"An installation step is outside this profile ({doc['file']}, line {n}: `{c}`); "
                    "STRhub does not interpret, complete or skip it."
                )
            commands += [{"file": doc["file"], "line": n, "text": c, "argv": c.split()}
                         for (n, c), k in zip(rows, kinds) if k == "step"]
    return commands, published, scanned, None


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
    has_submodules = ".gitmodules" in files
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

    commands, published, documents, err = _scan_docs(primary_docs, slug)
    if err:
        result["reason"] = err
        return result
    if not commands and not published and other_docs:
        commands, published, other_scanned, err = _scan_docs(other_docs, slug)
        documents += other_scanned
        if err:
            result["reason"] = err
            return result
    if not commands:
        return result
    builders = [
        c["text"] for c in commands
        if not re.match(r"(?:cd|mkdir|conda activate|source activate|(?:source|\.) \S+/bin/activate|(?:python3? -m )?pip3? --version|python3? --version)\b", c["text"])
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
    toolchain = _minimal_toolchain(commands)
    activated = [c["argv"][-1] for c in commands if re.match(r"(?:conda|source) activate\b", c["text"])]
    environment = activated[-1] if activated else None
    dockerfile = carrier(commands, uses_conda, environment, toolchain, venv_activate)
    base_desc = BASE_CONDA if uses_conda else BASE_PLAIN
    if toolchain:
        base_desc += f", plus minimal build toolchain ({', '.join(toolchain)}; no tool-specific libraries)"
    if has_submodules:
        base_desc += ", with git submodules initialized"
    first = commands[0]
    result.pop("gap")
    result.update(
        ready=True, repo=repo, ref=ref, documents=documents, commands=commands,
        published_alternatives=published, conda_environment=environment,
        base_condition={"image": BASE_IMAGE, "description": base_desc,
                        "role": "evaluator base environment",
                        "added_packages": list(toolchain),
                        "miniforge": uses_conda,
                        "submodules": has_submodules},
        citation={"repo": repo, "ref": ref, "path": first["file"], "line": first["line"],
                  "end_line": commands[-1]["line"], "verified": True,
                  "document_sha256": next(d["sha256"] for d in documents if d["path"] == first["file"])},
        carrier_dockerfile=dockerfile, carrier_sha256=digest(dockerfile),
        reason="Transcribe the installation commands the repository documents, unchanged and in order, "
               "into a fixed evaluator carrier; no step, dependency, option or choice was added.")
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
            toolchain: list[str] | tuple[str, ...] = (),
            venv_activate: str | None = None) -> str:
    """The evaluator's envelope around the literal commands. Everything that
    is not one of them is the declared base environment."""
    lines = ["# Evaluator carrier: strhub-documented-install/1; not an upstream Dockerfile."]
    lines += base_lines(uses_conda, toolchain)
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


def base_lines(uses_conda: bool, toolchain: list[str] | tuple[str, ...] = ()) -> list[str]:
    """The declared base environment every carrier starts from."""
    lines = ["FROM " + BASE_IMAGE,
             "ENV DEBIAN_FRONTEND=noninteractive",
             "RUN " + json.dumps(["bash", "-c", "echo 'APT::Get::Assume-Yes \"true\";' > /etc/apt/apt.conf.d/90strhub "
                                              "&& apt-get update"])]
    if toolchain:
        lines.append("RUN " + json.dumps(["bash", "-c", "apt-get install --no-install-recommends " + " ".join(toolchain)]))
    if uses_conda:
        lines += ["RUN " + json.dumps(["bash", "-c", "apt-get install curl ca-certificates bzip2 && "
                                       f"curl -fsSL {MINIFORGE_URL} -o /tmp/miniforge.sh && "
                                       "bash /tmp/miniforge.sh -b -p /opt/conda && rm /tmp/miniforge.sh && "
                                       # A login shell may reset PATH; conda stays on it either way.
                                       "echo 'export PATH=/opt/conda/bin:$PATH' > /etc/profile.d/00-strhub-conda.sh && "
                                       "ln -s /opt/conda/etc/profile.d/conda.sh /etc/profile.d/conda.sh"]),
                  "ENV PATH=/opt/conda/bin:$PATH"]
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
