"""STRhub's preparation: what it takes to get a tool ready to be run.

Installing, compiling and filling in the configuration files a README tells
its reader to fill in is what any user does before they can run a tool. When
a repository's own instructions are not enough for the evaluator to do that
literally, STRhub may do it, once, by hand, in a file committed under
`preparations/` and reviewed by its owner. The engine only replays that file.

What a preparation is not allowed to be is the run. It has no field for a
command, an option or an argument: the command is always read from the
repository's README at the pinned commit, and the only things replaced in it
are input and output paths (the registered sample, the reference genome, the
registered regions file). A file with any other key does not load.

Everything in it is shown in the report, under the command that was run, and
every line of `why` is a recommendation to the tool's author.

    schema: strhub-verified/preparation/1
    repo: https://github.com/owner/tool
    dataset: illumina-bam-hg38        # which registered sample the run reads
    regions: hipstr                   # optional: which layout of its loci
    environment:
      conda: false                    # true adds Miniforge to the base
      activate: null                  # optional: conda environment left active
      steps:                          # shell lines, run in the checkout, in order
        - apt-get install -y make g++
        - make
    files:                            # optional: files the README says to fill in
      - path: config/input.txt
        content: |
          ...
    why:                              # what the README does not say
      - The README lists zlib as a requirement and gives no command that installs it.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re

import yaml

import _paths
import documented_install

ROOT = pathlib.Path(__file__).resolve().parent.parent
FOLDER = "preparations"
SCHEMA = "strhub-verified/preparation/1"
PROFILE = "strhub-prepared-environment/1"
ENVIRONMENT = {"source": "prepared", "dockerfile": "Dockerfile", "os": ["ubuntu-22.04"]}
REGION_FORMATS = ["hipstr", "gangstr", "strsearch", "bed4", "motif", "eh_catalog", "trgt"]

#: The whole of what a preparation may say. No key here can carry a command
#: line or an option for the tool, and nothing outside it is accepted.
FILE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["schema", "repo", "dataset", "environment", "why"],
    "properties": {
        "schema": {"const": SCHEMA},
        "repo": {"type": "string", "pattern": r"^https://github\.com/[\w.-]+/[\w.-]+$"},
        "dataset": {"type": "string", "pattern": r"^[a-z0-9][a-z0-9-]*$"},
        "regions": {"enum": REGION_FORMATS},
        "environment": {
            "type": "object", "additionalProperties": False, "required": ["steps"],
            "properties": {
                "conda": {"type": "boolean"},
                "activate": {"type": ["string", "null"], "pattern": r"^[\w.-]+$"},
                "steps": {"type": "array", "minItems": 1, "items": {"type": "string", "minLength": 1}},
            },
        },
        "files": {
            "type": "array",
            "items": {"type": "object", "additionalProperties": False, "required": ["path", "content"],
                      "properties": {"path": {"type": "string", "minLength": 1}, "content": {"type": "string"}}},
        },
        "why": {"type": "array", "minItems": 1, "items": {"type": "string", "minLength": 1, "maxLength": 400}},
    },
}


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _slug(repo: str) -> str:
    match = re.fullmatch(r"https://github\.com/([\w.-]+/[\w.-]+?)(?:\.git)?/?", str(repo or "").strip())
    return match[1].lower() if match else ""


def load(path: pathlib.Path) -> dict:
    """A preparation file, validated. Raises ValueError on anything else."""
    import jsonschema
    try:
        data = yaml.safe_load(pathlib.Path(path).read_text())
        jsonschema.validate(data, FILE_SCHEMA)
    except (OSError, yaml.YAMLError, jsonschema.ValidationError) as exc:
        raise ValueError(f"{path}: not a preparation ({str(exc).splitlines()[0]})") from exc
    for step in data["environment"]["steps"]:
        if "\n" in step or "\r" in step:
            raise ValueError(f"{path}: a step is one line")
    for item in data.get("files") or []:
        if len(_paths.relative(item["path"]).parts) < 1:
            raise ValueError(f"{path}: a file needs a path inside the repository")
    return data


def find(repo: str, root: pathlib.Path | None = None) -> tuple[str, dict] | None:
    """The preparation committed for `repo`: (its path in this repository, its
    content), or None. Two files for one repository are refused, not ranked."""
    root = pathlib.Path(root or ROOT)
    want = _slug(repo)
    found = []
    for path in sorted((root / FOLDER).glob("*.yml")):
        data = load(path)
        if want and _slug(data["repo"]) == want:
            found.append((path.relative_to(root).as_posix(), data))
    if len(found) > 1:
        raise ValueError(f"more than one preparation for {repo}: " + ", ".join(p for p, _ in found))
    return found[0] if found else None


def carrier(prep: dict) -> str:
    """The evaluator's envelope: its declared base, the checkout, the steps in
    one shell that stops at the first failure, then the files."""
    env = prep["environment"]
    lines = ["# Evaluator carrier: strhub-prepared-environment/1; written by STRhub, not an upstream Dockerfile."]
    lines += documented_install.base_lines(bool(env.get("conda")))
    lines += ['COPY [".", "/opt/tool"]', "WORKDIR /opt/tool"]
    lines.append("RUN " + json.dumps(["bash", "-lc", "set -eo pipefail\n" + "\n".join(env["steps"]) + "\n"]))
    for item in prep.get("files") or []:
        # The content travels as an argument, so nothing in it is read by a shell.
        lines.append("RUN " + json.dumps(["bash", "-c", 'mkdir -p "$(dirname "$1")" && printf %s "$2" > "$1"',
                                           "write", item["path"], item["content"]]))
    if env.get("activate"):
        lines.append("RUN " + json.dumps(["bash", "-c",
                                           f"echo 'conda activate {env['activate']}' > /etc/profile.d/zz-strhub-env.sh"]))
    lines.append('ENTRYPOINT ["/bin/bash", "-lc"]')
    return "\n".join(lines) + "\n"


def discover(proposal: dict, root: pathlib.Path | None = None) -> dict:
    result = {"profile": PROFILE, "ready": False, "method": (proposal.get("build") or {}).get("method", "unknown"),
              "reason": "STRhub has not prepared an environment for this repository.", "gap": "strhub"}
    repo, ref = proposal.get("repo"), str(proposal.get("ref") or "")
    if not _slug(repo) or not re.fullmatch(r"[0-9a-f]{40}", ref):
        return result
    try:
        found = find(repo, root)
    except ValueError as exc:
        result["reason"] = f"STRhub's preparation for this repository does not load: {exc}"
        return result
    if not found:
        return result
    path, prep = found
    tree = set(proposal.get("tree_paths") or [])
    dockerfile = carrier(prep)
    env = prep["environment"]
    result.pop("gap")
    result.update(
        ready=True, repo=repo, ref=ref, file=path, preparation_sha256=digest(json.dumps(prep, sort_keys=True)),
        dataset=prep["dataset"], regions=prep.get("regions"),
        steps=list(env["steps"]), conda_environment=env.get("activate"),
        # Whether each file replaces one the repository ships (a configuration
        # the README says to edit) or is new: a reader needs to know which.
        files=[{"path": f["path"], "sha256": digest(f["content"]), "bytes": len(f["content"].encode("utf-8")),
                "replaces": f["path"] in tree} for f in prep.get("files") or []],
        why=list(prep["why"]),
        base_condition={"image": documented_install.BASE_IMAGE,
                        "description": documented_install.BASE_CONDA if env.get("conda") else documented_install.BASE_PLAIN,
                        "role": "evaluator base environment"},
        carrier_dockerfile=dockerfile, carrier_sha256=digest(dockerfile),
        reason="STRhub prepared the environment by hand, in a committed file; the command is the repository's own.")
    return result


def installation(proposal: dict, manifest: dict) -> dict:
    result = discover(proposal)
    if manifest.get("environment") != ENVIRONMENT or manifest.get("source") != {
            "repo": proposal.get("repo"), "ref": proposal.get("ref")}:
        return {"profile": PROFILE, "ready": False, "method": result.get("method", "unknown"), "gap": "strhub",
                "reason": "The effective manifest does not match STRhub's preparation for this repository."}
    if result.get("ready") and ((manifest.get("inputs") or {}).get("type") != result["dataset"]
                                 or (manifest.get("inputs") or {}).get("regions") != result["regions"]):
        return {"profile": PROFILE, "ready": False, "method": result.get("method", "unknown"), "gap": "strhub",
                "reason": "The effective manifest reads other inputs than STRhub's preparation names."}
    return result


def verify_checkout(root, install: dict) -> None:
    """The preparation on disk is still the one that was reviewed, and the
    checkout is the commit it was applied to."""
    if not install.get("ready") or install.get("profile") != PROFILE:
        raise ValueError("no prepared environment")
    root = pathlib.Path(root)
    tree = sorted(p.relative_to(root).as_posix() for p in root.rglob("*")
                  if ".git" not in p.relative_to(root).parts and (p.is_file() or p.is_symlink()))
    again = discover({"repo": install.get("repo"), "ref": install.get("ref"),
                      "build": {"method": install.get("method")}, "tree_paths": tree})
    if again != install:
        raise ValueError("STRhub's preparation does not match the one that was reviewed")


def materialise(root, install: dict, destination) -> None:
    verify_checkout(root, install)
    with destination.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(install["carrier_dockerfile"])
    if hashlib.sha256(destination.read_bytes()).hexdigest() != install["carrier_sha256"]:
        raise ValueError("prepared environment carrier digest mismatch")
