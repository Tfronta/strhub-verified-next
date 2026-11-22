# STRhub Verified: RepeatHMM (repeathmm-ont)

**Could not be determined.**

## As it is in the repository

**Step 1, the documented run: As documented, a third party cannot tell how to run it.** No repository document shows an installation this profile can transcribe literally; no missing step, dependency or choice was supplied by STRhub. Nothing was executed. That does not mean the tool does not work: what the guide asks for is missing from the README at this commit. Add it and try the link again on the new commit.

Missing from the commit, by the blocks docs/GUIA-PASO-1.md asks for:

- Installation, copyable

**Verdict: Could not be determined.** No repository document shows an installation this profile can transcribe literally; no missing step, dependency or choice was supplied by STRhub.

What stopped it, and what its owner can be asked:

- No repository document shows an installation this profile can transcribe literally; no missing step, dependency or choice was supplied by STRhub.
  - The tool's owner: open an issue, "Write the installation as commands that can be copied and run".

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
cd '.' && touch /tmp/.strhub_mark && ( python repeatHMM.py BAMinput --Onebamfile XXX.bam --repeatName HTT; ); rc=$?; find . -xdev -type f -newer /tmp/.strhub_mark -size +0 ! -path './.git/*' ! -path './proc/*' ! -path './sys/*' ! -path './dev/*' ! -path './data/*' ! -path '*/__pycache__/*' ! -name '*.pyc' ! -name '*.pyo' 2>/dev/null | head -500 | while IFS= read -r f; do mkdir -p "/data/out/$(dirname "$f")" && cp "$f" "/data/out/$f"; done; exit $rc
```

## Run details

- Source: `https://github.com/WGLab/RepeatHMM` @ `fa6c108fa0cc8ab344577147e52a8fcc3adde990`
- Environment: ubuntu-22.04 (`Dockerfile`)
- Generated: 2026-11-22T19:14:51+00:00
- Upstream: The verified commit is 8 commit(s) behind `master`. That is context, not a fault: a pinned release is often meant to sit behind, and the attestation describes the commit it names.
- CI run: https://github.com/Tfronta/strhub-verified-next/actions/runs/45059573616

## Verification matrix

| Leg | Available | Result | Errors reported | Dataset |
|---|---|---|---|---|
| External data | N/A | N/A | — | None |
| Tool's own example | N/A | N/A | — | — |

## Evidence

What this run's configuration rests on, each item at the verified commit. Open any of them to check the claim it supports.
- Install method: [`environment.yml`](https://github.com/WGLab/RepeatHMM/blob/fa6c108fa0cc8ab344577147e52a8fcc3adde990/environment.yml)
- Run command: [`docs/Usage.md` line 226](https://github.com/WGLab/RepeatHMM/blob/fa6c108fa0cc8ab344577147e52a8fcc3adde990/docs/Usage.md#L226): `python repeatHMM.py BAMinput --Onebamfile XXX.bam --repeatName HTT;`
- Documented input: [`README.md` line 23](https://github.com/WGLab/RepeatHMM/blob/fa6c108fa0cc8ab344577147e52a8fcc3adde990/README.md#L23): `RepeatHMM takes long reads from a subject as input, and can also take a BAM file as input to find more than 10 predefined trinucleotide repeats or a gene given by users, after all reads were well alig`

## Provenance of this trial (upstream vs. STRhub choices)

### From upstream documentation

- Install (conda): `repo_file:environment.yml`
- Command: `docs/Usage.md:L226`
- Input format: `bam` (`README.md:L23`)
- Supported platforms: ont (`README.md:L1`)
- Reference assembly: `both` (`docs/Usage.md:L62`)

### Selected by STRhub for this trial

- Dataset selected by STRhub: `ont-bam-hg38` — STRhub selected 'ont-bam-hg38' as compatible with upstream input 'bam' and platform 'ont'
- Platform used: `ont` (single documented platform)

## Notes from reading the repository

Recorded automatically from the tool's public files when this run was configured. **Not verified by execution**, and not part of the gates above. Useful for what to check by hand.

- Environment: no proven installation profile; STRhub did not manufacture installation steps.
- Input: the README documents BAM (line 23); this plan selects STRhub's ont-bam-hg38 reference data.
- Evaluator limitation: a read-file argument is outside the closed input substitution table.
- Run command: the one documented in docs/Usage.md (line 226), rewritten to STRhub's mounts; the capture wrapper is planned only if the procedure review passes.

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

