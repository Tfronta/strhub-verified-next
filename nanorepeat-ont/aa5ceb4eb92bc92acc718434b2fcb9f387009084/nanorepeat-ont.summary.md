# STRhub Verified: NanoRepeat (nanorepeat-ont)

**Could not be determined.**

## As it is in the repository

**Step 1, the documented run: As documented, a third party cannot tell how to run it.** The documented command reads a file that neither the repository nor STRhub holds, so the command was not run. Nothing was executed. That does not mean the tool does not work: what the guide asks for is missing from the README at this commit. Add it and try the link again on the new commit.

Missing from the commit, by the blocks docs/GUIA-PASO-1.md asks for:

- The declared input

**Verdict: Could not be determined.** The documented command reads a file that neither the repository nor STRhub holds, so the command was not run.

What stopped it, and what its owner can be asked:

- The documented command reads a file that is not in the repository at this commit and that STRhub does not hold, so the command cannot run as written.
  - The tool's owner: open an issue, "Ship, or link from the README, the file the documented command reads".
- The environment did not build from the install steps found in the repository.
  - The tool's owner: open an issue, "Build fails from a clean checkout".

Reached **Available**: the pinned public source exists.

### Gates

| Gate | Status | Meaning |
|---|---|---|
| Available | PASS | the pinned public source exists |
| Installs | — | the environment builds from source |
| Runs | — | it executes end-to-end without crashing |
| Runs + Expected IO | — | it produces a non-empty file in the declared format |
| Runs + Plausible output | — | its output looks like plausible genotype-bearing data (declared columns, DNA sequences, integer read counts, and enough recognisable forensic loci) |

### It did not build from source

STRhub tried to build the tool from its source at the pinned commit, following the build steps the repository declares, and the build failed. Nothing below the Installs gate ran.

What this means:

- **If you are trying to run it:** A build from source at this commit stopped in a clean environment; the observed build log lines are cited below.
- **If you are reviewing a paper:** Nothing ran, so this says nothing about the software's output. It records that this build attempt stopped at the Installs stage and cites the observed build log lines below.
- **If you maintain it:** Observed in the build log: the build stopped on missing packages, headers, or declared build steps during the executed install sequence. Whether the omission originates in the upstream documentation, an implicit dependency, or environment differences is not automatically determined from the log alone. Re-verifying after updating the repository is free.

What failed:

| What happened | Times | What the log establishes |
|---|---|---|
| pip cannot resolve a pinned dependency: pyminimap2>=2.30.0 | 4 | pip could not resolve 'pyminimap2>=2.30.0' as pinned: that version is not on PyPI, or is incompatible with the base image's Python. The pin is the build's as cited. |

Full build output: [`nanorepeat-ont.log-build.txt`](nanorepeat-ont.log-build.txt)

### Author-documented warnings and limitations

Quoted from the repository's README at the verified commit. STRhub did not establish any of this by running the tool; it is the author's own note about their own software.

**Limitation** (README line 296)

> NanoRepeat can accuratly quantify simple repeats but cannot handle mixed repeats of different motifs (i.e. a mixture of `GCCA` and `AAATT`), but imperfect repeats of approximately the same motif are OK.

### Planned command

The run step was skipped. This command was not executed by that step.

```
cd '.' && touch /tmp/.strhub_mark && ( nanoRepeat.py -i path/to/NanoRepeat_v1.3_example_data/HG002/hg002_Q20.20210805_3flowcells.hs37d5.example_regions.bam -t bam -d ont_q20 -r path/to/NanoRepeat_v1.3_example_data/HG002/GRCh37_chr1.fasta -b path/to/NanoRepeat_v1.3_example_data/HG002/HG002_GRCh37_example_regions.bed -c 4 --samtools path/to/samtools --minimap2 path/to/minimap2 -o ./nanorepeat_output/HG002 ); rc=$?; find . -xdev -type f -newer /tmp/.strhub_mark -size +0 ! -path './.git/*' ! -path './proc/*' ! -path './sys/*' ! -path './dev/*' ! -path './data/*' ! -path '*/__pycache__/*' ! -name '*.pyc' ! -name '*.pyo' 2>/dev/null | head -500 | while IFS= read -r f; do mkdir -p "/data/out/$(dirname "$f")" && cp "$f" "/data/out/$f"; done; exit $rc
```
- Log (build): [`nanorepeat-ont.log-build.txt`](nanorepeat-ont.log-build.txt)

## Run details

- Source: `https://github.com/WGLab/NanoRepeat` @ `aa5ceb4eb92bc92acc718434b2fcb9f387009084`
- Environment: ubuntu-22.04 (`Dockerfile`)
- Generated: 2026-11-22T19:15:26+00:00
- Upstream: The verified commit is 1 commit(s) behind `master`. That is context, not a fault: a pinned release is often meant to sit behind, and the attestation describes the commit it names.
- CI run: https://github.com/Tfronta/strhub-verified-next/actions/runs/45059567503

## Verification matrix

| Leg | Available | Result | Errors reported | Dataset |
|---|---|---|---|---|
| External data | N/A | N/A | — | None |
| Tool's own example | N/A | N/A | — | — |

## Evidence

What this run's configuration rests on, each item at the verified commit. Open any of them to check the claim it supports.
- Install method: [`pyproject.toml`](https://github.com/WGLab/NanoRepeat/blob/aa5ceb4eb92bc92acc718434b2fcb9f387009084/pyproject.toml)
- Run command: [`README.md` line 69](https://github.com/WGLab/NanoRepeat/blob/aa5ceb4eb92bc92acc718434b2fcb9f387009084/README.md#L69): `nanoRepeat.py \`
- Example data: [`example_data/HTT_repeat_region.bed`](https://github.com/WGLab/NanoRepeat/blob/aa5ceb4eb92bc92acc718434b2fcb9f387009084/example_data/HTT_repeat_region.bed)
- Known issue: [`README.md` line 296](https://github.com/WGLab/NanoRepeat/blob/aa5ceb4eb92bc92acc718434b2fcb9f387009084/README.md#L296): `Limitation`
- Documented input: [`README.md` line 81](https://github.com/WGLab/NanoRepeat/blob/aa5ceb4eb92bc92acc718434b2fcb9f387009084/README.md#L81): ``-i` specifies the input file, which can be in `fasta`, `fastq` or `bam` format.`

## Provenance of this trial (upstream vs. STRhub choices)

### From upstream documentation

- Install (pip): `README.md:L28-L32`
- Command: `README.md:L69`
- Input format: `bam` (`README.md:L81`)
- Supported platforms: ont (`README.md:L1`), pacbio (`README.md:L1`)
- Reference assembly: `both` (`README.md:L87`)
- Regions schema: `motif` (`README.md:L89`)

### Selected by STRhub for this trial

- Dataset selected by STRhub: `ont-bam-hg38` — STRhub selected 'ont-bam-hg38' as compatible with upstream input 'bam' and platform 'ont'
- Platform chosen by STRhub: `ont` from documented platforms (ont, pacbio)
- Base environment supplied by STRhub: `ubuntu:22.04`; added beyond plain Ubuntu: Miniforge (conda, python, pip)

## What this run needed beyond the repository

The result above describes a run configured as follows. Anyone repeating it needs the same things.

- A base environment for the documented installation: STRhub ran the repository's install commands unchanged on Ubuntu 22.04, package lists refreshed, apt answering yes, plus Miniforge (conda, python, pip). Base-image and package versions are not frozen by the commands.

## Notes from reading the repository

Recorded automatically from the tool's public files when this run was configured. **Not verified by execution**, and not part of the gates above. Useful for what to check by hand.

- Environment: STRhub transcribed the documented installation commands unchanged into its own carrier (Ubuntu 22.04, package lists refreshed, apt answering yes, plus Miniforge (conda, python, pip)).
- Input: the README documents BAM and FASTQ (line 81); this plan selects STRhub's ont-bam-hg38 reference data. Supported platforms documented: ont, pacbio; STRhub selected ont for this trial.
- Evaluator limitation: the command names a different assembly from the registered hg38 dataset.
- Run command: the README's own command, rewritten to STRhub's mounts; the capture wrapper is planned only if the procedure review passes.
- File: the documented command reads path/to/NanoRepeat_v1.3_example_data/HG002/HG002_GRCh37_example_regions.bed (after -b), which is neither in the repository nor among STRhub's data.

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

