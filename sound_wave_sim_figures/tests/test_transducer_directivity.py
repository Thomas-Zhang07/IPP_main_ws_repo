"""Loader tests: the package must expose the digitized directivity and the
derived gain, with the verified numbers and the documented conventions."""

from __future__ import annotations

import pathlib
import sys

import numpy as np
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sim"))

import transducer  # noqa: E402
from transducer import directivity as tr  # noqa: E402


def test_public_api():
    for name in ("level_db", "amplitude", "di_db", "q",
                 "half_angle_6db", "beamwidth_6db", "DI_DB"):
        assert hasattr(transducer, name)


def test_on_axis():
    assert tr.level_db(0.0) == pytest.approx(0.0, abs=0.05)
    assert tr.amplitude(1.0) == pytest.approx(1.0, abs=1e-6)


def test_di_and_q():
    assert tr.di_db() == pytest.approx(11.2, abs=0.6)
    assert tr.q() == pytest.approx(10 ** (tr.di_db() / 10.0), rel=1e-6)
    assert tr.DI_DB == pytest.approx(tr.di_db(), rel=1e-9)


def test_beamwidth():
    right = tr.half_angle_6db("right")
    left = tr.half_angle_6db("left")
    assert 38.5 <= right <= 43.5
    assert 41.0 <= left <= 45.0
    assert tr.beamwidth_6db() == pytest.approx(left + right, rel=1e-9)


def test_asymmetry_is_kept():
    assert tr.level_db(45.0, "left") - tr.level_db(45.0, "right") > 3.0


def test_amplitude_clips_outside_unit_range():
    clipped = tr.amplitude(np.array([-1.5, 1.5]))
    exact = tr.amplitude(np.array([-1.0, 1.0]))
    assert np.allclose(clipped, exact)
    assert np.all(np.isfinite(clipped))


def test_angle_out_of_range_raises():
    with pytest.raises(ValueError):
        tr.level_db(200.0)


def test_rear_is_not_zero():
    assert tr.level_db(180.0) < -30.0
