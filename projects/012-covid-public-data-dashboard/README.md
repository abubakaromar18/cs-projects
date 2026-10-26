# 012 · COVID/Public Data Dashboard

A small, end-to-end **data pipeline** in Python: it loads an open public-health
dataset, **cleans** it (and reports every fix), **analyzes** it with Pandas
(rolling averages, per-capita rates, case-fatality ratio, peaks, week-over-week
growth), and renders an **interactive Plotly dashboard** as a single HTML file.

It works with the [Our World in Data](https://ourworldindata.org/coronavirus)
COVID-19 export out of the box, and ships with a **synthetic** sample dataset
(fictional countries, simulated numbers) so everything runs offline.

```
CSV ──► load ──► clean ──► analyze ──► dashboard.html
        (str)    tidy daily  metrics +    4 linked charts
                 panel +     summary      + summary table
                 report
```

## Key CS / data-engineering concepts

| Concept | Where |
|---|---|
| ETL pipeline with separate, testable stages | `load.py` → `clean.py` → `analyze.py` → `dashboard.py` |
| Schema normalization & type coercion with error accounting | `clean.normalize_column`, `clean._to_number` |
| Data-quality repairs: duplicates, negative corrections, aggregates, missing keys | `clean.clean` + `CleaningReport` |
| Reindexing a time series onto a complete calendar (gap filling) | `pd.date_range` + `reindex` per group |
| Split-apply-combine (`groupby().transform`) | cumulative sums, rolling means |
| Moving averages to remove weekday reporting seasonality | `add_metrics(window=7)` |
| Normalization (per-100k rates) for fair comparison | `*_per_100k` columns |
| Avoiding look-ahead / truncation bias: compute metrics *before* date filtering | `cli.main` |
| Deterministic synthetic data generation for reproducible tests | `sample.py` (seeded RNG) |
| Interactive visualization with linked legends | `dashboard.build_dashboard` |

## Build, run, test

Requires Python 3.10+.

```bash
make dev            # pip install -e '.[dev]'  (pandas, plotly, pytest)
make test           # run the 20 tests
make demo           # sample data → out/dashboard.html + summary table
```

Without `make`:

```bash
pip install -e '.[dev]'
covid-dash --input examples/sample_covid.csv --summary --out dashboard.html
python -m pytest
```

### CLI

```
covid-dash (--input PATH|URL | --download) [options]

  --countries/-c  "A,B"   only these locations (case-insensitive)
  --start / --end DATE    date range to display
  --window N              rolling-average window (default 7)
  --top N                 keep the N locations with the most cases per 100k
  --summary               print the per-location summary
  --export-clean CSV      save the cleaned + enriched data
  --out/-o FILE           dashboard path (default dashboard.html)
  --offline               embed plotly.js so the HTML works without internet
  --no-html               skip the dashboard
```

Real data (needs internet; the OWID file is ~90 MB):

```bash
covid-dash --download --countries "Germany,Japan,Brazil,Nigeria" \
           --start 2021-01-01 --end 2022-12-31 --summary
```

## Example output

```
$ make demo
Cleaning report
  rows in                      996
  rows out                     800
  dropped missing keys           4
  dropped aggregates           200
  dropped duplicates             6
  bad numbers                    2
  negative values fixed          7
  gap days filled               14
  locations                      4
          total_cases  total_deaths  cases_per_100k  deaths_per_100k  cfr_pct   peak_date  peak_cases_avg   last_date  wow_growth_pct
location
Avalonia   257,705.00      3,118.00        4,772.31            57.74     1.21  2021-06-03        4,679.71  2021-07-19          -64.88
Dunmore     65,423.00        565.00        2,844.48            24.57     0.86  2021-05-03        1,514.00  2021-07-19          -78.59
Borealis   574,407.00      9,986.00        2,735.27            47.55     1.74  2021-06-23        9,053.71  2021-07-19          -64.28
Caldera    153,751.00      3,411.00        1,568.89            34.81     2.22  2021-04-14        2,382.71  2021-07-19          -27.35
wrote out/dashboard.html
```

The dashboard has four panels: new cases per 100k (7-day avg), new deaths
per 100k (7-day avg), cumulative cases per 100k, and case fatality ratio over
time, plus a summary table. Clicking a legend entry toggles that location in
every panel.

## Cleaning decisions (and why)

* **Aggregates** (`iso_code` starting with `OWID_`, e.g. "World", "Europe") are
  dropped so they don't dwarf countries or get double-counted. Use
  `clean(df, keep_aggregates=True)` to keep them.
* **Duplicates** on `(location, date)` keep the *last* row, which is the most
  recently published value.
* **Negative daily counts** are back-dated corrections. We can't know which
  earlier days were wrong, so they become 0, and cumulative totals stay
  monotonic.
* **Missing days** are inserted with 0 new events, so rolling windows always
  span real calendar days.
* **Unparseable numbers** ("unknown", "?") are counted in the report and
  treated as 0.

## About the sample data

`examples/sample_covid.csv` is generated by `python -m covid_dash.sample`
(`make sample`). The locations (Avalonia, Borealis, Caldera, Dunmore) are
fictional. Cases come from Gaussian "waves", weekend under-reporting and
Poisson noise, and deaths lag cases by two weeks. The generator then injects
realistic defects: blanks, junk strings, thousands separators, negatives,
duplicates, missing days, bad dates and a "World" aggregate. A test checks
that the committed file matches the generator byte for byte.

## Possible extensions

* Add vaccination and testing columns (positivity rate, doses per 100).
* Excess-mortality comparison against a baseline.
* Estimate the effective reproduction number R<sub>t</sub> from the case curve.
* Choropleth world map (`plotly.express.choropleth` on `iso_code`).
* Cache the downloaded CSV as Parquet and only refresh it when it's stale.
* Serve it live with Dash or Streamlit, with dropdowns instead of CLI flags.
