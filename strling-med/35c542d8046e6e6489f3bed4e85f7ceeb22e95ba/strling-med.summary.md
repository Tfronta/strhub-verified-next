# STRhub Verified: STRling (strling-med)

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
cd '.' && touch /tmp/.strhub_mark && ( ../strling call -v -o single/CANVAS.chr4-39348425_AAGGG_0_400 CANVAS.chr4-39348425_AAGGG_0_400.bam single/CANVAS.chr4-39348425_AAGGG_0_400.str.bin ); rc=$?; find . -xdev -type f -newer /tmp/.strhub_mark -size +0 ! -path './.git/*' ! -path './proc/*' ! -path './sys/*' ! -path './dev/*' ! -path './data/*' ! -path '*/__pycache__/*' ! -name '*.pyc' ! -name '*.pyo' 2>/dev/null | head -500 | while IFS= read -r f; do mkdir -p "/data/out/$(dirname "$f")" && cp "$f" "/data/out/$f"; done; exit $rc
```

## Run details

- Source: `https://github.com/quinlan-lab/STRling` @ `35c542d8046e6e6489f3bed4e85f7ceeb22e95ba`
- Environment: ubuntu-22.04 (`Dockerfile`)
- Generated: 2026-11-22T19:14:42+00:00
- Upstream: The verified commit is the head of `master`.
- CI run: https://github.com/Tfronta/strhub-verified-next/actions/runs/45059560669

## Verification matrix

| Leg | Available | Result | Errors reported | Dataset |
|---|---|---|---|---|
| External data | N/A | N/A | — | None |
| Tool's own example | N/A | N/A | — | — |

## Evidence

What this run's configuration rests on, each item at the verified commit. Open any of them to check the claim it supports.
- Run command: [`docs/source/test.rst` line 34](https://github.com/quinlan-lab/STRling/blob/35c542d8046e6e6489f3bed4e85f7ceeb22e95ba/docs/source/test.rst#L34): `../strling call -v -o single/CANVAS.chr4-39348425_AAGGG_0_400 CANVAS.chr4-39348425_AAGGG_0_400.bam single/CANVAS.chr4-39348425_AAGGG_0_400.str.bin`
- Example data: [`data/hg38.STR_disease_loci.bed`](https://github.com/quinlan-lab/STRling/blob/35c542d8046e6e6489f3bed4e85f7ceeb22e95ba/data/hg38.STR_disease_loci.bed)
- Example data: [`sim/htt_locus.bed`](https://github.com/quinlan-lab/STRling/blob/35c542d8046e6e6489f3bed4e85f7ceeb22e95ba/sim/htt_locus.bed)
- Example data: [`sim/disease_loci_sims_minpath.bed`](https://github.com/quinlan-lab/STRling/blob/35c542d8046e6e6489f3bed4e85f7ceeb22e95ba/sim/disease_loci_sims_minpath.bed)

## Provenance of this trial (upstream vs. STRhub choices)

### From upstream documentation

- Install (release_binary): `release_asset:strling`
- Command: `docs/source/test.rst:L34`
- Input format: `bam` (`docs/source/test.rst:L34`)
- Supported platforms: illumina (`README.md:L9`)
- Reference assembly: `hg38` (`docs/source/test.rst:L29`)

### Selected by STRhub for this trial

- Dataset selected by STRhub: `illumina-bam-hg38-med` — STRhub selected 'illumina-bam-hg38-med' as compatible with upstream input 'bam' and platform 'illumina'; shipped catalog 'data/hg38.STR_disease_loci.bed' overlaps 31 medical panel loci and 0 forensic loci
- Platform used: `illumina` (single documented platform)

## Notes from reading the repository

Recorded automatically from the tool's public files when this run was configured. **Not verified by execution**, and not part of the gates above. Useful for what to check by hand.

- Environment: no proven installation profile; STRhub did not manufacture installation steps.
- Input: the documented command takes BAM (docs/source/test.rst, line 34); no sentence says so, so the command is what was read. This plan selects STRhub's illumina-bam-hg38-med reference data.
- Panel: the shipped loci catalog (data/hg38.STR_disease_loci.bed) overlaps 31 loci in STRhub's medical STR slice and 0 in the forensic slice; this plan selects STRhub's illumina-bam-hg38-med reference data.
- Evaluator limitation: a read-file argument is outside the closed input substitution table.
- Run command: the one documented in docs/source/test.rst (line 34), rewritten to STRhub's mounts; the capture wrapper is planned only if the procedure review passes.

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

