"""Stage 4: visualisation.

Builds one Plotly figure with four linked panels and writes it as a
standalone HTML file (open it in any browser; hover, zoom and click legend
entries to toggle a location in every panel at once — they share
`legendgroup`s).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.colors import qualitative
from plotly.subplots import make_subplots


def _fmt(x, digits=1):
    return "—" if pd.isna(x) else f"{x:,.{digits}f}"


def build_dashboard(df: pd.DataFrame, summary: pd.DataFrame,
                    title: str = "COVID-19 Public Data Dashboard") -> go.Figure:
    fig = make_subplots(
        rows=3, cols=2,
        specs=[[{}, {}], [{}, {}], [{"type": "table", "colspan": 2}, None]],
        row_heights=[0.36, 0.30, 0.34],
        vertical_spacing=0.08,
        subplot_titles=(
            "New cases per 100k (7-day avg)",
            "New deaths per 100k (7-day avg)",
            "Cumulative cases per 100k",
            "Case fatality ratio (%)",
            "Summary by location",
        ),
    )
    palette = qualitative.Plotly
    order = list(summary.index)  # sorted by cases per 100k
    for i, loc in enumerate(order):
        g = df[df["location"] == loc].sort_values("date")
        color = palette[i % len(palette)]
        common = dict(legendgroup=loc, line=dict(color=color, width=2), mode="lines")
        fig.add_trace(go.Scatter(x=g["date"], y=g["cases_avg_per_100k"], name=loc,
                                 hovertemplate="%{x|%b %d %Y}<br>%{y:.1f} / 100k<extra>" + loc + "</extra>",
                                 **common), row=1, col=1)
        fig.add_trace(go.Scatter(x=g["date"], y=g["deaths_avg_per_100k"], name=loc, showlegend=False,
                                 hovertemplate="%{x|%b %d %Y}<br>%{y:.2f} / 100k<extra>" + loc + "</extra>",
                                 **common), row=1, col=2)
        fig.add_trace(go.Bar(x=[loc], y=[summary.loc[loc, "cases_per_100k"]], name=loc,
                             legendgroup=loc, showlegend=False, marker_color=color,
                             hovertemplate="%{y:,.0f} / 100k<extra>" + loc + "</extra>"), row=2, col=1)
        fig.add_trace(go.Scatter(x=g["date"], y=g["cfr_pct"], name=loc, showlegend=False,
                                 hovertemplate="%{x|%b %d %Y}<br>CFR %{y:.2f}%<extra>" + loc + "</extra>",
                                 **common), row=2, col=2)

    s = summary.reset_index()
    fig.add_trace(go.Table(
        header=dict(values=["Location", "Total cases", "Deaths", "Cases /100k",
                            "Deaths /100k", "CFR %", "Peak (7d avg)", "WoW %"],
                    fill_color="#2a3f5f", font=dict(color="white"), align="left"),
        cells=dict(values=[
            s["location"],
            [_fmt(v, 0) for v in s["total_cases"]],
            [_fmt(v, 0) for v in s["total_deaths"]],
            [_fmt(v, 0) for v in s["cases_per_100k"]],
            [_fmt(v, 1) for v in s["deaths_per_100k"]],
            [_fmt(v, 2) for v in s["cfr_pct"]],
            [f"{d} ({_fmt(v, 0)})" for d, v in zip(s["peak_date"], s["peak_cases_avg"])],
            [_fmt(v, 1) for v in s["wow_growth_pct"]],
        ], align="left"),
    ), row=3, col=1)

    start, end = df["date"].min(), df["date"].max()
    fig.update_layout(
        title=dict(text=f"{title}<br><sup>{start:%b %d %Y} – {end:%b %d %Y} · "
                        f"{len(order)} locations</sup>", y=0.985, yanchor="top"),
        template="plotly_white", height=1100, hovermode="x unified",
        legend=dict(orientation="h", y=1.03, x=0, yanchor="bottom"),
        margin=dict(t=120, l=50, r=30, b=30),
    )
    return fig


def write_html(fig: go.Figure, path: str | Path, offline: bool = False) -> Path:
    """Write the figure. `offline=True` embeds plotly.js (~4 MB) so the file
    works without internet; otherwise plotly.js loads from its CDN."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(path, include_plotlyjs=True if offline else "cdn", full_html=True)
    return path
