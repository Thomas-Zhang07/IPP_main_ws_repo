"""Board placement for every sampled configuration.

Global frame: x horizontal, y vertical, z forward (away from the array).
Board local frame: emitter (row r, column c) at (c*pitch, r*pitch, 0), normal
+z; the PCB outline extends by the measured margins around that grid.

A board is placed by a yaw about the vertical axis through a declared local
pivot point, which is then put at a declared global point.  Hinged layouts
therefore share an exact hinge line, and butted layouts share an exact PCB
edge, with no accumulated rounding.
"""

from __future__ import annotations

import dataclasses
import math
from dataclasses import dataclass, field

import numpy as np

import constants as C


def _rot_y(degrees: float) -> np.ndarray:
    a = math.radians(degrees)
    ca, sa = math.cos(a), math.sin(a)
    return np.array([[ca, 0.0, sa], [0.0, 1.0, 0.0], [-sa, 0.0, ca]])


def _local_grid() -> np.ndarray:
    r, c = np.meshgrid(np.arange(C.N_SIDE), np.arange(C.N_SIDE), indexing="ij")
    return np.column_stack(
        [c.ravel() * C.PITCH_M, r.ravel() * C.PITCH_M, np.zeros(C.N_PER_BOARD)]
    )


_LOCAL_GRID = _local_grid()


@dataclass
class Board:
    """One PCB: emitter positions, normals, outline and logical grid index."""

    positions: np.ndarray          # (256, 3)
    normals: np.ndarray            # (256, 3)
    outline: np.ndarray            # (4, 3) PCB corners, closed implicitly
    label: str = ""

    def __post_init__(self) -> None:
        assert self.positions.shape == (C.N_PER_BOARD, 3)
        assert self.normals.shape == (C.N_PER_BOARD, 3)
        assert self.outline.shape == (4, 3)

    @property
    def center(self) -> np.ndarray:
        return self.positions.mean(axis=0)


def make_board(
    pivot_global: tuple[float, float, float],
    *,
    yaw_deg: float = 0.0,
    pivot_local: tuple[float, float, float] = (0.0, 0.0, 0.0),
    label: str = "",
) -> Board:
    """Place one board.

    Local coordinates are rotated about ``pivot_local`` (yaw about +y) and
    that pivot is translated to ``pivot_global``.
    """
    rot = _rot_y(yaw_deg)
    pivot = np.asarray(pivot_local, dtype=float)
    target = np.asarray(pivot_global, dtype=float)

    positions = (_LOCAL_GRID - pivot) @ rot.T + target
    normals = np.tile(rot @ np.array([0.0, 0.0, 1.0]), (C.N_PER_BOARD, 1))

    ml, mr = C.MARGIN_LEFT_M, C.MARGIN_RIGHT_M
    mb, mt = C.MARGIN_BOTTOM_M, C.MARGIN_TOP_M
    corners = np.array(
        [
            [-ml, -mb, 0.0],
            [C.SPAN_M + mr, -mb, 0.0],
            [C.SPAN_M + mr, C.SPAN_M + mt, 0.0],
            [-ml, C.SPAN_M + mt, 0.0],
        ]
    )
    outline = (corners - pivot) @ rot.T + target
    return Board(positions=positions, normals=normals, outline=outline, label=label)


def board_span_x(board: Board) -> tuple[float, float]:
    return float(board.positions[:, 0].min()), float(board.positions[:, 0].max())


@dataclass
class Layout:
    key: str
    title: str
    boards: list[Board]
    notes: str = ""
    far_field: bool = True
    params: dict = field(default_factory=dict)

    @property
    def positions(self) -> np.ndarray:
        return np.vstack([b.positions for b in self.boards])

    @property
    def normals(self) -> np.ndarray:
        return np.vstack([b.normals for b in self.boards])

    def amplitudes(self, taper: str = "uniform") -> np.ndarray:
        if taper == "uniform":
            return np.ones(len(self.boards) * C.N_PER_BOARD)
        if taper != "hann":
            raise ValueError(f"unknown taper {taper!r}")
        n = C.N_SIDE
        h = 0.5 - 0.5 * np.cos(2.0 * np.pi * np.arange(n) / (n - 1))
        w2 = np.outer(h, h).ravel()          # rows x columns, symmetric
        return np.concatenate([w2 for _ in self.boards])

    def shifted(self, **params) -> "Layout":
        """Return a shallow copy carrying different parameters (for caching)."""
        copied = dataclasses.replace(self, params={**self.params, **params})
        return copied


# ---------------------------------------------------------------------------
# one-off layouts


def single() -> Layout:
    return Layout(
        key="01_single",
        title="Single board",
        boards=[
            make_board(
                (-C.SPAN_M / 2, -C.SPAN_M / 2, 0.0),
                label="A",
            )
        ],
        notes="16 x 16, uniform, broadside. Reference for one PCB.",
    )


def _pair_coplanar(seam_m: float, offset_y_m: float, key: str, title: str, notes: str):
    y0 = -C.SPAN_M / 2
    return Layout(
        key=key,
        title=title,
        boards=[
            make_board((-C.SPAN_M - seam_m / 2, y0, 0.0), label="A"),
            make_board((seam_m / 2, y0 + offset_y_m, 0.0), label="B"),
        ],
        notes=notes,
        params={"seam_m": seam_m, "offset_y_m": offset_y_m},
    )


def coplanar_butt() -> Layout:
    return _pair_coplanar(
        C.BUTT_SEAM_M, 0.0,
        "04_coplanar_butt",
        "Two boards, coplanar, PCB edges butted",
        "10.902 mm element seam, no y offset: the physical baseline.",
    )


def coplanar_gap() -> Layout:
    return _pair_coplanar(
        C.CURRENT_SEAM_M, C.CURRENT_OFFSET_Y_M,
        "05_coplanar_gap",
        "Two boards, coplanar, 5 mm gap (current)",
        "15.750 mm seam, 5.250 mm half-pitch y offset, 4.848 mm edge gap.",
    )


def pair_seam_only() -> Layout:
    return _pair_coplanar(
        C.CURRENT_SEAM_M, 0.0,
        "09_pair_seam_only",
        "Control: 15.750 mm seam, y offset 0",
        "Separates the seam effect from the half-pitch offset effect.",
    )


def v_pair(included_deg: float, key: str, title: str, seam_m: float = C.BUTT_SEAM_M) -> Layout:
    half = (180.0 - included_deg) / 2.0
    return Layout(
        key=key,
        title=title,
        boards=[
            make_board(
                (0.0, -C.SPAN_M / 2, 0.0),
                yaw_deg=+half,
                pivot_local=(C.SPAN_M + C.MARGIN_RIGHT_M, 0.0, 0.0),
                label="A",
            ),
            make_board(
                (0.0, -C.SPAN_M / 2, 0.0),
                yaw_deg=-half,
                pivot_local=(-C.MARGIN_LEFT_M, 0.0, 0.0),
                label="B",
            ),
        ],
        notes=(
            f"Included angle {included_deg:.0f} deg, PCB inner edges butted at "
            f"x=0, boards open forward toward the listener; normals converge."
        ),
        params={"included_deg": included_deg, "seam_m": seam_m},
    )


def facing(distance_m: float = 0.400) -> Layout:
    a = make_board((-C.SPAN_M / 2, -C.SPAN_M / 2, 0.0), label="A")
    # Board B is the same PCB turned 180 deg about the vertical centre line:
    # normal -z, margins mirrored, emitter grid coaxial with A.
    b_pos = a.positions.copy()
    b_pos[:, 0] *= -1.0
    b_pos[:, 2] = distance_m
    b_out = a.outline.copy()
    b_out[:, 0] *= -1.0
    b_out[:, 2] = distance_m
    b = Board(positions=b_pos,
              normals=np.tile(np.array([0.0, 0.0, -1.0]), (C.N_PER_BOARD, 1)),
              outline=b_out, label="B")
    return Layout(
        key="06_facing",
        title="Two boards facing each other, parallel",
        boards=[a, b],
        notes=(
            f"{distance_m * 1e3:.0f} mm apart, normals opposed (A +z, B -z), "
            "emitter grids coaxial. Far field is degenerate; near-field only."
        ),
        far_field=False,
        params={"distance_m": distance_m},
    )


def concave3(wing_deg: float = 30.0) -> Layout:
    centre = make_board((-C.SPAN_M / 2, -C.SPAN_M / 2, 0.0), label="B")
    left = make_board(
        (-C.SPAN_M / 2 - C.MARGIN_LEFT_M, -C.SPAN_M / 2, 0.0),
        yaw_deg=+wing_deg,
        pivot_local=(C.SPAN_M + C.MARGIN_RIGHT_M, 0.0, 0.0),
        label="A",
    )
    right = make_board(
        (C.SPAN_M / 2 + C.MARGIN_RIGHT_M, -C.SPAN_M / 2, 0.0),
        yaw_deg=-wing_deg,
        pivot_local=(-C.MARGIN_LEFT_M, 0.0, 0.0),
        label="C",
    )
    return Layout(
        key="07_concave3",
        title="Three boards, concave \\_/",
        boards=[left, centre, right],
        notes=(
            f"Wings yawed {wing_deg:.0f} deg forward about the centre board's "
            "PCB edges (element seam 10.902 mm), concave side to the listener."
        ),
        params={"wing_deg": wing_deg},
    )


def coplanar3(seam1_m: float = C.CURRENT_SEAM_M,
              seam2_m: float = C.CURRENT_SEAM_M,
              offsets: tuple[float, float, float] = (0.0, 0.0, 0.0),
              key: str = "08_coplanar3",
              title: str = "Three boards, coplanar, current gap") -> Layout:
    total = 3 * C.SPAN_M + seam1_m + seam2_m
    start = -total / 2
    xs = [start, start + C.SPAN_M + seam1_m,
          start + 2 * C.SPAN_M + seam1_m + seam2_m]
    boards = [
        make_board((x, -C.SPAN_M / 2 + off, 0.0), label=lab)
        for x, off, lab in zip(xs, offsets, "ABC")
    ]
    return Layout(
        key=key,
        title=title,
        boards=boards,
        notes=(
            f"Seams {seam1_m * 1e3:.3f} / {seam2_m * 1e3:.3f} mm, y offsets "
            f"{', '.join(f'{o * 1e3:.3f}' for o in offsets)} mm."
        ),
        params={"seam1_m": seam1_m, "seam2_m": seam2_m, "offsets": offsets},
    )


def butt_offset() -> Layout:
    """PCB edges touching, but board B keeps the 5.25 mm half-pitch offset.

    This is the "no gap" version of the current pair: the boards are slid
    together, so the element seam is the butted 10.902 mm, but the vertical
    half-pitch offset is retained.
    """
    return _pair_coplanar(
        C.BUTT_SEAM_M, C.CURRENT_OFFSET_Y_M,
        "10_butt_offset",
        "Two boards, coplanar, edges butted + 5.25 mm offset",
        "No PCB gap (10.902 mm element seam) with the current half-pitch "
        "offset; the buildable no-gap variant.",
    )


def baseline_layouts() -> list[Layout]:
    return [
        single(),
        v_pair(150.0, "02_v150", "Two boards, V 150 deg"),
        v_pair(120.0, "03_v120", "Two boards, V 120 deg"),
        coplanar_butt(),
        coplanar_gap(),
        facing(),
        concave3(30.0),
        coplanar3(),
        pair_seam_only(),
        butt_offset(),
    ]
