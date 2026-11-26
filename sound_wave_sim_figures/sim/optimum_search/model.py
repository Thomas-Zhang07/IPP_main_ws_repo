"""Fast separable far-field model for coplanar 16 x 16 boards.

For coplanar, equal boards the field factorises (see the design doc):
``p = E(u,v) · A(kp(u−u0)/2) · A(kp(v−v0)/2) · Σ_b exp(ik[(u−u0)x_b+(v−v0)y_b])``.
The Dirichlet factor is real (the board's intra-board phase is common to all
boards and cancels in the magnitude); comparisons with the exact solver are on
magnitudes, which is what every metric uses.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

import constants as C
import field
import transducer

N_SIDE = C.N_SIDE
PITCH = C.PITCH_M
SPAN = C.SPAN_M
FULL = N_SIDE * N_SIDE
VARIANTS = ("mean", "left", "right", "wide", "asym")


@dataclass(frozen=True)
class Candidate:
    key: str
    seams_m: tuple[float, ...]
    offsets_m: tuple[float, ...]

    @property
    def n_boards(self) -> int:
        return len(self.seams_m) + 1

    @property
    def span_m(self) -> float:
        return self.n_boards * SPAN + float(sum(self.seams_m))

    @property
    def span_y_m(self) -> float:
        return float(max(self.offsets_m) - min(self.offsets_m))

    @property
    def origins(self) -> np.ndarray:
        xs = [0.0]
        for seam in self.seams_m:
            xs.append(xs[-1] + SPAN + seam)
        return np.column_stack([np.asarray(xs, float),
                                np.asarray(self.offsets_m, float)])


def pair(s_m: float, o_m: float) -> Candidate:
    s_m, o_m = float(s_m), float(o_m)
    key = f"pair_{s_m * 1e3:.3f}_{o_m * 1e3:.3f}"
    return Candidate(key, (s_m,), (0.0, o_m))


def triple(s1_m: float, s2_m: float, o2_m: float, o3_m: float) -> Candidate:
    s1, s2, o2, o3 = map(float, (s1_m, s2_m, o2_m, o3_m))
    key = (f"triple_{s1 * 1e3:.3f}_{s2 * 1e3:.3f}"
           f"_{o2 * 1e3:.3f}_{o3 * 1e3:.3f}")
    return Candidate(key, (s1, s2), (0.0, o2, o3))


def from_key(key: str) -> Candidate:
    """Rebuild a Candidate from its CSV key (values in mm)."""
    parts = key.split("_")
    try:
        if parts[0] == "pair" and len(parts) == 3:
            return pair(float(parts[1]) / 1e3, float(parts[2]) / 1e3)
        if parts[0] == "triple" and len(parts) == 5:
            return triple(float(parts[1]) / 1e3, float(parts[2]) / 1e3,
                          float(parts[3]) / 1e3, float(parts[4]) / 1e3)
    except ValueError:
        pass
    raise ValueError(f"cannot parse candidate key {key!r}")


def board_factor(q, k: float = C.WAVE_NUMBER, pitch: float = PITCH,
                 n: int = N_SIDE):
    """``sin(nβ)/sin(β)`` with β = k·pitch·q/2, safe at sin β = 0."""
    beta = 0.5 * k * pitch * np.asarray(q, dtype=float)
    scalar = beta.ndim == 0
    beta = np.atleast_1d(beta)
    sin_b = np.sin(beta)
    out = np.empty_like(beta)
    safe = np.abs(sin_b) > 1e-9
    out[safe] = np.sin(n * beta[safe]) / sin_b[safe]
    out[~safe] = n * np.cos((n - 1) * beta[~safe])
    return float(out[0]) if scalar else out


def element_amplitude(dirs, variant: str = "mean") -> np.ndarray:
    """Normalized element pressure factor for each direction."""
    dirs = np.atleast_2d(np.asarray(dirs, dtype=float))
    w = np.clip(dirs[:, 2], -1.0, 1.0)
    theta = np.degrees(np.arccos(w))
    if variant == "mean":
        level = transducer.level_db(theta)
    elif variant in ("left", "right"):
        level = transducer.level_db(theta, variant)
    elif variant == "wide":
        level = transducer.level_db(np.minimum(theta * 81.0 / 92.0, 180.0))
    elif variant == "asym":
        phi = np.arctan2(dirs[:, 1], dirs[:, 0])
        right = transducer.level_db(theta, "right")
        left = transducer.level_db(theta, "left")
        level = (np.cos(phi / 2.0) ** 2 * right
                 + np.sin(phi / 2.0) ** 2 * left)
    else:
        raise ValueError(f"unknown element variant {variant!r}")
    return 10.0 ** (np.asarray(level) / 20.0)


def array_factor(cand: Candidate, dirs, u0: float, v0: float = 0.0):
    dirs = np.atleast_2d(np.asarray(dirs, dtype=float))
    u = dirs[:, 0] - u0
    v = dirs[:, 1] - v0
    origins = cand.origins
    lat = np.exp(
        1j * C.WAVE_NUMBER
        * (u[:, None] * origins[None, :, 0] + v[:, None] * origins[None, :, 1])
    ).sum(axis=1)
    return board_factor(u) * board_factor(v) * lat


def field_fast(cand: Candidate, dirs, u0: float, v0: float = 0.0,
               variant: str = "mean"):
    return array_factor(cand, dirs, u0, v0) * element_amplitude(dirs, variant)


def commanded_amp(cand: Candidate, u0: float, v0: float = 0.0,
                  variant: str = "mean") -> float:
    w2 = 1.0 - u0 * u0 - v0 * v0
    if w2 < 0.0:
        raise ValueError("commanded direction outside the hemisphere")
    d = np.array([[u0, v0, np.sqrt(w2)]])
    return float(FULL * cand.n_boards * element_amplitude(d, variant)[0])


def direction_grid(du: float):
    U2, V2, mask, dirs, el, az, _ = field.uv_grid(du)
    return dirs, el, az, mask
