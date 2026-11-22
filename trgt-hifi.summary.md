# STRhub Verified: TRGT (trgt-hifi)

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

### Author-documented warnings and limitations

Quoted from the repository's README at the verified commit. STRhub did not establish any of this by running the tool; it is the author's own note about their own software.

**Active development warning** (README line 18)

> Please note that TRGT is still under active development. We anticipate some
> changes to the input and output file formats of TRGT.

### Planned command

The run step was skipped. This command was not executed by that step.

```
cd '.' && touch /tmp/.strhub_mark && ( ./trgt genotype --genome /data/ref/hg38.fa --repeats /data/in/regions.bed --reads /data/in/input.bam --output-prefix sample ); rc=$?; find . -xdev -type f -newer /tmp/.strhub_mark -size +0 ! -path './.git/*' ! -path './proc/*' ! -path './sys/*' ! -path './dev/*' ! -path './data/*' ! -path '*/__pycache__/*' ! -name '*.pyc' ! -name '*.pyo' 2>/dev/null | head -500 | while IFS= read -r f; do mkdir -p "/data/out/$(dirname "$f")" && cp "$f" "/data/out/$f"; done; exit $rc
```

## Run details

- Source: `https://github.com/PacificBiosciences/trgt` @ `b21c6217eeaef9a080205932fe29f730dc00e31f`
- Environment: ubuntu-22.04 (`Dockerfile`)
- Generated: 2026-11-22T19:13:30+00:00
- Upstream: The verified commit is the head of `main`.
- CI run: https://github.com/Tfronta/strhub-verified-next/actions/runs/45059467962

## Verification matrix

| Leg | Available | Result | Errors reported | Dataset |
|---|---|---|---|---|
| External data | N/A | N/A | — | None |
| Tool's own example | N/A | N/A | — | — |

## Evidence

What this run's configuration rests on, each item at the verified commit. Open any of them to check the claim it supports.
- Run command: [`docs/tutorial.md` line 39](https://github.com/PacificBiosciences/trgt/blob/b21c6217eeaef9a080205932fe29f730dc00e31f/docs/tutorial.md#L39): `./trgt genotype --genome example/reference.fasta \`
- Example data: [`example/repeat.bed`](https://github.com/PacificBiosciences/trgt/blob/b21c6217eeaef9a080205932fe29f730dc00e31f/example/repeat.bed)
- Example data: [`example/reference.fasta`](https://github.com/PacificBiosciences/trgt/blob/b21c6217eeaef9a080205932fe29f730dc00e31f/example/reference.fasta)
- Example data: [`example/sample.bam`](https://github.com/PacificBiosciences/trgt/blob/b21c6217eeaef9a080205932fe29f730dc00e31f/example/sample.bam)
- Example data: [`repeats/pathogenic_repeats.hg38.bed`](https://github.com/PacificBiosciences/trgt/blob/b21c6217eeaef9a080205932fe29f730dc00e31f/repeats/pathogenic_repeats.hg38.bed)
- Example data: [`repeats/repeat_catalog.hg38.bed`](https://github.com/PacificBiosciences/trgt/blob/b21c6217eeaef9a080205932fe29f730dc00e31f/repeats/repeat_catalog.hg38.bed)
- Known issue: [`README.md` line 18](https://github.com/PacificBiosciences/trgt/blob/b21c6217eeaef9a080205932fe29f730dc00e31f/README.md#L18): `Active development warning`
- Documented input: [`README.md` line 9](https://github.com/PacificBiosciences/trgt/blob/b21c6217eeaef9a080205932fe29f730dc00e31f/README.md#L9): `It is now possible to add a fail reads BAM as a separate aligned BAM in addition to the primary `--reads` BAM.`

## Provenance of this trial (upstream vs. STRhub choices)

### From upstream documentation

- Install (release_binary): `release_asset:trgt-v5.1.0-x86_64-unknown-linux-gnu.tar.gz`
- Command: `docs/tutorial.md:L39`
- Input format: `bam` (`CHANGELOG.md:L9`)
- Supported platforms: pacbio (`README.md:L5`)
- Reference assembly: `hg38` (`README.md:L36`)
- Regions schema: `trgt` (`docs/tutorial.md:L28`)

### Mechanically derived bindings

- `example/reference.fasta` -> `/data/ref/hg38.fa` (registered reference genome mount)
- `example/repeat.bed` -> `/data/in/regions.bed` (registered regions file (trgt))
- `example/sample.bam` -> `/data/in/input.bam` (declared dataset mount)
- Regions layout `trgt` matched `trgt` (`docs/tutorial.md:L28`)

### Selected by STRhub for this trial

- Dataset selected by STRhub: `pacbio-hifi-bam-hg38` — STRhub selected 'pacbio-hifi-bam-hg38' as compatible with upstream input 'bam' and platform 'pacbio'
- Platform used: `pacbio` (single documented platform)
- Regions file mounted: `trgt`

## Notes from reading the repository

Recorded automatically from the tool's public files when this run was configured. **Not verified by execution**, and not part of the gates above. Useful for what to check by hand.

- Environment: no proven installation profile; STRhub did not manufacture installation steps.
- Input: the README documents BAM (line 9); this plan selects STRhub's pacbio-hifi-bam-hg38 reference data.
- reference_path: example/reference.fasta -> /data/ref/hg38.fa.
- regions_path: example/repeat.bed -> /data/in/regions.bed.
- read_path: example/sample.bam -> /data/in/input.bam.
- Run command: the one documented in docs/tutorial.md (line 39), rewritten to STRhub's mounts; the capture wrapper is planned only if the procedure review passes.

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

