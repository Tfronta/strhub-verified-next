# STRhub Verified: STRetch (stretch)

**Could not be determined.**

## As it is in the repository

**Step 1, the documented run: As documented, a third party cannot tell how to run it.** No repository document shows an installation this profile can transcribe literally; no missing step, dependency or choice was supplied by STRhub. Nothing was executed. That does not mean the tool does not work: what the guide asks for is missing from the README at this commit. Add it and try the link again on the new commit.

Missing from the commit, by the blocks docs/GUIA-PASO-1.md asks for:

- Installation, copyable

**Verdict: Could not be determined.** No repository document shows an installation this profile can transcribe literally; no missing step, dependency or choice was supplied by STRhub.

What stopped it, and what its owner can be asked:

- No repository document shows an installation this profile can transcribe literally; no missing step, dependency or choice was supplied by STRhub.
  - The tool's owner: open an issue, "Write the installation as commands that can be copied and run".
- The documented command reads a file that is not in the repository at this commit and that STRhub does not hold, so the command cannot run as written.
  - The tool's owner: open an issue, "Ship, or link from the README, the file the documented command reads".

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
cd '.' && touch /tmp/.strhub_mark && ( STRetch/tools/bin/bpipe run -p input_regions=all_STRs_in_genome.bed STRetch/pipelines/STRetch_wgs_bam_pipeline.groovy sample1.bam sample2.bam ); rc=$?; find . -xdev -type f -newer /tmp/.strhub_mark -size +0 ! -path './.git/*' ! -path './proc/*' ! -path './sys/*' ! -path './dev/*' ! -path './data/*' ! -path '*/__pycache__/*' ! -name '*.pyc' ! -name '*.pyo' 2>/dev/null | head -500 | while IFS= read -r f; do mkdir -p "/data/out/$(dirname "$f")" && cp "$f" "/data/out/$f"; done; exit $rc
```

## Run details

- Source: `https://github.com/Oshlack/STRetch` @ `ce74895ad7b469a43972c9571009fea8cb1fe39c`
- Environment: ubuntu-22.04 (`Dockerfile`)
- Generated: 2026-11-22T19:14:32+00:00
- Upstream: The verified commit is 19 commit(s) behind `master`. That is context, not a fault: a pinned release is often meant to sit behind, and the attestation describes the commit it names.
- CI run: https://github.com/Tfronta/strhub-verified-next/actions/runs/45059547695

## Verification matrix

| Leg | Available | Result | Errors reported | Dataset |
|---|---|---|---|---|
| External data | N/A | N/A | — | None |
| Tool's own example | N/A | N/A | — | — |

## Evidence

What this run's configuration rests on, each item at the verified commit. Open any of them to check the claim it supports.
- Install method: [`install.sh`](https://github.com/Oshlack/STRetch/blob/ce74895ad7b469a43972c9571009fea8cb1fe39c/install.sh)
- Run command: [`wiki/Running-STRetch` line 36](https://github.com/Oshlack/STRetch/wiki/Running-STRetch): ``STRetch/tools/bin/bpipe run -p input_regions=all_STRs_in_genome.bed STRetch/pipelines/STRetch_wgs_bam_pipeline.groovy sample1.bam sample2.bam``
- Example data: [`scripts/tests/test_data/49_L001_R1.STRdecoy.bam`](https://github.com/Oshlack/STRetch/blob/ce74895ad7b469a43972c9571009fea8cb1fe39c/scripts/tests/test_data/49_L001_R1.STRdecoy.bam)
- Example data: [`scripts/tests/test_data/11_L001_R1.STRdecoy.bam`](https://github.com/Oshlack/STRetch/blob/ce74895ad7b469a43972c9571009fea8cb1fe39c/scripts/tests/test_data/11_L001_R1.STRdecoy.bam)
- Documented input: [`README.md` line 34](https://github.com/Oshlack/STRetch/blob/ce74895ad7b469a43972c9571009fea8cb1fe39c/README.md#L34): `This pipeline takes a position sorted mapped bam file and extracts reads from it likely to contain STR sequence.`

## Provenance of this trial (upstream vs. STRhub choices)

### From upstream documentation

- Install (script): `repo_file:install.sh`
- Command: `wiki/Running-STRetch:L36`
- Input format: `bam` (`wiki/Running-STRetch:L34`)
- Supported platforms: illumina (`README.md:L15`)
- Reference assembly: not specified in repository documentation

### Selected by STRhub for this trial

- Dataset selected by STRhub: `illumina-bam-hg38` — STRhub selected 'illumina-bam-hg38' as compatible with upstream input 'bam' and platform 'illumina'
- Platform used: `illumina` (single documented platform)
- Assembly chosen by STRhub: `hg38` (upstream unspecified; STRhub staged coherent BAM, FASTA and regions on hg38)

## Notes from reading the repository

Recorded automatically from the tool's public files when this run was configured. **Not verified by execution**, and not part of the gates above. Useful for what to check by hand.

- Environment: no proven installation profile; STRhub did not manufacture installation steps.
- Input: the README documents BAM (line 34); this plan selects STRhub's illumina-bam-hg38 reference data.
- Evaluator limitation: a read-file argument is outside the closed input substitution table.
- Evaluator limitation: a read-file argument is outside the closed input substitution table.
- Run command: the one documented on the wiki (wiki/Running-STRetch, line 36), rewritten to STRhub's mounts; the capture wrapper is planned only if the procedure review passes. A wiki is not versioned with the code: it was read as it is today.
- File: the documented command reads all_STRs_in_genome.bed (in input_regions=all_STRs_in_genome.bed), which is neither in the repository nor among STRhub's data.

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

