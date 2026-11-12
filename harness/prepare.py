"""Prepare a verify run: read the manifest, resolve the external dataset, and
stage only the shared dataset admitted by the upstream procedure review.

Centralising this in Python (vs bash in the workflow) keeps it testable and
keeps the YAML small. It emits GitHub-Actions `key=value` step outputs, writes
the plan harness/engine runs, and stages the dataset under <work>/in_external.

Usage:
  python harness/prepare.py <tool> --work work --proposal <evidence.json> --plan-out work/plan.json

The descriptor is the one propose_manifest.py wrote to <work>/proposal from the
public repository. Its manifest is checked against pinned upstream evidence
before any Docker step.
"""
from __future__ import annotations
import argparse
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import datasets as datasets_lib  # noqa: E402
import _manifest  # noqa: E402
import _paths  # noqa: E402
import input_provenance  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent

def _check_source(path: pathlib.Path, root: pathlib.Path) -> None:
    _paths.confined(root, str(path.relative_to(root)))
    if path.is_dir():
        for child in path.iterdir():
            _paths.confined(root, str(child.relative_to(root)))
    elif path.name.endswith(".bam"):
        _paths.confined(root, str(_bam_sidecar(path).relative_to(root)))


def _check_dataset(input_type) -> None:
    rec = datasets_lib.load_index().get("datasets", {}).get(input_type)
    if not rec:
        return
    for key in ("data", "bam_index", "supported_loci"):
        if rec.get(key):
            src = _paths.confined(ROOT, rec[key])
            _check_source(src, ROOT)
    if rec.get("canonical_input"):
        # A canonical name is a filename, never a destination directory.
        if len(_paths.relative(rec["canonical_input"]).parts) != 1:
            raise ValueError("canonical_input must be a filename")


def preflight(m: dict, tool_dir: pathlib.Path, work: pathlib.Path) -> None:
    """All runner-side paths are checked before the first staging effect."""
    for name in ("proposal", "in_external", "out_external", "out_example", "ctx"):
        dest = _paths.destination(work, name)
        if dest.is_dir():
            # Includes stale files: staging must not follow a symlink
            # that a previous attempt left at a canonical destination filename.
            for child in dest.rglob("*"):
                _paths.destination(work, str(child.relative_to(work)))
    _paths.confined(tool_dir, m["environment"]["dockerfile"])
    assets = _paths.confined(tool_dir, "assets")
    if assets.is_dir():
        _check_source(assets, tool_dir)
    _check_dataset((m.get("inputs") or {}).get("type"))


def _bam_sidecar(bam: pathlib.Path) -> pathlib.Path:
    """Return the .bai path for a BAM (handles *.codis.bam → *.codis.bam.bai)."""
    return bam.parent / f"{bam.name}.bai"


def example_wrapper(cmd: str, cwd: str) -> str:
    """The README command, wrapped so that whatever it creates ends up under
    /data/out, whatever it was called and wherever it was written.

    A README example writes where it likes (`results/`, the cwd, a path in the
    command); the IO check reads /data/out. Instead of asking the author to
    rewrite their documented command to STRhub's mount, the wrapper marks the
    time, runs the command exactly as documented, and copies every regular file
    created or modified afterwards. The command's own exit status is preserved.
    """
    cmd = cmd.strip()
    return (
        f"cd {cwd!r} && touch /tmp/.strhub_mark && ( {cmd} ); rc=$?; "
        # -xdev: stay on the image's own filesystem. From a WORKDIR of `/`,
        # /proc and /sys are "newer" than the mark by construction, and copying
        # them passed a command that did not even exist; /data/out is a mount
        # too, so the copy never feeds on itself.
        "find . -xdev -type f -newer /tmp/.strhub_mark -size +0 ! -path './.git/*' "
        "! -path './proc/*' ! -path './sys/*' ! -path './dev/*' ! -path './data/*' "
        "! -path '*/__pycache__/*' ! -name '*.pyc' ! -name '*.pyo' "
        "2>/dev/null | head -500 | "
        "while IFS= read -r f; do mkdir -p \"/data/out/$(dirname \"$f\")\" && cp \"$f\" \"/data/out/$f\"; done; "
        "exit $rc"
    )


_WRAPPED = re.compile(r"^cd (?P<cwd>'[^']*'|\S+) && touch /tmp/\.strhub_mark && \( (?P<cmd>.+?) \); rc=\$\?; ", re.S)


def unwrap_example(cmd: str) -> tuple[str, str | None]:
    """The tool's own command back out of `example_wrapper`, with the directory
    it ran from; an unwrapped command comes back as it is, with no directory.

    The report names what the gates ran. The wrapper is STRhub's plumbing
    around that — marking the time, copying files — and a reader shown the
    whole line cannot tell which part is the tool's."""
    m = _WRAPPED.match(cmd)
    if not m:
        return cmd, None
    return m.group("cmd"), m.group("cwd").strip("'")


def _output_value(value) -> str:
    """One $GITHUB_OUTPUT value. Newlines are the delimiter of that file, so a
    manifest value carrying one could inject further keys (external_ready=1, ...)."""
    return str(value if value is not None else "").replace("\r", " ").replace("\n", " ")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("tool")
    ap.add_argument("--work", default="work")
    ap.add_argument("--mode", default="trial", choices=["trial", "publish"],
                    help="stamped into the plan; either way the descriptor is the one read from the repository")
    ap.add_argument("--proposal", default="",
                    help="path to recipe_proposal.json, the reading of the repository this run rests on")
    ap.add_argument("--plan-out", default="",
                    help="also write the step outputs as JSON: the plan harness/engine runs")
    args = ap.parse_args()

    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", args.tool):
        raise ValueError("tool must be a single safe directory name")
    work = pathlib.Path(args.work)
    # The only descriptor there is: the one propose_manifest.py derived from
    # the public repository in this run. No recipe is committed here.
    tool_dir = _paths.destination(work, "proposal")
    mode = args.mode
    mf = _paths.confined(tool_dir, "manifest.yml")
    m = _manifest.load(str(mf))
    preflight(m, tool_dir, work)
    inputs = m.get("inputs", {})
    input_type = inputs.get("type")

    # Recompute the review against the actual manifest. Cached may_say_runs
    # or an origin label is not authorization to build or run a procedure.
    import authorization
    proposal_data = {}
    prop_path = pathlib.Path(args.proposal) if args.proposal else None
    if prop_path and prop_path.is_file():
        try:
            proposal_data = json.loads(prop_path.read_text())
            if not isinstance(proposal_data, dict):
                proposal_data = {}
        except (ValueError, OSError):
            proposal_data = {}
    review = authorization.prepare_review(proposal_data, m, proposal_data.get("limitations") or [],
                                    (m.get("caveats") or {}).get("items") or [])
    procedure_ready = review["may_say_runs"]
    install_ready = review["install_ready"]
    import fidelity
    work.mkdir(parents=True, exist_ok=True)
    review_path = _paths.destination(work, "procedure_review.json")
    review_path.write_text(json.dumps(review, indent=2) + "\n")

    # Only a shared, registered dataset can enter the runtime mount. The
    # repository's own example reads its files at the original paths in the image.
    external_ready = False
    dataset_name = supported_loci = input_failure = ""
    if procedure_ready and input_type:
        try:
            ds = input_provenance.stage(ROOT, work, input_type)
            external_ready = True
            dataset_name = ds["name"]
            supported_loci = ds.get("supported_loci", "")
        except (ValueError, OSError, KeyError) as exc:
            input_failure = f"shared dataset staging could not be verified: {exc}"
            print(f"::error::{input_failure}", file=sys.stderr)
            install_ready = procedure_ready = False

    example_ready = install_ready and procedure_ready and bool(fidelity.example_citation(proposal_data, m))
    example = m.get("example") or {}

    values = {
        "ref": m["source"]["ref"],
        "procedure_ready": "1" if procedure_ready else "0",
        "install_ready": "1" if install_ready else "0",
        "installation_profile": (review.get("installation") or {}).get("profile", ""),
        "example_ready": "1" if example_ready else "0",
        "example_cmd": example_wrapper(example["cmd"], example["cwd"]) if example_ready else "",
        "cmd": m["run"]["cmd"],
        "dockerdir": tool_dir.relative_to(ROOT) if tool_dir.is_relative_to(ROOT) else tool_dir,
        "dockerfile": m["environment"]["dockerfile"],
        # Set when the repository ships its own Dockerfile: the Installs step then
        # clones the repository and builds that file with the clone as context,
        # and the run legs use the image's own entrypoint.
        "dockerfile_from_repo": (m["environment"].get("from_repo") or "") if m["environment"].get("source") == "repository" else "",
        "timeout": min(int(m["run"].get("timeout_minutes", 30)), 120),
        # The step's own ceiling, a little above the run's: harness/run_container.sh
        # enforces `timeout` and writes why into the log; this is only a backstop.
        "step_timeout": min(int(m["run"].get("timeout_minutes", 30)), 120) + 3,
        "manifest": mf,
        "repo": m["source"]["repo"],
        "mode": mode,
        "input_type": input_type or "",
        "external_ready": "1" if external_ready else "0",
        "dataset_name": dataset_name,
        "input_failure": input_failure,
        "supported_loci": supported_loci,
    }
    # Every value is flattened to one line: this goes to $GITHUB_OUTPUT, where a
    # newline starts a new key. Only `cmd` used to be flattened.
    print("\n".join(f"{k}={_output_value(v)}" for k, v in values.items()))
    if args.plan_out:
        # The same values, the same flattening, as one document: what the
        # engine (harness/engine) runs instead of reading them back off
        # $GITHUB_OUTPUT one `steps.m.outputs.*` at a time.
        plan = {"tool": args.tool, **{k: _output_value(v) for k, v in values.items()}}
        out = pathlib.Path(args.plan_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(plan, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
