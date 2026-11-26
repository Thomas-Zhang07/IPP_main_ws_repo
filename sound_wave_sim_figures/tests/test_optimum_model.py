"""Model tests: geometry, Dirichlet factors, element variants, fast evaluator
against the exact solver, and a safe pruning bound."""

from __future__ import annotations

import pathlib
import sys

import numpy as np
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sim"))

import constants as C
import geometry
import steering_study as S
from optimum_search import model as M


def test_board_factor_limits():
    assert M.board_factor(0.0) == pytest.approx(16.0, abs=1e-9)
    assert M.board_factor(C.WAVELENGTH_M / C.PITCH_M) == pytest.approx(
        -16.0, abs=1e-6)
    for q in (-1.0, -0.5, 0.0, 0.33, 0.8166, 1.0):
        assert np.isfinite(M.board_factor(q))


def test_lattice_minimax():
    # under steering the diagonal grating directions are visible; the pair
    # nulls x and puts y/diagonals at -3.01 dB (array factor only)
    cand = M.pair(0.01575, 0.002625)
    ug = C.WAVELENGTH_M / C.PITCH_M
    u0 = v0 = -0.3
    dirs = np.array([[u0 + ug, v0, -v0], [u0, v0 + ug, -u0],
                     [u0 + ug, v0 + ug, 1.0]])
    dirs[:, 2] = np.sqrt(np.maximum(0.0, 1.0 - dirs[:, 0] ** 2
                                    - dirs[:, 1] ** 2))
    f = np.abs(M.array_factor(cand, dirs, u0, v0)) / (2 * 256)
    assert f[0] < 1e-6
    assert f[1] == pytest.approx(10 ** (-3.01 / 20), abs=2e-3)
    assert f[2] == pytest.approx(10 ** (-3.01 / 20), abs=2e-3)


def test_fast_matches_exact_with_v0():
    cand = M.triple(0.014, 0.014, 0.0035, 0.0070)
    layout = geometry.coplanar3(0.014, 0.014, (0.0, 0.0035, 0.0070),
                                key="t", title="t")
    rng = np.random.default_rng(1)
    u = rng.uniform(-0.6, 0.6, 400)
    v = rng.uniform(-0.6, 0.6, 400)
    inside = u * u + v * v < 0.95
    dirs = np.column_stack([u[inside], v[inside],
                            np.sqrt(1 - u[inside] ** 2 - v[inside] ** 2)])
    u0, v0 = np.sin(np.radians(20)), np.sin(np.radians(10))
    fast = np.abs(M.field_fast(cand, dirs, u0, v0, "mean"))
    exact = np.abs(S.pattern(layout, dirs, u0, "measured", v0=v0))
    keep = exact > 10 ** (-40 / 20) * exact.max()
    rel = np.abs(fast[keep] - exact[keep]) / np.maximum(exact[keep], 1e-12)
    assert np.max(rel) < 1e-3
