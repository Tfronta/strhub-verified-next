"""Deterministic, tool-agnostic Track 2 ("Runs with adjustments") remediation.

ARCHITECTURAL INVARIANTS (ENFORCED BY `tests/test_no_forcing_guardrails.py`):
  1. ZERO AD-HOC / PER-TOOL LOGIC: Never branch on tool name, slug, author, or
     repository URL. Every rule below triggers solely on generic, observable
     structural facts (compiler/linker/pip diagnostics, standard root packaging
     manifests, `.gitmodules`, or single positional read-file tokens).
  2. ZERO SOURCE CODE MODIFICATION: The upstream checkout is NEVER edited or
     patched, and is mounted strictly read-only (`:/app:ro`) at runtime. Tools
     that require editing source files or custom config templates belong to
     Manual Verification (Level 2).
  3. STRICT TRACK SEPARATION: Track 1's `gates`, `verdict`, and `procedure_review`
     are NEVER mutated. Track 2 runs at most once (`MAX_ASSISTED_ATTEMPTS == 1`)
     in an isolated `work/assisted/` workspace and records its full delta under
     `assisted_run` so reviewers, users, and authors see both what failed
     literally and the exact adjustments that make the commit run.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import shutil
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import datasets as datasets_lib  # noqa: E402
import diagnose_log  # noqa: E402
import documented_install  # noqa: E402
import fidelity  # noqa: E402
import input_provenance  # noqa: E402
from prepare import example_wrapper, unwrap_example  # noqa: E402

SCHEMA = "strhub-assisted-remediation/1"
MAX_ASSISTED_ATTEMPTS = 1
ROOT = pathlib.Path(__file__).resolve().parent.parent

#: Closed generic table mapping missing standard build executables in Ubuntu 22.04
#: to their canonical Debian/Ubuntu apt package names.
_CMD_TO_APT: dict[str, tuple[str, ...]] = {
    "cmake": ("cmake",),
    "autoreconf": ("autoconf", "automake", "libtool", "pkg-config"),
    "aclocal": ("autoconf", "automake", "libtool"),
    "autoconf": ("autoconf", "automake", "libtool"),
    "automake": ("autoconf", "automake", "libtool"),
    "libtoolize": ("libtool",),
    "libtool": ("libtool",),
    "pkg-config": ("pkg-config",),
    "cargo": ("cargo",),
    "rustc": ("cargo",),
}

#: Standard Ubuntu 22.04 C/C++ build toolchain & compression/TLS/unit-test `-dev`
#: headers. Because `make` / `./configure` / `cmake` abort at the FIRST missing
#: executable or header (`autoreconf` -> `zlib.h` -> `bzlib.h` -> `lzma.h` ->
#: `curl/curl.h` -> `cmake` -> `GTest`), a single-pass (`MAX_ASSISTED_ATTEMPTS == 1`)
#: native C/C++ build supplies this standard Debian/Ubuntu C/C++ bundle together.
_STANDARD_NATIVE_CPP_APT: tuple[str, ...] = (
    "cmake",
    "autoconf",
    "automake",
    "libtool",
    "pkg-config",
    "zlib1g-dev",
    "libbz2-dev",
    "liblzma-dev",
    "libcurl4-openssl-dev",
    "libssl-dev",
    "libgtest-dev",
)
_NATIVE_BUILD_CMD_RE = re.compile(r"\b(?:make|cmake|autoreconf|autoconf|configure|g\+\+|gcc|clang\+\+)\b")
_GIT_SSH_LOG_RE = re.compile(
    r"(?:git@github\.com:|Permission denied \(publickey\)|Host key verification failed)",
    re.I,
)

#: Closed generic table mapping missing C/C++ headers, CMake Find modules, or
#: linker flags in `log_build.txt` to standard Ubuntu 22.04 `-dev` packages.
_BUILD_LOG_APT_RULES: tuple[tuple[re.Pattern[str], tuple[str, ...], str], ...] = (
    (re.compile(r"(?:zlib\.h:\s*No such file|Could NOT find ZLIB|cannot find -lz\b)", re.I),
     ("zlib1g-dev",), "zlib development headers (`zlib1g-dev`)"),
    (re.compile(r"(?:bzlib\.h:\s*No such file|Could NOT find BZip2|cannot find -lbz2\b)", re.I),
     ("libbz2-dev",), "bzip2 development headers (`libbz2-dev`)"),
    (re.compile(r"(?:lzma\.h:\s*No such file|Could NOT find LibLZMA|cannot find -llzma\b)", re.I),
     ("liblzma-dev",), "LZMA/xz development headers (`liblzma-dev`)"),
    (re.compile(r"(?:curl/curl\.h:\s*No such file|Could NOT find CURL|cannot find -lcurl\b)", re.I),
     ("libcurl4-openssl-dev",), "libcurl development headers (`libcurl4-openssl-dev`)"),
    (re.compile(r"(?:htslib/\w+\.h:\s*No such file|cannot find -lhts\b)", re.I),
     ("libhts-dev",), "HTSlib development headers (`libhts-dev`)"),
    (re.compile(r"(?:openssl/\w+\.h:\s*No such file|Could NOT find OpenSSL|cannot find -l(?:ssl|crypto)\b)", re.I),
     ("libssl-dev",), "OpenSSL development headers (`libssl-dev`)"),
    (re.compile(r"(?:(?:n?curses)\.h:\s*No such file|cannot find -l(?:n?cursesw?)\b)", re.I),
     ("libncurses5-dev",), "ncurses development headers (`libncurses5-dev`)"),
)

_SAFE_REL_SUBDIR = re.compile(r"^[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*$")


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in items:
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out


def _assisted_rewrite_command(
    raw_cmd: str,
    input_type: str | None,
    regions: str | None,
    *,
    tree_paths: set[str] | None = None,
    repo_url: str = "",
) -> tuple[str, str | None, list[dict]]:
    """Apply generic CLI adjustments (parent-folder prefix resolution, `key=file`
    input/regions/reference bindings, and single- or multi-sample positional read
    collapsing) when the strict profile left inputs unsubstituted."""
    eff_regions = regions
    adjustments: list[dict] = []
    if not input_type or not raw_cmd or raw_cmd.strip().startswith("true"):
        return raw_cmd, eff_regions, adjustments

    ds = datasets_lib.resolve(input_type)
    canonical = (ds or {}).get("canonical_input")
    if not canonical:
        return raw_cmd, eff_regions, adjustments

    working_cmd = raw_cmd

    # Pre-step 1: strip trailing variadic ellipsis marker (`...` or `…`)
    m_ell = re.search(r"\s+(\.\.\.|…)\s*$", working_cmd)
    if m_ell:
        tok_ell = m_ell.group(1)
        working_cmd = working_cmd[:m_ell.start()].rstrip()
        adjustments.append({
            "rule_id": "positional_reads_arg",
            "category": "cli_invocation",
            "what_failed_strict": f"The documented command ends with a variadic ellipsis marker (`{tok_ell}`).",
            "adjustment_applied": f"Removed trailing `{tok_ell}` synopsis marker for single-sample execution.",
            "author_fix": "Provide a concrete copy-pasteable single-sample command without ellipsis markers in README.md.",
        })

    # Pre-step 2: resolve `<repo_dir>/...` parent-directory prefix when `<repo_dir>` is the
    # cloned repository's own folder name and does not exist as a subfolder inside the tree.
    repo_clean = (repo_url or "").rstrip("/")
    repo_dir = repo_clean.rsplit("/", 1)[-1].removesuffix(".git") if "/" in repo_clean else ""
    if repo_dir and tree_paths:
        top_entries = {p.split("/", 1)[0] for p in tree_paths if p}
        if repo_dir not in top_entries:
            try:
                _probe_toks = fidelity.tokens(working_cmd)
            except ValueError:
                _probe_toks = []
            if _probe_toks:
                prefix_changes: list[tuple[int, int, str, str]] = []
                for idx, m in enumerate(fidelity.TOKEN.finditer(working_cmd)):
                    raw_t = m.group()
                    if (m.start() and not working_cmd[m.start() - 1].isspace()) or (
                        m.end() < len(working_cmd) and not working_cmd[m.end()].isspace()
                    ):
                        continue
                    q = raw_t[0] if len(raw_t) > 1 and raw_t[0] == raw_t[-1] and raw_t[0] in "'\"" else ""
                    val = raw_t[1:-1] if q else raw_t
                    if val.startswith(f"{repo_dir}/"):
                        rest = val[len(repo_dir) + 1:]
                        if rest and rest.split("/", 1)[0] in top_entries:
                            new_val = f"./{rest}" if idx == 0 else rest
                            repl = f"{q}{new_val}{q}" if q else new_val
                            prefix_changes.append((m.start(), m.end(), raw_t, repl))
                if prefix_changes:
                    for st_i, en_i, _, repl in reversed(prefix_changes):
                        working_cmd = working_cmd[:st_i] + repl + working_cmd[en_i:]
                    examples_str = ", ".join(f"`{orig}`" for _, _, orig, _ in prefix_changes[:2])
                    adjustments.append({
                        "rule_id": "repo_root_prefix",
                        "category": "cli_invocation",
                        "what_failed_strict": (
                            f"Command paths ({examples_str}) prefix the parent folder `{repo_dir}/`, "
                            "assuming invocation from one directory above `git clone`."
                        ),
                        "adjustment_applied": (
                            f"Resolved `{repo_dir}/...` paths relative to the cloned repository root."
                        ),
                        "author_fix": (
                            f"Write paths relative to the repository root after `cd {repo_dir}` in README.md."
                        ),
                    })

    strict_rw = fidelity.rewrite(working_cmd, input_type, regions=eff_regions, one_sample=False)
    if f"/data/in/{canonical}" in strict_rw["command"] and not strict_rw["limitations"]:
        return strict_rw["command"], eff_regions, adjustments

    # Case 5a: comma-separated sample list (`--bams a.bam,b.bam`) collapsed via one_sample=True
    one_rw = fidelity.rewrite(working_cmd, input_type, regions=eff_regions, one_sample=True)
    if f"/data/in/{canonical}" in one_rw["command"] and not one_rw["limitations"]:
        adjustments.append({
            "rule_id": "positional_reads_arg",
            "category": "cli_invocation",
            "what_failed_strict": "The documented command passes a multi-sample comma-separated input list.",
            "adjustment_applied": f"Collapsed the multi-sample input list to the single reference sample `/data/in/{canonical}`.",
            "author_fix": "Include a single-sample invocation example in README.md alongside multi-sample syntax.",
        })
        return one_rw["command"], eff_regions, adjustments

    base_cmd = one_rw["command"]

    def _read_kind(p: str) -> str:
        if re.search(r"\.f(?:ast)?q(?:\.gz)?$", p, re.I):
            return "fastq"
        if re.search(r"\.cram(?:\.gz)?$", p, re.I):
            return "cram"
        return "bam"

    # Case 5b-equals: `key=file` / `--flag=file` (`=`-joined) read, reference, or regions file parameters
    try:
        _eq_toks = fidelity.tokens(base_cmd)
    except ValueError:
        return base_cmd, eff_regions, adjustments

    eq_changes: list[tuple[int, int, str]] = []
    has_read_bound = f"/data/in/{canonical}" in base_cmd
    has_ref_bound = "/data/ref/" in base_cmd
    has_reg_bound = "/data/in/regions" in base_cmd
    ref_mount = ((ds or {}).get("reference_genome") or {}).get("mount_path")

    for idx, m in enumerate(fidelity.TOKEN.finditer(base_cmd)):
        if idx == 0:
            continue
        raw_tok = m.group()
        if (m.start() and not base_cmd[m.start() - 1].isspace()) or (
            m.end() < len(base_cmd) and not base_cmd[m.end()].isspace()
        ):
            continue
        oq = raw_tok[0] if len(raw_tok) > 1 and raw_tok[0] == raw_tok[-1] and raw_tok[0] in "'\"" else ""
        val = raw_tok[1:-1] if oq else raw_tok
        if "=" not in val:
            continue
        lhs, rhs = val.split("=", 1)
        rq = rhs[0] if len(rhs) > 1 and rhs[0] == rhs[-1] and rhs[0] in "'\"" else ""
        rval = rhs[1:-1] if rq else rhs
        if not lhs or not rval or rval.startswith("/data/") or re.search(r"\bpath/to/", rval, re.I):
            continue
        if re.search(r"(?:^|[-_])out(?:put|dir|_dir|-dir|_prefix|-prefix)?$", lhs, re.I):
            continue

        new_rval: str | None = None
        if (
            not has_read_bound
            and fidelity.READ_PATH.fullmatch(rval)
            and _read_kind(rval) == _read_kind(canonical)
            and rval.endswith(".gz") == canonical.endswith(".gz")
        ):
            new_rval = f"/data/in/{canonical}"
            has_read_bound = True
            adjustments.append({
                "rule_id": "equals_file_arg",
                "category": "cli_invocation",
                "what_failed_strict": f"Parameter `{raw_tok}` uses `=`-joined syntax outside the literal flag table.",
                "adjustment_applied": f"Bound `{lhs}` to reference sample `{new_rval}`.",
                "author_fix": "Include a space-separated CLI flag example or small sample file in README.md.",
            })
        elif (
            not has_ref_bound
            and ref_mount
            and fidelity.REFERENCE_PATH.fullmatch(rval)
            and not (
                (ds or {}).get("reference") == "hg38"
                and re.search(r"(?:hg19|grch37|b37|hs37d5)(?![a-z0-9])", rval, re.I)
            )
        ):
            new_rval = ref_mount
            has_ref_bound = True
            adjustments.append({
                "rule_id": "equals_file_arg",
                "category": "cli_invocation",
                "what_failed_strict": f"Reference parameter `{raw_tok}` uses `=`-joined syntax outside the literal flag table.",
                "adjustment_applied": f"Bound `{lhs}` to the public GRCh38 reference genome.",
                "author_fix": "Document standard reference flags (e.g. `--fasta hg38.fa`) in README.md.",
            })
        elif (
            not has_reg_bound
            and re.fullmatch(r"[\w./-]+\.bed", rval, re.I)
            and rval not in (tree_paths or set())
        ):
            cand_reg = eff_regions or ("bed4" if "bed4" in ((ds or {}).get("regions") or {}) else None)
            reg_src = ((ds or {}).get("regions") or {}).get(cand_reg or "")
            if reg_src and cand_reg:
                new_rval = "/data/in/regions" + pathlib.PurePosixPath(reg_src).suffix
                eff_regions = cand_reg
                has_reg_bound = True
                adjustments.append({
                    "rule_id": "equals_file_arg",
                    "category": "cli_invocation",
                    "what_failed_strict": (
                        f"Parameter `{raw_tok}` references an external `.bed` file `{rval}` not shipped in the commit."
                    ),
                    "adjustment_applied": f"Bound `{lhs}` to STRhub's public reference panel `{new_rval}`.",
                    "author_fix": f"Ship a small example `.bed` file in the repository or document standard `--regions` flags.",
                })

        if new_rval is not None:
            rebuilt = f"{lhs}={rq}{new_rval}{rq}" if rq else f"{lhs}={new_rval}"
            repl = f"{oq}{rebuilt}{oq}" if oq else rebuilt
            eq_changes.append((m.start(), m.end(), repl))

    if eq_changes:
        for st_i, en_i, repl in reversed(eq_changes):
            base_cmd = base_cmd[:st_i] + repl + base_cmd[en_i:]

    if f"/data/in/{canonical}" in base_cmd:
        return base_cmd, eff_regions, adjustments

    # Case 5b-positional: 1 or 2+ homogeneous positional read-file tokens (`tool sample.bam` or `tool s1.bam s2.bam`)
    try:
        toks = fidelity.tokens(base_cmd)
    except ValueError:
        return base_cmd, eff_regions, adjustments

    positional_matches: list[tuple[int, int, str, str]] = []
    for idx, m in enumerate(fidelity.TOKEN.finditer(base_cmd)):
        if idx == 0:
            continue
        raw_tok = m.group()
        if (m.start() and not base_cmd[m.start() - 1].isspace()) or (
            m.end() < len(base_cmd) and not base_cmd[m.end()].isspace()
        ):
            continue
        val = raw_tok[1:-1] if len(raw_tok) > 1 and raw_tok[0] == raw_tok[-1] and raw_tok[0] in "'\"" else raw_tok
        prev = toks[idx - 1] if idx else ""
        if prev in fidelity.OUTPUT_FLAGS or val.startswith("/data/"):
            continue
        if fidelity.READ_PATH.fullmatch(val) and _read_kind(val) == _read_kind(canonical) and val.endswith(".gz") == canonical.endswith(".gz"):
            positional_matches.append((m.start(), m.end(), raw_tok, val))

    if len(positional_matches) == 1:
        start, end, orig_tok, _ = positional_matches[0]
        target = f"/data/in/{canonical}"
        repl = orig_tok[0] + target + orig_tok[-1] if orig_tok[0] in "'\"" else target
        rewritten = base_cmd[:start] + repl + base_cmd[end:]
        adjustments.append({
            "rule_id": "positional_reads_arg",
            "category": "cli_invocation",
            "what_failed_strict": (
                f"Positional read-file argument `{orig_tok}` has no explicit input flag, "
                "so the literal profile refused to guess it."
            ),
            "adjustment_applied": f"Bound positional read-file token `{orig_tok}` to `{target}`.",
            "author_fix": (
                "Document an explicit input flag (e.g. `--bam` / `-i`) if supported, or ship a small "
                f"example file at `{orig_tok}` in the repository so the documented command runs verbatim."
            ),
        })
        return rewritten, eff_regions, adjustments

    if len(positional_matches) >= 2:
        is_paired_mates = _read_kind(canonical) == "fastq" and any(
            re.search(r"(?:_R?[12])\.(?:f(?:ast)?q)(?:\.gz)?$", v, re.I)
            for _, _, _, v in positional_matches
        )
        if not is_paired_mates:
            target = f"/data/in/{canonical}"
            rewritten = base_cmd
            for st_i, en_i, _, _ in reversed(positional_matches[1:]):
                cut_start = st_i - 1 if st_i > 0 and rewritten[st_i - 1] == " " else st_i
                rewritten = rewritten[:cut_start] + rewritten[en_i:]
            start0, end0, orig0, _ = positional_matches[0]
            repl0 = orig0[0] + target + orig0[-1] if orig0[0] in "'\"" else target
            rewritten = rewritten[:start0] + repl0 + rewritten[end0:]
            orig_list = " ".join(t for _, _, t, _ in positional_matches)
            adjustments.append({
                "rule_id": "positional_reads_arg",
                "category": "cli_invocation",
                "what_failed_strict": (
                    f"The documented command lists multiple positional sample files (`{orig_list}`), "
                    "which cannot map directly to one single-sample reference slice."
                ),
                "adjustment_applied": (
                    f"Collapsed multi-sample positional arguments (`{orig_list}`) to `{target}`."
                ),
                "author_fix": "Include a single-sample invocation example in README.md alongside multi-sample syntax.",
            })
            return rewritten, eff_regions, adjustments

    return base_cmd, eff_regions, adjustments


def _output_parent_dirs(unwrapped_cmd: str) -> list[str]:
    """Detect relative parent directories written by explicit output flags or
    shell `>` redirection so Track 2 can pre-create them with `mkdir -p`."""
    try:
        toks = fidelity.tokens(unwrapped_cmd)
    except ValueError:
        return []
    dirs: list[str] = []
    for i, raw in enumerate(toks):
        prev = toks[i - 1] if i else ""
        val = raw[1:-1] if len(raw) > 1 and raw[0] == raw[-1] and raw[0] in "'\"" else raw
        if val.startswith(("/", "-", "<")) or ".." in val.split("/"):
            continue
        if prev in ("--out-dir", "--outdir", "--working_path", "--working-path"):
            clean = val.strip("/")
            if clean and _SAFE_REL_SUBDIR.fullmatch(clean):
                dirs.append(clean)
        elif prev in fidelity.OUTPUT_FLAGS or prev == ">":
            parent = str(pathlib.PurePosixPath(val).parent)
            if parent and parent != "." and _SAFE_REL_SUBDIR.fullmatch(parent):
                dirs.append(parent)
    return _dedupe(dirs)


def needs_reference_genome(proposal: dict | None, manifest: dict | None) -> dict | None:
    """Return the dataset's `reference_genome` metadata when a potential Track 2
    assisted command references hg38 / a FASTA mount even though Track 1's
    `procedure_ready` was False (allowing `verify.yml` to cache/stage `work/ref`)."""
    if not isinstance(manifest, dict):
        return None
    inputs = manifest.get("inputs") or {}
    input_type = inputs.get("type")
    if not input_type:
        return None
    ds = datasets_lib.resolve(input_type)
    if not ds:
        return None
    raw_cmd, _ = unwrap_example((manifest.get("run") or {}).get("cmd") or "")
    tree_paths = set((proposal or {}).get("tree_paths") or [])
    repo_url = (manifest.get("source") or {}).get("repo") or (proposal or {}).get("repo") or ""
    candidate_cmd, _, _ = _assisted_rewrite_command(
        raw_cmd, input_type, inputs.get("regions"), tree_paths=tree_paths, repo_url=repo_url
    )
    return input_provenance.reference_for(ds, candidate_cmd)


def _detect_missing_apt(build_log_text: str) -> tuple[list[str], list[str]]:
    """Inspect `log_build.txt` for missing standard build tools or `-dev` headers."""
    pkgs: list[str] = []
    reasons: list[str] = []
    issues = diagnose_log.diagnose(build_log_text) if build_log_text else []
    for issue in issues:
        if issue.get("id") == "cmd_not_found":
            for ex in issue.get("examples") or []:
                mapped = _CMD_TO_APT.get(ex.strip().lower())
                if mapped:
                    pkgs.extend(mapped)
                    reasons.append(f"missing command `{ex}`")
    for m_cmd in re.finditer(r"(?:bash:\s*(?:line \d+:\s*)?|/bin/sh:\s*\d*:\s*|make:\s*)([A-Za-z0-9_+-]+):\s*(?:command )?not found", build_log_text):
        cmd_name = m_cmd.group(1).strip().lower()
        if cmd_name in _CMD_TO_APT:
            pkgs.extend(_CMD_TO_APT[cmd_name])
            reasons.append(f"missing command `{cmd_name}`")
    for pattern, rule_pkgs, label in _BUILD_LOG_APT_RULES:
        if pattern.search(build_log_text):
            pkgs.extend(rule_pkgs)
            reasons.append(f"missing {label}")
    return _dedupe(pkgs), _dedupe(reasons)


def _detect_python_floor_upgrade(commands: list[str], build_log_text: str) -> tuple[list[str], dict | None]:
    """If `conda create ... python=3.Y` failed because a dependency declared
    `Requires-Python >=3.X` (X > Y), bump `python=3.Y` to a compatible minor."""
    req_minors = [int(m.group(1)) for m in re.finditer(r"Requires-Python\s*>=\s*3\.(\d+)", build_log_text)]
    if not req_minors:
        return commands, None
    needed_minor = max(10, min(max(req_minors), 11))
    updated: list[str] = []
    changed_from: str | None = None
    for cmd in commands:
        m_py = re.search(r"\bpython=3\.(\d+)\b", cmd)
        if m_py and re.match(r"^(?:conda|mamba)\s+create\b", cmd) and int(m_py.group(1)) < max(req_minors):
            changed_from = f"3.{m_py.group(1)}"
            updated.append(re.sub(r"\bpython=3\.\d+\b", f"python=3.{needed_minor}", cmd, count=1))
        else:
            updated.append(cmd)
    if not changed_from:
        return commands, None
    return updated, {
        "rule_id": "python_floor_conflict",
        "category": "environment",
        "what_failed_strict": (
            f"README specifies `python={changed_from}`, but package metadata on PyPI requires "
            f"`Python >= 3.{min(req_minors)}`."
        ),
        "adjustment_applied": f"Updated Conda environment Python version from `{changed_from}` to `3.{needed_minor}`.",
        "author_fix": f"Update `python={changed_from}` to `python=3.{needed_minor}` in the README installation block.",
    }


def _build_assisted_dockerfile(
    install_commands: list[str],
    *,
    uses_conda: bool,
    conda_env: str | None,
    venv_activate: str | None,
    extra_apt: list[str],
    git_https_rewrite: bool = False,
) -> str:
    lines = ["# Assisted remediation carrier: strhub-assisted-remediation/1 (Track 2 rehearsal)."]
    lines += documented_install.base_lines(uses_conda)
    if extra_apt:
        lines.append(
            "RUN " + json.dumps([
                "bash", "-c",
                "apt-get update && apt-get install -y --no-install-recommends " + " ".join(extra_apt),
            ])
        )
    if git_https_rewrite:
        lines.append(
            "RUN " + json.dumps([
                "git", "config", "--global", "url.https://github.com/.insteadOf", "git@github.com:",
            ])
        )
    lines += ['COPY [".", "/opt/tool"]', "WORKDIR /opt/tool"]
    script = "set -eo pipefail\n" + "\n".join(install_commands) + "\n"
    lines.append("RUN " + json.dumps(["bash", "-lc", script]))
    if conda_env:
        lines.append("RUN " + json.dumps(["bash", "-c", f"echo 'conda activate {conda_env}' > /etc/profile.d/zz-strhub-env.sh"]))
    if venv_activate:
        lines.append("RUN " + json.dumps(["bash", "-c", f"echo 'source {venv_activate}' >> /etc/profile.d/zz-strhub-env.sh"]))
    lines.append('RUN ["bash", "-c", "echo \'export PATH=\\"$PATH:/opt/tool:/opt/tool/bin:/opt/tool/build\\"\' >> /etc/profile.d/zz-strhub-path.sh"]')
    lines.append('ENTRYPOINT ["/bin/bash", "-lc"]')
    return "\n".join(lines) + "\n"


def _build_readme_suggestion(
    repo_url: str,
    init_submodules: bool,
    extra_apt: list[str],
    git_https_rewrite: bool,
    install_commands: list[str],
    mkdir_dirs: list[str],
    display_run_cmd: str,
) -> str:
    clone_flag = "--recursive " if init_submodules else ""
    repo_clean = (repo_url or "https://github.com/owner/tool").rstrip("/")
    repo_dir = repo_clean.rsplit("/", 1)[-1].removesuffix(".git")
    inst_lines: list[str] = []
    if extra_apt:
        inst_lines.append("sudo apt-get update && sudo apt-get install -y " + " ".join(extra_apt))
    if git_https_rewrite:
        inst_lines.append('git config --global url."https://github.com/".insteadOf "git@github.com:"')
    inst_lines.append(f"git clone {clone_flag}{repo_clean}")
    inst_lines.append(f"cd {repo_dir}")
    inst_lines.extend(install_commands)
    usage_lines: list[str] = []
    for d in mkdir_dirs:
        usage_lines.append(f"mkdir -p {d}")
    usage_lines.append(display_run_cmd)
    return (
        "## Installation\n\n```bash\n"
        + "\n".join(inst_lines)
        + "\n```\n\n## Usage\n\n```bash\n"
        + "\n".join(usage_lines)
        + "\n```"
    )


def plan_assisted_run(
    proposal: dict | None,
    manifest: dict | None,
    review: dict | None,
    *,
    installs_passed: bool,
    installs_attempted: bool,
    runs_passed: bool,
    io_passed: bool,
    build_log_text: str = "",
) -> dict | None:
    """Pure planner: inspect Track 1's outcome and return a deterministic Track 2
    plan if and only if at least one of the 6 closed generic rules applies."""
    if not isinstance(proposal, dict) or not isinstance(manifest, dict) or not isinstance(review, dict):
        return None
    if runs_passed and io_passed:
        return None

    # Never retry hardware/licensing ceilings in Track 2.
    compat = manifest.get("compatibility") or {}
    if any(compat.values()):
        return None
    if build_log_text:
        log_ids = {i.get("id") for i in diagnose_log.diagnose(build_log_text)}
        if log_ids & diagnose_log.HARNESS_INCOMPATIBLE:
            return None

    tree_paths = set(proposal.get("tree_paths") or [])
    if ".dockerignore" in tree_paths:
        return None

    raw_run_cmd, raw_cwd = unwrap_example((manifest.get("run") or {}).get("cmd") or "")
    cwd = raw_cwd or "."
    if not raw_run_cmd or raw_run_cmd.strip().startswith("true"):
        return None

    inputs = manifest.get("inputs") or {}
    input_type = inputs.get("type")
    regions = inputs.get("regions")
    if not input_type or not datasets_lib.resolve(input_type):
        return None

    adjustments: list[dict] = []
    inst_info = review.get("installation") or {}
    base_cond = inst_info.get("base_condition") or {}
    doc_cmds = [c["text"] for c in (inst_info.get("commands") or []) if isinstance(c, dict) and c.get("text")]
    uses_conda = bool(base_cond.get("miniforge"))
    conda_env = inst_info.get("conda_environment")
    init_submodules = bool(base_cond.get("submodules"))
    venv_activate: str | None = None
    for c in doc_cmds:
        m_act = re.fullmatch(r"(?:source|\.) (\S+)/bin/activate", c)
        if m_act:
            venv_activate = f"/opt/tool/{m_act.group(1).strip('./')}/bin/activate"

    install_commands = list(doc_cmds)
    extra_apt: list[str] = []
    git_https_rewrite = False
    ssh_files = [str(f) for f in ((proposal.get("build") or {}).get("ssh_urls_in") or []) if f]

    repo_url = (manifest.get("source") or {}).get("repo") or proposal.get("repo") or ""
    assisted_cmd, effective_regions, cli_adjs = _assisted_rewrite_command(
        raw_run_cmd, input_type, regions, tree_paths=tree_paths, repo_url=repo_url
    )
    try:
        pre_toks = fidelity.tokens(assisted_cmd)
    except ValueError:
        pre_toks = []
    first_exe = pre_toks[0] if pre_toks else ""

    # --- Installation remediation (Rules 1, 2, 3, 4) -------------------------
    if not review.get("install_ready"):
        other_root_manifests = {
            "environment.yml", "environment.yaml", "pyproject.toml",
            "setup.py", "Makefile", "CMakeLists.txt",
        } & tree_paths
        needs_repo_script_build = (
            first_exe.startswith("./")
            and "/" in first_exe[2:]
            and first_exe[2:] not in tree_paths
        )
        # Rule 4: standard root packaging manifest or bootstrap script when README install block is missing/unusable
        if "install.sh" in tree_paths and (not other_root_manifests or needs_repo_script_build):
            install_commands = ["bash install.sh"]
            uses_conda = bool("environment.yml" in tree_paths or "environment.yaml" in tree_paths)
            extra_apt = _dedupe([
                *_STANDARD_NATIVE_CPP_APT,
                "wget", "unzip", "bzip2", "default-jre-headless", "libncurses5-dev",
            ])
            adjustments.append({
                "rule_id": "standard_manifest_in_root",
                "category": "environment",
                "what_failed_strict": "No literally copyable installation code block was admitted from README.md.",
                "adjustment_applied": (
                    "Executed root `install.sh` script shipped in the commit with standard Ubuntu 22.04 build packages."
                ),
                "author_fix": "Add a copyable installation block directly to README.md.",
            })
            if ssh_files:
                git_https_rewrite = True
                adjustments.append({
                    "rule_id": "ssh_git_url_in_build",
                    "category": "environment",
                    "what_failed_strict": (
                        f"Build file(s) (`{', '.join(ssh_files)}`) clone public GitHub dependencies via "
                        "`git@github.com:` SSH URLs, which fail without a configured SSH key."
                    ),
                    "adjustment_applied": (
                        'Configured Git HTTPS URL rewrite (`git config --global url."https://github.com/".insteadOf "git@github.com:"`).'
                    ),
                    "author_fix": (
                        f"Replace `git@github.com:` with `https://github.com/` in `{', '.join(ssh_files)}` "
                        "so clean checkouts build without SSH keys."
                    ),
                })
        elif "environment.yml" in tree_paths or "environment.yaml" in tree_paths:
            env_file = "environment.yml" if "environment.yml" in tree_paths else "environment.yaml"
            install_commands = [
                f"conda env create --name strhub_assisted --file={env_file}",
                "conda activate strhub_assisted",
            ]
            uses_conda = True
            conda_env = "strhub_assisted"
            adjustments.append({
                "rule_id": "standard_manifest_in_root",
                "category": "environment",
                "what_failed_strict": "No literally copyable installation code block was admitted from README.md.",
                "adjustment_applied": f"Built Conda environment directly from root `{env_file}` shipped in the commit.",
                "author_fix": f"Add a copyable installation block to README.md:\n`conda env create -n tool -f {env_file} && conda activate tool`.",
            })
        elif "pyproject.toml" in tree_paths or "setup.py" in tree_paths:
            pkg_file = "pyproject.toml" if "pyproject.toml" in tree_paths else "setup.py"
            install_commands = [
                "python3 -m venv .strhub-venv",
                "source .strhub-venv/bin/activate",
                "python -m pip install .",
            ]
            uses_conda = False
            venv_activate = "/opt/tool/.strhub-venv/bin/activate"
            adjustments.append({
                "rule_id": "standard_manifest_in_root",
                "category": "environment",
                "what_failed_strict": "No literally copyable installation code block was admitted from README.md.",
                "adjustment_applied": f"Installed Python package in a clean virtualenv from root `{pkg_file}`.",
                "author_fix": "Add a copyable installation block to README.md:\n`python3 -m venv .venv && source .venv/bin/activate && pip install .`.",
            })
        elif "Makefile" in tree_paths and "CMakeLists.txt" not in tree_paths:
            install_commands = ["make"]
            extra_apt = list(_STANDARD_NATIVE_CPP_APT)
            adjustments.append({
                "rule_id": "standard_manifest_in_root",
                "category": "environment",
                "what_failed_strict": "No literally copyable installation code block was admitted from README.md.",
                "adjustment_applied": (
                    "Installed standard Ubuntu 22.04 C/C++ build packages and ran `make` against "
                    "the root `Makefile` shipped in the commit."
                ),
                "author_fix": "Add a copyable `make` installation block (plus required `apt` libraries) to README.md.",
            })
            if ssh_files:
                git_https_rewrite = True
                adjustments.append({
                    "rule_id": "ssh_git_url_in_build",
                    "category": "environment",
                    "what_failed_strict": (
                        f"Build file(s) (`{', '.join(ssh_files)}`) clone public GitHub dependencies via "
                        "`git@github.com:` SSH URLs, which fail without a configured SSH key."
                    ),
                    "adjustment_applied": (
                        'Configured Git HTTPS URL rewrite (`git config --global url."https://github.com/".insteadOf "git@github.com:"`).'
                    ),
                    "author_fix": (
                        f"Replace `git@github.com:` with `https://github.com/` in `{', '.join(ssh_files)}` "
                        "so clean checkouts build without SSH keys."
                    ),
                })
        elif "CMakeLists.txt" in tree_paths:
            install_commands = ["cmake -B build -DCMAKE_BUILD_TYPE=Release", "cmake --build build -j2"]
            extra_apt = list(_STANDARD_NATIVE_CPP_APT)
            adjustments.append({
                "rule_id": "standard_manifest_in_root",
                "category": "environment",
                "what_failed_strict": "No literally copyable installation code block was admitted from README.md.",
                "adjustment_applied": (
                    "Installed standard Ubuntu 22.04 C/C++ build packages and ran CMake against "
                    "the root `CMakeLists.txt` shipped in the commit."
                ),
                "author_fix": "Add a copyable CMake installation block (`cmake -B build && cmake --build build`) to README.md.",
            })
            if ssh_files:
                git_https_rewrite = True
                adjustments.append({
                    "rule_id": "ssh_git_url_in_build",
                    "category": "environment",
                    "what_failed_strict": (
                        f"Build file(s) (`{', '.join(ssh_files)}`) clone public GitHub dependencies via "
                        "`git@github.com:` SSH URLs, which fail without a configured SSH key."
                    ),
                    "adjustment_applied": (
                        'Configured Git HTTPS URL rewrite (`git config --global url."https://github.com/".insteadOf "git@github.com:"`).'
                    ),
                    "author_fix": (
                        f"Replace `git@github.com:` with `https://github.com/` in `{', '.join(ssh_files)}` "
                        "so clean checkouts build without SSH keys."
                    ),
                })
        else:
            return None
    elif installs_attempted and not installs_passed:
        # Rule 1: missing standard Ubuntu build tools or `-dev` libraries.
        # Because `make`/`./configure`/`cmake` abort on the first missing tool or header,
        # a single-pass native C/C++ build supplies the standard Ubuntu C/C++ bundle together.
        apt_pkgs, apt_reasons = _detect_missing_apt(build_log_text)
        is_native_build = any(_NATIVE_BUILD_CMD_RE.search(c) for c in install_commands)
        native_pkg_hit = bool(set(apt_pkgs) & (set(_STANDARD_NATIVE_CPP_APT) | {"libhts-dev", "libncurses5-dev"}))
        if apt_pkgs:
            extra_apt = (
                _dedupe(list(_STANDARD_NATIVE_CPP_APT) + apt_pkgs)
                if (is_native_build or native_pkg_hit)
                else apt_pkgs
            )
            adjustments.append({
                "rule_id": "missing_apt_build_tool",
                "category": "environment",
                "what_failed_strict": "Build failed due to undeclared system packages (" + ", ".join(apt_reasons) + ").",
                "adjustment_applied": "Installed standard Ubuntu 22.04 build packages: `" + " ".join(extra_apt) + "`.",
                "author_fix": "Add `sudo apt-get update && sudo apt-get install -y " + " ".join(extra_apt) + "` to README.md.",
            })
        # Rule 1b: public GitHub `git@github.com:` SSH URLs inside build scripts/submodules
        if ssh_files or _GIT_SSH_LOG_RE.search(build_log_text):
            git_https_rewrite = True
            where_ssh = f" (`{', '.join(ssh_files)}`)" if ssh_files else ""
            target_fix = f"`{', '.join(ssh_files)}`" if ssh_files else "build scripts / `.gitmodules`"
            adjustments.append({
                "rule_id": "ssh_git_url_in_build",
                "category": "environment",
                "what_failed_strict": (
                    f"Build step{where_ssh} clones public GitHub dependencies via `git@github.com:` SSH URLs, "
                    "which fail without a configured SSH key."
                ),
                "adjustment_applied": (
                    'Configured Git HTTPS URL rewrite (`git config --global url."https://github.com/".insteadOf "git@github.com:"`).'
                ),
                "author_fix": (
                    f"Replace `git@github.com:` with `https://github.com/` in {target_fix} "
                    "so clean checkouts build without SSH keys."
                ),
            })
        # Rule 2: uninitialized `.gitmodules`
        if ".gitmodules" in tree_paths and not init_submodules:
            init_submodules = True
            adjustments.append({
                "rule_id": "uninitialized_submodules",
                "category": "environment",
                "what_failed_strict": "Repository contains `.gitmodules`, but README.md did not specify `--recursive`.",
                "adjustment_applied": "Initialized Git submodules (`git submodule update --init --recursive`) before building.",
                "author_fix": "Document `git clone --recursive <repo-url>` in README.md.",
            })
        # Rule 3: Conda Python version floor conflict
        if uses_conda:
            install_commands, py_adj = _detect_python_floor_upgrade(install_commands, build_log_text)
            if py_adj:
                adjustments.append(py_adj)
        if not adjustments:
            # Build failed for a reason none of our generic rules can safely fix.
            return None

    # Rule 4b: Conda dependency file (`environment.y*ml`) paired with root `setup.py` /
    # `pyproject.toml` where README omitted `pip install .` (so dependencies installed,
    # but the repository's own CLI script was never placed on `$PATH`).
    if (
        review.get("install_ready")
        and uses_conda
        and ("setup.py" in tree_paths or "pyproject.toml" in tree_paths)
        and not any(
            re.search(r"\b(?:pip\s+install|python3?\s+setup\.py\s+(?:install|develop))", c)
            for c in install_commands
        )
    ):
        pkg_manifest = "pyproject.toml" if "pyproject.toml" in tree_paths else "setup.py"
        install_commands.append("python -m pip install --no-deps .")
        adjustments.append({
            "rule_id": "standard_manifest_in_root",
            "category": "environment",
            "what_failed_strict": (
                f"Conda environment commands installed dependencies without installing the repository's "
                f"root Python package (`{pkg_manifest}`), leaving CLI scripts off `$PATH`."
            ),
            "adjustment_applied": (
                "Installed the verified commit's Python package into the Conda environment "
                "(`python -m pip install --no-deps .`)."
            ),
            "author_fix": (
                "Add `pip install --no-deps .` after `conda activate` in README.md (or prefix `./` when "
                "invoking scripts from the cloned directory)."
            ),
        })

    # --- CLI & Runtime remediation (Rules 5 & 6) -----------------------------
    adjustments.extend(cli_adjs)
    regions = effective_regions

    # Rule 5c: bare `.py` script in repository root invoked without `python` or `./`
    # when no root Python packaging manifest installed it onto `$PATH`.
    try:
        cmd_toks = fidelity.tokens(assisted_cmd)
    except ValueError:
        cmd_toks = []
    if (
        cmd_toks
        and "/" not in cmd_toks[0]
        and cmd_toks[0].endswith(".py")
        and cmd_toks[0] in tree_paths
        and "setup.py" not in tree_paths
        and "pyproject.toml" not in tree_paths
    ):
        orig_exe = cmd_toks[0]
        assisted_cmd = f"python3 ./{orig_exe}" + assisted_cmd[len(orig_exe):]
        adjustments.append({
            "rule_id": "positional_reads_arg",
            "category": "cli_invocation",
            "what_failed_strict": f"Command invokes `{orig_exe}` without `./` or `python3`, and `.` is not on `$PATH`.",
            "adjustment_applied": f"Invoked root script explicitly as `python3 ./{orig_exe}`.",
            "author_fix": f"Prefix `python3 ./{orig_exe}` (or `./{orig_exe}`) in README.md.",
        })

    ds = datasets_lib.resolve(input_type) or {}
    canonical = ds.get("canonical_input") or ""
    if not canonical or f"/data/in/{canonical}" not in assisted_cmd:
        # Even after Rule 5, the command still does not read the staged dataset
        # (e.g. it points to a custom missing config or hg19 path): abort cleanly.
        return None
    # Check remaining unresolvable placeholders or wrong assembly
    if re.search(r"(?:hg19|grch37|b37|hs37d5)(?![a-z0-9])", assisted_cmd, re.I) and ds.get("reference") == "hg38":
        return None
    if re.search(r"\bpath/to/", assisted_cmd, re.I):
        return None

    mkdir_dirs = _output_parent_dirs(assisted_cmd)
    if mkdir_dirs and (not runs_passed or not io_passed):
        # Only log Rule 6 as a primary adjustment if Track 1 already installed and failed at run/io,
        # or include mkdir defensively alongside other adjustments.
        if installs_passed and review.get("may_say_runs") and not adjustments:
            adjustments.append({
                "rule_id": "missing_output_parent_dir",
                "category": "cli_invocation",
                "what_failed_strict": "The documented command writes into a subdirectory that may not exist in a clean checkout.",
                "adjustment_applied": "Pre-created output parent directory (`mkdir -p " + " ".join(mkdir_dirs) + "`).",
                "author_fix": "Add `mkdir -p " + " ".join(mkdir_dirs) + "` before the command in README.md.",
            })
        elif adjustments:
            adjustments.append({
                "rule_id": "missing_output_parent_dir",
                "category": "cli_invocation",
                "what_failed_strict": "Command targets nested output path(s) `" + ", ".join(mkdir_dirs) + "`.",
                "adjustment_applied": "Pre-created output parent directory (`mkdir -p " + " ".join(mkdir_dirs) + "`).",
                "author_fix": "Ensure README.md includes `mkdir -p " + " ".join(mkdir_dirs) + "` or create output directories automatically.",
            })

    if not adjustments:
        return None

    exec_inner = (
        "mkdir -p " + " ".join(mkdir_dirs) + " && " + assisted_cmd
        if mkdir_dirs else assisted_cmd
    )
    wrapped_cmd = example_wrapper(exec_inner, cwd)
    dockerfile = _build_assisted_dockerfile(
        install_commands,
        uses_conda=uses_conda,
        conda_env=conda_env,
        venv_activate=venv_activate,
        extra_apt=extra_apt,
        git_https_rewrite=git_https_rewrite,
    )
    ref_genome = input_provenance.reference_for(ds, assisted_cmd)

    needs_rebuild = bool(not installs_passed or any(a["category"] == "environment" for a in adjustments))

    return {
        "schema": SCHEMA,
        "adjustments": adjustments,
        "needs_rebuild": needs_rebuild,
        "uses_conda": uses_conda,
        "conda_env": conda_env,
        "venv_activate": venv_activate,
        "init_submodules": init_submodules,
        "extra_apt": extra_apt,
        "git_https_rewrite": git_https_rewrite,
        "install_commands": install_commands,
        "dockerfile": dockerfile,
        "unwrapped_run_cmd": assisted_cmd,
        "wrapped_run_cmd": wrapped_cmd,
        "mkdir_dirs": mkdir_dirs,
        "cwd": cwd,
        "input_type": input_type,
        "regions": regions,
        "needs_reference": bool(ref_genome),
        "readme_suggestion": _build_readme_suggestion(
            repo_url, init_submodules, extra_apt, git_https_rewrite,
            install_commands, mkdir_dirs, raw_run_cmd,
        ),
    }


def explain_unassisted_reason(
    proposal: dict | None,
    manifest: dict | None,
    review: dict | None,
    *,
    installs_passed: bool,
    installs_attempted: bool,
    build_log_text: str = "",
) -> tuple[str, str]:
    """Explain deterministically why Track 2 could not launch an automated container
    without inventing commands, custom configs, or modifying repository files."""
    compat = ((manifest or {}).get("compatibility") or {}) if isinstance(manifest, dict) else {}
    if any(compat.values()):
        return (
            "hardware_or_license",
            "Automated Run 2 was evaluated and skipped because special hardware, a graphical display, "
            "or proprietary licensing is required outside the CPU-only container runner.",
        )
    if build_log_text:
        log_ids = {i.get("id") for i in diagnose_log.diagnose(build_log_text)}
        if log_ids & diagnose_log.HARNESS_INCOMPATIBLE:
            return (
                "hardware_or_license",
                "Automated Run 2 was evaluated and skipped because Run 1 hit a hardware, memory, "
                "or licensing boundary of the automated CPU-only runner.",
            )

    tree_paths = set((proposal or {}).get("tree_paths") or []) if isinstance(proposal, dict) else set()
    if ".dockerignore" in tree_paths:
        return (
            "dockerignore_present",
            "Automated Run 2 was evaluated and skipped because `.dockerignore` excludes files "
            "from the container build context.",
        )

    raw_run_cmd, _ = unwrap_example(((manifest or {}).get("run") or {}).get("cmd") or "") if isinstance(manifest, dict) else ("", "")
    if not raw_run_cmd or raw_run_cmd.strip().startswith("true"):
        return (
            "no_run_command",
            "Automated Run 2 was evaluated, and no concrete command-line invocation was found in "
            "the public documentation to execute without inventing commands.",
        )

    inputs = ((manifest or {}).get("inputs") or {}) if isinstance(manifest, dict) else {}
    input_type = inputs.get("type")
    ds = datasets_lib.resolve(input_type) if input_type else None
    if not input_type or not ds:
        return (
            "unsupported_input_type",
            "Automated Run 2 was evaluated, and no public reference sample is registered for the "
            "input format expected by this procedure.",
        )

    std_manifests = {
        "install.sh", "environment.yml", "environment.yaml",
        "pyproject.toml", "setup.py", "Makefile", "CMakeLists.txt",
    }
    if isinstance(review, dict) and not review.get("install_ready") and not (std_manifests & tree_paths):
        return (
            "no_standard_installer",
            "Automated Run 2 was evaluated, and neither a copyable installation block nor a standard "
            "root build manifest was found to build the environment automatically.",
        )

    if installs_attempted and not installs_passed:
        return (
            "unrecognized_build_failure",
            "Automated Run 2 inspected the Run 1 build log, and the compilation failure did not match "
            "a standard system package, submodule, or Python version adjustment.",
        )

    repo_url = (((manifest or {}).get("source") or {}).get("repo") or (proposal or {}).get("repo") or "")
    assisted_cmd, _, _ = _assisted_rewrite_command(
        raw_run_cmd, input_type, inputs.get("regions"), tree_paths=tree_paths, repo_url=repo_url
    )
    if re.search(r"\bpath/to/", assisted_cmd, re.I) or re.search(r"<[^<>]+>", assisted_cmd):
        return (
            "unresolved_placeholders",
            "Automated Run 2 was evaluated, and the documented command contains unresolved template "
            "placeholders (such as `path/to/...` or `<...>`) that cannot be filled without inventing paths.",
        )
    if re.search(r"(?:hg19|grch37|b37|hs37d5)(?![a-z0-9])", assisted_cmd, re.I) and ds.get("reference") == "hg38":
        return (
            "assembly_mismatch",
            "Automated Run 2 was evaluated, and the documented command targets GRCh37/hg19 files "
            "while the staged reference sample is aligned to GRCh38/hg38.",
        )
    canonical = ds.get("canonical_input") or ""
    if not canonical or f"/data/in/{canonical}" not in assisted_cmd:
        return (
            "custom_input_layout",
            "Automated Run 2 was evaluated, and the documented command expects an input directory "
            "or custom configuration file rather than a single sample file.",
        )
    return (
        "no_applicable_adjustment",
        "Automated Run 2 evaluated the repository and Run 1 logs, and no safe documentation-only "
        "adjustment applied without modifying files or inventing parameters.",
    )


def _unassisted_record(code: str, reason: str, *, installs_passed: bool) -> dict:
    return {
        "schema": SCHEMA,
        "attempted": False,
        "evaluated": True,
        "passed": False,
        "level": "installs" if installs_passed else "available",
        "skip_reason_code": code,
        "skip_reason": reason,
        "gates": {
            "available": True,
            "installs": bool(installs_passed),
            "runs": False,
            "io": False,
            "content": False,
        },
        "adjustments": [],
    }


def execute_assisted_run(
    ctx,
    proposal: dict | None,
    manifest: dict | None,
    review: dict | None,
    *,
    available_passed: bool,
    installs_passed: bool,
    installs_attempted: bool,
    runs_passed: bool,
    io_passed: bool,
) -> dict | None:
    """Execute at most `MAX_ASSISTED_ATTEMPTS` (1) isolated Track 2 pass under
    `work/assisted/` when Track 1 did not reach `runs and io`."""
    try:
        from harness.engine import stages
    except ImportError:
        from engine import stages

    if not available_passed or (runs_passed and io_passed):
        return None

    build_log_path = ctx.work_abs / "log_build.txt"
    build_log_text = build_log_path.read_text(errors="replace") if build_log_path.is_file() else ""

    plan = plan_assisted_run(
        proposal,
        manifest,
        review,
        installs_passed=installs_passed,
        installs_attempted=installs_attempted,
        runs_passed=runs_passed,
        io_passed=io_passed,
        build_log_text=build_log_text,
    )
    if plan is None:
        code, reason = explain_unassisted_reason(
            proposal,
            manifest,
            review,
            installs_passed=installs_passed,
            installs_attempted=installs_attempted,
            build_log_text=build_log_text,
        )
        return _unassisted_record(code, reason, installs_passed=installs_passed)

    assisted_rel = ctx.work / "assisted"
    assisted_abs = ctx.work_abs / "assisted"
    shutil.rmtree(assisted_abs, ignore_errors=True)
    assisted_abs.mkdir(parents=True, exist_ok=True)

    repo = ctx.plan["repo"]
    ref = ctx.plan["ref"]
    name = os.path.basename(str(repo).removesuffix(".git"))
    src_rel = assisted_rel / "ctx" / name
    src_abs = assisted_abs / "ctx" / name

    log_build_rel = assisted_rel / "log_build.txt"
    log_build_abs = assisted_abs / "log_build.txt"
    log_build_abs.write_text("")

    reusable_checkout = ctx.work_abs / "ctx" / name
    if installs_passed and not plan["needs_rebuild"] and reusable_checkout.is_dir():
        # Track 1 already built the exact environment image cleanly; reuse it
        # without re-running a multi-minute Conda/C++ build, while keeping `/app:ro`.
        src_abs = reusable_checkout
        assisted_image = ctx.image
        if build_log_path.is_file() and build_log_path.stat().st_size > 0:
            shutil.copy2(build_log_path, log_build_abs)
        term_src = build_log_path.with_suffix(build_log_path.suffix + ".terminal")
        if term_src.is_file() and term_src.stat().st_size > 0:
            shutil.copy2(term_src, log_build_abs.with_suffix(log_build_abs.suffix + ".terminal"))
    else:
        src_abs.parent.mkdir(parents=True, exist_ok=True)
        for argv in (
            ["git", "clone", "-q", "--", repo, str(src_rel)],
            ["git", "-C", str(src_rel), "checkout", "-q", ref],
        ):
            if ctx.exe.run(argv, log=log_build_abs, cwd=ctx.root) != 0:
                return _unassisted_record(
                    "no_applicable_adjustment",
                    "Automated Run 2 could not fetch the pinned commit for isolated execution.",
                    installs_passed=installs_passed,
                )

        if plan["init_submodules"] and (src_abs / ".gitmodules").exists():
            git_cmd = (
                ["git", "-c", "url.https://github.com/.insteadOf=git@github.com:"]
                if plan.get("git_https_rewrite")
                else ["git"]
            )
            argv_sub = [*git_cmd, "-C", str(src_rel), "submodule", "update", "--init", "--recursive"]
            if ctx.exe.run(argv_sub, log=log_build_abs, cwd=ctx.root) != 0:
                return _assemble_record(plan, installs_ok=False, runs_ok=False, io_doc=None, ct_doc=None,
                                        log_build=str(log_build_abs), log_ext="", out_ext="")

        df_abs = assisted_abs / "assisted.Dockerfile"
        df_abs.write_text(plan["dockerfile"], encoding="utf-8")
        assisted_image = f"{ctx.image}-assisted"
        argv_build = [
            "bash", ctx.harness("record_terminal.sh"), str(log_build_rel),
            "docker", "build", *stages.BUILD_LIMITS,
            "-f", str(df_abs), "-t", assisted_image, str(src_rel),
        ]
        rc_build = ctx.exe.run(argv_build, timeout=stages.BUILD_TIMEOUT_MINUTES * 60, cwd=ctx.root)
        if rc_build != 0:
            return _assemble_record(plan, installs_ok=False, runs_ok=False, io_doc=None, ct_doc=None,
                                    log_build=str(log_build_abs), log_ext="", out_ext="")

    # Stage verified dataset into work/assisted/in_external
    in_abs = assisted_abs / "in_external"
    out_rel = assisted_rel / "out_external"
    out_abs = assisted_abs / "out_external"
    out_abs.mkdir(parents=True, exist_ok=True)
    out_abs.chmod(0o777)

    try:
        ds_root = ctx.root if (ctx.root / ".git").exists() and (ctx.root / "datasets").is_dir() else ROOT
        _, dataset, files = input_provenance._plan(ds_root, plan["input_type"], plan["regions"])
        in_abs.mkdir(parents=True, exist_ok=True)
        import gzip as _gzip
        for source, fname, unpack in files:
            opener = _gzip.open if unpack else open
            with opener(source, "rb") as s_fh, (in_abs / fname).open("xb") as d_fh:
                shutil.copyfileobj(s_fh, d_fh)
    except Exception:  # noqa: BLE001
        return _unassisted_record(
            "unsupported_input_type",
            "Automated Run 2 could not stage the reference input files for this procedure.",
            installs_passed=installs_passed,
        )

    ref_dir_abs: pathlib.Path | None = None
    if plan["needs_reference"]:
        cand_ref = ctx.work_abs / "ref"
        genome = (dataset or {}).get("reference_genome") or {}
        if not genome.get("filename") or not (cand_ref / genome["filename"]).is_file():
            return _unassisted_record(
                "no_applicable_adjustment",
                "Automated Run 2 required the GRCh38 reference genome, which was not staged in the workspace.",
                installs_passed=installs_passed,
            )
        ref_dir_abs = cand_ref

    log_ext_rel = assisted_rel / "log_external.txt"
    log_ext_abs = assisted_abs / "log_external.txt"
    mounts = [
        "-v", f"{src_abs}:/app:ro",
        "-v", f"{in_abs}:/data/in:ro",
    ]
    if ref_dir_abs is not None:
        mounts += ["-v", f"{ref_dir_abs}:/data/ref:ro"]
    mounts += ["-v", f"{out_abs}:/data/out"]

    argv_run = [
        "bash", ctx.harness("run_container.sh"),
        f"{ctx.container_prefix}_assisted",
        str(ctx.plan["timeout"]),
        str(log_ext_rel),
        *stages.HARDENING,
        *mounts,
        assisted_image,
        plan["wrapped_run_cmd"],
    ]
    rc_run = ctx.exe.run(argv_run, timeout=int(ctx.plan["step_timeout"]) * 60, cwd=ctx.root)
    runs_ok = rc_run == 0

    io_json_abs = assisted_abs / "io_external.json"
    ct_json_abs = assisted_abs / "content_external.json"
    ctx.exe.run(
        [ctx.python, ctx.harness("check_io.py"), ctx.manifest, str(out_rel), "--json", str(io_json_abs)],
        cwd=ctx.root,
    )
    ctx.exe.run(
        [ctx.python, ctx.harness("check_content.py"), ctx.manifest, str(out_rel),
         "--json", str(ct_json_abs), "--panel", dataset.get("supported_loci", "")],
        cwd=ctx.root,
    )
    io_doc = stages._load(io_json_abs)
    ct_doc = stages._load(ct_json_abs)
    return _assemble_record(
        plan,
        installs_ok=True,
        runs_ok=runs_ok,
        io_doc=io_doc,
        ct_doc=ct_doc,
        log_build=str(log_build_abs),
        log_ext=str(log_ext_abs),
        out_ext=str(out_abs),
    )


def _assemble_record(
    plan: dict,
    *,
    installs_ok: bool,
    runs_ok: bool,
    io_doc: dict | None,
    ct_doc: dict | None,
    log_build: str,
    log_ext: str,
    out_ext: str,
) -> dict:
    io_ok = bool(runs_ok and io_doc and io_doc.get("passed"))
    ct_ok = bool(io_ok and ct_doc and ct_doc.get("passed"))
    gates = {
        "available": True,
        "installs": bool(installs_ok),
        "runs": bool(runs_ok),
        "io": io_ok,
        "content": ct_ok,
    }
    ladder = ("available", "installs", "runs", "io", "content")
    level = "none"
    for g in ladder:
        if gates[g]:
            level = g
        else:
            break
    return {
        "schema": SCHEMA,
        "attempted": True,
        "evaluated": True,
        "passed": bool(runs_ok and io_ok),
        "level": level,
        "content_verified": ct_ok,
        "gates": gates,
        "adjustments": plan["adjustments"],
        "verified_commands": {
            "extra_apt": plan["extra_apt"],
            "git_https_rewrite": bool(plan.get("git_https_rewrite")),
            "init_submodules": plan["init_submodules"],
            "install": plan["install_commands"],
            "mkdir_dirs": plan["mkdir_dirs"],
            "run": plan["unwrapped_run_cmd"],
            "dockerfile": plan["dockerfile"],
        },
        "readme_suggestion": plan["readme_suggestion"],
        "io_detail": io_doc or {},
        "content_detail": ct_doc or {},
        "paths": {
            "log_build": log_build,
            "log_external": log_ext,
            "out_external": out_ext,
        },
    }
