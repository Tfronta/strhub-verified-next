# strhub-verified-next

The STRhub Verified engine, rebuilt clean from the old `strhub-verified` on
2026-11-12. This repository starts from only the modules the old engine's
inventory marked KEEP (`docs/INVENTARIO-2026-11-12.md`), copied as they were
at commit ca612d9 of the old repository, plus the contract with the web
(`docs/WEB-CONTRACT.md`). It was then pruned to what the definition below
needs (branch `prune/clean-engine`).

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
   A reference genome the author's command names is the one exception to
   "STRhub supplies only the sample": it is a public, standard file no
   repository ships, so STRhub mounts it read-only and says so in the report.
2. The web depends only on what `docs/WEB-CONTRACT.md` says. Change the
   engine and that file in one commit, and the web's fixture test in the
   same step.
3. Dead code is deleted, not kept "just in case". A module nobody invokes
   from `.github/workflows/verify.yml` or from a module that is invoked
   goes.

## Layout

- `.github/workflows/verify.yml` — the one workflow: a `workflow_dispatch`
  that runs the commands below and uploads the artifact the web reads. Two
  jobs: `verify` executes the author's code and can only read; `publish`
  can write to `gh-pages` and executes nothing of the author's.
- `harness/engine/` — the gate runner (`python -m harness.engine run`).
- `harness/*.py` — reading the repository, preparing the plan, checking
  outputs, writing the report, publishing.
- `datasets/`, `illumina_slices/`, `ont_slices/`, `pacbio_slices/` — the
  registered public samples the external leg mounts read-only.
- `docs/` — the rules the engine follows, the contract, the inventory, and
  the old engine's README for reference.

## Cómo correr un trial a mano

Estos son los comandos que ejecuta `.github/workflows/verify.yml`, en el
mismo orden. Hacen falta Python 3.11 o posterior, git y, para que las
compuertas Installs y Runs corran de verdad, Docker. Todo se ejecuta desde
la raíz del repositorio, sobre un checkout limpio (el dataset se verifica
contra el commit de este repositorio).

```bash
pip install pyyaml jsonschema pytest reportlab pillow
```

```bash
python -m pytest harness/tests -q
```

El nombre de la corrida, el repositorio público y el commit o tag a fijar
(los inputs `tool`, `repo`, `ref` y `ref_label` del dispatch):

```bash
export TOOL=trial-hipstr-v0.7 REPO=https://github.com/tfwillems/HipSTR REF=b2033bfbb5cf55496b776463bdf2993fa763a4be REF_LABEL=v0.7 MODE=trial
```

1. Leer el repositorio en ese commit y escribir el descriptor de la corrida
   (`work/proposal/manifest.yml` y `Dockerfile`). `GH_TOKEN` es opcional y
   solo sube el límite de la API de GitHub.

```bash
mkdir -p work && python harness/detect_recipe.py "$REPO" "$REF" --tag "$REF_LABEL" --json recipe_proposal.json
```

```bash
python harness/propose_manifest.py recipe_proposal.json --slug "$TOOL" --ref-label "$REF_LABEL" --out-dir work/proposal
```

2. Recalcular la revisión del procedimiento, montar el único dataset
   registrado y escribir el plan (`work/plan.json`).

```bash
python harness/prepare.py "$TOOL" --work work --mode "$MODE" --proposal recipe_proposal.json --plan-out work/plan.json
```

   Si el comando documentado nombra un genoma de referencia, `prepare.py`
   imprime `reference_ready=1` con `ref_genome_url`, `ref_genome_md5_url` y
   `ref_genome_filename`. Solo en ese caso el workflow lo descarga a
   `work/ref/`, lo coteja con el checksum que publica UCSC, lo indexa y lo
   deja en caché (son unos 3 GB descomprimido; hace falta `samtools`):

```bash
mkdir -p work/ref && curl -fsSL -o work/ref/hg38.fa.gz https://hgdownload.soe.ucsc.edu/goldenPath/hg38/bigZips/hg38.fa.gz
```

```bash
echo "$(curl -fsSL https://hgdownload.soe.ucsc.edu/goldenPath/hg38/bigZips/md5sum.txt | awk '$2 == "hg38.fa.gz" {print $1}')  work/ref/hg38.fa.gz" | md5sum -c -
```

```bash
gunzip work/ref/hg38.fa.gz && samtools faidx work/ref/hg38.fa
```

3. Las compuertas: Available, Installs, el ejemplo del README, la corrida
   sobre el dataset y sus chequeos. Sale con 0 aunque una compuerta falle:
   el fallo es un resultado y queda en `run_record.json` con el comando
   exacto, el código de salida y el log.

```bash
python -m harness.engine run --plan work/plan.json --work work --record run_record.json
```

4. El reporte (`reports/<slug>.json`, el badge, el resumen, el HTML, los
   logs y las terminales). `<slug>` es el del reporte (por ejemplo
   `hipstr`), no el nombre de la corrida.

```bash
python harness/report.py --manifest work/proposal/manifest.yml --engine-record run_record.json --procedure-review work/procedure_review.json --mounted-inputs work/mounted_inputs.json --matrix matrix.json --example example.json --log-build work/log_build.txt --log-example work/log_example.txt --log-external work/log_external.txt --recipe-proposal recipe_proposal.json --ref "$REF" --check-upstream --mode "$MODE" --infra-failure "" --run-url ""
```

   En el workflow `--ref` es el `ref` que imprimió `prepare.py` (el del
   manifest), `--infra-failure` nombra el paso de STRhub que falló cuando
   hubo uno y `--run-url` es la URL de la corrida.

5. Decidir si se publica. Solo `PUBLISH=true` lo permite, y aun así la
   compuerta exige un veredicto atribuible y que la tarjeta sea del mismo
   repositorio. `published_index.json` es el `index.json` de gh-pages; si
   no se pudo leer, no se publica.

```bash
PUBLISH=false python harness/publish_gate.py --report reports/hipstr.json --slug hipstr --index published_index.json
```

6. Adjuntar el manifest y el Dockerfile que usó la corrida, y generar el PDF.

```bash
python harness/attach_recipe.py "$TOOL" --dockerdir work/proposal --proposal recipe_proposal.json --procedure-review work/procedure_review.json --source-install-dockerfile work/source-install.Dockerfile
```

```bash
python harness/generate_pdf.py --manifest work/proposal/manifest.yml --publishable false
```

7. El artifact que sube el workflow es `reports/` más `run_record.json`,
   con nombre `trial-<tool>` (o `attestation-<tool>` si `mode` es
   `publish`). Su forma está en `docs/WEB-CONTRACT.md`.

8. Solo en `main`, solo si el dispatch pidió `publish: true` y solo si la
   compuerta dijo `publishable=true`, un **segundo job** (`publish`) baja el
   artifact, vuelve a correr la compuerta, coloca el reporte en un clon de
   `gh-pages` y regenera el índice. Los pasos 1 a 7 corren en el job
   `verify`, cuyo token solo puede leer este repositorio: es el que ejecuta
   código del autor (su Dockerfile, su Makefile, la herramienta). `publish`
   es el único con permiso de escritura y no ejecuta nada del autor.

```bash
python harness/publish_layout.py <clon-de-gh-pages> --reports reports --slug hipstr
```

```bash
python harness/build_index.py <clon-de-gh-pages> --out <clon-de-gh-pages>/index.html
```

Los pasos 1 a 7 dejan archivos en la raíz (`work/`, `reports/`,
`recipe_proposal.json`, `run_record.json`, `matrix.json`, `example.json`,
`io_external.json`, `content_external.json`); conviene correrlos en un
clon aparte. `harness/local_trial.py` hace lo mismo en un directorio
temporal para el desarrollo de la web.
