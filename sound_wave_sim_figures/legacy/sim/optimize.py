"""2- and 3-board search: which geometry leaks least?

Coplanar candidates are evaluated with :class:`field.CoplanarModel`, which is
exact and ~300x faster than summing 512 emitters per direction.  Every
candidate is therefore scored on the same full-resolution direction-cosine
grid as the figures; there is no coarse-grid aliasing.  Tilted layouts (V,
concave) use the direct solver and are few.
"""

from __future__ import annotations

import csv
import itertools
import json
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

import constants as C
import field
import geometry

SEARCH_DU = 0.004          # same resolution as the figures
REPORT_DU = 0.003

SEAM_MIN, SEAM_MAX = C.BUTT_SEAM_M, 0.02625
OFFSET_MIN, OFFSET_MAX = 0.0, C.PITCH_M

OFFSET_PATTERNS = (
    (0.0, 0.0, 0.0),
    (0.0, 0.5 * C.PITCH_M, 0.0),
    (0.5 * C.PITCH_M, 0.0, 0.5 * C.PITCH_M),
    (0.0, 0.5 * C.PITCH_M, 0.5 * C.PITCH_M),
)

_MODEL = None


def _model() -> field.CoplanarModel:
    global _MODEL
    if _MODEL is None:
        _MODEL = field.CoplanarModel(du=SEARCH_DU)
    return _MODEL


def pair_offsets(seam: float, offset: float) -> list[tuple[float, float, float]]:
    """Board origins relative to board A's first emitter (metres)."""
    return [(0.0, 0.0, 0.0), (C.SPAN_M + seam, offset, 0.0)]


def three_offsets(s1: float, s2: float,
                  offs) -> list[tuple[float, float, float]]:
    xs = [0.0, C.SPAN_M + s1, 2 * C.SPAN_M + s1 + s2]
    return [(x, float(y), 0.0) for x, y in zip(xs, offs)]


def build(spec: dict) -> geometry.Layout:
    kind = spec["kind"]
    if kind == "pair":
        return geometry._pair_coplanar(
            float(spec["seam"]), float(spec["offset"]),
            "study2_pair", "Study pair", "searched pair",
        )
    if kind == "v":
        return geometry.v_pair(
            float(spec["included"]), f"study2_v{spec['included']:.0f}",
            f"V {spec['included']:.0f} deg",
        )
    if kind == "three":
        return geometry.coplanar3(
            float(spec["s1"]), float(spec["s2"]),
            tuple(float(o) for o in spec["offsets"]),
            key="study3_three", title="Study three",
        )
    if kind == "concave":
        return geometry.concave3(float(spec["wing"]))
    raise ValueError(kind)


def _row(spec: dict, m: dict) -> dict:
    row = {
        "kind": spec["kind"],
        "taper": spec.get("taper", "uniform"),
        "short": spec.get("label") or _short(spec),
        "n_boards": 3 if spec["kind"] in ("three", "concave") else 2,
        "key": spec.get("key", "study"),
        "band_energy_pct": round(m["band_energy_pct"], 4),
        "leak_60_pct": round(m["leak_60_pct"], 4),
        "lobe_54_75_db": round(m["lobe_54_75_db"], 3),
        "band_max_db": round(m["band_max_db"], 3),
        "di_db": round(m["di_db"], 3),
        "bw6_xz_deg": round(m["bw6_xz_deg"], 3),
        "bw6_yz_deg": round(m["bw6_yz_deg"], 3),
        "on_axis_db": round(m["on_axis_db"], 3),
    }
    for key in ("seam", "offset", "included", "s1", "s2", "wing"):
        if key in spec:
            row[key] = round(float(spec[key]), 6)
    if "offsets" in spec:
        row["offsets"] = ",".join(f"{o:.6f}" for o in spec["offsets"])
    return row


def _short(spec: dict) -> str:
    if spec["kind"] == "pair":
        return (f"pair s={float(spec['seam']) * 1e3:.2f} "
                f"o={float(spec['offset']) * 1e3:.2f}")
    if spec["kind"] == "v":
        return f"V {float(spec['included']):.0f}°"
    if spec["kind"] == "three":
        offs = "/".join(f"{float(o) * 1e3:.1f}" for o in spec["offsets"])
        return (f"3 s={float(spec['s1']) * 1e3:.2f}/"
                f"{float(spec['s2']) * 1e3:.2f} o={offs}")
    return f"concave wing {float(spec['wing']):.0f}°"


def evaluate(spec: dict) -> dict:
    kind = spec["kind"]
    taper = spec.get("taper", "uniform")
    if kind == "pair":
        m = _model().analyse(pair_offsets(spec["seam"], spec["offset"]), taper)
    elif kind == "three":
        m = _model().analyse(
            three_offsets(spec["s1"], spec["s2"], spec["offsets"]), taper
        )
    else:
        layout = build(spec)
        m = field.analyse(layout.positions, layout.normals,
                          layout.amplitudes(taper), du=SEARCH_DU)
    return _row(spec, m)


def _run_pool(specs: list[dict], workers: int | None = None) -> list[dict]:
    if not specs:
        return []
    if workers is None:
        workers = min(10, max(1, (os.cpu_count() or 2) - 2))
    if workers == 0:
        return [evaluate(s) for s in specs]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(evaluate, specs, chunksize=8))


def _dedupe(rows: list[dict]) -> list[dict]:
    seen, out = set(), []
    for r in rows:
        k = (r["kind"], r.get("seam"), r.get("offset"), r.get("s1"),
             r.get("s2"), r.get("included"), r.get("wing"),
             r.get("offsets"), r["taper"])
        if k not in seen:
            seen.add(k)
            out.append(r)
    return out


def search(workers: int | None = None) -> dict:
    """Full-resolution sweep, then local refinement of the leaders."""
    seams = np.arange(SEAM_MIN, SEAM_MAX + 1e-9, 0.000525)
    offsets = np.arange(OFFSET_MIN, OFFSET_MAX + 1e-9, 0.000525)
    seams3 = np.arange(SEAM_MIN, SEAM_MAX + 1e-9, 0.000525)

    specs: list[dict] = []
    for seam, offset, taper in itertools.product(seams, offsets,
                                                 ("uniform", "hann")):
        specs.append({"kind": "pair", "seam": float(seam),
                      "offset": float(offset), "taper": taper})
    for s1, s2, offs, taper in itertools.product(
            seams3, seams3, OFFSET_PATTERNS, ("uniform", "hann")):
        specs.append({"kind": "three", "s1": float(s1), "s2": float(s2),
                      "offsets": tuple(float(o) for o in offs),
                      "taper": taper})
    for included, taper in itertools.product(
            (90, 105, 120, 135, 150, 165), ("uniform", "hann")):
        specs.append({"kind": "v", "included": float(included),
                      "taper": taper})
    for wing, taper in itertools.product((0, 10, 20, 30),
                                         ("uniform", "hann")):
        specs.append({"kind": "concave", "wing": float(wing),
                      "taper": taper})

    # named reference points, evaluated on the same grid
    specs[:0] = [
        {"kind": "pair", "seam": C.CURRENT_SEAM_M,
         "offset": C.CURRENT_OFFSET_Y_M, "taper": "uniform",
         "label": "current pair 15.75/5.25", "key": "05_coplanar_gap"},
        {"kind": "pair", "seam": C.BUTT_SEAM_M, "offset": 0.0,
         "taper": "uniform", "label": "butted pair",
         "key": "04_coplanar_butt"},
        {"kind": "pair", "seam": C.CURRENT_SEAM_M, "offset": 0.0,
         "taper": "uniform", "label": "seam-only control",
         "key": "09_pair_seam_only"},
        {"kind": "v", "included": 150.0, "taper": "uniform",
         "label": "V 150°", "key": "02_v150"},
        {"kind": "v", "included": 120.0, "taper": "uniform",
         "label": "V 120°", "key": "03_v120"},
        {"kind": "three", "s1": C.CURRENT_SEAM_M, "s2": C.CURRENT_SEAM_M,
         "offsets": (0.0, 0.0, 0.0), "taper": "uniform",
         "label": "3-board reference", "key": "08_coplanar3"},
    ]

    rows = _dedupe(_run_pool(specs, workers))
    best_pair = best_of(rows, ("pair",))
    best_three = best_of(rows, ("three",))

    fine: list[dict] = []
    for dseam in np.arange(-0.00105, 0.00105 + 1e-9, 0.0002625):
        for doff in np.arange(-0.00105, 0.00105 + 1e-9, 0.0002625):
            for taper in ("uniform", "hann"):
                fine.append({
                    "kind": "pair",
                    "seam": float(np.clip(best_pair["seam"] + dseam,
                                          SEAM_MIN, SEAM_MAX)),
                    "offset": float(np.clip(best_pair["offset"] + doff,
                                            OFFSET_MIN, OFFSET_MAX)),
                    "taper": taper,
                })
    for ds1 in np.arange(-0.00105, 0.00105 + 1e-9, 0.0002625):
        for ds2 in np.arange(-0.00105, 0.00105 + 1e-9, 0.0002625):
            for taper in ("uniform", "hann"):
                fine.append({
                    "kind": "three",
                    "s1": float(np.clip(best_three["s1"] + ds1,
                                        SEAM_MIN, SEAM_MAX)),
                    "s2": float(np.clip(best_three["s2"] + ds2,
                                        SEAM_MIN, SEAM_MAX)),
                    "offsets": tuple(float(o) for o in
                                     best_three["offsets"].split(",")),
                    "taper": taper,
                })
    rows = _dedupe(rows + _run_pool(fine, workers))

    return {
        "rows": rows,
        "best_pair": best_of(rows, ("pair",)),
        "best_three": best_of(rows, ("three",)),
    }


def best_of(rows: list[dict], kinds: tuple[str, ...],
            ref_key: str = "05_coplanar_gap") -> dict:
    """Best candidate that does not give up directivity or beamwidth.

    Scored on the 50-60 deg band peak, tie-broken by band energy.  For a pair
    the design intent is kept: the 54.75 deg lobe must still be nulled, which
    is what the current geometry was built for.
    """
    ref = next(r for r in rows if r.get("key") == ref_key)
    subset = [
        r for r in rows
        if r["kind"] in kinds
        and r["di_db"] >= ref["di_db"] - 0.2
        and r["bw6_xz_deg"] <= ref["bw6_xz_deg"] + 0.05
    ] or [r for r in rows if r["kind"] in kinds]
    if "pair" in kinds:
        nulled = [r for r in subset if r["lobe_54_75_db"] < -60.0]
        if nulled:
            subset = nulled
    return min(subset, key=lambda r: (r["band_max_db"], r["band_energy_pct"]))


def _num(value):
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return None if number != number else number


def row_to_spec(row: dict) -> dict:
    spec = {"kind": row["kind"], "taper": row["taper"]}
    for key in ("seam", "offset", "included", "s1", "s2", "wing"):
        number = _num(row.get(key))
        if number is not None:
            spec[key] = number
    if row.get("offsets"):
        spec["offsets"] = tuple(float(v) for v in row["offsets"].split(","))
    return spec


def layout_from_row(row: dict) -> geometry.Layout:
    lay = build(row_to_spec(row))
    lay.key = "opt2" if row["kind"] in ("pair", "v") else "opt3"
    if row["kind"] == "three":
        offs = " / ".join(f"{float(v) * 1e3:.2f}" for v in
                          row["offsets"].split(","))
        detail = (f"seams {float(row['s1']) * 1e3:.2f} / "
                  f"{float(row['s2']) * 1e3:.2f} mm, y offsets {offs} mm")
    else:
        detail = (f"seam {float(row['seam']) * 1e3:.2f} mm, y offset "
                  f"{float(row['offset']) * 1e3:.2f} mm")
    lay.title = ("Optimal " + ("2" if lay.key == "opt2" else "3")
                 + "-board layout — " + detail)
    lay.notes = (
        f"Tap: {row['taper']}. Selected by lowest 50–60° band peak in the "
        "searched space, subject to DI and beamwidth no worse than the "
        "current pair. Ideal model."
    )
    return lay


def save(rows: list[dict], specs: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    fields = sorted({k for r in rows for k in r})
    with open(out_dir / "candidates.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    with open(out_dir / "best.json", "w", encoding="utf-8") as fh:
        json.dump(specs, fh, indent=2)
