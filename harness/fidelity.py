"""Conservative, read-only comparison with a pinned upstream procedure.

This is a closed substitution profile, not a shell equivalence prover. A
construct we cannot establish is an evaluator limitation; it is never repaired.
"""
from __future__ import annotations

import hashlib
import json
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
        line = re.sub(r"^\$ ", "", line)
        if result and result[-1][1].endswith("\\") and all(result[-1][1].count(q) % 2 == 0 for q in "'\""):
            start, previous = result.pop()
            result.append((start, previous[:-1].rstrip() + " " + line))
        else:
            result.append((number, line))
    return result


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


def rewrite(command: str, input_type: str | None) -> dict:
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
    if ((ds or {}).get("reference") == "hg38"
            and re.search(r"(?:hg19|grch37|hg18|ncbi36|t2t|chm13)(?![a-z0-9])", command, re.I)):
        result["limitations"].append("the command names a different assembly from the registered hg38 dataset")
        return result
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
            kind = lambda path: "fastq" if re.search(r"\.f(?:ast)?q(?:\.gz)?$", path, re.I) else "cram" if re.search(r"\.cram(?:\.gz)?$", path, re.I) else "bam"
            compatible = (not READ_PATH.fullmatch(value) or
                          (kind(value) == kind(canonical) and value.endswith(".gz") == canonical.endswith(".gz")))
            if angle:
                names = re.findall(r"bam|cram|fastq", value, re.I)
                compatible = not names or kind(canonical) in [n.lower() for n in names]
            if compatible:
                target, role = f"/data/in/{canonical}", "read_path"
            else:
                result["limitations"].append("the declared sample does not have the documented read-file kind")
        elif previous in INPUT_FLAGS and "," in value:
            result["limitations"].append("input list cardinality is not changed to fit one available sample")
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
        elif i and previous not in OUTPUT_FLAGS and READ_PATH.fullmatch(value) and value != f"/data/in/{canonical}":
            result["limitations"].append("a read-file argument is outside the closed input substitution table")
        if target and role == "read_path":
            result["read_bindings"].append({"token": i, "original": raw, "target": target})
        if target and target != value:
            replacement = raw[0] + target + raw[-1] if raw[0] in "'\"" else target
            changes.append((m.start(), m.end(), replacement))
            result["substitutions"].append({"token": i, "original": raw,
                "replacement": replacement, "role": role, "basis": {"output_placeholder": "explicit output-path placeholder",
                                                         "reference_path": "registered reference genome mount"}.get(role, "declared dataset mount")})
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


def installation(proposal: dict, manifest: dict) -> dict:
    """Review the one installation this evaluator admits: a separately
    versioned, literal source transcript (harness/source_install.py).

    A Dockerfile in the repository is never built. It is arbitrary code its
    author wrote for their own machines, and building it would hand the
    evaluator's build to it. A Makefile, package name or release link alone is
    discovery evidence, not proof of every dependency, compiler option and
    environment setting we might add.
    """
    env, build = manifest.get("environment") or {}, proposal.get("build") or {}
    if env.get("source") == "documented":
        import source_install
        return source_install.installation(proposal, manifest)
    reason = ("This evaluator has no proven installation profile for this recipe; no dependencies, "
              "compiler options or environment fixes may be supplied by STRhub.")
    if build.get("method") == "dockerfile":
        reason += " A Dockerfile shipped in the repository is not built."
    return {"profile": PROFILE, "ready": False, "method": build.get("method", "unknown"), "reason": reason}


def image_invocation_supported(proposal: dict, installation_review: dict | None = None) -> bool:
    """The only image is the evaluator's own carrier around the cited
    transcript, whose entrypoint is fixed; anything else is not run."""
    import source_install
    return bool(installation_review and installation_review.get("profile") == source_install.PROFILE
                and installation_review.get("ready") and source_install.discover(proposal) == installation_review)


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
    import source_install
    if install.get("profile") != source_install.PROFILE:
        raise ValueError("no proven installation profile; Docker must not run")
    source_install.verify_checkout(root, install)
    citations = (review.get("command_review") or {}).get("citations") or []
    checks = [(c.get("path"), c.get("document_sha256")) for c in citations]
    example = example_citation(review["evidence"]["proposal"], manifest) if review["may_say_runs"] else None
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
        import source_install
        source_install.materialise(pathlib.Path(args.checkout), review["installation"],
                                   pathlib.Path(args.source_install_dockerfile))
