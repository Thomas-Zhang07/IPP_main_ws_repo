"""Metric tests: the mask catches the first sidelobe, the commanded level is
geometry-independent, SRANGE is contiguous, and the integral metrics are sane."""

from __future__ import annotations

import pathlib
import sys

import numpy as np
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sim"))

import constants as C
from optimum_search import model as M, metrics as X


def test_first_sidelobe_is_captured():
    cand = M.pair(C.CURRENT_SEAM_M, 0.0)
    dirs, _, _, _ = M.direction_grid(0.004)
    mag = np.abs(M.field_fast(cand, dirs, 0.0, 0.0))
    d0 = np.array([0.0, 0.0, 1.0])
    comp = X.sl_components(mag, dirs, d0, M.commanded_amp(cand, 0, 0))
    assert comp["sl_near"] == pytest.approx(-13.1, abs=0.8)


def test_fixed_mask_excludes_the_first_x_sidelobe_on_the_current_pair():
    cand = M.pair(C.CURRENT_SEAM_M, 0.00525)
    t = np.arange(0, 8, 0.005)
    a = np.radians(t)
    dirs = np.column_stack([np.sin(a), np.zeros_like(a), np.cos(a)])
    p = np.abs(M.field_fast(cand, dirs, 0, 0))
    peaks = np.flatnonzero((p[1:-1] > p[:-2]) & (p[1:-1] > p[2:])) + 1
    first = peaks[0]
    assert t[first] == pytest.approx(2.06, abs=0.02)
    assert t[first] < X.MASK_DEG
    assert 20 * np.log10(p[first] / p[0]) == pytest.approx(-12.48, abs=0.05)


def test_commanded_level_is_geometry_independent():
    a = M.commanded_amp(M.pair(0.01575, 0.00525), np.sin(np.radians(20)), 0.0)
    b = M.commanded_amp(M.pair(0.01575, 0.0), np.sin(np.radians(20)), 0.0)
    assert a == pytest.approx(b, rel=1e-12)


def test_srange_contiguity():
    curve = {0: -30.0, 5: -20.0, 10: -2.0, 15: -20.0, 20: -1.0}
    assert X._contiguous(curve, threshold=-3.0) == 5.0


def test_di0_range():
    cand = M.pair(0.01575, 0.00525)
    assert 38.5 < X.di0(cand) < 40.5


def test_di0_convergence():
    cand = M.pair(0.016, 0.00525)
    assert X.di0(cand) == pytest.approx(X.di0(cand, fine=True), abs=0.1)


def test_n54_patch():
    cand = M.pair(0.016, 0.00525)
    assert X.n54(cand) == pytest.approx(-28.8, abs=1.5)


def test_score_states_keys():
    cand = M.pair(0.01575, 0.00525)
    states = [(0, 0), (20, 0), (20, 45), (35, 225)]
    out = X.score_states(cand, 0.01, states)
    for key in ("SL_cmd", "SL_clean", "SL_near", "SL_far_s", "SL_diag"):
        assert key in out
    assert out["SL_diag"] >= out["SL_clean"]
