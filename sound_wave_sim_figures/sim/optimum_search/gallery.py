"""Full-steering galleries for the recommended optima."""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import colors
import numpy as np

import constants as C
import field
import render_png as R

from . import metrics, model

AZIMUTHS = (0.0, 45.0, 90.0, 135.0, 180.0, 225.0, 270.0, 315.0)
STEERING_STATES = ([(0.0, 0.0)]
                   + [(float(t), float(a))
                      for t in np.arange(5.0, 35.0 + 1e-9, 5.0)
                      for a in AZIMUTHS])
FLOOR = -40.0


def _state(theta, phi):
    t, p = np.radians(theta), np.radians(phi)
    return np.sin(t) * np.cos(p), np.sin(t) * np.sin(p)


def _plane_dirs(phi, n=721):
    alpha = np.linspace(-90.0, 90.0, n)
    a, p = np.radians(alpha), np.radians(phi)
    return alpha, np.column_stack([np.sin(a) * np.cos(p),
                                   np.sin(a) * np.sin(p), np.cos(a)])


def _db(mag, peak):
    return 20.0 * np.log10(np.maximum(mag / max(peak, 1e-12),
                                      10.0 ** (FLOOR / 20.0)))


def _tag(theta, phi):
    return f"steer_{theta:02.0f}_{phi:03.0f}.png"


def _view_levels(measured_fn, iso_fn, theta, phi, du=0.008):
    th = np.radians(np.linspace(0.0, 90.0, 61))
    ph = np.radians(np.linspace(0.0, 360.0, 180, endpoint=False))
    TH, PH = np.meshgrid(th, ph, indexing="ij")
    dirs = np.column_stack([np.sin(TH).ravel() * np.cos(PH).ravel(),
                            np.sin(TH).ravel() * np.sin(PH).ravel(),
                            np.cos(TH).ravel()])
    U2, _, mask, uv, _, _, _ = field.uv_grid(du)
    alpha, cut = _plane_dirs(phi)
    u0, v0 = _state(theta, phi)
    command = metrics._direction(theta, phi)[None, :]
    all_dirs = np.vstack((dirs, uv, cut, command))
    iso = np.abs(iso_fn(all_dirs, u0, v0))
    mag = np.abs(measured_fn(all_dirs, u0, v0))
    levels = _db(mag, mag.max())
    i, j = len(dirs), len(dirs) + len(uv)
    db2 = np.full(U2.shape, np.nan)
    db2[mask] = levels[i:j]
    return {"surface": (TH, PH, levels[:i].reshape(TH.shape)), "uv": db2,
            "alpha": alpha, "measured": levels[j:-1],
            "isotropic": _db(iso[j:-1], iso.max())}


def _render_3d(label, theta, phi, path, views):
    TH, PH, db = views["surface"]
    radius = 0.02 + 0.58 * np.clip((db - FLOOR) / (0.0 - FLOOR), 0.0, 1.0)
    x = np.sin(TH) * np.cos(PH) * radius
    y = np.sin(TH) * np.sin(PH) * radius
    z = np.cos(TH) * radius
    norm = colors.Normalize(vmin=FLOOR, vmax=0.0)
    rgb = R.RAMP(norm(db))[..., :3]
    lit = colors.LightSource(azdeg=315, altdeg=45).shade_rgb(
        rgb, z, blend_mode="soft")
    face = np.concatenate([lit, np.full(lit.shape[:2] + (1,), 0.98)], axis=-1)
    fig = plt.figure(figsize=(6.6, 6.2))
    ax = fig.add_axes([0.02, 0.02, 0.9, 0.86], projection="3d")
    ax.plot_surface(x, y, z, facecolors=face, rstride=1, cstride=1,
                    linewidth=0, antialiased=False, shade=False)
    ring = C.WAVELENGTH_M / C.PITCH_M
    t = np.linspace(0.0, 2.0 * np.pi, 240)
    ax.plot(0.42 * ring * np.cos(t), 0.42 * ring * np.sin(t),
            np.full_like(t, 0.42 * np.sqrt(1.0 - ring * ring)),
            color=R.CYAN, lw=0.9, alpha=0.7)
    ax.set_xlim(-0.62, 0.62)
    ax.set_ylim(-0.62, 0.62)
    ax.set_zlim(-0.40, 0.80)
    ax.set_box_aspect((1.0, 1.0, 1.0), zoom=1.7)
    ax.set_axis_off()
    ax.view_init(elev=45.0, azim=float(phi) - 90.0)
    fig.suptitle(f"3D far-field · steer {theta:.0f}° / {phi:.0f}°",
                 fontsize=12, fontweight="bold", x=0.02, ha="left", y=0.97)
    fig.text(0.02, 0.93, label, fontsize=8.5, color=R.INK_2)
    cax = fig.add_axes([0.93, 0.3, 0.015, 0.45])
    fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=R.RAMP), cax=cax,
                 label="dB re peak")
    fig.savefig(path, dpi=140, bbox_inches="tight")
    plt.close(fig)


def _render_polar(label, theta, phi, path, views):
    alpha, db = views["alpha"], views["measured"]
    radius = np.clip((db - FLOOR) / (0.0 - FLOOR), 0.0, 1.0)
    tp = np.radians(90.0 - alpha)
    fig = plt.figure(figsize=(6.0, 4.4))
    ax = fig.add_subplot(111, projection="polar")
    ax.plot(tp, radius, color=R.INK, lw=1.1)
    ax.fill(tp, radius, color=R.BLUE, alpha=0.12)
    ax.set_thetamin(0)
    ax.set_thetamax(180)
    ax.set_ylim(0, 1.12)
    ax.set_yticks([0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels([])
    ax.set_xticks(np.radians([0, 45, 90, 135, 180]))
    ax.set_xticklabels([])
    ax.tick_params(length=0)
    ax.plot([np.radians(90.0 - theta)], [1.06], "o", color=R.BLUE, ms=6)
    ax.set_title(f"Polar cut · steer {theta:.0f}° / {phi:.0f}°", fontsize=12,
                 fontweight="bold", pad=12)
    fig.text(0.02, 0.05, f"{label} · rings at 0, −10, −20, −30 dB",
             fontsize=7.5, color=R.MUTED)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _render_uv(label, theta, phi, path, views):
    u0, v0 = _state(theta, phi)
    db2 = views["uv"]
    fig, ax = plt.subplots(figsize=(5.8, 5.2))
    im = ax.imshow(np.ma.masked_invalid(db2), origin="lower",
                   extent=[-1, 1, -1, 1], cmap=R.RAMP, vmin=FLOOR, vmax=0.0,
                   interpolation="nearest")
    ring = C.WAVELENGTH_M / C.PITCH_M
    t = np.linspace(0.0, 2.0 * np.pi, 400)
    ax.plot(ring * np.cos(t), ring * np.sin(t), color=R.CYAN, lw=0.9, ls="--")
    ax.plot([u0], [v0], "+", color="white", ms=10, mew=1.4)
    ax.set_xlim(-1, 1)
    ax.set_ylim(-1, 1)
    ax.set_aspect("equal")
    ax.set_xlabel("u = sinθ cosφ")
    ax.set_ylabel("v = sinθ sinφ")
    ax.set_title(f"UV map · steer {theta:.0f}° / {phi:.0f}°", fontsize=12,
                 fontweight="bold", loc="left")
    fig.colorbar(im, ax=ax, shrink=0.85, label="dB re peak")
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _render_amplitude(label, theta, phi, path, views):
    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    for element, colour in (("isotropic", R.GRAY), ("measured", R.BLUE)):
        ax.plot(views["alpha"], views[element], color=colour, lw=1.15, label=element)
    ax.axvline(theta, color=R.BLUE, lw=0.9, ls=":")
    for ang in (-54.75, 54.75):
        ax.axvline(ang, color=R.ORANGE, lw=0.8, ls=":")
    ax.set_xlim(-90, 90)
    ax.set_ylim(FLOOR, 3)
    ax.set_xlabel("elevation in the steering plane (deg)")
    ax.set_ylabel("level (dB re peak)")
    ax.grid(alpha=0.22)
    ax.legend(fontsize=8, loc="lower left")
    ax.set_title(f"Amplitude vs angle · steer {theta:.0f}° / {phi:.0f}°",
                 fontsize=12, fontweight="bold", loc="left")
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def render_optimum(cand, out_dir, states=None, *, measured_fn=None,
                   iso_fn=None, label=None, score_fn=None) -> list[dict]:
    """Render a full steering gallery.

    ``cand`` may be None when ``measured_fn``/``iso_fn`` are supplied (the V
    layouts use their own exact model).
    """
    out = Path(out_dir)
    for sub in ("3d", "polar", "uv", "amplitude"):
        folder = out / sub
        folder.mkdir(parents=True, exist_ok=True)
        for old in folder.glob("*.png"):
            old.unlink()
    states = STEERING_STATES if states is None else states
    if measured_fn is None:
        measured_fn = lambda d, u, v: model.field_fast(cand, d, u, v)
    if iso_fn is None:
        iso_fn = lambda d, u, v: model.array_factor(cand, d, u, v)
    if score_fn is None:
        def score_fn(theta, phi):
            return metrics.score_states(cand, 0.01, [(theta, phi)], dirs=dirs)
    label = label or (getattr(cand, "key", "") if cand is not None else "")
    rows = []
    dirs, _, _, _ = model.direction_grid(0.01)
    for theta, phi in states:
        tag = _tag(theta, phi)
        views = _view_levels(measured_fn, iso_fn, theta, phi)
        _render_3d(label, theta, phi, out / "3d" / tag, views)
        _render_polar(label, theta, phi, out / "polar" / tag, views)
        _render_uv(label, theta, phi, out / "uv" / tag, views)
        _render_amplitude(label, theta, phi, out / "amplitude" / tag, views)
        comp = score_fn(theta, phi)
        rows.append({"theta": theta, "phi": phi, **comp})
    with open(out / "metrics.csv", "w", newline="", encoding="utf-8") as fh:
        fields = ["theta", "phi", "SL_cmd", "SL_clean", "SL_near", "SL_far_s",
                  "SL_diag"]
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: (f"{row[k]:.3f}" if isinstance(row[k], float)
                                 else row[k]) for k in fields})
    return rows
