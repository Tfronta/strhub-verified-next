# The contract between strhub-verified and strhub-web

This file is the whole of what the web (`Tfronta/strhub-web`) depends on from
this engine. Nothing else the engine writes is read by the web, and nothing
the web reads is outside this file. **A change to any item below changes
this file in the same commit**, and lands on the web in the same step: a
fresh real artifact goes to `lib/verified/__fixtures__/` there, and its
test (`lib/verified/trial-artifact.test.ts`) says what the web stopped
reading. Fields the engine stops writing are removed from the web's
`types/verified.ts` in that same change, so nothing dead stays readable
by mistake.

What the feature is, in the owner's words: an external auditor. It reads
the public repository, checks whether it holds everything needed to install
and run the tool exactly as the author documents, tries to run it that way,
and if anything is missing or fails it does not force it: "could not run"
is a result. The report shows the terminal with the exact error. "Could
not run" may mean "badly documented"; then the author is asked, through a
GitHub issue draft, to document better and try again.

## 1. Dispatch (web → engine)

One `workflow_dispatch` of `.github/workflows/verify.yml` on `main`
(`VERIFIED_ENGINE_BRANCH` on the web, default `main`), sent by the web's
GitHub App installation (`lib/verified/github.ts::dispatchTrial`). Inputs:

| input | value |
|---|---|
| `tool` | the run's own name, e.g. `trial-hipstr-v0.7`; also the artifact's suffix |
| `repo` | the public repository URL the user typed |
| `ref` | the commit, tag or branch to pin; empty means the default branch |
| `ref_label` | optional, the ref as the user typed it, for the page |
| `dispatch_id` | `tr_<…>`, the web's correlation id |
| `mode` | `trial` (the web never dispatches a publication); `publish` only renames the artifact `attestation-<tool>` and stamps the report |
| `publish` | `false`; only the literal `true` lets a run reach `gh-pages` |

`tool` and `repo` are required and have no default: a dispatch without
either fails in the workflow's first step and says why. These seven are
the only inputs; the workflow has no other trigger.

The run is named `Trial <tool> [<dispatch_id>]` (`run-name` in the
workflow), whatever the mode. GitHub returns no run id for a dispatch, so
the web finds the run by that name (`findRunByDispatchId`). Do not change
the shape of the run name.

## 2. The trial artifact (engine → web)

Uploaded by the workflow's `Upload attestation` step, named
`trial-<tool>`, kept 30 days. Its layout since c485b42:

```
reports/<slug>.json            the report (§3)
reports/<slug>.recipe.json     the manifest and Dockerfile the run used
reports/<slug>.summary.md      the report in prose
reports/<slug>.badge.json      shields.io badge (not read by the web)
reports/<slug>.html            static page of the report
reports/<slug>.pdf             certificate
reports/<slug>.log-<leg>.txt       output of a leg that ran (build, example, external)
reports/<slug>.terminal-<leg>.txt  the same with the exact argv, as record_terminal.sh wrote it
run_record.json                every stage's command, exit status and log path (not read by the web yet)
```

The legs are `build` (the `docker build`), `example` (the README's own
command on the repository's own data) and `external` (the documented
command on the registered dataset). The stages in `run_record.json` are
`available`, `installs`, `runs_example`, `example`, `runs_external`,
`io_external`, `content_external`.

`<slug>` is the report's slug (`report.slug` in the manifest, e.g.
`hipstr`), which is not the run's `tool` name. The web finds the report
first (`reports/<slug>.json`, else `<slug>.json`, else any JSON that is not
`.recipe.json`, `.badge.json` or `run_record.json`) and keys every other
file off the stem it was found under. Before c485b42 the same files sat at
the artifact's root; the web still reads that layout for artifacts within
their 30 days.

A leg that did not run has no log and no terminal. When the review refuses
to run (no proven install procedure, a command that cannot be established
at the pinned commit), the only text is `verdict.reason`.

## 3. The report, `schema: strhub-verified/1`

Written by `harness/report.py`. The web's type is
`types/verified.ts::VerifiedReport`. Fields the web reads, by what they
are for:

**Identity and source**
- `schema`, `generated`, `ci_run`, `mode` (`trial` | `publish`)
- `tool`: `{ name, version?, contact? }`
- `source`: `{ repo, ref, ref_resolved?, committed? }`
- `submission`: `{ by }`
- `instrument`: always `documented` (the repository's own instructions; the
  engine has no other instrument)
- `recipe`: `{ origin: "proposed" }`

**What happened**
- `gates`: `{ available, installs, runs, io, content }`, booleans
- `level`: the furthest gate passed (`none` … `content`)
- `verdict`: `{ code, title, reason, basis?, readme_gaps?, blockers? }`;
  `code` ∈ `runs` | `fails` | `undetermined` | `out_of_scope`;
  `blockers[]` = `{ code, what, ask_owner: { title, body } }` — the issue
  the web drafts for the author. **Never again:** `self_fix`,
  `self_fix_text` (removed in ca612d9).
- `step1`: the documented run as the headline: `{ code, headline, body, missing, missing_text, guide }`
- `environment`: `{ dockerfile?, os?, source? }`. **Never again:**
  `environment.fallback`, `fallback_used` (removed in df57a78).
- `install_detail`: `{ passed?, diagnostics?, faults? }` — why the build failed
- `io_detail`, `content_detail`, `datasets`, `run`: what the run read and wrote
- `diagnostics`: per leg, the errors the tool's own log reported
- `logs`, `terminals`: `{ <leg>: <file name> }`, the files of §2 / §4
- `evidence[]`: `{ claim, kind, path, line?, text?, url }` — where each
  claim was read in the repository, openable at the pinned ref. `claim`
  includes `fallback_environment` (the published image the README names;
  evidence, not a plan B).
- `recommendations[]`: `{ code, text }`, what the README or the repository
  could add, on every report whatever the verdict (never what stopped the
  run: that is `verdict.readme_gaps` and `verdict.blockers`). Codes:
  `example_data`, `reference_assembly`, and the README gap items (`readme`,
  `install`, `command`, `command_input`, `input`, `output`). Absent when
  there is none. **The web does not render it yet.**
- `mounted_inputs`: what the external leg was given, verified before launch:
  `files[]` (the registered dataset under `/data/in`, by sha256) and, only
  when the documented command names a reference genome, `reference`:
  `{ mount_path, index_mount_path, assembly, source_url, sha256, size_bytes,
  transformation }` (the public genome mounted read-only at `/data/ref`).
  The web does not read it yet.
- `upstream`, `procedure_review`, `procedure_validation`,
  `author_known_issues`, `needed_beyond_repo`, `repo_test_data`,
  `caveats`, `scope`, `recipe`, `certificate`
- **Never again:** `manual_verification`, `readme_check`, `regions`,
  `gates.starts`, `record_type`, `evidence_review`, `recipe.workarounds`,
  any `instrument` other than `documented`, and the `own` leg in `datasets`,
  `logs`, `terminals` and `diagnostics` (removed on `prune/clean-engine`).

## 4. Publication (engine → gh-pages → web)

`harness/publish_layout.py` lands a published run at
`<slug>/<sha>/<slug>.{json,html,pdf,badge.json,log-*.txt,terminal-*.txt}`
on `gh-pages`, with the root `<slug>.*` set an alias of the newest commit.
`index.json` at the root (`harness/build_index.py`) is what the web's
catalogue reads (`lib/verified.ts`, raw.githubusercontent on `gh-pages`):
one entry per slug with `slug, name, level, label, verdict, generated,
sha, version, variant, committed, versions[], report, page, …` and per
version `{ sha, instrument, version, variant, committed, generated, level,
label, verdict, errors_reported, ci_run, report, page, pdf?, retired? }`.
Only runs of the repository's own instructions are placed, listed in
`versions[]` or aliased at the root. A report already on `gh-pages` that
the engine did not write (another `instrument`, a `record_type`) is left
where it is; if it is still a root set its entry's `label` reads "Not
verified as documented". **Never again:** `fallback_used`, `own_state`,
`readme_score`, `readme_max`, `record_type`, `evidence_review` on entries
or versions, and version rows under `<slug>/<sha>/curated/`.

## 5. How to change any of this

1. Change the engine and this file in one commit.
2. Run one trial from the web form; download its artifact
   (`gh run download <run> -n trial-<tool>` or the API zip) into
   strhub-web `lib/verified/__fixtures__/` and point the test at it.
3. Change the web's reader and types in the same pull request as the
   fixture, and remove every field the engine no longer writes.
4. Merge the engine first, then the web (the web deploys to production
   from `main`).
