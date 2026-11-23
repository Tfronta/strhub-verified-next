# STRhub Verified: STRspy (strspy-ont)

**Could not be determined.**

## As it is in the repository

**Step 1, the documented run: As documented, a third party cannot tell how to run it.** An installation step is outside this profile (README.md, line 61: `wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh`); STRhub does not interpret, complete or skip it. Nothing was executed. That does not mean the tool does not work: what the guide asks for is missing from the README at this commit. Add it and try the link again on the new commit.

Missing from the commit, by the blocks docs/GUIA-PASO-1.md asks for:

- Installation, copyable

**Verdict: Could not be determined.** An installation step is outside this profile (README.md, line 61: `wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh`); STRhub does not interpret, complete or skip it.

What stopped it, and what its owner can be asked:

- An installation step is outside this profile (README.md, line 61: `wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh`); STRhub does not interpret, complete or skip it.
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

### Author-documented warnings and limitations

Quoted from the repository's README at the verified commit. STRhub did not establish any of this by running the tool; it is the author's own note about their own software.

**Known bug** (README line 291)

> When using the wrapper ('STRspy_run_v1.0.sh'), One might run into an issue. The parallel version of **STRspy_Parallel_v2.0_Args.sh** is unable to properly connect with "gnu parallel" and exits the workflow without mapping or further analysis steps of the pipeline. Solution to this, the user can choose the Normal version to avoid any crash.
> ***Tip: Its good practice to use pre-aligned bams for quicker outcomes.***

### Planned command

The run step was skipped. This command was not executed by that step.

```
cd '.' && touch /tmp/.strhub_mark && ( bash ./STRspy_run_v2.0_Args.sh config/InputConfig.txt config/ToolsConfig.txt ); rc=$?; find . -xdev -type f -newer /tmp/.strhub_mark -size +0 ! -path './.git/*' ! -path './proc/*' ! -path './sys/*' ! -path './dev/*' ! -path './data/*' ! -path '*/__pycache__/*' ! -name '*.pyc' ! -name '*.pyo' 2>/dev/null | head -500 | while IFS= read -r f; do mkdir -p "/data/out/$(dirname "$f")" && cp "$f" "/data/out/$f"; done; exit $rc
```

## Run details

- Source: `https://github.com/unique379r/strspy` @ `dafdee7e7e5672c8dc732e8577dbe153f53a12f5`
- Environment: ubuntu-22.04 (`Dockerfile`)
- Generated: 2026-11-23T14:07:58+00:00
- Upstream: The verified commit is 14 commit(s) behind `main`. That is context, not a fault: a pinned release is often meant to sit behind, and the attestation describes the commit it names.
- CI run: https://github.com/Tfronta/strhub-verified-next/actions/runs/45190720306

## Verification matrix

| Leg | Available | Result | Errors reported | Dataset |
|---|---|---|---|---|
| External data | N/A | N/A | — | None |
| Tool's own example | N/A | N/A | — | — |

## Evidence

What this run's configuration rests on, each item at the verified commit. Open any of them to check the claim it supports.
- Install method: [`setup/STRspy_2.0_env.yml`](https://github.com/unique379r/strspy/blob/dafdee7e7e5672c8dc732e8577dbe153f53a12f5/setup/STRspy_2.0_env.yml)
- Run command: [`README.md` line 120](https://github.com/unique379r/strspy/blob/dafdee7e7e5672c8dc732e8577dbe153f53a12f5/README.md#L120): `USAGE: bash ./STRspy_run_v2.0_Args.sh config/InputConfig.txt config/ToolsConfig.txt`
- Example data: [`db-v2/STRspy_v2.DB.sort.bed`](https://github.com/unique379r/strspy/blob/dafdee7e7e5672c8dc732e8577dbe153f53a12f5/db-v2/STRspy_v2.DB.sort.bed)
- Example data: [`db-v2/optional-create-custom-db/testTwofa/TPOX.fa`](https://github.com/unique379r/strspy/blob/dafdee7e7e5672c8dc732e8577dbe153f53a12f5/db-v2/optional-create-custom-db/testTwofa/TPOX.fa)
- Example data: [`db-v2/optional-create-custom-db/testTwofa/vWA.fa`](https://github.com/unique379r/strspy/blob/dafdee7e7e5672c8dc732e8577dbe153f53a12f5/db-v2/optional-create-custom-db/testTwofa/vWA.fa)
- Known issue: [`README.md` line 291](https://github.com/unique379r/strspy/blob/dafdee7e7e5672c8dc732e8577dbe153f53a12f5/README.md#L291): `Known bug`
- Documented input: [`README.md` line 44](https://github.com/unique379r/strspy/blob/dafdee7e7e5672c8dc732e8577dbe153f53a12f5/README.md#L44): `Input either fastq (raw reads usually from ONT) or bam (pre-aligned reads by user)`
- Author's recommendation: [`README.md` line 295](https://github.com/unique379r/strspy/blob/dafdee7e7e5672c8dc732e8577dbe153f53a12f5/README.md#L295): `***Tip: Its good practice to use pre-aligned bams for quicker outcomes.***`

## Provenance of this trial (upstream vs. STRhub choices)

### From upstream documentation

- Install (conda): `repo_file:setup/STRspy_2.0_env.yml`
- Command: `README.md:L120`
- Input format: `bam` (`README.md:L44`)
- Supported platforms: ont (`README.md:L44`)
- Reference assembly: `both` (`README.md:L33`)

### Selected by STRhub for this trial

- Dataset selected by STRhub: `ont-bam-hg38` — STRhub selected 'ont-bam-hg38' as compatible with upstream input 'bam' and platform 'ont'
- Platform used: `ont` (single documented platform)

## Notes from reading the repository

Recorded automatically from the tool's public files when this run was configured. **Not verified by execution**, and not part of the gates above. Useful for what to check by hand.

- Environment: no proven installation profile; STRhub did not manufacture installation steps.
- Input: the README documents BAM and FASTQ (line 44); this plan selects STRhub's ont-bam-hg38 reference data. The author recommends BAM (line 295: "Tip: Its good practice to use pre-aligned bams for quicker outcomes.").
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

