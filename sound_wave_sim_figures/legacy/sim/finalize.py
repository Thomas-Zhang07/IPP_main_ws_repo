"""Complete the outputs from a saved search (run_all crashed only in charts).

This is the post-processing half of run_all, split so a long search does not
have to be repeated.  run_all.py remains the canonical entry point.
"""

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
DATA = ROOT / "data"
NUM = ("band_energy_pct", "leak_60_pct", "lobe_54_75_db", "band_max_db",
       "di_db", "bw6_xz_deg", "bw6_yz_deg", "on_axis_db")


def load_rows():
    rows = list(csv.DictReader(open(DATA / "candidates.csv",
                                    encoding="utf-8-sig")))
    for r in rows:
        for k in NUM:
            try:
                r[k] = float(r[k])
            except (TypeError, ValueError):
                r[k] = float("nan")
    return rows


def main():
    rows_search = load_rows()
    best_pair = optimize.best_of(rows_search, ("pair",))
    best_three = optimize.best_of(rows_search, ("three",))
    print("best pair:", best_pair["short"], best_pair.get("key"))
    print("best three:", best_three["short"])

    study_dir = FIG / "study"
    study_dir.mkdir(parents=True, exist_ok=True)
    current = next(r for r in rows_search if r["key"] == "05_coplanar_gap")
    render_png.study2_scan_png(rows_search, study_dir / "study2_scan.png",
                               current=current)
    render_png.study2_yaw_png(rows_search, study_dir / "study2_yaw.png")
    render_png.study3_heatmap_png(rows_search, study_dir / "study3_heatmap.png",
                                  best=best_three)
    render_png.pareto_png(rows_search, FIG / "pareto.png", current=current,
                          optimal=best_three)

    # accurate baseline metrics + index entries (cached)
    cache = DATA / "baselines.json"
    rows, entries = [], []
    if cache.exists():
        rows = json.load(open(cache, encoding="utf-8"))
        entries = [{
            "key": r["key"], "tag": "baseline", "title": r["short"],
            "stat": ("no far field" if r["di_db"] is None else
                     f"DI {r['di_db']:.1f} dB · band {r['band_energy_pct']:.1f} %"),
        } for r in rows]
        print("  baselines loaded from cache")
    for layout in ([] if cache.exists() else geometry.baseline_layouts()):
        m = None
        if layout.far_field:
            m = cache.analysis(layout, du=0.004)
        row = {
            "key": layout.key, "short": layout.title,
            "n_boards": len(layout.boards),
            "di_db": None if m is None else m["di_db"],
            "lobe_54_75_db": None if m is None else m["lobe_54_75_db"],
            "band_max_db": None if m is None else m["band_max_db"],
            "band_energy_pct": None if m is None else m["band_energy_pct"],
            "leak_60_pct": None if m is None else m["leak_60_pct"],
            "bw6_xz_deg": None if m is None else m["bw6_xz_deg"],
            "bw6_yz_deg": None if m is None else m["bw6_yz_deg"],
            "on_axis_db": None if m is None else m["on_axis_db"],
        }
        rows.append(row)
        entries.append({
            "key": layout.key, "tag": "baseline", "title": layout.title,
            "stat": ("no far field" if m is None else
                     f"DI {m['di_db']:.1f} dB · band {m['band_energy_pct']:.1f} %"),
        })
        if layout.key == "05_coplanar_gap":
            current_row = row
        print("  baseline", layout.key)

    # optimal 3-board set (the 2-board optimum is the current pair, already rendered)
    if best_three.get("key") != "05_coplanar_gap":
        layout = optimize.layout_from_row(best_three)
        m = cache.analysis(layout, du=0.003)
        fig_dir = FIG / layout.key
        fig_dir.mkdir(parents=True, exist_ok=True)
        render_png.far_field_png(layout, m, fig_dir / "farfield.png")
        near = cache.near(layout, res=0.005)
        render_png.near_field_png(layout, near, fig_dir / "nearfield.png")
        export_web.write_page(layout, m, near, WEB)
        rows.append({
            "key": layout.key, "short": layout.title,
            "n_boards": len(layout.boards), "di_db": m["di_db"],
            "lobe_54_75_db": m["lobe_54_75_db"], "band_max_db": m["band_max_db"],
            "band_energy_pct": m["band_energy_pct"], "leak_60_pct": m["leak_60_pct"],
            "bw6_xz_deg": m["bw6_xz_deg"], "bw6_yz_deg": m["bw6_yz_deg"],
            "on_axis_db": m["on_axis_db"],
        })
        entries.append({
            "key": layout.key, "tag": "searched optimum", "title": layout.title,
            "stat": f"DI {m['di_db']:.1f} dB · band {m['band_energy_pct']:.1f} %",
        })

    render_png.comparison_png(rows, FIG / "comparison.png")
    fields = ["key", "short", "n_boards", "di_db", "lobe_54_75_db",
              "band_max_db", "band_energy_pct", "leak_60_pct",
              "bw6_xz_deg", "bw6_yz_deg", "on_axis_db"]
    with open(ROOT / "metrics.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in fields})
    export_web.write_index(entries, WEB)

    with open(DATA / "baselines.json", "w", encoding="utf-8") as fh:
        json.dump(rows, fh, indent=2)
    with open(ROOT / "verdict.json", "w", encoding="utf-8") as fh:
        json.dump({"best_pair": best_pair, "best_three": best_three,
                   "current": current}, fh, indent=2)
    print("done")


if __name__ == "__main__":
    main()
