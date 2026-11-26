"""Build web/overlay.html: all layouts, two at a time with opacity control."""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sim"))

import cache  # noqa: E402
import field  # noqa: E402
import geometry  # noqa: E402
import optimize  # noqa: E402
import export_web  # noqa: E402

WEB = ROOT / "web"
DU = 0.006


def quantise(m):
    U, V, db = m["U"], m["V"], m["db"]
    q = np.full(db.shape, 255, dtype=np.uint8)
    valid = np.isfinite(db)
    q[valid] = np.clip(np.round((np.clip(db[valid], -40, 0) + 40) / 40 * 250),
                       0, 250).astype(np.uint8)
    return ([round(float(x), 4) for x in U[0]],
            [round(float(x), 4) for x in V[:, 0]],
            base64.b64encode(q.tobytes()).decode(), db.shape[1], db.shape[0])


def entry(layout, m):
    u, v, db64, nu, nv = quantise(m)
    return {
        "key": layout.key,
        "title": layout.title,
        "nu": nu, "nv": nv,
        "u": u, "v": v, "db": db64,
        "metrics": {
            "di_db": m["di_db"],
            "band_max_db": m["band_max_db"],
            "band_energy_pct": m["band_energy_pct"],
            "leak_60_pct": m["leak_60_pct"],
            "lobe_54_75_db": m["lobe_54_75_db"],
        },
        "boards": [
            {
                "outline": [[round(float(x), 4) for x in p] for p in b.outline],
                "normal": [round(float(x), 4) for x in b.normals[0]],
            }
            for b in layout.boards
        ],
    }


def main():
    layouts = [l for l in geometry.baseline_layouts() if l.far_field]
    verdict = json.load(open(ROOT / "verdict.json", encoding="utf-8"))
    layouts.append(optimize.layout_from_row(verdict["best_three"]))

    data = []
    for layout in layouts:
        m = cache.analysis(layout, du=DU)
        data.append(entry(layout, m))
        print("overlay data", layout.key, flush=True)

    export_web.write_overlay(data, WEB / "overlay.html",
                             default_a="05_coplanar_gap",
                             default_b="09_pair_seam_only")
    print("overlay written")

    index = WEB / "index.html"
    if index.exists():
        html = index.read_text(encoding="utf-8")
        card = ('<a class="card" href="overlay.html"><div class="tag">compare</div>'
                '<div class="name">Overlay two layouts</div>'
                '<div class="stat">two surfaces, independent opacity</div></a>')
        if "overlay.html" not in html:
            html = html.replace("<main>", "<main>\n" + card, 1)
            index.write_text(html, encoding="utf-8")
            print("index linked")


if __name__ == "__main__":
    main()
