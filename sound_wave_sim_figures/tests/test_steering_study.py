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
