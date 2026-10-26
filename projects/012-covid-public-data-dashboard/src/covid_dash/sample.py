"""Deterministic generator for the bundled *synthetic* sample dataset.

The locations are fictional and the numbers are simulated (epidemic waves
as Gaussian bumps + Poisson noise), so the demo and tests run offline
without implying anything about real places. The generator deliberately
injects the kinds of defects found in real exports so the cleaning stage
has something to do.

    python -m covid_dash.sample examples/sample_covid.csv
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

# name, iso, continent, population, [(peak_day, height_per_100k, width_days)...], cfr
LOCATIONS = [
    ("Avalonia", "AVA", "Europe", 5_400_000, [(40, 55, 12), (150, 90, 15)], 0.012),
    ("Borealis", "BOR", "North America", 21_000_000, [(70, 30, 20), (170, 45, 12)], 0.018),
    ("Caldera", "CAL", "Africa", 9_800_000, [(100, 25, 25)], 0.022),
    ("Dunmore", "DUN", "Oceania", 2_300_000, [(25, 15, 10), (120, 70, 10), (175, 40, 8)], 0.008),
]
DAYS = 200
START = "2021-01-01"


def generate(seed: int = 12) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range(START, periods=DAYS, freq="D")
    t = np.arange(DAYS)
    rows = []
    for name, iso, cont, pop, waves, cfr in LOCATIONS:
        rate = sum(h * np.exp(-0.5 * ((t - p) / w) ** 2) for p, h, w in waves) + 0.5
        expected = rate * pop / 100_000
        expected *= np.where(dates.dayofweek >= 5, 0.6, 1.1)  # weekend under-reporting
        cases = rng.poisson(expected)
        # deaths lag cases by ~2 weeks
        deaths = rng.poisson(np.roll(expected, 14) * cfr)
        deaths[:14] = rng.poisson(expected[:14] * cfr)
        for d, c, k in zip(dates, cases, deaths):
            rows.append([iso, cont, name, d.date().isoformat(), str(c), str(k), str(pop)])
    df = pd.DataFrame(rows, columns=["iso_code", "continent", "location", "date",
                                     "new_cases", "new_deaths", "population"])

    # World aggregate rows (should be dropped by `clean`)
    world = (df.assign(nc=df.new_cases.astype(int), nd=df.new_deaths.astype(int))
               .groupby("date", as_index=False)[["nc", "nd"]].sum())
    total_pop = sum(l[3] for l in LOCATIONS)
    agg = pd.DataFrame({"iso_code": "OWID_WRL", "continent": "", "location": "World",
                        "date": world["date"], "new_cases": world["nc"].astype(str),
                        "new_deaths": world["nd"].astype(str), "population": str(total_pop)})
    df = pd.concat([df, agg], ignore_index=True)

    # --- inject realistic defects --------------------------------------
    idx = rng.choice(df.index[df.iso_code != "OWID_WRL"], size=40, replace=False)
    df.loc[idx[:8], "new_cases"] = ["n/a", "", "unknown", "", "n/a", "", "?", ""]
    df.loc[idx[8:12], "new_cases"] = ["-120", "-35", "-7", "-300"]      # corrections
    df.loc[idx[12:15], "new_deaths"] = ["-2", "-1", "-5"]
    big = df.loc[idx[15:20], "new_cases"].astype(int) + 1000
    df.loc[idx[15:20], "new_cases"] = [f"{v:,}" for v in big]          # "1,234" style
    dupes = df.loc[idx[20:26]].copy()                                  # duplicated rows
    gaps = idx[26:36]                                                  # reporting gaps
    blank_keys = idx[36:40]
    df.loc[blank_keys[:2], "date"] = "not-a-date"
    df.loc[blank_keys[2:], "location"] = ""
    df = df.drop(index=gaps)
    df = pd.concat([df, dupes], ignore_index=True)
    return df.sample(frac=1, random_state=seed).reset_index(drop=True)  # shuffle order


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "sample_covid.csv"
    generate().to_csv(out, index=False)
    print(f"wrote {out}")
