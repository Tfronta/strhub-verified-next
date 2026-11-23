# Recording a Local Manual Verification

When a tool cannot be evaluated automatically (GPU, high RAM, Conda/interactive setup, or upstream script bugs), run it locally against an **unmodified checkout** of the official repository and record the run mechanically with `harness/manual_record.py`.

## Safeguards enforced automatically

1. **Identity check:** `origin` must match `--repo`, `HEAD` must resolve to a full 40-char SHA, and **no tracked file may be modified** (untracked config files required by the README can be whitelisted with `--allow-untracked`).
2. **Privacy hygiene:** runs via subprocess (no interactive shell prompt) and redacts checkout path (`/work`), input/output dirs (`/data/in`, `/data/out`), `$HOME` (`<HOME>`), local username (`<user>`), and computer/host names (`<host>`, including macOS `ComputerName`).
3. **Mechanical gates:** captures verbatim sanitized terminal output, exit code, and validates any VCF/TSV/CSV outputs using `vcf_structure` and `content_auto`.

## 1. Create a short notes YAML file (example)

```yaml
tool_name: STRspy
version: v2.0
base: "Ubuntu 22.04 + Conda (local workstation)"
dataset_type: ont-bam-hg38
dataset_label: "1000 Genomes ONT, hg38 CODIS slice (R10 SUP)"
without_preparation: "README.md instructs downloading a Miniconda shell installer via wget."
failure_summary: "STRspy_run_v2.0_Args.sh checks for STRspy_Normal_v2.0_Args.sh in root instead of src/ and exits 1."
steps:
  - "conda env create -f setup/STRspy_2.0_env.yml"
  - "conda activate strspy_env"
recommendations:
  - "Fix the path checks on lines 180 and 193 of STRspy_run_v2.0_Args.sh to check src/..."
pr_url: "https://github.com/unique379r/strspy/pull/..."
proposed_fix_note: "Minimal fix proposed upstream; official commit remains Manual · Fails until merged."
```

## 2. Record the real local run

```bash
python3 harness/manual_record.py \
  --slug strspy-ont \
  --repo https://github.com/unique379r/strspy \
  --checkout /tmp/upstream-strspy \
  --version v2.0 \
  --cmd "bash ./STRspy_run_v2.0_Args.sh config/InputConfig.txt config/ToolsConfig.txt" \
  --notes /tmp/strspy-notes.yml \
  --out-dir /tmp/bundle-strspy
```

For a tool that **succeeds** and writes VCF/TSV outputs, add `--output-dir /tmp/tool-out` (and optionally `--output-glob "**/*.vcf.gz"` and `--regions-file datasets/.../loci.bed`).

## 3. Review and publish to `gh-pages`

```bash
# Dry-run first (checks schema, terminal file presence, and zero personal leaks)
python3 harness/publish_manual.py --bundle /tmp/bundle-strspy --slug strspy-ont

# Publish to gh-pages (writes strictly under <slug>/<sha>-curated/ without altering the automatic alias)
python3 harness/publish_manual.py --bundle /tmp/bundle-strspy --slug strspy-ont --push
```
