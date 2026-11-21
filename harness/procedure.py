"""Whose failure would this be, before any container is started.

A reviewer handing over a repository link needs the answer before Docker, and
needs it split three ways. A red result that mixes them is the failure mode
this exists to stop:

  tool      the commit states an install a third party can execute (its own
            Dockerfile with a supported, cited build command), STRhub holds
            the input, and the command was not
            rewritten past path substitution. A failure of that run is the
            tool's.
  strhub    STRhub would be supplying the environment, the input, a file, or
            a guess. A failure of that run is ours. It must not be published
            as the tool failing, and a success must not be published as the
            tool running as documented.
  recipe    the commit does not state a procedure, or states one whose input
            STRhub does not hold. Nothing was executed. That is a finding
            about the documentation or about our sample shelf, said as such.

Pure: no network, no Docker. The preview server and the verdict both read it.
"""
from __future__ import annotations

import re
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from prepare import unwrap_example  # noqa: E402
from prepare import example_wrapper  # noqa: E402
import fidelity  # noqa: E402

# Discovery families are not execution permissions. Only the versioned
# installation profile can establish a citable installation.
PACKABLE_FROM_REPO = {
    "dockerfile", "conda", "pip", "cmake", "make", "autotools", "cargo", "go", "r", "nim", "script", "release_binary",
}
PUBLISHED_INSTALL = {"docker_image", "bioconda"}


def _sentence(text: str) -> str:
    """A finding as one sentence: a capital to open it and a full stop to end it."""
    text = " ".join(str(text).split())
    if not text:
        return ""
    text = text[0].upper() + text[1:]
    return text if text[-1] in ".!?" else text + "."


def _flags(cmd: str) -> set[str]:
    return set(re.findall(r"(?:^|\s)(--[\w-]+|-\w)\b", cmd))


def _tool_text(cmd: str) -> str:
    """No shell prefix is automatically excused as harness plumbing."""
    return cmd


def _command_amendments(cited: str, rewritten: str, expected: str | None = None) -> list[dict]:
    """Compare the complete text after the closed, recorded substitutions.

    Even apparently harmless whitespace changes are not inferred equivalent:
    adjacency, quoted spaces, newlines and redirection descriptors matter.
    """
    out = []
    if not cited:
        return [{"code": "command_evidence_missing", "what": "No complete upstream command was established."}]
    if "[" in cited and "[" not in rewritten:
        out.append({"code": "synopsis_trimmed", "what": "A usage synopsis was changed instead of executed as documented."})
    baseline = expected if expected is not None else cited
    extra, missing = _flags(rewritten) - _flags(baseline), _flags(baseline) - _flags(rewritten)
    if extra:
        out.append({"code": "flag_injected", "what": "Flags added: " + ", ".join(sorted(extra))})
    if missing:
        out.append({"code": "flag_dropped", "what": "Flags removed: " + ", ".join(sorted(missing))})
    same = rewritten == baseline
    if not same:
        out.append({"code": "command_changed", "what": "The complete executed command differs from the cited command beyond the closed substitution table; executable, values, positional arguments, quoting, order and shell operators are all significant."})
    return out


def classify(proposal: dict, manifest: dict, limitations: list[str],
             caveat_items: list[str] | None = None) -> dict:
    """The review of one proposal. `may_say_runs` is the only bit the verdict
    needs: when it is false, a green gate ladder still cannot say the tool
    runs as documented."""
    proposal = proposal or {}
    manifest = manifest or {}
    limitations = list(limitations or [])
    notes = list(caveat_items or [])
    build = proposal.get("build") or {}
    method = build.get("method") or "unknown"
    source = (manifest.get("environment") or {}).get("source")
    citable = False
    published = method in PUBLISHED_INSTALL

    cited = ""
    commands = proposal.get("commands") or []
    if commands:
        cited = commands[0].get("cmd") or ""
    rewritten, _cwd = unwrap_example((manifest.get("run") or {}).get("cmd") or "")
    transformation = fidelity.rewrite_for(manifest, cited, proposal)
    prepared = source == "prepared"
    expected = transformation["command"]
    citations = [fidelity.cite(proposal, commands[0])] if commands else []
    if commands and commands[0].get("prerequisite"):
        prerequisite = commands[0]["prerequisite"]
        pre_review = fidelity.rewrite_for(manifest, prerequisite["cmd"], proposal)
        citations.append(fidelity.cite(proposal, prerequisite))
        transformation["limitations"] += pre_review["limitations"]
        transformation["prerequisite"] = pre_review
    amendments = _command_amendments(cited, rewritten, expected)
    if commands and commands[0].get("prerequisite"):
        amendments.append({"code": "prerequisite_profile_unsupported", "what": "A preceding command inferred from a shared filename is not proof of the documented execution sequence; it is not automatically chained."})
    raw_cmd = (manifest.get("run") or {}).get("cmd") or ""
    if _cwd is None:
        amendments.append({"code": "capture_wrapper_missing", "what": "This profile requires the exact evaluator capture wrapper so output routing is established before execution."})
    if _cwd is not None and raw_cmd != example_wrapper(rewritten, _cwd):
        amendments.append({"code": "capture_wrapper_changed", "what": "The capture wrapper differs from the evaluator's exact wrapper; no prefix or suffix may hide a procedure change."})
    if _cwd is not None and _cwd != ".":
        amendments.append({"code": "working_directory_changed", "what": "The command would run from a directory other than the root of the repository; this profile does not establish that change."})
    identity = ((manifest.get("source") or {}).get("ref") == proposal.get("ref")
                and str((manifest.get("source") or {}).get("repo", "")).removesuffix(".git").rstrip("/")
                == str(proposal.get("repo") or "").removesuffix(".git").rstrip("/"))
    if not identity or not citations or not all(c["verified"] for c in citations):
        amendments.append({"code": "command_evidence_missing", "what": "The complete command and prerequisite must be established at the cited lines of this same pinned upstream commit; wiki text or a recipe label is not proof."})
    if transformation["limitations"]:
        amendments.append({"code": "command_profile_unsupported", "what": " ".join(_sentence(item) for item in transformation["limitations"])})
    if (manifest.get("inputs") or {}).get("type") and not transformation["read_bindings"]:
        amendments.append({"code": "input_not_substituted", "what": "This evaluator cannot establish that the cited command reads the declared reference input; no config or input list was rewritten to make it do so."})
    inputs = manifest.get("inputs") or {}
    input_evidence = proposal.get("input_type") or {}
    declared_type = input_evidence.get("best")
    # In a run STRhub prepared, the dataset is the one its preparation names,
    # by hand and in the open: it was not swapped or counted by a heuristic.
    if declared_type and inputs.get("type") != declared_type and not prepared:
        amendments.append({"code": "input_swapped", "what": "The effective input type differs from the one selected from the original documentation."})
    if inputs.get("type") and input_evidence.get("platform_how") == "counted" and not prepared:
        amendments.append({"code": "input_platform_unproven", "what": "Counting platform mentions does not establish which shared dataset this procedure reads."})
    signals = input_evidence.get("signals") or {}
    asm = input_evidence.get("assembly") or {}
    if (re.search(r"-hg38(?:-|$)", inputs.get("type") or "")
            and (asm.get("incompatible_with_hg38") or (signals.get("hg19") and not signals.get("hg38")))):
        amendments.append({"code": "input_assembly_mismatch", "what": "The documentation names hg19/GRCh37 or declares hg38 incompatibility without establishing compatibility with the registered hg38 dataset."})
    installation = fidelity.installation(proposal, manifest)
    citable = installation["ready"]
    if installation["ready"] and not fidelity.image_invocation_supported(proposal, installation):
        amendments.append({"code": "image_invocation_unsupported", "what": "The upstream image does not declare the shell entrypoint this evaluator needs; ENTRYPOINT is not overridden or repaired."})
    install_gap = "strhub" if installation["ready"] else installation.get("gap", "strhub")
    if not installation["ready"]:
        # The documentation falls short of what the guide asks (the author can
        # close it), or this evaluator's profiles do (nothing is asked of them).
        amendments.append({"code": "install_not_copyable" if install_gap == "commit" else "install_profile_unsupported",
                           "what": installation["reason"]})

    if any("holds no reference sample as" in n or "other documented kind was used" in n for n in notes):
        amendments.append({"code": "input_swapped",
                           "what": "The input kind this run would use is not the one the documentation "
                                   "names first: STRhub substituted a kind it holds a sample of."})
    if "input_type_guessed" in limitations:
        amendments.append({"code": "input_guessed",
                           "what": "No sentence states what the tool reads, so the sample was chosen "
                                   "from mentions alone."})
    tool_cmd = _tool_text(rewritten)
    if any("could not resolve" in n for n in notes):
        amendments.append({"code": "synopsis_trimmed",
                           "what": "The command contains placeholders that neither the repository nor "
                                   "STRhub's substitution table can fill in."})
    has_shipped_example = bool((manifest.get("example") or {}).get("cmd") or (proposal.get("example") or {}).get("cmd"))
    # A data file that is still the path from the README was not pointed at
    # STRhub's sample, and if the repository does not ship those files either,
    # running that command would fail with "file not found" of our staging.
    if cited and not has_shipped_example \
            and re.search(r"\.(?:bam|cram|sam|fastq|fq|fasta|fa|bed|vcf)(?:\.gz)?\b|\b(?:bam|fastq|read|sample)[_-]?list\b", tool_cmd, re.I) \
            and "/data/in" not in tool_cmd and "/data/ref" not in tool_cmd:
        amendments.append({"code": "input_not_substituted",
                           "what": "The command still names the repository's own file paths, not STRhub's "
                                   "sample. Running it would not be the reference-sample test."})
    if any("HTTPS instead" in n for n in notes):
        amendments.append({"code": "ssh_rewritten",
                           "what": "A build step fetches dependencies over SSH; STRhub would rewrite that "
                                   "to HTTPS, which is a change to the procedure."})
    glob = ((manifest.get("outputs") or [{}])[0].get("path"))
    if glob in ("**/*", "**/*.*"):
        amendments.append({"code": "output_unnamed",
                           "what": "The documentation does not name an output file, so any file the "
                                   "wrapper copied would have been counted as the documented output."})
    if proposal and method not in PACKABLE_FROM_REPO and method not in PUBLISHED_INSTALL:
        amendments.append({"code": "no_install_procedure",
                           "what": "This commit does not state an install procedure a third party can execute."})
    if published and not citable:
        amendments.append({"code": "published_image",
                           "what": "The install named here is a published image or package. That is a claim "
                                   "about the image, not about this commit, and it was not counted as the commit running."})

    # Mandatory traceability (`evidence_source`) for every parameter inferred or applied.
    inst_cite = (installation.get("citation")
                 or (installation.get("documented_installation") or {}).get("citation") or {})
    if inst_cite.get("path"):
        inst_start = inst_cite.get("start_line") or inst_cite.get("line")
        inst_end = inst_cite.get("end_line") or inst_start
        inst_es = (f"{inst_cite['path']}:L{inst_start}-L{inst_end}"
                   if inst_start and inst_end and inst_start != inst_end
                   else f"{inst_cite['path']}:L{inst_start}" if inst_start else f"repo_file:{inst_cite['path']}")
    elif installation.get("file"):
        inst_es = installation["file"]
    else:
        inst_es = build.get("evidence_source")

    c0 = citations[0] if citations else {}
    cmd_es = (f"{c0['path']}:L{c0['line']}-L{c0['end_line']}" if c0.get("end_line")
              else f"{c0['path']}:L{c0['line']}") if c0.get("verified") else (
              commands[0].get("evidence_source") if commands else None)

    inferences: dict[str, dict] = {
        "install": {
            "evidence_source": inst_es,
            "verified": bool(installation.get("ready") and inst_es),
        },
        "run_command": {
            "evidence_source": cmd_es,
            "verified": bool(citations and all(c.get("verified") for c in citations)),
            **({"kind": "doc", "path": c0["path"], "document_sha256": c0.get("document_sha256")}
               if c0.get("verified") else {}),
        },
    }
    upstream_inputs = (input_evidence.get("statements") or {}).get("inputs") or []
    upstream_kind = upstream_inputs[0]["kind"] if upstream_inputs else (
        "bam" if "bam" in (inputs.get("type") or "") else "fastq" if "fastq" in (inputs.get("type") or "") else None
    )
    if inputs.get("type"):
        if prepared:
            inferences["input_type"] = {
                "evidence_source": installation.get("file") or "preparation",
                "verified": bool(installation.get("ready")),
                "upstream_input_kind": upstream_kind,
                "selected_dataset": inputs.get("type"),
            }
        elif input_evidence.get("how") == "counted" or "input_type_guessed" in limitations:
            inferences["input_type"] = {"evidence_source": None, "verified": False}
        elif input_evidence.get("evidence_source"):
            ver = fidelity.verify_evidence_source(proposal, input_evidence.get("evidence_source"))
            inferences["input_type"] = {
                **ver,
                "upstream_input_kind": upstream_kind,
                "selected_dataset": inputs.get("type"),
            }
        elif c0.get("verified") and transformation["read_bindings"]:
            inferences["input_type"] = {
                "verified": True, "kind": "doc", "path": c0["path"], "line": c0["line"],
                "document_sha256": c0.get("document_sha256"),
                "evidence_source": f"{c0['path']}:L{c0['line']}",
                "upstream_input_kind": upstream_kind,
                "selected_dataset": inputs.get("type"),
            }
        else:
            inferences["input_type"] = {"evidence_source": None, "verified": False}
    plat_how = input_evidence.get("platform_how")
    sup_plats = input_evidence.get("supported_platforms") or []
    if inputs.get("type") and not prepared and plat_how in ("stated", "multi_stated"):
        selected_plat = input_evidence.get("platform")
        plat_es = input_evidence.get("platform_evidence_source") or next(
            (p.get("evidence_source") for p in sup_plats if p.get("platform") == selected_plat), None
        )
        ver_p = fidelity.verify_evidence_source(proposal, plat_es) if plat_es else {"verified": False, "evidence_source": None}
        inferences["platform"] = {
            **ver_p,
            "selected": selected_plat,
            "selection_basis": "harness_choice_from_supported" if plat_how == "multi_stated" else "upstream_single_platform",
            "supported_platforms": [p["platform"] for p in sup_plats] if sup_plats else ([selected_plat] if selected_plat else []),
        }
    reg = proposal.get("regions") or {}
    cmd_uses_regions = any(t in fidelity.REGION_FLAGS or (t.split("=", 1)[0] in fidelity.REGION_FLAGS if "=" in t else False)
                           for t in cited.split())
    if reg.get("ambiguous") and (inputs.get("regions") or cmd_uses_regions) and not prepared:
        cand_names = ", ".join(c["format"] for c in (reg.get("candidates") or []) if c.get("format"))
        amendments.append({
            "code": "ambiguous_regions_schema",
            "what": f"The repository documents multiple conflicting region schemas ({cand_names}); STRhub cannot deterministically pick one.",
        })
    if inputs.get("regions"):
        if prepared:
            inferences["regions"] = {
                "evidence_source": installation.get("file") or "preparation",
                "verified": bool(installation.get("ready")),
            }
        else:
            ver = fidelity.verify_evidence_source(proposal, reg.get("evidence_source"), reg.get("text"))
            inferences["regions"] = {
                **ver,
                "verified": bool(ver.get("verified") and reg.get("format") == inputs.get("regions")),
            }
            if not inferences["regions"]["verified"]:
                amendments.append({
                    "code": "unbacked_inference",
                    "what": "The declared regions layout lacks a verified documentary citation in the repository.",
                })
    if any(s.get("role") == "read_path" and "," in s.get("original", "")
           for s in transformation.get("substitutions") or []):
        if prepared:
            inferences["single_sample_bams"] = {
                "evidence_source": installation.get("file") or "preparation",
                "verified": bool(installation.get("ready")),
            }
        else:
            ss = proposal.get("single_sample_bams") or {}
            ver = fidelity.verify_evidence_source(proposal, ss.get("evidence_source"), ss.get("text"))
            paired_flags = ss.get("paired_flags") or []
            paired_ok = True
            paired_sources = []
            reduced_roles = {s.get("role") for s in transformation.get("substitutions") or []}
            for req_role, req_flag in (("sample_list", "--bam-samps"), ("library_list", "--bam-libs")):
                if req_role not in reduced_roles:
                    continue
                entry = next((p for p in paired_flags if p.get("flag") == req_flag), None)
                pver = fidelity.verify_evidence_source(
                    proposal, (entry or {}).get("evidence_source"), (entry or {}).get("text")
                )
                if not entry or not pver.get("verified"):
                    paired_ok = False
                else:
                    paired_sources.append(entry["evidence_source"])
            inferences["single_sample_bams"] = {
                **ver,
                "verified": bool(ver.get("verified") and ss.get("allowed") and paired_ok),
                **({"paired_evidence_sources": paired_sources} if paired_sources else {}),
            }
            if not inferences["single_sample_bams"]["verified"]:
                amendments.append({
                    "code": "unbacked_inference",
                    "what": "Single-sample substitution of a comma-separated input list lacks a verified documentary citation in the repository.",
                })
    out_info = proposal.get("output") or {}
    if out_info.get("evidence_source"):
        inferences["output"] = fidelity.verify_evidence_source(proposal, out_info.get("evidence_source"))
    elif glob not in ("**/*", "**/*.*", None) and c0.get("verified"):
        inferences["output"] = {
            "verified": True, "kind": "doc", "path": c0["path"], "line": c0["line"],
            "document_sha256": c0.get("document_sha256"),
            "evidence_source": f"{c0['path']}:L{c0['line']}",
        }
    else:
        inferences["output"] = {"evidence_source": None, "verified": False}

    unbacked_inferences = sorted(k for k, v in inferences.items() if not v.get("verified"))
    if unbacked_inferences and not amendments:
        amendments.append({
            "code": "unbacked_inference",
            "what": "Inferred parameters lack a verified documentary citation in the repository: "
                    + ", ".join(unbacked_inferences) + ".",
        })

    # One lead, in the order a reviewer should read it. The first match is
    # why we will not call a red result the tool's.
    if not proposal:
        blocker, basis = "procedure_evidence_missing", "strhub"
    elif "no_reference_dataset" in limitations:
        blocker, basis = "missing_input", "recipe"
    elif not installation["ready"] and method != "unknown" and install_gap == "commit":
        blocker, basis = "install_not_copyable", "recipe"
    elif not installation["ready"] and method != "unknown":
        blocker, basis = "install_profile_unsupported", "strhub"
    elif any(a["code"] == "ambiguous_regions_schema" for a in amendments):
        blocker, basis = "ambiguous_regions_schema", "recipe"
    elif "documented_file_missing" in limitations:
        blocker, basis = "missing_file", "recipe"
    elif any(a["code"] == "input_not_substituted" for a in amendments):
        blocker, basis = "input_not_substituted", "strhub"
    elif "no_command" in limitations:
        blocker, basis = "no_command", "recipe"
    elif any(a["code"] == "no_install_procedure" for a in amendments):
        blocker, basis = "no_install_procedure", "recipe"
    elif any(a["code"] == "published_image" for a in amendments):
        blocker, basis = "published_image", "strhub"
    elif amendments:
        blocker, basis = amendments[0]["code"], "strhub"
    else:
        blocker, basis = "ready", "gates"

    may_say_runs = blocker == "ready"
    if may_say_runs:
        status_code = "VERIFIED_PROCEDURE_READY"
    elif blocker in ("command_profile_unsupported", "synopsis_trimmed", "flag_injected", "flag_dropped",
                     "command_changed", "prerequisite_profile_unsupported", "working_directory_changed",
                     "capture_wrapper_missing", "capture_wrapper_changed", "input_not_substituted",
                     "ambiguous_regions_schema"):
        status_code = "FAILED_AMBIGUOUS_CLI"
    else:
        status_code = "UNVERIFIED_INSUFFICIENT_DOCS"

    if may_say_runs:
        reason = ("The repository states how to install (" + method + ") and STRhub holds the sample. "
                  "The container is that install, packaged. If the documented command then fails, "
                  "the failure is that command's.")
        attribution = "tool"
    elif basis == "recipe":
        reason = next((a["what"] for a in amendments if a["code"] == blocker), "")
        if not reason:
            reason = {
                "missing_input": "STRhub holds no reference sample of the kind this procedure reads, "
                                 "and the repository ships no example to run, so nothing was executed.",
                "missing_file": "The documented command reads a file that neither the repository nor "
                                "STRhub holds, so the command was not run.",
                "no_command": "No command line invoking the tool was found in the commit, so nothing was run.",
            }.get(blocker, "STRhub could not complete a procedure stated at this commit.")
        attribution = "strhub"
    else:
        # What stopped it first, then everything else the review found, each
        # as a sentence of its own: a reader gets the lead before the list.
        ordered = sorted(amendments, key=lambda a: a["code"] != blocker)
        reason = " ".join(dict.fromkeys(_sentence(a["what"]) for a in ordered))
        attribution = "strhub"

    asm_declared = asm.get("declared")
    if asm_declared is None and (signals.get("hg38") or signals.get("hg19")):
        asm_declared = "both" if (signals.get("hg38") and signals.get("hg19")) else ("hg38" if signals.get("hg38") else "hg19_only")
    dataset_id = inputs.get("type")
    ds_assembly = "hg38" if dataset_id and re.search(r"-hg38(?:-|$)", dataset_id) else None
    plat_list = ([{"platform": p["platform"], "evidence_source": p.get("evidence_source")} for p in sup_plats]
                 if sup_plats else ([{"platform": input_evidence.get("platform"), "evidence_source": input_evidence.get("platform_evidence_source")}]
                                    if plat_how in ("stated", "multi_stated") and input_evidence.get("platform") else []))
    subs = transformation.get("substitutions") or []
    ss_subs = [s for s in subs if s.get("role") == "read_path" and "," in s.get("original", "")]
    ss_paired = [s for s in subs if s.get("role") in ("sample_list", "library_list")]
    base_cond = installation.get("base_condition") or {}
    provenance = {
        "from_upstream": {
            "install": {"method": method, "evidence_source": inst_es},
            "command": {"value": cited, "evidence_source": cmd_es} if cited else None,
            "input_kind": {
                "value": upstream_kind,
                "evidence_source": (inferences.get("input_type") or {}).get("evidence_source"),
            } if upstream_kind else None,
            "supported_platforms": plat_list,
            "assembly": {
                "declared": asm_declared,
                "evidence_source": asm.get("evidence_source"),
            },
            "regions_schema": {
                "format": reg.get("format"),
                "evidence_source": reg.get("evidence_source"),
            } if reg.get("format") else None,
            "output_format": {
                "glob": glob,
                "evidence_source": (inferences.get("output") or {}).get("evidence_source"),
            } if glob not in ("**/*", "**/*.*", None) else None,
        },
        "derived": {
            "command_rewrites": [
                {"role": s.get("role"), "original": s.get("original"), "replacement": s.get("replacement"), "basis": s.get("basis")}
                for s in subs
            ],
            "regions_layout_binding": {
                "documented_schema": reg.get("format"),
                "evidence_source": reg.get("evidence_source"),
                "strhub_regions_layout": inputs.get("regions"),
            } if inputs.get("regions") else None,
            "single_sample_adaptation": {
                "applied": True,
                "original": ss_subs[0]["original"],
                "replacement": ss_subs[0]["replacement"],
                "evidence_source": (inferences.get("single_sample_bams") or {}).get("evidence_source"),
                **({"paired_substitutions": [
                    {"role": s["role"], "original": s["original"], "replacement": s["replacement"]}
                    for s in ss_paired
                ], "paired_evidence_sources": (inferences.get("single_sample_bams") or {}).get("paired_evidence_sources") or []}
                   if ss_paired else {}),
                "note": "STRhub trial mounted one compatible sample for the documented multi-file placeholder list",
            } if ss_subs else None,
        },
        "harness_choices": {
            "dataset": {
                "selected": dataset_id,
                "reason": (f"STRhub selected '{dataset_id}' as compatible with upstream input '{upstream_kind}'"
                           + (f" and platform '{input_evidence.get('platform')}'" if input_evidence.get("platform") else "")
                           + (f"; shipped catalog '{input_evidence['panel_match']['catalog_file']}' overlaps "
                              f"{input_evidence['panel_match']['medical_overlap']} medical panel loci and 0 forensic loci"
                              if input_evidence.get("panel_match") and dataset_id == input_evidence["panel_match"].get("dataset")
                              else ""))
                          if dataset_id else None,
            } if dataset_id else None,
            "platform": {
                "selected": input_evidence.get("platform"),
                "basis": ("harness_choice_from_supported" if plat_how == "multi_stated"
                          else "upstream_single_platform" if plat_how == "stated"
                          else "counted_unproven"),
                "supported_platforms": [p["platform"] for p in plat_list],
            } if input_evidence.get("platform") else None,
            "assembly": {
                "selected": ds_assembly,
                "basis": ("upstream_stated" if asm_declared in ("hg38", "both")
                          else "harness_choice_unstated" if ds_assembly and not asm_declared
                          else "incompatible"),
                "note": ("Upstream did not specify an assembly; STRhub supplied an internally coherent hg38 BAM, FASTA and regions set"
                         if ds_assembly and not asm_declared else None),
            } if ds_assembly or asm_declared else None,
            "regions_layout": inputs.get("regions"),
            "base_environment": {
                "image": base_cond.get("image"),
                "description": base_cond.get("description"),
                "added_packages": list(base_cond.get("added_packages") or []),
                "miniforge": bool(base_cond.get("miniforge")),
                "submodules": bool(base_cond.get("submodules")),
            } if base_cond else None,
        },
    }

    return {
        "may_say_runs": may_say_runs,
        "status_code": status_code,
        "basis": basis,
        "attribution": attribution,
        "blocker": blocker,
        "reason": reason,
        "amendments": amendments,
        "inferences": inferences,
        "unbacked_inferences": unbacked_inferences,
        "provenance": provenance,
        "install_method": method,
        "citable_install": citable,
        "input_type": (manifest.get("inputs") or {}).get("type"),
        "output_glob": glob,
        "profile": fidelity.PROFILE,
        "install_ready": installation["ready"],
        # The repository's own example can be run as documented: the install
        # is admitted and the example's command is cited, whole, at the commit.
        # It needs nothing of STRhub's, so it does not wait for `may_say_runs`,
        # which is about the run on STRhub's sample.
        "example_ready": bool(installation["ready"] and fidelity.example_citation(proposal, manifest)),
        "installation": installation,
        "command_review": {**transformation, "expected": expected, "executed": rewritten,
                           "cited_sha256": fidelity.digest(cited),
                           "executed_sha256": fidelity.digest(rewritten), "citations": citations},
    }
