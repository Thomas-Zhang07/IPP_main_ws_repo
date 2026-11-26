#!/usr/bin/env python3
"""Plot broadside cuts for the recommended 36.75 mm seam / 5.25 mm offset."""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

F, C = 40000.0, 343.0
lam = C / F * 1000.0
k = 2 * np.pi / lam
pitch = 10.5
ax0, ay0 = 5.4060, 13.7060

theta = np.deg2rad(np.linspace(-90, 90, 3601))


def af(seam, offy, phi_deg):
    ax = ax0 + pitch * np.arange(16)
    ay = ay0 + pitch * np.arange(16)
    bx = ax0 + 15 * pitch + seam + pitch * np.arange(16)
    by = ay0 + offy + pitch * np.arange(16)
    X = np.concatenate([np.repeat(ax, 16), np.repeat(bx, 16)])
    Y = np.concatenate([np.tile(ay, 16), np.tile(by, 16)])
    phi = np.deg2rad(phi_deg)
    ph = k * (np.outer(np.sin(theta), X * np.cos(phi) + Y * np.sin(phi)))
    return np.abs(np.exp(1j * ph).sum(axis=1))


fig, ax = plt.subplots(figsize=(8, 5))
for seam, offy, label, color in [
    (15.75, 5.25, "15.75 mm seam, 5.25 mm y (recommended)", "tab:blue"),
    (26.25, 5.25, "26.25 mm seam, 5.25 mm y (larger gap)", "tab:red"),
    (10.902, 5.25, "10.90 mm butted seam, 5.25 mm y", "0.5"),
]:
    for phi, ls in [(0, "-"), (90, "--")]:
        p = af(seam, offy, phi)
        ax.plot(np.rad2deg(theta), 20 * np.log10(p / p[np.argmin(abs(theta))] + 1e-12),
                ls, color=color, lw=1.2,
                label=label + (", phi=0" if phi == 0 else ", phi=90"))
ax.set_xlim(-90, 90)
ax.set_ylim(-60, 2)
ax.axvline(np.rad2deg(np.arcsin(lam / pitch)), color="k", lw=0.5, ls=":")
ax.axvline(-np.rad2deg(np.arcsin(lam / pitch)), color="k", lw=0.5, ls=":")
ax.text(np.rad2deg(np.arcsin(lam / pitch)) + 1, -55,
        "grating direction\n54.75 deg", fontsize=7, va="bottom")
ax.set_xlabel("theta (deg)")
ax.set_ylabel("normalised array factor (dB)")
ax.set_title("512-element array factor, f=40 kHz, isotropic elements")
ax.grid(True, lw=0.3)
ax.legend(fontsize=6, ncol=2, loc="lower center")
fig.tight_layout()
out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "pattern_recommended.png")
fig.savefig(out, dpi=160)
print("wrote", out)



