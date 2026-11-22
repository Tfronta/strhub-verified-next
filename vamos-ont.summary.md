# STRhub Verified: vamos (vamos-ont)

**Could not be determined.**

## As it is in the repository

**Step 1, the documented run: As documented, a third party cannot tell how to run it.** An installation step is outside this profile (README.md, line 32: `cd vamos*/src/ && make`); STRhub does not interpret, complete or skip it. Nothing was executed. That does not mean the tool does not work: what the guide asks for is missing from the README at this commit. Add it and try the link again on the new commit.

Missing from the commit, by the blocks docs/GUIA-PASO-1.md asks for:

- Installation, copyable

**Verdict: Could not be determined.** An installation step is outside this profile (README.md, line 32: `cd vamos*/src/ && make`); STRhub does not interpret, complete or skip it.

What stopped it, and what its owner can be asked:

- An installation step is outside this profile (README.md, line 32: `cd vamos*/src/ && make`); STRhub does not interpret, complete or skip it.
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
cd '.' && touch /tmp/.strhub_mark && ( vamos --read -b /data/in/input.bam -r vamos.effMotifs-0.1.GRCh38.tsv -s NA24385_CCS_h1 -o reads.vcf -t 8 ); rc=$?; find . -xdev -type f -newer /tmp/.strhub_mark -size +0 ! -path './.git/*' ! -path './proc/*' ! -path './sys/*' ! -path './dev/*' ! -path './data/*' ! -path '*/__pycache__/*' ! -name '*.pyc' ! -name '*.pyo' 2>/dev/null | head -500 | while IFS= read -r f; do mkdir -p "/data/out/$(dirname "$f")" && cp "$f" "/data/out/$f"; done; exit $rc
```

## Run details

- Source: `https://github.com/ChaissonLab/vamos` @ `5c4a069847fbe6ca6067de1bff6098c9403db9ec`
- Environment: ubuntu-22.04 (`Dockerfile`)
- Generated: 2026-11-22T19:14:15+00:00
- Upstream: The verified commit is 3 commit(s) behind `master`. That is context, not a fault: a pinned release is often meant to sit behind, and the attestation describes the commit it names.
- CI run: https://github.com/Tfronta/strhub-verified-next/actions/runs/45059523245

## Verification matrix

| Leg | Available | Result | Errors reported | Dataset |
|---|---|---|---|---|
| External data | N/A | N/A | — | None |
| Tool's own example | N/A | N/A | — | — |

## Evidence

What this run's configuration rests on, each item at the verified commit. Open any of them to check the claim it supports.
- Install method: [`requirements.txt`](https://github.com/ChaissonLab/vamos/blob/5c4a069847fbe6ca6067de1bff6098c9403db9ec/requirements.txt)
- Run command: [`README.md` line 69](https://github.com/ChaissonLab/vamos/blob/5c4a069847fbe6ca6067de1bff6098c9403db9ec/README.md#L69): `vamos --read -b ../example/demo.aln.bam -r vamos.effMotifs-0.1.GRCh38.tsv -s NA24385_CCS_h1 -o reads.vcf -t 8`
- Example data: [`tryvamos/example/loci_for_waterfall.bed`](https://github.com/ChaissonLab/vamos/blob/5c4a069847fbe6ca6067de1bff6098c9403db9ec/tryvamos/example/loci_for_waterfall.bed)
- Example data: [`example/one_region_motif.bed`](https://github.com/ChaissonLab/vamos/blob/5c4a069847fbe6ca6067de1bff6098c9403db9ec/example/one_region_motif.bed)
- Example data: [`tryvamos/example/HPRC_HG005_h2.contig.vcf`](https://github.com/ChaissonLab/vamos/blob/5c4a069847fbe6ca6067de1bff6098c9403db9ec/tryvamos/example/HPRC_HG005_h2.contig.vcf)
- Example data: [`tryvamos/example/HPRC_HG002_h2.contig.vcf`](https://github.com/ChaissonLab/vamos/blob/5c4a069847fbe6ca6067de1bff6098c9403db9ec/tryvamos/example/HPRC_HG002_h2.contig.vcf)
- Example data: [`tryvamos/example/HPRC_HG005_h1.contig.vcf`](https://github.com/ChaissonLab/vamos/blob/5c4a069847fbe6ca6067de1bff6098c9403db9ec/tryvamos/example/HPRC_HG005_h1.contig.vcf)
- Documented input: [`README.md` line 18](https://github.com/ChaissonLab/vamos/blob/5c4a069847fbe6ca6067de1bff6098c9403db9ec/README.md#L18): `Most functionality of *tryvamos* uses multi-sample diploid vcf(s) as input.`

## Provenance of this trial (upstream vs. STRhub choices)

### From upstream documentation

- Install (conda): `repo_file:requirements.txt`
- Command: `README.md:L69`
- Input format: `vcf` (`README.md:L69`)
- Reference assembly: `hg38` (`README.md:L52`)
- Regions schema: `motif` (`README.md:L45`)

### Mechanically derived bindings

- `../example/demo.aln.bam` -> `/data/in/input.bam` (declared dataset mount)

### Selected by STRhub for this trial

- Dataset selected by STRhub: `ont-bam-hg38` — STRhub selected 'ont-bam-hg38' as compatible with upstream input 'vcf' and platform 'ont'

## Notes from reading the repository

Recorded automatically from the tool's public files when this run was configured. **Not verified by execution**, and not part of the gates above. Useful for what to check by hand.

- Environment: no proven installation profile; STRhub did not manufacture installation steps.
- Input: the documented command takes BAM (README.md, line 69); no sentence says so, so the command is what was read. This plan selects STRhub's ont-bam-hg38 reference data.
- read_path: ../example/demo.aln.bam -> /data/in/input.bam.
- Run command: the README's own command, rewritten to STRhub's mounts; the capture wrapper is planned only if the procedure review passes.
- File: the documented command reads vamos.effMotifs-0.1.GRCh38.tsv (after -r), which is neither in the repository nor among STRhub's data.

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

