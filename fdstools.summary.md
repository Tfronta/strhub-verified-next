# STRhub Verified: FDSTools (fdstools)

**Could not be determined.**

## As it is in the repository

**Step 1, the documented run: As documented, a third party cannot tell how to run it.** No repository document shows an installation this profile can transcribe literally; no missing step, dependency or choice was supplied by STRhub. Nothing was executed. That does not mean the tool does not work: what the guide asks for is missing from the README at this commit. Add it and try the link again on the new commit.

Missing from the commit, by the blocks docs/GUIA-PASO-1.md asks for:

- Installation, copyable

**Verdict: Could not be determined.** No repository document shows an installation this profile can transcribe literally; no missing step, dependency or choice was supplied by STRhub.

What stopped it, and what its owner can be asked:

- No repository document shows an installation this profile can transcribe literally; no missing step, dependency or choice was supplied by STRhub.
  - The tool's owner: open an issue, "Write the installation as commands that can be copied and run".
- No command line invoking the tool was found in the README.
  - The tool's owner: open an issue, "Document the command that runs the tool".

What the README does not say:

- No command line invoking the tool was found in the README's code blocks.
- The README does not describe the output file or its format.

Reached **Available**: the pinned public source exists.

### Gates

| Gate | Status | Meaning |
|---|---|---|
| Available | PASS | the pinned public source exists |
| Installs | — | the environment builds from source |
| Runs | — | it executes end-to-end without crashing |
| Runs + Expected IO | — | it produces a non-empty file in the declared format |
| Runs + Plausible output | — | its output looks like plausible genotype-bearing data (declared columns, DNA sequences, integer read counts, and enough recognisable forensic loci) |

### Planned command

The run step was skipped. This command was not executed by that step.

```
true  # no command found in the README; nothing to run
```

## Run details

- Source: `https://github.com/Jerrythafast/FDSTools` @ `5cad6d057fd2f16bd77f9aa2420e920ccfcc7aa6`
- Environment: ubuntu-22.04 (`Dockerfile`)
- Generated: 2026-11-22T19:13:51+00:00
- Upstream: The verified commit is the head of `main`.
- CI run: https://github.com/Tfronta/strhub-verified-next/actions/runs/45059487320

## Verification matrix

| Leg | Available | Result | Errors reported | Dataset |
|---|---|---|---|---|
| External data | N/A | N/A | — | None |
| Tool's own example | N/A | N/A | — | — |

## Evidence

What this run's configuration rests on, each item at the verified commit. Open any of them to check the claim it supports.
- Install method: [`pyproject.toml`](https://github.com/Jerrythafast/FDSTools/blob/5cad6d057fd2f16bd77f9aa2420e920ccfcc7aa6/pyproject.toml)
- Example data: [`tests/data/demultiplex/advanced2a/E0150_S2_R1_001.fastq.gz`](https://github.com/Jerrythafast/FDSTools/blob/5cad6d057fd2f16bd77f9aa2420e920ccfcc7aa6/tests/data/demultiplex/advanced2a/E0150_S2_R1_001.fastq.gz)
- Example data: [`tests/data/demultiplex/advanced2a/E0150_S2_R2_001.fastq.gz`](https://github.com/Jerrythafast/FDSTools/blob/5cad6d057fd2f16bd77f9aa2420e920ccfcc7aa6/tests/data/demultiplex/advanced2a/E0150_S2_R2_001.fastq.gz)
- Example data: [`tests/data/demultiplex/default/E0049_S1_R1_001.fastq.gz`](https://github.com/Jerrythafast/FDSTools/blob/5cad6d057fd2f16bd77f9aa2420e920ccfcc7aa6/tests/data/demultiplex/default/E0049_S1_R1_001.fastq.gz)
- Example data: [`tests/data/demultiplex/default/E0049_S1_R2_001.fastq.gz`](https://github.com/Jerrythafast/FDSTools/blob/5cad6d057fd2f16bd77f9aa2420e920ccfcc7aa6/tests/data/demultiplex/default/E0049_S1_R2_001.fastq.gz)
- Example data: [`tests/data/demultiplex/default/E0150_S2_R1_001.fastq.gz`](https://github.com/Jerrythafast/FDSTools/blob/5cad6d057fd2f16bd77f9aa2420e920ccfcc7aa6/tests/data/demultiplex/default/E0150_S2_R1_001.fastq.gz)

## Provenance of this trial (upstream vs. STRhub choices)

### From upstream documentation

- Install (pip): `repo_file:pyproject.toml`
- Input format: `fastq` (not explicitly stated)
- Supported platforms: illumina (`README.md:L115`)
- Reference assembly: `hg38` (`README.md:L69`)

### Selected by STRhub for this trial

- Dataset selected by STRhub: `illumina-str-fastq` — STRhub selected 'illumina-str-fastq' as compatible with upstream input 'fastq' and platform 'illumina'

## Notes from reading the repository

Recorded automatically from the tool's public files when this run was configured. **Not verified by execution**, and not part of the gates above. Useful for what to check by hand.

- Environment: no proven installation profile; STRhub did not manufacture installation steps.
- Input: no sentence in the README says what the tool takes; illumina-str-fastq is only a guess from mentions; it is not authorization to execute.

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

