"""Synthetic cited source for tests of decisions after a valid procedure review.

Not an upstream fixture, an execution receipt or a shortcut in production.
Tests use the real reviewer and validator; no STR program is launched.
"""
import copy

import authorization
import fidelity
import prepare

COMMAND = 'tool --reads sample.bam --output result.vcf'
INSTALL_BLOCK = "apt-get update\napt-get install -y make g++\nmake"
MAKEFILE = "all:\n\t$(CXX) main.cpp -o tool\n"


def document(command):
    """A README with the one installation section the source profile admits
    and the command, each on its own cited line."""
    return ("# Tool\n\n## Installation (Ubuntu 22.04)\n\n```sh\n" + INSTALL_BLOCK
            + "\n```\n\n## Usage\n\n```sh\n" + command + "\n```\n")


def line_of(text, command):
    return next(i for i, row in enumerate(text.splitlines(), 1) if row == command)


def context(proposal_fields=None, manifest_fields=None):
    source = {"repo": "https://github.com/example/tool", "ref": "a" * 40}
    doc = document(COMMAND)
    p = {**source, "build": {"method": "make", "file": "Makefile"},
         "commands": [{"cmd": COMMAND, "file": "README.md", "line": line_of(doc, COMMAND), "origin": "readme"}],
         "source_documents": [{"file": "README.md", "origin": "readme", "text": doc}],
         "upstream_files": {"Makefile": MAKEFILE}, "tree_paths": ["Makefile", "README.md"], "tree_truncated": False}
    p.update(copy.deepcopy(proposal_fields or {}))
    m = {"tool": {"name": "Example", "version": "test"}, "source": source,
         "environment": {"source": "documented", "dockerfile": "Dockerfile", "os": ["ubuntu-22.04"]},
         "inputs": {"type": "illumina-bam-hg38"},
         "run": {"cmd": prepare.example_wrapper(fidelity.rewrite(COMMAND, "illumina-bam-hg38")["command"], ".")},
         "outputs": [{"path": "result.vcf", "format": "vcf", "min_records": 1}]}
    m.update(copy.deepcopy(manifest_fields or {}))
    r = authorization.prepare_review(p, m, p.get("limitations", []), [])
    return p, m, r


def decide(gates, diagnostics=None, **kwargs):
    import verdict
    proposal = kwargs.pop("recipe_proposal", None)
    compatibility = kwargs.pop("declared_compatibility", None)
    p, m, reviewed = context(proposal, {"compatibility": compatibility} if compatibility else None)
    return verdict.decide(gates, diagnostics, recipe_proposal=p, manifest=m, procedure=reviewed, **kwargs)


def report(code="runs", repo="https://github.com/example/tool", ref="a" * 40):
    """A freshly synthesized bound report for publication-policy tests."""
    import certificate_text
    import verdict
    source = {"repo": repo, "ref": ref}
    p, m, reviewed = context({**source}, {"source": source})
    gates = {"available": True, "installs": True, "runs": code == "runs", "io": code == "runs", "content": code == "runs"}
    inner, cwd = prepare.unwrap_example(m["run"]["cmd"])
    return {"schema": "strhub-verified/1", "tool": m["tool"], "source": {**source, "ref_resolved": ref},
            "environment": m["environment"], "input_contract": m["inputs"], "gates": gates,
            "instrument": certificate_text.INSTRUMENT, "recipe": {"origin": "proposed"},
            "procedure_review": reviewed,
            "run": {"cmd": inner, "effective_cmd": m["run"]["cmd"], "cwd": cwd,
                    "step_outcome": "success" if gates["runs"] else "failure"},
            "verdict": verdict.decide(gates, procedure=reviewed, manifest=m)}
