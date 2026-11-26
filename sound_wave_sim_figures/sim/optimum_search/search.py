"""Candidate grids, coarse/refine scoring, Pareto front and CSV."""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

from . import metrics, model

BUILD_MIN_M = 0.010902
SEAM_MAX_M = 0.02625
OFFSET_MAX_M = 0.0105
EXACT_SEAMS = (0.010902, 0.014, 0.01575, 0.0175, 0.0245, 0.02625)

AZIMUTHS = (0.0, 45.0, 90.0, 135.0, 180.0, 225.0, 270.0, 315.0)
THETA_MAX = 35.0
REFINE_STATES = ([(0.0, 0.0)]
                 + [(float(t), a) for t in np.arange(5.0, THETA_MAX + 1e-9, 5.0)
                    for a in AZIMUTHS])
COARSE_STATES = [(t, a) for t in (0.0, 10.0, 20.0, 25.0, 30.0, 35.0)
                 for a in (0.0, 45.0, 90.0, 135.0)]

CSV_FIELDS = ["key", "n_boards", "span_mm", "span_y_mm", "SL_cmd", "SL_clean",
              "SL_near", "SL_far_s", "SL_diag", "SRANGE_0dB", "SRANGE_-3dB",
              "DI0", "BNE0", "SL_near0", "SL_far0", "SL_shoulder0", "N54",
              "SL_4bit", "SL_mech", "SL_drift", "SL_elem", "robust_max",
              "shortlist"]


def _sorted_unique(values):
    return np.array(sorted(set(round(float(v), 6) for v in values)))


def seam_values(two_board: bool) -> np.ndarray:
    step = 0.00025 if two_board else 0.0005
    grid = np.arange(0.011, SEAM_MAX_M + 1e-9, step)
    return _sorted_unique(list(grid) + list(EXACT_SEAMS))


def offset_values(two_board: bool) -> np.ndarray:
    if two_board:
        values = np.arange(0.0, OFFSET_MAX_M + 1e-9, 0.00025)
    else:
        values = np.arange(0.0, OFFSET_MAX_M + 1e-9, 0.00175)
    return _sorted_unique(list(values) + [0.0035, 0.00525, 0.007, 0.0105])


def two_board_candidates():
    return [model.pair(s, o) for s in seam_values(True)
            for o in offset_values(True)]


def three_board_candidates():
    return [model.triple(s1, s2, o2, o3)
            for s1 in seam_values(False) for s2 in seam_values(False)
            for o2 in offset_values(False) for o3 in offset_values(False)]


def score_rows(cands, states, dirs=None, du: float = 0.02,
               variant: str = "mean"):
    if dirs is None:
        dirs, _, _, _ = model.direction_grid(du)
    rows = []
    for cand in cands:
        vals = metrics.score_states(cand, du, states, variant, dirs=dirs)
        row = {"key": cand.key, "cand": cand, "n_boards": cand.n_boards,
               "span_mm": cand.span_m * 1e3, "span_y_mm": cand.span_y_m * 1e3}
        row.update(vals)
        rows.append(row)
    return rows


def _dominates(a, b, keys):
    better = all(s * a[k] <= s * b[k] + 1e-12 for k, s in keys)
    strict = any(s * a[k] < s * b[k] - 1e-12 for k, s in keys)
    return better and strict


def pareto(rows, minimize=("SL_cmd", "SL_diag"), maximize=("SRANGE_0dB",)):
    keys = [(k, 1.0) for k in minimize] + [(k, -1.0) for k in maximize]
    keys = [(k, s) for k, s in keys if all(k in r for r in rows)]
    front = []
    for i, r in enumerate(rows):
        if any(_dominates(q, r, keys) for j, q in enumerate(rows) if j != i):
            continue
        front.append(r)
    return front


def pareto2(rows, k1="SL_cmd", k2="SL_diag"):
    """Fast 2-objective (minimise) non-dominated set."""
    ordered = sorted(rows, key=lambda r: (r[k1], r[k2]))
    front, best2 = [], np.inf
    for row in ordered:
        if row[k2] <= best2 + 1e-12:
            front.append(row)
            best2 = min(best2, row[k2])
    return front


def add_srange(rows, top_n=40, step_deg=1.0, du=0.012, dirs=None):
    dirs, _, _, _ = model.direction_grid(du)
    ranked = sorted(rows, key=lambda r: r.get("SL_cmd", 0.0)
                    + 0.3 * r.get("SL_diag", 0.0))
    for row in ranked[:top_n]:
        out = metrics.srange(row["cand"], AZIMUTHS, step_deg=step_deg, du=du,
                             dirs=dirs)
        row["SRANGE_0dB"] = out[0.0]
        row["SRANGE_-3dB"] = out[-3.0]
    return rows


def write_csv(rows, path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            out = {}
            for key in CSV_FIELDS:
                value = row.get(key, "")
                out[key] = f"{value:.3f}" if isinstance(value, float) else value
            writer.writerow(out)


def load_front(path: Path):
    rows = []
    with open(path, newline="", encoding="utf-8") as fh:
        for raw in csv.DictReader(fh):
            row = {"key": raw["key"], "cand": model.from_key(raw["key"])}
            for key, value in raw.items():
                if key in ("key", ""):
                    continue
                try:
                    row[key] = float(value) if value != "" else float("nan")
                except ValueError:
                    row[key] = value
            rows.append(row)
    return rows
