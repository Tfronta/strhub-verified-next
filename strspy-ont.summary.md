# STRhub Verified: STRspy (strspy-ont)

**Could not be determined.**

## As it is in the repository

**Step 1, the documented run: As documented, a third party cannot tell how to run it.** An installation step is outside this profile (README.md, line 27: `wget https://repo.anaconda.com/miniconda/Miniconda3-py39_4.9.2-Linux-x86_64.sh`); STRhub does not interpret, complete or skip it. Nothing was executed. That does not mean the tool does not work: what the guide asks for is missing from the README at this commit. Add it and try the link again on the new commit.

Missing from the commit, by the blocks docs/GUIA-PASO-1.md asks for:

- Installation, copyable

**Verdict: Could not be determined.** An installation step is outside this profile (README.md, line 27: `wget https://repo.anaconda.com/miniconda/Miniconda3-py39_4.9.2-Linux-x86_64.sh`); STRhub does not interpret, complete or skip it.

What stopped it, and what its owner can be asked:

- An installation step is outside this profile (README.md, line 27: `wget https://repo.anaconda.com/miniconda/Miniconda3-py39_4.9.2-Linux-x86_64.sh`); STRhub does not interpret, complete or skip it.
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
cd '.' && touch /tmp/.strhub_mark && ( bash ./STRspy_run_v1.0.sh config/InputConfig.txt config/ToolsConfig.txt ); rc=$?; find . -xdev -type f -newer /tmp/.strhub_mark -size +0 ! -path './.git/*' ! -path './proc/*' ! -path './sys/*' ! -path './dev/*' ! -path './data/*' ! -path '*/__pycache__/*' ! -name '*.pyc' ! -name '*.pyo' 2>/dev/null | head -500 | while IFS= read -r f; do mkdir -p "/data/out/$(dirname "$f")" && cp "$f" "/data/out/$f"; done; exit $rc
```

## Run details

- Source: `https://github.com/unique379r/strspy` @ `cbf650081e92f5d36eb7409d7208dbde425fdf95`
- Environment: ubuntu-22.04 (`Dockerfile`)
- Generated: 2026-11-22T19:11:43+00:00
- Upstream: The verified commit is 58 commit(s) behind `main`. That is context, not a fault: a pinned release is often meant to sit behind, and the attestation describes the commit it names.
- CI run: https://github.com/Tfronta/strhub-verified-next/actions/runs/45059310337

## Verification matrix

| Leg | Available | Result | Errors reported | Dataset |
|---|---|---|---|---|
| External data | N/A | N/A | — | None |
| Tool's own example | N/A | N/A | — | — |

## Evidence

What this run's configuration rests on, each item at the verified commit. Open any of them to check the claim it supports.
- Install method: [`setup/environment.yml`](https://github.com/unique379r/strspy/blob/cbf650081e92f5d36eb7409d7208dbde425fdf95/setup/environment.yml)
- Run command: [`README.md` line 81](https://github.com/unique379r/strspy/blob/cbf650081e92f5d36eb7409d7208dbde425fdf95/README.md#L81): ``USAGE: bash ./STRspy_run_v1.0.sh config/InputConfig.txt config/ToolsConfig.txt``
- Example data: [`customDB/regions.sort.named.bed`](https://github.com/unique379r/strspy/blob/cbf650081e92f5d36eb7409d7208dbde425fdf95/customDB/regions.sort.named.bed)
- Documented input: [`README.md` line 12](https://github.com/unique379r/strspy/blob/cbf650081e92f5d36eb7409d7208dbde425fdf95/README.md#L12): `Input either fastq (raw reads usually from ONT) or bam (pre-aligned reads usually froom PacBio)`

## Provenance of this trial (upstream vs. STRhub choices)

### From upstream documentation

- Install (conda): `repo_file:setup/environment.yml`
- Command: `README.md:L81`
- Input format: `bam` (`README.md:L12`)
- Supported platforms: ont (`README.md:L4`), pacbio (`README.md:L4`)
- Reference assembly: `both` (`README.md:L109`)

### Selected by STRhub for this trial

- Dataset selected by STRhub: `ont-bam-hg38` — STRhub selected 'ont-bam-hg38' as compatible with upstream input 'bam' and platform 'ont'
- Platform chosen by STRhub: `ont` from documented platforms (ont, pacbio)

## Notes from reading the repository

Recorded automatically from the tool's public files when this run was configured. **Not verified by execution**, and not part of the gates above. Useful for what to check by hand.

- Environment: no proven installation profile; STRhub did not manufacture installation steps.
- Input: the README documents BAM and FASTQ (line 12); this plan selects STRhub's ont-bam-hg38 reference data. Supported platforms documented: ont, pacbio; STRhub selected ont for this trial.
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

