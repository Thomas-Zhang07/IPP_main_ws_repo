"""Far-field and near-field pressure models for arbitrary board layouts.

Every emitter is a baffled circular piston (10 mm) driven at uniform phase;
the pressure is the coherent sum of the piston fields, with each element's
own board normal used for its directivity. The array near field uses spherical
propagation from point elements with far-field piston directivity; it does not
resolve the pressure distribution across an individual transducer face.
"""

from __future__ import annotations

import math

import numpy as np

import constants as C


# ---------------------------------------------------------------------------
# element directivity

def _bessel_j1(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    term = x / 2.0
    total = term.copy()
    for m in range(1, 60):
        term = term * (-(x * x) / 4.0) / (m * (m + 1))
        total = total + term
        if np.max(np.abs(term)) < 1e-14:
            break
    return total


def piston_directivity(cos_beta: np.ndarray, wavenumber: float = C.WAVE_NUMBER) -> np.ndarray:
    """Baffled 10 mm piston: 2*J1(x)/x, zero behind the board."""
    cos_beta = np.asarray(cos_beta, dtype=float)
    sin_beta = np.sqrt(np.maximum(0.0, 1.0 - cos_beta**2))
    x = wavenumber * C.ELEMENT_RADIUS_M * sin_beta
    x = np.maximum(x, 1e-12)
    return np.where(cos_beta > 0.0, 2.0 * _bessel_j1(x) / x, 0.0)


# ---------------------------------------------------------------------------
# direction grids

def uv_grid(du: float = 0.004):
    """Direction-cosine grid over the forward hemisphere.

    Returns (U2, V2, mask, dirs, el_deg, az_deg, solid_angle).  The square
    grid is |u|,|v| <= 1 with the unit disk valid.
    """
    u = np.arange(-1.0, 1.0 + du / 2.0, du)
    U2, V2 = np.meshgrid(u, u, indexing="xy")
    mask = U2**2 + V2**2 <= 1.0
    uu, vv = U2[mask], V2[mask]
    ww = np.sqrt(np.maximum(0.0, 1.0 - uu**2 - vv**2))
    dirs = np.column_stack([uu, vv, ww])
    el = np.degrees(np.arccos(np.clip(ww, -1.0, 1.0)))
    az = np.degrees(np.arctan2(vv, uu))
    # At fixed v, u=sqrt(1-v²) sin(t) gives dOmega=dt dv. Integrate each
    # row's end cells to the horizon instead of dividing by w=0 there.
    rows = np.flatnonzero(mask.any(axis=1))
    v = u[rows]
    dv = np.diff(np.r_[-1., (v[1:] + v[:-1]) / 2, 1.])
    weights = []
    for row, width in zip(rows, dv):
        centers = u[mask[row]]
        edges = (centers[1:] + centers[:-1]) / 2
        radius = np.sqrt(max(0., 1 - u[row]**2))
        angles = np.arcsin(np.clip(edges / radius, -1., 1.)) if edges.size else edges
        weights.append(width * np.diff(np.r_[-np.pi / 2, angles, np.pi / 2]))
    domega = np.concatenate(weights)
    return U2, V2, mask, dirs, el, az, domega


def dir_from_angles(el_deg: float, az_deg: float) -> np.ndarray:
    e, a = math.radians(el_deg), math.radians(az_deg)
    return np.array([math.sin(e) * math.cos(a), math.sin(e) * math.sin(a), math.cos(e)])


# ---------------------------------------------------------------------------
# fields

def far_field(
    positions: np.ndarray,
    normals: np.ndarray,
    amplitudes: np.ndarray,
    dirs: np.ndarray,
    chunk: int = 4096,
    phases: np.ndarray | None = None,
    wavenumber: float | None = None,
) -> np.ndarray:
    """Complex pressure per direction (coherent sum over emitters)."""
    out = np.empty(dirs.shape[0], dtype=complex)
    weights = amplitudes.astype(complex)
    if phases is not None:
        weights = weights * np.exp(1j * np.asarray(phases, dtype=float))
    k = C.WAVE_NUMBER if wavenumber is None else float(wavenumber)
    for start in range(0, dirs.shape[0], chunk):
        block = dirs[start:start + chunk]
        cos_beta = block @ normals.T
        directivity = piston_directivity(cos_beta, k)
        phase = np.exp(1j * k * (block @ positions.T))
        out[start:start + chunk] = (directivity * phase * weights).sum(axis=1)
    return out


def near_field_points(
    positions: np.ndarray,
    normals: np.ndarray,
    amplitudes: np.ndarray,
    points: np.ndarray,
    chunk: int = 2048,
    *,
    element_pattern=piston_directivity,
) -> np.ndarray:
    """Complex pressure for exp(+iωt), matching the far-field phase convention."""
    out = np.empty(points.shape[0], dtype=complex)
    for start in range(0, points.shape[0], chunk):
        block = points[start:start + chunk]
        delta = block[:, None, :] - positions[None, :, :]
        r = np.linalg.norm(delta, axis=-1)
        direction = np.divide(delta, r[:, :, None], out=np.zeros_like(delta, dtype=float),
                              where=r[:, :, None] > 0)
        cos_beta = np.einsum("pnk,nk->pn", direction, normals)
        directivity = element_pattern(cos_beta)
        out[start:start + chunk] = (
            directivity
            * np.exp(-1j * C.WAVE_NUMBER * r)
            / np.maximum(r, C.ELEMENT_RADIUS_M)
            * amplitudes[None, :]
        ).sum(axis=1)
    return out


def near_field_plane(
    positions: np.ndarray,
    normals: np.ndarray,
    amplitudes: np.ndarray,
    xs: np.ndarray,
    zs: np.ndarray,
    y: float,
    chunk: int = 2048,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Pressure on a plane y = const, on the x-z grid.

    Returns (x_grid, z_grid, complex pressure) with shape (len(zs), len(xs)).
    """
    X, Z = np.meshgrid(xs, zs, indexing="xy")
    points = np.column_stack([X.ravel(), np.full(X.size, float(y)), Z.ravel()])
    p = near_field_points(positions, normals, amplitudes, points, chunk=chunk)
    return X, Z, p.reshape(X.shape)


def near_field_xy(
    positions: np.ndarray,
    normals: np.ndarray,
    amplitudes: np.ndarray,
    xs: np.ndarray,
    ys: np.ndarray,
    z: float,
    chunk: int = 2048,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    X, Y = np.meshgrid(xs, ys, indexing="xy")
    points = np.column_stack([X.ravel(), Y.ravel(), np.full(X.size, float(z))])
    p = near_field_points(positions, normals, amplitudes, points, chunk=chunk)
    return X, Y, p.reshape(X.shape)


# ---------------------------------------------------------------------------
# fast exact model for coplanar boards


class CoplanarModel:
    """Exact far field for any set of coplanar, equal boards.

    Every board is the same 16x16 piston grid with the same +z normal, so its
    pattern B(u) is computed once; a candidate geometry only changes the
    lattice factor L(u) = sum_b exp(i k u . delta_b).  That makes a full
    direction-cosine scan cheap enough to run inside the search.
    """

    def __init__(self, du: float = 0.004):
        self.du = float(du)
        U2, V2, mask, dirs, el, az, domega = uv_grid(du)
        self.grid = (U2, V2, mask, dirs, el, az, domega)
        self.dirs = dirs
        self.directivity = piston_directivity(np.clip(dirs[:, 2], -1.0, 1.0))
        n = C.N_SIDE
        h = 0.5 - 0.5 * np.cos(2.0 * np.pi * np.arange(n) / (n - 1))
        self.weights = {
            "uniform": np.ones(C.N_PER_BOARD),
            "hann": np.outer(h, h).ravel(),
        }
        r, c = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
        self.local = np.column_stack(
            [c.ravel() * C.PITCH_M, r.ravel() * C.PITCH_M,
             np.zeros(C.N_PER_BOARD)]
        )
        self._board_patterns = {
            name: self._board_sum(self.local, w, dirs)
            for name, w in self.weights.items()
        }

    @staticmethod
    def _board_sum(local, weights, dirs, chunk: int = 2048) -> np.ndarray:
        out = np.empty(dirs.shape[0], dtype=complex)
        for start in range(0, dirs.shape[0], chunk):
            block = dirs[start:start + chunk]
            out[start:start + chunk] = (
                np.exp(1j * C.WAVE_NUMBER * (block @ local.T)) @ weights
            )
        return out

    def _fn(self, offsets: np.ndarray, taper: str):
        name = taper if taper in self.weights else "uniform"
        pattern = self._board_patterns[name]

        def field_fn(dirs: np.ndarray) -> np.ndarray:
            if dirs is self.dirs:
                board = pattern
            else:
                board = self._board_sum(self.local, self.weights[name], dirs)
            lattice = np.zeros(dirs.shape[0], dtype=complex)
            for delta in offsets:
                lattice = lattice + np.exp(
                    1j * C.WAVE_NUMBER * (dirs @ np.asarray(delta, float))
                )
            return (self.directivity_for(dirs) * board * lattice)

        return field_fn

    def directivity_for(self, dirs: np.ndarray) -> np.ndarray:
        if dirs is self.dirs:
            return self.directivity
        return piston_directivity(np.clip(dirs[:, 2], -1.0, 1.0))

    def analyse(self, offsets, taper: str = "uniform") -> dict:
        offsets = np.asarray(offsets, dtype=float)
        fn = self._fn(offsets, taper)
        U2, V2, mask, dirs, el, az, domega = self.grid
        lattice = np.zeros(dirs.shape[0], dtype=complex)
        for delta in offsets:
            lattice = lattice + np.exp(
                1j * C.WAVE_NUMBER * (dirs @ np.asarray(delta, float))
            )
        name = taper if taper in self.weights else "uniform"
        field = self.directivity * self._board_patterns[name] * lattice
        return analyse_fn(fn, self.du, field=field, grid=self.grid)


# ---------------------------------------------------------------------------
# metrics

def _db(level: np.ndarray, peak: float) -> np.ndarray:
    return 20.0 * np.log10(np.maximum(np.abs(level) / peak, 10.0 ** (C.DB_FLOOR / 20.0)))


def cut_levels(
    positions, normals, amplitudes, az_deg: float, step_deg: float = 0.1
) -> tuple[np.ndarray, np.ndarray]:
    el = np.arange(0.0, 90.0 + 1e-9, step_deg)
    dirs = np.stack([dir_from_angles(e, az_deg) for e in el])
    return el, np.abs(far_field(positions, normals, amplitudes, dirs))


def _half_power_width(el, level, peak_level):
    """Full width at -6 dB (amplitude half), not -3 dB."""
    half = peak_level / 2.0
    if float(level.max()) < peak_level * 0.99:
        return float("nan")
    i_peak = int(np.argmax(level))
    i = i_peak
    while i > 0 and level[i - 1] >= half:
        i -= 1
    j = i_peak
    while j < len(level) - 1 and level[j + 1] >= half:
        j += 1
    width = float(el[j] - el[i])
    if i_peak == 0:
        # broadside peak: the cut starts at the centre; mirror for the full width
        width *= 2.0
    return width


def refine_peak_fn(
    field_fn,
    center: np.ndarray,
    span: float = 0.02,
    step: float = 0.0005,
) -> tuple[np.ndarray, float]:
    """Local fine search around a coarse peak; returns (direction, peak)."""
    u0 = np.array([center[0], center[1]], dtype=float)
    u = np.arange(u0[0] - span, u0[0] + span + step / 2, step)
    v = np.arange(u0[1] - span, u0[1] + span + step / 2, step)
    U, V = np.meshgrid(u, v, indexing="xy")
    inside = U**2 + V**2 < 1.0
    uu, vv = U[inside], V[inside]
    ww = np.sqrt(np.maximum(0.0, 1.0 - uu**2 - vv**2))
    dirs = np.column_stack([uu, vv, ww])
    level = np.abs(field_fn(dirs))
    i = int(np.argmax(level))
    return dirs[i], float(level[i])


def refine_peak(positions, normals, amplitudes, center, span=0.02, step=0.0005):
    return refine_peak_fn(
        lambda d: far_field(positions, normals, amplitudes, d),
        center, span, step,
    )


def analyse(
    positions: np.ndarray,
    normals: np.ndarray,
    amplitudes: np.ndarray,
    du: float = 0.004,
) -> dict:
    """Far-field metrics for an explicit emitter set."""
    return analyse_fn(
        lambda d: far_field(positions, normals, amplitudes, d),
        du,
        cut_positions=(positions, normals, amplitudes),
    )


def analyse_fn(field_fn, du: float = 0.004, cut_positions=None,
               field=None, grid=None) -> dict:
    """Far-field metrics on the forward hemisphere from a field callable.

    ``field_fn(dirs)`` returns complex pressure for (M, 3) directions.
    ``cut_positions`` (positions, normals, amplitudes) is needed only for the
    fine polar cuts; the fast coplanar model supplies its own callable.
    """
    if grid is None:
        grid = uv_grid(du)
    U2, V2, mask, dirs, el, az, domega = grid
    if field is None:
        field = field_fn(dirs)
    amp = np.abs(field)
    coarse_dir = dirs[int(np.argmax(amp))]
    peak_dir, peak = refine_peak_fn(field_fn, coarse_dir)
    db_flat = 20.0 * np.log10(np.maximum(amp / peak, 1e-12)).astype(float)

    power = amp**2 * domega
    total = float(power.sum())
    band_50_60 = (el >= 50.0) & (el <= 60.0)
    above_60 = el > 60.0

    # The four axial grating directions carry the report's claim. Evaluate
    # them exactly: any grid misses a narrow null.
    lobe_az = (0.0, 90.0, 180.0, -90.0)
    lobe_dirs = np.stack(
        [dir_from_angles(C.GRATING_ANGLE_DEG, a) for a in lobe_az]
    )
    lobe_field = field_fn(lobe_dirs)
    lobe_by_az = {
        str(a): float(20.0 * np.log10(max(abs(v) / peak, 1e-12)))
        for a, v in zip(lobe_az, lobe_field)
    }
    lobe = max(lobe_by_az.values())

    # Main-lobe cone: 15 deg around the refined maximum.
    cos_ang = np.clip(dirs @ peak_dir, -1.0, 1.0)
    outside = np.degrees(np.arccos(cos_ang)) > 15.0
    peak_sidelobe = float(db_flat[outside].max())

    peak_az = float(np.degrees(np.arctan2(peak_dir[1], peak_dir[0])))
    peak_el = float(np.degrees(np.arccos(np.clip(peak_dir[2], -1.0, 1.0))))
    el_cut = np.arange(0.0, 90.0 + 1e-9, 0.05)
    if cut_positions is not None:
        cp, cn, ca = cut_positions
        _, cut_x = cut_levels(cp, cn, ca, 0.0, 0.05)
        _, cut_y = cut_levels(cp, cn, ca, 90.0, 0.05)
    else:
        az_cut = np.arange(0.0, 90.0 + 1e-9, 0.05)
        cut_x = np.abs(field_fn(np.stack([dir_from_angles(e, 0.0) for e in az_cut])))
        cut_y = np.abs(field_fn(np.stack([dir_from_angles(e, 90.0) for e in az_cut])))
    bw6_x = _half_power_width(el_cut, cut_x, peak)
    bw6_y = _half_power_width(el_cut, cut_y, peak)

    on_axis = float(20.0 * np.log10(max(
        abs(field_fn(np.array([[0.0, 0.0, 1.0]]))[0]) / peak, 1e-12)))
    di = 10.0 * math.log10(4.0 * math.pi * peak**2 / total) if total > 0 else float("nan")

    db2 = np.full(U2.shape, np.nan)
    db2[mask] = db_flat

    return {
        "peak": peak,
        "on_axis_db": on_axis,
        "lobe_54_75_db": lobe,
        "lobe_by_az_db": lobe_by_az,
        "band_max_db": float(db_flat[band_50_60].max()),
        "band_energy_pct": 100.0 * float(power[band_50_60].sum()) / total,
        "leak_60_pct": 100.0 * float(power[above_60].sum()) / total,
        "peak_sidelobe_db": peak_sidelobe,
        "bw6_xz_deg": bw6_x,
        "bw6_yz_deg": bw6_y,
        "di_db": di,
        "peak_el_deg": peak_el,
        "peak_az_deg": peak_az,
        "db": db2,
        "db_flat": db_flat,
        "U": U2,
        "V": V2,
        "mask": mask,
        "el": el,
        "az": az,
        "du": du,
    }
