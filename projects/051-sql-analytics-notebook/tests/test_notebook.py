"""The generated notebook must execute top to bottom without errors."""

from pathlib import Path

import pytest

nbformat = pytest.importorskip("nbformat")
nbclient = pytest.importorskip("nbclient")
pytest.importorskip("matplotlib")

ROOT = Path(__file__).resolve().parent.parent


def test_notebook_executes():
    nb = nbformat.read(ROOT / "notebook.ipynb", as_version=4)
    nbclient.NotebookClient(
        nb, timeout=120, kernel_name="python3", resources={"metadata": {"path": str(ROOT)}}
    ).execute()
    errors = [o for c in nb.cells if c.cell_type == "code" for o in c.outputs if o.output_type == "error"]
    assert not errors


def test_notebook_in_sync_with_sql():
    """Every query file appears in the notebook (regenerate with `make notebook` if this fails)."""
    from analytics import list_queries

    text = (ROOT / "notebook.ipynb").read_text()
    for name in list_queries():
        assert f'run_query(conn, \\"{name}\\"' in text
