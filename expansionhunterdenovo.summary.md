# STRhub Verified: ExpansionHunterDenovo (expansionhunterdenovo)

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
- **If you maintain it:** The cause could not be classified automatically. The full build output is linked below.

What failed:

| What happened | Times | What the log establishes |
|---|---|---|
| A download in the build failed: https://dl.bintray.com/boostorg/release/1.67.0/source/boost_1_67_0.tar.bz2 | 3 | Observed: during compilation, CMake attempted to fetch an external dependency from 'https://dl.bintray.com/boostorg/release/1.67.0/source/boost_1_67_0.tar.bz2' and received an HTTP or hash-mismatch error. Inferred: the remote URL may be unavailable or hosted on a retired service (such as dl.bintray.com, which shut down in May 2021). Not determined automatically: whether the outage is transient or permanent. |

Full build output: [`expansionhunterdenovo.log-build.txt`](expansionhunterdenovo.log-build.txt)

### Author-documented warnings and limitations

Quoted from the repository's README at the verified commit. STRhub did not establish any of this by running the tool; it is the author's own note about their own software.

**Limitations** (README line 36)

> - STRs shorter than the read length are ignored; the program is appropriate
> only for detecting expansions that exceed the read length.
> - The location of each reported STR is approximate (up to about 500bp-1Kbp)
> - STRs are not genotyped; the program reports a depth-normalized count of reads
> originating inside each STR; this count can be used as a very approximate
> measure of the repeat length
> - To achieve best results all samples must be sequenced on the same instrument
> to similar coverage, have the same read and fragment lengths, and be subjected
> to the same computational pre-processing (e.g.…

### Planned command

The run step was skipped. This command was not executed by that step.

```
cd '.' && touch /tmp/.strhub_mark && ( ExpansionHunterDenovo profile --reads input.bam --reference reference.fasta --output-prefix output --min-anchor-mapq 50 --max-irr-mapq 40 ); rc=$?; find . -xdev -type f -newer /tmp/.strhub_mark -size +0 ! -path './.git/*' ! -path './proc/*' ! -path './sys/*' ! -path './dev/*' ! -path './data/*' ! -path '*/__pycache__/*' ! -name '*.pyc' ! -name '*.pyo' 2>/dev/null | head -500 | while IFS= read -r f; do mkdir -p "/data/out/$(dirname "$f")" && cp "$f" "/data/out/$f"; done; exit $rc
```
- Log (build): [`expansionhunterdenovo.log-build.txt`](expansionhunterdenovo.log-build.txt)

## Run details

- Source: `https://github.com/Illumina/ExpansionHunterDenovo` @ `5a48ed8b6dceb8d772f702e239c5afede9d5108c`
- Environment: ubuntu-22.04 (`Dockerfile`)
- Generated: 2026-11-22T19:12:00+00:00
- Upstream: The verified commit is 7 commit(s) behind `master`. That is context, not a fault: a pinned release is often meant to sit behind, and the attestation describes the commit it names.
- CI run: https://github.com/Tfronta/strhub-verified-next/actions/runs/45059287281

## Verification matrix

| Leg | Available | Result | Errors reported | Dataset |
|---|---|---|---|---|
| External data | N/A | N/A | — | None |
| Tool's own example | N/A | N/A | — | — |

## Evidence

What this run's configuration rests on, each item at the verified commit. Open any of them to check the claim it supports.
- Run command: [`documentation/05_Computing_profiles.md` line 35](https://github.com/Illumina/ExpansionHunterDenovo/blob/5a48ed8b6dceb8d772f702e239c5afede9d5108c/documentation/05_Computing_profiles.md#L35): `ExpansionHunterDenovo profile \`
- Example data: [`examples/outlier/reference.fasta`](https://github.com/Illumina/ExpansionHunterDenovo/blob/5a48ed8b6dceb8d772f702e239c5afede9d5108c/examples/outlier/reference.fasta)
- Example data: [`examples/case-control/reference.fasta`](https://github.com/Illumina/ExpansionHunterDenovo/blob/5a48ed8b6dceb8d772f702e239c5afede9d5108c/examples/case-control/reference.fasta)
- Example data: [`examples/outlier/bamlets/sample10.bam`](https://github.com/Illumina/ExpansionHunterDenovo/blob/5a48ed8b6dceb8d772f702e239c5afede9d5108c/examples/outlier/bamlets/sample10.bam)
- Example data: [`examples/outlier/bamlets/sample12.bam`](https://github.com/Illumina/ExpansionHunterDenovo/blob/5a48ed8b6dceb8d772f702e239c5afede9d5108c/examples/outlier/bamlets/sample12.bam)
- Example data: [`examples/outlier/bamlets/sample14.bam`](https://github.com/Illumina/ExpansionHunterDenovo/blob/5a48ed8b6dceb8d772f702e239c5afede9d5108c/examples/outlier/bamlets/sample14.bam)
- Known issue: [`README.md` line 36](https://github.com/Illumina/ExpansionHunterDenovo/blob/5a48ed8b6dceb8d772f702e239c5afede9d5108c/README.md#L36): `Limitations`
- Documented input: [`README.md` line 10](https://github.com/Illumina/ExpansionHunterDenovo/blob/5a48ed8b6dceb8d772f702e239c5afede9d5108c/README.md#L10): `During the first step, genome-wide STR profiles are extracted from the input BAM`

## Provenance of this trial (upstream vs. STRhub choices)

### From upstream documentation

- Install (release_binary): `documentation/02_Installation.md:L19-L30`
- Command: `documentation/05_Computing_profiles.md:L35`
- Input format: `bam` (not explicitly stated)
- Reference assembly: `both` (`documentation/08_Annotation.md:L41`)

### Selected by STRhub for this trial

- Base environment supplied by STRhub: `ubuntu:22.04`; added beyond plain Ubuntu: minimal build toolchain: build-essential, cmake, git, ca-certificates (no tool-specific libraries)

## What this run needed beyond the repository

The result above describes a run configured as follows. Anyone repeating it needs the same things.

- A base environment for the documented installation: STRhub ran the repository's install commands unchanged on Ubuntu 22.04, package lists refreshed, apt answering yes, plus minimal build toolchain (build-essential, cmake, git, ca-certificates; no tool-specific libraries). Base-image and package versions are not frozen by the commands.

## Notes from reading the repository

Recorded automatically from the tool's public files when this run was configured. **Not verified by execution**, and not part of the gates above. Useful for what to check by hand.

- Environment: STRhub transcribed the documented installation commands unchanged into its own carrier (Ubuntu 22.04, package lists refreshed, apt answering yes, plus minimal build toolchain (build-essential, cmake, git, ca-certificates; no tool-specific libraries)).
- Run command: the one documented in documentation/05_Computing_profiles.md (line 35), rewritten to STRhub's mounts; the capture wrapper is planned only if the procedure review passes.

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

