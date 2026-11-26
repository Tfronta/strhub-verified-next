"""Walk the ladder once, in order, and write the RunRecord.

The order: Available, Installs, the example leg and its check, the
external leg and its checks, the matrix. Each stage is conditioned on the
ones before it the way the workflow's `if:` lines conditioned the steps; a
stage that does not run is recorded as such, with its reason, never dropped.
"""
from __future__ import annotations

import pathlib

from . import record, stages
from .executor import Executor
from .record import StageResult
from .stages import Ctx

#: What the attestation used to derive from step outcomes: a failure of
#: STRhub's own evidence checks, which must never read as the tool failing.
EVIDENCE_FAILURES = {
    "installs": "the upstream procedure evidence check before Docker",
    "runs_external": "the provenance check of the mounted dataset and reference genome",
}


def _infra_failure(plan: dict, ins: StageResult, ext: StageResult) -> str:
    if plan.get("input_failure"):
        return plan["input_failure"]
    if ins.status == "failed" and ins.outputs.get("source_evidence") != "verified":
        return EVIDENCE_FAILURES["installs"]
    if ext.status == "failed" and ext.outputs.get("input_evidence") != "verified":
        return EVIDENCE_FAILURES["runs_external"]
    return ""


def run(plan: dict, work: pathlib.Path, root: pathlib.Path, exe: Executor | None = None,
        python: str | None = None, results: pathlib.Path | None = None, image: str | None = None,
        container_prefix: str | None = None) -> dict:
    ctx = Ctx(plan=plan, work=pathlib.Path(work), root=pathlib.Path(root), exe=exe or Executor(),
              **({"python": python} if python else {}),
              **({"results": pathlib.Path(results)} if results else {}),
              **({"image": image} if image else {}),
              **({"container_prefix": container_prefix} if container_prefix else {}))
    done: list[StageResult] = []

    def keep(r: StageResult) -> StageResult:
        done.append(r)
        print(f"[engine] {r.stage}: {r.status}" + (f" (exit {r.exit_code})" if r.exit_code is not None else "")
              + (f" — {r.reason}" if r.reason else ""))
        return r

    av = keep(stages.available(ctx))
    ins = keep(stages.installs(ctx, av))
    ex = keep(stages.runs_example(ctx, ins))
    keep(stages.check_example(ctx))
    ext = keep(stages.runs_external(ctx, ins))
    io_stage = keep(stages.check_io(ctx, ext))
    keep(stages.check_content(ctx, ext))
    legs = stages.matrix(ctx)

    # The badge ladder rests on the external leg; a leg whose mount was not
    # verified never ran, and reads as a skipped step, as it did.
    verified = ext.outputs.get("input_evidence") == "verified"
    infra = _infra_failure(ctx.plan, ins, ext)
    ladder = {"leg": "external", "runs": ext.outcome if verified else "skipped",
              "io": ctx.result("io_external.json"), "content": ctx.result("content_external.json"),
              "supported_loci": ctx.plan.get("supported_loci", ""),
              "input_type": ctx.plan.get("input_type", ""), "dataset": ctx.plan.get("dataset_name", "")}

    assisted_record = None
    io_doc = stages._load(ctx.result_abs("io_external.json"))
    io_ok = bool(io_doc.get("passed")) if isinstance(io_doc, dict) else io_stage.passed
    track1_passed = verified and ext.passed and io_ok
    if not infra and av.passed and not track1_passed:
        prop_raw = ctx.plan.get("proposal") or ""
        prop_path = pathlib.Path(prop_raw) if prop_raw else (ctx.root / "recipe_proposal.json")
        if not prop_path.is_absolute():
            prop_path = ctx.root / prop_path
        mf_raw = ctx.plan.get("manifest") or ""
        mf_path = pathlib.Path(mf_raw) if mf_raw else None
        if mf_path is not None and not mf_path.is_absolute():
            mf_path = ctx.root / mf_path
        rev_path = ctx.work_abs / "procedure_review.json"
        if prop_path.is_file() and mf_path is not None and mf_path.is_file() and rev_path.is_file():
            import sys as _sys
            if str(ctx.root / "harness") not in _sys.path:
                _sys.path.insert(0, str(ctx.root / "harness"))
            import _manifest
            import assisted_remediation
            proposal_doc = stages._load(prop_path)
            review_doc = stages._load(rev_path)
            try:
                manifest_doc = _manifest.load(str(mf_path))
            except Exception:  # noqa: BLE001
                manifest_doc = None
            assisted_record = assisted_remediation.execute_assisted_run(
                ctx,
                proposal_doc,
                manifest_doc,
                review_doc,
                available_passed=av.passed,
                installs_passed=ins.passed,
                installs_attempted=ins.status != "not_run",
                runs_passed=bool(verified and ext.passed),
                io_passed=io_ok,
            )

    out_rec = {
        "schema": record.SCHEMA,
        "created": record.now(),
        "tool": ctx.plan.get("tool", ""),
        "mode": ctx.plan.get("mode", ""),
        "image": ctx.image,
        "hardening": list(stages.HARDENING),
        "plan": dict(ctx.plan),
        "stages": [r.to_dict() for r in done],
        # Step outcomes in GitHub's vocabulary, what report.py was handed before.
        "outcomes": {
            "available": av.outcome,
            "installs": ins.outcome,
            "runs_example": ex.outcome,
            "runs_external": ext.outcome,
        },
        "evidence": {
            "source": ins.outputs.get("source_evidence", ""),
            "input": ext.outputs.get("input_evidence", ""),
        },
        "infra_failure": infra,
        "ladder": ladder,
        "environment_built": ins.outputs.get("environment", ""),
        "matrix": legs,
    }
    if assisted_record is not None:
        out_rec["assisted"] = assisted_record
    return out_rec
