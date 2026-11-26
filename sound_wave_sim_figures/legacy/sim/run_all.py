"""Regenerate every figure, table and 3D page from scratch.

    python sim/run_all.py                 # full run (~15-25 min, 8 cores)
    python sim/run_all.py --workers 4
    python sim/run_all.py --baselines-only
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sim"))

import constants as C  # noqa: E402
import export_web  # noqa: E402
import cache  # noqa: E402
import field  # noqa: E402
import geometry  # noqa: E402
import optimize  # noqa: E402
import render_png  # noqa: E402

FIG = ROOT / "figures"
WEB = ROOT / "web"
DATA = ROOT / "data"

REPORT_DU = 0.003
FIGURE_DU = 0.004
NEAR_RES = 0.005


def _row_from_metrics(layout, m) -> dict:
    if m is None:
        return {
            "key": layout.key, "short": layout.title, "n_boards": len(layout.boards),
            "di_db": None, "lobe_54_75_db": None, "band_max_db": None,
            "band_energy_pct": None, "leak_60_pct": None,
            "bw6_xz_deg": None, "bw6_yz_deg": None, "on_axis_db": None,
        }
    return {
        "key": layout.key,
        "short": layout.title,
        "n_boards": len(layout.boards),
        "di_db": m["di_db"],
        "lobe_54_75_db": m["lobe_54_75_db"],
        "band_max_db": m["band_max_db"],
        "band_energy_pct": m["band_energy_pct"],
        "leak_60_pct": m["leak_60_pct"],
        "bw6_xz_deg": m["bw6_xz_deg"],
        "bw6_yz_deg": m["bw6_yz_deg"],
        "on_axis_db": m["on_axis_db"],
    }


def _run_layout(layout, tag: str, entries: list[dict]) -> dict:
    t0 = time.time()
    fig_dir = FIG / layout.key
    fig_dir.mkdir(parents=True, exist_ok=True)
    m = None
    if layout.far_field:
        m = cache.analysis(layout, du=FIGURE_DU)
        render_png.far_field_png(layout, m, fig_dir / "farfield.png")
    res = 0.0025 if layout.key == "06_facing" else NEAR_RES
    near = cache.near(layout, res=res)
    render_png.near_field_png(layout, near, fig_dir / "nearfield.png")
    export_web.write_page(layout, m, near, WEB)

    row = _row_from_metrics(layout, m)
    stat = ("no far field (opposed boards)" if m is None else
            f"DI {m['di_db']:.1f} dB · lobe {m['lobe_54_75_db']:.0f} dB · "
            f"band {m['band_energy_pct']:.1f} %")
    entries.append({"key": layout.key, "tag": tag, "title": layout.title,
                    "stat": stat})
    print(f"  {layout.key:20s} {time.time() - t0:5.1f}s  {stat}")
    return row


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--baselines-only", action="store_true")
    args = ap.parse_args()

    for d in (FIG, WEB, DATA):
        d.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    entries: list[dict] = []

    print("Baseline layouts")
    for layout in geometry.baseline_layouts():
        rows.append(_run_layout(layout, "baseline", entries))

    if not args.baselines_only:
        print("Searching 2- and 3-board layouts")
        t0 = time.time()
        study = optimize.search(args.workers)
        rows_search = study["rows"]
        optimize.save(rows_search, {
            "best_pair": study["best_pair"],
            "best_three": study["best_three"],
        }, DATA)
        print(f"  {len(rows_search)} candidates in {time.time() - t0:.0f}s")

        current = next(r for r in rows_search if r["key"] == "05_coplanar_gap")
        alternatives = [
            r for r in rows_search
            if r["kind"] == "pair" and r["lobe_54_75_db"] > -60.0
            and np.isfinite(r.get("on_axis_db", np.nan))
            and r["on_axis_db"] > -0.5
        ]
        alternative = min(alternatives, key=lambda r: r["band_max_db"])
        alt_row = dict(alternative)
        alt_row["key"] = "05_alt"
        alt_row["short"] = "Pair 16.54 / 5.25 (no null)"
        rows.append(alt_row)
        study_dir = FIG / "study"
        study_dir.mkdir(parents=True, exist_ok=True)
        render_png.study2_scan_png(rows_search, study_dir / "study2_scan.png",
                                   current=current)
        render_png.study2_yaw_png(rows_search, study_dir / "study2_yaw.png")
        render_png.study3_heatmap_png(rows_search, study_dir / "study3_heatmap.png",
                                      best=study["best_three"])

        print("Optimal layouts")
        finals = []
        for row in (study["best_pair"], study["best_three"]):
            if row.get("key") == "05_coplanar_gap":
                # the 2-board optimum is the current pair, already rendered
                continue
            layout = optimize.layout_from_row(row)
            m = cache.analysis(layout, du=REPORT_DU)
            fig_dir = FIG / layout.key
            fig_dir.mkdir(parents=True, exist_ok=True)
            render_png.far_field_png(layout, m, fig_dir / "farfield.png")
            near = cache.near(layout, res=NEAR_RES)
            render_png.near_field_png(layout, near, fig_dir / "nearfield.png")
            export_web.write_page(layout, m, near, WEB)
            final_row = _row_from_metrics(layout, m)
            final_row["short"] = layout.title
            finals.append(final_row)
            entries.append({
                "key": layout.key, "tag": "searched optimum",
                "title": layout.title,
                "stat": (f"DI {m['di_db']:.1f} dB · lobe "
                         f"{m['lobe_54_75_db']:.0f} dB · band "
                         f"{m['band_energy_pct']:.1f} %"),
            })

        rows.extend(finals)
        accurate_opt = next((r for r in finals if r["key"] == "opt3"),
                            study["best_three"])
        render_png.pareto_png(rows_search, FIG / "pareto.png",
                              current=current,
                              optimal=accurate_opt,
                              alternative=alternative)
    # ---- tables and summary charts
    if not args.baselines_only:
        render_png.decomposition_png(geometry.coplanar_gap(),
                                     FIG / "decomposition.png")
    render_png.comparison_png(rows, FIG / "comparison.png")
    if not args.baselines_only:
        tolerance_dir = FIG
        render_png.tolerance_png(geometry.coplanar_gap(),
                                 tolerance_dir / "tolerance.png")
    if not args.baselines_only:
        render_png.leak_compare_png(
            [(geometry.coplanar_gap(), render_png.BLUE, "current pair"),
             (geometry.coplanar_butt(), render_png.GRAY, "butted pair")],
            FIG / "leak_compare.png",
        )
    with open(ROOT / "metrics.csv", "w", newline="", encoding="utf-8") as fh:
        fields = ["key", "short", "n_boards", "di_db", "lobe_54_75_db",
                  "band_max_db", "band_energy_pct", "leak_60_pct",
                  "bw6_xz_deg", "bw6_yz_deg", "on_axis_db"]
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in fields})

    export_web.write_index(entries, WEB)
    if not args.baselines_only:
        with open(ROOT / "verdict.json", "w", encoding="utf-8") as fh:
            json.dump({
                "best_pair": study["best_pair"],
                "best_three": study["best_three"],
                "current": next(r for r in rows_search
                                if r["key"] == "05_coplanar_gap"),
            }, fh, indent=2)
    print("done")


if __name__ == "__main__":
    main()
