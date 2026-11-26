"""Digitize the TR4010HC measured polar chart from ``transducers.jpg``.

The photographed datasheet page is the only directivity data available for
the part.  The chart geometry is calibrated with constants measured once on
that image (centre, 0 dB radius, ring spacing); the trace is tracked for
both halves of the asymmetric cut, bridged across the dark radial spokes and
smoothed.  ``directivity.csv`` is the committed result.

Run::

    python sim/transducer/digitize.py
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

# --- calibration for transducers.jpg (2160 x 2250 px) ---------------------
IMAGE_SIZE = (2250, 2160, 3)          # rows, cols, channels
CENTER_CX = 1506                      # chart centre, px
CENTER_CY = 1820
R0_PX = 297.0                         # radius of the 0 dB ring, px
PX_PER_6DB = 45.0                     # radial spacing of the rings, px / 6 dB
TRACE_STEP_DEG = 0.25                 # angular sampling of the extraction
R_MIN_PX, R_MAX_PX, R_STEP_PX = 15.0, 330.0, 0.5
SPOKE_BRIDGE_DEG = 2.5                # blank the dark 30 deg spoke lines
SMOOTH_POINTS = 9                     # circular box filter (~2.25 deg)
OUT_STEP_DEG = 0.5                    # committed grid
OVERLAY_CROP = (1150, 1500, 1980, 2180)  # left, top, right, bottom

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_IMAGE = ROOT / "transducers.jpg"
DEFAULT_OUT = Path(__file__).resolve().parent


def check_image(img: np.ndarray) -> None:
    """Reject anything but the calibrated datasheet photograph."""
    if img.shape != IMAGE_SIZE:
        raise ValueError(
            f"expected a {IMAGE_SIZE[1]}x{IMAGE_SIZE[0]} RGB image, "
            f"got shape {img.shape}"
        )


def _pink_mask(img: np.ndarray) -> np.ndarray:
    """Light-pink curve pixels; the darker red dB labels fail ``g > 135``."""
    r, g, b = img[:, :, 0], img[:, :, 1], img[:, :, 2]
    return (r - g > 14) & (r - b > 8) & (r > 170) & (g > 135)


def _trace_profile(mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Largest pink radius per angle, in px (NaN where the trace is hidden)."""
    angles = np.arange(0.0, 360.0, TRACE_STEP_DEG)
    radii = np.arange(R_MIN_PX, R_MAX_PX, R_STEP_PX)
    prof = np.full(angles.size, np.nan)
    for i, a in enumerate(angles):
        t = math.radians(a)
        y = np.rint(CENTER_CY - radii * math.cos(t)).astype(int)
        x = np.rint(CENTER_CX + radii * math.sin(t)).astype(int)
        inside = (y >= 0) & (y < mask.shape[0]) & (x >= 0) & (x < mask.shape[1])
        hit = np.zeros(radii.size, dtype=bool)
        hit[inside] = mask[y[inside], x[inside]]
        if hit.any():
            prof[i] = radii[hit].max()
    return angles, prof


def _bridge_spokes(angles: np.ndarray, prof: np.ndarray) -> np.ndarray:
    """Interpolate across the 30 deg spokes, which overwrite the curve."""
    prof = prof.copy()
    for spoke in range(0, 360, 30):
        dd = np.minimum(np.abs(angles - spoke), 360.0 - np.abs(angles - spoke))
        prof[dd < SPOKE_BRIDGE_DEG] = np.nan
    ok = np.isfinite(prof)
    if not ok.any():
        raise ValueError("no trace found in the chart")
    return np.interp(angles, angles[ok], prof[ok])


def _to_db(radii_px: np.ndarray) -> np.ndarray:
    return -6.0 * (R0_PX - radii_px) / PX_PER_6DB


def _smooth_circular(db: np.ndarray, points: int = SMOOTH_POINTS) -> np.ndarray:
    half = points // 2
    padded = np.concatenate([db[-half:], db, db[:half]])
    return np.convolve(padded, np.ones(points) / points, mode="valid")


def _collapse(angles: np.ndarray, db: np.ndarray):
    """Fold the 0..360 cut onto 0..180: right, left and power-averaged."""
    out_angles = np.arange(0.0, 180.0 + 1e-9, OUT_STEP_DEG)
    front = angles <= 180.0
    right = np.interp(out_angles, angles[front], db[front])
    # left(theta) = profile(360 - theta); index 0 repeats the on-axis sample
    mirrored = np.roll(db[::-1], 1)
    left = np.interp(out_angles, angles, mirrored)
    mean_power = 10.0 * np.log10(
        (10.0 ** (right / 10.0) + 10.0 ** (left / 10.0)) / 2.0
    )
    return out_angles, right, left, mean_power


def _derive(angles: np.ndarray, mean_power: np.ndarray) -> tuple[float, float]:
    """Standard 4 pi directivity: Q = 2 / int_0^pi P sin(theta) dtheta."""
    th = np.radians(angles)
    q = 2.0 / np.trapezoid(10.0 ** (mean_power / 10.0) * np.sin(th), th)
    return float(q), float(10.0 * math.log10(q))


def _crossing(angles: np.ndarray, curve: np.ndarray, level: float = -6.0) -> float:
    below = np.flatnonzero(curve <= level)
    if below.size == 0:
        raise ValueError(f"no {level:g} dB crossing in the cut")
    return float(angles[below[0]])


def extract(image_path: Path | str = DEFAULT_IMAGE) -> dict:
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(path)
    img = np.asarray(Image.open(path).convert("RGB"), dtype=int)
    check_image(img)
    angles, prof = _trace_profile(_pink_mask(img))
    db = _smooth_circular(_to_db(_bridge_spokes(angles, prof)))
    # The chart's 0 dB ring is the reference; normalise the digitized peak to
    # 0 dB so the levels are a true directivity and DI is well defined.
    db = db - db[0]
    out_angles, right, left, mean_power = _collapse(angles, db)
    q, di = _derive(out_angles, mean_power)
    return {
        "angles_deg": out_angles,
        "db_right": right,
        "db_left": left,
        "db_mean_power": mean_power,
        "q": q,
        "di_db": di,
        "half_right_deg": _crossing(out_angles, right),
        "half_left_deg": _crossing(out_angles, left),
    }


def _write_overlay(result: dict, path: Path,
                   image_path: Path = DEFAULT_IMAGE) -> None:
    if not Path(image_path).exists():
        return
    img = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(img)
    for a, db_r, db_l in zip(result["angles_deg"], result["db_right"],
                             result["db_left"]):
        for theta, level in ((a, db_r), (360.0 - a, db_l)):
            radius = R0_PX + level * (PX_PER_6DB / 6.0)
            t = math.radians(theta)
            x = CENTER_CX + radius * math.sin(t)
            y = CENTER_CY - radius * math.cos(t)
            draw.ellipse([x - 1, y - 1, x + 1, y + 1], fill=(0, 0, 255))
    left, top, right, bottom = OVERLAY_CROP
    img.crop(OVERLAY_CROP).resize(((right - left) * 2, (bottom - top) * 2),
                                  Image.LANCZOS).save(path)


def write_outputs(result: dict, out_dir: Path | str = DEFAULT_OUT):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "directivity.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        fh.write("angle_deg,db_right,db_left,db_mean_power\n")
        for a, r, l, m in zip(result["angles_deg"], result["db_right"],
                              result["db_left"], result["db_mean_power"]):
            fh.write(f"{a:.2f},{r:.3f},{l:.3f},{m:.3f}\n")
    overlay = out_dir / "overlay.png"
    _write_overlay(result, overlay)
    return csv_path, overlay


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Digitize the transducer polar chart.")
    ap.add_argument("--image", default=str(DEFAULT_IMAGE))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args(argv)
    result = extract(args.image)
    csv_path, overlay = write_outputs(result, args.out)
    print(f"DI {result['di_db']:.2f} dB  (Q {result['q']:.2f})")
    print(f"half-angles: right {result['half_right_deg']:.1f} deg, "
          f"left {result['half_left_deg']:.1f} deg")
    print(f"wrote {csv_path}")
    print(f"wrote {overlay}")


if __name__ == "__main__":
    main()
