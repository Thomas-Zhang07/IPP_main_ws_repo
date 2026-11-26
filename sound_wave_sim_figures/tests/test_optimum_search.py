"""Search tests: grids include the exact null seams, the front is
non-dominated, and a smoke score returns usable rows."""

from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sim"))

from optimum_search import search as Q


def test_candidate_counts_positive():
    assert len(Q.two_board_candidates()) > 2000
    assert len(Q.three_board_candidates()) > 20000


def test_exact_null_seams_present():
    seams = Q.seam_values(two_board=True)
    assert any(abs(s - 0.01575) < 1e-9 for s in seams)
    assert any(abs(s - 0.02625) < 1e-9 for s in seams)


def test_pareto_non_dominated():
    rows = [{"k": 0, "SL_cmd": -3.0, "SL_diag": -2.0, "DI0": 10.0},
            {"k": 1, "SL_cmd": -2.0, "SL_diag": -3.0, "DI0": 10.0},
            {"k": 2, "SL_cmd": -2.0, "SL_diag": -1.0, "DI0": 9.0}]
    front = Q.pareto(rows)
    assert {r["k"] for r in front} == {0, 1}


def test_key_roundtrip_and_load(tmp_path):
    rows = [{"key": "pair_15.750_2.625", "n_boards": 2, "span_mm": 331.0,
             "SL_cmd": -1.0, "SL_diag": -3.0, "DI0": 42.0}]
    path = tmp_path / "front.csv"
    Q.write_csv(rows, path)
    loaded = Q.load_front(path)
    assert loaded[0]["cand"].key == "pair_15.750_2.625"
    assert loaded[0]["SL_cmd"] == pytest.approx(-1.0)


def test_front_roundtrip_keeps_robustness(tmp_path):
    rows = [{"key": "pair_15.750_2.625", "n_boards": 2, "span_mm": 331.0,
             "SL_cmd": 2.2, "SL_near": -12.5, "SL_diag": -0.9, "DI0": 41.9,
             "robust_max": 0.6, "shortlist": -3.0}]
    path = tmp_path / "front.csv"
    Q.write_csv(rows, path)
    loaded = Q.load_front(path)
    assert loaded[0]["cand"].key == "pair_15.750_2.625"
    assert loaded[0]["robust_max"] == pytest.approx(0.6)
    assert loaded[0]["shortlist"] == pytest.approx(-3.0)


def test_smoke_two_board_scores():
    rows = Q.score_rows(
        [Q.model.pair(0.01575, 0.002625), Q.model.pair(0.01575, 0.00525)],
        states=[(0.0, 0.0), (20.0, 45.0), (35.0, 45.0)], du=0.01)
    assert len(rows) == 2
    for row in rows:
        for key in ("SL_cmd", "SL_clean", "SL_near", "SL_far_s", "SL_diag"):
            assert key in row
    # at 35 deg diagonal the minimax layout beats the axial-null pair
    assert rows[0]["SL_diag"] <= rows[1]["SL_diag"] + 0.5
