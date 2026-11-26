"""Fast model and included-angle search for V-shaped two-board pairs.

The coplanar model cannot represent tilted boards.  Each board is still a
planar 16 x 16 grid, so its field factorises in its own local axes:

    p_b(d) = E_b(d) · Σ_{c,r} exp(i k (d−s)·(origin_b + c p u_b + r p v_b))

with ``s = (u0, v0, w0)`` the 3-D command (depth-compensated).  The complex
Dirichlet phase is kept because it differs between boards and shapes their
interference.  The search also allows a y offset of one board along the hinge,
which nulls the y-axis pitch grating at a half-pitch offset.

Grating and broadside directions are sampled exactly by the metrics, so the
coarse search grid does not alias narrow lobes.

Run the sweep::

    python -m optimum_search.vshape
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np

import constants as C
import geometry
import render_png as R
import transducer

from . import metrics, model, report, search

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "search2"
FIGS = ROOT / "figures" / "search2"


def v_pair_offset(included_deg: float, offset_y_m: float = 0.0):
    """V pair with board B shifted along the hinge (y)."""
    layout = geometry.v_pair(float(included_deg),
                             f"v{included_deg:03.0f}_{offset_y_m * 1e3:05.2f}",
                             f"V {included_deg:.0f} / y {offset_y_m * 1e3:.2f}")
    if offset_y_m:
        board = layout.boards[1]
        board.positions[:, 1] += offset_y_m
        board.outline[:, 1] += offset_y_m
    return layout


def _frames(layout):
    frames = []
    for board in layout.boards:
        pos = board.positions
        origin = pos[0].astype(float)
        u = (pos[1] - pos[0]) / C.PITCH_M
        v = (pos[model.N_SIDE] - pos[0]) / C.PITCH_M
        normal = board.normals[0] / np.linalg.norm(board.normals[0])
        frames.append((origin, u, v, normal))
    return frames


def _element(cos_beta, variant):
    if variant == "mean":
        return transducer.amplitude(cos_beta)
    theta = np.degrees(np.arccos(np.clip(cos_beta, -1.0, 1.0)))
    if variant in ("left", "right"):
        return 10.0 ** (transducer.level_db(theta, variant) / 20.0)
    if variant == "wide":
        return 10.0 ** (transducer.level_db(
            np.minimum(theta * 81.0 / 92.0, 180.0)) / 20.0)
    raise ValueError(f"unsupported variant for V boards: {variant}")


def field_v(layout, dirs, u0, v0=0.0, variant="mean"):
    """Exact separable field for a layout of planar (possibly tilted) boards."""
    if u0 * u0 + v0 * v0 > 1.0 + 1e-12:
        raise ValueError("commanded direction outside the hemisphere")
    dirs = np.atleast_2d(np.asarray(dirs, dtype=float))
    w0 = float(np.sqrt(max(0.0, 1.0 - u0 * u0 - v0 * v0)))
    q = dirs - np.array([u0, v0, w0])
    n = model.N_SIDE
    total = np.zeros(dirs.shape[0], dtype=complex)
    for origin, u, v, normal in _frames(layout):
        qu = q @ u
        qv = q @ v
        beta_u = 0.5 * C.WAVE_NUMBER * C.PITCH_M * qu
        beta_v = 0.5 * C.WAVE_NUMBER * C.PITCH_M * qv
        board = (np.exp(1j * (n - 1) * (beta_u + beta_v))
                 * model.board_factor(qu) * model.board_factor(qv))
        total += (_element(dirs @ normal, variant) * board
                  * np.exp(1j * C.WAVE_NUMBER * (q @ origin)))
    return total


def field_fn(layout, variant="mean"):
    return lambda dirs, u0, v0: field_v(layout, dirs, u0, v0, variant)


def evaluate(included_deg, offset_y_m, states, dirs, srange_du=0.02,
             variant="mean", step=0.012) -> dict:
    layout = v_pair_offset(included_deg, offset_y_m)
    fn = field_fn(layout, variant)
    comp = metrics.score_states_fn(fn, dirs, states, exact=True, step=step)
    sr = metrics.srange_fn(fn, search.AZIMUTHS, step_deg=1.0, du=srange_du,
                           exact=True)
    di = metrics.di0_fn(fn)
    pos = layout.positions
    row = {
        "key": layout.key,
        "included_deg": float(included_deg),
        "offset_mm": float(offset_y_m * 1e3),
        "span_mm": float((pos[:, 0].max() - pos[:, 0].min()) * 1e3),
        "depth_mm": float((pos[:, 2].max() - pos[:, 2].min()) * 1e3),
        "SL_cmd": comp["SL_cmd"], "SL_clean": comp["SL_clean"],
        "SL_near": comp["SL_near"], "SL_far_s": comp["SL_far_s"],
        "SL_diag": comp["SL_diag"], "DI0": di,
        "SRANGE_0dB": sr[0.0], "SRANGE_-3dB": sr[-3.0],
    }
    row["shortlist"] = report.provisional_score(row)
    return row


VARIANTS = ("mean", "left", "right", "wide")


def variant_envelope(row, states, dirs, step=0.012) -> None:
    """Element-pattern envelope for a front row (mean used for ranking)."""
    layout = v_pair_offset(row["included_deg"], row["offset_mm"] / 1e3)
    for variant in ("left", "right", "wide"):
        comp = metrics.score_states_fn(field_fn(layout, variant), dirs,
                                       states, exact=True, step=step)
        row[f"SL_cmd_{variant}"] = comp["SL_cmd"]
    row["SL_cmd_env"] = max([row["SL_cmd"]] + [row[f"SL_cmd_{v}"]
                                              for v in ("left", "right",
                                                        "wide")])


def search_v(included=np.arange(60.0, 181.0, 5.0),
             offsets_m=(0.0, 0.00525), states=None, du=0.012,
             srange_du=0.02):
    states = search.REFINE_STATES if states is None else states
    dirs, _, _, _ = model.direction_grid(du)
    rows = [evaluate(float(inc), float(off), states, dirs, srange_du,
                     step=du)
            for inc in included for off in offsets_m]
    front = sorted(search.pareto(rows), key=report.provisional_score)
    for row in front:
        variant_envelope(row, states, dirs, step=du)
    return rows, front


CSV_FIELDS = ["key", "included_deg", "offset_mm", "span_mm", "depth_mm",
              "SL_cmd", "SL_clean", "SL_near", "SL_far_s", "SL_diag",
              "SRANGE_0dB", "SRANGE_-3dB", "DI0", "shortlist",
              "SL_cmd_left", "SL_cmd_right", "SL_cmd_wide", "SL_cmd_env"]


def write_csv(rows, path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: (f"{row[k]:.3f}" if isinstance(row.get(k), float)
                                 else row.get(k, "")) for k in CSV_FIELDS})


def plot(rows, front, path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 2, figsize=(13, 5))
    ax = axs[0]
    for off, colour, marker in ((0.0, R.BLUE, "o"), (5.25, R.ORANGE, "s")):
        sel = [r for r in rows if abs(r["offset_mm"] - off) < 1e-6]
        ax.plot([r["included_deg"] for r in sel], [r["SL_cmd"] for r in sel],
                "-" + marker, color=colour, ms=4, lw=1.3,
                label=f"SL_cmd, y offset {off:.2f} mm")
        ax.plot([r["included_deg"] for r in sel], [r["SRANGE_0dB"] for r in sel],
                ":", color=colour, lw=1.1,
                label=f"SRANGE₀ (deg), y offset {off:.2f} mm")
    ax.set_xlabel("included angle (deg)")
    ax.set_title("V pair: worst sidelobe and 0 dB range", fontsize=12,
                 loc="left")
    ax.grid(alpha=0.22)
    ax.legend(fontsize=7)
    ax = axs[1]
    for off, marker in ((0.0, "o"), (5.25, "s")):
        sel = [r for r in rows if abs(r["offset_mm"] - off) < 1e-6]
        ax.scatter([r["SL_cmd"] for r in sel], [r["SL_diag"] for r in sel],
                   c=[r["included_deg"] for r in sel], cmap="viridis",
                   marker=marker, s=34)
    ax.plot([r["SL_cmd"] for r in front], [r["SL_diag"] for r in front],
            "o", mfc="none", mec=R.RED, ms=11, label="front")
    ax.set_xlabel("SL_cmd (dB)")
    ax.set_ylabel("SL_diag (dB)")
    ax.set_title("V-pair front (circles y=0, squares y=5.25)", fontsize=12,
                 loc="left")
    ax.grid(alpha=0.22)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--angles", default="60:180:5")
    ap.add_argument("--offsets", default="0,5.25",
                    help="comma-separated y offsets in mm")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args(argv)
    a, b, step = (float(x) for x in args.angles.split(":"))
    offsets = tuple(float(x) / 1e3 for x in args.offsets.split(","))
    rows, front = search_v(np.arange(a, b + step / 2, step), offsets)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    FIGS.mkdir(parents=True, exist_ok=True)
    write_csv(rows, out / "sweep_v.csv")
    write_csv(front, out / "front_v.csv")
    plot(rows, front, FIGS / "front_v.png")
    best = front[0] if front else min(rows, key=report.provisional_score)
    print(f"best V: {best['included_deg']:.0f} deg, y {best['offset_mm']:.2f} mm"
          f"  SL_cmd {best['SL_cmd']:.2f}  SL_diag {best['SL_diag']:.2f}"
          f"  SRANGE0 {best['SRANGE_0dB']:.0f}  DI0 {best['DI0']:.2f}")
    print("element envelope:", {k: round(best[k], 2)
                                for k in ("SL_cmd", "SL_cmd_left",
                                          "SL_cmd_right", "SL_cmd_wide",
                                          "SL_cmd_env")})
    print("front:", ", ".join(f"{r['included_deg']:.0f}deg/y{r['offset_mm']:.2f}"
                              for r in front))
    coplanar = ROOT / "data" / "search2" / "front_2.csv"
    if coplanar.exists():
        with open(coplanar, newline="", encoding="utf-8") as fh:
            cp = sorted(csv.DictReader(fh),
                        key=lambda r: float(r["shortlist"]))[0]
        print(f"coplanar leader: {cp['key']}  SL_cmd {float(cp['SL_cmd']):.2f}"
              f"  SL_diag {float(cp['SL_diag']):.2f}  SRANGE0 "
              f"{float(cp['SRANGE_0dB']):.0f}  DI0 {float(cp['DI0']):.2f}")
    print("DI0 is on-axis forward-hemisphere directivity, not peak DI when "
          "the command is buried.")


if __name__ == "__main__":
    main()
