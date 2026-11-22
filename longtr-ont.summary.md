# STRhub Verified: LongTR (longtr-ont)

**Does not run as documented: stops at install.**

## As it is in the repository

**Step 1, the documented run: As documented, it does not run.** The environment did not build from the declared install steps. That does not mean the tool does not work. It means a third party following the README at this commit did not reach the end. Fix the documentation, or the step that broke, and try the link again on the new commit.

**Verdict: Fails.** The environment did not build from the declared install steps.

What stopped it, and what its owner can be asked:

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
| Command not found: autoreconf | 2 | No 'autoreconf' executable was found on the container's PATH. The image is the one the review admits; nothing was added to it. |

Full build output: [`longtr-ont.log-build.txt`](longtr-ont.log-build.txt)

### Planned command

The run step was skipped. This command was not executed by that step.

```
cd '.' && touch /tmp/.strhub_mark && ( ./LongTR --bams             /data/in/input.bam --fasta            /data/ref/hg38.fa --regions          /data/in/regions.bed --tr-vcf           tr_calls.vcf.gz --bam-samps        SAMPLE1 --bam-libs         LIB1 ); rc=$?; find . -xdev -type f -newer /tmp/.strhub_mark -size +0 ! -path './.git/*' ! -path './proc/*' ! -path './sys/*' ! -path './dev/*' ! -path './data/*' ! -path '*/__pycache__/*' ! -name '*.pyc' ! -name '*.pyo' 2>/dev/null | head -500 | while IFS= read -r f; do mkdir -p "/data/out/$(dirname "$f")" && cp "$f" "/data/out/$f"; done; exit $rc
```
- Log (build): [`longtr-ont.log-build.txt`](longtr-ont.log-build.txt)

## Run details

- Source: `https://github.com/gymrek-lab/LongTR` @ `2be6cf5ec0b108601719c16171a3f0099d1cb88d`
- Environment: ubuntu-22.04 (`Dockerfile`)
- Generated: 2026-11-22T19:12:34+00:00
- Upstream: The verified commit is 8 commit(s) behind `master`. That is context, not a fault: a pinned release is often meant to sit behind, and the attestation describes the commit it names.
- CI run: https://github.com/Tfronta/strhub-verified-next/actions/runs/45059299441

## Verification matrix

| Leg | Available | Result | Errors reported | Dataset |
|---|---|---|---|---|
| External data | yes | — | — | 1000 Genomes ONT, hg38 CODIS slice (R10 SUP) |
| Tool's own example | N/A | N/A | — | — |

## Evidence

What this run's configuration rests on, each item at the verified commit. Open any of them to check the claim it supports.
- Install method: [`Makefile`](https://github.com/gymrek-lab/LongTR/blob/2be6cf5ec0b108601719c16171a3f0099d1cb88d/Makefile)
- Run command: [`README.md` line 127](https://github.com/gymrek-lab/LongTR/blob/2be6cf5ec0b108601719c16171a3f0099d1cb88d/README.md#L127): `./LongTR --bams             run1.bam,run2.bam,run3.bam,run4.cram`
- Example data: [`test/input/chr1_regions.bed`](https://github.com/gymrek-lab/LongTR/blob/2be6cf5ec0b108601719c16171a3f0099d1cb88d/test/input/chr1_regions.bed)
- Example data: [`test/input/chr1_regions_v2.bed`](https://github.com/gymrek-lab/LongTR/blob/2be6cf5ec0b108601719c16171a3f0099d1cb88d/test/input/chr1_regions_v2.bed)
- Example data: [`test_data/test_regions_hg38.bed`](https://github.com/gymrek-lab/LongTR/blob/2be6cf5ec0b108601719c16171a3f0099d1cb88d/test_data/test_regions_hg38.bed)
- Example data: [`test_data/HG002_sample_reads.bam`](https://github.com/gymrek-lab/LongTR/blob/2be6cf5ec0b108601719c16171a3f0099d1cb88d/test_data/HG002_sample_reads.bam)
- Example data: [`test_data/HG004_sample_reads.bam`](https://github.com/gymrek-lab/LongTR/blob/2be6cf5ec0b108601719c16171a3f0099d1cb88d/test_data/HG004_sample_reads.bam)
- Documented input: [`README.md` line 35](https://github.com/gymrek-lab/LongTR/blob/2be6cf5ec0b108601719c16171a3f0099d1cb88d/README.md#L35): `./LongTR --bams             long_read_sample1.bam,long_read_sample2.bam,...`

## Provenance of this trial (upstream vs. STRhub choices)

### From upstream documentation

- Install (make): `README.md:L25`
- Command: `README.md:L127-L132`
- Input format: `bam` (`README.md:L35`)
- Supported platforms: ont (`README.md:L1`), pacbio (`README.md:L1`)
- Reference assembly: not specified in repository documentation
- Regions schema: `motif` (`README.md:L142-L155`)

### Mechanically derived bindings

- `run1.bam,run2.bam,run3.bam,run4.cram` -> `/data/in/input.bam` (declared dataset mount)
- `genome.fa` -> `/data/ref/hg38.fa` (registered reference genome mount)
- `tr_regions.bed` -> `/data/in/regions.bed` (registered regions file (motif))
- `SAMPLE1,SAMPLE1,SAMPLE2,SAMPLE3` -> `SAMPLE1` (positional sample list aligned with single-sample BAM)
- `LIB1,LIB2,LIB3,LIB4` -> `LIB1` (positional library list aligned with single-sample BAM)
- Regions layout `motif` matched `motif` (`README.md:L142-L155`)
- Single-sample trial mount: `run1.bam,run2.bam,run3.bam,run4.cram` -> `/data/in/input.bam`; `SAMPLE1,SAMPLE1,SAMPLE2,SAMPLE3` -> `SAMPLE1`; `LIB1,LIB2,LIB3,LIB4` -> `LIB1` (`README.md:L42`, `README.md:L99`, `README.md:L100`)

### Selected by STRhub for this trial

- Dataset selected by STRhub: `ont-bam-hg38` — STRhub selected 'ont-bam-hg38' as compatible with upstream input 'bam' and platform 'ont'
- Platform chosen by STRhub: `ont` from documented platforms (ont, pacbio)
- Assembly chosen by STRhub: `hg38` (upstream unspecified; STRhub staged coherent BAM, FASTA and regions on hg38)
- Regions file mounted: `motif`
- Base environment supplied by STRhub: `ubuntu:22.04`; added beyond plain Ubuntu: minimal build toolchain: build-essential, git, ca-certificates (no tool-specific libraries)

## What this run needed beyond the repository

The result above describes a run configured as follows. Anyone repeating it needs the same things.

- Test data: a public reference sample was selected, but was not executed because installation did not complete.
- A base environment for the documented installation: STRhub ran the repository's install commands unchanged on Ubuntu 22.04, package lists refreshed, apt answering yes, plus minimal build toolchain (build-essential, git, ca-certificates; no tool-specific libraries). Base-image and package versions are not frozen by the commands.

## Notes from reading the repository

Recorded automatically from the tool's public files when this run was configured. **Not verified by execution**, and not part of the gates above. Useful for what to check by hand.

- Environment: STRhub transcribed the documented installation commands unchanged into its own carrier (Ubuntu 22.04, package lists refreshed, apt answering yes, plus minimal build toolchain (build-essential, git, ca-certificates; no tool-specific libraries)).
- Input: the README documents BAM (line 35); this plan selects STRhub's ont-bam-hg38 reference data. Supported platforms documented: ont, pacbio; STRhub selected ont for this trial.
- read_path: run1.bam,run2.bam,run3.bam,run4.cram -> /data/in/input.bam.
- reference_path: genome.fa -> /data/ref/hg38.fa.
- regions_path: tr_regions.bed -> /data/in/regions.bed.
- sample_list: SAMPLE1,SAMPLE1,SAMPLE2,SAMPLE3 -> SAMPLE1.
- library_list: LIB1,LIB2,LIB3,LIB4 -> LIB1.
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

