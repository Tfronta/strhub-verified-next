# STRhub Verified: tandem-genotypes (tandem-genotypes)

**Could not be determined.**

## As it is in the repository

**Step 1, the documented run: STRhub could not attempt the documented run.** STRhub holds no reference sample of the kind this procedure reads, and the repository ships no example to run, so nothing was executed. The limitation is ours. Nothing here is a finding about the tool.

**Verdict: Could not be determined.** STRhub holds no reference sample of the kind this procedure reads, and the repository ships no example to run, so nothing was executed.

What stopped it, and what its owner can be asked:

- STRhub has no reference sample of the kind this tool reads, and the repository ships no example to run, so nothing was executed.
  - The tool's owner: open an issue, "Ship a small example dataset".
- The environment did not build from the install steps found in the repository.
  - The tool's owner: open an issue, "Build fails from a clean checkout".

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

**Limitations** (README line 317)

> * `tandem-genotypes` doesn't work for tandem repeats at (or extremely
> near) the edge of a sequence. This is because it uses DNA reads
> that clearly align beyond both sides of the repeat.

### Planned command

The run step was skipped. This command was not executed by that step.

```
cd '.' && touch /tmp/.strhub_mark && ( tandem-genotypes -g refGene.txt microsat.txt alignments.maf > tg.txt ); rc=$?; find . -xdev -type f -newer /tmp/.strhub_mark -size +0 ! -path './.git/*' ! -path './proc/*' ! -path './sys/*' ! -path './dev/*' ! -path './data/*' ! -path '*/__pycache__/*' ! -name '*.pyc' ! -name '*.pyo' 2>/dev/null | head -500 | while IFS= read -r f; do mkdir -p "/data/out/$(dirname "$f")" && cp "$f" "/data/out/$f"; done; exit $rc
```

## Run details

- Source: `https://github.com/mcfrith/tandem-genotypes` @ `706a6b6a134788afb689e35445c67b4c2ae40666`
- Environment: ubuntu-22.04 (`Dockerfile`)
- Generated: 2026-11-22T19:14:10+00:00
- Upstream: The verified commit is the head of `master`.
- CI run: https://github.com/Tfronta/strhub-verified-next/actions/runs/45059506033

## Verification matrix

| Leg | Available | Result | Errors reported | Dataset |
|---|---|---|---|---|
| External data | N/A | N/A | — | None |
| Tool's own example | N/A | N/A | — | — |

## Evidence

What this run's configuration rests on, each item at the verified commit. Open any of them to check the claim it supports.
- Bioconda package: [`README.md` line 13](https://github.com/mcfrith/tandem-genotypes/blob/706a6b6a134788afb689e35445c67b4c2ae40666/README.md#L13): ``tandem-genotypes` from [bioconda](https://bioconda.github.io/).`
- Run command: [`README.md` line 21](https://github.com/mcfrith/tandem-genotypes/blob/706a6b6a134788afb689e35445c67b4c2ae40666/README.md#L21): `tandem-genotypes -g refGene.txt microsat.txt alignments.maf > tg.txt`
- Example data: [`tests/near-beg.bed`](https://github.com/mcfrith/tandem-genotypes/blob/706a6b6a134788afb689e35445c67b4c2ae40666/tests/near-beg.bed)
- Example data: [`tests/small-rep.bed`](https://github.com/mcfrith/tandem-genotypes/blob/706a6b6a134788afb689e35445c67b4c2ae40666/tests/small-rep.bed)
- Example data: [`tests/far.bed`](https://github.com/mcfrith/tandem-genotypes/blob/706a6b6a134788afb689e35445c67b4c2ae40666/tests/far.bed)
- Example data: [`tests/slop3.bed`](https://github.com/mcfrith/tandem-genotypes/blob/706a6b6a134788afb689e35445c67b4c2ae40666/tests/slop3.bed)
- Known issue: [`README.md` line 317](https://github.com/mcfrith/tandem-genotypes/blob/706a6b6a134788afb689e35445c67b4c2ae40666/README.md#L317): `Limitations`
- Documented input: [`README.md` line 103](https://github.com/mcfrith/tandem-genotypes/blob/706a6b6a134788afb689e35445c67b4c2ae40666/README.md#L103): `This uses 3 input files: the read sequences (in fastq or fasta`

## Provenance of this trial (upstream vs. STRhub choices)

### From upstream documentation

- Install (bioconda): `README.md:L13`
- Command: `README.md:L21`
- Input format: `fastq` (not explicitly stated)
- Reference assembly: `both` (`README.md:L122`)

## Notes from reading the repository

Recorded automatically from the tool's public files when this run was configured. **Not verified by execution**, and not part of the gates above. Useful for what to check by hand.

- Environment: no proven installation profile; STRhub did not manufacture installation steps.
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

