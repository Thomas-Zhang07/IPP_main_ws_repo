"""End-to-end orchestration: coarse sweep, refine, front, robustness, report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from . import gallery, metrics, model, report, robustness, search

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "search2"
FIGS = ROOT / "figures" / "search2"
DOC = ROOT / "docs" / "2026-11-26-optimal-search-report.md"

ROBUST_STATES = [(0.0, 0.0), (20.0, 0.0), (20.0, 45.0),
                 (35.0, 0.0), (35.0, 45.0), (35.0, 90.0), (35.0, 135.0),
                 (35.0, 180.0), (35.0, 225.0), (35.0, 270.0), (35.0, 315.0)]

SEEDS_TWO = (model.pair(0.01575, 0.002625),
             model.pair(0.01575, 0.00525),
             model.pair(0.02625, 0.00525))

SEEDS_THREE = (model.triple(0.014, 0.014, 0.0035, 0.0070),
               model.triple(0.014, 0.014, 0.00525, 0.0),
               model.triple(0.0175, 0.0175, 0.0035, 0.0070),
               model.triple(0.014, 0.0245, 0.0035, 0.0070),
               model.triple(0.0245, 0.0245, 0.0035, 0.0070))


def _provisional(row) -> float:
    return row["SL_cmd"] + 0.3 * row["SL_diag"]


def _dedupe(cands):
    seen, out = set(), []
    for cand in cands:
        if cand.key not in seen:
            seen.add(cand.key)
            out.append(cand)
    return out


def _dedupe_rows(rows):
    seen, out = set(), []
    for row in rows:
        key = row["cand"].key
        if key not in seen:
            seen.add(key)
            out.append(row)
    return out


def _with_seeds(leaders, seeds):
    keys = {r["cand"].key for r in leaders}
    extra = [c for c in seeds if c.key not in keys]
    if not extra:
        return leaders
    dirs, _, _, _ = model.direction_grid(0.02)
    rows = search.score_rows(extra, search.COARSE_STATES, dirs=dirs)
    return leaders + rows


def _finish(leaders, du_fine=0.01, du_leader=0.004, srange_du=0.02,
            probe_n=80, robust_top=5):
    cands = _dedupe([r["cand"] for r in leaders])
    dirs_f, _, _, _ = model.direction_grid(du_fine)
    rows = search.score_rows(cands, search.REFINE_STATES, dirs=dirs_f)
    for row in rows:
        row.update(metrics.report_metrics(row["cand"]))

    probes = sorted(rows, key=_provisional)[:probe_n]
    search.add_srange(probes, top_n=len(probes), step_deg=1.0, du=srange_du)
    sr = {r["key"]: (r.get("SRANGE_0dB", np.nan), r.get("SRANGE_-3dB", np.nan))
          for r in probes}

    dirs_l, _, _, _ = model.direction_grid(du_leader)
    fine = search.score_rows([r["cand"] for r in probes[:15]],
                             search.REFINE_STATES, dirs=dirs_l)
    for row in fine:
        row.update(metrics.report_metrics(row["cand"]))
        row["SRANGE_0dB"], row["SRANGE_-3dB"] = sr[row["key"]]
    fine_keys = {r["key"] for r in fine}
    merged = fine + [r for r in probes if r["key"] not in fine_keys]

    front = sorted(search.pareto(merged), key=report.provisional_score)
    for row in front[:robust_top]:
        row.update(robustness.robust(row["cand"], ROBUST_STATES,
                                     n_draws=100, du=0.02))
    for row in front:
        row["shortlist"] = report.shortlist_score(row)
    leader = (min(front[:robust_top], key=report.shortlist_score)
              if front else None)
    return rows, front, leader


def run_two(top_k=200, du_coarse=0.02):
    rows = search.score_rows(search.two_board_candidates(),
                             search.COARSE_STATES, du=du_coarse)
    rows.sort(key=_provisional)
    keep = _dedupe_rows([r for r in rows[:top_k]]
                        + search.pareto2(rows)[:top_k])
    leaders = _with_seeds(keep, SEEDS_TWO)
    return _finish(leaders)


def three_board_coarse():
    seams = sorted(set(search.seam_values(False)[::2])
                   | set(search.EXACT_SEAMS))
    offsets = [0.0, 0.0035, 0.00525, 0.007, 0.0105]
    return [model.triple(s1, s2, o2, o3)
            for s1 in seams for s2 in seams for o2 in offsets for o3 in offsets]


def run_three(top_k=200, du_coarse=0.025):
    rows = search.score_rows(three_board_coarse(), search.COARSE_STATES,
                             du=du_coarse)
    rows.sort(key=_provisional)
    seeds = _dedupe_rows([r for r in rows[:60]] + search.pareto2(rows))
    local = []
    for row in seeds[:40]:
        cand = row["cand"]
        for ds1 in (-0.001, 0.0, 0.001):
            for ds2 in (-0.001, 0.0, 0.001):
                for do2 in (-0.001, 0.0, 0.001):
                    for do3 in (-0.001, 0.0, 0.001):
                        s1 = max(cand.seams_m[0] + ds1, search.BUILD_MIN_M)
                        s2 = max(cand.seams_m[1] + ds2, search.BUILD_MIN_M)
                        o2 = float(np.clip(cand.offsets_m[1] + do2, 0.0,
                                           search.OFFSET_MAX_M))
                        o3 = float(np.clip(cand.offsets_m[2] + do3, 0.0,
                                           search.OFFSET_MAX_M))
                        local.append(model.triple(s1, s2, o2, o3))
    local_rows = search.score_rows(_dedupe(local), search.COARSE_STATES,
                                   du=du_coarse)
    local_rows.sort(key=_provisional)
    leaders = _dedupe_rows([r for r in local_rows[:top_k]]
                           + search.pareto2(local_rows)[:top_k])
    leaders = _with_seeds(leaders, SEEDS_THREE)
    return _finish(leaders)


def _reference_rows(cands):
    dirs, _, _, _ = model.direction_grid(0.008)
    rows = []
    for cand in cands:
        vals = metrics.score_states(cand, 0.008, search.REFINE_STATES,
                                    dirs=dirs)
        vals.update(metrics.report_metrics(cand))
        sr = metrics.srange(cand, search.AZIMUTHS, step_deg=1.0, du=0.02)
        vals["SRANGE_0dB"] = sr[0.0]
        vals["SRANGE_-3dB"] = sr[-3.0]
        rows.append({"key": cand.key, "n_boards": cand.n_boards,
                     "span_mm": cand.span_m * 1e3,
                     "span_y_mm": cand.span_y_m * 1e3, **vals})
    return rows


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--two", action="store_true")
    ap.add_argument("--three", action="store_true")
    ap.add_argument("--gallery", action="store_true")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--out", default=str(FIGS))
    args = ap.parse_args(argv)

    out = Path(args.out)
    DATA.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)

    front2, front3 = [], []
    leader2 = leader3 = None
    if args.two:
        print("two-board sweep ...")
        _, front2, leader2 = run_two()
        search.write_csv(front2, DATA / "front_2.csv")
        report.front_figure(front2, out / "front_2.png",
                            "2-board front — measured element")
        report.trade_figure(front2, out / "trade_2.png",
                            "2-board trade-off")
    if args.three:
        print("three-board sweep ...")
        _, front3, leader3 = run_three()
        search.write_csv(front3, DATA / "front_3.csv")
        report.front_figure(front3, out / "front_3.png",
                            "3-board front — measured element")
        report.trade_figure(front3, out / "trade_3.png",
                            "3-board trade-off")

    if args.gallery and not front2 and (DATA / "front_2.csv").exists():
        front2 = search.load_front(DATA / "front_2.csv")
    if args.gallery and not front3 and (DATA / "front_3.csv").exists():
        front3 = search.load_front(DATA / "front_3.csv")
    for front in (front2, front3):
        for row in front:
            row["shortlist"] = report.shortlist_score(row)

    saved = {}
    if (DATA / "leaders.json").exists():
        saved = json.loads((DATA / "leaders.json").read_text(encoding="utf-8"))
    leaders = {}
    for tag, front, leader in (("2", front2, leader2), ("3", front3, leader3)):
        if not front:
            continue
        if leader is None:
            key = saved.get(tag)
            leader = next((r for r in front if r["key"] == key), front[0])
        leaders[tag] = leader
    if leaders and (leader2 or leader3):
        saved.update({tag: row["key"] for tag, row in leaders.items()})
        (DATA / "leaders.json").write_text(json.dumps(saved, indent=2),
                                           encoding="utf-8")

    if "2" in leaders:
        report.leader_curve(leaders["2"]["cand"], out / "leader_2.png")
    if "3" in leaders:
        report.leader_curve(leaders["3"]["cand"], out / "leader_3.png")
    references = {"2": _reference_rows(SEEDS_TWO),
                  "3": _reference_rows(SEEDS_THREE)}
    report.write_report(front2, front3, leaders, DOC, references=references)
    print(f"report: {DOC}")

    if args.gallery:
        for tag, row in leaders.items():
            print(f"gallery optimum_{tag}: {row['key']} ...")
            gallery.render_optimum(row["cand"], out / f"optimum_{tag}")
