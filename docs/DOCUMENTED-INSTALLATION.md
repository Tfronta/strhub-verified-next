# Documented installation: profile 1

`strhub-documented-install/1` (`harness/documented_install.py`) installs a
tool by running the install commands its repository documents, unchanged and
in the order written. It is the second installation profile, tried after the
narrower `strhub-source-install/1` (`docs/SOURCE-INSTALLATION.md`). Neither
builds a Dockerfile the repository ships.

## What it reads

Code blocks (fenced, or indented by four spaces) of repository documents at
the pinned commit, under a heading about installing: install, build, compile,
setup, requirements, prerequisites, dependencies, getting started, quick
start. Wikis, truncated trees and documents with HTML comments are not read.

## What a step may be

Each line must be one whole, plain command of this list. Options not shown
here are not admitted.

| Family | Commands |
|---|---|
| apt | `apt update`, `apt install [-y] <packages>` (also `apt-get`) |
| conda | `conda create -n NAME [packages]`, `conda env create -f FILE [-n NAME]`, `conda install [-c CHANNEL] <packages>`, `conda activate NAME` (also `mamba`) |
| pip | `pip install .`, `pip install -e .`, `pip install -r FILE`, `python setup.py install` |
| build | `make [-j N] [install]`, `cmake <args>`, `./configure [--options]`, `cargo build --release` |
| shell | `mkdir [-p] DIR`, `cd DIR`, and `a && b` between admitted commands |

A file or directory a step names must be in the commit.

## What the evaluator does around the steps

It says each of these in the report (`procedure_review.installation`):

- The base is `ubuntu:22.04` with its package lists refreshed and apt set to
  answer yes. Miniforge (conda, python, pip) is added only when a step uses
  conda, pip or python. Nothing else is installed: a README whose `make`
  needs a compiler has to install one.
- A leading `sudo` is dropped: the build runs as root.
- `git clone` of this project and the `cd` into it are dropped: the build
  already stands in a checkout of the pinned commit.
- The steps run in one shell that stops at the first failure, so `cd` and
  `conda activate` carry from one line to the next.
- The conda environment the steps activate last stays active for the
  documented command.

## What makes the plan not ready

Nothing is approximated. The plan is refused, naming the line, when an
install block holds a command outside the list: a shell operator other than
`&&`, a glob, a variable, a placeholder, a download (`wget`, `curl`), an
archive to unpack, a script, a clone of another repository. Also when a step
names a file the commit does not hold, when the repository uses submodules
or ships a `.dockerignore`, and when two installations with the same steps
are documented and STRhub would have to choose.

A block that installs a **published** copy of the tool (PyPI, Bioconda, a
Docker image) is an alternative to building this commit. It is never run; the
plan lists it under `published_alternatives`.

## What a failed build means

The steps are the repository's and nothing was added, so a build that fails
is a finding about the documented installation on a clean Ubuntu 22.04: the
report shows the terminal with the exact error. It is run once.
