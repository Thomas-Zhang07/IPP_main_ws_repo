"""Measured element directivity for the TR4010HC ultrasonic transducer.

Digitized from the only available source, the photographed datasheet polar
chart (``transducers.jpg``; see ``digitize.py``).  Levels are relative to the
on-axis response and already carry the part's left/right asymmetry.  The
intended use is a drop-in replacement for the ideal piston factor in the
far-field model: multiply every element's contribution by
``amplitude(cos_beta)`` evaluated against that element's own axis.

Directivity convention is the standard 4 pi one::

    Q = 2 / int_0^pi P(theta) sin(theta) dtheta,   DI = 10 log10 Q

with ``P`` the normalized power pattern (0 dB on axis).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

DATA_PATH = Path(__file__).with_name("directivity.csv")
SOURCE = "transducers.jpg - TR4010HC series polar chart, 40.0 kHz"
HALVES = ("left", "right", "mean")

_data = None


def load(path: Path | str = DATA_PATH):
    """Read ``directivity.csv``; returns ``(angles, right, left, mean)``."""
    tab = np.genfromtxt(Path(path), delimiter=",", names=True)
    return (tab["angle_deg"], tab["db_right"], tab["db_left"],
            tab["db_mean_power"])


def _arrays():
    global _data
    if _data is None:
        _data = load()
    return _data


def level_db(theta_deg, half: str = "mean"):
    """Relative level in dB at an angle (deg) from the element's axis."""
    if half not in HALVES:
        raise ValueError(f"half must be one of {HALVES}")
    angles, db_right, db_left, db_mean = _arrays()
    curve = {"right": db_right, "left": db_left, "mean": db_mean}[half]
    theta = np.asarray(theta_deg, dtype=float)
    if np.any(theta < 0.0) or np.any(theta > 180.0):
        raise ValueError("theta_deg must lie in [0, 180]")
    return np.interp(theta, angles, curve)


def amplitude(cos_beta):
    """Normalized pressure factor, 1.0 on axis; ``cos_beta`` is clipped."""
    cos_beta = np.clip(np.asarray(cos_beta, dtype=float), -1.0, 1.0)
    theta = np.degrees(np.arccos(cos_beta))
    return 10.0 ** (level_db(theta, "mean") / 20.0)


def q() -> float:
    """Directivity factor over the full sphere (4 pi)."""
    angles, _, _, db_mean = _arrays()
    th = np.radians(angles)
    power = 10.0 ** (db_mean / 10.0)
    return float(2.0 / np.trapezoid(power * np.sin(th), th))


def di_db() -> float:
    """Directivity index in dB, 10 log10 Q."""
    return float(10.0 * np.log10(q()))


def half_angle_6db(half: str) -> float:
    """Angle (deg) where one half of the measured cut first falls to -6 dB."""
    if half not in ("left", "right"):
        raise ValueError("half must be 'left' or 'right'")
    angles, db_right, db_left, _ = _arrays()
    curve = db_right if half == "right" else db_left
    below = np.flatnonzero(curve <= -6.0)
    if below.size == 0:
        raise ValueError("no -6 dB crossing in the cut")
    return float(angles[below[0]])


def beamwidth_6db() -> float:
    """Full -6 dB beamwidth as the sum of the two measured half-angles."""
    return half_angle_6db("left") + half_angle_6db("right")


DI_DB = di_db()
