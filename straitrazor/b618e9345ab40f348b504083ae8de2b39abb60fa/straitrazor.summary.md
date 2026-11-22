# STRhub Verified: straitrazor (straitrazor)

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

**known issues** (README line 114)

> There's been one computer architecture (windows 7 + Xeon processor) that's caused some issues with the str8rzr.exe executable. In this case, str8rzr would occassionally crash, and I had to recompile it for that computer (and since then it's been fine). Please let me know if you experience problems-- especially crashes-- it'll let me further diagnose the exact problems therein.
> str8rzr is written in C/C++ with multithreading support using the pthreads library. This new release couples a new search strategy (see algorithm) coupled with a complete redesign of the code-base used to identify short…

### What the README or repository could add

Read off the repository at the verified commit. None of these changes the result above; each would make the tool easier for a new user, and for STRhub, to run as documented.

- The repository ships no example input. A small example the documented command can read, with the output it should produce, would let any user reproduce the run without outside data.

### Planned command

The run step was skipped. This command was not executed by that step.

```
cd '.' && touch /tmp/.strhub_mark && ( str8rzr -c configFile fastqfile > allsequences.txt ); rc=$?; find . -xdev -type f -newer /tmp/.strhub_mark -size +0 ! -path './.git/*' ! -path './proc/*' ! -path './sys/*' ! -path './dev/*' ! -path './data/*' ! -path '*/__pycache__/*' ! -name '*.pyc' ! -name '*.pyo' 2>/dev/null | head -500 | while IFS= read -r f; do mkdir -p "/data/out/$(dirname "$f")" && cp "$f" "/data/out/$f"; done; exit $rc
```

## Run details

- Source: `https://github.com/Ahhgust/STRaitRazor` @ `b618e9345ab40f348b504083ae8de2b39abb60fa`
- Environment: ubuntu-22.04 (`Dockerfile`)
- Generated: 2026-11-22T19:13:23+00:00
- Upstream: The verified commit is the head of `master`.
- CI run: https://github.com/Tfronta/strhub-verified-next/actions/runs/45059461312

## Verification matrix

| Leg | Available | Result | Errors reported | Dataset |
|---|---|---|---|---|
| External data | N/A | N/A | — | None |
| Tool's own example | N/A | N/A | — | — |

## Evidence

What this run's configuration rests on, each item at the verified commit. Open any of them to check the claim it supports.
- Install method: [`Makefile`](https://github.com/Ahhgust/STRaitRazor/blob/b618e9345ab40f348b504083ae8de2b39abb60fa/Makefile)
- Run command: [`README.md` line 123](https://github.com/Ahhgust/STRaitRazor/blob/b618e9345ab40f348b504083ae8de2b39abb60fa/README.md#L123): `str8rzr -c configFile fastqfile > allsequences.txt`
- Known issue: [`README.md` line 114](https://github.com/Ahhgust/STRaitRazor/blob/b618e9345ab40f348b504083ae8de2b39abb60fa/README.md#L114): `known issues`
- Documented input: [`README.md` line 19](https://github.com/Ahhgust/STRaitRazor/blob/b618e9345ab40f348b504083ae8de2b39abb60fa/README.md#L19): `Put str8rzr.exe, batchCstr8.bat, the appropriate config file (Forenseq.config), and all fastq files into this directory.<br>`

## Provenance of this trial (upstream vs. STRhub choices)

### From upstream documentation

- Install (make): `repo_file:Makefile`
- Command: `README.md:L123`
- Input format: `fastq` (`README.md:L19`)
- Supported platforms: illumina (`README.md:L8`)
- Reference assembly: `hg38` (`README.md:L211`)

### Selected by STRhub for this trial

- Dataset selected by STRhub: `illumina-str-fastq` — STRhub selected 'illumina-str-fastq' as compatible with upstream input 'fastq' and platform 'illumina'
- Platform used: `illumina` (single documented platform)

## Notes from reading the repository

Recorded automatically from the tool's public files when this run was configured. **Not verified by execution**, and not part of the gates above. Useful for what to check by hand.

- Environment: no proven installation profile; STRhub did not manufacture installation steps.
- Input: the README documents FASTQ (line 19); this plan selects STRhub's illumina-str-fastq reference data.
- Evaluator limitation: unresolved placeholder; no value was invented.
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

