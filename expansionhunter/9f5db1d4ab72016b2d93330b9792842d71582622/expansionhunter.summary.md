# STRhub Verified: ExpansionHunter (expansionhunter)

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
| CMake could not find a required system library: ZLIB | 2 | Observed: CMake reported missing 'ZLIB' development components (ZLIB_LIBRARY ZLIB_INCLUDE_DIR) after running the executed installation steps. Inferred: installing the corresponding system '-dev' package (such as zlib1g-dev, libbz2-dev, or liblzma-dev, rather than only a runtime package like zlib1g) may resolve this build stop. Not determined automatically: whether the omission sits in the upstream documentation, an implicit system prerequisite, or the base environment. |

Full build output: [`expansionhunter.log-build.txt`](expansionhunter.log-build.txt)

### Planned command

The run step was skipped. This command was not executed by that step.

```
cd '.' && touch /tmp/.strhub_mark && ( ExpansionHunter --reads /data/in/input.bam --reference /data/ref/hg38.fa --variant-catalog /data/in/regions.json --output-prefix sample ); rc=$?; find . -xdev -type f -newer /tmp/.strhub_mark -size +0 ! -path './.git/*' ! -path './proc/*' ! -path './sys/*' ! -path './dev/*' ! -path './data/*' ! -path '*/__pycache__/*' ! -name '*.pyc' ! -name '*.pyo' 2>/dev/null | head -500 | while IFS= read -r f; do mkdir -p "/data/out/$(dirname "$f")" && cp "$f" "/data/out/$f"; done; exit $rc
```
- Log (build): [`expansionhunter.log-build.txt`](expansionhunter.log-build.txt)

## Run details

- Source: `https://github.com/Illumina/ExpansionHunter` @ `9f5db1d4ab72016b2d93330b9792842d71582622`
- Environment: ubuntu-22.04 (`Dockerfile`)
- Generated: 2026-11-22T19:12:10+00:00
- Upstream: The verified commit is 8 commit(s) behind `master`. That is context, not a fault: a pinned release is often meant to sit behind, and the attestation describes the commit it names.
- CI run: https://github.com/Tfronta/strhub-verified-next/actions/runs/45059275700

## Verification matrix

| Leg | Available | Result | Errors reported | Dataset |
|---|---|---|---|---|
| External data | yes | — | — | Illumina BAM (hg38), NA12878 (autosomal, female) |
| Tool's own example | N/A | N/A | — | — |

## Evidence

What this run's configuration rests on, each item at the verified commit. Open any of them to check the claim it supports.
- Run command: [`docs/03_Usage.md` line 15](https://github.com/Illumina/ExpansionHunter/blob/9f5db1d4ab72016b2d93330b9792842d71582622/docs/03_Usage.md#L15): `ExpansionHunter --reads <BAM/CRAM file with aligned reads> \`
- Example data: [`example/input/reference.fa`](https://github.com/Illumina/ExpansionHunter/blob/9f5db1d4ab72016b2d93330b9792842d71582622/example/input/reference.fa)
- Example data: [`example/input/variants.bam`](https://github.com/Illumina/ExpansionHunter/blob/9f5db1d4ab72016b2d93330b9792842d71582622/example/input/variants.bam)
- Example data: [`example/output/repeats.vcf`](https://github.com/Illumina/ExpansionHunter/blob/9f5db1d4ab72016b2d93330b9792842d71582622/example/output/repeats.vcf)
- Example data: [`example/output/repeats_realigned.bam`](https://github.com/Illumina/ExpansionHunter/blob/9f5db1d4ab72016b2d93330b9792842d71582622/example/output/repeats_realigned.bam)
- Documented input: [`README.md` line 15](https://github.com/Illumina/ExpansionHunter/blob/9f5db1d4ab72016b2d93330b9792842d71582622/README.md#L15): `ExpansionHunter --reads <BAM/CRAM file with aligned reads> \`

## Provenance of this trial (upstream vs. STRhub choices)

### From upstream documentation

- Install (release_binary): `docs/02_Installation.md:L19-L35`
- Command: `docs/03_Usage.md:L15`
- Input format: `bam` (`docs/03_Usage.md:L15`)
- Supported platforms: illumina (`README.md:L37`)
- Reference assembly: not specified in repository documentation
- Regions schema: `eh_catalog` (`docs/04_VariantCatalogFiles.md:L17-L27`)

### Mechanically derived bindings

- `<BAM/CRAM file with aligned reads>` -> `/data/in/input.bam` (declared dataset mount)
- `<FASTA file with reference genome>` -> `/data/ref/hg38.fa` (registered reference genome mount)
- `<JSON file specifying variants to genotype>` -> `/data/in/regions.json` (registered regions file (eh_catalog))
- `<Prefix for the output files>` -> `sample` (explicit output-path placeholder)
- Regions layout `eh_catalog` matched `eh_catalog` (`docs/04_VariantCatalogFiles.md:L17-L27`)

### Selected by STRhub for this trial

- Dataset selected by STRhub: `illumina-bam-hg38` — STRhub selected 'illumina-bam-hg38' as compatible with upstream input 'bam' and platform 'illumina'
- Platform used: `illumina` (single documented platform)
- Assembly chosen by STRhub: `hg38` (upstream unspecified; STRhub staged coherent BAM, FASTA and regions on hg38)
- Regions file mounted: `eh_catalog`
- Base environment supplied by STRhub: `ubuntu:22.04`; added beyond plain Ubuntu: minimal build toolchain: build-essential, cmake, git, ca-certificates (no tool-specific libraries)

## What this run needed beyond the repository

The result above describes a run configured as follows. Anyone repeating it needs the same things.

- Test data: a public reference sample was selected, but was not executed because installation did not complete.
- A base environment for the documented installation: STRhub ran the repository's install commands unchanged on Ubuntu 22.04, package lists refreshed, apt answering yes, plus minimal build toolchain (build-essential, cmake, git, ca-certificates; no tool-specific libraries). Base-image and package versions are not frozen by the commands.

## Notes from reading the repository

Recorded automatically from the tool's public files when this run was configured. **Not verified by execution**, and not part of the gates above. Useful for what to check by hand.

- Environment: STRhub transcribed the documented installation commands unchanged into its own carrier (Ubuntu 22.04, package lists refreshed, apt answering yes, plus minimal build toolchain (build-essential, cmake, git, ca-certificates; no tool-specific libraries)).
- Input: the README documents BAM (line 15); this plan selects STRhub's illumina-bam-hg38 reference data.
- read_path: <BAM/CRAM file with aligned reads> -> /data/in/input.bam.
- reference_path: <FASTA file with reference genome> -> /data/ref/hg38.fa.
- regions_path: <JSON file specifying variants to genotype> -> /data/in/regions.json.
- output_placeholder: <Prefix for the output files> -> sample.
- Run command: the one documented in docs/03_Usage.md (line 15), rewritten to STRhub's mounts; the capture wrapper is planned only if the procedure review passes.

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

