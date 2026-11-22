# STRhub Verified: lusSTR (lusstr-snp)

**Could not be determined.**

## As it is in the repository

**Step 1, the documented run: STRhub could not attempt the documented run.** STRhub holds no reference sample of the kind this procedure reads, and the repository ships no example to run, so nothing was executed. The limitation is ours. Nothing here is a finding about the tool.

**Verdict: Could not be determined.** STRhub holds no reference sample of the kind this procedure reads, and the repository ships no example to run, so nothing was executed.

What stopped it, and what its owner can be asked:

- STRhub has no reference sample of the kind this tool reads, and the repository ships no example to run, so nothing was executed.
  - The tool's owner: open an issue, "Ship a small example dataset".
- The environment did not build from the install steps found in the repository.
  - The tool's owner: open an issue, "Build fails from a clean checkout".

What the README does not say:

- The README's example commands do not show where the input file goes.

Reached **Available**: the pinned public source exists.

### Gates

| Gate | Status | Meaning |
|---|---|---|
| Available | PASS | the pinned public source exists |
| Installs | — | the environment builds from source |
| Runs | — | it executes end-to-end without crashing |
| Runs + Expected IO | — | it produces a non-empty file in the declared format |
| Runs + Plausible output | — | its output looks like plausible genotype-bearing data (declared columns, DNA sequences, integer read counts, and enough recognisable forensic loci) |

### What the README or repository could add

Read off the repository at the verified commit. None of these changes the result above; each would make the tool easier for a new user, and for STRhub, to run as documented.

- The repository ships no example input. A small example the documented command can read, with the output it should produce, would let any user reproduce the run without outside data.

### Planned command

The run step was skipped. This command was not executed by that step.

```
cd '.' && touch /tmp/.strhub_mark && ( lusstr strs all ); rc=$?; find . -xdev -type f -newer /tmp/.strhub_mark -size +0 ! -path './.git/*' ! -path './proc/*' ! -path './sys/*' ! -path './dev/*' ! -path './data/*' ! -path '*/__pycache__/*' ! -name '*.pyc' ! -name '*.pyo' 2>/dev/null | head -500 | while IFS= read -r f; do mkdir -p "/data/out/$(dirname "$f")" && cp "$f" "/data/out/$f"; done; exit $rc
```

## Run details

- Source: `https://github.com/bioforensics/lusSTR` @ `2425112706d03929ee3cf82588ddd6a2f315083c`
- Environment: ubuntu-22.04 (`Dockerfile`)
- Generated: 2026-11-22T19:13:53+00:00
- Upstream: The verified commit is 4 commit(s) behind `master`. That is context, not a fault: a pinned release is often meant to sit behind, and the attestation describes the commit it names.
- CI run: https://github.com/Tfronta/strhub-verified-next/actions/runs/45059493742

## Verification matrix

| Leg | Available | Result | Errors reported | Dataset |
|---|---|---|---|---|
| External data | N/A | N/A | — | None |
| Tool's own example | N/A | N/A | — | — |

## Evidence

What this run's configuration rests on, each item at the verified commit. Open any of them to check the claim it supports.
- Install method: [`setup.py`](https://github.com/bioforensics/lusSTR/blob/2425112706d03929ee3cf82588ddd6a2f315083c/setup.py)
- Fallback environment: [`README.md` line 37](https://github.com/bioforensics/lusSTR/blob/2425112706d03929ee3cf82588ddd6a2f315083c/README.md#L37): `conda install -c bioconda lusstr`
- Run command: [`README.md` line 112](https://github.com/bioforensics/lusSTR/blob/2425112706d03929ee3cf82588ddd6a2f315083c/README.md#L112): `lusstr strs all`

## Provenance of this trial (upstream vs. STRhub choices)

### From upstream documentation

- Install (pip): `repo_file:setup.py`
- Command: `README.md:L112`
- Input format: `fastq` (not explicitly stated)
- Reference assembly: not specified in repository documentation

### Selected by STRhub for this trial

- Dataset selected by STRhub: `illumina-snp-fastq` — STRhub selected 'illumina-snp-fastq' as compatible with upstream input 'fastq' and platform 'illumina'

## Notes from reading the repository

Recorded automatically from the tool's public files when this run was configured. **Not verified by execution**, and not part of the gates above. Useful for what to check by hand.

- Environment: no proven installation profile; STRhub did not manufacture installation steps.
- Input: no sentence in the README says what the tool takes; illumina-snp-fastq is only a guess from mentions; it is not authorization to execute.
- Run command: the README's own command, rewritten to STRhub's mounts; the capture wrapper is planned only if the procedure review passes.

## Out of scope

This report does not evaluate any of the following:

- Genotype correctness or accuracy
- Concordance against known truth sets
- Sensitivity, specificity, or stutter performance
- Allele calling accuracy or forensic casework suitability
- Regulatory compliance or ISO accreditation
- Multi-laboratory or multi-dataset reproducibility

## Limitations

- Single reference dataset per input type
- Single containerized environment (Docker / ubuntu-22.04)
- No truth-set comparison or ground-truth genotypes
- No accuracy or concordance assessment
- No forensic or clinical validation of results
- No sequencing data were processed because execution did not complete

## Scope (read this)

Assessment of documented execution in the stated environment and output format. Concerns reproducible execution only; no claim of accuracy, casework fitness, or regulatory validation.

This is **not** a claim that the genotypes are correct, nor that the tool is fit for casework or meets any regulatory standard. Concordance against known truth is out of scope.

Verified automatically, in a clean environment, on the tool's public source at the pinned commit. This is a record of what happened, not an endorsement by the tool's author.

