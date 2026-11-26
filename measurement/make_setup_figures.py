#!/usr/bin/env python3
"""Generate the measurement setup figures for the 26.11.25 report section.

Four PNGs under measurement/figures/:
  1. setup_lab_plan.png      top view, broadside vs the 54.75 deg null
  2. setup_array.png         front view of the 512 elements + side elevation
  3. setup_timing.png        gate waveform and the microwave window
  4. setup_chain.png         receive chain and scope channels

Pure matplotlib; no hardware.
"""

from __future__ import annotations

import math

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Arc, Circle, FancyArrowPatch, Rectangle

A_COLOR = "#4C72B0"
B_COLOR = "#8172B3"
MIC = "#DD8452"
GATE = "#55A868"
RED = "#C44E52"
GREY = "#5F5F5F"
LIGHT = "#BDBDBD"

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.linewidth": 0.8,
        "savefig.bbox": "tight",
        "savefig.facecolor": "white",
    }
)

SEAM = 0.01575  # m
PITCH = 0.0105  # m
SPAN = 15 * PITCH  # 0.1575 m element span per board
APERTURE_X = 2 * SPAN + SEAM  # 0.33075 m
APERTURE_Y = SPAN + 0.00525  # 0.16275 m


def arrow(ax, p0, p1, color, lw=1.5, ls="-", style="-|>", ms=10):
    ax.add_patch(
        FancyArrowPatch(
            p0,
            p1,
            arrowstyle=style,
            mutation_scale=ms,
            color=color,
            lw=lw,
            linestyle=ls,
            shrinkA=0,
            shrinkB=0,
        )
    )


def rotation_axis(ax, xy, r, color="k"):
    x, y = xy
    ax.add_patch(Circle(xy, r, fill=False, ec=color, lw=1.1))
    ax.plot([x - r * 0.55, x + r * 0.55], [y, y], color=color, lw=1.1)
    ax.plot([x, x], [y - r * 0.55, y + r * 0.55], color=color, lw=1.1)


def fig_lab_plan(path):
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 4.8))

    for ax, theta, title in zip(
        axes,
        (0.0, 54.75),
        ("(a) Broadside: array normal points at the mic",
         "(b) Null: array rotated 54.75°"),
    ):
        ax.set_xlim(-0.75, 3.75)
        ax.set_ylim(-1.35, 1.35)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(title, fontsize=11, loc="left", fontweight="bold")

        for gx in np.arange(-0.5, 3.8, 0.5):
            ax.axvline(gx, color="#EFEFEF", lw=0.6, zorder=0)
        for gy in np.arange(-1.25, 1.3, 0.5):
            ax.axhline(gy, color="#EFEFEF", lw=0.6, zorder=0)

        n = math.radians(theta)
        normal = np.array([math.cos(n), math.sin(n)])
        line = np.array([-math.sin(n), math.cos(n)])  # array width in plan

        # two board segments with the 15.75 mm seam gap at the centre
        half = APERTURE_X / 2
        g = SEAM / 2
        ax.plot(
            [line[0] * g, line[0] * half],
            [line[1] * g, line[1] * half],
            color=A_COLOR, lw=7, solid_capstyle="butt", zorder=3,
        )
        ax.plot(
            [-line[0] * g, -line[0] * half],
            [-line[1] * g, -line[1] * half],
            color=B_COLOR, lw=7, solid_capstyle="butt", zorder=3,
        )
        ax.text(
            line[0] * (half + 0.06), line[1] * (half + 0.06) + 0.05,
            "A", color=A_COLOR, fontsize=10, fontweight="bold", ha="center",
        )
        ax.text(
            -line[0] * (half + 0.06), -line[1] * (half + 0.06) + 0.05,
            "B", color=B_COLOR, fontsize=10, fontweight="bold", ha="center",
        )

        rotation_axis(ax, (0.0, 0.0), 0.035)

        arrow(ax, (0, 0), normal * 0.88, GREY, lw=1.1, ls="--")
        if theta > 0:
            ax.text(
                normal[0] * 1.02, normal[1] * 1.02, "normal",
                color=GREY, fontsize=9, ha="center", va="center",
            )
        else:
            ax.text(0.52, 0.12, "normal = mic line", color=GREY,
                    fontsize=9, ha="center")

        mic = np.array([3.0, 0.0])
        ax.plot(*mic, "o", color=MIC, ms=10, zorder=5)
        ax.text(mic[0], mic[1] - 0.20, "mic  R = 3.0 m", color=MIC,
                fontsize=9, ha="center")
        ax.plot([0, mic[0]], [0, mic[1]], color=GREY, lw=0.9, ls=":")

        if theta > 0:
            ax.add_patch(
                Arc((0, 0), 1.15, 1.15, theta1=0, theta2=theta,
                    color=RED, lw=1.5)
            )
            mid = math.radians(theta / 2)
            ax.text(
                0.64 * math.cos(mid), 0.64 * math.sin(mid),
                "54.75°", color=RED, fontsize=11, fontweight="bold",
                ha="center", va="center",
            )
            ax.add_patch(
                Arc((0, 0), 0.55, 0.55, theta1=0, theta2=theta,
                    color=RED, lw=1.2, ls="--")
            )
            ax.text(0.12, -0.42, "rotate 54.75°\nabout the vertical",
                    color=RED, fontsize=9)
            ax.text(1.55, 0.55, "main beam\npoints 54.75° away",
                    color=RED, fontsize=9, ha="center")
            ax.text(1.55, -0.12, "mic is on the az 0 lobe", color=RED,
                    fontsize=8, ha="center")
        else:
            ax.text(1.50, 0.14, "main beam → mic", color=GREY,
                    fontsize=9, ha="center")

        ax.text(-0.72, 1.22, "top view · array and mic at 1.6 m height",
                fontsize=8, color=GREY)

    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def fig_array(path):
    fig, (ax, side) = plt.subplots(
        1, 2, figsize=(13.0, 5.0), gridspec_kw={"width_ratios": [1.45, 1.0]}
    )

    # --- front view ---------------------------------------------------
    ax.set_xlim(-14, 352)
    ax.set_ylim(-18, 208)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("(a) Front view: 512 elements, seam vertical",
                 fontsize=11, loc="left", fontweight="bold")

    xs = np.arange(16) * PITCH * 1000
    ys = np.arange(16) * PITCH * 1000
    xa, ya = np.meshgrid(xs, ys)
    xb, yb = np.meshgrid(xs + 173.25, ys + 5.25)
    ax.scatter(xa.ravel(), ya.ravel(), s=7, color=A_COLOR, zorder=3)
    ax.scatter(xb.ravel(), yb.ravel(), s=7, color=B_COLOR, zorder=3)
    ax.add_patch(Rectangle((0, 0), 157.5, 157.5, fill=False,
                           ec=A_COLOR, lw=1.2))
    ax.add_patch(Rectangle((173.25, 5.25), 157.5, 157.5, fill=False,
                           ec=B_COLOR, lw=1.2))

    ax.annotate("", xy=(157.5, 172), xytext=(173.25, 172),
                arrowprops=dict(arrowstyle="<->", color="k", lw=1.0))
    ax.text(165.4, 176, "15.75 mm seam", ha="center", fontsize=9)
    ax.annotate("", xy=(340, 0), xytext=(340, 5.25),
                arrowprops=dict(arrowstyle="<->", color="k", lw=1.0))
    ax.text(344, 2.6, "5.25 mm", fontsize=8, rotation=90, va="center")

    cx, cy = 165.375, 81.375
    ax.plot(cx, cy, "k+", ms=12, mew=1.6)
    ax.text(cx + 6, cy + 5, "rotation axis", fontsize=8)
    arrow(ax, (cx, cy), (cx + 95, cy), RED, lw=1.1, ms=9)
    ax.text(cx + 100, cy, "az 0 / 180", color=RED, fontsize=8, va="center")
    arrow(ax, (cx, cy), (cx, cy + 72), RED, lw=1.1, ms=9)
    ax.text(cx, cy + 78, "az 90 / 270", color=RED, fontsize=8, ha="center")

    ax.text(165.4, -10,
            "element span 330.75 × 162.75 mm · pitch 10.5 mm · "
            "az 0/180 is horizontal when the seam is vertical",
            ha="center", fontsize=9)
    ax.text(165.4, 198, "Roll 90° about the normal for the az 90/270 cuts",
            ha="center", fontsize=9, fontweight="bold")

    # --- side elevation ----------------------------------------------
    side.set_xlim(-0.35, 3.65)
    side.set_ylim(0, 2.35)
    side.set_aspect("equal")
    side.axis("off")
    side.set_title("(b) Side view: height and first floor bounce",
                   fontsize=11, loc="left", fontweight="bold")

    side.axhline(0, color="#777777", lw=2.4)
    side.text(3.1, 0.06, "floor", fontsize=8, color="#777777")
    side.plot([0, 0], [1.6 - APERTURE_Y / 2, 1.6 + APERTURE_Y / 2],
              color=A_COLOR, lw=9, solid_capstyle="butt")
    side.text(-0.10, 1.6 + APERTURE_Y / 2 + 0.06, "array", color=A_COLOR,
              fontsize=9, ha="center")
    side.plot(3.0, 1.6, "o", color=MIC, ms=10)
    side.text(3.0, 1.38, "mic", color=MIC, fontsize=9, ha="center")

    side.plot([0, 3.0], [1.6, 1.6], color=GREY, lw=1.2, ls="--")
    side.text(1.5, 1.68, "direct 3.0 m · 8.75 ms", color=GREY,
              fontsize=9, ha="center")

    xs_b = np.array([0.0, 1.5, 3.0])
    ys_b = np.array([1.6, 0.0, 1.6])
    side.plot(xs_b, ys_b, color=RED, lw=1.2, ls=":")
    side.text(1.5, 0.62, "floor bounce 4.74 m\n+5.07 ms", color=RED,
              fontsize=8, ha="center")

    side.annotate("", xy=(-0.16, 0), xytext=(-0.16, 1.6),
                  arrowprops=dict(arrowstyle="<->", color="k", lw=1.0))
    side.text(-0.22, 0.8, "1.6 m", fontsize=9, rotation=90, va="center")

    side.text(1.8, 2.18, "settled window 1.6–4.0 ms; bounce at +5.07 ms",
              fontsize=8, color=GREY, ha="center")

    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def fig_timing(path):
    fig, (gate, mic) = plt.subplots(
        2, 1, figsize=(11.4, 5.8),
        gridspec_kw={"height_ratios": [1.0, 1.35]},
    )

    # --- gate ---------------------------------------------------------
    gate.set_xlim(-6, 108)
    gate.set_ylim(-0.25, 1.45)
    gate.axis("off")
    gate.set_title("(a) Gate: 4 ms on, 96 ms off (10 Hz)",
                   fontsize=11, loc="left", fontweight="bold")
    gate.plot([0, 0, 4, 4, 100], [0, 1, 1, 0, 0], color=GATE, lw=2.4)
    gate.plot([100, 100, 104], [0, 1, 1], color=GATE, lw=2.4, alpha=0.4)
    gate.annotate("", xy=(0, 1.16), xytext=(4, 1.16),
                  arrowprops=dict(arrowstyle="<->", color=GATE, lw=1.1))
    gate.text(2, 1.23, "4 ms ON", color=GATE, fontsize=9, ha="center")
    gate.annotate("", xy=(4, 0.55), xytext=(100, 0.55),
                  arrowprops=dict(arrowstyle="<->", color=GREY, lw=1.0))
    gate.text(52, 0.63, "96 ms OFF — room decays ~90 dB (RT60 ≈ 70 ms at 40 kHz)",
              color=GREY, fontsize=9, ha="center")
    gate.text(52, -0.18, "period 100 ms · next burst starts at 100 ms",
              color=GREY, fontsize=8, ha="center")

    # --- at the mic ---------------------------------------------------
    mic.set_xlim(-0.15, 5.6)
    mic.set_ylim(-0.35, 1.55)
    mic.axis("off")
    mic.set_title("(b) At the mic: time after the first arrival",
                  fontsize=11, loc="left", fontweight="bold")

    mic.axvspan(0, 0.787, color="#9ECAE1", alpha=0.55, lw=0)
    mic.axvspan(0.787, 1.5, color="#FDD0A2", alpha=0.55, lw=0)
    mic.axvspan(1.6, 4.0, color="#A1D99B", alpha=0.65, lw=0)
    mic.text(0.39, 1.38, "aperture\nfill 0.79 ms", fontsize=8,
             ha="center", va="top")
    mic.text(1.14, 1.38, "settling\n~0.7 ms", fontsize=8,
             ha="center", va="top")
    mic.text(2.8, 1.38, "analysis 1.6–4.0 ms\n2.4 ms · 96 cycles", fontsize=9,
             ha="center", va="top", fontweight="bold")
    mic.axvline(4.0, color=GREY, lw=1.1, ls="--")
    mic.text(4.06, 0.55, "burst ends", color=GREY, fontsize=8)
    mic.axvline(5.07, color=RED, lw=1.3, ls="--")
    mic.text(5.12, 0.30, "first floor bounce", color=RED, fontsize=8)

    t = np.linspace(0, 5.6, 1600)
    env = np.zeros_like(t)
    rise = t <= 1.5
    env[rise] = np.clip(t[rise] / 1.5, 0, 1)
    env[(t > 1.5) & (t <= 4.0)] = 1.0
    mic.step(t, env, where="post", color=GATE, lw=1.8)
    mic.plot([5.07, 5.07], [0, 0.22], color=RED, lw=1.6)

    mic.annotate("", xy=(0, 0.02), xytext=(0.787, 0.02),
                 arrowprops=dict(arrowstyle="<->", color="#3182BD", lw=1.0))
    mic.annotate("", xy=(0.787, 0.02), xytext=(1.5, 0.02),
                 arrowprops=dict(arrowstyle="<->", color="#E6550D", lw=1.0))
    mic.annotate("", xy=(1.6, 0.02), xytext=(4.0, 0.02),
                 arrowprops=dict(arrowstyle="<->", color="#238B45", lw=1.0))
    mic.set_ylim(-0.48, 1.60)
    mic.axhline(0, color="#B0B0B0", lw=0.8)
    for x in range(0, 7):
        mic.plot([x, x], [-0.03, 0.03], color="k", lw=0.8)
        mic.text(x, -0.14, str(x), ha="center", fontsize=8)
    mic.text(3.0, -0.38, "time after first arrival (ms)", ha="center",
             fontsize=9)

    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def fig_chain(path):
    fig, ax = plt.subplots(figsize=(12.4, 4.6))
    ax.set_xlim(0, 12.4)
    ax.set_ylim(0, 4.6)
    ax.axis("off")
    ax.set_title("Receive chain and scope channels", fontsize=12,
                 loc="left", fontweight="bold")

    def box(x, y, w, h, label, edge, face="white", fs=9):
        ax.add_patch(Rectangle((x, y), w, h, fc=face, ec=edge, lw=1.4))
        ax.text(x + w / 2, y + h / 2, label, ha="center", va="center",
                fontsize=fs)

    box(0.25, 1.85, 2.15, 1.25, "MA40S4R\n40 kHz piezo\n(flush in shield box)",
        MIC, fs=9)
    box(3.05, 1.55, 3.30, 1.85,
        "Buffer  0 dB / +20 dB\nOPA2134 or TL072\n1 MΩ input\n"
        "two 9 V batteries\nshielded metal box", A_COLOR, fs=9)
    box(7.05, 1.85, 2.40, 1.25, "Scope Ch1\n1 MΩ · 1× probe\n1–10 MS/s",
        GREY, fs=9)

    arrow(ax, (2.40, 2.47), (3.05, 2.47), GREY)
    arrow(ax, (6.35, 2.47), (7.05, 2.47), GREY)
    ax.text(2.72, 2.62, "≤1.5 m\nRG-58", fontsize=7, ha="center")

    box(7.05, 0.55, 2.40, 0.75, "Scope Ch2\nMISC_C gate 3.3 V", GATE, fs=8)
    box(9.85, 0.55, 2.30, 0.75, "Ch3 MISC_D\nCh4 MISC_A\n(sync check)", GREY, fs=8)
    arrow(ax, (6.35, 0.93), (7.05, 0.93), GATE)

    ax.text(0.25, 0.35,
            "main beam 0.2–3.6 Vrms at 0 dB; use +20 dB for the null. "
            "Never 40–60 dB.",
            fontsize=8, color=GREY)
    ax.text(0.25, 0.12,
            "EMI block test: a book 5 cm in front of the mic must drop the "
            "40 kHz level ≥45 dB.",
            fontsize=8, color=GREY)

    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def main():
    import os

    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "figures")
    os.makedirs(out, exist_ok=True)
    fig_lab_plan(os.path.join(out, "setup_lab_plan.png"))
    fig_array(os.path.join(out, "setup_array.png"))
    fig_timing(os.path.join(out, "setup_timing.png"))
    fig_chain(os.path.join(out, "setup_chain.png"))
    print("wrote", out)


if __name__ == "__main__":
    main()
