#!/usr/bin/env python3
"""Append the 26.11.25 section (board-layout simulation) to the LUIS report.

Creates one heading1 at the end of the page and appends the section body under
it. Images use the three-step flow; HTML files are attached as file cards.

Usage:
    python feishu_add_1125.py --dry-run
    python feishu_add_1125.py
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


def run(content: str, bold: bool = False) -> dict:
    style = {"bold": True} if bold else {}
    return {"text_run": {"content": content, "text_element_style": style}}


def heading(level: int, content: str) -> dict:
    key = {1: "heading1", 2: "heading2", 3: "heading3"}[level]
    return {"block_type": 2 + level, key: {"elements": [run(content, bold=True)]}}


SECTION = [
    ("h1", "26.11.25"),
    ("text", "Ideal-model simulation of the board layouts: 40 kHz, 10.5 mm pitch, "
             "10 mm piston elements, uniform phase. Workspace "
             "E:\\LUIS\\IPP\\sound_wave_sim_figures."),
    ("text", "Read the 50–60° band peak and band energy; the exact 54.75° point "
             "null is a tuning result, not a leak metric."),

    ("h2", "1. Layouts compared"),
    ("image", "figures/comparison.png"),
    ("image", "figures/05_coplanar_gap/farfield.png"),
    ("image", "figures/05_coplanar_gap/nearfield.png"),

    ("h2", "2. Current pair vs butted pair"),
    ("image", "figures/leak_compare.png"),
    ("image", "figures/decomposition.png"),
    ("bullet", "Butted (10.902 mm seam, y 0): band peak −12.7 dB, >60° 0.48 %."),
    ("bullet", "Current (15.75 / 5.25): band peak −14.7 dB, >60° 0.74 %; the "
               "null is ≈2° wide; band energy 23.4 % (butted 24.5 %)."),
    ("bullet", "Without the null requirement, a 16.54 / 5.25 pair gives −15.4 dB."),

    ("h2", "3. Search and 3-board optimum"),
    ("image", "figures/pareto.png"),
    ("image", "figures/study/study2_scan.png"),
    ("image", "figures/study/study3_heatmap.png"),
    ("image", "figures/opt3/farfield.png"),
    ("bullet", "2-board: the current pair is the only one that nulls all four "
               "54.75° lobes; 16.54 / 5.25 is the best without a null."),
    ("bullet", "3-board optimum: seams 12.48 / 17.20 mm, offsets 0 / 5.25 / 0; "
               "DI 40.3 dB, band peak −16.0 dB, band energy 23.8 %, span 502 mm."),
    ("bullet", "It buys +1.8 dB DI and 1.6 dB band peak, not less total band energy."),

    ("h2", "4. Tolerance"),
    ("image", "figures/tolerance.png"),
    ("bullet", "Random phase/gain errors: the null stays below −52 dB at 15° RMS."),
    ("bullet", "Systematic 0.35 % shift in k (≈ ±2 °C): the null lifts to −38 dB."),
    ("bullet", "Mechanical ±1–2 mm: DI unchanged, band peak ±1.4 dB; 1 mm raises "
               "the null to −23 dB. Details in docs/2026-11-23-two-board-sensitivity.md."),

    ("h2", "5. Interactive pages"),
    ("file", "web/overlay.html"),
    ("file", "web/05_coplanar_gap/index.html"),
    ("text", "Open in a browser with internet (three.js CDN). The overlay page "
             "compares any two layouts with independent opacity; each layout page "
             "carries its numbers, a lobe cut and labelled grating lobes."),
]


def image_size(path: Path, max_w: int = 900) -> tuple[int, int]:
    w, h = Image.open(path).size
    width = min(w, max_w)
    return width, round(h * width / w)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.dry_run:
        for kind, payload in SECTION:
            print(f"{kind:7} {payload[:100]}")
        return

    app_id, app_secret = load_credentials()
    token = get_tenant_token(app_id, app_secret)
    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {token}"})

    j = get_json(session, f"/docx/v1/documents/{DOC}/blocks", {"page_size": 500})
    items = check(j, "list blocks")["items"]
    page = next(b for b in items if b["block_id"] == DOC)
    index = len(page.get("children", []))

    r = session.post(
        f"{BASE}/docx/v1/documents/{DOC}/blocks/{DOC}/children",
        json={"children": [heading(1, "26.11.25")], "index": index},
        timeout=60,
    )
    j = r.json()
    if j.get("code") != 0:
        sys.exit(f"create heading failed: {j.get('code')} {j.get('msg')}")
    parent = j["data"]["children"][0]["block_id"]
    print(f"created heading1 26.11.25 at page index {index}: {parent}")
    time.sleep(0.4)

    pos = 0
    for kind, payload in SECTION[1:]:
        if kind == "image":
            r = session.post(
                f"{BASE}/docx/v1/documents/{DOC}/blocks/{parent}/children",
                json={"children": [{"block_type": 27, "image": {}}], "index": pos},
                timeout=60,
            )
            j = r.json()
            if j.get("code") != 0:
                sys.exit(f"create image block failed: {j.get('code')} {j.get('msg')}")
            bid = j["data"]["children"][0]["block_id"]
            path = SIM / payload
            mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
            data = {"file_name": path.name, "parent_type": "docx_image",
                    "parent_node": bid, "size": str(path.stat().st_size)}
            with open(path, "rb") as fh:
                u = session.post(f"{BASE}/drive/v1/medias/upload_all", data=data,
                                 files={"file": (path.name, fh, mime)}, timeout=180)
            uj = u.json()
            if uj.get("code") != 0:
                sys.exit(f"upload {payload} failed: {uj.get('code')} {uj.get('msg')}")
            ft = uj["data"]["file_token"]
            w, h = image_size(path)
            p = session.patch(
                f"{BASE}/docx/v1/documents/{DOC}/blocks/{bid}",
                json={"replace_image": {"token": ft, "width": w, "height": h,
                                        "align": 2}},
                timeout=60,
            )
            pj = p.json()
            if pj.get("code") != 0:
                sys.exit(f"replace_image {payload} failed: {pj.get('code')} {pj.get('msg')}")
            print(f"  image {payload} -> {bid}")
        elif kind == "file":
            r = session.post(
                f"{BASE}/docx/v1/documents/{DOC}/blocks/{parent}/children",
                json={"children": [{"block_type": 23, "file": {"view_type": 1}}],
                      "index": pos},
                timeout=60,
            )
            j = r.json()
            if j.get("code") != 0:
                sys.exit(f"create file block failed: {j.get('code')} {j.get('msg')}")
            child = j["data"]["children"][0]
            bid = child["block_id"]
            if child.get("block_type") == 33:
                kids = child.get("children") or []
                if not kids:
                    jj = get_json(session, f"/docx/v1/documents/{DOC}/blocks",
                                  {"page_size": 500})
                    allb = check(jj, "list for file")["items"]
                    kids = [b["block_id"] for b in allb
                            if b.get("parent_id") == bid and b["block_type"] == 23]
                if not kids:
                    sys.exit("could not resolve file block under view")
                bid = kids[0]
            path = SIM / payload
            data = {"file_name": path.name, "parent_type": "docx_file",
                    "parent_node": bid, "size": str(path.stat().st_size)}
            with open(path, "rb") as fh:
                u = session.post(f"{BASE}/drive/v1/medias/upload_all", data=data,
                                 files={"file": (path.name, fh, "text/html")},
                                 timeout=180)
            uj = u.json()
            if uj.get("code") != 0:
                sys.exit(f"upload {payload} failed: {uj.get('code')} {uj.get('msg')}")
            ft = uj["data"]["file_token"]
            p = session.patch(
                f"{BASE}/docx/v1/documents/{DOC}/blocks/{bid}",
                json={"replace_file": {"token": ft, "name": path.name}},
                timeout=60,
            )
            pj = p.json()
            if pj.get("code") != 0:
                sys.exit(f"replace_file {payload} failed: {pj.get('code')} {pj.get('msg')}")
            print(f"  file {payload} -> {bid}")
        else:
            block = {
                "h2": heading(2, payload),
                "h3": heading(3, payload),
                "text": {"block_type": 2, "text": {"elements": [run(payload)]}},
                "bullet": {"block_type": 12, "bullet": {"elements": [run(payload)]}},
            }[kind]
            r = session.post(
                f"{BASE}/docx/v1/documents/{DOC}/blocks/{parent}/children",
                json={"children": [block], "index": pos},
                timeout=60,
            )
            j = r.json()
            if j.get("code") != 0:
                sys.exit(f"create {kind} failed: {j.get('code')} {j.get('msg')}")
            print(f"  {kind}: {payload[:60]}")
        pos += 1
        time.sleep(0.4)

    j = get_json(session, f"/docx/v1/documents/{DOC}/blocks", {"page_size": 500})
    print(f"done. blocks now: {len(check(j, 'final list')['items'])}")


if __name__ == "__main__":
    main()
