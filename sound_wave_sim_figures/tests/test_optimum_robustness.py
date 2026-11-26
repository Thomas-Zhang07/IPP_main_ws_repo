"""Robustness tests: quantisation at broadside equals the continuous case,
the mechanical corner is finite, and the envelope bound holds."""

from __future__ import annotations

import pathlib
import sys

import numpy as np
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sim"))

from optimum_search import metrics as X, model as M, robustness as R


def test_4bit_broadside_equals_continuous():
    cand = M.pair(0.01575, 0.00525)
    nominal = X.score_states(cand, 0.012, [(0.0, 0.0)])["SL_cmd"]
    assert R.sl_4bit(cand, [(0.0, 0.0)], n_offsets=1) == pytest.approx(
        nominal, abs=0.15)


def test_4bit_steered_is_finite():
    cand = M.pair(0.01575, 0.00525)
    value = R.sl_4bit(cand, [(20.0, 0.0)], n_offsets=1)
    assert np.isfinite(value) and value > -20.0


def test_mech_is_finite():
    cand = M.pair(0.01575, 0.00525)
    assert np.isfinite(R.sl_mech(cand, [(20.0, 0.0)], n_draws=2))


def test_drift_is_sane():
    cand = M.pair(0.01575, 0.00525)
    value = R.sl_drift(cand, [(20.0, 0.0), (35.0, 45.0)])
    assert np.isfinite(value) and -20.0 < value < 10.0


def test_elem_envelope_ordering():
    cand = M.pair(0.01575, 0.00525)
    out = R.robust(cand, [(0.0, 0.0), (20.0, 0.0)], n_draws=2)
    assert out["robust_max"] >= max(out["SL_4bit"], out["SL_mech"],
                                    out["SL_drift"], out["SL_elem"])
