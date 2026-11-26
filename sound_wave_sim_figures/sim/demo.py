"""Build the offline array comparison from the same solvers as the steering study."""
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
from optimum_search.model import from_key

ROOT = Path(__file__).resolve().parents[1]
COMMANDS = (0, 20, 35)
NT, NP = 61, 120
RADIUS = 2.0


def layouts():
    saved = json.loads((ROOT / "data/search2/leaders.json").read_text())
    best2, best3 = (from_key(saved[k]) for k in ("2", "3"))
    pair = G._pair_coplanar(*best2.seams_m, best2.offsets_m[1], best2.key,
                            "Search pair", "")
    triple = G.coplanar3(*best3.seams_m, best3.offsets_m, best3.key, "Search triple")
    return [(G.single(), "Single board"), (G.coplanar_gap(), "Current pair"),
            (G.v_pair(120, "03_v120", "V120"), "V120"),
            (G.v_pair(150, "02_v150", "V150"), "V150"),
            (pair, "Search pair"), (triple, "Search triple")]


def angles():
    theta, phi = np.meshgrid(np.linspace(0, np.pi/2, NT),
                             np.arange(NP) * (2*np.pi/NP), indexing="ij")
    mesh = np.column_stack([(np.sin(theta)*np.cos(phi)).ravel(),
                            (np.sin(theta)*np.sin(phi)).ravel(), np.cos(theta).ravel()])
    angle = np.linspace(-90, 90, 721)
    rad = np.radians(angle)
    cut = np.column_stack([np.sin(rad), np.zeros_like(rad), np.cos(rad)])
    return np.vstack([mesh, cut])


def encode(level):
    # One byte per sample; -50 to +1 dB, in 0.2 dB steps.
    db = 20*np.log10(np.maximum(level, 1e-12))
    return base64.b64encode(np.rint((np.clip(db, -50, 1)+50)*5).astype("u1")).decode()


def scene(layout, label, dirs, commands=COMMANDS):
    pos, normals = layout.positions, layout.normals
    origin = np.zeros(3)
    if np.ptp(pos[:, 2]) == 0:
        origin = (pos.min(axis=0) + pos.max(axis=0)) / 2
    u = np.sin(np.radians(commands))
    far = S._patterns(layout, dirs, u, np.zeros_like(u), S.ELEMENTS)
    states = {}
    for j, steer in enumerate(commands):
        k0 = np.array([u[j], 0, np.cos(np.radians(steer))])
        weights = np.exp(-1j * C.WAVE_NUMBER * (pos @ k0))
        for kind in S.ELEMENTS:
            fn = transducer.amplitude if kind == "measured" else np.ones_like
            near = field.near_field_points(pos, normals, weights, origin + RADIUS*dirs,
                                           chunk=128, element_pattern=fn)
            states[f"{steer}/{kind}/far"] = encode(np.abs(far[kind][:, j])/len(pos))
            states[f"{steer}/{kind}/2m"] = encode(RADIUS*np.abs(near)/len(pos))
    boards = [np.round((b.outline-origin)*1000, 1).tolist() for b in layout.boards]
    return dict(key=layout.key, label=label, emitters=len(pos), boards=boards, states=states)


def build(path):
    dirs = angles()
    data = dict(nt=NT, np=NP, commands=COMMANDS,
                layouts=[scene(g, label, dirs) for g, label in layouts()])
    template = Path(__file__).with_name("demo_template.html").read_text(encoding="utf-8")
    path.write_text(template.replace("__DATA__", json.dumps(data, separators=(",", ":"))),
                    encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "docs/array-demo.html")
    build(parser.parse_args().out)
