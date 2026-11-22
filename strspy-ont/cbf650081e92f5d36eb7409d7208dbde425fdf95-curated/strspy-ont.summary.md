# STRhub Verified: STRspy (strspy-ont)

**Runs as documented.**

## As it is in the repository

**Step 1, the documented run: As documented, it runs.** A third party installed the tool with the steps this commit states and ran the command it writes, and the output file that command names appeared. This says nothing about genotypes or about the forensic panel.

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

### What the author documents as a known issue

Quoted from the repository's README at the verified commit. STRhub did not establish any of this by running the tool; it is the author's own note about their own software.

**Known bug** (README line 294)

> When using the wrapper ('STRspy_run_v1.0.sh'), One might run into an issue. The parallel version of **STRspy_Parallel_v2.0_Args.sh** is unable to properly connect with "gnu parallel" and exits the workflow without mapping or further analysis steps of the pipeline. Solution to this, the user can choose the Normal version to avoid any crash. ***Tip: Its good practice to use pre-aligned bams for quicker outcomes.***

### Command submitted to runner

The run step reported success. This is the configured command submitted to that step; a failed step alone does not prove the program started.

```
cd '.' && touch /tmp/.strhub_mark && ( bash src/STRspy_Normal_v2.0_Args.sh -i /data/in/input.bam -r yes -t ont -f db-v2/STRspy2.0-DB-fixed -b db-v2/STRspy2.0-DB-fixed -l db-v2/STRspy_v2.DB.sort.bed -k 0.4 -o Results -c config/UserToolsConfig.txt -d 4 ); rc=$?; find . -xdev -type f -newer /tmp/.strhub_mark -size +0 ! -path './.git/*' ! -path './proc/*' ! -path './sys/*' ! -path './dev/*' ! -path './data/*' ! -path '*/__pycache__/*' ! -name '*.pyc' ! -name '*.pyo' 2>/dev/null | head -500 | while IFS= read -r f; do mkdir -p "/data/out/$(dirname "$f")" && cp "$f" "/data/out/$f"; done; exit $rc
```
- Log (external): [`strspy-ont.log-external.txt`](strspy-ont.log-external.txt)
- Log (build): [`strspy-ont.log-build.txt`](strspy-ont.log-build.txt)

## Run details

- Source: `https://github.com/Tfronta/strspy` @ `b4c3cc6ab3c866788ec456c22597a112d5237def`
- Environment: ubuntu-22.04 (`Dockerfile`)
- Generated: 2026-11-21T18:21:34+00:00
- Upstream: The verified commit is the head of `main`.
- Fork: This repository is a fork of unique379r/strspy (compared with its branch STRspy2.0): 167 file(s) differ, 1 documentation, 157 data, 9 code. It changes code, so this result is about the fork and not about the original.
- CI run: https://github.com/Tfronta/strhub-verified-next/actions/runs/44934862541

## Output content (plausibility evidence)

- Sequence records: **40** (malformed: 0)
- STR loci detected: **22**
- Total reads across calls: **0** (deepest single sequence: 0)
- STR loci: CSF1PO, D10S1248, D12S391, D13S317, D16S539, D18S51, D19S433, D1S1656, D21S11, D22S1045, D2S1338, D2S441, D3S1358, D5S818, D7S820, D8S1179, DYS391, DYS393 …
- Top markers by read depth: CSF1PO (0), D10S1248 (0), D12S391 (0), D13S317 (0), D16S539 (0), D18S51 (0)

## Verification matrix

| Leg | Available | Result | Errors reported | Dataset |
|---|---|---|---|---|
| External data | yes | PASS | — | 1000 Genomes ONT, hg38 CODIS slice (R10 SUP) |
| Tool's own example | N/A | N/A | — | — |

## Evidence

What this run's configuration rests on, each item at the verified commit. Open any of them to check the claim it supports.
- Install method: [`setup/STRspy_2.0_env.yml`](https://github.com/Tfronta/strspy/blob/b4c3cc6ab3c866788ec456c22597a112d5237def/setup/STRspy_2.0_env.yml)
- Run command: [`README.md` line 120](https://github.com/Tfronta/strspy/blob/b4c3cc6ab3c866788ec456c22597a112d5237def/README.md#L120): `bash src/STRspy_Normal_v2.0_Args.sh -i sample.bam -r yes -t ont -f db-v2/STRspy2.0-DB-fixed -b db-v2/STRspy2.0-DB-fixed -l db-v2/STRspy_v2.DB.sort.bed -k 0.4 -o Results -c config/UserToolsConfig.txt -d 4`
- Example data: [`db-v2/STRspy2.0-DB-fixed/TPOX.bed`](https://github.com/Tfronta/strspy/blob/b4c3cc6ab3c866788ec456c22597a112d5237def/db-v2/STRspy2.0-DB-fixed/TPOX.bed)
- Example data: [`db-v2/STRspy2.0-DB-fixed/vWA.bed`](https://github.com/Tfronta/strspy/blob/b4c3cc6ab3c866788ec456c22597a112d5237def/db-v2/STRspy2.0-DB-fixed/vWA.bed)
- Example data: [`db-v2/STRspy2.0-DB-fixed/DYS19.bed`](https://github.com/Tfronta/strspy/blob/b4c3cc6ab3c866788ec456c22597a112d5237def/db-v2/STRspy2.0-DB-fixed/DYS19.bed)
- Example data: [`db-v2/STRspy2.0-DB-fixed/TH01.bed`](https://github.com/Tfronta/strspy/blob/b4c3cc6ab3c866788ec456c22597a112d5237def/db-v2/STRspy2.0-DB-fixed/TH01.bed)
- Example data: [`db-v2/STRspy2.0-DB-fixed/DYS393.bed`](https://github.com/Tfronta/strspy/blob/b4c3cc6ab3c866788ec456c22597a112d5237def/db-v2/STRspy2.0-DB-fixed/DYS393.bed)
- Known issue: [`README.md` line 294](https://github.com/Tfronta/strspy/blob/b4c3cc6ab3c866788ec456c22597a112d5237def/README.md#L294): `Known bug`
- Documented input: [`README.md` line 44](https://github.com/Tfronta/strspy/blob/b4c3cc6ab3c866788ec456c22597a112d5237def/README.md#L44): `Input either fastq (raw reads usually from ONT) or bam (pre-aligned reads by user)`
- Author's recommendation: [`README.md` line 298](https://github.com/Tfronta/strspy/blob/b4c3cc6ab3c866788ec456c22597a112d5237def/README.md#L298): `***Tip: Its good practice to use pre-aligned bams for quicker outcomes.***`

## Provenance of this trial (upstream vs. STRhub choices)

### From upstream documentation

- Install (conda): `README.md:L71-L72`
- Command: `README.md:L120`
- Input format: `bam` (`README.md:L44`)
- Supported platforms: ont (`README.md:L44`)
- Reference assembly: `both` (`README.md:L33`)

### Mechanically derived bindings

- `sample.bam` -> `/data/in/input.bam` (declared dataset mount)

### Selected by STRhub for this trial

- Dataset selected by STRhub: `ont-bam-hg38` — STRhub selected 'ont-bam-hg38' as compatible with upstream input 'bam' and platform 'ont'
- Platform used: `ont` (single documented platform)
- Base environment supplied by STRhub: `ubuntu:22.04`; added beyond plain Ubuntu: Miniforge (conda, python, pip)

## What this run needed beyond the repository

The result above describes a run configured as follows. Anyone repeating it needs the same things.

- Test data: no sample from the repository was used, so a public reference sample stood in.
- A base environment for the documented installation: STRhub ran the repository's install commands unchanged on Ubuntu 22.04, package lists refreshed, apt answering yes, plus Miniforge (conda, python, pip). Base-image and package versions are not frozen by the commands.

## Notes from reading the repository

Recorded automatically from the tool's public files when this run was configured. **Not verified by execution**, and not part of the gates above. Useful for what to check by hand.

- Environment: STRhub transcribed the documented installation commands unchanged into its own carrier (Ubuntu 22.04, package lists refreshed, apt answering yes, plus Miniforge (conda, python, pip)).
- Input: the README documents BAM and FASTQ (line 44); this plan selects STRhub's ont-bam-hg38 reference data. The author recommends BAM (line 298: "Tip: Its good practice to use pre-aligned bams for quicker outcomes.").
- read_path: sample.bam -> /data/in/input.bam.
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
- No forensic validation of results
- Short-read limitations apply (very long STR alleles may not span reads)

## Scope (read this)

Assessment of documented execution in the stated environment and output format. Concerns reproducible execution only; no claim of accuracy, casework fitness, or regulatory validation.

This is **not** a claim that the genotypes are correct, nor that the tool is fit for casework or meets any regulatory standard. Concordance against known truth is out of scope.

Verified automatically, in a clean environment, on the tool's public source at the pinned commit. This is a record of what happened, not an endorsement by the tool's author.

