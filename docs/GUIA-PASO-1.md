# Documentation Requirements for Automated Verification (Step 1)

STRhub Verified tests one question first, before evaluating forensic STR panels:

> At the pinned commit, can a third party install the tool and run it end to end by following only what that commit documents, and obtain the declared output file?

STRhub does not guess missing steps, invent command flags, or silently patch your setup. If a required piece is missing, the report names the exact gap and does not run the tool.

**A tool that stops or returns "could not be determined" is not being judged as broken.** It means the documentation at that commit does not yet contain a complete, copyable procedure for an automated clean-environment run.

---

## Quick checklist (4 blocks)

For automated verification to run from your `README.md`, include:

1. **Copyable installation commands** in a code block under an installation heading.
2. **One concrete example command** (not an abstract usage synopsis).
3. **Declared input format and file path** (and reference assembly, if used).
4. **Declared output file or extension** written by that command.

---

## The four blocks in detail

### 1. Copyable installation

Put the exact install commands in a code block under an installation heading (such as `## Installation`, `## Setup`, `## Build`, or `### Create an environment`). STRhub runs them in order on a clean Ubuntu 22.04 container.

```bash
# Example: plain commands where every referenced file exists in the commit
conda env create -f environment.yml
conda activate mytool
pip install .
```

**Base environment provided automatically (and declared in the report):**
- Clean Ubuntu 22.04 with refreshed `apt` package lists (`apt` answering yes).
- Miniforge (`conda`, `python`, `pip`) when your commands use Conda or Python/pip.
- Minimal generic build toolchain (`build-essential`, and `cmake` when `cmake` is invoked) when compiling with `make`, `./configure`, or `cmake`. No tool-specific libraries are added.

**Commands STRhub can execute literally:**
`apt install`, `conda create`, `conda env create`, `conda install`, `conda activate`, `pip install .`, `pip install -r requirements.txt`, `python setup.py install`, `make`, `cmake`, `./configure`, `cargo build --release`, `mkdir`, `cd`, and `&&` chaining between them. See [DOCUMENTED-INSTALLATION.md](DOCUMENTED-INSTALLATION.md) for the complete grammar.

**What cannot be executed automatically (and is reported with the exact line):**
- Prose descriptions ("install the usual dependencies and compile").
- Lists of library names without the `apt install` / `conda` command that installs them.
- Downloads, archive extraction, or custom setup scripts (`wget`, `curl`, `tar`, `bash setup.sh`), pipes, variables, or placeholders like `mytool-X.X.tar.gz`.
- Instructions hosted only on an external wiki or website outside the commit.
- A repository `Dockerfile` (never built as the evaluator container) or repositories requiring git submodules (`.gitmodules`).
- Published packages or images (`pip install mytool`, `conda install -c bioconda mytool`, `docker pull ...`): these test a pre-published artifact rather than the pinned commit, so they are listed as context and not run.

---

### 2. One runnable command

Provide a concrete single-sample command in a code block, without synopsis brackets (`[...]`) or shell variables (`$VAR`). Multi-line commands using `\` or indented option lines are supported.

```bash
# Good: concrete command
mytool --bam sample.bam --fasta hg38.fa --regions panel.bed --out sample.vcf

# Not a runnable command: abstract synopsis
mytool --bam <in.bam> [--regions FILE] [--threads N] ...
```

If your README includes a synopsis for reference, keep it and add one concrete worked example right below it.

---

### 3. Declared input

State in the README what input format (BAM, CRAM, or FASTQ) and sequencing platform (e.g., Illumina, Oxford Nanopore, PacBio) the tool reads.

In the example command, pass the input **file** (not a directory) after a standard flag such as `--bam`, `--bams`, `--reads`, `--fastq`, `--in`, `--input`, `-i`, or `-b`, using a concrete filename or angle-bracket placeholder (`sample.bam`, `path/to/sample.bam`, `<sample.bam>`). Avoid shell variables such as `$BAM`.

- **Reference genome:** If your command reads a reference FASTA, pass it with a standard flag (`--fasta`, `--ref`, `--reference`, `--genome`, `-r`, `-f`, `-g`) and state the assembly (`hg38`/`GRCh38`). STRhub mounts an uncompressed public UCSC `hg38` FASTA with its `.fai` index automatically (`.fa.gz` and `.2bit` are not mounted).
- **Regions / catalog files:** Either ship the file in the commit, or document the exact columns/layout of the regions file in the README so STRhub can mount the matching reference panel BED.
- **Best option: commit a tiny example dataset.** A small test slice of a few megabytes lets any user, reviewer, or editor reproduce your tool in seconds using your own files.

---

### 4. Declared output

State the output file name or extension produced by the command so STRhub can verify that the expected output appeared.

```markdown
Writes `sample.vcf` (or `results/*.tsv`) in the output directory.
```

---

## Copy-and-paste README template

Replace the names and keep this structure:

````markdown
## Installation

```bash
conda env create -f environment.yml
conda activate mytool
pip install .
```

## Example

Reads aligned ONT/Illumina BAM files (`hg38`) and writes `out.vcf`.

```bash
mytool --bam sample.bam --fasta hg38.fa --out out.vcf
```
````

---

## Reading the outcomes

| Outcome | What it means |
|---|---|
| **As documented, it runs.** | The install succeeded, the documented command ran end to end, and the declared output appeared. |
| **As documented, it does not run.** | The procedure was executed without modification and stopped at install or runtime. **This does not mean the tool does not work.** The full log is linked so the failing step can be fixed. |
| **A third party cannot tell how to run it.** | Nothing was executed because one of the four blocks above is missing or outside the automated profile. |
| **STRhub could not attempt the run (our limitation).** | STRhub does not hold a reference sample of that kind or cannot fetch a required feature (e.g., submodules). This is never reported as a fault of your tool. |

---

## Manual verification option

If automated verification is not possible for your repository (for example, legacy documentation, complex setup, or unsupported input layouts), you can request **manual verification by the STRhub team** (response time: **3 to 5 business days**).

---

## Scope

Step 1 evaluates reproducible installation, execution, and output plausibility in a clean environment on one public hg38 reference sample per input type (CODIS and expanded forensic panels). It does **not** evaluate genotype concordance against truth sets, accuracy, or fitness for forensic casework.
