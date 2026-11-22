# STRhub Verified: STRique (strique)

**Could not be determined.**

## As it is in the repository

**Step 1, the documented run: STRhub could not attempt the documented run.** STRhub holds no reference sample of the kind this procedure reads, and the repository ships no example to run, so nothing was executed. The limitation is ours. Nothing here is a finding about the tool.

**Verdict: Could not be determined.** STRhub holds no reference sample of the kind this procedure reads, and the repository ships no example to run, so nothing was executed.

What stopped it, and what its owner can be asked:

- STRhub has no reference sample of the kind this tool reads, and the repository ships no example to run, so nothing was executed.
  - The tool's owner: open an issue, "Ship a small example dataset".
- The environment did not build from the install steps found in the repository.
  - The tool's owner: open an issue, "Build fails from a clean checkout".

What the README does not say:

- The README does not say what kind of data the tool takes (FASTQ or BAM; Illumina or nanopore; reference build).

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
cd '.' && touch /tmp/.strhub_mark && ( cat /host/my_data.hg19.sam | python3 scripts/STRique.py count /host/my_data/reads.fofn models/r9_4_450bps.model configs/repeat_config.tsv > /host/my_data.hg19.strique.tsv ); rc=$?; find . -xdev -type f -newer /tmp/.strhub_mark -size +0 ! -path './.git/*' ! -path './proc/*' ! -path './sys/*' ! -path './dev/*' ! -path './data/*' ! -path '*/__pycache__/*' ! -name '*.pyc' ! -name '*.pyo' 2>/dev/null | head -500 | while IFS= read -r f; do mkdir -p "/data/out/$(dirname "$f")" && cp "$f" "/data/out/$f"; done; exit $rc
```

## Run details

- Source: `https://github.com/giesselmann/STRique` @ `ade4589ecb2bf6672c839e31b80b7cc0c0d7b084`
- Environment: ubuntu-22.04 (`Dockerfile`)
- Generated: 2026-11-22T19:13:55+00:00
- Upstream: The verified commit is 12 commit(s) behind `master`. That is context, not a fault: a pinned release is often meant to sit behind, and the attestation describes the commit it names.
- CI run: https://github.com/Tfronta/strhub-verified-next/actions/runs/45059500100

## Verification matrix

| Leg | Available | Result | Errors reported | Dataset |
|---|---|---|---|---|
| External data | N/A | N/A | — | None |
| Tool's own example | N/A | N/A | — | — |

## Evidence

What this run's configuration rests on, each item at the verified commit. Open any of them to check the claim it supports.
- Install method: [`Dockerfile`](https://github.com/giesselmann/STRique/blob/ade4589ecb2bf6672c839e31b80b7cc0c0d7b084/Dockerfile)
- Fallback environment: [`README.md` line 4](https://github.com/giesselmann/STRique/blob/ade4589ecb2bf6672c839e31b80b7cc0c0d7b084/README.md#L4): `[![Docker Cloud Build Status](https://img.shields.io/docker/cloud/build/giesselmann/strique.svg)](https://hub.docker.com/r/giesselmann/strique/)`
- Run command: [`docs/examples/intro.md` line 86](https://github.com/giesselmann/STRique/blob/ade4589ecb2bf6672c839e31b80b7cc0c0d7b084/docs/examples/intro.md#L86): `cat /host/my_data.hg19.sam | python3 scripts/STRique.py count \`
- Example data: [`data/c9orf72.fa`](https://github.com/giesselmann/STRique/blob/ade4589ecb2bf6672c839e31b80b7cc0c0d7b084/data/c9orf72.fa)

## Provenance of this trial (upstream vs. STRhub choices)

### From upstream documentation

- Install (dockerfile): `repo_file:Dockerfile`
- Command: `docs/examples/intro.md:L86`
- Supported platforms: ont (`README.md:L9`)
- Reference assembly: `hg19_only` (`docs/examples/intro.md:L42`)

## Notes from reading the repository

Recorded automatically from the tool's public files when this run was configured. **Not verified by execution**, and not part of the gates above. Useful for what to check by hand.

- Environment: no proven installation profile; STRhub did not manufacture installation steps. STRhub does not build a Dockerfile shipped in a repository.
- Run command: the one documented in docs/examples/intro.md (line 86), rewritten to STRhub's mounts; the capture wrapper is planned only if the procedure review passes.
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

