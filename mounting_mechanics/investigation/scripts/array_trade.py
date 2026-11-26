#!/usr/bin/env python3
"""Array-factor trade study for the measured SonicSurface geometry.

Uses the dimensions extracted from the Gerber/pick-place data:
  pitch 10.5 mm, board A first element x=13.706 mm y=5.496 mm,
  board outline 185.0921 x 168.402 mm.

The code is a design tool, not a measurement. Isotropic elements, 40 kHz,
c=343 m/s. Reports peak sidelobe and the grating-direction level for candidate
seams and offsets. Writes acoustics_trade.csv and a small JSON summary.
"""
import json
import os
import sys
import numpy as np

F = 40000.0
C = 343.0
LAM = C / F * 1000.0  # mm
K = 2 * np.pi / LAM
PITCH = 10.5
A_X0 = 5.4060
A_Y0 = 13.7060
BOARD_W = 185.092086
BOARD_H = 168.402

# Angular grid: theta 0..90 in 0.25 deg, phi 0..360 in 1 deg.
theta = np.deg2rad(np.arange(0, 90.0001, 0.25))
phi = np.deg2rad(np.arange(0, 360.0001, 1.0))
TH, PH = np.meshgrid(theta, phi, indexing="ij")
U = np.sin(TH) * np.cos(PH)
V = np.sin(TH) * np.sin(PH)


def positions(seam, off_y):
    """512 element positions; seam is A_last_x to B_first_x."""
    ax = A_X0 + PITCH * np.arange(16)
    ay = A_Y0 + PITCH * np.arange(16)
    bx = (A_X0 + PITCH * 15 + seam) + PITCH * np.arange(16)
    by = (A_Y0 + off_y) + PITCH * np.arange(16)
    X = np.concatenate([np.repeat(ax, 16), np.repeat(bx, 16)])
    Y = np.concatenate([np.tile(ay, 16), np.tile(by, 16)])
    return X, Y


def pattern(seam, off_y, dx_err=0.0, dy_err=0.0):
    X, Y = positions(seam, off_y)
    X = X.copy()
    Y = Y.copy()
    X[256:] += dx_err
    Y[256:] += dy_err
    phase = np.outer(U.ravel(), X) + np.outer(V.ravel(), Y)
    af = np.exp(1j * K * phase).sum(axis=1)
    return af.reshape(U.shape)


def summarize(seam, off_y, dx_err=0.0, dy_err=0.0):
    af = pattern(seam, off_y, dx_err, dy_err)
    mag = np.abs(af)
    main = mag[0, 0]
    db = 20 * np.log10(np.maximum(mag / main, 1e-12))
    th_flat = TH.ravel()
    db_flat = db.ravel()

    # Sidelobe: everything beyond 5 deg from broadside. Cylindrical symmetry
    # is not assumed because the layout is rectangular.
    mask = th_flat > np.deg2rad(5.0)
    peak = float(db_flat[mask].max())
    # First sidelobe region 5-15 deg.
    mask1 = (th_flat > np.deg2rad(5.0)) & (th_flat < np.deg2rad(15.0))
    first = float(db_flat[mask1].max())
    # Grating direction in the x=const plane (phi=0/180) and y plane.
    thg = np.arcsin(LAM / PITCH)
    # Values from the 2D grid at the nearest theta sample.
    i = int(round(thg / np.deg2rad(0.25)))
    grating_levels = {
        "theta_deg": float(np.rad2deg(thg)),
        "phi0_db": float(db[i, 0]),
        "phi90_db": float(db[i, 90]),
        "phi180_db": float(db[i, 180]),
        "phi270_db": float(db[i, 270]),
    }
    # Null depth: relative level of the two-board sum at the exact grating
    # direction when the offset is nominal.
    return {
        "seam_mm": seam,
        "off_y_mm": off_y,
        "dx_err_mm": dx_err,
        "dy_err_mm": dy_err,
        "peak_sidelobe_db": peak,
        "first_sidelobe_5_15_db": first,
        "grating": grating_levels,
    }


def main():
    out_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cases = []
    for seam in [10.902, 15.75, 26.25, 36.75]:
        for off_y in [5.0, 5.25]:
            cases.append(summarize(seam, off_y))
    # Error cases at the recommended geometry.
    for dx, dy in [(0, 0), (0.15, 0), (-0.15, 0), (0, 0.15), (0, -0.15),
                   (0.15, 0.15), (-0.15, -0.15), (0.15, -0.15), (-0.15, 0.15)]:
        cases.append(summarize(15.75, 5.25, dx, dy))

    with open(os.path.join(out_dir, "acoustics_trade.csv"), "w", encoding="utf-8") as f:
        f.write("seam_mm,off_y_mm,dx_err_mm,dy_err_mm,peak_sidelobe_db,"
                "first_sidelobe_5_15_db,grating_theta_deg,grating_phi0_db,"
                "grating_phi90_db,grating_phi180_db,grating_phi270_db\n")
        for c in cases:
            g = c["grating"]
            f.write("%.4f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f\n" %
                    (c["seam_mm"], c["off_y_mm"], c["dx_err_mm"], c["dy_err_mm"],
                     c["peak_sidelobe_db"], c["first_sidelobe_5_15_db"],
                     g["theta_deg"], g["phi0_db"], g["phi90_db"],
                     g["phi180_db"], g["phi270_db"]))

    print("%8s %6s %8s %10s %10s %8s" % ("seam", "off_y", "peakSL", "firstSL", "grat0", "grat90"))
    for c in cases:
        if c["dx_err_mm"] == 0 and c["dy_err_mm"] == 0:
            print("%8.3f %6.2f %8.2f %10.2f %10.2f %8.2f" %
                  (c["seam_mm"], c["off_y_mm"], c["peak_sidelobe_db"],
                   c["first_sidelobe_5_15_db"], c["grating"]["phi0_db"],
                   c["grating"]["phi90_db"]))
    print("\nTolerance cases at seam=15.75, off_y=5.25:")
    for c in cases:
        if c["dx_err_mm"] != 0 or c["dy_err_mm"] != 0:
            print("dx=%+.2f dy=%+.2f peakSL %.2f grating0 %.2f" %
                  (c["dx_err_mm"], c["dy_err_mm"], c["peak_sidelobe_db"],
                   c["grating"]["phi0_db"]))
    print("\nGrating angle (10.5 mm pitch): %.3f deg; lambda %.3f mm"
          % (np.rad2deg(np.arcsin(LAM / PITCH)), LAM))
    print("Wrote", os.path.join(out_dir, "acoustics_trade.csv"))


if __name__ == "__main__":
    main()


