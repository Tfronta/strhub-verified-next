# STRhub Verified: TRTools (trtools)

**Could not be determined.**

## As it is in the repository

**Step 1, the documented run: STRhub could not attempt the documented run.** STRhub holds no reference sample of the kind this procedure reads, and the repository ships no example to run, so nothing was executed. The limitation is ours. Nothing here is a finding about the tool.

**Verdict: Could not be determined.** STRhub holds no reference sample of the kind this procedure reads, and the repository ships no example to run, so nothing was executed.

What stopped it, and what its owner can be asked:

- No command line invoking the tool was found in the README.
  - The tool's owner: open an issue, "Document the command that runs the tool".
- STRhub has no reference sample of the kind this tool reads, and the repository ships no example to run, so nothing was executed.
  - The tool's owner: open an issue, "Ship a small example dataset".
- The environment did not build from the install steps found in the repository.
  - The tool's owner: open an issue, "Build fails from a clean checkout".

What the README does not say:

- No command line invoking the tool was found in the README's code blocks.

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

- Source: `https://github.com/gymreklab/TRTools` @ `ce22d847ea954e4f015818dc288dfa87a47761a8`
- Environment: ubuntu-22.04 (`Dockerfile`)
- Generated: 2026-11-22T19:14:06+00:00
- Upstream: The verified commit is 6 commit(s) behind `master`. That is context, not a fault: a pinned release is often meant to sit behind, and the attestation describes the commit it names.
- CI run: https://github.com/Tfronta/strhub-verified-next/actions/runs/45059511855

## Verification matrix

| Leg | Available | Result | Errors reported | Dataset |
|---|---|---|---|---|
| External data | N/A | N/A | — | None |
| Tool's own example | N/A | N/A | — | — |

## Evidence

What this run's configuration rests on, each item at the verified commit. Open any of them to check the claim it supports.
- Install method: [`pyproject.toml`](https://github.com/gymreklab/TRTools/blob/ce22d847ea954e4f015818dc288dfa87a47761a8/pyproject.toml)
- Example data: [`example-files/dummy_A_pos.bed`](https://github.com/gymreklab/TRTools/blob/ce22d847ea954e4f015818dc288dfa87a47761a8/example-files/dummy_A_pos.bed)
- Example data: [`trtools/testsupport/sample_simtrdata/CBL.fa`](https://github.com/gymreklab/TRTools/blob/ce22d847ea954e4f015818dc288dfa87a47761a8/trtools/testsupport/sample_simtrdata/CBL.fa)
- Example data: [`example-files/sample1_advntr.vcf.gz`](https://github.com/gymreklab/TRTools/blob/ce22d847ea954e4f015818dc288dfa87a47761a8/example-files/sample1_advntr.vcf.gz)
- Example data: [`example-files/sample2_advntr.vcf.gz`](https://github.com/gymreklab/TRTools/blob/ce22d847ea954e4f015818dc288dfa87a47761a8/example-files/sample2_advntr.vcf.gz)
- Example data: [`trtools/testsupport/sample_vcfs/mergeSTR_vcfs/test_file_advntr2.vcf.gz`](https://github.com/gymreklab/TRTools/blob/ce22d847ea954e4f015818dc288dfa87a47761a8/trtools/testsupport/sample_vcfs/mergeSTR_vcfs/test_file_advntr2.vcf.gz)
- Documented input: [`README.rst` line 10](https://github.com/gymreklab/TRTools/blob/ce22d847ea954e4f015818dc288dfa87a47761a8/README.rst#L10): `mergeSTR --vcfs ceu_ex.vcf.gz,yri_ex.vcf.gz --out merged`

## Provenance of this trial (upstream vs. STRhub choices)

### From upstream documentation

- Install (pip): `repo_file:pyproject.toml`
- Input format: `vcf` (not explicitly stated)
- Supported platforms: ont (`doc/CALLERS.rst:L43`)
- Reference assembly: `both` (`doc/CALLERS.rst:L62`)

### Selected by STRhub for this trial

- Platform used: `ont` (single documented platform)

## Notes from reading the repository

Recorded automatically from the tool's public files when this run was configured. **Not verified by execution**, and not part of the gates above. Useful for what to check by hand.

- Environment: no proven installation profile; STRhub did not manufacture installation steps.

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

