"""Re-render the near-field sheets (and the optimal 3-board set) after a
presentation-only change, without repeating the search."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sim"))

import cache  # noqa: E402
import field  # noqa: E402
import geometry  # noqa: E402
import optimize  # noqa: E402
import render_png  # noqa: E402
import export_web  # noqa: E402

FIG = ROOT / "figures"
WEB = ROOT / "web"


def main():
    for layout in geometry.baseline_layouts():
        res = 0.0025 if layout.key == "06_facing" else 0.005
        near = cache.near(layout, res=res)
        fig_dir = FIG / layout.key
        fig_dir.mkdir(parents=True, exist_ok=True)
        render_png.near_field_png(layout, near, fig_dir / "nearfield.png")
        print("near", layout.key)

    verdict = json.load(open(ROOT / "verdict.json", encoding="utf-8"))
    layout = optimize.layout_from_row(verdict["best_three"])
    m = cache.analysis(layout, du=0.003)
    fig_dir = FIG / layout.key
    render_png.far_field_png(layout, m, fig_dir / "farfield.png")
    near = cache.near(layout, res=0.005)
    render_png.near_field_png(layout, near, fig_dir / "nearfield.png")
    export_web.write_page(layout, m, near, WEB)
    print("optimal", layout.key, layout.title)

    rows = []
    for r in csv.DictReader(open(ROOT / "metrics.csv", encoding="utf-8-sig")):
        for k in ("di_db", "on_axis_db", "lobe_54_75_db", "band_max_db",
                  "band_energy_pct", "leak_60_pct", "bw6_xz_deg",
                  "bw6_yz_deg"):
            try:
                r[k] = float(r[k])
            except (TypeError, ValueError):
                r[k] = None
        r["n_boards"] = int(r["n_boards"])
        rows.append(r)
    render_png.comparison_png(rows, FIG / "comparison.png")
    print("comparison")


if __name__ == "__main__":
    main()
