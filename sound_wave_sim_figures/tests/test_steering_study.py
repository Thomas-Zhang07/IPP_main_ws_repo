"""Steering-study checks: the grating-lobe algebra and the two element models
must reproduce the values established by the investigation."""

from __future__ import annotations

import pathlib
import sys

import numpy as np
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sim"))

import geometry  # noqa: E402
import steering_study as S  # noqa: E402


def _dir(theta_deg: float):
    t = np.radians(theta_deg)
    return np.array([[np.sin(t), 0.0, np.cos(t)]])


def _level(layout, u0, element, theta_a, theta_b):
    a = abs(S.pattern(layout, _dir(theta_a), u0, element)[0])
    b = abs(S.pattern(layout, _dir(theta_b), u0, element)[0])
    return 20.0 * np.log10(a / b)


def test_grating_angle_formula():
    assert S.grating_deg(0) == pytest.approx(-54.75, abs=0.05)
    assert S.grating_deg(30) == pytest.approx(-18.5, abs=0.2)
    assert S.grating_deg(70) == pytest.approx(7.1, abs=0.2)


def test_isotropic_grating_equals_main():
    layout = geometry.single()
    assert _level(layout, 0.0, "isotropic", 54.75, 0.0) == pytest.approx(
        0.0, abs=0.05)
    u0 = S.steer_u0(30.0)
    assert _level(layout, u0, "isotropic", -18.5, 30.0) == pytest.approx(
        0.0, abs=0.05)


def test_measured_grating_at_broadside():
    layout = geometry.single()
    assert _level(layout, 0.0, "measured", 54.75, 0.0) == pytest.approx(
        -28.2, abs=1.5)


def test_measured_grating_at_steer20():
    layout = geometry.single()
    u0 = S.steer_u0(20.0)
    assert _level(layout, u0, "measured", -28.3, 20.0) == pytest.approx(
        -1.0, abs=1.5)


def test_main_peak_at_steer_angle():
    layout = geometry.single()
    alpha, mag = S.cut_x(layout, S.steer_u0(30.0), "measured")
    sel = np.abs(alpha - 30.0) <= 5.0
    peak = alpha[sel][int(np.argmax(mag[sel]))]
    assert peak == pytest.approx(30.0, abs=0.6)


def test_steering_plots_and_table_share_one_peak(monkeypatch):
    monkeypatch.setattr(S, "SETUPS", (("one", "single", geometry.single),))
    monkeypatch.setattr(S, "ELEMENTS", ("isotropic",))
    monkeypatch.setattr(S, "STEERS", np.array([30]))
    monkeypatch.setattr(S, "DU", 0.12)  # misses the command and grating orders
    results, rows = S.study()
    result = results["one", "isotropic", 30.0]
    assert rows[0]["main_level_db"] == pytest.approx(0, abs=1e-8)
    assert rows[0]["sidelobe_level_db"] == pytest.approx(0, abs=0.01)
    for view in ("db2", "cut_db", "surface_db"):
        assert np.nanmax(result[view]) <= 1e-10
    assert np.nanmax(result["db2"]) < -0.01


def test_vectorized_commands_match_direct_sum():
    layout = geometry.v_pair(120, "v", "V")
    dirs = np.vstack([_dir(t) for t in (-40, 0, 28)])
    u, v = np.array([0, 0.31]), np.array([0.21, -0.14])
    fields = S._patterns(layout, dirs, u, v, S.ELEMENTS)
    for i in range(len(u)):
        phase = (dirs - [u[i], v[i], np.sqrt(1-u[i]**2-v[i]**2)]) @ layout.positions.T
        waves = np.exp(1j * S.C.WAVE_NUMBER * phase)
        for kind in S.ELEMENTS:
            e = S.transducer.amplitude(dirs @ layout.normals.T) if kind == "measured" else 1
            np.testing.assert_allclose(fields[kind][:, i], (e * waves).sum(axis=1), atol=1e-10)


@pytest.mark.parametrize("included", [120, 150])
@pytest.mark.parametrize("theta,phi", [(0, 0), (20, 0), (35, 45)])
def test_v_board_coherence_at_command(included, theta, phi):
    layout = geometry.v_pair(included, "v", "V")
    d = S.field.dir_from_angles(theta, phi)[None, :]
    u, v = d[0, :2]
    measured = S.pattern(layout, d, u, "measured", v0=v)[0]
    np.testing.assert_allclose(measured, S.transducer.amplitude(d @ layout.normals.T).sum(),
                               atol=1e-9)
    assert abs(S.pattern(layout, d, u, "isotropic", v0=v)[0]) == pytest.approx(512)
    projected = S.pattern(layout, d, u, "isotropic", v0=v, phase_law="projected_xy")
    reference = np.exp(1j * S.C.WAVE_NUMBER * layout.positions[:, 2] * d[0, 2]).sum()
    np.testing.assert_allclose(projected[0], reference, atol=1e-9)
    assert abs(projected[0]) < 512


def test_depth_compensation_does_not_change_flat_board():
    flat = geometry.coplanar_gap()
    dirs = np.vstack([_dir(t) for t in (-50, 0, 19)])
    args = (flat, dirs, 0.33, "measured")
    np.testing.assert_allclose(S.pattern(*args), S.pattern(*args, phase_law="projected_xy"))


@pytest.mark.parametrize("angle,spread,loss", [(120, 6.785, -7.65), (150, 7.885, -10.47)])
def test_v_microphone_observes_curvature_without_changing_drive(angle, spread, loss):
    layout = geometry.v_pair(angle, "v", "V")
    reading = S.v_microphone_check(layout)
    assert reading["curvature_spread_mm"] == pytest.approx(spread, abs=0.002)
    assert reading["level_re_coherent_bound_db"] == pytest.approx(loss, abs=0.02)
    distant = S.v_microphone_check(layout, 200)
    assert distant["level_re_coherent_bound_db"] == pytest.approx(0, abs=0.003)
