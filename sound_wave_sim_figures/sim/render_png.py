"""Matplotlib rendering: 2D figures at 300 dpi.

Sequential magnitude uses the inferno ramp (dark floor, bright peak), so low
levels stay visible on a light surface.  Categorical colours carry board
family identity; every multi-series plot has a legend.
"""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from matplotlib.patches import Patch, Polygon

import constants as C
import field
import geometry

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#8a8983"
GRID = "#e6e5e0"

BLUE = "#2a78d6"
ORANGE = "#eb6834"
AQUA = "#1baf7a"
YELLOW = "#eda100"
VIOLET = "#6250d6"
GRAY = "#8a8983"
RED = "#e34948"
CYAN = "#38bdf8"
DARK = "#104281"

FAMILY_COLOR = {
    "single": GRAY,
    "pair": BLUE,
    "v": ORANGE,
    "three": AQUA,
    "control": VIOLET,
    "best": DARK,
}

# Sequential, perceptually uniform, dark at the floor.
RAMP = LinearSegmentedColormap.from_list(
    "db_inferno",
    ["#000004", "#1b0c41", "#4a0c6b", "#781c6d", "#a52c60",
     "#cf4446", "#ed6925", "#fb9b06", "#f7d13d", "#fcffa4"],
)
RAMP.set_bad((1.0, 1.0, 1.0, 0.0))
DIVERGING = LinearSegmentedColormap.from_list(
    "pressure_div",
    ["#104281", "#5598e7", "#cde2fb", "#f7f7f5",
     "#f6c9b0", "#ed6925", "#a52c60"],
)

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 9,
    "axes.edgecolor": MUTED,
    "axes.labelcolor": INK_2,
    "axes.titlecolor": INK,
    "xtick.color": INK_2,
    "ytick.color": INK_2,
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "axes.grid": False,
})

FLOOR = C.DB_FLOOR


def _fmt_deg(value) -> str:
    if value is None or not np.isfinite(value):
        return "—"
    return f"{value:.1f}°"


def _fmt_db(value) -> str:
    if value is None or not np.isfinite(value):
        return "—"
    if value <= -60.0:
        return "< −60 dB"
    return f"{value:.1f} dB"


def _db_norm(db: np.ndarray) -> np.ndarray:
    return np.clip(db, FLOOR, 0.0)


def dB(values: np.ndarray, peak: float) -> np.ndarray:
    return 20.0 * np.log10(
        np.maximum(np.abs(values) / peak, 10.0 ** (FLOOR / 20.0))
    )


# ---------------------------------------------------------------------------
# board sketches


def draw_board_view(ax, layout):
    normals = layout.normals
    zs = layout.positions[:, 2]
    if np.all(normals[:, 2] > 0.999) and float(np.ptp(zs)) < 1e-6:
        _draw_top_view(ax, layout)
    else:
        draw_plan_view(ax, layout)


def _draw_top_view(ax, layout):
    ax.set_facecolor(SURFACE)
    for board in layout.boards:
        poly = Polygon(
            board.outline[:, [0, 1]], closed=True,
            facecolor="#dff0e7", edgecolor="#2f6b4f", linewidth=1.2, zorder=2,
        )
        ax.add_patch(poly)
        ax.scatter(board.positions[:, 0], board.positions[:, 1], s=2.2,
                   color="#2f6b4f", zorder=3, linewidths=0)
        c = board.center
        ax.text(c[0], c[1], board.label, ha="center", va="center",
                fontsize=10, color="#2f6b4f", fontweight="bold", zorder=4)
    ax.set_aspect("equal")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_title("Top view (normals out of page)", fontsize=9, loc="left",
                 color=INK_2)
    ax.tick_params(labelsize=7, length=2)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(True, color=GRID, lw=0.6, zorder=0)


def draw_plan_view(ax, layout, *, arrows=True, labels=True):
    ax.set_facecolor(SURFACE)
    for board in layout.boards:
        poly = Polygon(
            board.outline[:, [0, 2]], closed=True,
            facecolor="#dff0e7", edgecolor="#2f6b4f", linewidth=1.2, zorder=2,
        )
        ax.add_patch(poly)
        ax.scatter(board.positions[:, 0], board.positions[:, 2],
                   s=1.6, color="#2f6b4f", zorder=3, linewidths=0)
        if arrows:
            c = board.center
            n = board.normals[0] * 0.030
            ax.annotate(
                "", xy=(c[0] + n[0], c[2] + n[2]), xytext=(c[0], c[2]),
                arrowprops=dict(arrowstyle="-|>", color="#c2410c", lw=1.4),
                zorder=4,
            )
            ax.annotate(
                f"n_{board.label}",
                xy=(c[0] + n[0] * 1.28, c[2] + n[2] * 1.28),
                color="#c2410c", fontsize=8, ha="center", va="center",
            )
        if labels:
            c = board.center
            ax.text(c[0], c[2] - 0.035, board.label, ha="center", va="top",
                    fontsize=10, color="#2f6b4f", fontweight="bold")
    ax.set_aspect("equal")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("z, forward (m)")
    ax.set_title("Plan view (normal arrows)", fontsize=9, loc="left",
                 color=INK_2)
    ax.tick_params(labelsize=7, length=2)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(True, color=GRID, lw=0.6, zorder=0)


def _family(key: str) -> str:
    if key.startswith("01"):
        return "single"
    if key.startswith("02") or key.startswith("03"):
        return "v"
    if key.startswith("04") or key.startswith("05") or key.startswith("10"):
        return "pair"
    if key.startswith("07") or key.startswith("08") or key.startswith("opt3"):
        return "three"
    if key.startswith("opt2"):
        return "pair"
    if key.startswith("09"):
        return "control"
    return "best"


# ---------------------------------------------------------------------------
# far-field sheet


def _u_minor_rings(ax):
    """Faint constant-angle rings and the grating circle."""
    for ang in (30.0, 60.0):
        r = math.sin(math.radians(ang))
        th = np.linspace(0, 2 * math.pi, 300)
        ax.plot(r * np.cos(th), r * np.sin(th), color=GRID, lw=0.8, zorder=2)
        ax.text(r + 0.02, 0.03, f"{ang:.0f}°", color=MUTED, fontsize=7.5,
                ha="left", va="bottom", zorder=3)
    ug = math.sin(math.radians(C.GRATING_ANGLE_DEG))
    th = np.linspace(0, 2 * math.pi, 400)
    ax.plot(ug * np.cos(th), ug * np.sin(th), color=CYAN, lw=1.4,
            ls=(0, (4, 3)), zorder=4)
    for ux, uy in ((ug, 0), (-ug, 0), (0, ug), (0, -ug)):
        ax.plot([ux], [uy], marker="+", ms=8, color=CYAN, mew=1.4, zorder=5)
    ax.text(-0.97, 0.86, "54.75° grating ring", color=CYAN, fontsize=8,
            ha="left", va="center", zorder=6,
            bbox=dict(boxstyle="round,pad=0.25", fc="black", ec="none",
                      alpha=0.55))


def _cart_cut(ax, el, level, peak, title, color, mark_grating=True):
    db = np.clip(dB(level, peak), FLOOR, 0.0)
    ax.plot(el, db, color=color, lw=1.7, zorder=3)
    ax.set_xlim(0, 90)
    ax.set_ylim(FLOOR, 0)
    ax.set_xticks([0, 30, 60, 90])
    ax.set_xlabel("angle from broadside (deg)")
    ax.set_ylabel("level (dB re peak)")
    ax.set_title(title, fontsize=9, loc="left", color=INK_2)
    ax.grid(color=GRID, lw=0.7, zorder=0)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(labelsize=8, length=2)
    if mark_grating:
        ax.axvline(C.GRATING_ANGLE_DEG, color=CYAN, lw=1.2, ls=(0, (4, 3)),
                   zorder=4)
        ax.text(C.GRATING_ANGLE_DEG + 1.5, -1.0, "54.75°", color=CYAN,
                fontsize=8, ha="left", va="top")


def far_field_png(layout: geometry.Layout, m: dict, path: Path) -> None:
    fig = plt.figure(figsize=(14.4, 5.7))
    gs = fig.add_gridspec(1, 4, width_ratios=[1.05, 1.9, 1.25, 1.25],
                          wspace=0.40)
    ax_tv = fig.add_subplot(gs[0, 0])
    ax_map = fig.add_subplot(gs[0, 1])
    ax_xz = fig.add_subplot(gs[0, 2])
    ax_yz = fig.add_subplot(gs[0, 3])

    draw_board_view(ax_tv, layout)

    db = np.clip(m["db"], FLOOR, 0.0)
    mesh = ax_map.pcolormesh(m["U"], m["V"], db, cmap=RAMP, vmin=FLOOR,
                             vmax=0, shading="auto", rasterized=True)
    _u_minor_rings(ax_map)
    ax_map.set_xlabel("u$_x$ = sin θ · cos φ")
    ax_map.set_ylabel("u$_y$ = sin θ · sin φ")
    ax_map.set_title("Forward hemisphere in direction cosines (dB)",
                     fontsize=9, loc="left", color=INK_2)
    ax_map.set_xlim(-1.02, 1.02)
    ax_map.set_ylim(-1.02, 1.02)
    ax_map.set_aspect("equal")
    ax_map.set_xticks([-1, -0.5, 0, 0.5, 1])
    ax_map.set_yticks([-1, -0.5, 0, 0.5, 1])
    ax_map.tick_params(labelsize=8, length=2)
    for s in ("top", "right"):
        ax_map.spines[s].set_visible(False)
    cb = fig.colorbar(mesh, ax=ax_map, pad=0.015, fraction=0.046)
    cb.ax.tick_params(labelsize=7, length=2)
    cb.outline.set_edgecolor(GRID)
    cb.set_label("dB re peak", fontsize=8, color=INK_2)

    el_cut, cut_x = field.cut_levels(
        layout.positions, layout.normals, layout.amplitudes(), 0.0, 0.25
    )
    el_env = np.arange(0.0, 90.0 + 0.25, 0.25)
    az_env = np.arange(0.0, 360.0, 1.0)
    E, A = np.meshgrid(el_env, az_env, indexing="ij")
    dirs_env = np.stack([
        np.sin(np.radians(E)) * np.cos(np.radians(A)),
        np.sin(np.radians(E)) * np.sin(np.radians(A)),
        np.cos(np.radians(E)),
    ], axis=-1).reshape(-1, 3)
    env_amp = np.abs(field.far_field(layout.positions, layout.normals,
                                     layout.amplitudes(), dirs_env))
    envelope = env_amp.reshape(E.shape).max(axis=1)
    color = FAMILY_COLOR[_family(layout.key)]
    _cart_cut(ax_xz, el_cut, cut_x, m["peak"], "Cut in x–z plane", color)
    _cart_cut(ax_yz, el_env, envelope, m["peak"],
              "Worst case over azimuth", color)

    fig.suptitle(layout.title, fontsize=13, fontweight="bold", x=0.012,
                 ha="left", color=INK, y=0.985)
    fig.text(0.012, 0.925, layout.notes, fontsize=8.5, color=INK_2,
             ha="left", va="top")

    stats = (
        f"DI (forward) {m['di_db']:.1f} dB    "
        f"54.75° lobe {_fmt_db(m['lobe_54_75_db'])}    "
        f"50–60° band peak {m['band_max_db']:.1f} dB    "
        f"band energy {m['band_energy_pct']:.1f} %    "
        f"leak >60° {m['leak_60_pct']:.1f} %    "
        f"−6 dB beam {_fmt_deg(m['bw6_xz_deg'])} × {_fmt_deg(m['bw6_yz_deg'])}"
    )
    fig.text(0.012, 0.055, stats, fontsize=8.5, color=INK_2, ha="left")
    fig.text(
        0.012, 0.018,
        "Ideal model: uniform phase, 10 mm piston elements, no phase errors. "
        "Levels are relative to each pattern's peak.",
        fontsize=7.5, color=MUTED, ha="left",
    )
    fig.subplots_adjust(left=0.045, right=0.985, top=0.845, bottom=0.15)
    fig.savefig(path, dpi=300)
    plt.close(fig)


# ---------------------------------------------------------------------------
# near-field sheet


def near_field_arrays(layout, taper="uniform", res=0.005):
    amps = layout.amplitudes(taper)
    pos = layout.positions
    xmin, xmax = float(pos[:, 0].min()), float(pos[:, 0].max())
    ymid = float(0.5 * (pos[:, 1].min() + pos[:, 1].max()))
    zmax = 1.5 if layout.key != "06_facing" else float(layout.params["distance_m"])
    pad = 0.20
    xs = np.arange(xmin - pad, xmax + pad + res, res)
    zs = np.arange(0.02, zmax + res, res)
    X, Z, p_xz = field.near_field_plane(pos, layout.normals, amps, xs, zs, ymid)

    z_plane = 0.30 if layout.key != "06_facing" else zmax / 2
    res_xy = max(0.003, res * 0.75)
    xs_xy = np.arange(xmin - pad, xmax + pad + res_xy, res_xy)
    ys = np.arange(ymid - 0.30, ymid + 0.30 + res_xy, res_xy)
    XY, YY, p_xy = field.near_field_xy(pos, layout.normals, amps, xs_xy, ys,
                                       z_plane)

    # y-z slice at x = 0 (shows the vertical grating lobes and the y offset)
    y2 = np.arange(ymid - 0.30, ymid + 0.30 + res, res)
    Zg, Yg = np.meshgrid(zs, y2, indexing="xy")
    pts = np.column_stack([np.zeros(Yg.size), Yg.ravel(), Zg.ravel()])
    p_yz = field.near_field_points(pos, layout.normals, amps, pts).reshape(Yg.shape)

    # zoomed x-z window for the instantaneous-pressure view
    xc = 0.5 * (xmin + xmax)
    z_zoom_max = min(0.22, zmax)
    xz_z = np.arange(xc - 0.26, xc + 0.26 + 0.0015, 0.0015)
    zz_z = np.arange(0.02, z_zoom_max + 0.0015, 0.0015)
    XZ_Z, ZZ_Z, p_zoom = field.near_field_plane(
        pos, layout.normals, amps, xz_z, zz_z, ymid
    )

    peak = float(np.abs(p_xz).max())
    return {
        "X": X, "Z": Z, "p_xz": p_xz,
        "XY": XY, "YY": YY, "p_xy": p_xy,
        "YZ": Zg, "YYZ": Yg, "p_yz": p_yz,
        "XZ_Z": XZ_Z, "ZZ_Z": ZZ_Z, "p_zoom": p_zoom,
        "peak": peak, "ymid": ymid, "z_plane": z_plane,
    }


def near_field_png(layout: geometry.Layout, data: dict, path: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(13.4, 9.6))
    ax1, ax2, ax3, ax4 = axes.ravel()
    peak = data["peak"]

    db_xz = _db_norm(dB(data["p_xz"], peak))
    mesh = ax1.pcolormesh(data["X"], data["Z"], db_xz, cmap=RAMP,
                          vmin=FLOOR, vmax=0, shading="auto", rasterized=True)
    ax1.axhline(data["z_plane"], color=CYAN, lw=0.9, ls=(0, (3, 3)))
    ax1.text(data["X"].min() + 0.02, data["z_plane"] + 0.015,
             f"z = {data['z_plane'] * 1e3:.0f} mm slice", fontsize=7.5,
             color=INK, bbox=dict(boxstyle="round,pad=0.2", fc="white",
                                  ec="none", alpha=0.85))
    if data["Z"].max() > 1.0:
        ax1.axhline(1.0, color="white", lw=0.7, ls=(0, (2, 3)), alpha=0.8)
        ax1.text(data["X"].min() + 0.02, 1.015, "1 m", fontsize=7.5,
                 color=INK, bbox=dict(boxstyle="round,pad=0.2", fc="white",
                                      ec="none", alpha=0.85))
    _draw_cross_section(ax1, layout, data["ymid"])
    ax1.set_xlabel("x (m)")
    ax1.set_ylabel("z, distance from array (m)")
    ax1.set_title("x–z plane, array mid-height (dB re peak)",
                  fontsize=9, loc="left", color=INK_2)
    _finish(ax1)

    db_xy = _db_norm(dB(data["p_xy"], peak))
    mesh2 = ax2.pcolormesh(data["XY"], data["YY"], db_xy, cmap=RAMP,
                           vmin=FLOOR, vmax=0, shading="auto", rasterized=True)
    for board in layout.boards:
        ax2.plot(board.outline[:, 0], board.outline[:, 1], color="#2f6b4f",
                 lw=0.9, ls=(0, (4, 3)), alpha=0.85)
    ax2.set_xlabel("x (m)")
    ax2.set_ylabel("y (m)")
    ax2.set_title(
        f"x–y plane at z = {data['z_plane'] * 1e3:.0f} mm "
        "(dashed: PCB outline)", fontsize=9, loc="left", color=INK_2)
    _finish(ax2)

    db_yz = _db_norm(dB(data["p_yz"], peak))
    mesh3 = ax3.pcolormesh(data["YZ"], data["YYZ"], db_yz, cmap=RAMP,
                           vmin=FLOOR, vmax=0, shading="auto", rasterized=True)
    ax3.set_xlabel("z, distance from array (m)")
    ax3.set_ylabel("y (m)")
    ax3.set_title("y–z plane at x = 0 (dB re peak)",
                  fontsize=9, loc="left", color=INK_2)
    _finish(ax3)

    zoom = np.real(data["p_zoom"]) / peak
    norm = TwoSlopeNorm(vmin=-0.8, vcenter=0.0, vmax=0.8)
    mesh4 = ax4.pcolormesh(data["XZ_Z"], data["ZZ_Z"], zoom,
                           cmap=DIVERGING, norm=norm, shading="auto",
                           rasterized=True)
    _draw_cross_section(ax4, layout, data["ymid"])
    ax4.set_xlabel("x (m)")
    ax4.set_ylabel("z, distance from array (m)")
    ax4.set_title("Instantaneous pressure Re(p), near-seam zoom",
                  fontsize=9, loc="left", color=INK_2)
    ax4.set_aspect("equal")
    _finish(ax4)

    for ax, mesh in ((ax1, mesh), (ax2, mesh2), (ax3, mesh3)):
        cb = fig.colorbar(mesh, ax=ax, pad=0.015, fraction=0.046)
        cb.ax.tick_params(labelsize=7, length=2)
        cb.outline.set_edgecolor(GRID)
        cb.set_label("dB re common peak", fontsize=8, color=INK_2)
    cb4 = fig.colorbar(mesh4, ax=ax4, pad=0.015, fraction=0.046)
    cb4.ax.tick_params(labelsize=7, length=2)
    cb4.outline.set_edgecolor(GRID)
    cb4.set_label("Re(p) / peak |p|", fontsize=8, color=INK_2)

    fig.suptitle(f"{layout.title} — near field", fontsize=13,
                 fontweight="bold", x=0.012, ha="left", color=INK, y=0.985)
    fig.text(0.012, 0.952,
             "Full-wave sum of 10 mm piston sources; magnitude panels share "
             "one normalisation (peak of the x–z plane).\n"
             "This is the Fresnel region (D²/λ ≈ 13–30 m); the far-field "
             "lobes are on the far-field sheet. Lower-right: seam zoom, Re(p).",
             fontsize=8.5, color=INK_2, ha="left", va="top")
    fig.subplots_adjust(left=0.055, right=0.97, top=0.875, bottom=0.07,
                        wspace=0.24, hspace=0.30)
    fig.savefig(path, dpi=300)
    plt.close(fig)


def _finish(ax):
    ax.tick_params(labelsize=8, length=2)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def _draw_cross_section(ax, layout, ymid):
    for board in layout.boards:
        pts = board.outline
        if pts[:, 1].min() > ymid + 0.01 or pts[:, 1].max() < ymid - 0.01:
            continue

        def at_y(p, q, y):
            t = (y - p[1]) / (q[1] - p[1])
            return p + t * (q - p)

        left = at_y(pts[0], pts[3], ymid)
        right = at_y(pts[1], pts[2], ymid)
        ax.plot([left[0], right[0]], [left[2], right[2]], color="#2f6b4f",
                lw=3.0, solid_capstyle="butt", zorder=5)


# ---------------------------------------------------------------------------
# comparison charts


def _short_label(row: dict) -> str:
    key = row["key"]
    if key.startswith("opt3"):
        return "Optimal 3-board"
    if key.startswith("opt2"):
        return "Optimal 2-board"
    if key == "05_coplanar_gap":
        return "Current pair (15.75 / 5.25)"
    if key == "05_alt":
        return "Pair 16.54 / 5.25 (no null)"
    if key == "04_coplanar_butt":
        return "Coplanar butted"
    if key == "10_butt_offset":
        return "Butted + 5.25 offset"
    if key == "09_pair_seam_only":
        return "Seam-only control"
    if key == "02_v150":
        return "V 150°"
    if key == "03_v120":
        return "V 120°"
    if key == "07_concave3":
        return "Concave 3-board"
    if key == "08_coplanar3":
        return "Coplanar 3-board"
    if key == "01_single":
        return "Single board"
    return row["short"]


def comparison_png(rows: list[dict], path: Path, only=None) -> None:
    rows = [r for r in rows if r.get("di_db") is not None]

    def group_of(r):
        if r["key"].startswith("09"):
            return "control"
        if r.get("n_boards") == 1:
            return "single"
        if r.get("n_boards") == 3:
            return "three"
        return "pair"

    groups = [("Single board", "single"), ("2 boards", "pair"),
              ("3 boards", "three"), ("Control", "control")]

    order, labels, colors, headers, ys_list = [], [], [], [], []
    y = 0.0
    for title, key in groups:
        grp = sorted([r for r in rows if group_of(r) == key],
                     key=lambda r: -r["di_db"])
        if not grp:
            continue
        if len(grp) > 1:
            headers.append((title, y))
            y += 0.9
        for r in grp:
            order.append(r)
            labels.append(_short_label(r))
            colors.append(FAMILY_COLOR[_family(r["key"])])
            ys_list.append(y)
            y += 1.0
        y += 0.5
    n = len(order)
    ys = np.array(ys_list, dtype=float)
    ymax = float(y) if len(ys) else 0.0

    current = next((r for r in order if r["key"] == "05_coplanar_gap"), None)
    panels = [
        ("di_db", "Directivity index (dB)\nhigher is better", "{:.1f}", False),
        ("on_axis_db", "Broadside level re peak (dB)\nhigher is better", "{:.1f}", False),
        ("lobe_54_75_db", "Exact 54.75° lobe (dB)\nlower is better", "{:.1f}", True),
        ("band_max_db", "50–60° band peak (dB)\nlower is better", "{:.1f}", False),
        ("band_energy_pct", "Power in 50–60° band\n(% of forward) lower is better", "{:.1f}", False),
        ("leak_60_pct", "Power above 60°\n(% of forward) lower is better", "{:.2f}", False),
    ]
    sel = panels if only is None else [panels[i] for i in only]
    fig, axes = plt.subplots(1, len(sel), figsize=(3.75 * len(sel), 5.0),
                             sharey=False)
    for ax, (key, title, fmt, clip) in zip(axes, sel):
        vals = [r[key] for r in order]
        plot_vals = [max(v, -60.0) if clip else v for v in vals]
        ax.barh(ys, plot_vals, color=colors, height=0.64, zorder=3)
        ax.scatter(plot_vals, ys, s=9, color=INK, zorder=4, linewidths=0)
        span = max(1e-6, max(abs(v) for v in plot_vals))
        pad = 0.02 * span
        for yi, raw, pv in zip(ys, vals, plot_vals):
            if clip and raw <= -60.0:
                ax.text(1.0, yi, "< −60 (null)", va="center", ha="left",
                        fontsize=7.5, color=INK_2)
                continue
            txt = fmt.format(raw)
            ha = "right" if raw < 0 else "left"
            ax.text(pv + (-pad if raw < 0 else pad), yi, txt, va="center",
                    ha=ha, fontsize=7.5, color=INK_2)
        if current is not None and np.isfinite(current[key]):
            v = max(current[key], -60.0) if clip else current[key]
            ax.axvline(v, color=DARK, lw=0.9, ls=(0, (3, 3)), zorder=2)
        lo, hi = ax.get_xlim()
        span = hi - lo
        ax.set_xlim(lo - 0.06 * span, hi + 0.12 * span)
        ax.axvline(0.0, color=MUTED, lw=0.8, zorder=2)
        ax.set_title(title, fontsize=8.8, loc="left", color=INK_2)
        ax.grid(axis="x", color=GRID, lw=0.6, zorder=0)
        ax.tick_params(labelsize=8, length=2)
        for s in ("top", "right", "left"):
            ax.spines[s].set_visible(False)
    ticks = list(ys) + [hv for _, hv in headers]
    tick_labels = labels + [title for title, _ in headers]
    axes[0].set_yticks(ticks)
    axes[0].set_yticklabels(tick_labels, fontsize=8.5)
    for ax in axes:
        ax.tick_params(axis="y", length=0, labelleft=(ax is axes[0]))
    titles = {title for title, _ in headers}
    for lbl in axes[0].get_yticklabels():
        if lbl.get_text() in titles:
            lbl.set_fontweight("bold")
            lbl.set_color(INK)
    axes[0].set_ylim(ymax + 0.3, -0.6)
    legend = [
        Patch(facecolor=FAMILY_COLOR["single"], label="single board"),
        Patch(facecolor=FAMILY_COLOR["pair"], label="2 boards"),
        Patch(facecolor=FAMILY_COLOR["three"], label="3 boards"),
        Patch(facecolor=FAMILY_COLOR["control"], label="control"),
        plt.Line2D([], [], color=DARK, ls=(0, (3, 3)), label="current pair"),
    ]
    fig.legend(handles=legend, loc="lower left", ncol=5, frameon=False,
               fontsize=8.5, bbox_to_anchor=(0.012, 0.005))
    fig.suptitle("Board layouts compared — ideal model", fontsize=13,
                 fontweight="bold", x=0.012, ha="left", color=INK, y=0.985)
    fig.text(0.012, 0.925,
             "Rows grouped by board count. Bars are coloured by family; the "
             "dashed line marks the current 15.75 / 5.25 pair in every panel.",
             fontsize=8.5, color=INK_2, ha="left", va="top")
    fig.subplots_adjust(left=0.13, right=0.995, top=0.80, bottom=0.135,
                        wspace=0.14)
    fig.savefig(path, dpi=300)
    plt.close(fig)


def _kind_family(r: dict) -> str:
    if r.get("key") == "study":
        return {"pair": "pair", "v": "v", "three": "three",
                "concave": "three"}.get(r.get("kind"), "best")
    return _family(r["key"])


def pareto_png(rows: list[dict], path: Path, current=None, optimal=None,
               alternative=None) -> None:
    """Pareto front over the two competing goals: DI up, band peak down."""
    fig, ax = plt.subplots(figsize=(9.6, 5.8))
    pts = []
    for r in rows:
        di, pk = r.get("di_db"), r.get("band_max_db")
        onax = r.get("on_axis_db", -99.0)
        if di is None or pk is None or not np.isfinite(di) or not np.isfinite(pk):
            continue
        # designs whose broadside beam has collapsed are not candidates
        if onax is None or not np.isfinite(onax) or onax < -0.5:
            continue
        if di < 33.0:
            continue
        if _kind_family(r) in ("pair", "v", "three", "control"):
            pts.append((float(di), float(pk), r))
    ax.scatter([p[0] for p in pts], [p[1] for p in pts], s=7,
               color=MUTED, alpha=0.18, linewidths=0, zorder=2,
               label="searched geometry")

    if optimal is not None:
        odi, opk = float(optimal["di_db"]), float(optimal["band_max_db"])
        pts = [(di, opk if (abs(di - odi) < 0.05 and pk < opk) else pk, r)
               for di, pk, r in pts]
    ordered = sorted(pts, key=lambda p: (-round(p[0], 2), p[1]))
    front, best = [], 1e9
    for di, pk, r in ordered:
        if pk < best - 0.05:
            front.append((di, pk, r))
            best = pk
    if front:
        ax.scatter([p[0] for p in front], [p[1] for p in front], s=52,
                   color=DARK, zorder=5, linewidths=0, label="Pareto front")

    if current is not None:
        ax.scatter([current["di_db"]], [current["band_max_db"]],
                   marker="*", s=260, color=BLUE, edgecolor=SURFACE,
                   linewidth=1.0, zorder=6, label="current pair")
        ax.annotate("current pair", (current["di_db"],
                                     current["band_max_db"]),
                    xytext=(8, -16), textcoords="offset points",
                    fontsize=8.5, color=BLUE, fontweight="bold")
    if alternative is not None:
        ax.scatter([alternative["di_db"]], [alternative["band_max_db"]],
                   marker="s", s=70, facecolor="none", edgecolor=ORANGE,
                   linewidth=1.5, zorder=6, label="best non-null pair")
        ax.annotate("best pair without\nthe null", (alternative["di_db"],
                                                    alternative["band_max_db"]),
                    xytext=(-10, -26), textcoords="offset points",
                    fontsize=7.5, color=ORANGE, ha="right")
    if optimal is not None:
        ax.scatter([optimal["di_db"]], [optimal["band_max_db"]],
                   marker="D", s=110, facecolor="none", edgecolor=INK,
                   linewidth=1.5, zorder=6, label="searched optimum")
        ax.annotate("optimum", (optimal["di_db"], optimal["band_max_db"]),
                    xytext=(-16, 12), textcoords="offset points",
                    fontsize=8.5, color=INK, ha="right")

    ax.set_xlabel("directivity index (dB) — higher is better")
    ax.set_ylabel("50–60° band peak (dB re main peak) — lower is better")
    ax.set_title("Directionality versus grating-band leak", fontsize=12,
                 loc="left", fontweight="bold", color=INK)
    ax.grid(color=GRID, lw=0.7, zorder=0)
    for s_ in ("top", "right"):
        ax.spines[s_].set_visible(False)
    ax.legend(frameon=False, fontsize=8.5, ncol=2, loc="upper left",
              bbox_to_anchor=(0.0, -0.15))
    fig.tight_layout()
    fig.savefig(path, dpi=300)
    plt.close(fig)


def _heat(rows, xkey, ykey, value="band_max_db"):
    xs = sorted({round(float(r[xkey]) * 1e3, 4) for r in rows})
    ys = sorted({round(float(r[ykey]) * 1e3, 4) for r in rows})
    xi = {x: i for i, x in enumerate(xs)}
    yi = {y: i for i, y in enumerate(ys)}
    Z = np.full((len(ys), len(xs)), np.nan)
    for r in rows:
        xv = round(float(r[xkey]) * 1e3, 4)
        yv = round(float(r[ykey]) * 1e3, 4)
        Z[yi[yv], xi[xv]] = float(r[value])
    return np.array(xs), np.array(ys), _fill_nan(Z)


def _fill_nan(Z: np.ndarray) -> np.ndarray:
    """Nearest-neighbour fill so unsampled cells do not read as missing data."""
    Z = Z.astype(float).copy()
    for _ in range(200):
        mask = np.isnan(Z)
        if not mask.any():
            break
        pad = np.pad(Z, 1, constant_values=np.nan)
        stack = np.stack([pad[:-2, 1:-1], pad[2:, 1:-1],
                          pad[1:-1, :-2], pad[1:-1, 2:]])
        with np.errstate(invalid="ignore"):
            mean = np.nanmean(stack, axis=0)
        if not np.isfinite(mean[mask]).any():
            Z[mask] = np.nanmean(Z)
            break
        Z[mask] = mean[mask]
    return np.nan_to_num(Z, nan=float(np.nanmean(Z)))


def study2_scan_png(rows, path, current=None):
    sel = [r for r in rows if r["kind"] == "pair" and r["taper"] == "uniform"]
    xs, ys, Z = _heat(sel, "seam", "offset")
    fig, ax = plt.subplots(figsize=(8.2, 5.4))
    mesh = ax.pcolormesh(xs, ys, Z, cmap=RAMP, shading="nearest",
                         rasterized=True)
    cb = fig.colorbar(mesh, ax=ax, pad=0.015)
    cb.set_label("band peak, 50–60° (dB re main peak)", fontsize=8.5)
    cb.ax.tick_params(labelsize=7, length=2)
    cb.outline.set_edgecolor(GRID)
    if current is not None:
        ax.plot([float(current["seam"]) * 1e3],
                [float(current["offset"]) * 1e3],
                marker="*", ms=16, color=CYAN, mec="black", mew=0.8,
                zorder=5, label="current 15.75 / 5.25")
        ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    ax.set_xlabel("element seam between boards (mm)")
    ax.set_ylabel("y offset of board B (mm)")
    ax.set_title("2-board coplanar scan — grating-band peak, uniform taper",
                 fontsize=11, loc="left", color=INK)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=300)
    plt.close(fig)


def study2_yaw_png(rows, path):
    fig, ax = plt.subplots(figsize=(7.6, 4.8))
    for taper, color, label in (("uniform", BLUE, "uniform"),
                                ("hann", ORANGE, "Hann taper")):
        pts = sorted([r for r in rows if r["kind"] == "v"
                      and r["taper"] == taper],
                     key=lambda r: float(r["included"]))
        ax.plot([float(r["included"]) for r in pts],
                [r["band_max_db"] for r in pts],
                marker="o", ms=5, lw=2, color=color, label=label)
    ax.set_xlabel("V included angle between the faces (deg)")
    ax.set_ylabel("50–60° band peak (dB re main peak)")
    ax.set_title("V layouts — grating-band peak versus opening angle",
                 fontsize=11, loc="left", color=INK)
    ax.grid(color=GRID, lw=0.7)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.legend(frameon=False, fontsize=8.5)
    fig.tight_layout()
    fig.savefig(path, dpi=300)
    plt.close(fig)


def study3_heatmap_png(rows, path, best=None):
    three = [r for r in rows if r["kind"] == "three" and r["taper"] == "uniform"]
    if not three:
        return
    pattern = min(three, key=lambda r: float(r["band_max_db"]))["offsets"]
    sel = [r for r in three if r["offsets"] == pattern]
    xs, ys, Z = _heat(sel, "s1", "s2")
    fig, ax = plt.subplots(figsize=(8.0, 5.6))
    mesh = ax.pcolormesh(xs, ys, Z, cmap=RAMP, shading="nearest",
                         rasterized=True)
    cb = fig.colorbar(mesh, ax=ax, pad=0.015)
    cb.set_label("band peak, 50–60° (dB re main peak)", fontsize=8.5)
    cb.ax.tick_params(labelsize=7, length=2)
    cb.outline.set_edgecolor(GRID)
    if best is not None:
        ax.plot([float(best["s1"]) * 1e3], [float(best["s2"]) * 1e3],
                marker="D", ms=10, mfc="none", mec=CYAN, mew=1.8, zorder=5)
    ax.set_xlabel("A–B seam (mm)")
    ax.set_ylabel("B–C seam (mm)")
    offs = "/".join(f"{float(v) * 1e3:.1f}" for v in pattern.split(","))
    ax.set_title(f"3-board coplanar scan, offsets {offs} mm — band peak",
                 fontsize=11, loc="left", color=INK)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=300)
    plt.close(fig)


def leak_compare_png(layouts, path: Path, title="Where the leak actually changes", notes=None) -> None:
    """Two cuts that expose the split lobe: elevation at x, lateral at y."""
    fig, axes = plt.subplots(1, 2, figsize=(13.2, 5.0))
    ug = math.sin(math.radians(C.GRATING_ANGLE_DEG))
    ugz = math.cos(math.radians(C.GRATING_ANGLE_DEG))

    el = np.arange(40.0, 70.0 + 0.02, 0.02)
    dirs_x = np.stack([field.dir_from_angles(e, 0.0) for e in el])
    ux = np.arange(-0.20, 0.20 + 0.001, 0.001)
    uz2 = np.sqrt(np.maximum(0.0, 1.0 - ux**2 - ug**2))
    dirs_y = np.column_stack([ux, np.full_like(ux, ug), uz2])

    for layout, color, label in layouts:
        amps = layout.amplitudes()
        p_axis = abs(field.far_field(
            layout.positions, layout.normals, amps,
            np.array([[0.0, 0.0, 1.0]]),
        )[0])
        lx = 20 * np.log10(np.maximum(abs(field.far_field(
            layout.positions, layout.normals, amps, dirs_x)) / p_axis, 1e-6))
        ly = 20 * np.log10(np.maximum(abs(field.far_field(
            layout.positions, layout.normals, amps, dirs_y)) / p_axis, 1e-6))
        axes[0].plot(el, np.clip(lx, -50, 0), color=color, lw=1.8, label=label)
        axes[1].plot(ux, np.clip(ly, -50, 0), color=color, lw=1.8, label=label)

    axes[0].axvline(C.GRATING_ANGLE_DEG, color=CYAN, lw=1.2, ls=(0, (4, 3)))
    axes[0].text(C.GRATING_ANGLE_DEG + 0.3, -1.0, "54.75°", color=CYAN,
                 fontsize=8, va="top")
    axes[0].set_xlim(40, 70)
    axes[0].set_ylim(-50, 0)
    axes[0].set_xlabel("elevation through the φ = 0 lobe (deg)")
    axes[0].set_ylabel("level (dB re main peak)")
    axes[0].set_title("x-lobe: split radially in elevation", fontsize=10,
                      loc="left", color=INK_2)
    axes[0].legend(frameon=False, fontsize=8.5, loc="lower left")

    axes[1].axvline(0.0, color=CYAN, lw=1.2, ls=(0, (4, 3)))
    axes[1].set_xlim(-0.20, 0.20)
    axes[1].set_ylim(-50, 0)
    axes[1].set_xlabel("u$_x$ through the φ = 90° lobe (u$_y$ = 0.817)")
    axes[1].set_title("y-lobe: split laterally in u$_x$", fontsize=10,
                      loc="left", color=INK_2)

    for ax in axes:
        ax.grid(color=GRID, lw=0.7)
        ax.tick_params(labelsize=8, length=2)
        for s_ in ("top", "right"):
            ax.spines[s_].set_visible(False)

    if notes is None:
        notes = ("The current pair removes the lobe peak at 54.75° only; 2° "
                 "away the level matches the butted pair, so the 3D surface "
                 "and the band energy barely change.")
    fig.suptitle(title, fontsize=13, fontweight="bold", x=0.012, ha="left",
                 color=INK, y=0.98)
    fig.text(0.012, 0.915, notes, fontsize=8.5, color=INK_2, ha="left",
             va="top")
    fig.subplots_adjust(left=0.06, right=0.98, top=0.84, bottom=0.13,
                        wspace=0.20)
    fig.savefig(path, dpi=300)
    plt.close(fig)


def tolerance_png(layout, path: Path, sigmas=(0, 2, 5, 10, 15), trials=24,
                  seed=0) -> None:
    """Random errors barely fill the null; a systematic k shift moves it."""
    rng = np.random.default_rng(seed)
    U2, V2, mask, dirs, el, az, _ = field.uv_grid(0.02)
    band = (el >= 50.0) & (el <= 60.0)
    lobe_dirs = np.stack([
        field.dir_from_angles(C.GRATING_ANGLE_DEG, a)
        for a in (0.0, 90.0, 180.0, -90.0)
    ])
    amps = layout.amplitudes()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.2, 4.9))

    band_med, lobe_med = [], []
    for sigma in sigmas:
        bp, lb = [], []
        for _ in range(trials):
            phases = np.radians(rng.normal(0.0, sigma, len(amps)))
            gain = amps * 10 ** (rng.normal(0.0, 0.5, len(amps)) / 20.0)
            p_axis = abs(field.far_field(
                layout.positions, layout.normals, gain,
                np.array([[0.0, 0.0, 1.0]]), phases=phases)[0])
            grid = abs(field.far_field(layout.positions, layout.normals, gain,
                                       dirs, phases=phases))
            db = 20 * np.log10(np.maximum(grid / p_axis, 1e-9))
            bp.append(float(db[band].max()))
            lobe = abs(field.far_field(layout.positions, layout.normals, gain,
                                       lobe_dirs, phases=phases))
            lb.append(float(20 * np.log10(max(lobe.max() / p_axis, 1e-9))))
        band_med.append(np.median(bp))
        lobe_med.append(np.median(lb))

    x = np.array(sigmas, dtype=float)
    ax1.plot(x, np.clip(band_med, -80, 0), marker="o", color=BLUE, lw=2,
             label="50–60° band peak")
    ax1.plot(x, np.clip(lobe_med, -80, 0), marker="s", color=ORANGE, lw=2,
             label="exact 54.75° lobe")
    ax1.set_xlabel("random phase error, RMS (deg); gain error 0.5 dB RMS")
    ax1.set_ylabel("level (dB re main peak)")
    ax1.set_ylim(-80, -8)
    ax1.set_title("Random errors: the null barely fills", fontsize=10,
                  loc="left", color=INK_2)
    ax1.grid(color=GRID, lw=0.7)
    ax1.legend(frameon=False, fontsize=8.5, loc="center right")

    deltas = np.array([0.0, 0.1, 0.2, 0.35, 0.5, 1.0])
    lobe_shift = []
    for delta in deltas:
        k = C.WAVE_NUMBER * (1.0 + delta / 100.0)
        p_axis = abs(field.far_field(
            layout.positions, layout.normals, amps,
            np.array([[0.0, 0.0, 1.0]]), wavenumber=k)[0])
        lobe = abs(field.far_field(layout.positions, layout.normals, amps,
                                   lobe_dirs, wavenumber=k))
        lobe_shift.append(float(20 * np.log10(max(lobe.max() / p_axis, 1e-9))))

    ax2.plot(deltas, np.clip(lobe_shift, -80, 0), marker="o", color=ORANGE,
             lw=2, label="exact 54.75° lobe")
    ax2.axvspan(0.0, 0.35, color=RED, alpha=0.06, linewidth=0)
    ax2.text(0.17, -76, "±2 °C in air", color=RED, fontsize=7.5, ha="center")
    ax2.set_xlabel("carrier / sound-speed offset (%)")
    ax2.set_ylabel("level at the nominal 54.75° direction (dB)")
    ax2.set_ylim(-80, -8)
    ax2.set_title("Systematic shift: the null moves away",
                  fontsize=10, loc="left", color=INK_2)
    ax2.grid(color=GRID, lw=0.7)

    for ax in (ax1, ax2):
        ax.tick_params(labelsize=8, length=2)
        for s_ in ("top", "right"):
            ax.spines[s_].set_visible(False)

    fig.suptitle("Tolerance of the current pair", fontsize=13,
                 fontweight="bold", x=0.012, ha="left", color=INK, y=0.98)
    fig.text(0.012, 0.905,
             "Left: 24 Monte Carlo trials per point. Right: uniform +1 % "
             "change in k, as a temperature or sound-speed drift.",
             fontsize=8.5, color=INK_2, ha="left", va="top")
    fig.subplots_adjust(left=0.06, right=0.98, top=0.80, bottom=0.15,
                        wspace=0.22)
    fig.savefig(path, dpi=300)
    plt.close(fig)


def decomposition_png(layout, path: Path) -> None:
    """Board A, board B and the coherent sum, on the same grid and scale."""
    assert len(layout.boards) == 2, "decomposition needs a two-board layout"
    U, V, mask, dirs, el, az, _ = field.uv_grid(0.006)
    a, b = layout.boards
    amps = layout.amplitudes()
    aa = amps[:C.N_PER_BOARD]
    ab = amps[C.N_PER_BOARD:]
    pa = field.far_field(a.positions, a.normals, aa, dirs)
    pb = field.far_field(b.positions, b.normals, ab, dirs)
    ps = pa + pb
    peak = float(abs(ps).max())
    ring = math.sin(math.radians(C.GRATING_ANGLE_DEG))
    circle = np.linspace(0, 2 * math.pi, 300)

    fig, axes = plt.subplots(2, 2, figsize=(11.4, 9.6))
    ax_a, ax_b, ax_s, ax_c = axes.ravel()
    for ax, data, title in (
        (ax_a, pa, "Board A alone"),
        (ax_b, pb, "Board B alone"),
        (ax_s, ps, "A + B, coherent sum"),
    ):
        db = 20 * np.log10(np.maximum(abs(data) / peak, 10 ** (FLOOR / 20)))
        Z = np.full(U.shape, np.nan)
        Z[mask] = np.clip(db, FLOOR, 0)
        mesh = ax.pcolormesh(U, V, Z, cmap=RAMP, vmin=FLOOR, vmax=0,
                             shading="auto", rasterized=True)
        ax.plot(ring * np.cos(circle), ring * np.sin(circle), color=CYAN,
                lw=1.1, ls=(0, (4, 3)))
        for ux, uy in ((ring, 0), (-ring, 0), (0, ring), (0, -ring)):
            ax.plot([ux], [uy], marker="+", ms=8, color=CYAN, mew=1.3)
        ax.set_xlim(-1.02, 1.02)
        ax.set_ylim(-1.02, 1.02)
        ax.set_aspect("equal")
        ax.set_xlabel("u$_x$")
        ax.set_ylabel("u$_y$")
        ax.set_title(title, fontsize=10, loc="left", color=INK_2)
        for s_ in ("top", "right"):
            ax.spines[s_].set_visible(False)
    cax = fig.add_axes([0.935, 0.57, 0.012, 0.31])
    cb = fig.colorbar(mesh, cax=cax)
    cb.set_label("dB re the sum's main peak", fontsize=8)
    cb.ax.tick_params(labelsize=7, length=2)
    cb.outline.set_edgecolor(GRID)

    elc = np.arange(44.0, 66.0 + 0.02, 0.02)
    dirc = np.stack([field.dir_from_angles(e, 0.0) for e in elc])
    fa = field.far_field(a.positions, a.normals, aa, dirc)
    fb = field.far_field(b.positions, b.normals, ab, dirc)
    fs = field.far_field(layout.positions, layout.normals,
                         layout.amplitudes(), dirc)
    for data, color, label in ((fa, GRAY, "A alone"), (fb, ORANGE, "B alone"),
                               (fs, BLUE, "A + B")):
        lev = 20 * np.log10(np.maximum(abs(data) / peak, 1e-6))
        ax_c.plot(elc, np.clip(lev, -50, 0), color=color, lw=1.7, label=label)
    ax_c.axvline(C.GRATING_ANGLE_DEG, color=CYAN, lw=1.1, ls=(0, (4, 3)))
    ax_c.set_xlim(44, 66)
    ax_c.set_ylim(-50, 0)
    ax_c.set_xlabel("elevation through the φ = 0 lobe (deg)")
    ax_c.set_ylabel("dB re the sum's main peak")
    ax_c.set_title("Cut through the lobe", fontsize=10, loc="left", color=INK_2)
    ax_c.grid(color=GRID, lw=0.7)
    ax_c.legend(frameon=False, fontsize=8.5, loc="lower left")
    for s_ in ("top", "right"):
        ax_c.spines[s_].set_visible(False)

    fig.suptitle(f"Far-field decomposition — {layout.title}", fontsize=13,
                 fontweight="bold", x=0.012, ha="left", color=INK, y=0.98)
    fig.text(0.012, 0.935,
             "Both boards are identical 16 x 16 arrays, so their individual "
             "patterns coincide (the A and B curves overlap); the null exists "
             "only in the coherent sum. Cyan = 54.75° grating ring.",
             fontsize=8.5, color=INK_2, ha="left", va="top")
    fig.subplots_adjust(left=0.07, right=0.905, top=0.90, bottom=0.07,
                        wspace=0.25, hspace=0.28)
    fig.savefig(path, dpi=300)
    plt.close(fig)
