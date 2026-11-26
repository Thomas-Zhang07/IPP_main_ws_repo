"""Steering study for the candidate board arrangements.

Seven setups, each steered in x with a continuous linear phase ramp from 0 to
70 deg in 5 deg steps, in two element models:

    isotropic  - array factor only (no transducer directivity)
    measured   - the digitized TR4010HC pattern, evaluated against each
                 element's own board normal (so tilted boards tilt their
                 element patterns too)

Every steering angle is written as its own image; there are no montages.

``figures/steering/<layout>/``
    isotropic/{3d,polar,uv}/steer_XX.png
    measured/{3d,polar,uv}/steer_XX.png
    amplitude/steer_XX.png        level vs angle, both cases overlaid
    summary/*.png                 four steering-curve charts
    metrics.csv
``figures/steering/summary_all/``  cross-layout charts (measured element)
``figures/steering/metrics_all.csv``

Run::

    python sim/steering_study.py
"""

from __future__ import annotations

import csv
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import colors

import constants as C
import field
import geometry
import render_png as R
import transducer

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "figures" / "steering"

STEERS = np.arange(0, 71, 5)
ELEMENTS = ("isotropic", "measured")
ELEMENT_LABEL = {
    "isotropic": "no transducer (isotropic elements)",
    "measured": "measured TR4010HC pattern",
}
SHORT_LABEL = {
    "isotropic": "no transducer (isotropic)",
    "measured": "measured TR4010HC",
}
SETUPS = (
    ("01_single", "Single board", geometry.single),
    ("03_v120", "V 120°", lambda: geometry.v_pair(
        120.0, "03_v120", "Two boards, V 120 deg")),
    ("02_v150", "V 150°", lambda: geometry.v_pair(
        150.0, "02_v150", "Two boards, V 150 deg")),
    ("05_coplanar_gap", "Current pair", geometry.coplanar_gap),
    ("09_pair_seam_only", "Same seam, y = 0", geometry.pair_seam_only),
    ("07_concave3", "Concave 3-board", lambda: geometry.concave3(30.0)),
    ("08_coplanar3", "Coplanar 3-board", geometry.coplanar3),
)
SETUP_COLORS = (R.GRAY, R.BLUE, R.ORANGE, R.AQUA, R.VIOLET, R.RED, R.DARK)

DU = 0.008          # direction-cosine grid for maps
CUT_STEP = 0.05     # deg, x-z cut
FLOOR = -40.0
MAIN_WINDOW = 12.0  # deg around the steering angle
SIDELOBE_CONE = 15.0


def steer_u0(steer_deg: float) -> float:
    return float(np.sin(np.radians(steer_deg)))


def grating_deg(steer_deg: float) -> float:
    """Direction of the m = -1 grating lobe of the 10.5 mm pitch."""
    s = np.sin(np.radians(steer_deg)) - C.WAVELENGTH_M / C.PITCH_M
    return float(np.degrees(np.arcsin(np.clip(s, -1.0, 1.0))))


def pattern(layout, dirs: np.ndarray, u0: float, element: str,
            chunk: int = 2048, v0: float = 0.0, *, phase_law="xyz") -> np.ndarray:
    """Complex pressure for a linear phase ramp steering to ``(u0, v0)``.

    The measured element factor is evaluated per element against that
    element's own normal, so tilted boards carry their own beam tilt.
    """
    return _patterns(layout, dirs, [u0], [v0], [element], chunk, phase_law)[element][:, 0]


def _patterns(layout, dirs, u0, v0, elements, chunk=512, phase_law="xyz"):
    """Use forward unit command vectors, or the old projected ramp as a control."""
    if set(elements) - set(ELEMENT_LABEL):
        raise ValueError("unknown element model")
    pos, nrm = layout.positions, layout.normals
    w2 = 1 - np.square(u0) - np.square(v0)
    if np.any(w2 < -1e-12):
        raise ValueError("command outside forward hemisphere")
    if phase_law not in ("xyz", "projected_xy"):
        raise ValueError("unknown steering phase law")
    w0 = np.sqrt(np.maximum(w2, 0)) if phase_law == "xyz" else np.zeros_like(w2)
    steer = np.exp(-1j * C.WAVE_NUMBER * (pos @ np.array([u0, v0, w0])))
    out = {key: np.empty((len(dirs), len(u0)), dtype=complex) for key in elements}
    for s in range(0, dirs.shape[0], chunk):
        d = dirs[s:s + chunk]
        ph = np.exp(1j * C.WAVE_NUMBER * (d @ pos.T))
        for key in elements:
            kernel = ph if key == "isotropic" else ph * transducer.amplitude(d @ nrm.T)
            out[key][s:s + chunk] = kernel @ steer
    return out


def cut_x(layout, u0: float, element: str):
    """x-z plane cut: elevation alpha in [-90, 90] deg from +z toward +x."""
    alpha, dirs = _cut_grid()
    return alpha, np.abs(pattern(layout, dirs, u0, element))


def _cut_grid():
    alpha = np.linspace(-90.0, 90.0, round(180.0 / CUT_STEP) + 1)
    rad = np.radians(alpha)
    dirs = np.column_stack([np.sin(rad), np.zeros_like(rad), np.cos(rad)])
    return alpha, dirs


def v_microphone_check(layout, distance_m=2.0):
    """Broadside plane-wave drive, receiver on +z from the hinge midpoint."""
    if not np.isfinite(distance_m) or distance_m <= layout.positions[:, 2].max():
        raise ValueError("microphone must be in front of the aperture")
    pos = layout.positions
    mic = np.array([[0., 0., distance_m]])
    delta = mic - pos
    r = np.linalg.norm(delta, axis=1)
    weights = np.exp(-1j * C.WAVE_NUMBER * pos[:, 2])
    pressure = field.near_field_points(pos, layout.normals, weights, mic,
                                       element_pattern=transducer.amplitude)[0]
    cos_beta = np.einsum("ij,ij->i", delta / r[:, None], layout.normals)
    upper_bound = np.sum(transducer.amplitude(cos_beta) / r)
    spread = np.ptp(r - (distance_m - pos[:, 2]))
    return {"layout": layout.key, "mic_z_m": distance_m,
            "curvature_spread_mm": 1e3 * spread,
            "curvature_spread_deg": np.degrees(C.WAVE_NUMBER * spread),
            "level_re_coherent_bound_db": 20 * np.log10(abs(pressure) / upper_bound)}


def _local_peak(alpha, mag, center: float, halfwidth: float = MAIN_WINDOW):
    sel = np.abs(alpha - center) <= halfwidth
    if not sel.any():
        return float("nan"), float("nan")
    idx = np.flatnonzero(sel)[int(np.argmax(mag[sel]))]
    return float(alpha[idx]), float(mag[idx])


def _to_db(mag: np.ndarray, peak: float) -> np.ndarray:
    return 20.0 * np.log10(np.maximum(mag / peak, 10.0 ** (FLOOR / 20.0)))


def study(phase_law=None):
    U2, _, mask, uv_dirs, _, _, _ = field.uv_grid(DU)
    alpha, cut_dirs = _cut_grid()
    th, _, surface_dirs = _surface_grid()
    dirs = np.vstack((uv_dirs, cut_dirs, surface_dirs))
    uv_end = len(uv_dirs)
    cut_end = uv_end + len(cut_dirs)
    el = np.degrees(np.arccos(np.clip(dirs[:, 2], -1, 1)))
    az = np.degrees(np.arctan2(dirs[:, 1], dirs[:, 0]))
    results, rows = {}, []
    for key, title, ctor in SETUPS:
        layout = ctor()
        # Retain the three-board concave study as a projected-drive control.
        drive = phase_law or ("projected_xy" if key == "07_concave3" else "xyz")
        fields = _patterns(layout, dirs, np.sin(np.radians(STEERS)),
                           np.zeros(len(STEERS)), ELEMENTS, phase_law=drive)
        for element in ELEMENTS:
            for j, steer in enumerate(STEERS):
                abl = np.abs(fields[element][:, j])
                peak = float(abl.max())
                db = _to_db(abl, peak)
                db2 = np.full(U2.shape, np.nan)
                db2[mask] = db[:uv_end]
                mag = abl[uv_end:cut_end]
                cut_db = db[uv_end:cut_end]
                main_ang, main_mag = _local_peak(alpha, mag, float(steer))
                a = np.radians(main_ang)
                main_dir = np.array([np.sin(a), 0.0, np.cos(a)])
                cosang = np.clip(dirs @ main_dir, -1.0, 1.0)
                outside = np.degrees(np.arccos(cosang)) > SIDELOBE_CONE
                if outside.any():
                    i = int(np.argmax(np.where(outside, abl, -1.0)))
                    side_level = float(20.0 * np.log10(max(abl[i] / peak, 1e-12)))
                    side_dir = dirs[i]
                    side_el, side_az = float(el[i]), float(az[i])
                else:
                    side_level = float("nan")
                    side_dir = None
                    side_el = side_az = float("nan")
                main_level = 20.0 * np.log10(
                    max(main_mag, 1e-12) / max(peak, 1e-12))
                results[(key, element, float(steer))] = {
                    "db2": db2, "alpha": alpha, "cut_db": cut_db,
                    "surface_db": db[cut_end:].reshape(th.shape),
                    "main_dir": main_dir, "main_angle": main_ang,
                    "main_level": main_level,
                    "side_dir": side_dir, "side_level": side_level,
                    "side_el": side_el, "side_az": side_az,
                }
                rows.append({
                    "layout": key, "layout_title": title,
                    "phase_law": drive,
                    "element": element, "steer_deg": float(steer),
                    "main_angle_deg": main_ang,
                    "main_level_db": main_level,
                    "sidelobe_el_deg": side_el,
                    "sidelobe_az_deg": side_az,
                    "sidelobe_level_db": side_level,
                    "sidelobe_minus_main_db": side_level - main_level,
                })
    return results, rows


def _footnote(fig, text: str) -> None:
    fig.text(0.01, 0.015, text, fontsize=7.5, color=R.MUTED, ha="left")


def _surface_grid():
    th = np.radians(np.linspace(0.0, 90.0, 61))
    ph = np.radians(np.linspace(0.0, 360.0, 180, endpoint=False))
    TH, PH = np.meshgrid(th, ph, indexing="ij")
    dirs = np.column_stack([
        np.sin(TH).ravel() * np.cos(PH).ravel(),
        np.sin(TH).ravel() * np.sin(PH).ravel(),
        np.cos(TH).ravel(),
    ])
    return TH, PH, dirs


def _lobe_xyz(direction, level):
    r = 0.02 + 0.58 * np.clip((level - FLOOR) / (0.0 - FLOOR), 0.0, 1.0)
    return r * direction


def one_3d(layout, element: str, steer: float, res: dict,
           path: Path) -> None:
    """Matches the web pages: compact lit surface, boards, grating ring."""
    TH, PH, _ = _surface_grid()
    db = res["surface_db"]
    radius = 0.02 + 0.58 * np.clip((db - FLOOR) / (0.0 - FLOOR), 0.0, 1.0)
    x = np.sin(TH) * np.cos(PH) * radius
    y = np.sin(TH) * np.sin(PH) * radius
    z = np.cos(TH) * radius

    norm = colors.Normalize(vmin=FLOOR, vmax=0.0)
    rgb = R.RAMP(norm(db))[..., :3]
    lit = colors.LightSource(azdeg=315, altdeg=45).shade_rgb(
        rgb, z, blend_mode="soft")
    facecolors = np.concatenate(
        [lit, np.full(lit.shape[:2] + (1,), 0.98)], axis=-1)

    fig = plt.figure(figsize=(7.6, 7.0))
    ax = fig.add_axes([0.02, 0.02, 0.88, 0.86], projection="3d")
    ax.plot_surface(x, y, z, facecolors=facecolors, rstride=1, cstride=1,
                    linewidth=0, antialiased=False, shade=False)

    for board in layout.boards:
        ax.plot(board.outline[:, 0], board.outline[:, 1], board.outline[:, 2],
                color="#2f6b4f", lw=1.0)
        ax.scatter(board.positions[:, 0], board.positions[:, 1],
                   board.positions[:, 2], s=0.6, color="#d8c08a",
                   depthshade=False)

    ug = np.sin(np.radians(54.75))
    uz = np.cos(np.radians(54.75))
    t = np.linspace(0.0, 2.0 * np.pi, 240)
    ax.plot(0.42 * ug * np.cos(t), 0.42 * ug * np.sin(t),
            np.full_like(t, 0.42 * uz), color=R.CYAN, lw=1.0, alpha=0.75)

    lobes = [(res["main_dir"], res["main_level"], R.BLUE, "main")]
    if res["side_dir"] is not None and np.isfinite(res["side_level"]):
        lobes.append((res["side_dir"], res["side_level"], R.ORANGE, "sidelobe"))
    for direction, level, colour, name in lobes:
        px, py, pz = _lobe_xyz(np.asarray(direction, float), level)
        ax.scatter([px], [py], [pz], color=colour, s=24, depthshade=False)
        ax.text(px, py, pz + 0.05, f"{name} {level:.1f} dB", fontsize=6.5,
                color=colour, ha="center", va="bottom")

    ax.set_xlim(-0.62, 0.62)
    ax.set_ylim(-0.62, 0.62)
    ax.set_zlim(-0.40, 0.80)
    ax.set_box_aspect((1.0, 1.0, 1.0), zoom=1.7)
    ax.set_axis_off()
    ax.view_init(elev=50.0, azim=40.0)

    fig.suptitle(f"3D far-field · steer {steer:.0f}°", fontsize=13,
                 fontweight="bold", x=0.02, ha="left", y=0.97)
    fig.text(0.02, 0.925, f"{SHORT_LABEL[element]} · {layout.title}",
             fontsize=9.5, color=R.INK_2, ha="left")
    cax = fig.add_axes([0.93, 0.30, 0.015, 0.45])
    fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=R.RAMP), cax=cax,
                 label="dB re peak")
    _footnote(fig, "Surface radius linear in dB above −40 dB; cyan ring = "
                   "flat-board broadside grating-angle reference.")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def one_polar(res, element: str, layout, steer: float, path: Path) -> None:
    alpha, db = res["alpha"], res["cut_db"]
    theta_p = np.radians(90.0 - alpha)
    radius = np.clip((db - FLOOR) / (0.0 - FLOOR), 0.0, 1.0)
    fig = plt.figure(figsize=(6.2, 4.6))
    ax = fig.add_subplot(111, projection="polar")
    ax.plot(theta_p, radius, color=R.INK, lw=1.1)
    ax.fill(theta_p, radius, color=R.BLUE, alpha=0.12)
    ax.set_thetamin(0)
    ax.set_thetamax(180)
    ax.set_ylim(0, 1.15)
    ax.set_yticks([0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels([])
    ax.set_xticks(np.radians([0, 45, 90, 135, 180]))
    ax.set_xticklabels([])
    ax.tick_params(length=0)
    markers = [(float(steer), R.BLUE)]
    if res["side_dir"] is not None:
        az = res["side_az"]
        if abs(az) < 5.0 or abs(az) > 175.0:
            side_alpha = res["side_el"] * (1.0 if abs(az) < 5.0 else -1.0)
            markers.append((side_alpha, R.ORANGE))
    for ang, col in markers:
        ax.plot([np.radians(90.0 - ang)], [1.07], "o", color=col, ms=6)
    ax.set_title(f"Polar cut, x–z · steer {steer:.0f}°", fontsize=13,
                 fontweight="bold", pad=14)
    fig.text(0.02, 0.90, f"{SHORT_LABEL[element]} · {layout.title}",
             fontsize=9, color=R.INK_2, ha="left")
    fig.text(0.02, 0.06, "blue dot = steering direction · orange dot = "
             "strongest sidelobe (when in the cut) · rings at 0, −10, −20, "
             "−30 dB · 0° at the top",
             fontsize=7.2, color=R.MUTED, ha="left")
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def one_uv(res, element: str, layout, steer: float, path: Path) -> None:
    db2 = res["db2"]
    ring = C.WAVELENGTH_M / C.PITCH_M
    t = np.linspace(0.0, 2.0 * np.pi, 400)
    fig, ax = plt.subplots(figsize=(6.4, 5.6))
    im = ax.imshow(np.ma.masked_invalid(db2), origin="lower",
                   extent=[-1, 1, -1, 1], cmap=R.RAMP, vmin=FLOOR, vmax=0.0,
                   interpolation="nearest")
    ax.plot(ring * np.cos(t), ring * np.sin(t), color=R.CYAN, lw=0.9, ls="--")
    md = np.asarray(res["main_dir"], float)
    ax.plot([md[0]], [md[1]], "+", color="white", ms=11, mew=1.5)
    if res["side_dir"] is not None:
        sd = np.asarray(res["side_dir"], float)
        ax.plot([sd[0]], [sd[1]], "o", mfc="none", mec=R.ORANGE, ms=8, mew=1.4)
    ax.set_xlim(-1, 1)
    ax.set_ylim(-1, 1)
    ax.set_aspect("equal")
    ax.set_xlabel("u = sinθ cosφ")
    ax.set_ylabel("v = sinθ sinφ")
    fig.suptitle(f"UV-space map · steer {steer:.0f}°", fontsize=13,
                 fontweight="bold", x=0.02, ha="left", y=0.97)
    fig.text(0.02, 0.925, f"{SHORT_LABEL[element]} · {layout.title}",
             fontsize=9, color=R.INK_2, ha="left")
    fig.text(0.02, 0.05, "white cross = main beam · orange circle = strongest "
             "outside 15° · dashed ring = flat-board broadside λ/d",
             fontsize=7.2, color=R.MUTED, ha="left")
    fig.colorbar(im, ax=ax, shrink=0.85, label="dB re peak")
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def one_amplitude_case(results, element: str, layout, steer: float,
                       path: Path) -> None:
    res = results[(layout.key, element, float(steer))]
    colour = R.GRAY if element == "isotropic" else R.BLUE
    fig, ax = plt.subplots(figsize=(9.5, 4.8))
    ax.plot(res["alpha"], res["cut_db"], color=colour, lw=1.3)
    ax.axvline(float(steer), color=R.BLUE, lw=0.9, ls=":")
    for ang in (-54.75, 54.75):
        ax.axvline(ang, color=R.ORANGE, lw=0.8, ls=":")
    ax.set_xlim(-90, 90)
    ax.set_ylim(FLOOR, 3)
    ax.set_xlabel("angle in x–z (deg)")
    ax.set_ylabel("level (dB re peak)")
    ax.grid(alpha=0.22, lw=0.6)
    ax.set_title(f"Amplitude vs angle · {layout.title} · steer {steer:.0f}°",
                 fontsize=12, fontweight="bold", loc="left")
    ax.text(0.01, 0.03, SHORT_LABEL[element], transform=ax.transAxes,
            fontsize=8.5, color=colour, ha="left", va="bottom")
    fig.text(0.01, 0.005, "dotted blue = steering direction · dotted orange = "
             "±54.75° flat-board broadside reference · linear amplitude = 10^(dB/20)",
             fontsize=7.5, color=R.MUTED)
    fig.tight_layout(rect=(0, 0.035, 1, 1))
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def one_amplitude(results, layout, steer: float, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(9.5, 4.8))
    for element, colour in (("isotropic", R.GRAY), ("measured", R.BLUE)):
        res = results[(layout.key, element, float(steer))]
        ax.plot(res["alpha"], res["cut_db"], color=colour, lw=1.15,
                label=ELEMENT_LABEL[element])
    ax.axvline(float(steer), color=R.BLUE, lw=0.9, ls=":")
    for ang in (-54.75, 54.75):
        ax.axvline(ang, color=R.ORANGE, lw=0.8, ls=":")
    ax.set_xlim(-90, 90)
    ax.set_ylim(FLOOR, 3)
    ax.set_xlabel("angle in x–z (deg)")
    ax.set_ylabel("level (dB re peak)")
    ax.grid(alpha=0.22, lw=0.6)
    ax.legend(fontsize=8, loc="lower left")
    ax.set_title(f"Amplitude vs angle · {layout.title} · steer {steer:.0f}°",
                 fontsize=12, fontweight="bold", loc="left")
    fig.text(0.01, 0.02, "dotted blue = steering direction · dotted orange = "
             "±54.75° flat-board broadside reference · linear amplitude = 10^(dB/20)",
             fontsize=7.5, color=R.MUTED, ha="left")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def _rows_for(rows, layout_key, element=None):
    sel = [r for r in rows if r["layout"] == layout_key]
    if element is not None:
        sel = [r for r in sel if r["element"] == element]
    return sel


def layout_summaries(rows, layout_key: str) -> None:
    steers = STEERS.astype(float)
    out = OUT / layout_key / "summary"
    measured = _rows_for(rows, layout_key, "measured")

    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    for element, colour in (("isotropic", R.GRAY), ("measured", R.BLUE)):
        vals = [r["main_angle_deg"] for r in _rows_for(rows, layout_key, element)]
        ax.plot(steers, vals, "-o", color=colour, ms=4, lw=1.3,
                label=ELEMENT_LABEL[element])
    ax.plot(steers, steers, color=R.MUTED, lw=0.8, ls=":",
            label="commanded angle")
    ax.set_xlabel("steering angle (deg)")
    ax.set_ylabel("main-beam direction in x–z (deg)")
    ax.set_title("Main-beam direction", fontsize=13, loc="left")
    ax.grid(alpha=0.22)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out / "main_direction.png", dpi=160, bbox_inches="tight")
    plt.close(fig)

    charts = (
        ("main_level_db", "Main-beam level", "main_beam_level.png"),
        ("sidelobe_level_db", "Strongest sidelobe level",
         "sidelobe_level.png"),
        ("sidelobe_minus_main_db", "Sidelobe minus main",
         "sidelobe_minus_main.png"),
    )
    for key, title, name in charts:
        fig, ax = plt.subplots(figsize=(8.5, 4.8))
        for element, colour in (("isotropic", R.GRAY), ("measured", R.BLUE)):
            vals = [r[key] for r in _rows_for(rows, layout_key, element)]
            ax.plot(steers, vals, "-o", color=colour, ms=4, lw=1.3,
                    label=ELEMENT_LABEL[element])
        if key == "sidelobe_minus_main_db":
            ax.axhline(0.0, color=R.RED, lw=0.9, ls="--")
            above = [r["steer_deg"] for r in measured
                     if np.isfinite(r[key]) and r[key] > 0.0]
            if above:
                ax.annotate(
                    f"sidelobe stronger from {min(above):.0f}°",
                    xy=(min(above), 0.0), xytext=(min(above) + 5, 5),
                    fontsize=8, color=R.INK_2,
                    arrowprops=dict(arrowstyle="->", color=R.MUTED, lw=0.8))
        ax.set_xlabel("steering angle (deg)")
        ax.set_ylabel("dB re peak")
        ax.set_title(title, fontsize=13, loc="left")
        ax.grid(alpha=0.22)
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(out / name, dpi=160, bbox_inches="tight")
        plt.close(fig)


def cross_summaries(rows) -> None:
    steers = STEERS.astype(float)
    out = OUT / "summary_all"
    charts = (
        ("main_level_db", "Main-beam level", "all_main_level.png"),
        ("sidelobe_level_db", "Strongest sidelobe level",
         "all_sidelobe_level.png"),
        ("sidelobe_minus_main_db", "Sidelobe minus main",
         "all_sidelobe_minus_main.png"),
    )
    for key, title, name in charts:
        fig, ax = plt.subplots(figsize=(10.5, 5.4))
        for (layout_key, label, _), colour in zip(SETUPS, SETUP_COLORS):
            vals = [r[key] for r in _rows_for(rows, layout_key, "measured")]
            ax.plot(steers, vals, "-o", color=colour, ms=3.5, lw=1.4,
                    label=label)
        if key == "sidelobe_minus_main_db":
            ax.axhline(0.0, color=R.RED, lw=0.9, ls="--")
        ax.set_xlabel("steering angle (deg)")
        ax.set_ylabel("dB re peak")
        ax.set_title(f"{title} — measured element", fontsize=13, loc="left")
        ax.grid(alpha=0.22)
        ax.legend(fontsize=8, ncol=2)
        fig.tight_layout()
        fig.savefig(out / name, dpi=160, bbox_inches="tight")
        plt.close(fig)

    fig, ax = plt.subplots(figsize=(10.5, 5.4))
    for (layout_key, label, _), colour in zip(SETUPS, SETUP_COLORS):
        vals = [r["main_angle_deg"]
                for r in _rows_for(rows, layout_key, "measured")]
        ax.plot(steers, vals, "-o", color=colour, ms=3.5, lw=1.4, label=label)
    ax.plot(steers, steers, color=R.MUTED, lw=0.8, ls=":",
            label="commanded angle")
    ax.set_xlabel("steering angle (deg)")
    ax.set_ylabel("main-beam direction in x–z (deg)")
    ax.set_title("Main-beam direction — measured element", fontsize=13,
                 loc="left")
    ax.grid(alpha=0.22)
    ax.legend(fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(out / "all_main_direction.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


CSV_FIELDS = ["layout", "element", "phase_law", "steer_deg", "main_angle_deg",
              "main_level_db", "sidelobe_el_deg", "sidelobe_az_deg",
              "sidelobe_level_db", "sidelobe_minus_main_db"]


def write_csv(rows, path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: (f"{r[k]:.3f}" if isinstance(r[k], float) else r[k])
                        for k in CSV_FIELDS})


def main(phase_law=None) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for key, _, _ in SETUPS:
        for sub in ("isotropic/3d", "isotropic/polar", "isotropic/uv",
                    "measured/3d", "measured/polar", "measured/uv",
                    "isotropic/amplitude", "measured/amplitude",
                    "amplitude", "summary"):
            (OUT / key / sub).mkdir(parents=True, exist_ok=True)
    (OUT / "summary_all").mkdir(parents=True, exist_ok=True)

    print(f"computing {len(SETUPS)} layouts x 2 cases x {len(STEERS)} angles ...")
    if phase_law is None:
        checks = [v_microphone_check(ctor()) for key, _, ctor in SETUPS
                  if key in ("02_v150", "03_v120")]
        if checks:
            with (OUT / "v_microphone_2m.csv").open("w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=checks[0].keys())
                writer.writeheader()
                writer.writerows(checks)
    results, rows = study(phase_law)
    write_csv(rows, OUT / "metrics_all.csv")

    for key, title, _ in SETUPS:
        # rebuild the layout object for titles/boards in the figure functions
        ctor = dict((k, f) for k, _, f in SETUPS)[key]
        layout = ctor()
        per = OUT / key
        write_csv([r for r in rows if r["layout"] == key], per / "metrics.csv")
        print(f"figures {title} ...")
        for steer in STEERS:
            tag = f"steer_{steer:02.0f}.png"
            for element in ELEMENTS:
                res = results[(key, element, float(steer))]
                one_3d(layout, element, float(steer), res,
                       per / element / "3d" / tag)
                one_polar(res, element, layout, float(steer),
                          per / element / "polar" / tag)
                one_uv(res, element, layout, float(steer),
                       per / element / "uv" / tag)
                one_amplitude_case(results, element, layout, float(steer),
                                   per / element / "amplitude" / tag)
            one_amplitude(results, layout, float(steer),
                          per / "amplitude" / tag)
        layout_summaries(rows, key)
    print("cross-layout summaries")
    cross_summaries(rows)
    print(f"wrote {OUT}")
    for key, title, _ in SETUPS:
        me = _rows_for(rows, key, "measured")
        print(f"  {key:18s} " + "  ".join(
            f"steer {r['steer_deg']:.0f}°: side {r['sidelobe_level_db']:.1f}"
            for r in me[::3]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--phase-law", choices=("xyz", "projected_xy"),
                        help="override the study defaults for comparison")
    parser.add_argument("--out", type=Path, help="separate results directory")
    args = parser.parse_args()
    if args.phase_law and (args.out is None or args.out.resolve() == OUT.resolve()):
        parser.error("--phase-law needs a separate --out directory")
    if args.out is not None:
        OUT = args.out
    main(args.phase_law)
