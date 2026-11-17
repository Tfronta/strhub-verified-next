"""Conservative, read-only comparison with a pinned upstream procedure.

This is a closed substitution profile, not a shell equivalence prover. A
construct we cannot establish is an evaluator limitation; it is never repaired.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import shlex

import datasets as datasets_lib

PROFILE = "strhub-upstream-procedure/1"
TOKEN = re.compile(r"'[^']*'|\"(?:\\.|[^\"\\])*\"|<[^<>\n]+>|[^\s'\";&|<>()]+|[;&|<>()]+")
INPUT_FLAGS = {"--in", "--input", "--bam", "--bams", "--reads", "--fastq", "-i", "-b"}
OUTPUT_FLAGS = {"--out", "--output", "--output-prefix", "--out-dir", "-o"}
READ_PATH = re.compile(r"[\w./-]+\.(?:bam|cram|f(?:ast)?q)(?:\.gz)?\Z", re.I)
#: A reference genome is a public, standard file the documentation names and no
#: repository ships. When the registered dataset is aligned to one, the token
#: that names it becomes that genome's read-only mount: after one of these
#: flags, or anywhere when the file is called hg38/GRCh38.
REFERENCE_FLAGS = {"--fasta", "--ref", "--reference", "--genome", "--ref-fasta", "--reference-fasta",
                   "--fasta-ref", "-r", "-R", "-f", "-g"}
REFERENCE_PATH = re.compile(r"[\w./-]+\.(?:fa|fasta|fna)\Z", re.I)
REFERENCE_OTHER_FORM = re.compile(r"[\w./-]+\.(?:(?:fa|fasta|fna)\.(?:gz|bgz)|2bit)\Z", re.I)
HG38_NAME = re.compile(r"(?:hg38|grch38)", re.I)


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def literal_lines(text: str) -> list[tuple[int, str]]:
    """Only explicit unquoted shell continuations, never inferred flag lines."""
    result = []
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        line = re.sub(r"^(?:\$\s+|usage:\s*)", "", line, flags=re.I)
        if result and result[-1][1].endswith("\\") and all(result[-1][1].count(q) % 2 == 0 for q in "'\""):
            start, previous = result.pop()
            result.append((start, previous[:-1].rstrip() + " " + line))
        else:
            result.append((number, line))
    return result


CONTINUATION = re.compile(r"^[ \t]+--?[A-Za-z]")


def continued_lines(text: str) -> list[tuple[int, int, str]]:
    """Commands a document writes over several lines without a backslash: a
    line followed by indented lines that each begin with an option.

        ./tool --bams   sample.bam
               --fasta  genome.fa

    is one command, read the way its reader reads it. (start, end, command),
    the continuation lines joined by one space with their indentation
    dropped. A following line that does not begin with an option is not
    joined, so two commands are never read as one."""
    rows = text.splitlines()
    out = []
    for i, raw in enumerate(rows):
        if CONTINUATION.match(raw) or not raw.strip():
            continue
        j = i + 1
        while j < len(rows) and CONTINUATION.match(rows[j]):
            j += 1
        if j > i + 1:
            head = re.sub(r"^(?:\$\s+|usage:\s*)", "", raw.strip(), flags=re.I)
            out.append((i + 1, j, " ".join([head] + [r.strip() for r in rows[i + 1:j]])))
    return out


def tokens(command: str) -> list[str]:
    matches = list(TOKEN.finditer(command))
    end = 0
    for m in matches:
        if command[end:m.start()].strip():
            raise ValueError("unrecognized shell quoting")
        end = m.end()
    if command[end:].strip():
        raise ValueError("unrecognized shell quoting")
    return [m.group() for m in matches]


REGION_FLAGS = {"--regions", "--region", "--loci", "--repeats", "--variant-catalog", "--catalog",
                "--ref_bed", "--ref-bed", "--bed", "--targets", "-l"}
REGION_PATH = re.compile(r"[\w./-]+\.(?:bed|json|tsv|txt)(?:\.gz)?\Z", re.I)


def rewrite(command: str, input_type: str | None, regions: str | None = None, one_sample: bool = False) -> dict:
    """Only standalone read paths, the reference genome the registered dataset
    is aligned to, and explicit output placeholders.

    No executable changes, defaults, config selection, region conversion,
    list reduction, synopsis expansion, shell-variable filling or mkdir.
    The original quoting, operators and whitespace are otherwise preserved.
    """
    result = {"profile": PROFILE, "cited": command, "command": command,
              "substitutions": [], "read_bindings": [], "limitations": []}
    if (re.search(r"[$`#\\\n\r*?{}]", command) or re.search(r"\[\s*--?", command)
            or re.search(r"\.\.\.|…", command)):
        result["limitations"].append("shell expansion or synopsis is outside the substitution profile")
        return result
    try:
        toks = tokens(command)
    except ValueError as exc:
        result["limitations"].append(str(exc))
        return result
    ds = datasets_lib.resolve(input_type) if input_type else None
    canonical = (ds or {}).get("canonical_input")
    reference_mount = ((ds or {}).get("reference_genome") or {}).get("mount_path")
    reference_used = False
    # The regions file a preparation named: the dataset's own loci, in the
    # layout the tool reads, mounted beside the sample. Never without one.
    regions_source = ((ds or {}).get("regions") or {}).get(regions or "")
    regions_mount = ("/data/in/regions" + pathlib.PurePosixPath(regions_source).suffix) if regions_source else None
    regions_used = False
    if ((ds or {}).get("reference") == "hg38"
            and re.search(r"(?:hg19|grch37|b37|hs37d5|ncbi37|hg18|ncbi36|t2t|chm13)(?![a-z0-9])", command, re.I)):
        result["limitations"].append("the command names a different assembly from the registered hg38 dataset")
        return result
    def _read_kind(path: str) -> str:
        if re.search(r"\.f(?:ast)?q(?:\.gz)?$", path, re.I):
            return "fastq"
        if re.search(r"\.cram(?:\.gz)?$", path, re.I):
            return "cram"
        return "bam"

    collapsed_list_len = None
    if one_sample and canonical:
        list_lens = []
        for idx in range(1, len(toks)):
            if toks[idx - 1] in INPUT_FLAGS:
                raw_tok = toks[idx]
                val_tok = raw_tok[1:-1] if len(raw_tok) > 1 and raw_tok[0] == raw_tok[-1] and raw_tok[0] in "'\"" else raw_tok
                if "," in val_tok:
                    parts = val_tok.split(",")
                    if (all(READ_PATH.fullmatch(part) for part in parts)
                            and _read_kind(parts[0]) == _read_kind(canonical)
                            and parts[0].endswith(".gz") == canonical.endswith(".gz")):
                        list_lens.append(len(parts))
        if len(list_lens) == 1 and list_lens[0] >= 2:
            collapsed_list_len = list_lens[0]

    changes = []
    for i, m in enumerate(TOKEN.finditer(command)):
        raw = m.group()
        # Only whole arguments, never a substring of another value or assignment.
        if (m.start() and not command[m.start() - 1].isspace()) or (m.end() < len(command) and not command[m.end()].isspace()):
            continue
        value = raw[1:-1] if len(raw) > 1 and raw[0] == raw[-1] and raw[0] in "'\"" else raw
        previous = toks[i - 1] if i else ""
        target, role = None, None
        angle = value.startswith("<") and value.endswith(">")
        read_placeholder = angle and bool(re.search(r"bam|cram|fastq|reads|input", value, re.I))
        if previous in INPUT_FLAGS and canonical and (READ_PATH.fullmatch(value) or read_placeholder):
            compatible = (not READ_PATH.fullmatch(value) or
                          (_read_kind(value) == _read_kind(canonical) and value.endswith(".gz") == canonical.endswith(".gz")))
            if angle:
                names = re.findall(r"bam|cram|fastq", value, re.I)
                compatible = not names or _read_kind(canonical) in [n.lower() for n in names]
            if compatible:
                target, role = f"/data/in/{canonical}", "read_path"
            else:
                result["limitations"].append("the declared sample does not have the documented read-file kind")
        elif previous in INPUT_FLAGS and "," in value and one_sample and canonical \
                and all(READ_PATH.fullmatch(part) for part in value.split(",")):
            parts = value.split(",")
            if _read_kind(parts[0]) == _read_kind(canonical) and parts[0].endswith(".gz") == canonical.endswith(".gz"):
                # A documented list of the reader's own files, in a run STRhub
                # prepared: the one registered sample stands in for it, and says so.
                target, role = f"/data/in/{canonical}", "read_path"
            else:
                result["limitations"].append("the declared sample does not have the documented read-file kind")
        elif previous in INPUT_FLAGS and "," in value:
            result["limitations"].append("input list cardinality is not changed to fit one available sample")
        elif one_sample and collapsed_list_len and previous in ("--bam-samps", "--bam-libs") and "," in value:
            parts = value.split(",")
            if len(parts) == collapsed_list_len and all(re.fullmatch(r"[\w.-]+", part) for part in parts):
                target = parts[0]
                role = "sample_list" if previous == "--bam-samps" else "library_list"
        elif regions_mount and previous in REGION_FLAGS and (REGION_PATH.fullmatch(value) or angle) \
                and not value.startswith("/data/"):
            target, role = regions_mount, "regions_path"
            regions_used = True
        elif previous in OUTPUT_FLAGS and angle and re.search(r"output|prefix|directory", value, re.I):
            target, role = "sample", "output_placeholder"
        elif ds and i and previous not in OUTPUT_FLAGS and not value.startswith("/data/") and (
                (previous in REFERENCE_FLAGS and (REFERENCE_PATH.fullmatch(value) or REFERENCE_OTHER_FORM.fullmatch(value)
                                                  or (angle and re.search(r"reference|genome|fasta|\.fa\b", value, re.I))))
                or ((REFERENCE_PATH.fullmatch(value) or REFERENCE_OTHER_FORM.fullmatch(value))
                    and HG38_NAME.search(value.rsplit("/", 1)[-1]))):
            if not reference_mount:
                result["limitations"].append("the command reads a reference genome and none is registered for the declared dataset")
            elif REFERENCE_OTHER_FORM.fullmatch(value):
                result["limitations"].append("the command reads the reference genome in a form STRhub does not mount (it mounts an uncompressed FASTA with its .fai index)")
            else:
                target, role = reference_mount, "reference_path"
                reference_used = True
        elif ds and i and previous not in OUTPUT_FLAGS and READ_PATH.fullmatch(value) and value != f"/data/in/{canonical}":
            # Only when a dataset is being substituted. With none (the
            # repository's own example) a read file the command names is the
            # repository's own, at its own path, and is left exactly there.
            result["limitations"].append("a read-file argument is outside the closed input substitution table")
        if target and role == "read_path":
            result["read_bindings"].append({"token": i, "original": raw, "target": target})
        if target and target != value:
            replacement = raw[0] + target + raw[-1] if raw[0] in "'\"" else target
            changes.append((m.start(), m.end(), replacement))
            result["substitutions"].append({
                "token": i,
                "original": raw,
                "replacement": replacement,
                "role": role,
                "basis": {
                    "output_placeholder": "explicit output-path placeholder",
                    "reference_path": "registered reference genome mount",
                    "regions_path": f"registered regions file ({regions})",
                    "sample_list": "positional sample list aligned with single-sample BAM",
                    "library_list": "positional library list aligned with single-sample BAM",
                }.get(role, "declared dataset mount"),
            })
    if len(result["read_bindings"]) > 1:
        result["limitations"].append("multiple read inputs cannot be mapped to a single shared sample")
        return result
    rewritten = command
    for start, end, value in reversed(changes):
        rewritten = rewritten[:start] + value + rewritten[end:]
    result["command"] = rewritten
    declared_paths = {f"/data/in/{canonical}"} if canonical else set()
    if canonical and (ds or {}).get("format") == "bam":
        declared_paths.add(f"/data/in/{canonical}.bai")
    if reference_used:
        declared_paths.add(reference_mount)
    if regions_used:
        declared_paths.add(regions_mount)
    mounted_paths = set(re.findall(r"/data/(?:in|ref)(?:/[\w./-]+)?", rewritten))
    if mounted_paths - declared_paths:
        result["limitations"].append("the command requires a runner input outside the shared dataset; no catalog, regions file or configuration is supplied to fill that path")
    if re.search(r"<[^<>]+>|\b(?:configFile|fastqfile)\b", rewritten, re.I):
        result["limitations"].append("unresolved placeholder; no value was invented")
    return result


def cite(proposal: dict, candidate: dict) -> dict:
    """Bind a complete command to its source line, rather than a 300-char quote."""
    source = {"repo": proposal.get("repo"), "ref": proposal.get("ref")}
    out = {"repo": source.get("repo"), "ref": source.get("ref"),
           "path": candidate.get("file"), "line": candidate.get("line"), "verified": False}
    if not re.fullmatch(r"[0-9a-f]{40}", str(source.get("ref") or "")):
        out["reason"] = "upstream ref is not a full immutable commit"
        return out
    for doc in proposal.get("source_documents") or []:
        if doc.get("file") != candidate.get("file") or doc.get("origin") == "wiki":
            continue
        # Unlike discovery, never join separate flag lines or strip a synopsis.
        text = doc.get("text") or ""
        if any(n == candidate.get("line") and line.strip() == candidate.get("cmd")
               for n, line in literal_lines(text)):
            out.update(verified=True, document_sha256=digest(text), command_sha256=digest(candidate["cmd"]))
            return out
        for start, end, joined in continued_lines(text):
            if start == candidate.get("line") and joined == candidate.get("cmd"):
                # Written over several lines; say so, with where it ends.
                out.update(verified=True, end_line=end, continued=True,
                           document_sha256=digest(text), command_sha256=digest(candidate["cmd"]))
                return out
    out["reason"] = "the complete command is not established at the cited repository line"
    return out


def example_citation(proposal: dict, manifest: dict) -> dict | None:
    """An example uses the literal command and the files in the upstream image."""
    example = manifest.get("example") or {}
    cmd = example.get("cmd")
    if not cmd or example.get("cwd") != "." or rewrite(cmd, None)["limitations"]:
        return None
    for candidate in proposal.get("commands", []):
        if candidate.get("cmd") == cmd:
            evidence = cite(proposal, candidate)
            if evidence["verified"]:
                return evidence
    return None


def install_profiles() -> dict:
    """The installation profiles this evaluator admits, by name, in the order
    they are tried. Each one builds a carrier the evaluator writes around
    commands the repository documents; none builds a file the repository ships."""
    import documented_install
    import preparation
    import source_install
    return {source_install.PROFILE: source_install, documented_install.PROFILE: documented_install,
            preparation.PROFILE: preparation}


def literal_profiles() -> list:
    """The profiles that install from the repository's documentation alone."""
    import documented_install
    import source_install
    return [source_install, documented_install]


def verify_evidence_source(proposal: dict | None, cite_str: str | None,
                           quoted_text: str | None = None) -> dict:
    """Verify that an `evidence_source` citation (e.g. `README.md:L308-L322`,
    `README.md:L75`, `repo_file:Makefile`, `example_file:test/sample.bam`)
    points to real, non-wiki repository content in `proposal`."""
    out = {"verified": False, "evidence_source": cite_str}
    if not proposal or not cite_str or not isinstance(cite_str, str):
        return out
    if cite_str.startswith(("repo_file:", "example_file:")):
        path = cite_str.split(":", 1)[1]
        if path and path in set(proposal.get("tree_paths") or []):
            return {"verified": True, "kind": "tree", "path": path, "evidence_source": cite_str}
        return out
    m = re.fullmatch(r"(?P<path>[^:]+):L(?P<start>\d+)(?:-L(?P<end>\d+))?", cite_str)
    if not m:
        return out
    path = m.group("path")
    start = int(m.group("start"))
    end = int(m.group("end") or start)
    for doc in proposal.get("source_documents") or []:
        if doc.get("file") != path or doc.get("origin") == "wiki":
            continue
        raw_text = doc.get("text") or ""
        lines = raw_text.splitlines()
        if 1 <= start <= end <= len(lines):
            span = "\n".join(lines[start - 1:end])
            if quoted_text is not None and (not quoted_text or quoted_text not in span):
                return out
            return {
                "verified": True,
                "kind": "doc",
                "path": path,
                "line": start,
                "end_line": end,
                "document_sha256": digest(raw_text),
                "evidence_source": cite_str,
            }
    return out


def documented_regions(proposal: dict | None) -> str | None:
    """The regions layout documented in the repository, when backed by a
    verified citation in `source_documents`."""
    if not proposal:
        return None
    reg = proposal.get("regions") or {}
    if reg.get("ambiguous"):
        return None
    fmt = reg.get("format")
    if not fmt:
        return None
    check = verify_evidence_source(proposal, reg.get("evidence_source"), reg.get("text"))
    return fmt if check["verified"] else None


def _command_comma_flags(command: str) -> dict[str, list[str]]:
    if not command:
        return {}
    toks = command.split()
    out: dict[str, list[str]] = {}
    targets = INPUT_FLAGS | {"--bam-samps", "--bam-libs", "--samp-sex"}
    i = 0
    while i < len(toks):
        tok = toks[i]
        flag, val = None, None
        if "=" in tok:
            k, v = tok.split("=", 1)
            if k.lower() in targets:
                flag, val = k.lower(), v
        elif tok.lower() in targets and i + 1 < len(toks):
            flag, val = tok.lower(), toks[i + 1]
            i += 1
        if flag and val and "," in val:
            out[flag] = val.strip("'\"").split(",")
        i += 1
    return out


def documented_single_sample(proposal: dict | None, command: str = "") -> bool:
    """Whether the repository's documentation explicitly establishes that
    `--bams`/`--bam` is a comma-separated list of sample BAMs and, when
    positional `--bam-samps`/`--bam-libs` lists appear, every such flag has
    verified 1-to-1 documentary backing and matching cardinality."""
    if not proposal:
        return False
    ss = proposal.get("single_sample_bams") or {}
    if not ss.get("allowed"):
        return False
    check = verify_evidence_source(proposal, ss.get("evidence_source"), ss.get("text"))
    if not check["verified"]:
        return False
    if command and re.search(r"(?:^|\s)--(?:bam-(?:samps|libs)|samp-sex)(?:\s+|=)\S*,\S*", command, re.I):
        flag_vals = _command_comma_flags(command)
        if "--samp-sex" in flag_vals:
            return False
        bam_items = next((flag_vals[f] for f in ("--bams", "--bam", "-b") if f in flag_vals), None)
        if not bam_items or len(bam_items) < 2:
            return False
        paired = ss.get("paired_flags") or []
        seen_paired = 0
        for req_flag in ("--bam-samps", "--bam-libs"):
            if req_flag not in flag_vals:
                continue
            if len(flag_vals[req_flag]) != len(bam_items):
                return False
            entry = next((p for p in paired if p.get("flag") == req_flag), None)
            if not entry:
                return False
            pcheck = verify_evidence_source(proposal, entry.get("evidence_source"), entry.get("text"))
            if not pcheck["verified"]:
                return False
            seen_paired += 1
        if not seen_paired:
            return False
    return True


def rewrite_for(manifest: dict, command: str, proposal: dict | None = None) -> dict:
    """`rewrite` with what the effective manifest says about the run: its
    dataset, the regions layout a preparation or verified repository
    documentation named, and whether one sample stands in for a documented
    list."""
    inputs = manifest.get("inputs") or {}
    env_source = (manifest.get("environment") or {}).get("source")
    prepared = env_source == "prepared"
    doc_ok = env_source == "documented" and proposal is not None
    req_regions = inputs.get("regions")
    regions = req_regions if (prepared or (doc_ok and req_regions and req_regions == documented_regions(proposal))) else None
    one_sample = prepared or (doc_ok and documented_single_sample(proposal, command))
    return rewrite(command, inputs.get("type"), regions=regions, one_sample=one_sample)


def install_plan(proposal: dict) -> dict:
    """The first profile that can transcribe the repository's installation."""
    plan = {}
    for module in literal_profiles():
        plan = module.discover(proposal)
        if plan.get("ready"):
            break
    return plan


def installation(proposal: dict, manifest: dict) -> dict:
    """Review the installations this evaluator admits: a literal source
    transcript (harness/source_install.py) or the install commands a document
    shows (harness/documented_install.py).

    A Dockerfile in the repository is never built. It is arbitrary code its
    author wrote for their own machines, and building it would hand the
    evaluator's build to it. A Makefile, package name or release link alone is
    discovery evidence, not proof of every dependency, compiler option and
    environment setting we might add.
    """
    env, build = manifest.get("environment") or {}, proposal.get("build") or {}
    if env.get("source") == "prepared":
        import preparation
        return preparation.installation(proposal, manifest)
    if env.get("source") == "documented":
        result = {}
        for module in literal_profiles():
            result = module.installation(proposal, manifest)
            if result.get("ready"):
                break
        return result
    # Why no profile could transcribe the installation, in the plan's own
    # words, and whose the gap is: the documentation's or this evaluator's.
    plan = install_plan(proposal)
    reason = plan.get("reason") or ("This evaluator has no proven installation profile for this recipe; no "
                                    "dependencies, compiler options or environment fixes may be supplied by STRhub.")
    if build.get("method") == "dockerfile":
        reason += " A Dockerfile shipped in the repository is not built."
    return {"profile": PROFILE, "ready": False, "method": build.get("method", "unknown"), "reason": reason,
            "gap": plan.get("gap", "strhub")}


def image_invocation_supported(proposal: dict, installation_review: dict | None = None) -> bool:
    """The only image is the evaluator's own carrier around the cited
    transcript, whose entrypoint is fixed; anything else is not run."""
    module = install_profiles().get((installation_review or {}).get("profile"))
    return bool(module and installation_review.get("ready") and module.discover(proposal) == installation_review)


def verify_checkout(root, review: dict, manifest: dict | None = None) -> None:
    """Check the cited documents and source against the actual pinned checkout."""
    import _paths
    import authorization
    checked = authorization.validate(review, manifest)
    if not checked.valid:
        raise ValueError("no proven procedure for the effective manifest: " + checked.reason)
    review = checked.review
    install = review.get("installation") or {}
    if review.get("profile") != PROFILE or not install.get("ready"):
        raise ValueError("no proven installation profile; Docker must not run")
    module = install_profiles().get(install.get("profile"))
    if module is None:
        raise ValueError("no proven installation profile; Docker must not run")
    module.verify_checkout(root, install)
    citations = (review.get("command_review") or {}).get("citations") or []
    checks = [(c.get("path"), c.get("document_sha256")) for c in citations]
    for inf in (review.get("inferences") or {}).values():
        if isinstance(inf, dict) and inf.get("kind") == "doc" and inf.get("path") and inf.get("document_sha256"):
            pair = (inf["path"], inf["document_sha256"])
            if pair not in checks:
                checks.append(pair)
    example = (example_citation(review["evidence"]["proposal"], manifest)
               if review["may_say_runs"] or review.get("example_ready") else None)
    if example:
        checks.append((example["path"], example["document_sha256"]))
    for relative, expected in checks:
        if not relative or not expected:
            raise ValueError("incomplete upstream file evidence")
        path = _paths.confined(root, relative)
        # Hash raw bytes; decoding/newline changes must not be disguised.
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"upstream evidence differs at pinned checkout: {relative}")


if __name__ == "__main__":
    import argparse
    import json
    import pathlib
    parser = argparse.ArgumentParser(description="Check upstream evidence before Docker")
    parser.add_argument("--checkout", required=True)
    parser.add_argument("--review", required=True)
    parser.add_argument("--manifest", required=True, help="actual effective manifest, not a cached contract")
    parser.add_argument("--source-install-dockerfile", help="Materialise only a verified source-installation carrier")
    args = parser.parse_args()
    review = json.loads(pathlib.Path(args.review).read_text())
    import _manifest
    verify_checkout(pathlib.Path(args.checkout), review, _manifest.load(args.manifest))
    if args.source_install_dockerfile:
        install_profiles()[review["installation"]["profile"]].materialise(
            pathlib.Path(args.checkout), review["installation"], pathlib.Path(args.source_install_dockerfile))
