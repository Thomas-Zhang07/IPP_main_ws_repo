#!/usr/bin/env python3
"""Rebuild 26.11.25: individual 3D shots, y-offset section, tables.

Deletes the previous 26.11.25 subtree (created by this project) and recreates
it. Usage: python feishu_rebuild_1125.py [--dry-run]
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import requests
from PIL import Image

from feishu_inspect import BASE, check, get_json, get_tenant_token, load_credentials

DOC = "Fvdld3xEGo0UY9xfKszcxU6HnGc"
SIM = Path(r"E:\LUIS\IPP\sound_wave_sim_figures")

LAYOUT_TABLE = [
    ["Layout", "DI (dB)", "54.75° lobe (dB)", "Band peak (dB)", "Band energy",
     ">60° leak", "Beam x–z", "Elements", "Span"],
    ["Single board", "35.5", "−12.8", "−12.7", "23.8 %", "0.65 %", "3.5°",
     "256", "158 mm (168 PCB)"],
    ["2-board, current", "38.5", "null", "−14.7", "23.4 %", "0.74 %", "1.7°",
     "512", "331 mm (342 PCB)"],
    ["2-board, best without null", "38.5", "−25.4", "−15.4", "23.3 %",
     "0.73 %", "1.7°", "512", "332 mm (342 PCB)"],
    ["3-board optimum", "40.3", "−17.1", "−16.0", "23.8 %", "0.66 %", "1.1°",
     "768", "502 mm (513 PCB)"],
]

LIT_TABLE = [
    ["Work / device", "Elements", "Pitch / span", "Beam / SPL", "Grating / sidelobe"],
    ["This work, 2-board current", "512", "10.5 mm / 331 mm",
     "DI 38.5 dB; 1.7° x; SPL not modelled", "band −14.7 dB; >60° 0.74 %"],
    ["This work, 3-board", "768", "10.5 mm / 502 mm",
     "DI 40.3 dB; 1.1° x; SPL not modelled", "band −16.0 dB; >60° 0.66 %"],
    ["Tang 2023", "200", "12.75 mm mean (1.5λ)", "—",
     "PSLL −18.7 dB @40k; −21.8 dB @30k (measured, 2 m)"],
    ["Allevato 2022", "64", "200 mm spiral",
     "152 dB max; 2.3° resolution; ±80° FoV", "grating-lobe-free (measured)"],
    ["Hirayama 2019", "2 × 256", "10.5 mm", "154.6–158.6 dB at focus",
     "opposed boards"],
    ["Suzuki 2021", "249 / module", "—", "—", "0.1 ms module sync as printed"],
    ["Chen 2024", "—", "—", "—", "4 mm path error degrades focus"],
    ["Shi & Gan 2011", "8 channels", "—", "—",
     "8.3–12.0 dB lobe reduction (steered PAL)"],
]

SHOTS = [
    ("01_single", "Single board"),
    ("02_v150", "V 150°"),
    ("03_v120", "V 120°"),
    ("04_coplanar_butt", "Butted pair"),
    ("05_coplanar_gap", "Current pair"),
    ("09_pair_seam_only", "Same seam, y = 0"),
    ("06_facing", "Facing pair (near field)"),
    ("07_concave3", "Concave 3-board"),
    ("08_coplanar3", "Coplanar 3-board"),
    ("10_butt_offset", "Butted + offset"),
    ("opt3", "Optimal 3-board"),
]


def run(text: str, bold: bool = False) -> dict:
    return {"text_run": {"content": text,
                         "text_element_style": {"bold": True} if bold else {}}}


def heading(level: int, text: str) -> dict:
    key = {1: "heading1", 2: "heading2", 3: "heading3"}[level]
    return {"block_type": 2 + level, key: {"elements": [run(text, True)]}}


def items():
    out = [
        ("h1", "26.11.25", 0),
        ("text", "Ideal-model simulation of the board layouts: 40 kHz, "
                 "10.5 mm pitch, 10 mm piston elements, uniform phase.", 0),
        ("h2", "1. Simulation", 0),
        ("h3", "1.1 All layouts, one by one", 1),
    ]
    for key, label in SHOTS:
        out.append(("image", f"figures/3d_crop/{key}.png", 2))
        out.append(("caption", label, 2))
        out.append(("image", f"figures/{key}/nearfield.png", 2))
    out += [
        ("image", "figures/comparison_left.png", 2),
        ("image", "figures/comparison_right.png", 2),

        ("h3", "1.2 Confirming the 5.25 mm y-offset", 1),
        ("image", "figures/offset_compare.png", 2),
        ("bullet", "Same 15.75 mm seam, y offset 0: the x-axis lobes are "
                   "still nulled by the seam; the y-axis lobes stay at −12.8 dB "
                   "(grey curve sits under the blue one in the x-lobe panel).", 2),
        ("bullet", "Current, y offset 5.25 mm: all four axial lobes are nulled; "
                   "band peak −14.7 dB vs −12.7 dB.", 2),
        ("bullet", "Band energy and >60° leak are unchanged (23.4 %, 0.74 %): "
                   "the offset moves the peak, not the total power.", 2),

        ("h3", "1.3 Search and 3-board optimum", 1),
        ("table", LAYOUT_TABLE, 2),
        ("image", "figures/pareto.png", 2),
        ("image", "figures/study/study2_scan.png", 2),
        ("image", "figures/study/study3_heatmap.png", 2),
        ("image", "figures/opt3/farfield.png", 2),
        ("bullet", "2-board: the current pair is the only one that nulls all "
                   "four 54.75° lobes; 16.54 / 5.25 is the best without a null.", 2),
        ("bullet", "3-board: +1.8 dB DI, 1.3 dB lower band peak, band energy "
                   "+0.4 pp, 502 mm span.", 2),

        ("h3", "1.4 Tolerance", 1),
        ("image", "figures/tolerance.png", 2),
        ("bullet", "Random phase/gain errors: null median ≈ −51 dB at 15° RMS.", 2),
        ("bullet", "Systematic 0.1 % shift in k (≈ ±0.6 °C) lifts the null to "
                   "−38 dB; 0.35 % (≈ ±2 °C) to about −28 dB.", 2),
        ("bullet", "Mechanical ±2 mm: band peak −13.3…−15.2 dB; ±1 mm raises "
                   "the null to −23 dB.", 2),

        ("h3", "1.5 Interactive pages", 1),
        ("text", "Source: E:\\LUIS\\IPP\\sound_wave_sim_figures.", 2),
        ("file", "web/overlay.html", 2),
        ("file", "web/05_coplanar_gap/index.html", 2),

        ("h2", "2. Literature context", 0),
        ("text", "Verified citations (24 DOIs) in "
                 "docs/2026-11-24-literature-review.md and docs/references.bib.", 1),
        ("table", LIT_TABLE, 1),
        ("text", "Aim: DI ≥ 38 dB measured, band peak ≤ −15 dB with the current "
                 "boards, audio 70–80 dB at 1–2 m. A −18 dB band peak needs an "
                 "aperiodic PCB, not a fixture change. Published numbers marked "
                 "here are from abstracts; check them in the PDFs.", 1),
    ]
    return out


def image_size(path: Path, max_w: int = 900) -> tuple[int, int]:
    w, h = Image.open(path).size
    width = min(w, max_w)
    return width, round(h * width / w)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    seq = items()
    if args.dry_run:
        for kind, payload, level in seq:
            label = payload if isinstance(payload, str) else f"table {len(payload)}x{len(payload[0])}"
            print(f"{kind:8} L{level} {label[:80]}")
        return

    app_id, app_secret = load_credentials()
    session = requests.Session()
    session.headers.update(
        {"Authorization": f"Bearer {get_tenant_token(app_id, app_secret)}"})

    j = get_json(session, f"/docx/v1/documents/{DOC}/blocks", {"page_size": 500})
    items_ = check(j, "list")["items"]
    by = {b["block_id"]: b for b in items_}
    page = by[DOC]
    old_index = None
    for idx, cid in enumerate(page.get("children", [])):
        b = by[cid]
        if b["block_type"] == 3:
            txt = "".join(e.get("text_run", {}).get("content", "")
                          for e in b.get("heading1", {}).get("elements", []))
            if txt.strip() == "26.11.25":
                old_index = idx
                break
    if old_index is None:
        sys.exit("26.11.25 not found")
    print("deleting old section at", old_index)
    r = session.delete(
        f"{BASE}/docx/v1/documents/{DOC}/blocks/{DOC}/children/batch_delete",
        json={"start_index": old_index, "end_index": old_index + 1}, timeout=60)
    j = r.json()
    if j.get("code") != 0:
        sys.exit(f"delete: {j.get('code')} {j.get('msg')}")
    time.sleep(0.5)

    j = get_json(session, f"/docx/v1/documents/{DOC}/blocks", {"page_size": 500})
    items_ = check(j, "list2")["items"]
    by = {b["block_id"]: b for b in items_}
    index = len(by[DOC].get("children", []))
    r = session.post(f"{BASE}/docx/v1/documents/{DOC}/blocks/{DOC}/children",
                     json={"children": [heading(1, "26.11.25")],
                           "index": index}, timeout=60)
    j = r.json()
    if j.get("code") != 0:
        sys.exit("heading failed")
    ids = {0: j["data"]["children"][0]["block_id"]}
    counts = {ids[0]: 0}
    print("heading1", ids[0])
    time.sleep(0.4)

    def create(parent, pos, block, label):
        r = session.post(
            f"{BASE}/docx/v1/documents/{DOC}/blocks/{parent}/children",
            json={"children": [block], "index": pos}, timeout=60)
        j = r.json()
        if j.get("code") != 0:
            sys.exit(f"{label}: {j.get('code')} {j.get('msg')}")
        return j["data"]["children"][0]["block_id"]

    for kind, payload, level in seq[1:]:
        parent = ids[level] if level > 0 else ids[0]
        pos = counts.get(parent, 0)
        if kind in ("h2", "h3"):
            hl = 2 if kind == "h2" else 3
            bid = create(parent, pos, heading(hl, payload), kind)
            ids[hl - 1] = bid
            counts[bid] = 0
            for deeper in list(ids):
                if deeper > hl - 1:
                    del ids[deeper]
            print(f"  {kind} {payload} -> {bid}")
        elif kind == "image":
            bid = create(parent, pos, {"block_type": 27, "image": {}}, "img")
            path = SIM / payload
            mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
            data = {"file_name": path.name, "parent_type": "docx_image",
                    "parent_node": bid, "size": str(path.stat().st_size)}
            with open(path, "rb") as fh:
                uj = session.post(f"{BASE}/drive/v1/medias/upload_all", data=data,
                                  files={"file": (path.name, fh, mime)},
                                  timeout=180).json()
            if uj.get("code") != 0:
                sys.exit(f"upload {payload}: {uj.get('code')} {uj.get('msg')}")
            w, h = image_size(path)
            pj = session.patch(
                f"{BASE}/docx/v1/documents/{DOC}/blocks/{bid}",
                json={"replace_image": {"token": uj["data"]["file_token"],
                                        "width": w, "height": h, "align": 2}},
                timeout=60).json()
            if pj.get("code") != 0:
                sys.exit(f"replace_image {payload}: {pj.get('code')}")
            print(f"  image {payload}")
        elif kind == "table":
            rows = payload
            R, C = len(rows), len(rows[0])
            bid = create(parent, pos,
                         {"block_type": 31,
                          "table": {"property": {"row_size": R,
                                                 "column_size": C}}}, "table")
            jj = get_json(session, f"/docx/v1/documents/{DOC}/blocks",
                          {"page_size": 500})
            allb = check(jj, "cells")["items"]
            tb = next(b for b in allb if b["block_id"] == bid)
            cells = tb.get("children", []) or [
                b["block_id"] for b in allb if b.get("parent_id") == bid]
            if len(cells) != R * C:
                sys.exit(f"table cells {len(cells)} != {R*C}")
            for i, cell in enumerate(cells):
                text = rows[i // C][i % C]
                create(cell, 0, {"block_type": 2,
                                 "text": {"elements": [run(text, bold=(i < C))]}},
                       "cell")
                time.sleep(0.15)
            print(f"  table {R}x{C} -> {bid}")
        elif kind == "file":
            child = session.post(
                f"{BASE}/docx/v1/documents/{DOC}/blocks/{parent}/children",
                json={"children": [{"block_type": 23,
                                    "file": {"view_type": 1}}],
                      "index": pos}, timeout=60).json()
            if child.get("code") != 0:
                sys.exit("file block failed")
            cb = child["data"]["children"][0]
            bid = cb["block_id"]
            if cb.get("block_type") == 33:
                kids = cb.get("children") or []
                if not kids:
                    jj = get_json(session, f"/docx/v1/documents/{DOC}/blocks",
                                  {"page_size": 500})
                    allb = check(jj, "filekids")["items"]
                    kids = [b["block_id"] for b in allb
                            if b.get("parent_id") == bid and b["block_type"] == 23]
                bid = kids[0]
            path = SIM / payload
            data = {"file_name": path.name, "parent_type": "docx_file",
                    "parent_node": bid, "size": str(path.stat().st_size)}
            with open(path, "rb") as fh:
                uj = session.post(f"{BASE}/drive/v1/medias/upload_all", data=data,
                                  files={"file": (path.name, fh, "text/html")},
                                  timeout=180).json()
            if uj.get("code") != 0:
                sys.exit(f"upload file: {uj.get('code')}")
            pj = session.patch(
                f"{BASE}/docx/v1/documents/{DOC}/blocks/{bid}",
                json={"replace_file": {"token": uj["data"]["file_token"],
                                       "name": path.name}}, timeout=60).json()
            if pj.get("code") != 0:
                sys.exit(f"replace_file: {pj.get('code')}")
            print(f"  file {payload}")
        else:
            if kind == "caption":
                block = {"block_type": 2,
                         "text": {"elements": [run(payload)]}}
                block["text"]["style"] = {"align": 2}
            else:
                block = {"block_type": 2, "text": {"elements": [run(payload)]}}
            create(parent, pos, block, kind)
            print(f"  {kind} {payload[:50]}")
        counts[parent] = pos + 1
        time.sleep(0.35)

    j = get_json(session, f"/docx/v1/documents/{DOC}/blocks", {"page_size": 500})
    print("done. blocks", len(check(j, "final")["items"]))


if __name__ == "__main__":
    main()
