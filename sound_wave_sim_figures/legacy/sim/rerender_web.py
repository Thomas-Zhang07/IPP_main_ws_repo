"""Regenerate every 3D page with data labels and the comparison inset."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sim"))

import cache  # noqa: E402
import field  # noqa: E402
import geometry  # noqa: E402
import optimize  # noqa: E402
import render_png  # noqa: E402
import export_web  # noqa: E402

WEB = ROOT / "web"


def main():
    entries = []
    for layout in geometry.baseline_layouts():
        m = None
        if layout.far_field:
            m = cache.analysis(layout, du=0.004)
        res = 0.0025 if layout.key == "06_facing" else 0.005
        near = cache.near(layout, res=res)
        export_web.write_page(layout, m, near, WEB)
        entries.append({
            "key": layout.key, "tag": "baseline", "title": layout.title,
            "stat": ("no far field" if m is None else
                     f"DI {m['di_db']:.1f} dB · band {m['band_energy_pct']:.1f} %"),
        })
        print("page", layout.key, flush=True)

    verdict = json.load(open(ROOT / "verdict.json", encoding="utf-8"))
    layout = optimize.layout_from_row(verdict["best_three"])
    m = cache.analysis(layout, du=0.003)
    near = cache.near(layout, res=0.005)
    export_web.write_page(layout, m, near, WEB)
    entries.append({
        "key": layout.key, "tag": "searched optimum", "title": layout.title,
        "stat": f"DI {m['di_db']:.1f} dB · band {m['band_energy_pct']:.1f} %",
    })
    export_web.write_index(entries, WEB)
    print("index written")


if __name__ == "__main__":
    main()
