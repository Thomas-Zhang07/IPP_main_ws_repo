"""Like-for-like re-score of the candidate families.

The coplanar fronts were produced with the grid-only metrics (``exact=False``),
while the V search samples the exact grating/broadside directions.  This
module re-scores the top rows of every front with the same exact metrics, the
same fine grid and the same DI quadrature, and writes ``winners.csv`` — the
one table the report quotes.

Run::

    python -m optimum_search.rescore
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

from . import metrics, model, report, search, vshape

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "search2"

TOP = 3
DU = 0.008
STEP = 0.008


def _row(family, key, boards, span_mm, depth_mm, fn, elem_env=None,
         extra=None):
    dirs, _, _, _ = model.direction_grid(DU)
    comp = metrics.score_states_fn(fn, dirs, search.REFINE_STATES,
                                   exact=True, step=STEP)
    sr = metrics.srange_fn(fn, search.AZIMUTHS, step_deg=1.0, du=0.02,
                           exact=True)
    di = metrics.di0_fn(fn, fine=True)
    row = {"family": family, "key": key, "boards": boards,
           "span_mm": span_mm, "depth_mm": depth_mm,
           "SL_cmd": comp["SL_cmd"], "SL_diag": comp["SL_diag"],
           "SRANGE_0dB": sr[0.0], "SRANGE_-3dB": sr[-3.0], "DI0": di,
           "element_env": "" if elem_env is None else elem_env,
           "shortlist": report.provisional_score(
               {"SL_cmd": comp["SL_cmd"], "SL_diag": comp["SL_diag"],
                "SRANGE_0dB": sr[0.0], "DI0": di})}
    row.update(extra or {})
    return row


def coplanar_rows(family, csv_name, n=TOP):
    path = OUT / csv_name
    with open(path, newline="", encoding="utf-8") as fh:
        rows = sorted(csv.DictReader(fh), key=lambda r: float(r["shortlist"]))
    out = []
    for r in rows[:n]:
        cand = model.from_key(r["key"])
        fn = lambda d, u, v: model.field_fast(cand, d, u, v, "mean")
        out.append(_row(family, r["key"], int(r["n_boards"]),
                        float(r["span_mm"]), "", fn,
                        r.get("SL_elem") or None,
                        {"SL_4bit": r.get("SL_4bit", ""),
                         "SL_mech": r.get("SL_mech", ""),
                         "SL_drift": r.get("SL_drift", "")}))
    return out


def v_rows(n=TOP):
    path = OUT / "front_v.csv"
    with open(path, newline="", encoding="utf-8") as fh:
        rows = sorted(csv.DictReader(fh), key=lambda r: float(r["shortlist"]))
    out = []
    for r in rows[:n]:
        inc, off = float(r["included_deg"]), float(r["offset_mm"]) / 1e3
        layout = vshape.v_pair_offset(inc, off)
        fn = vshape.field_fn(layout, "mean")
        out.append(_row(f"V {inc:.0f} deg / y {off * 1e3:.2f} mm",
                        r["key"], 2, float(r["span_mm"]),
                        float(r["depth_mm"]), fn, r.get("SL_cmd_env") or None))
    return out


def main() -> None:
    rows = (coplanar_rows("2-board", "front_2.csv")
            + coplanar_rows("3-board", "front_3.csv")
            + v_rows())
    fields = ["family", "key", "boards", "span_mm", "depth_mm", "SL_cmd",
              "SL_diag", "SRANGE_0dB", "SRANGE_-3dB", "DI0", "element_env",
              "SL_4bit", "SL_mech", "SL_drift", "shortlist"]
    with open(OUT / "winners.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow({k: (f"{row[k]:.3f}" if isinstance(row.get(k), float)
                            else row.get(k, "")) for k in fields})
    (OUT / "winners.json").write_text(json.dumps(rows, indent=2), "utf-8")
    for row in rows:
        print(f"{row['family']:22s} {row['key']:40s}"
              f"  SL_cmd {row['SL_cmd']:+.2f}  SL_diag {row['SL_diag']:+.2f}"
              f"  SRANGE0 {row['SRANGE_0dB']:.0f}  DI0 {row['DI0']:.2f}"
              f"  env {row['element_env'] or '-'}")


if __name__ == "__main__":
    main()
