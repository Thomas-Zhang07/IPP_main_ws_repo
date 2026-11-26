"""Report and gallery smoke tests: figures are written and the report names
the leaders."""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sim"))

from optimum_search import gallery as G, model as M, report as P

ROWS = [{"key": "pair_15.750_2.625", "n_boards": 2, "span_mm": 331.0,
         "SL_cmd": -13.0, "SL_diag": -3.0, "DI0": 38.5, "SL_clean": -13.0,
         "SL_near": -13.0, "SRANGE_0dB": 24.0, "SRANGE_-3dB": 20.0}]


def test_front_figure(tmp_path):
    out = tmp_path / "front.png"
    P.front_figure(ROWS, out, "test front")
    assert out.exists() and out.stat().st_size > 1000


def test_report_contains_front(tmp_path):
    out = tmp_path / "report.md"
    P.write_report(ROWS, ROWS, {"2": ROWS[0]}, out)
    text = out.read_text(encoding="utf-8")
    assert "pair_15.750_2.625" in text and "SL_cmd" in text


def test_gallery_small(tmp_path):
    cand = M.pair(0.01575, 0.002625)
    rows = G.render_optimum(cand, tmp_path,
                            states=[(0.0, 0.0), (20.0, 45.0)])
    assert len(rows) == 2
    for sub in ("3d", "polar", "uv", "amplitude"):
        files = list((tmp_path / sub).glob("*.png"))
        assert len(files) == 2 and files[0].stat().st_size > 1000
    assert (tmp_path / "metrics.csv").exists()
