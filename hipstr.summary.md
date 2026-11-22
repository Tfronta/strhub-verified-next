# STRhub Verified: HipSTR (hipstr)

**Runs as documented.**

## As it is in the repository

**Step 1, the documented run: As documented, it runs.** A third party installed the tool with the steps this commit states and ran the command it writes, and the output file that command names appeared. This says nothing about genotypes or about concordance on any reference panel.

**Verdict: Runs.** The tool installed and its run produced its documented output.

Reached **Runs + Plausible output**: its output looks like plausible genotype-bearing data (declared columns, DNA sequences, integer read counts, and enough recognisable forensic loci).

### Gates

| Gate | Status | Meaning |
|---|---|---|
| Available | PASS | the pinned public source exists |
| Installs | PASS | the environment builds from source |
| Runs | PASS | it executes end-to-end without crashing |
| Runs + Expected IO | PASS | it produces a non-empty file in the declared format |
| Runs + Plausible output | PASS | its output looks like plausible genotype-bearing data (declared columns, DNA sequences, integer read counts, and enough recognisable forensic loci) |

### What the README or repository could add

Read off the repository at the verified commit. None of these changes the result above; each would make the tool easier for a new user, and for STRhub, to run as documented.

- The documented command reads a reference genome and the README does not say which assembly it expects. STRhub mounted hg38; stating the assembly would remove the guess.

### Command submitted to runner

The run step reported success. This is the configured command submitted to that step; the step exit status alone does not prove the program started.

```
cd '.' && touch /tmp/.strhub_mark && ( ./HipSTR --bams          /data/in/input.bam --fasta         /data/ref/hg38.fa --regions       /data/in/regions.bed --str-vcf       str_calls.vcf.gz ); rc=$?; find . -xdev -type f -newer /tmp/.strhub_mark -size +0 ! -path './.git/*' ! -path './proc/*' ! -path './sys/*' ! -path './dev/*' ! -path './data/*' ! -path '*/__pycache__/*' ! -name '*.pyc' ! -name '*.pyo' 2>/dev/null | head -500 | while IFS= read -r f; do mkdir -p "/data/out/$(dirname "$f")" && cp "$f" "/data/out/$f"; done; exit $rc
```
- Log (external): [`hipstr.log-external.txt`](hipstr.log-external.txt)
- Log (build): [`hipstr.log-build.txt`](hipstr.log-build.txt)

## Run details

- Source: `https://github.com/tfwillems/HipSTR` @ `12e989be4a8f9ab59f0c4c5da3784b82018cac82`
- Environment: ubuntu-22.04 (`Dockerfile`)
- Generated: 2026-11-22T19:14:06+00:00
- Upstream: The verified commit is 1 commit(s) behind `master`. That is context, not a fault: a pinned release is often meant to sit behind, and the attestation describes the commit it names.
- CI run: https://github.com/Tfronta/strhub-verified-next/actions/runs/45059250503

## Output content (plausibility evidence)

- Sequence records: **21** (malformed: 0)
- STR loci detected: **21**
- Total reads across calls: **7851** (deepest single sequence: 517)
- STR loci: CSF1PO, D10S1248, D12S391, D13S317, D16S539, D18S51, D19S433, D1S1656, D22S1045, D2S441, D3S1358, D5S818, D6S1043, D7S820, D8S1179, FGA, PentaD, PentaE …
- Top markers by read depth: D18S51 (517), FGA (477), vWA (456), PentaD (431), D2S441 (428), D3S1358 (419)

## Verification matrix

| Leg | Available | Result | Errors reported | Dataset |
|---|---|---|---|---|
| External data | yes | PASS | — | Illumina BAM (hg38), NA12878 (autosomal, female) |
| Tool's own example | N/A | N/A | — | — |

## Evidence

What this run's configuration rests on, each item at the verified commit. Open any of them to check the claim it supports.
- Install method: [`Makefile`](https://github.com/tfwillems/HipSTR/blob/12e989be4a8f9ab59f0c4c5da3784b82018cac82/Makefile)
- Run command: [`README.md` line 69](https://github.com/tfwillems/HipSTR/blob/12e989be4a8f9ab59f0c4c5da3784b82018cac82/README.md#L69): `./HipSTR --bams          run1.bam,run2.bam,run3.bam,run4.bam`
- Example data: [`test/input/chr1_regions.bed`](https://github.com/tfwillems/HipSTR/blob/12e989be4a8f9ab59f0c4c5da3784b82018cac82/test/input/chr1_regions.bed)
- Example data: [`test/input/chr1_regions_v2.bed`](https://github.com/tfwillems/HipSTR/blob/12e989be4a8f9ab59f0c4c5da3784b82018cac82/test/input/chr1_regions_v2.bed)
- Example data: [`test/input/1kg.chr1.imputed.vcf.gz`](https://github.com/tfwillems/HipSTR/blob/12e989be4a8f9ab59f0c4c5da3784b82018cac82/test/input/1kg.chr1.imputed.vcf.gz)
- Documented input: [`README.md` line 69](https://github.com/tfwillems/HipSTR/blob/12e989be4a8f9ab59f0c4c5da3784b82018cac82/README.md#L69): `./HipSTR --bams          run1.bam,run2.bam,run3.bam,run4.bam`
- Platform advice: [`README.md` line 435](https://github.com/tfwillems/HipSTR/blob/12e989be4a8f9ab59f0c4c5da3784b82018cac82/README.md#L435): `We do not recommend running it on PacBio or Oxford Nanopore data, as the difference in error profiles will be problematic`

## Provenance of this trial (upstream vs. STRhub choices)

### From upstream documentation

- Install (make): `README.md:L49-L59`
- Command: `README.md:L69-L72`
- Input format: `bam` (`README.md:L69`)
- Supported platforms: illumina (`README.md:L36`)
- Reference assembly: not specified in repository documentation
- Regions schema: `hipstr` (`README.md:L308-L322`)

### Mechanically derived bindings

- `run1.bam,run2.bam,run3.bam,run4.bam` -> `/data/in/input.bam` (declared dataset mount)
- `genome.fa` -> `/data/ref/hg38.fa` (registered reference genome mount)
- `str_regions.bed` -> `/data/in/regions.bed` (registered regions file (hipstr))
- Regions layout `hipstr` matched `hipstr` (`README.md:L308-L322`)
- Single-sample trial mount: `run1.bam,run2.bam,run3.bam,run4.bam` -> `/data/in/input.bam` (`README.md:L75`)

### Selected by STRhub for this trial

- Dataset selected by STRhub: `illumina-bam-hg38` — STRhub selected 'illumina-bam-hg38' as compatible with upstream input 'bam' and platform 'illumina'
- Platform used: `illumina` (single documented platform)
- Assembly chosen by STRhub: `hg38` (upstream unspecified; STRhub staged coherent BAM, FASTA and regions on hg38)
- Regions file mounted: `hipstr`
- Base environment supplied by STRhub: `ubuntu:22.04`; added beyond plain Ubuntu: minimal build toolchain: git, ca-certificates (no tool-specific libraries)

## What this run needed beyond the repository

The result above describes a run configured as follows. Anyone repeating it needs the same things.

- Test data: no sample from the repository was used, so a public reference sample stood in.
- A base environment for the documented installation: STRhub ran the repository's install commands unchanged on Ubuntu 22.04, package lists refreshed, apt answering yes, plus minimal build toolchain (git, ca-certificates; no tool-specific libraries). Base-image and package versions are not frozen by the commands.
- A reference genome (GRCh38 / hg38): the command names one, and STRhub mounted the public copy at /data/ref/hg38.fa.

## Notes from reading the repository

Recorded automatically from the tool's public files when this run was configured. **Not verified by execution**, and not part of the gates above. Useful for what to check by hand.

- Environment: STRhub transcribed the documented installation commands unchanged into its own carrier (Ubuntu 22.04, package lists refreshed, apt answering yes, plus minimal build toolchain (git, ca-certificates; no tool-specific libraries)).
- Input: the README documents BAM (line 69); this plan selects STRhub's illumina-bam-hg38 reference data.
- read_path: run1.bam,run2.bam,run3.bam,run4.bam -> /data/in/input.bam.
- reference_path: genome.fa -> /data/ref/hg38.fa.
- regions_path: str_regions.bed -> /data/in/regions.bed.
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
- Short-read limitations apply (very long STR alleles may not span single short reads)

## Scope (read this)

Assessment of documented execution in the stated environment and output format. Concerns reproducible execution only; no claim of accuracy, casework fitness, or regulatory validation.

This is **not** a claim that the genotypes are correct, nor that the tool is fit for casework or meets any regulatory standard. Concordance against known truth is out of scope.

Verified automatically, in a clean environment, on the tool's public source at the pinned commit. This is a record of what happened, not an endorsement by the tool's author.

