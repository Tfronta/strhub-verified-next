# Inventario de STRhub Verified (motor y web), 2026-11-12

Hecho por la sesión "drop-plan-b-and-self-fix" contra la definición de la dueña:
Verified es un auditor externo; lee el repo, intenta correr como está documentado, no fuerza nada;
"no pudo correr" es un resultado; muestra la terminal con el error exacto; pide al autor que
documente mejor (issue) y vuelva a probar. KEEP = necesario para eso. DELETE = capa que fuerza,
escribe recetas, parchea documentación faltante o está muerta. UNSURE = no se decide desde el código.

Chequeos hechos a mano sobre el informe: `app/api/verify/trial/publish` es un stub 410 (la web nunca
publica); `harness/engine/stages.py` monta /data/in y /data/out, nunca /data/ref aunque
`datasets/index.json` declara `reference_genome`; el trial de HipSTR corrió solo la etapa `available`.

Contrato motor↔web: strhub-verified PR 66 (`docs/WEB-CONTRACT.md`). Test con artifacts reales: strhub-web PR 78.

---

## Motor (strhub-verified)

### Workflow y nivel repo
| path | qué hace | veredicto | por qué |
|---|---|---|---|
| `.github/workflows/verify.yml` job `resolve` | pytest, casos BED, selftest del picker, elige tools | KEEP (podar) | Sacar "Shared BED cases" (solo para el BED del owner) |
| verify.yml job `upstream` (`if: schedule`) | Mensual: despacha trials por releases nuevos | DELETE | Muerto: no hay trigger `schedule:`; además auto-inicia corridas |
| verify.yml job `documented` (`if: schedule`) | Refresca tools curados | DELETE | Muerto y sirve a la capa curada |
| verify.yml `verify`: propose / m / repo_read / engine / attest / attach / PDF / summary / upload / deploy | El pipeline | KEEP | Es la definición |
| verify.yml "PR check · no regression" | Falla un PR si baja el nivel publicado | UNSURE | Solo útil con recetas curadas en `tools/` |
| verify.yml "Commit the recipe a published trial ran" | Copia manifest y Dockerfile a `tools/<slug>` y pushea a main | DELETE | Escribe recetas |
| verify.yml "Clear a stale rejection notice" | `git rm state/rejections/...` | DELETE | Flujo de rechazos |
| `.github/workflows/documented-refresh.yml` | Versión manual del job `documented` | DELETE | Capa curada |
| `history-check.yml` + `harness/history_check.py` + `history/strspy-ont.yml` | Re-corre commits históricos | UNSURE | QA del motor, no producto |
| `tools/{expansionhunter-med,mahi-mahi-ont-med,straitrazor,strspy-ont,trgt-hifi-med}` | Recetas commiteadas para modo publish | DELETE | Recetas escritas o curadas por STRhub (las copias "* 2" son duplicados de Finder sin trackear) |
| `state/verified-store.json`, `pending/`, `autoconfig/*.json` | Store de submit y autoconfig | DELETE | Flujos muertos |
| `schema/manifest.schema.json` | Valida manifests | KEEP | Lo usa `_manifest.py` |
| `datasets/index.json` + `datasets/*/` | Registro de datasets | KEEP (podar) | Sacar `regions_library`, entradas `*-med` y `reference_genome` (nunca se monta) |
| `download_medical.sh` | Baja slices médicos | DELETE | Panel médico |
| docs `PLAN-Medical-STR-Panel`, `PLAN-Owner-Provided-BED`, `PLAN-Documented-Is-The-Badge`, `EVIDENCE-REVIEW-2026-11-09`, `docs/evidence-reviews/`, `HIPSTR-HG38-TRIAL-2026-11-10`, `stash-hipstr-assets-superseded.patch` | Planes de capas a sacar | DELETE | Describen lo que se va |
| docs `GUIA-PASO-1`, `NO-ADAPTIVE-RETRIES`, `UPSTREAM-FIDELITY`, `SOURCE-INSTALLATION`, `INPUT-BOUNDARY`, `MANDATORY-PROCEDURE-EVIDENCE`, `VCF-STRUCTURE`, `PLAN-Paso-1`, `PLAN-Unamended-Procedure`, `PLAN-Version-History` | Reglas del motor actual | KEEP | Coinciden con la definición |
| docs `INFORME-AUDITORIA-*`, `SESION-*-handoff`, `PLAN-STRhub-Verified`, `PLAN-Claims-Need-Evidence` | Notas históricas | UNSURE | Archivar |

### `harness/engine/` (runner)
| path | qué hace | veredicto | por qué |
|---|---|---|---|
| `__main__.py`, `__init__.py` | `python -m harness.engine run` | KEEP | Lo invoca verify.yml |
| `runner.py` | Corre las etapas y escribe `run_record.json`, sin reintentos | KEEP | Núcleo |
| `stages.py` `available`, `installs`, `runs_example`, `check_example`, `runs_external`, `check_io` | Ref fijado, un `docker build`, el ejemplo del README, una corrida sobre el dataset, chequeo IO | KEEP | "Correr como está documentado y registrar el fallo" |
| `stages.py` `starts` | Chequeo `--help` | DELETE | Muerto: `prepare.py` siempre pone `starts_cmd: ""` |
| `stages.py` `check_content` + `matrix` | Peldaño content y `matrix.json` | UNSURE | Gate más allá de "corrió y escribió la salida documentada" |
| `executor.py`, `record.py` | Subprocesos; esquema del record | KEEP | Núcleo |

### `harness/*.py`
| path | qué hace | veredicto | por qué |
|---|---|---|---|
| `prepare.py` `main`, `example_wrapper`, `unwrap_example` | Arma `plan.json`, recalcula la revisión, monta el dataset | KEEP | Núcleo |
| `prepare.py` `stage_own`, `stage_regions`, `stage_external`, `_check_regions`, `starts_command`, `is_placeholder_command` | Staging viejo de fixtures, BED y regiones | DELETE | Solo los tests los llaman |
| `_manifest.py`, `_paths.py` | Carga de manifest; confinamiento de paths | KEEP | Núcleo |
| `input_provenance.py` | Monta y verifica por hash el único dataset | KEEP | Núcleo |
| `fidelity.py` | Compara el checkout con el procedimiento citado | KEEP | Hace cumplir "como está documentado" |
| `authorization.py`, `procedure.py` | Recalculan la revisión (`install_ready`, `may_say_runs`) | KEEP | Los necesita `prepare` |
| `source_install.py` | Convierte un bloque literal `apt`/`make` del README en Dockerfile | UNSURE | STRhub escribe un Dockerfile, aunque solo desde la transcripción literal del autor |
| `detect_recipe.py` (1843 líneas) | Lee árbol y README: build, comandos, tipo de input, gaps | KEEP (podar) | Sacar el hook `regions_library` (~l.1776) y la adivinación de kits/catálogo |
| `propose_manifest.py` | De la lectura al manifest y Dockerfile del trial | KEEP (podar) | Sacar `_panel_windows`, lógica de loci/regiones y el docstring de `/data/ref` |
| `datasets.py` | Tipo de input → dataset | KEEP | Lo usan fidelity, propose y prepare |
| `check_example.py`, `check_io.py`, `vcf_structure.py` | ¿Apareció la salida documentada? | KEEP | Núcleo |
| `check_content.py`, `content_auto.py` | Peldaño content contra el panel | UNSURE | Peldaño extra |
| `check_starts.py` | Juicio del `--help` | DELETE | Muerto |
| `check_readme.py` | Checklist consultivo del README | DELETE | Nunca corre; nada produce `readme_result.json` |
| `diagnose_log.py` | Patrones de error en los logs | KEEP (podar) | `manual_eligibility()` (l.749) es DELETE |
| `record_terminal.sh`, `run_container.sh` | argv exacto y transcripción; `docker run` endurecido | KEEP | "La terminal con el error exacto" |
| `report.py` | Arma `reports/<slug>.json`, badge y resumen | KEEP (podar) | Inputs muertos: `--readme`, `--regions-source`, `--bed-validation`, `--log-own`, `--starts`. `CURATED_NEEDED` y `manual_verification` son DELETE |
| `verdict.py` | Cuatro veredictos; blockers con `ask_owner` | KEEP | Sacar el argumento `manual_verification` |
| `certificate_text.py`, `claims.py`, `command_record.py` | Frases del certificado; claims; presentación del comando | KEEP (podar) | Sacar ramas curated/maintainer |
| `generate_pdf.py` | PDF | UNSURE | Segundo render del reporte |
| `attach_recipe.py` | Pone `recipe.json` en el artifact | KEEP | La web lo lee |
| `publish_gate.py`, `publish_layout.py`, `build_index.py`, `upstream.py` | Publicación, gh-pages, `index.json` | KEEP | Catálogo |
| `pick_tools.py` | Elige tools para dispatch/PR/schedule | UNSURE | Solo mientras existan `tools/` y modo publish |
| `local_trial.py` | Corre el motor local; la web dev lo usa | UNSURE | Herramienta de desarrollo |
| `trial_fixtures.py`, `snapshot_repo.py`, `benchmark_recipes.py`, `benchmark_trials.py` | Fixtures, snapshots, benchmark | UNSURE | Tooling de test |
| `assist.py`, `assist_report.py` | Agente de recetas retirado | DELETE | Self-fix retirado |
| `regions_library.py`, `build_regions_library.py`, `build_strsearch_bed.py` | Regiones escritas por STRhub | DELETE | Parchea documentación faltante |
| `validate_bed.py`, `test_validate_bed.py`, `rejection.py` | BED del owner; rechazos | DELETE | Nada produce sus salidas |
| `build_medical_candidates.py` | Panel médico desde STRchive | DELETE | Panel médico |
| `build_panel.py` | Genera `datasets/*/loci.bed` | UNSURE | Depende del gate content |
| `documented_refresh.py` | Despacha trials de tools curados | DELETE | Capa curada |
| `upstream_refresh.py` | Despacha trials por releases | DELETE / UNSURE | Nunca corre |
| `migrate_layout.py` | Migración única de gh-pages | DELETE | Ya corrió |
| `publication_review.py` | Retiros editoriales a mano (`record_type: editorial_review`) | DELETE | Reviews escritas a mano |
| `preview_server.py` | Página local de clasificación | DELETE | Solo dev |
| `harness/tests/` (49 archivos) | Tests | KEEP / podar | Borrar los de módulos borrados |

## Web (strhub-web)

### `app/api/verify/`
| path | qué hace | veredicto | por qué |
|---|---|---|---|
| `trial/route.ts` | POST despacha; GET sondea y lee el artifact | KEEP | Núcleo |
| `trial/file/route.ts` | Sirve PDF, HTML, logs y terminales | KEEP | Núcleo |
| `resolve-ref/route.ts` | Resuelve el commit antes del dispatch | KEEP | Núcleo |
| `submit`, `approve`, `autoconfig`, `repo-context`, `trial/publish` | Stubs 410 (`retired-recipe-route.ts`) | DELETE | Muertos |
| `status/route.ts` | Sondea ids `sv_` y el aviso de rechazo | DELETE | Flujo retirado; los trials usan `tr_` |
| `reject`, `submissions`, `test-email` | Cola admin; email | DELETE | Flujo retirado |

### `app/verified/`
| path | qué hace | veredicto | por qué |
|---|---|---|---|
| `page.tsx`, `[slug]/page.tsx`, `layout.tsx`, `trial/[id]/page.tsx`, `submit/page.tsx`, `review/page.tsx` | Catálogo, detalle, trial, formulario | KEEP | Núcleo |
| `how-to-read/page.tsx` | Explicador | UNSURE | No está en la definición |
| `check/page.tsx` | Clasificador de logs "¿es mi setup o la herramienta?" | DELETE | Feature extra |
| `manual/page.tsx` | Pedido de verificación manual | DELETE | Verificación manual |
| `submit/advanced/page.tsx` | Redirect | DELETE | Muerto |

### `components/verified/`
| path | qué hace | veredicto | por qué |
|---|---|---|---|
| `verified-start.tsx` | Formulario repo+ref y la caja `readmeTips` | KEEP | Formulario y la ventanita "qué necesita Verified" |
| `verified-trial.tsx` | Sondea y dibuja un trial; botón de issue | KEEP | Núcleo |
| `verified-list.tsx`, `verified-detail.tsx` | Catálogo; reporte publicado | KEEP (podar) | Sacar ramas `editorial_review` y agrupado médico |
| `verified-check.tsx`, `verified-manual-request.tsx` | Clasificador; pedido manual | DELETE | Extra; manual |
| `verified-how-to-read.tsx` | Explicador | UNSURE | |
| `issue-draft-dialog.tsx` | Redactor de issues, solo admin | UNSURE | Duplica `trial-next-steps.ownerIssueUrl` |
| `report/verified-report-body`, `cover`, `source-card`, `certificate`, `gates`, `terminal`, `output`, `verdict` | Layout; terminal exacta; veredicto | KEEP | Núcleo |
| `report/findings.tsx` | `BuildFailedCard` y `AutoDiagnostics` KEEP; `ManualOffer` y `ReadmeCheck` DELETE; `AuthorKnownIssues`, `EvidenceList` UNSURE | KEEP (podar) | |
| `report/instrument.tsx` | Qué cambió STRhub en recetas curadas | DELETE | Capa curada |
| `report/history.tsx` | Historial | KEEP (podar) | Sacar plegado curated |
| `report/verification.tsx` | Claims + matriz de piernas | KEEP (podar) | Sacar la pierna `own` (l.80) |
| `report/closing.tsx` | `ScopeBlock` KEEP; `DisputeCard` y contacto DELETE | KEEP (podar) | Disputas |
| `report/editorial-review.tsx` | Reviews a mano | DELETE | |
| `report/header.tsx` | `ReportHeader` | DELETE | No se importa en ningún lado |

### `lib/verified/` y `types/verified.ts`
| path | qué hace | veredicto | por qué |
|---|---|---|---|
| `github.ts` | Token de la App, `dispatchTrial` (siempre `publish:"false"`), artifacts | KEEP (podar) | Sacar `putFile`, `deleteFile`, `listDirectory`, `pathExists` |
| `trial.ts`, `trial-artifact.ts`, `log-files.ts`, `repo-url.ts`, `step1.ts`, `trial-next-steps.ts` | Ciclo del trial, parser, nombres de logs, Step 1, issue | KEEP | En `log-files.ts` sacar piernas `own` y `starts` |
| `badge.ts`, `gate-state.ts`, `diagnostics.ts`, `certificate.ts`, `format-date.ts`, `output-evidence.ts`, `dataset-provenance.ts` | Helpers de display | KEEP (podar) | Sacar ramas médicas y curated |
| `history.ts`, `instrument.ts` | Historial; instrumentos documented/maintainer/curated | KEEP (podar) | Sacar `curatedNoteOf`, `foldStrhubRuns`, instrumento `curated` |
| `extra-gates.ts` | Filas starts y example | UNSURE | example sí; starts muerto |
| `submission.ts` (640 líneas) | Schema zod del submit viejo | DELETE (dejar 2 exports) | Solo se importan `SHA_OR_TAG` y `githubRepoUrl` |
| `store.ts` | Store de submissions | DELETE (dejar `normalizeRepo`) | Flujo retirado |
| `rejection.ts`, `dispute.ts`, `manual.ts`, `contact.ts` | Rechazos, disputas, manual, contacto | DELETE (`contact.ts` UNSURE: lo usan about/privacy/api/contact) | |
| `validate-regions.ts`, `regions-format.ts`, `bed-cases.json`, `input-path-cases.json`, `detect-output.ts`, `medical-panel.ts` | BED del owner, detección de salida vieja, loci médicos | DELETE | Solo tests los importan |
| `log-kinds.ts` | Clasificador de logs | DELETE | Solo `verified-check.tsx` |
| `issue-draft.ts` | Redactor rico de issues (con workarounds curated) | UNSURE | Solo admin |
| `retired-recipe-route.ts` | 410 | DELETE | |
| `lib/verified.ts` | `index.json` y reportes desde gh-pages | KEEP | Catálogo |
| `types/verified.ts` | Tipos | KEEP (podar) | Sacar `VerifiedWorkaround`, `ManualBasis`, `VerifiedManualVerification`, `VerifiedEvidenceReview`, `VerifiedEditorialNotice`, instrumento `curated`, pierna `own` |

## Qué corre hoy verify.yml, en orden
`resolve`: pytest harness/tests; test_validate_bed.py; pick_tools --selftest; pick_tools.
`verify`: (trial) detect_recipe → propose_manifest; prepare.py (authorization, procedure, fidelity, input_provenance, datasets); (no trial) detect_recipe → repo_read.json; `python -m harness.engine run` (available → installs [clone, _paths, fidelity, record_terminal.sh docker build] → starts [siempre not run] → runs_example [run_container.sh] → check_example → runs_external [input_provenance, run_container.sh] → check_io [vcf_structure] → check_content [content_auto] → matrix.json); report.py (diagnose_log, verdict, certificate_text, upstream, authorization, command_record); publish_gate; (trial) attach_recipe; generate_pdf; upload (reports/ + run_record.json); deploy solo en main (publish_layout, build_index); commit de receta a tools/ y limpieza de rechazos.

## Defectos encontrados
- **El tool por defecto no existe**: `strait-razor-powerseq` vs `tools/straitrazor`. Un dispatch sin tool falla en `prepare`.
- **La web nunca publica**: siempre manda `publish:"false"` y `trial/publish` devuelve 410. Una corrida desde el formulario jamás llega a gh-pages.
- **No se monta genoma de referencia**: `datasets/index.json` declara `/data/ref/hg38.fa` pero `stages._run_leg` solo monta `/data/in` y `/data/out`. Un comando documentado que necesita `hg38.fa` no lo encuentra: hueco de STRhub, no de la herramienta.
- **Ningún `regions.bed` llega al mount**: `verify()` rechaza cualquier archivo que no sea del dataset.

## Datasets que monta el motor
`/data/in` (solo lectura, pierna external): los archivos registrados en `datasets/index.json`, copiados con nombre canónico y sha256 verificado. BAM: `illumina_slices/NA12878.autosomal.bam`, `NA12878.medical.bam`, `HG002.ystr.bam`, `ont_slices/HG00113.codis.bam`/`.medical.bam`, `pacbio_slices/HG002.hifi.codis.bam`/`.medical.bam`; `ont-fastq` → `HG00113.codis.panel.fastq.gz`; `illumina-str-fastq` → `sample.fastq`. `/data/out` (escritura) para ambas piernas. Hardening: `--network none`, 6g, 2 CPUs, 512 procesos, `--cap-drop ALL`, `no-new-privileges`.

## Lecturas de la web de campos que el motor ya no escribe o nunca llena
`manual_verification` (ambos lados a borrar); `readme_check` (siempre null); pierna `own` en datasets/LOG_LEGS (el motor emite solo external y example); `gates.starts` (nunca); `regions.source` (nunca); `recipe.workarounds` (solo manifests curados commiteados); `record_type: editorial_review` / `evidence_review` (solo `publication_review.py` a mano); `/api/verify/status` lee `state/rejections/` que nada escribe.
