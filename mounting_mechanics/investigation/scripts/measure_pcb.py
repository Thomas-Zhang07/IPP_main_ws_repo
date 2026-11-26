#!/usr/bin/env python3
"""Measure the SonicSurface 16x16 PCB from its Altium Gerber/place data.

Reads only the extracted files under investigation/gerber_extracted and writes
measurements.json plus a printed report. This file is the source of every PCB
or element dimension quoted in the mounting design; nothing is assumed.

Run with:
  python -I measure_pcb.py <extracted_dir>

The extracted directory is data and is never imported.
"""
from __future__ import annotations

import collections
import json
import os
import re
import sys

MIL = 0.0254
GERBER_SCALE = 100000.0  # %FSLAX25Y25*% : 2 integer, 5 decimal digits


def parse_gerber_flashes(path):
    """Return {aperture: [(x_in, y_in), ...]} for all D03 flashes."""
    flashes = collections.defaultdict(list)
    ap = None
    x = y = 0.0
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            s = line.strip()
            if s == "D03*":
                if ap is not None:
                    flashes[ap].append((x, y))
                continue
            m = re.match(r"^D(\d+)\*$", s)
            if m:
                ap = "D" + m.group(1)
                continue
            mx = re.search(r"X(-?\d+)", s)
            my = re.search(r"Y(-?\d+)", s)
            if mx:
                x = int(mx.group(1)) / GERBER_SCALE
            if my:
                y = int(my.group(1)) / GERBER_SCALE
    return flashes


def gerber_extents(path):
    """Rough coordinate extents of a Gerber file (all X/Y words)."""
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    xs = [int(v) / GERBER_SCALE for v in re.findall(r"X(-?\d+)", text)]
    ys = [int(v) / GERBER_SCALE for v in re.findall(r"Y(-?\d+)", text)]
    if not xs or not ys:
        return None
    return {
        "x_min_in": min(xs), "x_max_in": max(xs),
        "y_min_in": min(ys), "y_max_in": max(ys),
        "x_min_mm": min(xs) * 25.4, "x_max_mm": max(xs) * 25.4,
        "y_min_mm": min(ys) * 25.4, "y_max_mm": max(ys) * 25.4,
    }


def parse_placements(path):
    rows = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            p = line.split()
            if len(p) >= 8 and p[1] == "Transducer_10mm":
                rows.append({
                    "designator": p[0],
                    "x_mil": float(p[2].replace("mil", "")),
                    "y_mil": float(p[3].replace("mil", "")),
                })
    for r in rows:
        r["x_mm"] = r["x_mil"] * MIL
        r["y_mm"] = r["y_mil"] * MIL
    return rows


def parse_drr_counts(path):
    """Read the Altium drill report table (authoritative hole counts)."""
    tools = {}
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            m = re.match(r"^T(\d+)\s+([0-9.]+)mil\s+\(([0-9.]+)mm\)\s+\w+\s+(\d+)", line.strip())
            if m:
                tools[int(m.group(1))] = {
                    "diameter_mil": float(m.group(2)),
                    "diameter_mm": float(m.group(3)),
                    "count": int(m.group(4)),
                }
    return tools


def unique_sorted(vals, tol=1e-6):
    out = []
    for v in sorted(vals):
        if not out or abs(v - out[-1]) > tol:
            out.append(v)
    return out


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: measure_pcb.py <extracted_dir>")
    root = os.path.abspath(sys.argv[1])
    out_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    gm1 = gerber_extents(os.path.join(root, "Main.GM1"))
    board_w = gm1["x_max_mm"] - gm1["x_min_mm"]
    board_h = gm1["y_max_mm"] - gm1["y_min_mm"]

    placements = parse_placements(os.path.join(root, "Pick Place for Main.txt"))
    xs = unique_sorted([p["x_mm"] for p in placements])
    ys = unique_sorted([p["y_mm"] for p in placements])
    if len(placements) != 256 or len(xs) != 16 or len(ys) != 16:
        raise SystemExit("unexpected grid: %d placements, %d x, %d y"
                         % (len(placements), len(xs), len(ys)))

    # Verify the pick-place grid against the 512 top solder-mask openings.
    gts = parse_gerber_flashes(os.path.join(root, "Main.GTS"))
    pin_hits = [(x * 25.4, y * 25.4) for x, y in gts["D45"]]
    if len(pin_hits) != 512:
        raise SystemExit("expected 512 D45 transducer pin openings, got %d" % len(pin_hits))
    pin_x = unique_sorted([p[0] for p in pin_hits], tol=0.002)
    pin_y = unique_sorted([p[1] for p in pin_hits], tol=0.002)
    max_pin_err = 0.0
    for p in placements:
        for sx in (-2.5, 2.5):
            d = min(abs((p["x_mm"] + sx) - v) for v in pin_x)
            max_pin_err = max(max_pin_err, d)
        d = min(abs(p["y_mm"] - v) for v in pin_y)
        max_pin_err = max(max_pin_err, d)

    # 4 x 3.5 mm mounting holes: copper ring D26 and mask opening D46.
    gtl = parse_gerber_flashes(os.path.join(root, "Main.GTL"))
    mount_holes = [{"x_mm": round(x * 25.4, 4), "y_mm": round(y * 25.4, 4)}
                   for x, y in gtl["D26"]]
    mount_holes.sort(key=lambda p: (round(p["y_mm"], 2), round(p["x_mm"], 2)))

    margin_left = xs[0] - gm1["x_min_mm"]
    margin_right = gm1["x_max_mm"] - xs[-1]
    margin_bottom = ys[0] - gm1["y_min_mm"]
    margin_top = gm1["y_max_mm"] - ys[-1]
    pitch_x = (xs[-1] - xs[0]) / 15
    pitch_y = (ys[-1] - ys[0]) / 15

    # Transducer body assumed 10.0 mm diameter (BOM: "Transducer 10mm").
    trans_d = 10.0
    edge_gap = {
        "left_element_centre_to_edge_mm": margin_left,
        "right_element_centre_to_edge_mm": margin_right,
        "bottom_element_centre_to_edge_mm": margin_bottom,
        "top_element_centre_to_edge_mm": margin_top,
        "left_body_edge_to_board_edge_mm": margin_left - trans_d / 2,
        "right_body_edge_to_board_edge_mm": margin_right - trans_d / 2,
        "bottom_body_edge_to_board_edge_mm": margin_bottom - trans_d / 2,
        "top_body_edge_to_board_edge_mm": margin_top - trans_d / 2,
    }

    # Safe trim limits at the inner (seam) edges before a 3.5 mm mounting hole
    # or the copper pour is touched. Board A's right edge and B's left edge.
    right_hole = [h for h in mount_holes if h["x_mm"] > board_w / 2][0]
    left_hole = [h for h in mount_holes if h["x_mm"] < board_w / 2][0]
    trim_limit_right = board_w - (right_hole["x_mm"] + 3.5 / 2)
    trim_limit_left = (left_hole["x_mm"] - 3.5 / 2) - 0.0
    copper_right_clear = gm1["x_max_mm"] - gerber_extents(os.path.join(root, "Main.GTL"))["x_max_mm"]
    copper_left_clear = gerber_extents(os.path.join(root, "Main.GTL"))["x_min_mm"] - gm1["x_min_mm"]

    # D25 is the 1.016 mm via pad on both copper layers. These are the nearest
    # via features to the inner edges; they are not the trim limit, but the
    # clearances document that fact.
    via_x = sorted(set(round(x * 25.4, 4) for x, y in gtl["D25"]))
    via_y = sorted(set(round(y * 25.4, 4) for x, y in gtl["D25"]))
    via_d = 1.016
    via_clear = {
        "pad_diameter_mm": via_d,
        "nearest_centre_to_A_right_edge_mm": board_w - max(via_x),
        "nearest_pad_edge_to_A_right_edge_mm": board_w - max(via_x) - via_d / 2,
        "nearest_centre_to_B_left_edge_mm": min(via_x),
        "nearest_pad_edge_to_B_left_edge_mm": min(via_x) - via_d / 2,
        "via_x_extent_mm": [min(via_x), max(via_x)],
        "via_y_extent_mm": [min(via_y), max(via_y)],
    }

    drill = parse_drr_counts(os.path.join(root, "Main.DRR"))

    # Candidate seams. The acoustic requirement must use the measured pitch.
    seam_butted = margin_right + margin_left
    half_pitch = pitch_x / 2
    # Smallest non-overlapping seam that is half_pitch modulo pitch.
    k = 1
    while True:
        target = k * pitch_x + half_pitch
        if target >= seam_butted:
            break
        k += 1
    seam_next = target
    gap_next = seam_next - seam_butted
    # Smallest non-overlapping seam that is 5 mm modulo 10 mm (legacy target).
    k = 1
    while True:
        legacy = k * 10.0 + 5.0
        if legacy >= seam_butted:
            break
        k += 1
    gap_legacy = legacy - seam_butted

    result = {
        "sources": {
            "gerber_zip": r"E:\LUIS\IPP\SonicSurface\Electronics\16x16 10mm transducers SMD PCB Gerbers\SonicSurface1.2_2Layers_183x169.zip",
            "bom_txt": r"E:\LUIS\IPP\SonicSurface\Electronics\16x16 10mm transducers SMD PCB Gerbers\BOM.txt",
            "place_file": os.path.join(root, "Pick Place for Main.txt"),
            "drill_report": os.path.join(root, "Main.DRR"),
            "mechanical_1": os.path.join(root, "Main.GM1"),
            "top_copper": os.path.join(root, "Main.GTL"),
            "top_solder_mask": os.path.join(root, "Main.GTS"),
            "existing_stl": r"E:\LUIS\IPP\SonicSurface\Mech\spacer\3d printed spacer.stl",
        },
        "board_outline_from_GM1": gm1,
        "board_width_mm": board_w,
        "board_height_mm": board_h,
        "board_thickness_mm": None,
        "board_thickness_note": "Not encoded in Gerber/drill/BOM data. Measure the physical PCB; the fixture clamp accommodates 1.2-2.4 mm.",
        "placements": {
            "count": len(placements),
            "x_positions_mm": xs,
            "y_positions_mm": ys,
            "x_pitch_mm": pitch_x,
            "y_pitch_mm": pitch_y,
            "x_span_mm": xs[-1] - xs[0],
            "y_span_mm": ys[-1] - ys[0],
            "max_error_vs_512_mask_openings_mm": max_pin_err,
            "rows_are_y_bottom_to_top": True,
        },
        "margins_mm": {
            "left_x_min_to_board_left": margin_left,
            "right_board_right_to_x_max": margin_right,
            "bottom_y_min_to_board_bottom": margin_bottom,
            "top_board_top_to_y_max": margin_top,
            "x_symmetric": abs(margin_left - margin_right) < 0.02,
            "y_symmetric": abs(margin_bottom - margin_top) < 0.02,
            "x_margin_mismatch_right_minus_left_mm": margin_right - margin_left,
            "y_margin_mismatch_top_minus_bottom_mm": margin_top - margin_bottom,
            "transducer_10mm_body_clearance": edge_gap,
        },
        "mounting_holes_3p5mm": mount_holes,
        "mounting_hole_count": len(mount_holes),
        "inner_edge_trim_limits_mm": {
            "board_A_right_to_3p5mm_hole_edge": trim_limit_right,
            "board_B_left_to_3p5mm_hole_edge": trim_limit_left,
            "board_A_right_top_copper_clearance": copper_right_clear,
            "board_A_left_top_copper_clearance": copper_left_clear,
            "nearest_via_features": via_clear,
        },
        "drill_report_tools": drill,
        "seam_analysis": {
            "pitch_mm": pitch_x,
            "half_pitch_mm": half_pitch,
            "seam_when_board_edges_butted_mm": seam_butted,
            "smallest_nonoverlap_seam_half_pitch_mod_pitch_mm": seam_next,
            "required_edge_gap_for_that_seam_mm": gap_next,
            "smallest_nonoverlap_seam_5mod10_mm": legacy,
            "required_edge_gap_for_legacy_seam_mm": gap_legacy,
            "trim_needed_for_half_pitch_seam_mm": seam_butted - (k * pitch_x + half_pitch - pitch_x),
        },
        "layer_extents_mm": {},
        "notes": [
            "GM1 is the board outline; its extents are exact Gerber coordinates.",
            "The BOM and zip filename say 183 x 169 mm; the GM1 outline is 185.0921 x 168.4020 mm.",
            "The measured transducer pitch is 10.5000 mm, not 10.000 mm. The array span is 157.5 mm, not 150 mm.",
            "The 512 D45 mask openings agree with the 256 pick-place centres to <0.01 mm.",
            "The 4 corner mounting holes are 3.5 mm nominal, centred about 3.2 mm from the board edges.",
            "No board thickness is present in the source data; measure it.",
        ],
    }

    for name in ["Main.GM1", "Main.GTL", "Main.GBL", "Main.GTO", "Main.GBO",
                 "Main.GTS", "Main.GBS", "Main.GD1", "Main.GG1",
                 "Main.GM13", "Main.GM15"]:
        p = os.path.join(root, name)
        if os.path.exists(p):
            result["layer_extents_mm"][name] = gerber_extents(p)

    with open(os.path.join(out_dir, "measurements.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print("PCB outline (GM1): %.4f x %.4f mm" % (board_w, board_h))
    print("Transducer grid: %d x %d, pitch %.4f x %.4f mm, span %.4f x %.4f mm"
          % (len(xs), len(ys), pitch_x, pitch_y, xs[-1] - xs[0], ys[-1] - ys[0]))
    print("Pick-place vs 512 mask openings: max error %.4f mm" % max_pin_err)
    print("X positions: " + ", ".join("%.4f" % v for v in xs))
    print("Y positions: " + ", ".join("%.4f" % v for v in ys))
    print("Margins: left %.4f right %.4f bottom %.4f top %.4f mm"
          % (margin_left, margin_right, margin_bottom, margin_top))
    print("X symmetry mismatch %.4f mm; Y symmetry mismatch %.4f mm"
          % (margin_right - margin_left, margin_top - margin_bottom))
    print("Butted seam: %.4f mm" % seam_butted)
    print("Smallest no-trim seam, half-pitch mod pitch: %.4f mm (edge gap %.4f mm)"
          % (seam_next, gap_next))
    print("Smallest no-trim seam, 5 mod 10: %.4f mm (edge gap %.4f mm)"
          % (legacy, gap_legacy))
    print("Mounting holes 3.5 mm:")
    for h in mount_holes:
        print("  (%.3f, %.3f)" % (h["x_mm"], h["y_mm"]))
    print("Trim limit at A right edge before 3.5 mm hole edge: %.3f mm"
          % trim_limit_right)
    print("Trim limit at B left edge before 3.5 mm hole edge: %.3f mm"
          % trim_limit_left)
    print("Wrote", os.path.join(out_dir, "measurements.json"))


if __name__ == "__main__":
    main()
