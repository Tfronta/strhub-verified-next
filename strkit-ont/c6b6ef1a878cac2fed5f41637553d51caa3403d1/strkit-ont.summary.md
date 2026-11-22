# STRhub Verified: strkit (strkit-ont)

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

### Planned command

The run step was skipped. This command was not executed by that step.

```
cd '.' && touch /tmp/.strhub_mark && ( strkit call --loci /path/to/catalog --ref /path/to/ref.fa.gz --processes 10 --seed 342 --vcf sample.vcf path/to/sample.bam ); rc=$?; find . -xdev -type f -newer /tmp/.strhub_mark -size +0 ! -path './.git/*' ! -path './proc/*' ! -path './sys/*' ! -path './dev/*' ! -path './data/*' ! -path '*/__pycache__/*' ! -name '*.pyc' ! -name '*.pyo' 2>/dev/null | head -500 | while IFS= read -r f; do mkdir -p "/data/out/$(dirname "$f")" && cp "$f" "/data/out/$f"; done; exit $rc
```

## Run details

- Source: `https://github.com/davidlougheed/strkit` @ `c6b6ef1a878cac2fed5f41637553d51caa3403d1`
- Environment: ubuntu-22.04 (`Dockerfile`)
- Generated: 2026-11-22T19:14:23+00:00
- Upstream: The verified commit is the head of `master`.
- CI run: https://github.com/Tfronta/strhub-verified-next/actions/runs/45059529334

## Verification matrix

| Leg | Available | Result | Errors reported | Dataset |
|---|---|---|---|---|
| External data | N/A | N/A | — | None |
| Tool's own example | N/A | N/A | — | — |

## Evidence

What this run's configuration rests on, each item at the verified commit. Open any of them to check the claim it supports.
- Install method: [`pyproject.toml`](https://github.com/davidlougheed/strkit/blob/c6b6ef1a878cac2fed5f41637553d51caa3403d1/pyproject.toml)
- Fallback environment: [`README.md` line 94](https://github.com/davidlougheed/strkit/blob/c6b6ef1a878cac2fed5f41637553d51caa3403d1/README.md#L94): `docker pull ghcr.io/davidlougheed/strkit:latest`
- Run command: [`docs/caller_usage.md` line 151](https://github.com/davidlougheed/strkit/blob/c6b6ef1a878cac2fed5f41637553d51caa3403d1/docs/caller_usage.md#L151): `strkit call \`
- Example data: [`tests/data/test_loci.bed`](https://github.com/davidlougheed/strkit/blob/c6b6ef1a878cac2fed5f41637553d51caa3403d1/tests/data/test_loci.bed)
- Documented input: [`README.md` line 111](https://github.com/davidlougheed/strkit/blob/c6b6ef1a878cac2fed5f41637553d51caa3403d1/README.md#L111): `/inputs/file.bam \`

## Provenance of this trial (upstream vs. STRhub choices)

### From upstream documentation

- Install (pip): `repo_file:pyproject.toml`
- Command: `docs/caller_usage.md:L151`
- Input format: `bam` (`README.md:L111`)
- Supported platforms: ont (`README.md:L1`), pacbio (`README.md:L5`), illumina (`README.md:L402`)
- Reference assembly: `both` (`README.md:L250`)
- Regions schema: `motif` (`README.md:L179`)

### Selected by STRhub for this trial

- Dataset selected by STRhub: `ont-bam-hg38` — STRhub selected 'ont-bam-hg38' as compatible with upstream input 'bam' and platform 'ont'
- Platform chosen by STRhub: `ont` from documented platforms (ont, pacbio, illumina)

## Notes from reading the repository

Recorded automatically from the tool's public files when this run was configured. **Not verified by execution**, and not part of the gates above. Useful for what to check by hand.

- Environment: no proven installation profile; STRhub did not manufacture installation steps.
- Input: the README documents BAM (line 111); this plan selects STRhub's ont-bam-hg38 reference data. Supported platforms documented: ont, pacbio, illumina; STRhub selected ont for this trial.
- Evaluator limitation: the command reads the reference genome in a form STRhub does not mount (it mounts an uncompressed FASTA with its .fai index).
- Evaluator limitation: a read-file argument is outside the closed input substitution table.
- Run command: the one documented in docs/caller_usage.md (line 151), rewritten to STRhub's mounts; the capture wrapper is planned only if the procedure review passes.

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

