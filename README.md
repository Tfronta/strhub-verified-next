# strhub-verified-next

The STRhub Verified engine, rebuilt clean from the old `strhub-verified` on
2026-11-12. This repository starts from only the modules the old engine's
inventory marked KEEP (`docs/INVENTARIO-2026-11-12.md`), copied as they were
at commit ca612d9 of the old repository, plus the contract with the web
(`docs/WEB-CONTRACT.md`). It is not yet pruned; that is the first job.

## What Verified is

An external auditor. It reads a public repository, checks whether it holds
everything needed to install and run the tool exactly as the author
documents, tries to run it that way, and if anything is missing or fails it
does **not** force it: "could not run" is a result. The report shows the
terminal with the exact error. "Could not run" may mean "badly documented";
then the author is asked, through a GitHub issue draft, to document better
and try again.

## Rules for this repository

1. Nothing in here may force a run: no fallback environments, no recipes
   written by STRhub, no fixes proposed to the author's commands, no
   retries, no regions or reference files the author did not document.
2. The web depends only on what `docs/WEB-CONTRACT.md` says. Change the
   engine and that file in one commit, and the web's fixture test in the
   same step.
3. Dead code is deleted, not kept "just in case". A module nobody invokes
   from `.github/workflows/verify.yml` or from a module that is invoked
   goes.

## Layout

- `harness/engine/` — the gate runner (`python -m harness.engine run`).
- `harness/*.py` — reading the repository, preparing the plan, checking
  outputs, writing the report, publishing.
- `datasets/`, `illumina_slices/`, `ont_slices/`, `pacbio_slices/` — the
  registered public samples the external leg mounts read-only.
- `docs/` — the rules the engine follows, the contract, the inventory, and
  the old engine's README for reference.
