"""Generate notebook.ipynb from the SQL files so the notebook never drifts from them.

Run ``make notebook`` (or ``python build_notebook.py``) after editing queries.
Add ``--execute`` to run every cell and save outputs.
"""

from __future__ import annotations

import sys
from pathlib import Path

import nbformat as nbf

from analytics import list_queries, load_query

HERE = Path(__file__).resolve().parent
OUT = HERE / "notebook.ipynb"

# Optional extra cell (Python) shown after a query to visualise its result.
CHARTS = {
    "03_summary_by_species_sex": """\
ax = df.pivot(index="species", columns="sex", values="avg_body_mass_g").plot.bar(rot=0)
ax.set_ylabel("Average body mass (g)")
ax.set_title("Body mass by species and sex")
plt.show()""",
    "06_yearly_trend": """\
ax = df.pivot(index="year", columns="species", values="avg_mass_g").plot(marker="o")
ax.set_xticks([2007, 2008, 2009])
ax.set_ylabel("Average body mass (g)")
ax.set_title("Yearly average body mass")
plt.show()""",
    "09_mass_histogram": """\
ax = df.set_index("bucket_start_g")[["adelie", "chinstrap", "gentoo"]].plot.bar(stacked=True, rot=45)
ax.set_xlabel("Body mass bucket start (g)")
ax.set_ylabel("Penguins")
ax.set_title("Body-mass distribution (500 g buckets)")
plt.show()""",
}


def build() -> nbf.NotebookNode:
    nb = nbf.v4.new_notebook()
    cells = [
        nbf.v4.new_markdown_cell(
            "# SQL Analytics Notebook — Palmer Penguins\n\n"
            "Exploratory analysis of the [Palmer Penguins](https://allisonhorst.github.io/palmerpenguins/) "
            "dataset (344 penguins, 3 species, 3 islands, 2007–2009; CC0) using **SQL in SQLite**.\n\n"
            "Every query lives in `sql/queries/` — this notebook is generated from them by "
            "`build_notebook.py`. Each section names the SQL technique it shows."
        ),
        nbf.v4.new_code_cell(
            "%matplotlib inline\n"
            "import matplotlib.pyplot as plt\n"
            "import pandas as pd\n"
            "plt.rcParams.update({\"figure.figsize\": (6, 3.5), \"figure.dpi\": 72})\n"
            "from analytics import build_database, load_query, run_query\n\n"
            "conn = build_database()  # in-memory SQLite, loaded from data/*.csv\n"
            "pd.read_sql_query(\"SELECT * FROM penguins LIMIT 5\", conn)"
        ),
        nbf.v4.new_markdown_cell("## Schema\n\n```sql\n" + (HERE / "sql/schema.sql").read_text().strip() + "\n```"),
    ]
    for name in list_queries():
        sql = load_query(name)
        header = sql.splitlines()[0].lstrip("- ").strip()
        cells.append(nbf.v4.new_markdown_cell(f"## {header}\n\n```sql\n{sql.strip()}\n```"))
        cells.append(nbf.v4.new_code_cell(f'df = run_query(conn, "{name}", as_frame=True)\ndf'))
        if name in CHARTS:
            cells.append(nbf.v4.new_code_cell(CHARTS[name]))
    cells.append(
        nbf.v4.new_markdown_cell(
            "## Takeaways\n\n"
            "* Gentoo live only on Biscoe and Chinstrap only on Dream; Adelie are on all three islands.\n"
            "* Gentoo are the heaviest species by roughly 1 kg; males outweigh females in every species.\n"
            "* Bill depth alone separates Gentoo; bill length then splits Adelie from Chinstrap — a two-rule "
            "`CASE` classifier gets over 90% right per species.\n"
            "* Only two penguins are more than 2.5 standard deviations from their species mean."
        )
    )
    nb.cells = cells
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    return nb


def main() -> None:
    nb = build()
    if "--execute" in sys.argv:
        from nbclient import NotebookClient

        NotebookClient(nb, timeout=120, kernel_name="python3", resources={"metadata": {"path": str(HERE)}}).execute()
    nbf.write(nb, OUT)
    print(f"wrote {OUT.name} ({len(nb.cells)} cells)")


if __name__ == "__main__":
    main()
