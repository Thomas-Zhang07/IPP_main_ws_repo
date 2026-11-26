#!/usr/bin/env python3
"""Extend 26.12.2 §2 in place: title first, four commands per layout.

Insertion only — nothing is deleted.  For every layout group
(3D 35°, caption, uv 35°, caption, card) we insert

    h3 title, 3D 0/20/60 before the 3D 35° figure,
    uv 0/20/60 before the uv 35° figure,

and rewrite the two captions, so the group reads
title → 0/20/35/60 → uv 0/20/35/60 → card.  The V layout also gets its
35°/45° diagonal uv map.

    python feishu_section2_insert.py --dry-run
    python feishu_section2_insert.py
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
FIG = Path(r"E:\LUIS\IPP\sound_wave_sim_figures\figures")

STUDY = {
    "01_single": "01_single",
    "04_current_pair": "05_coplanar_gap",
    "05_seam_only": "09_pair_seam_only",
    "07_coplanar3": "08_coplanar3",
    "06_concave3": "07_concave3",
    "02_v120": "03_v120",
    "03_v150": "02_v150",
}
SEARCH = {"08_pair_leader": "optimum_2", "09_triple_leader": "optimum_3",
          "10_v135": "optimum_v"}
TITLES = {
    "01_single": "Single board",
    "04_current_pair": "Current pair (as built)",
    "05_seam_only": "Same seam, y = 0",
    "07_coplanar3": "Coplanar 3-board",
    "06_concave3": "Concave 3-board (30°, projected drive)",
    "02_v120": "V 120°",
    "03_v150": "V 150°",
    "08_pair_leader": "Best 2-board (search)",
    "09_triple_leader": "Best 3-board (search)",
    "10_v135": "Best V 135° / y 5.25 mm (search)",
}
ORDER = ["01_single", "04_current_pair", "05_seam_only", "07_coplanar3",
         "06_concave3", "02_v120", "03_v150", "08_pair_leader",
         "09_triple_leader", "10_v135"]


def figures(key: str):
    if key in STUDY:
        base = FIG / "steering" / STUDY[key] / "measured"
        f3 = lambda a: base / "3d" / f"steer_{a:02d}.png"
        fuv = lambda a: base / "uv" / f"steer_{a:02d}.png"
    else:
        base = FIG / "search2" / SEARCH[key]
        f3 = lambda a: base / "3d" / f"steer_{a:02d}_000.png"
        fuv = lambda a: base / "uv" / f"steer_{a:02d}_000.png"
    return [f3(0), f3(20), f3(60)], [fuv(0), fuv(20), fuv(60)]


def run(text: str, bold: bool = False) -> dict:
    return {"text_run": {"content": text,
                         "text_element_style": {"bold": True} if bold else {}}}


def image_size(path: Path, max_w: int = 900) -> tuple[int, int]:
    w, h = Image.open(path).size
    width = min(w, max_w)
    return width, round(h * width / w)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    plan = []
    for key in ORDER:
        extra3, extra_uv = figures(key)
        plan.append((key, extra3, extra_uv))
    if args.dry_run:
        for key, extra3, extra_uv in plan:
            print(f"{key:16s} h3 '{TITLES[key]}'")
            for p in extra3 + extra_uv:
                print("    ", p.name, "" if p.exists() else "MISSING")
            if key == "10_v135":
                p = FIG / "search2/optimum_v/uv/steer_35_045.png"
                print("    ", p.name, "" if p.exists() else "MISSING")
        return

    app_id, app_secret = load_credentials()
    session = requests.Session()
    session.headers.update(
        {"Authorization": f"Bearer {get_tenant_token(app_id, app_secret)}"})

    def list_all():
        items, token = [], None
        while True:
            params = {"page_size": 500}
            if token:
                params["page_token"] = token
            data = check(get_json(
                session, f"/docx/v1/documents/{DOC}/blocks", params), "list")
            items += data["items"]
            token = data.get("page_token")
            if not data.get("has_more"):
                return items

    def text_of(b):
        for k, v in b.items():
            if isinstance(v, dict) and "elements" in v:
                return "".join(e.get("text_run", {}).get("content", "")
                               for e in v["elements"])
        return ""

    blocks = list_all()
    h2 = next(b for b in blocks if b["block_type"] == 4
              and text_of(b) == "2. Layouts, measured vs ideal")
    children = [b for b in blocks if b.get("parent_id") == h2["block_id"]]
    parent = h2["block_id"]
    print(f"§2 has {len(children)} children")
    if len(children) != 51:
        sys.exit("expected 51 children (1 intro + 10 x 5); aborting")

    def create(idx, block, label):
        r = session.post(
            f"{BASE}/docx/v1/documents/{DOC}/blocks/{parent}/children",
            json={"children": [block], "index": idx}, timeout=60)
        j = r.json()
        if j.get("code") != 0:
            sys.exit(f"{label}: {j.get('code')} {j.get('msg')}")
        return j["data"]["children"][0]["block_id"]

    def add_image(idx, path):
        bid = create(idx, {"block_type": 27, "image": {}}, "img")
        data = {"file_name": path.name, "parent_type": "docx_image",
                "parent_node": bid, "size": str(path.stat().st_size)}
        with open(path, "rb") as fh:
            uj = session.post(f"{BASE}/drive/v1/medias/upload_all", data=data,
                              files={"file": (path.name, fh, "image/png")},
                              timeout=180).json()
        if uj.get("code") != 0:
            sys.exit(f"upload {path.name}: {uj.get('code')}")
        w, h = image_size(path)
        pj = session.patch(
            f"{BASE}/docx/v1/documents/{DOC}/blocks/{bid}",
            json={"replace_image": {"token": uj["data"]["file_token"],
                                    "width": w, "height": h, "align": 2}},
            timeout=60).json()
        if pj.get("code") != 0:
            sys.exit(f"replace_image {path.name}: {pj.get('code')}")
        print("    +", path.name)

    # intro line
    intro = children[0]
    pj = session.patch(
        f"{BASE}/docx/v1/documents/{DOC}/blocks/{intro['block_id']}",
        json={"update_text_elements": {"elements": [run(
            "Ten layouts, far field, measured element, at four commands: "
            "0°, 20°, 35°, 60°. Each card opens the interactive page "
            "(0–70° in 5° steps, datasheet/isotropic, 2 m microphone).")]}},
        timeout=60).json()
    print("intro", pj.get("code"))

    # groups of five, processed last -> first so indices stay valid
    for gi in range(len(ORDER) - 1, -1, -1):
        key = ORDER[gi]
        g = 1 + gi * 5
        grp = children[g:g + 5]
        types = [b["block_type"] for b in grp]
        if types != [27, 2, 27, 2, 33]:
            sys.exit(f"unexpected group at {g}: {types}")
        cap3, capuv = grp[1]["block_id"], grp[3]["block_id"]
        extra3, extra_uv = figures(key)
        print(f"  group {key} at {g}")

        create(g, {"block_type": 5, "heading3":
                   {"elements": [run(TITLES[key], True)]}}, "h3")
        # keep 35° in the middle: 0 and 20 before it, 60 after it
        add_image(g + 1, extra3[0])
        add_image(g + 2, extra3[1])
        add_image(g + 4, extra3[2])
        add_image(g + 6, extra_uv[0])
        add_image(g + 7, extra_uv[1])
        add_image(g + 9, extra_uv[2])
        note = ""
        if key == "10_v135":
            add_image(g + 10, FIG / "search2/optimum_v/uv/steer_35_045.png")
            note = ", and the 35°/45° diagonal"
        time.sleep(0.3)
        for bid, text in (
                (cap3, f"{TITLES[key]} — far field, measured element: "
                       "0°, 20°, 35°, 60°"),
                (capuv, f"{TITLES[key]} — uv map: 0°, 20°, 35°, 60°{note}")):
            pj = session.patch(
                f"{BASE}/docx/v1/documents/{DOC}/blocks/{bid}",
                json={"update_text_elements": {"elements": [run(text)]}},
                timeout=60).json()
            if pj.get("code") != 0:
                sys.exit(f"caption {bid}: {pj.get('code')}")
        time.sleep(0.3)

    print("done. §2 children now:",
          len([b for b in list_all() if b.get("parent_id") == parent]))


if __name__ == "__main__":
    main()
