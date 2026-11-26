"""Report-only figures for the Feishu workbench section.

Three compact panels that the existing galleries do not provide:

* ``element_pattern.png`` - the measured TR4010HC element against an ideal
  baffled 10 mm piston, linear and polar.
* ``mic2m.png`` - level at the 2 m microphone relative to the coherent bound
  for the two V layouts, with the per-emitter path spread.
* ``winners.png`` - worst sidelobe against contiguous 0 dB range for the three
  candidate families, winners marked.

Run::

    python report_figures.py
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import constants as C
import render_png as R
import transducer

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "figures" / "report"
DATA = ROOT / "data" / "search2"


def element_pattern(path: Path) -> None:
    theta = np.linspace(0.0, 180.0, 721)
    ka = C.WAVE_NUMBER * 0.005  # 10 mm piston radius, baffled
    x = ka * np.sin(np.radians(theta))
    from scipy.special import j1
    piston = np.where(x > 1e-9, 2.0 * j1(x) / np.maximum(x, 1e-12), 1.0)
    piston_db = 20.0 * np.log10(np.maximum(np.abs(piston), 1e-9))
    mean_db = transducer.level_db(theta, "mean")
    left_db = transducer.level_db(theta, "left")
    right_db = transducer.level_db(theta, "right")

    fig = plt.figure(figsize=(11.6, 4.4))
    ax = fig.add_subplot(1, 2, 1)
    ax.plot(theta, mean_db, color=R.INK, lw=1.8, label="measured, mean")
    ax.plot(theta, left_db, color=R.BLUE, lw=1.0, ls="--", label="left half")
    ax.plot(theta, right_db, color=R.ORANGE, lw=1.0, ls=":", label="right half")
    fwd = theta <= 90.0
    ax.plot(theta[fwd], piston_db[fwd], color=R.GRAY, lw=1.2, ls="-.",
            label="ideal 10 mm piston (0–90°)")
    ax.axhline(-6.0, color=R.GRID, lw=0.8)
    b_left = transducer.half_angle_6db("left")
    b_right = transducer.half_angle_6db("right")
    for b6 in (b_left, b_right):
        ax.axvline(b6, color=R.VIOLET, lw=0.9, ls=":")
    ax.annotate(f"−6 dB at {b_left:.0f}° / {b_right:.0f}°", (b_right, -6.0),
                xytext=(b_right + 6, -2.5),
                fontsize=8.5, color=R.VIOLET,
                arrowprops=dict(arrowstyle="->", color=R.VIOLET, lw=0.8))
    ax.axvline(54.75, color=R.AQUA, lw=1.0, ls="--")
    ax.annotate("array grating angle 54.75°", (54.75, -8), xytext=(72, -4),
                fontsize=8.5, color=R.AQUA,
                arrowprops=dict(arrowstyle="->", color=R.AQUA, lw=0.8))
    ax.set_xlim(0, 180)
    ax.set_ylim(-50, 3)
    ax.set_xticks(np.arange(0, 181, 30))
    ax.set_xlabel("angle from element axis (deg)")
    ax.set_ylabel("level (dB re on-axis)")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8, loc="lower left")
    ax.set_title("Measured element vs ideal piston", fontsize=12,
                 fontweight="bold", loc="left")

    # Hemisphere map of the measured element: radius = angle from the axis,
    # angle = azimuth, and the left/right halves follow the datasheet cut.
    th = np.linspace(0.0, 90.0, 181)
    ph = np.linspace(0.0, 360.0, 181)
    TH, PH = np.meshgrid(th, ph, indexing="ij")
    right = np.cos(np.radians(PH)) >= 0.0
    db = np.where(right, transducer.level_db(TH, "right"),
                  transducer.level_db(TH, "left"))
    ax = fig.add_subplot(1, 2, 2, projection="polar")
    mesh = ax.pcolormesh(np.radians(PH), TH, db, cmap=R.RAMP, vmin=-40,
                         vmax=0.0, shading="auto")
    ax.set_ylim(0, 90)
    ax.set_yticks([30, 60, 90])
    ax.set_yticklabels(["30°", "60°", "90°"], fontsize=8)
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.grid(alpha=0.3, color="white", lw=0.6)
    cb = fig.colorbar(mesh, ax=ax, shrink=0.85, pad=0.08)
    cb.set_label("dB re on-axis", fontsize=9)
    fig.suptitle(f"DI {transducer.di_db():.1f} dB · −6 dB beam "
                 f"{transducer.beamwidth_6db():.0f}° · side lobes ≈ −21 dB · "
                 f"rear ≈ −36 dB", fontsize=10.5, x=0.01, ha="left", y=0.995)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def mic2m(path: Path) -> None:
    rows = list(csv.DictReader(
        (ROOT / "figures/steering/v_microphone_2m.csv").open(encoding="utf-8")))
    labels = [{"03_v120": "V 120°", "02_v150": "V 150°"}[r["layout"]]
              for r in rows]
    level = [float(r["level_re_coherent_bound_db"]) for r in rows]
    spread = [float(r["curvature_spread_mm"]) for r in rows]
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    bars = ax.bar(labels, level, color=(R.BLUE, R.ORANGE), width=0.5)
    for bar, mm, sp in zip(bars, level, spread):
        ax.text(bar.get_x() + bar.get_width() / 2, mm / 2,
                f"{mm:.2f} dB\npath spread {sp:.1f} mm",
                ha="center", va="center", fontsize=9.5, color="white",
                fontweight="600")
    ax.axhline(0.0, color=R.INK, lw=1.0)
    ax.set_ylim(min(level) - 3.2, 1.0)
    ax.set_ylabel("level re coherent bound (dB)")
    ax.set_title("Microphone at 2 m on the commanded ray", fontsize=12,
                 fontweight="bold", loc="left")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def winners(path: Path) -> None:
    rows = list(csv.DictReader((DATA / "winners.csv").open(encoding="utf-8")))
    colour = {"2-board": R.BLUE, "3-board": R.ORANGE}
    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    for fam, marker in (("2-board", "o"), ("3-board", "s")):
        sel = [r for r in rows if r["family"] == fam]
        ax.scatter([float(r["SL_cmd"]) for r in sel],
                   [float(r["SRANGE_0dB"]) for r in sel],
                   s=52, marker=marker, color=colour[fam], label=fam,
                   zorder=3)
    vsel = [r for r in rows if r["family"].startswith("V")]
    ax.scatter([float(r["SL_cmd"]) for r in vsel],
               [float(r["SRANGE_0dB"]) for r in vsel],
               s=52, marker="^", color=R.VIOLET, label="V pair", zorder=3)
    best = min((r for r in rows if r["family"] == "3-board"),
               key=lambda r: float(r["SL_cmd"]))
    best2 = min((r for r in rows if r["family"] == "2-board"),
                key=lambda r: float(r["shortlist"]))
    for row, label, pos in (
            (best, "recommended: " + best["key"], (0.10, 29.0)),
            (best2, "best 2-board: " + best2["key"], (0.62, 25.3))):
        x, y = float(row["SL_cmd"]), float(row["SRANGE_0dB"])
        ax.scatter([x], [y], s=240, facecolors="none", edgecolors=R.RED,
                   lw=1.8, zorder=4)
        ax.annotate(label, (x, y), xytext=pos, textcoords="data",
                    fontsize=8.2, color=R.RED, ha="left",
                    arrowprops=dict(arrowstyle="->", color=R.RED, lw=0.9))
    ax.set_xlabel("worst sidelobe, SL_cmd (dB)")
    ax.set_ylabel("contiguous 0 dB range, SRANGE₀ (deg)")
    ax.set_title("Winners: same metrics for all three families", fontsize=12,
                 fontweight="bold", loc="left")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8.5)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    element_pattern(OUT / "element_pattern.png")
    mic2m(OUT / "mic2m.png")
    winners(OUT / "winners.png")
    print("wrote", *(p.name for p in sorted(OUT.glob("*.png"))))


if __name__ == "__main__":
    main()
