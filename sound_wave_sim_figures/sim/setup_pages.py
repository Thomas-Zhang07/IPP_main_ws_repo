"""Standalone 3D field viewers, one HTML page per board layout.

Each page carries the same controls (command angle, measured/isotropic element,
far field or 2 m microphone) but a single layout, so the Feishu section can
attach one small interactive file per setup instead of one monolith.

Pages land in ``E:\\LUIS\\IPP\\report\\assets\\11.26\\3d``.

Run::

    python setup_pages.py [--out DIR] [--only KEY]
"""

from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path

import numpy as np

import constants as C
import field
import geometry as G
import steering_study as S
import transducer
from optimum_search import model, vshape
from optimum_search.model import from_key

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(r"E:\LUIS\IPP\report\assets\11.26\3d")
TEMPLATE = Path(__file__).with_name("setup_template.html")

COMMANDS = np.arange(0.0, 70.0 + 1e-9, 5.0)
NT, NP = 61, 120
RADIUS = 2.0
DEFAULT_ANGLE = 35.0


def _leaders():
    saved = json.loads((ROOT / "data/search2/leaders.json").read_text())
    best2, best3 = (from_key(saved[k]) for k in ("2", "3"))
    pair = G._pair_coplanar(*best2.seams_m, best2.offsets_m[1], best2.key,
                            "Search pair (coplanar leader)", "")
    triple = G.coplanar3(*best3.seams_m, best3.offsets_m, best3.key,
                         "Search triple (coplanar leader)")
    return pair, triple


def layouts():
    pair, triple = _leaders()
    v135 = vshape.v_pair_offset(135.0, 0.00525)
    return [
        ("01_single", "Single board", G.single,
         "One 16 x 16 panel at broadside. The only grating staircase here is "
         "the panel's own ±54.75° order."),
        ("02_v120", "V 120°", lambda: G.v_pair(120.0, "03_v120",
                                               "Two boards, V 120 deg"),
         "Two panels hinged at 120°. The drive is depth-compensated, so the "
         "hinge angle changes the aperture, not the command."),
        ("03_v150", "V 150°", lambda: G.v_pair(150.0, "02_v150",
                                               "Two boards, V 150 deg"),
         "Two panels hinged at 150°, the shallow V. Compare with 120°: the "
         "flatter pair keeps more forward gain and loses the deep null."),
        ("04_current_pair", "Current pair", G.coplanar_gap,
         "The as-built butted pair with the cable seam: the seam suppresses "
         "the x-axis grating lobes but not the y-axis ones."),
        ("05_seam_only", "Same seam, y = 0", G.pair_seam_only,
         "Control for the 5.25 mm offset: same seam, boards aligned in y. "
         "All four axial grating lobes come back."),
        ("06_concave3", "Concave 3-board", lambda: G.concave3(30.0),
         "Three panels on a 30° concave arc, driven with the projected "
         "phase control, i.e. no per-board depth compensation."),
        ("07_coplanar3", "Coplanar 3-board", G.coplanar3,
         "Three coplanar panels: the extra aperture buys gain, not a lower "
         "worst-case sidelobe."),
        ("08_pair_leader", "Best 2-board (search)", lambda: pair,
         "Coplanar leader of the 2-board search: seams 16.00 / 5.25 mm, "
         "chosen on the joint sidelobe and range score."),
        ("09_triple_leader", "Best 3-board (search)", lambda: triple,
         "Coplanar leader of the 3-board search: seams 18.50 / 14.75 / "
         "10.50 / 5.25 mm."),
        ("10_v135", "V 135° (search)", lambda: v135,
         "Best V pair: 135° included angle with board B shifted 5.25 mm "
         "along the hinge, which nulls the y-axis grating."),
    ]


def directions():
    theta, phi = np.meshgrid(np.linspace(0, np.pi / 2, NT),
                             np.arange(NP) * (2 * np.pi / NP), indexing="ij")
    mesh = np.column_stack([(np.sin(theta) * np.cos(phi)).ravel(),
                            (np.sin(theta) * np.sin(phi)).ravel(),
                            np.cos(theta).ravel()])
    angle = np.linspace(-90, 90, 721)
    rad = np.radians(angle)
    cut = np.column_stack([np.sin(rad), np.zeros_like(rad), np.cos(rad)])
    return np.vstack([mesh, cut])


def encode(level):
    db = 20 * np.log10(np.maximum(level, 1e-12))
    return base64.b64encode(
        np.rint((np.clip(db, -50, 1) + 50) * 5).astype("u1")).decode()


def scene(layout, title, details, dirs):
    pos, normals = layout.positions, layout.normals
    origin = np.zeros(3)
    if np.ptp(pos[:, 2]) == 0:
        origin = (pos.min(axis=0) + pos.max(axis=0)) / 2
    u = np.sin(np.radians(COMMANDS))
    far = S._patterns(layout, dirs, u, np.zeros_like(u), S.ELEMENTS)
    states = {}
    for j, steer in enumerate(COMMANDS):
        for kind in S.ELEMENTS:
            states[f"{steer:.0f}/{kind}/far"] = encode(
                np.abs(far[kind][:, j]) / len(pos))
    k0 = np.array([[u[j], 0.0, np.cos(np.radians(COMMANDS[j]))]
                   for j in range(len(COMMANDS))])
    for j, steer in enumerate(COMMANDS):
        weights = np.exp(-1j * C.WAVE_NUMBER * (pos @ k0[j]))
        for kind in S.ELEMENTS:
            fn = transducer.amplitude if kind == "measured" else np.ones_like
            near = field.near_field_points(pos, normals, weights,
                                           origin + RADIUS * dirs,
                                           chunk=128, element_pattern=fn)
            states[f"{steer:.0f}/{kind}/2m"] = encode(
                RADIUS * np.abs(near) / len(pos))
    boards = [np.round((b.outline - origin) * 1000, 1).tolist()
              for b in layout.boards]
    span = float(np.ptp(pos[:, 0]))
    return dict(key=layout.key, label=title, details=details,
                nt=NT, np=NP,
                emitters=len(pos), boards=boards,
                angles=[float(a) for a in COMMANDS],
                default_angle=DEFAULT_ANGLE,
                span=f"{span * 1e3:.0f} mm span", states=states)


def build(out_dir: Path, only: str | None = None) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    template = TEMPLATE.read_text(encoding="utf-8")
    dirs = directions()
    written = []
    for key, title, ctor, details in layouts():
        if only and only not in key:
            continue
        layout = ctor()
        data = scene(layout, title, details, dirs)
        markup = (template
                  .replace("__TITLE__", title)
                  .replace("__EMITTERS__", str(data["emitters"]))
                  .replace("__SPAN__", data["span"])
                  .replace("__KEY__", layout.key)
                  .replace("__MAXI__", str(len(data["angles"]) - 1))
                  .replace("__DEFI__", str(data["angles"].index(DEFAULT_ANGLE)))
                  .replace("__DATA__", json.dumps(data, separators=(",", ":"))))
        path = out_dir / f"{key}.html"
        path.write_text(markup, encoding="utf-8")
        written.append(path)
        print(f"{path.name}  {path.stat().st_size / 1024:.0f} KB")
    return written


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--only", default=None)
    args = ap.parse_args(argv)
    build(args.out, args.only)


if __name__ == "__main__":
    main()
