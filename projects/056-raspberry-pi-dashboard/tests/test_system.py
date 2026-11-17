from pidash import system


def test_reads_fake_linux_tree(tmp_path):
    sys_root, proc_root = tmp_path / "sys", tmp_path / "proc"
    (sys_root / "class/thermal/thermal_zone0").mkdir(parents=True)
    (sys_root / "class/thermal/thermal_zone0/temp").write_text("51234\n")
    proc_root.mkdir()
    (proc_root / "uptime").write_text("3725.42 9000.1\n")
    (proc_root / "meminfo").write_text("MemTotal:  3884000 kB\nMemFree: 100 kB\nMemAvailable:  2048000 kB\n")

    v = system.vitals(sys_root, proc_root)
    assert v["cpu_temp_c"] == 51.2
    assert v["uptime_s"] == 3725.42
    assert v["memory_mb"] == {"total": 3792, "available": 2000}


def test_missing_files_degrade_to_none(tmp_path):
    assert system.cpu_temp_c(tmp_path) is None
    assert system.uptime_seconds(tmp_path) is None
    assert system.memory_mb(tmp_path) is None


def test_garbage_temp_is_none(tmp_path):
    p = tmp_path / "class/thermal/thermal_zone0"
    p.mkdir(parents=True)
    (p / "temp").write_text("hot")
    assert system.cpu_temp_c(tmp_path) is None
