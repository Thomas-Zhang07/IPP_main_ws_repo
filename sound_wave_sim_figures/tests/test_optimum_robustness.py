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


def test_placement_error_uses_nominal_drive_phases():
    cand = M.pair(0.01575, 0.00525)
    nominal = R._positions(cand)
    offsets = np.array([[0, 0], [0.0002, -0.0002]])
    actual = nominal + np.repeat(offsets, M.FULL, axis=0)
    d0 = R._commanded_dir(0.31, -0.2)
    dirs = np.array([d0, [0, 0, 1], R._commanded_dir(-0.5, 0.2)])
    gains, phases = np.array([1, 0.9]), np.array([0, 0.12])
    weights = np.repeat(gains * np.exp(1j * phases), M.FULL)
    phase = dirs[:, :2] @ actual.T - nominal @ d0[:2]
    exact = (np.exp(1j * R.C.WAVE_NUMBER * phase) @ weights) * M.element_amplitude(dirs)
    fast = R._board_field(cand, dirs, *d0[:2], "mean", cand.origins + offsets,
                          gains, phases)
    np.testing.assert_allclose(np.abs(fast), np.abs(exact), rtol=1e-10)


def test_latin_hypercube_stratifies_dimensions_independently():
    n = 32
    draw = R._lhs(np.random.default_rng(1), n, 4, 0, 1)
    ranks = (n * draw).astype(int).T
    for col in ranks:
        np.testing.assert_array_equal(np.sort(col), np.arange(n))
    assert len(np.unique(ranks, axis=0)) == len(ranks)


def test_drift_is_sane():
    cand = M.pair(0.01575, 0.00525)
    value = R.sl_drift(cand, [(20.0, 0.0), (35.0, 45.0)])
    assert np.isfinite(value) and -20.0 < value < 10.0


def test_elem_envelope_ordering():
    cand = M.pair(0.01575, 0.00525)
    out = R.robust(cand, [(0.0, 0.0), (20.0, 0.0)], n_draws=2)
    assert out["robust_max"] >= max(out["SL_4bit"], out["SL_mech"],
                                    out["SL_drift"], out["SL_elem"])
