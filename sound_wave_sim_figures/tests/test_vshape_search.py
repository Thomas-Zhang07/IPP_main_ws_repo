"""Validate the fast V model against the exact solver and smoke the angle search."""

from __future__ import annotations

import pathlib
import sys

import numpy as np
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sim"))

import geometry
import steering_study as S
from optimum_search import metrics as X, model as M, vshape as V


@pytest.mark.parametrize("included", [120.0, 150.0, 180.0])
def test_fast_v_matches_exact(included):
    layout = geometry.v_pair(included, "v", "V")
    rng = np.random.default_rng(3)
    u = rng.uniform(-0.5, 0.5, 300)
    v = rng.uniform(-0.5, 0.5, 300)
    inside = u * u + v * v < 0.9
    dirs = np.column_stack([u[inside], v[inside],
                            np.sqrt(1 - u[inside] ** 2 - v[inside] ** 2)])
    u0, v0 = np.sin(np.radians(20)), np.sin(np.radians(10))
    fast = np.abs(V.field_v(layout, dirs, u0, v0))
    exact = np.abs(S.pattern(layout, dirs, u0, "measured", v0=v0))
    keep = exact > 10 ** (-40 / 20) * exact.max()
    rel = np.abs(fast[keep] - exact[keep]) / np.maximum(exact[keep], 1e-12)
    assert np.max(rel) < 1e-6


def test_v180_matches_coplanar_butt():
    flat = geometry.coplanar_butt()
    hinge = geometry.v_pair(180.0, "v180", "V180")
    dirs = np.array([[0.1, 0.05, np.sqrt(1 - 0.0125)],
                     [0.3, 0.2, np.sqrt(1 - 0.13)]])
    u0, v0 = np.sin(np.radians(20)), np.sin(np.radians(10))
    a = np.abs(V.field_v(hinge, dirs, u0, v0))
    b = np.abs(S.pattern(flat, dirs, u0, "measured", v0=v0))
    np.testing.assert_allclose(a, b, rtol=1e-6)


def test_v_is_coherent_at_command():
    layout = geometry.v_pair(120, "v", "V")
    theta, phi = 20.0, 45.0
    t, p = np.radians(theta), np.radians(phi)
    d = np.array([[np.sin(t) * np.cos(p), np.sin(t) * np.sin(p),
                   np.cos(t)]])
    field = V.field_v(layout, d, d[0, 0], d[0, 1])[0]
    expected = S.transducer.amplitude(d @ layout.normals.T).sum()
    assert abs(field) == pytest.approx(abs(expected), rel=1e-9)


def test_invalid_command_raises():
    layout = geometry.v_pair(120, "v", "V")
    with pytest.raises(ValueError):
        V.field_v(layout, np.array([[0.0, 0.0, 1.0]]), 0.9, 0.9)


def test_variants_are_finite():
    layout = geometry.v_pair(120, "v", "V")
    d = np.array([[0.1, 0.0, np.sqrt(0.99)]])
    for variant in ("mean", "left", "right", "wide"):
        assert np.isfinite(abs(V.field_v(layout, d, 0.1, 0.0, variant)[0]))
    with pytest.raises(ValueError):
        V.field_v(layout, d, 0.1, 0.0, "asym")


def test_exact_sampling_is_grid_independent():
    layout = geometry.v_pair(135.0, "v135", "V135")
    fn = V.field_fn(layout)
    states = [(0.0, 0.0), (20.0, 45.0), (35.0, 90.0)]
    vals = []
    for du in (0.012, 0.004):
        dirs, _, _, _ = M.direction_grid(du)
        vals.append(X.score_states_fn(fn, dirs, states, exact=True)["SL_cmd"])
    assert vals[0] == pytest.approx(vals[1], abs=0.05)


def test_half_pitch_offset_nulls_the_y_grating():
    import constants as C

    state_theta, state_phi = 25.0, 90.0
    t = np.radians(state_theta)
    u0, v0 = 0.0, np.sin(t)
    vg = v0 - C.WAVELENGTH_M / C.PITCH_M
    d = np.array([[0.0, vg, np.sqrt(max(0.0, 1.0 - vg * vg))]])
    d0 = np.array([[0.0, v0, np.cos(t)]])

    def level(offset_mm):
        layout = V.v_pair_offset(135.0, offset_mm / 1e3)
        fn = V.field_fn(layout)
        return 20 * np.log10(abs(fn(d, u0, v0)[0]) / abs(fn(d0, u0, v0)[0]))

    assert level(0.0) > -3.0
    assert level(5.25) < level(0.0) - 20.0


def test_search_small():
    rows, front = V.search_v(included=np.array([120.0, 150.0, 180.0]),
                             states=[(0.0, 0.0), (20.0, 45.0)],
                             du=0.04, srange_du=0.05)
    assert len(rows) == 6  # 3 angles x 2 offsets
    for row in rows:
        for key in ("SL_cmd", "SL_diag", "SRANGE_0dB", "DI0"):
            assert np.isfinite(row[key])
    assert front
