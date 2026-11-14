# Preparation and strict execution

Decided by the owner on 2026-11-13.

## Two steps, always in this order

1. **The repository as it is.** Its own installation commands, its own
   command, nothing of STRhub's but the sample and the reference genome. If
   that can be run, that is the result, and no preparation is looked at.
2. **Only when step 1 cannot be run: STRhub's preparation**, if one is
   committed under `preparations/` for that repository. The environment is
   then STRhub's. The command is still the README's, at the pinned commit.

A report says which step produced it and, for step 2, why step 1 was not
enough (`preparation.without_preparation`).

## What a preparation may do

What any user has to do before they can run a tool:

- install and compile (shell steps, run in the checkout, in order);
- write the configuration files the README tells the reader to fill in;
- name the registered sample the run reads, and the layout of its loci.

## What it may never do

- carry the command, an option, a flag or an argument: the format has no
  field for one, and a file with any other key does not load;
- change what the documented command does.

Shell steps are free text, so the format cannot enforce the second rule by
itself. A step that edits the tool's source, wraps its executable or changes
its defaults breaks it. That is what the owner's review of each file is for,
and why every step is printed in the report.

## What is replaced in the command

Only input and output paths: the read file (or a documented list of read
files, which the one registered sample stands in for), the reference genome,
and the regions file when the preparation names a layout. Options are never
added, removed or changed. Each replacement is listed in the report
(`procedure_review.command_review.substitutions`).

## What the report says

- The label: "Documented command runs, with STRhub's preparation" or
  "Documented command fails, with STRhub's preparation". Never "as
  documented": the installation was not the README's.
- Under the command that was run: the base, every step, every file written
  (and whether it replaced one the repository ships), the sample and the
  regions layout, and the file the preparation is recorded in.
- Every line of the preparation's `why` as a recommendation to the author.

## The control run

A failure in an environment STRhub prepared could be the preparation's
fault. It is published as a finding about the tool only once a **control
run** exists: the same preparation, with the code corrected, running. Until
then `publish_gate` refuses it. Linking a failure to its control
(`preparation.control`) is not built yet.

## A new tool nobody has prepared

Step 1 answers at once. When it cannot run, the report names what the
README lacks, with a request the reviewer can send to the author. A
preparation is written by hand, later, when STRhub decides to.
