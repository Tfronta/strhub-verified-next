"""What the dataset index registers is in the repository, as it says.

Forensic and medical samples, and for each BAM dataset its loci written in
the layout each tool family reads. A regions file is an input a tool's
preparation names; the index only says which exist."""
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
INDEX = json.loads((ROOT / "datasets" / "index.json").read_text())
DATASETS = INDEX["datasets"]
FORMATS = set(INDEX["regions_formats"])


def test_forensic_and_medical_panels_are_both_registered():
    assert {"illumina-bam-hg38", "illumina-bam-hg38-y", "ont-bam-hg38", "pacbio-hifi-bam-hg38",
            "illumina-str-fastq", "ont-fastq"} <= set(DATASETS)
    assert {"illumina-bam-hg38-med", "ont-bam-hg38-med", "pacbio-hifi-bam-hg38-med"} <= set(DATASETS)


@pytest.mark.parametrize("name", sorted(DATASETS))
def test_every_registered_file_is_in_the_repository(name):
    entry = DATASETS[name]
    paths = [entry["data"], entry.get("bam_index"), entry.get("supported_loci"), *(entry.get("regions") or {}).values()]
    for path in filter(None, paths):
        assert (ROOT / path).is_file() and (ROOT / path).stat().st_size > 0, path
    # A name the container sees, never a directory.
    assert "/" not in entry["canonical_input"]


@pytest.mark.parametrize("name", sorted(n for n, e in DATASETS.items() if e.get("regions")))
def test_regions_are_the_dataset_s_own_loci_in_each_known_layout(name):
    entry = DATASETS[name]
    assert set(entry["regions"]) == FORMATS
    panel = sum(1 for line in (ROOT / entry["supported_loci"]).read_text().splitlines()
                if line.strip() and not line.startswith("#"))
    for fmt, path in entry["regions"].items():
        assert path.startswith(f"datasets/{name}/regions/"), path
        text = (ROOT / path).read_text()
        if fmt == "eh_catalog":
            loci = len(json.loads(text))
        else:
            if fmt in ("hipstr", "gangstr"):
                # No comment line: HipSTR and GangSTR reject or misread one.
                assert not text.startswith("#")
            loci = sum(1 for line in text.splitlines() if line.strip() and not line.startswith("#"))
        assert 0 < loci <= panel + 5, (fmt, loci, panel)


def test_hg38_datasets_name_the_reference_they_are_aligned_to():
    for name, entry in DATASETS.items():
        if entry.get("reference") == "hg38":
            genome = entry["reference_genome"]
            assert genome["mount_path"] == "/data/ref/" + genome["filename"] and genome["md5_url"]
