"""Disk cache for the expensive field computations.

Far-field analysis and near-field planes are keyed by the actual emitter
positions plus the grid settings, so a page or figure rebuild after a
presentation-only change takes seconds instead of minutes.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np

import field
import render_png

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "cache"

_SCALARS = ("peak", "on_axis_db", "lobe_54_75_db", "band_max_db",
            "band_energy_pct", "leak_60_pct", "peak_sidelobe_db",
            "bw6_xz_deg", "bw6_yz_deg", "di_db", "peak_el_deg",
            "peak_az_deg", "du")
_ARRAYS = ("db", "U", "V", "mask", "el", "az")
_NEAR_SCALARS = ("peak", "ymid", "z_plane")


def _sig(layout) -> str:
    payload = (np.ascontiguousarray(layout.positions, dtype=float).tobytes()
               + np.ascontiguousarray(layout.normals, dtype=float).tobytes())
    digest = hashlib.md5(payload).hexdigest()[:12]
    return f"{layout.key}_{digest}"


def _ensure():
    CACHE.mkdir(parents=True, exist_ok=True)


def analysis(layout, du: float = 0.004, taper: str = "uniform") -> dict:
    _ensure()
    path = CACHE / f"analysis_v2_{_sig(layout)}_{taper}_{du:.4f}.npz"
    if path.exists():
        with np.load(path) as z:
            m = {k: float(z[k]) for k in _SCALARS}
            m.update({k: z[k] for k in _ARRAYS})
            m["lobe_by_az_db"] = {
                str(k): float(v)
                for k, v in zip(z["lobe_keys"], z["lobe_vals"])
            }
        return m

    m = field.analyse(layout.positions, layout.normals,
                      layout.amplitudes(taper), du=du)
    lobe = m["lobe_by_az_db"]
    np.savez_compressed(
        path,
        **{k: np.asarray(m[k]) for k in _ARRAYS},
        **{k: np.asarray(m[k]) for k in _SCALARS},
        lobe_keys=np.array(list(lobe.keys())),
        lobe_vals=np.array(list(lobe.values())),
    )
    return m


def near(layout, res: float = 0.005, taper: str = "uniform") -> dict:
    _ensure()
    path = CACHE / f"near_{_sig(layout)}_{taper}_{res:.4f}.npz"
    if path.exists():
        with np.load(path) as z:
            d = {k: z[k] for k in z.files}
        for k in _NEAR_SCALARS:
            d[k] = float(d[k])
        return d

    d = render_png.near_field_arrays(layout, taper=taper, res=res)
    np.savez_compressed(path, **{k: np.asarray(v) for k, v in d.items()})
    return d
