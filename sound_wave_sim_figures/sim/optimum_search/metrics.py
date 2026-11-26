"""Scoring rubrics for the optimal search.

All levels are relative to the commanded-direction level. The main-lobe mask
is geodesic (angle from the commanded direction), 4 degrees; `SL_near` covers
4-15 degrees and `SL_far` beyond 15.
"""

from __future__ import annotations

import numpy as np

import constants as C

from . import model

MASK_DEG = 4.0
NEAR_MAX_DEG = 15.0
CLEAN_MAX_DEG = 24.1
DIAGONAL_AZIMUTHS = (45.0, 135.0, 225.0, 315.0)


def _direction(theta_deg, phi_deg):
    t, p = np.radians(theta_deg), np.radians(phi_deg)
    return np.array([np.sin(t) * np.cos(p), np.sin(t) * np.sin(p), np.cos(t)])


def _angles_to(dirs, d0):
    d0 = np.asarray(d0, float)
    d0 = d0 / np.linalg.norm(d0)
    return np.degrees(np.arccos(np.clip(dirs @ d0, -1.0, 1.0)))


def sl_components(mag, dirs, d0, cmd_amp, mask_deg=MASK_DEG):
    ang = _angles_to(dirs, d0)
    outside = ang > mask_deg
    near = outside & (ang <= NEAR_MAX_DEG)
    far = ang > NEAR_MAX_DEG

    def level(sel):
        if not sel.any():
            return float("-inf")
        return 20.0 * np.log10(
            max(float(np.max(mag[sel])), 1e-12) / max(cmd_amp, 1e-12))

    return {"sl_cmd": level(outside), "sl_near": level(near),
            "sl_far": level(far)}


def _values_fn(field_fn, dirs, theta_deg, phi_deg, exact=False, step=0.004):
    t, p = np.radians(theta_deg), np.radians(phi_deg)
    u0, v0 = np.sin(t) * np.cos(p), np.sin(t) * np.sin(p)
    d0 = _direction(theta_deg, phi_deg)
    base = np.abs(field_fn(dirs, u0, v0))
    mag = base
    eval_dirs = dirs
    if exact:
        # A coarse grid can miss narrow grating lobes, the broadside line and
        # the peak of a narrow sidelobe. Evaluate those explicitly, then
        # refine locally around the strongest outside-mask grid point.
        grating = C.WAVELENGTH_M / C.PITCH_M
        extra = [[0.0, 0.0, 1.0]]
        for du, dv in ((grating, 0.0), (-grating, 0.0),
                       (0.0, grating), (0.0, -grating)):
            u, v = u0 + du, v0 + dv
            r2 = u * u + v * v
            if r2 <= 1.0:
                extra.append([u, v, np.sqrt(max(0.0, 1.0 - r2))])
        ang = _angles_to(dirs, d0)
        outside = ang > MASK_DEG
        if outside.any():
            idx = np.flatnonzero(outside)[int(np.argmax(base[outside]))]
            cu, cv = dirs[idx, 0], dirs[idx, 1]
            span = max(float(step), 0.002)
            grid = np.linspace(-span, span, 9)
            LU, LV = np.meshgrid(cu + grid, cv + grid, indexing="xy")
            ok = LU ** 2 + LV ** 2 <= 1.0
            lu, lv = LU[ok], LV[ok]
            extra += np.column_stack(
                [lu, lv, np.sqrt(np.maximum(0.0, 1.0 - lu ** 2 - lv ** 2))]
            ).tolist()
        extra = np.asarray(extra, dtype=float)
        eval_dirs = np.vstack([dirs, extra])
        mag = np.concatenate([base, np.abs(field_fn(extra, u0, v0))])
    cmd = abs(field_fn(d0[None, :], u0, v0)[0])
    return sl_components(mag, eval_dirs, d0, cmd)


def _state_values(cand, dirs, theta_deg, phi_deg, variant):
    return _values_fn(
        lambda d, u, v: model.field_fast(cand, d, u, v, variant),
        dirs, theta_deg, phi_deg)


def score_states_fn(field_fn, dirs, states, exact=False, step=0.004) -> dict:
    worst = {"SL_cmd": -np.inf, "SL_clean": -np.inf, "SL_near": -np.inf,
             "SL_far_s": -np.inf, "SL_diag": -np.inf}
    for theta, phi in states:
        comp = _values_fn(field_fn, dirs, theta, phi, exact, step)
        worst["SL_cmd"] = max(worst["SL_cmd"], comp["sl_cmd"])
        worst["SL_near"] = max(worst["SL_near"], comp["sl_near"])
        worst["SL_far_s"] = max(worst["SL_far_s"], comp["sl_far"])
        if theta <= CLEAN_MAX_DEG:
            worst["SL_clean"] = max(worst["SL_clean"], comp["sl_cmd"])
        if float(phi) % 360.0 in DIAGONAL_AZIMUTHS:
            worst["SL_diag"] = max(worst["SL_diag"], comp["sl_cmd"])
    return {k: float(v) for k, v in worst.items()}


def score_states(cand, du: float, states, variant: str = "mean",
                 dirs=None, exact: bool = False) -> dict:
    if dirs is None:
        dirs, _, _, _ = model.direction_grid(du)
    return score_states_fn(
        lambda d, u, v: model.field_fast(cand, d, u, v, variant), dirs, states,
        exact)


def _contiguous(curve: dict, threshold: float) -> float:
    """Largest contiguous theta from 0 whose value stays <= threshold."""
    out = 0.0
    for theta in sorted(curve):
        if curve[theta] <= threshold:
            out = float(theta)
        else:
            break
    return out


def srange_fn(field_fn, azimuths_deg, step_deg: float = 1.0,
              thresholds=(0.0, -3.0), du: float = 0.012, dirs=None,
              exact=False) -> dict:
    if dirs is None:
        dirs, _, _, _ = model.direction_grid(du)
    thetas = np.arange(0.0, 70.0 + step_deg / 2.0, step_deg)
    curves = {phi: {} for phi in azimuths_deg}
    for phi in azimuths_deg:
        for theta in thetas:
            comp = _values_fn(field_fn, dirs, float(theta), float(phi),
                              exact, du)
            curves[phi][float(theta)] = comp["sl_cmd"]
    out = {}
    for thr in thresholds:
        per_az = [_contiguous(curves[phi], thr) for phi in azimuths_deg]
        out[thr] = float(np.min(per_az))
    return out


def srange(cand, azimuths_deg, variant: str = "mean", step_deg: float = 1.0,
           thresholds=(0.0, -3.0), du: float = 0.012, dirs=None) -> dict:
    return srange_fn(
        lambda d, u, v: model.field_fast(cand, d, u, v, variant),
        azimuths_deg, step_deg, thresholds, du, dirs)


def _power_quad_fn(field_fn, ct_lo, ct_hi, n_ct=128, n_phi=256):
    x, w = np.polynomial.legendre.leggauss(n_ct)
    ct = 0.5 * (ct_hi - ct_lo) * x + 0.5 * (ct_hi + ct_lo)
    wct = 0.5 * (ct_hi - ct_lo) * w
    phis = np.linspace(0.0, 2.0 * np.pi, n_phi, endpoint=False)
    dphi = 2.0 * np.pi / n_phi
    CT, PH = np.meshgrid(ct, phis, indexing="ij")
    st = np.sqrt(np.maximum(0.0, 1.0 - CT * CT))
    dirs = np.column_stack([st.ravel() * np.cos(PH).ravel(),
                            st.ravel() * np.sin(PH).ravel(), CT.ravel()])
    weights = (np.repeat(wct[:, None], n_phi, axis=1) * dphi).ravel()
    p = np.abs(field_fn(dirs, 0.0, 0.0)) ** 2
    return float(np.sum(p * weights))


def _power_quad(cand, variant, ct_lo, ct_hi, n_ct=128, n_phi=256):
    return _power_quad_fn(
        lambda d, u, v: model.field_fast(cand, d, u, v, variant),
        ct_lo, ct_hi, n_ct, n_phi)


def _forward_power_fn(field_fn, ct_range=(0.0, 1.0)):
    """Forward power with the < 1 deg main lobe on its own quadrature."""
    a, b = ct_range
    split = float(np.cos(np.radians(5.0)))
    total = 0.0
    if a < split:
        total += _power_quad_fn(field_fn, a, min(b, split),
                                n_ct=160, n_phi=256)
    if b > split:
        total += _power_quad_fn(field_fn, max(a, split), b,
                                n_ct=96, n_phi=256)
    return total


def _forward_power(cand, variant, ct_range=(0.0, 1.0)):
    return _forward_power_fn(
        lambda d, u, v: model.field_fast(cand, d, u, v, variant), ct_range)


def di0_fn(field_fn, fine: bool = False) -> float:
    peak = abs(field_fn(np.array([[0.0, 0.0, 1.0]]), 0.0, 0.0)[0]) ** 2
    if fine:
        split = float(np.cos(np.radians(5.0)))
        total = (_power_quad_fn(field_fn, 0.0, split,
                                n_ct=192, n_phi=384)
                 + _power_quad_fn(field_fn, split, 1.0,
                                  n_ct=192, n_phi=384))
    else:
        total = _forward_power_fn(field_fn)
    return float(10.0 * np.log10(4.0 * np.pi * peak / total))


def di0(cand, variant: str = "mean", fine: bool = False) -> float:
    return di0_fn(
        lambda d, u, v: model.field_fast(cand, d, u, v, variant), fine)


def bne0(cand, variant: str = "mean") -> float:
    total = _forward_power(cand, variant)
    band = _forward_power(cand, variant,
                          ct_range=(np.cos(np.radians(60.0)),
                                    np.cos(np.radians(50.0))))
    return float(100.0 * band / total)


def report_metrics(cand, variant: str = "mean", du: float = 0.008) -> dict:
    """R1 metrics for the report table."""
    dirs, _, _, _ = model.direction_grid(du)
    mag = np.abs(model.field_fast(cand, dirs, 0.0, 0.0, variant))
    cmd = model.commanded_amp(cand, 0.0, 0.0, variant)
    d0 = np.array([0.0, 0.0, 1.0])
    comp = sl_components(mag, dirs, d0, cmd)
    ang = _angles_to(dirs, d0)
    shoulder_sel = (ang > 2.5) & (ang <= MASK_DEG)
    shoulder = (20.0 * np.log10(max(float(np.max(mag[shoulder_sel])), 1e-12)
                                / cmd) if shoulder_sel.any() else float("nan"))
    return {
        "DI0": di0(cand, variant),
        "BNE0": bne0(cand, variant),
        "N54": n54(cand, variant),
        "SL_near0": comp["sl_near"],
        "SL_far0": comp["sl_far"],
        "SL_shoulder0": float(shoulder),
    }


def n54(cand, variant: str = "mean") -> float:
    thetas = np.linspace(52.75, 56.75, 9)
    phis = np.array([0.0, 90.0, 180.0, 270.0])
    cmd = model.commanded_amp(cand, 0.0, 0.0, variant)
    worst = -np.inf
    for phi0 in phis:
        patch = [_direction(theta, phi0 + dphi)
                 for theta in thetas for dphi in np.linspace(-2.0, 2.0, 9)]
        mag = np.abs(model.field_fast(cand, np.array(patch), 0.0, 0.0,
                                      variant))
        worst = max(worst, 20.0 * np.log10(max(mag.max(), 1e-12) / cmd))
    return float(max(worst, -60.0))
