import pathlib
import subprocess


HARNESS = pathlib.Path(__file__).resolve().parents[1]


def test_transcript_contains_the_launch_and_unmodified_output(tmp_path):
    output_log = tmp_path / "log.txt"
    program = tmp_path / "probe.sh"
    program.write_text('printf "received: <%s>\\n" "$1"\nprintf "error: line 2\\n" >&2\nexit 17\n')

    result = subprocess.run(
        ["bash", str(HARNESS / "record_terminal.sh"), str(output_log),
         "bash", "probe.sh", "reads one.bam"],
        cwd=tmp_path, capture_output=True,
    )

    expected_output = b"received: <reads one.bam>\nerror: line 2\n"
    assert result.returncode == 17
    assert result.stdout == output_log.read_bytes() == expected_output
    assert (tmp_path / "log.txt.terminal").read_bytes() == (
        b"$ bash probe.sh reads\\ one.bam\n" + expected_output + b"\n[exit 17]\n"
    )


def test_run_container_enforces_out_dir_disk_quota_watchdog(tmp_path):
    """If a container writes more than STRHUB_MAX_OUT_KB into /data/out,
    run_container.sh terminates it and logs 'Disk quota exceeded' (exit 125)."""
    import os

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    out_dir = tmp_path / "out_external"
    out_dir.mkdir()
    log_file = tmp_path / "log_external.txt"

    # Fake `docker` CLI simulating a container writing 64 KiB into /data/out then sleeping.
    docker_shim = bin_dir / "docker"
    docker_shim.write_text(
        "#!/usr/bin/env bash\n"
        "if [ \"$1\" = \"run\" ]; then\n"
        "  dd if=/dev/zero of=\"${TEST_OUT_DIR}/flood.bin\" bs=1024 count=64 2>/dev/null\n"
        "  sleep 6\n"
        "  exit 0\n"
        "fi\n"
        "exit 0\n"
    )
    docker_shim.chmod(0o755)

    env = dict(os.environ)
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '/usr/bin:/bin')}"
    env["TEST_OUT_DIR"] = str(out_dir)
    env["STRHUB_MAX_OUT_KB"] = "16"

    res = subprocess.run(
        ["bash", str(HARNESS / "run_container.sh"), "test_quota_c", "1", str(log_file),
         "-v", f"{out_dir}:/data/out", "toolimg:ci", "echo run"],
        capture_output=True, text=True, env=env, timeout=15,
    )
    assert res.returncode == 125
    assert "Disk quota exceeded" in log_file.read_text()
