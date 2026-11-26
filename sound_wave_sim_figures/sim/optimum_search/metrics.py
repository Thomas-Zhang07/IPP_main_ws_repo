"""Scoring rubrics for the optimal search.

All levels are relative to the commanded-direction level. The main-lobe mask
is geodesic (angle from the commanded direction), 4 degrees; `SL_near` covers
4-15 degrees and `SL_far` beyond 15.
"""

from __future__ import annotations

import numpy as np

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


def _state_values(cand, dirs, theta_deg, phi_deg, variant):
    t, p = np.radians(theta_deg), np.radians(phi_deg)
    u0, v0 = np.sin(t) * np.cos(p), np.sin(t) * np.sin(p)
    mag = np.abs(model.field_fast(cand, dirs, u0, v0, variant))
    cmd = model.commanded_amp(cand, u0, v0, variant)
    comp = sl_components(mag, dirs, _direction(theta_deg, phi_deg), cmd)
    return comp


def score_states(cand, du: float, states, variant: str = "mean",
                 dirs=None) -> dict:
    if dirs is None:
        dirs, _, _, _ = model.direction_grid(du)
    worst = {"SL_cmd": -np.inf, "SL_clean": -np.inf, "SL_near": -np.inf,
             "SL_far_s": -np.inf, "SL_diag": -np.inf}
    for theta, phi in states:
        comp = _state_values(cand, dirs, theta, phi, variant)
        worst["SL_cmd"] = max(worst["SL_cmd"], comp["sl_cmd"])
        worst["SL_near"] = max(worst["SL_near"], comp["sl_near"])
        worst["SL_far_s"] = max(worst["SL_far_s"], comp["sl_far"])
        if theta <= CLEAN_MAX_DEG:
            worst["SL_clean"] = max(worst["SL_clean"], comp["sl_cmd"])
        if float(phi) % 360.0 in DIAGONAL_AZIMUTHS:
            worst["SL_diag"] = max(worst["SL_diag"], comp["sl_cmd"])
    return {k: float(v) for k, v in worst.items()}


def _contiguous(curve: dict, threshold: float) -> float:
    """Largest contiguous theta from 0 whose value stays <= threshold."""
    out = 0.0
    for theta in sorted(curve):
        if curve[theta] <= threshold:
            out = float(theta)
        else:
            break
    return out


def srange(cand, azimuths_deg, variant: str = "mean", step_deg: float = 1.0,
           thresholds=(0.0, -3.0), du: float = 0.012, dirs=None) -> dict:
    if dirs is None:
        dirs, _, _, _ = model.direction_grid(du)
    thetas = np.arange(0.0, 70.0 + step_deg / 2.0, step_deg)
    curves = {phi: {} for phi in azimuths_deg}
    for phi in azimuths_deg:
        for theta in thetas:
            comp = _state_values(cand, dirs, float(theta), float(phi), variant)
            curves[phi][float(theta)] = comp["sl_cmd"]
    out = {}
    for thr in thresholds:
        per_az = [_contiguous(curves[phi], thr) for phi in azimuths_deg]
        out[thr] = float(np.min(per_az))
    return out


def _power_quad(cand, variant, ct_lo, ct_hi, n_ct=128, n_phi=256):
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
    p = np.abs(model.field_fast(cand, dirs, 0.0, 0.0, variant)) ** 2
    return float(np.sum(p * weights))


def _forward_power(cand, variant, ct_range=(0.0, 1.0)):
    """Forward power with the < 1 deg main lobe on its own quadrature."""
    a, b = ct_range
    split = float(np.cos(np.radians(5.0)))
    total = 0.0
    if a < split:
        total += _power_quad(cand, variant, a, min(b, split),
                             n_ct=160, n_phi=256)
    if b > split:
        total += _power_quad(cand, variant, max(a, split), b,
                             n_ct=96, n_phi=256)
    return total


def di0(cand, variant: str = "mean", fine: bool = False) -> float:
    peak = abs(model.field_fast(cand, np.array([[0.0, 0.0, 1.0]]),
                                0.0, 0.0, variant)[0]) ** 2
    if fine:
        split = float(np.cos(np.radians(5.0)))
        total = (_power_quad(cand, variant, 0.0, split,
                             n_ct=192, n_phi=384)
                 + _power_quad(cand, variant, split, 1.0,
                               n_ct=192, n_phi=384))
    else:
        total = _forward_power(cand, variant)
    return float(10.0 * np.log10(4.0 * np.pi * peak / total))


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
