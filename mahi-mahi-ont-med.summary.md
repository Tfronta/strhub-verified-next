# STRhub Verified: mahi-mahi (mahi-mahi-ont-med)

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

### Author-documented warnings and limitations

Quoted from the repository's README at the verified commit. STRhub did not establish any of this by running the tool; it is the author's own note about their own software.

**Warnings and precautions** (README line 815)

> - Use the loci file version that matches the reference genome passed to --ref.
> - Haplotagged input is recommended. If --bypass-haplotag-check is used, close-in-length alleles may be merged and accuracy may be reduced.
> - If using non-standard --loci, check the BED file carefully before use.
> - If a TR region contains sequence that is not actually repetitive, motif decomposition of this unexpected sequence may be effectively nonsensical. The reported length in bases is still meaningful.
> - Previous versions of mahi-mahi have used different parameters, configurations, and filenames. Please refer…

**Known limitations** (README line 827)

> - When the original BAM contains many non-spanning reads, `DP` can be lower than an allele's `AD` or the sum of `AD`. `DP` measures mean alignment depth over the reference repeat interval, whereas `AD` counts reads selected for allele-length estimation, including selected non-spanning reads. This difference does not by itself indicate an invalid call.
> - Expansions supported mainly by non-spanning reads may be underestimated and sized less precisely than fully spanned alleles.
> - Apparent interruptions may be sequencing errors. Visual verification using the read visualisation is recommended.
> …

**Troubleshooting and Support** (README line 891)

> For help, contact Oxford Nanopore Technologies through your usual support channel: Oxford Nanopore customer support.
> - Confirm that the reference genome matches the loci file.
> - Confirm that the BAM or CRAM file is readable and indexed.
> - Confirm that the sample sex argument is correct.
> - Confirm that the input BAM is haplotagged unless --bypass-haplotag-check is intentionally being used.

### Command submitted to runner

The run step reported success. This is the configured command submitted to that step; the step exit status alone does not prove the program started.

```
cd '.' && touch /tmp/.strhub_mark && ( mahi-mahi --bam /data/in/input.bam --ref /data/ref/hg38.fa --loci hg38 --sample SAMPLE --sex XX --out-dir out ); rc=$?; find . -xdev -type f -newer /tmp/.strhub_mark -size +0 ! -path './.git/*' ! -path './proc/*' ! -path './sys/*' ! -path './dev/*' ! -path './data/*' ! -path '*/__pycache__/*' ! -name '*.pyc' ! -name '*.pyo' 2>/dev/null | head -500 | while IFS= read -r f; do mkdir -p "/data/out/$(dirname "$f")" && cp "$f" "/data/out/$f"; done; exit $rc
```
- Log (external): [`mahi-mahi-ont-med.log-external.txt`](mahi-mahi-ont-med.log-external.txt)
- Log (build): [`mahi-mahi-ont-med.log-build.txt`](mahi-mahi-ont-med.log-build.txt)

## Run details

- Source: `https://github.com/nanoporetech/mahi-mahi` @ `861ea09ab44e88424c45b04d8018f3948a8fefbb`
- Environment: ubuntu-22.04 (`Dockerfile`)
- Generated: 2026-11-22T19:14:07+00:00
- Upstream: The verified commit is 2 commit(s) behind `main`. That is context, not a fault: a pinned release is often meant to sit behind, and the attestation describes the commit it names.
- CI run: https://github.com/Tfronta/strhub-verified-next/actions/runs/45059262501

## Output content (plausibility evidence)

- Sequence records: **99** (malformed: 0)
- STR loci detected: **74**
- Total reads across calls: **2533** (deepest single sequence: 52)
- STR loci: ABCD3, AFF2, AFF3, AR, ARX, ATN1, ATXN1, ATXN10, ATXN2, ATXN3, ATXN7, ATXN8OS, BCLAF3, BEAN1, C9orf72, CACNA1A, CBL, CNBP …
- Top markers by read depth: TNRC6A (144), HTT (123), SAMD12 (117), DAB1 (114), RAPGEF2 (114), MARCHF6 (107)

## Verification matrix

| Leg | Available | Result | Errors reported | Dataset |
|---|---|---|---|---|
| External data | yes | PASS | — | 1000 Genomes ONT, hg38 medical STR slice (R10 SUP) |
| Tool's own example | N/A | N/A | — | — |

## Evidence

What this run's configuration rests on, each item at the verified commit. Open any of them to check the claim it supports.
- Install method: [`pyproject.toml`](https://github.com/nanoporetech/mahi-mahi/blob/861ea09ab44e88424c45b04d8018f3948a8fefbb/pyproject.toml)
- Run command: [`README.md` line 230](https://github.com/nanoporetech/mahi-mahi/blob/861ea09ab44e88424c45b04d8018f3948a8fefbb/README.md#L230): `mahi-mahi \`
- Example data: [`src/mahi_mahi/data/str_loci.hg19.bed`](https://github.com/nanoporetech/mahi-mahi/blob/861ea09ab44e88424c45b04d8018f3948a8fefbb/src/mahi_mahi/data/str_loci.hg19.bed)
- Example data: [`src/mahi_mahi/data/str_loci.hg38.bed`](https://github.com/nanoporetech/mahi-mahi/blob/861ea09ab44e88424c45b04d8018f3948a8fefbb/src/mahi_mahi/data/str_loci.hg38.bed)
- Known issue: [`README.md` line 815](https://github.com/nanoporetech/mahi-mahi/blob/861ea09ab44e88424c45b04d8018f3948a8fefbb/README.md#L815): `Warnings and precautions`
- Known issue: [`README.md` line 827](https://github.com/nanoporetech/mahi-mahi/blob/861ea09ab44e88424c45b04d8018f3948a8fefbb/README.md#L827): `Known limitations`
- Known issue: [`README.md` line 891](https://github.com/nanoporetech/mahi-mahi/blob/861ea09ab44e88424c45b04d8018f3948a8fefbb/README.md#L891): `Troubleshooting and Support`
- Documented input: [`README.md` line 55](https://github.com/nanoporetech/mahi-mahi/blob/861ea09ab44e88424c45b04d8018f3948a8fefbb/README.md#L55): `-   Aligned BAM or CRAM input.`

## Provenance of this trial (upstream vs. STRhub choices)

### From upstream documentation

- Install (pip): `README.md:L106-L128`
- Command: `README.md:L230`
- Input format: `bam` (`README.md:L55`)
- Supported platforms: ont (`README.md:L17`)
- Reference assembly: `both` (`README.md:L57`)

### Mechanically derived bindings

- `sample.bam` -> `/data/in/input.bam` (declared dataset mount)
- `reference.fasta` -> `/data/ref/hg38.fa` (registered reference genome mount)

### Selected by STRhub for this trial

- Dataset selected by STRhub: `ont-bam-hg38-med` — STRhub selected 'ont-bam-hg38-med' as compatible with upstream input 'bam' and platform 'ont'; shipped catalog 'src/mahi_mahi/data/str_loci.hg38.bed' overlaps 49 medical panel loci and 0 forensic loci
- Platform used: `ont` (single documented platform)
- Base environment supplied by STRhub: `ubuntu:22.04`; added beyond plain Ubuntu: minimal build toolchain: python3, python3-venv, python3-pip, python-is-python3, ca-certificates (no tool-specific libraries)

## What this run needed beyond the repository

The result above describes a run configured as follows. Anyone repeating it needs the same things.

- Test data: no sample from the repository was used, so a public reference sample stood in.
- A base environment for the documented installation: STRhub ran the repository's install commands unchanged on Ubuntu 22.04, package lists refreshed, apt answering yes, plus minimal build toolchain (python3, python3-venv, python3-pip, python-is-python3, ca-certificates; no tool-specific libraries). Base-image and package versions are not frozen by the commands.
- A reference genome (GRCh38 / hg38): the command names one, and STRhub mounted the public copy at /data/ref/hg38.fa.

## Notes from reading the repository

Recorded automatically from the tool's public files when this run was configured. **Not verified by execution**, and not part of the gates above. Useful for what to check by hand.

- Environment: STRhub transcribed the documented installation commands unchanged into its own carrier (Ubuntu 22.04, package lists refreshed, apt answering yes, plus minimal build toolchain (python3, python3-venv, python3-pip, python-is-python3, ca-certificates; no tool-specific libraries)).
- Input: the README documents BAM (line 55); this plan selects STRhub's ont-bam-hg38-med reference data.
- Panel: the shipped loci catalog (src/mahi_mahi/data/str_loci.hg38.bed) overlaps 49 loci in STRhub's medical STR slice and 0 in the forensic slice; this plan selects STRhub's ont-bam-hg38-med reference data.
- read_path: sample.bam -> /data/in/input.bam.
- reference_path: reference.fasta -> /data/ref/hg38.fa.
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
- Long-read sequencing characteristics apply (basecalling accuracy, homopolymers, unphased reads, or extreme repeat expansions can affect allele resolution)

## Scope (read this)

Assessment of documented execution in the stated environment and output format. Concerns reproducible execution only; no claim of accuracy, casework fitness, or regulatory validation.

This is **not** a claim that the genotypes are correct, nor that the tool is fit for casework or meets any regulatory standard. Concordance against known truth is out of scope.

Verified automatically, in a clean environment, on the tool's public source at the pinned commit. This is a record of what happened, not an endorsement by the tool's author.

