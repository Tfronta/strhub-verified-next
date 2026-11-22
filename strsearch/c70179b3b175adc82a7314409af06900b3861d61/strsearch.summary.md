# STRhub Verified: STRsearch (strsearch)

**Could not be determined.**

## As it is in the repository

**Step 1, the documented run: As documented, a third party cannot tell how to run it.** An installation step is outside this profile (README.md, line 22: `wget https://github.com/AnJingwd/STRsearch/archive/master.zip`); STRhub does not interpret, complete or skip it. Nothing was executed. That does not mean the tool does not work: what the guide asks for is missing from the README at this commit. Add it and try the link again on the new commit.

Missing from the commit, by the blocks docs/GUIA-PASO-1.md asks for:

- Installation, copyable

**Verdict: Could not be determined.** An installation step is outside this profile (README.md, line 22: `wget https://github.com/AnJingwd/STRsearch/archive/master.zip`); STRhub does not interpret, complete or skip it.

What stopped it, and what its owner can be asked:

- An installation step is outside this profile (README.md, line 22: `wget https://github.com/AnJingwd/STRsearch/archive/master.zip`); STRhub does not interpret, complete or skip it.
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
cd '.' && touch /tmp/.strhub_mark && ( python3 pipeline.py from_bam --working_path example/test_results --sample test --sex male --bam /data/in/input.bam --ref_bed /data/in/regions.bed --genotypes example/test_results/test_genotypes.txt --multiple_alleles example/test_results/test_multiple_alleles.txt --qc_matrix example/test_results/test_qc_matrix.txt ); rc=$?; find . -xdev -type f -newer /tmp/.strhub_mark -size +0 ! -path './.git/*' ! -path './proc/*' ! -path './sys/*' ! -path './dev/*' ! -path './data/*' ! -path '*/__pycache__/*' ! -name '*.pyc' ! -name '*.pyo' 2>/dev/null | head -500 | while IFS= read -r f; do mkdir -p "/data/out/$(dirname "$f")" && cp "$f" "/data/out/$f"; done; exit $rc
```

## Run details

- Source: `https://github.com/AnJingwd/STRsearch` @ `c70179b3b175adc82a7314409af06900b3861d61`
- Environment: ubuntu-22.04 (`Dockerfile`)
- Generated: 2026-11-22T19:13:42+00:00
- Upstream: The verified commit is the head of `master`.
- CI run: https://github.com/Tfronta/strhub-verified-next/actions/runs/45059480777

## Verification matrix

| Leg | Available | Result | Errors reported | Dataset |
|---|---|---|---|---|
| External data | N/A | N/A | — | None |
| Tool's own example | N/A | N/A | — | — |

## Evidence

What this run's configuration rests on, each item at the verified commit. Open any of them to check the claim it supports.
- Published image: [`README.md` line 223](https://github.com/AnJingwd/STRsearch/blob/c70179b3b175adc82a7314409af06900b3861d61/README.md#L223): `docker pull anjing123/strsearch:latest`
- Run command: [`README.md` line 107](https://github.com/AnJingwd/STRsearch/blob/c70179b3b175adc82a7314409af06900b3861d61/README.md#L107): `python3 pipeline.py from_bam \`
- Example data: [`example/ref_test.bed`](https://github.com/AnJingwd/STRsearch/blob/c70179b3b175adc82a7314409af06900b3861d61/example/ref_test.bed)
- Example data: [`example/test_data/test.bam`](https://github.com/AnJingwd/STRsearch/blob/c70179b3b175adc82a7314409af06900b3861d61/example/test_data/test.bam)
- Example data: [`example/test_data/test_R1.fastq`](https://github.com/AnJingwd/STRsearch/blob/c70179b3b175adc82a7314409af06900b3861d61/example/test_data/test_R1.fastq)
- Example data: [`example/test_data/test_R2.fastq`](https://github.com/AnJingwd/STRsearch/blob/c70179b3b175adc82a7314409af06900b3861d61/example/test_data/test_R2.fastq)
- Example data: [`example/test_output/STRfq/Marker94_reads_test_sortByname.bam`](https://github.com/AnJingwd/STRsearch/blob/c70179b3b175adc82a7314409af06900b3861d61/example/test_output/STRfq/Marker94_reads_test_sortByname.bam)
- Documented input: [`README.md` line 77](https://github.com/AnJingwd/STRsearch/blob/c70179b3b175adc82a7314409af06900b3861d61/README.md#L77): `FASTQ file or BAM-file from singe-end or paird-end sequencing platforms`

## Provenance of this trial (upstream vs. STRhub choices)

### From upstream documentation

- Install (docker_image): `README.md:L223`
- Command: `README.md:L107`
- Input format: `bam` (`README.md:L77`)
- Reference assembly: `hg19_only` (`README.md:L101`)
- Regions schema: `strsearch` (`README.md:L49`)

### Mechanically derived bindings

- `example/test_results/alignments/test.bam` -> `/data/in/input.bam` (declared dataset mount)
- `example/ref_test.bed` -> `/data/in/regions.bed` (registered regions file (strsearch))
- Regions layout `strsearch` matched `strsearch` (`README.md:L49`)

### Selected by STRhub for this trial

- Dataset selected by STRhub: `illumina-bam-hg38` — STRhub selected 'illumina-bam-hg38' as compatible with upstream input 'bam' and platform 'illumina'
- Regions file mounted: `strsearch`

## Notes from reading the repository

Recorded automatically from the tool's public files when this run was configured. **Not verified by execution**, and not part of the gates above. Useful for what to check by hand.

- Environment: no proven installation profile; STRhub did not manufacture installation steps.
- Input: the README documents BAM and FASTQ (line 77); this plan selects STRhub's illumina-bam-hg38 reference data.
- read_path: example/test_results/alignments/test.bam -> /data/in/input.bam.
- regions_path: example/ref_test.bed -> /data/in/regions.bed.
- Run command: the README's own command, rewritten to STRhub's mounts; the capture wrapper is planned only if the procedure review passes.
- Documentation mentions hg19/GRCh37 only; STRhub reference BAMs are hg38

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

