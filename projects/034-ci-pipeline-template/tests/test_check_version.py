import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("check_version", ROOT / "scripts/check_version.py")
check_version = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_version)


@pytest.mark.parametrize(
    ("tag", "version", "ok"),
    [
        ("v1.2.3", "1.2.3", True),
        ("v1.0.0rc1", "1.0.0rc1", True),
        ("v1.2.3", "1.2.4", False),
        ("1.2.3", "1.2.3", False),
        ("v1.2", "1.2", False),
        ("release", "1.0.0", False),
    ],
)
def test_check(tag, version, ok):
    assert (check_version.check(tag, version) is None) is ok


def test_pyproject_and_package_versions_agree():
    import slugkit

    assert check_version.project_version(ROOT / "pyproject.toml") == slugkit.__version__


def test_main_exit_codes(capsys):
    version = check_version.project_version(ROOT / "pyproject.toml")
    assert check_version.main(["prog", f"v{version}"]) == 0
    assert check_version.main(["prog", "v99.99.99"]) == 1
    assert "::error::" in capsys.readouterr().out
    assert check_version.main(["prog"]) == 2
