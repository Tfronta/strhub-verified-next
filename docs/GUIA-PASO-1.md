# Step 1: what a commit needs to state so a stranger can run the tool

STRhub Verified tests one thing first, before anything about forensic STR panels:

> At the pinned commit, can a third party install the tool and run it end to end by following
> only what that commit writes, and get the output file the command names?

Nothing is invented to fill a gap. STRhub does not write the install for you, does not add a
flag that your command does not carry, and does not guess a file layout. If a step is missing,
the report says which one, and the run is not attempted. That is why this page exists: it is the
whole contract, and it is four blocks long.

This is not a style guide and it is not a review of your software. A tool can be excellent and
still fail step 1, because step 1 is about the commit, not about the code.

---

## The four blocks

### 1. Installation, copyable

The commands, in a code block, under a heading about installing. STRhub runs them exactly as
written, in order, on a clean Ubuntu 22.04 (with conda, python and pip when a command uses
them), and adds nothing: no package, no option, no missing step.

```bash
# good: plain commands, and every file they name is in the commit
conda env create -f environment.yml
conda activate mytool
pip install .
```

What it can follow: `apt install`, `conda create` / `conda env create` / `conda install` /
`conda activate`, `pip install .` / `pip install -r requirements.txt`, `python setup.py install`,
`make`, `cmake`, `./configure`, `cargo build --release`, `mkdir`, `cd`, and `&&` between them.
The full list is in [DOCUMENTED-INSTALLATION.md](DOCUMENTED-INSTALLATION.md).

What it cannot follow, and reports as missing with the line that stopped it:

- prose that has to be interpreted ("install the usual dependencies and compile");
- a list of library names without the command that installs them: on a clean machine `make`
  has no compiler unless a line installs one;
- a download or an archive to unpack (`wget`, `curl`, `tar`), a script, a pipe, a variable, a
  glob or a placeholder such as `mytool-X.X.tar.gz`;
- a link to an external wiki: the wiki is not in the commit;
- a `Dockerfile`: one shipped in the repository is never built.

A line that installs a published copy (`pip install mytool`, a Bioconda package, a Docker
image) is not the commit under test. It is listed in the report and not run.

### 2. One command

The command for a single sample, in a code block, with no synopsis brackets.

```bash
# good
mytool --bam sample.bam --ref hg38.fa --regions panel.bed --out sample.vcf

# not a command: this is a usage synopsis
mytool --bam <in.bam> [--regions FILE] [--threads N] ...
```

A synopsis is not a command. Dropping the optional arguments to turn it into one is a change to
your procedure, so STRhub will not do it: it reports that no command was found. If your README
has a synopsis for reference, add a worked example line as well.

### 3. The declared input

The file the command names, plus one line saying what kind of file it is (BAM, CRAM, FASTQ,
other). The file is either in the commit or an explicit placeholder: `<sample.bam>`,
`path/to/sample.bam`, `$BAM`.

**The reference genome.** If the command reads one, name it in the command and say which
assembly it is (hg19, hg38, T2T):

```bash
# good: the flag says it is the reference, the name says which one
mytool --bam sample.bam --fasta hg38.fa --out sample.vcf
```

You do not ship the genome and you are not asked to. When the command names a reference after a
flag such as `--fasta`, `--ref`, `--reference` or `--genome`, or names a file called `hg38` or
`GRCh38`, STRhub mounts the public UCSC hg38 FASTA (uncompressed, with its `.fai` index) in its
place and says so in the report. What STRhub cannot stand in for: a compressed (`.fa.gz`) or
`.2bit` reference, another assembly, or a reference passed with no flag under a name that does
not say what it is. Those are reported as a limitation of STRhub's, not as a gap of yours.

**Any other file the command reads** (a regions BED, a catalog, a model, a config): ship it in
the commit, or document the step that fetches it. STRhub does not write or supply one. If it is
missing, the report says which file and the run is not attempted.

**The strongest thing you can do here is commit a small example**, and show a command that
runs on it. A slice of a few megabytes turns step 1 into something any user, reviewer or editor
can reproduce in seconds. When the README has a command whose input files are in the commit,
that command is the result STRhub reports: it runs it as written, on your data, with nothing of
its own. The run on STRhub's reference sample is then a second, separate observation.

### 4. The declared output

The file the command writes, by name.

```markdown
Writes `sample.vcf` in the output directory.
```

If the documentation does not name an output, STRhub has no way to tell your result from any
stray file the run left behind, so it will not claim the output appeared. A directory name plus
the extension is enough (`out/*.vcf`), as long as it is stated.

---

## A section you can copy

Everything above, as one README section. Replace the names; keep the shape.

````markdown
## Installation

```bash
conda env create -f environment.yml
conda activate mytool
pip install .
```

## Example

Reads `example/sample.bam` (BAM, aligned to hg38) and writes `example/out.vcf`.

```bash
mytool --bam example/sample.bam --fasta hg38.fa --out example/out.vcf
```
````

With that section and `example/sample.bam` in the commit, anyone can paste the repository's
link into STRhub Verified and get an answer. If you are submitting a manuscript, run it
yourself first and cite the result's link: your reviewers only have to open it.

## What STRhub does with this

It packages exactly the install you declared into a container and runs exactly the command you
wrote, on the files that command names. Packaging your `Makefile` or your `environment.yml` into
an image is wrapping your own instructions, not a second recipe. Adding a dependency you did not
list, rewriting your build, or swapping your input kind for one we happen to hold would be a
different procedure, and a result from it says nothing about your commit, so it is not published
as one.

Three outcomes, and none of them is a judgement about your software:

| Outcome | What it means |
|---|---|
| **As documented, it runs.** | The install ran, the command finished, and the output file you named appeared. Nothing is claimed about genotype accuracy or fitness for casework. |
| **As documented, it does not run.** | The procedure was executed without amendment and stopped. This does not mean the tool does not work. It means a third party following the README at this commit did not reach the end. The log is linked. |
| **A third party cannot tell how to run it.** | Nothing was executed, because one of the four blocks is missing. The report names the block. |

There is also a fourth case that is **ours, not yours**: STRhub may not hold a sample of the kind
your command reads, or may hold slices of other coordinates. The report says so in those words.
It is a limitation of our reference data and it is never reported as your tool failing.

## Recommendations in the report

Whatever the outcome, the report ends with what the README or the repository could add. They do
not change the result. Typical ones: the repository ships no example data; the README does not
say which reference assembly the command expects; the README does not describe the output.

## Trying again

Fix the block the report names, then submit the link again on the new commit. Verification is
pinned to a commit, so a new attempt is a new commit. There is no form where STRhub writes the
missing piece for you, on purpose: the value of the attestation is that nobody filled the gap.

## What step 1 does not say

It does not say the genotypes are correct, that the tool agrees with capillary electrophoresis,
or that it is fit for casework. Those need a truth set, and phase 1 does not have one. Step 1 is
reproducibility of installation and execution, and the report says so on its first page.

The run on STRhub's data uses one public hg38 reference sample per input type (slices over the
CODIS and expanded panels), mounted read-only, and nothing else beyond the reference genome
described above.
