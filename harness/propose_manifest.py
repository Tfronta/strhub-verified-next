"""Turn a recipe proposal (detect_recipe.py) into a trial recipe: manifest.yml,
Dockerfile and, when the README's command runs on shipped data, the `example`
block. This is what a trial from a bare URL runs, before any human has typed a
command.

Two legs come out of one proposal:

  example   the README's command, verbatim, on the repository's own data,
            captured by the wrapper (see prepare.example_wrapper). Needs no
            rewriting and no STRhub data. The reviewer's gate.
  run       the same command with only the substitutions the closed profile
            in fidelity.rewrite admits: the input token becomes the registered
            dataset's canonical mount (/data/in/input.bam,
            /data/in/sample.fastq), and the reference genome the README
            names becomes the one that dataset is aligned to
            (/data/ref/hg38.fa, a public file no repository ships). Nothing
            else is supplied: no regions or catalog file. A command that
            reads one the repository does not ship is recorded as a
            limitation and is not run. Outputs are not rewritten: the command runs in the clone
            and whatever it creates is captured, so the tool's own output
            layout is kept.

Everything uncertain is written down: the manifest carries `caveats` with the
substitutions made and the warnings detect_recipe raised, so the report says
what STRhub did rather than present it as the author's configuration.

Usage:
  python harness/propose_manifest.py proposal.json --slug <slug> \
      [--submitted-by third_party] [--out-dir work/proposal]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import datasets as datasets_lib  # noqa: E402
import _manifest  # noqa: E402
from prepare import example_wrapper  # noqa: E402

OUTPUT_GLOB = {
    "vcf": ("**/*.vcf*", "vcf"),
    "tsv": ("**/*.t[sx][vt]", "tsv"),   # .tsv and .txt
    "csv": ("**/*.csv", "csv"),
    "json": ("**/*.json", "json"),
}

def rewrite_for_strhub(cmd: str, input_type: str | None, regions: str | None = None,
                       one_sample: bool = False) -> tuple[str, list[str]]:
    """Apply only the closed, independently checked substitution profile."""
    import fidelity
    review = fidelity.rewrite(cmd, input_type, regions=regions, one_sample=one_sample)
    notes = [f"{item['role']}: {item['original']} -> {item['replacement']}."
             for item in review['substitutions']]
    notes += [f"Evaluator limitation: {item}." for item in review['limitations']]
    return review['command'], notes


TYPE_SLUG_SUFFIX = {
    "illumina-bam-hg38": "",
    "illumina-str-fastq": "",
    "illumina-bam-hg38-y": "y",
    "ont-bam-hg38": "ont",
    "ont-bam-hg38-med": "ont-med",
    "ont-fastq": "ont",
    "pacbio-hifi-bam-hg38": "hifi",
    "illumina-bam-hg38-med": "med",
    "pacbio-hifi-bam-hg38-med": "hifi-med",
    "illumina-snp-fastq": "snp",
    "capillary-fsa": "fsa",
}


def catalogue_slug(name: str, input_type: str | None) -> str:
    """The slug a trial from a URL is filed under if it is published.

    One card per tool and assay, whose version moves as releases do: the
    name, and a suffix only for a non-canonical input type. No version and
    no commit — `hipstr-v0-7` would have lied the day v0.8 was verified, or
    spawned a second card. A trial of a tool that is already listed lands on
    its card and refreshes it rather than opening another.
    """
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    suffix = ""
    if input_type:
        mapped = TYPE_SLUG_SUFFIX.get(input_type)
        suffix = mapped if mapped is not None else input_type.split("-")[-1]
    return (f"{base}-{suffix}" if suffix else base) or "tool"


def tool_name_as_written(repo: str, proposal: dict) -> str:
    """The repository's own spelling of its name.

    A GitHub path is case-flattened by its owner as often as not
    (`unique379r/strspy`), and a report that renders that is naming the
    project something nobody calls it. The same word usually appears
    correctly cased in the README prose and in the repository's own file
    names; the most frequent such spelling wins, and the path segment is
    used when there is none.
    """
    segment = repo.rstrip("/").split("/")[-1]
    pattern = re.compile(re.escape(segment), re.I)
    haystack = proposal.get("readme_text", "") + "\n" + "\n".join(proposal.get("tool_names") or [])
    counts: dict[str, int] = {}
    for m in pattern.finditer(haystack):
        counts[m.group(0)] = counts.get(m.group(0), 0) + 1
    if not counts:
        return segment
    # Ties go to the spelling that is not all-lowercase: "STRspy" over "strspy"
    # when a README uses both, since the flat one is what a URL forces.
    return max(counts, key=lambda w: (counts[w], w != w.lower()))


def build(proposal: dict, slug: str, submitted_by: str = "third_party",
          ref_label: str = "") -> dict:
    """Two steps, always in this order. First the repository as it is: its
    own installation, its own command, nothing of STRhub's but the sample.
    Only when that cannot be run does STRhub's preparation for the repository
    apply, if one is committed: the environment is then STRhub's, declared in
    full, and the command is still the README's. The result says which it
    was, and why the first step was not enough."""
    literal = _build(proposal, slug, submitted_by, ref_label)
    review = literal["procedure"]
    if review.get("may_say_runs") or review.get("example_ready"):
        return literal
    import preparation
    plan = preparation.discover(proposal)
    if not plan.get("ready"):
        return literal
    prepared = _build(proposal, slug, submitted_by, ref_label, prepared=plan)
    prepared["without_preparation"] = {"blocker": review.get("blocker"), "basis": review.get("basis"),
                                       "reason": review.get("reason")}
    return prepared


def _build(proposal: dict, slug: str, submitted_by: str = "third_party",
           ref_label: str = "", prepared: dict | None = None) -> dict:
    """Return {"manifest": dict, "manifest_yml": str, "dockerfile": str,
    "limitations": [...], "readme_gaps": [...]}.

    `slug` names the run (the artifact, the working directories); the
    manifest's report.slug is the catalogue slug derived below, which is
    where the result is filed if it is published. `ref_label` is the tag or
    release the ref was resolved from, when there was one: that is the version
    a person cites, and the report shows it large; a bare commit shows its
    short SHA.
    """
    repo, ref = proposal["repo"], proposal["ref"]
    name = tool_name_as_written(repo, proposal)
    build_info = proposal.get("build") or {}
    commands = proposal.get("commands") or []
    input_type = (proposal.get("input_type") or {}).get("best")
    if prepared:
        # The sample is the one STRhub's preparation names, by hand.
        input_type = prepared["dataset"]
    out_fmt = (proposal.get("output") or {}).get("format")
    limitations: list[str] = []
    it = proposal.get("input_type") or {}
    stmts = it.get("statements") or {}
    # The input caveat quotes what the README says and states what this run
    # did. Nothing in it is inferred: the kinds, the recommendation and the
    # lines come from read_input_statements, and when nothing was there to
    # read the caveat says the type was guessed — which is a limitation the
    # verdict weighs, not a fact about the tool.
    input_note = None
    if prepared:
        input_note = (f"Input: STRhub's preparation selects its {input_type} reference data"
                      + (f" and its loci in the {prepared['regions']} layout." if prepared.get("regions") else "."))
    elif input_type:
        if it.get("how") == "command" and commands:
            top = commands[0]
            kind = "BAM" if "bam" in input_type else "FASTQ"
            input_note = (f"Input: the documented command takes {kind} ({top.get('file') or 'README.md'}, "
                          f"line {top.get('line')}); no sentence says so, so the command is what was read. "
                          f"This plan selects STRhub's {input_type} reference data.")
        elif it.get("how") == "read":
            docs = stmts.get("inputs") or []
            kinds = " and ".join(i["kind"].upper() for i in docs)
            line = docs[0]["line"] if docs else None
            input_note = (f"Input: the README documents {kinds}"
                          + (f" (line {line})" if line else "")
                          + f"; this plan selects STRhub's {input_type} reference data.")
            rec = stmts.get("recommendation")
            if rec:
                quote = re.sub(r"[*_`]+", "", rec["text"])[:90]
                input_note += (f" The author recommends {rec['kind'].upper()} "
                               f"(line {rec['line']}: \"{quote}\").")
        if it.get("platform_how") == "multi_stated" and input_note:
            plats = ", ".join(p["platform"] for p in (it.get("supported_platforms") or []))
            if plats:
                input_note += f" Supported platforms documented: {plats}; STRhub selected {it.get('platform')} for this trial."
        if not input_note:
            input_note = (f"Input: no sentence in the README says what the tool takes; "
                          f"{input_type} is only a guess from mentions; it is not authorization to execute.")
            limitations.append("input_type_guessed")
    caveat_items: list[str] = []
    import fidelity
    source_plan = fidelity.install_plan(proposal)

    # --- environment
    if prepared:
        import preparation
        source_plan = prepared
        dockerfile_text = prepared["carrier_dockerfile"]
        env = dict(preparation.ENVIRONMENT)
        cwd = "."
        if prepared.get("installed_by") == "repository":
            caveat_items.append("Environment: STRhub transcribed the documented installation commands unchanged into its "
                                f"own carrier; its preparation ({prepared['file']}) supplies the inputs only.")
        else:
            caveat_items.append(f"Environment: prepared by STRhub by hand ({prepared['file']}); every step is listed in "
                                "the report. The command is the repository's own.")
    elif source_plan["ready"]:
        # One generic transcript: no tool names, prior results or package guesses.
        dockerfile_text = source_plan["carrier_dockerfile"]
        env = {"dockerfile": "Dockerfile", "os": ["ubuntu-22.04"], "source": "documented"}
        cwd = "."
        caveat_items.append("Environment: STRhub transcribed the documented installation commands unchanged into its own carrier ("
                            + source_plan["base_condition"].get("description", source_plan["base_condition"]["image"]) + ").")
    else:
        # Non-runnable: never infer dependencies, interpreters or library paths.
        dockerfile_text = "# Installation profile not established; must not be built.\nFROM scratch\n"
        env = {"dockerfile": "Dockerfile", "os": ["ubuntu-22.04"], "source": "generated"}
        cwd = "."
        limitations.append("install_method_unknown" if build_info.get("method") == "unknown"
                           else "install_profile_unsupported")
        caveat_items.append("Environment: no proven installation profile; STRhub did not manufacture installation steps."
                            + (" STRhub does not build a Dockerfile shipped in a repository." if build_info.get("method") == "dockerfile" else ""))

    # --- the command
    best = commands[0]["cmd"] if commands else ""
    doc_regions = None if prepared else fidelity.documented_regions(proposal)
    doc_one_sample = False if prepared else fidelity.documented_single_sample(proposal, best)
    eff_regions = (prepared or {}).get("regions") or doc_regions
    eff_one_sample = bool(prepared) or doc_one_sample
    used_regions = (prepared or {}).get("regions")
    if input_note:
        caveat_items.append(input_note)
    pm = (proposal.get("input_type") or {}).get("panel_match")
    if pm and not prepared:
        caveat_items.append(
            f"Panel: the shipped loci catalog ({pm['catalog_file']}) overlaps "
            f"{pm['medical_overlap']} loci in STRhub's medical STR slice and 0 in the "
            f"forensic slice; this plan selects STRhub's {pm['dataset']} reference data."
        )
    if not best:
        limitations.append("no_command")
        run_cmd = "true  # no command found in the README; nothing to run"
    else:
        rewritten, notes = rewrite_for_strhub(best, input_type, regions=eff_regions,
                                              one_sample=eff_one_sample)
        if not prepared and doc_regions and "/data/in/regions." in rewritten:
            used_regions = doc_regions
        pre = commands[0].get("prerequisite")
        if pre:
            notes.append("Evaluator limitation: a possible prerequisite was discovered but was not automatically chained.")
        caveat_items += notes
        run_cmd = example_wrapper(rewritten, cwd)
        top = commands[0]
        if top.get("origin", "readme") == "readme":
            caveat_items.append("Run command: the README's own command, rewritten to STRhub's mounts; "
                                "the capture wrapper is planned only if the procedure review passes.")
        elif top.get("origin") == "wiki":
            caveat_items.append(f"Run command: the one documented on the wiki ({top['file']}, line {top['line']}), "
                                "rewritten to STRhub's mounts; the capture wrapper is planned only if the procedure review passes. "
                                "A wiki is not versioned with the code: it was read as it is today.")
        else:
            caveat_items.append(f"Run command: the one documented in {top['file']} (line {top['line']}), "
                                "rewritten to STRhub's mounts; the capture wrapper is planned only if the procedure review passes.")
    if best and input_type and datasets_lib.resolve(input_type):
        limitations += check_documented_files(run_cmd, proposal, input_type, caveat_items)
    # --- outputs
    glob, fmt = OUTPUT_GLOB.get(out_fmt or "", ("**/*", "text"))
    outputs = [{"path": glob, "format": fmt, "min_records": 1}]

    # A label that is just the SHA again (the form passes the resolved ref
    # through when nothing better was found) is not a version.
    version = ref_label.strip() if ref_label and not ref.startswith(ref_label.strip()) else ref[:7]
    manifest = {
        "tool": {"name": name, "version": version, "contact": f"{repo.rstrip('/')}/issues"},
        "submission": {"by": submitted_by},
        "source": {"repo": repo, "ref": ref},
        # Discovery origin only. Eligibility requires the pinned procedure
        # review; this label does not establish documented execution.
        "recipe": {"origin": "proposed"},
        "report": {"slug": catalogue_slug(name, input_type)},
        "environment": env,
        "run": {"cmd": run_cmd, "timeout_minutes": 20},
        "inputs": ({"type": input_type, **({"regions": used_regions} if used_regions else {})}
                   if input_type else {}),
        "outputs": outputs,
    }
    ex = proposal.get("example")
    if ex and ex.get("cmd"):
        # Executable paths are part of the cited procedure, never rewritten.
        ex_cwd = "." if source_plan["ready"] else (ex.get("cwd") or cwd)
        manifest["example"] = {"cmd": ex["cmd"], "cwd": ex_cwd, "source": "detected"}
    # Nothing to run on at all: no STRhub data for the input type and no
    # example in the repository. Every run leg is then N/A, and a verdict read
    # off the gates would call that "fails" — it is nothing of the kind.
    if not (input_type and datasets_lib.resolve(input_type)) and not ex:
        limitations.append("no_reference_dataset")
    warnings = (proposal.get("input_type") or {}).get("warnings") or []
    caveat_items += warnings
    if caveat_items:
        manifest["caveats"] = {"source": "detect_recipe", "items": [c[:300] for c in caveat_items[:8]]}
    # Not a manifest field: the schema rejects anything it does not name, and
    # this is a review of the proposal, not a step the container runs.
    import authorization
    reviewed = authorization.prepare_review(proposal, manifest, limitations, caveat_items)

    header = ("# STRhub Verified candidate, proposed by detect_recipe.\n"
              "# Requires pinned upstream evidence and a strict procedure review.\n"
              "# An origin label is not proof; unsupported procedures must not run.\n")
    return {
        "manifest": manifest,
        "manifest_yml": header + yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True, width=1000),
        "dockerfile": dockerfile_text,
        "limitations": limitations,
        "readme_gaps": (proposal.get("readme") or {}).get("gaps", []),
        "procedure": reviewed,
    }


#: Flags whose value is a file the tool READS (a reference, a catalog, a
#: motif list, a model), as opposed to one it writes.
INPUT_FILE_FLAG = re.compile(r"^--?(?:r|ref|reference|genome|motifs?|catalog|variant[-_]catalog|loci|regions?|"
                             r"repeats?|db|database|model|library|lib|config|conf|in|input|i|b|bams?|bed|"
                             r"annotation|table|rmsk|microsat)$", re.I)
DATA_FILE = re.compile(r"\.(?:tsv|txt|json|bed|csv|pa|model|pkl|tab|gz|ini|cfg|conf|config|fa|fasta)$", re.I)
#: A reference genome is STRhub's to supply (fidelity.rewrite mounts the one
#: the dataset is aligned to). When it cannot, that is a limitation of the
#: substitution profile and is recorded there: it is never a file to ask the
#: tool's author to ship.
REFERENCE_GENOME_FILE = re.compile(r"\.(?:fa|fasta|fna)(?:\.(?:gz|bgz))?$|\.2bit$", re.I)


def check_documented_files(run_cmd: str, proposal: dict, input_type: str,
                           caveats: list[str]) -> list[str]:
    """What the documented command reads that the run cannot give it: a file
    that is neither in the repository at the pinned commit nor the registered
    dataset. STRhub puts nothing in its place; the command is not run and the
    report says which file. A reference genome is not such a file: it is
    STRhub's to supply."""
    from prepare import unwrap_example
    cmd, _ = unwrap_example(run_cmd)
    tree = set(proposal.get("tree_paths") or [])
    out: list[str] = []
    toks = cmd.split()
    for i, t in enumerate(toks):
        path = t.strip("'\"").lstrip("./")
        prev = toks[i - 1] if i else ""
        if REFERENCE_GENOME_FILE.search(path) and path not in tree:
            continue
        if (INPUT_FILE_FLAG.match(prev) and DATA_FILE.search(path) and not t.startswith(("/data/", "-"))
                and path not in tree and "*" not in path):
            caveats.append(f"File: the documented command reads {t} (after {prev}), which is neither in "
                           "the repository nor among STRhub's data.")
            out.append("documented_file_missing")
        elif "=" in path and not path.startswith("-"):
            k, v = path.split("=", 1)
            v_clean = v.strip("'\"").lstrip("./")
            if (INPUT_FILE_FLAG.match(f"--{k.split('_')[-1]}") and DATA_FILE.search(v_clean)
                    and not REFERENCE_GENOME_FILE.search(v_clean) and not v.startswith("/data/") and v_clean not in tree and "*" not in v_clean):
                caveats.append(f"File: the documented command reads {v} (in {t}), which is neither in "
                               "the repository nor among STRhub's data.")
                out.append("documented_file_missing")
    return list(dict.fromkeys(out))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("proposal", help="detect_recipe.py --json output")
    ap.add_argument("--slug", required=True)
    ap.add_argument("--submitted-by", default="third_party", choices=["maintainer", "third_party"])
    ap.add_argument("--ref-label", default="",
                    help="the tag or release the ref was resolved from, shown as the version")
    ap.add_argument("--out-dir", default="", help="also write manifest.yml + Dockerfile here")
    args = ap.parse_args()
    proposal = json.loads(pathlib.Path(args.proposal).read_text())
    r = build(proposal, args.slug, args.submitted_by, args.ref_label)
    _manifest.loads(r["manifest_yml"])
    # The limitations travel back into the proposal file so the report's verdict
    # can read them alongside the README gaps.
    proposal["limitations"] = r["limitations"]
    proposal["procedure"] = r["procedure"]
    if r.get("without_preparation"):
        # Why the repository's own instructions were not enough, for the report.
        proposal["without_preparation"] = r["without_preparation"]
    pathlib.Path(args.proposal).write_text(json.dumps(proposal, indent=2))
    if args.out_dir:
        d = pathlib.Path(args.out_dir)
        d.mkdir(parents=True, exist_ok=True)
        (d / "manifest.yml").write_text(r["manifest_yml"])
        (d / "Dockerfile").write_text(r["dockerfile"])
    print(json.dumps({"slug": args.slug, "catalogue_slug": r["manifest"]["report"]["slug"],
                      "limitations": r["limitations"],
                      "example": bool(r["manifest"].get("example")),
                      "input_type": r["manifest"].get("inputs", {}).get("type")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
