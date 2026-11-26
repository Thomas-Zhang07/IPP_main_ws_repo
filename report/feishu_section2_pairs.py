#!/usr/bin/env python3
"""Rebuild 26.12.2 §2 with per-command pairs: 3D and uv at the same angle.

Builds a fresh "2. Layouts, measured vs ideal" heading inserted in front of
the existing one, so nothing is lost if the build fails; the old heading is
removed afterwards with `--drop-old`.

    python feishu_section2_pairs.py --dry-run
    python feishu_section2_pairs.py --build
    python feishu_section2_pairs.py --drop-old
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
TITLE = "2. Layouts, measured vs ideal"
ROOT = "ZNyHdUaAdonejVxoiiNc9hsBngf"
FIG = Path(r"E:\LUIS\IPP\sound_wave_sim_figures\figures")
ASSETS = Path(r"E:\LUIS\IPP\report\assets\11.26\3d")

STUDY = {"01_single": "01_single", "04_current_pair": "05_coplanar_gap",
         "05_seam_only": "09_pair_seam_only", "07_coplanar3": "08_coplanar3",
         "06_concave3": "07_concave3", "02_v120": "03_v120",
         "03_v150": "02_v150"}
SEARCH = {"08_pair_leader": "optimum_2", "09_triple_leader": "optimum_3",
          "10_v135": "optimum_v"}
TITLES = {"01_single": "Single board",
          "04_current_pair": "Current pair (as built)",
          "05_seam_only": "Same seam, y = 0",
          "07_coplanar3": "Coplanar 3-board",
          "06_concave3": "Concave 3-board (30°, projected drive)",
          "02_v120": "V 120°", "03_v150": "V 150°",
          "08_pair_leader": "Best 2-board (search)",
          "09_triple_leader": "Best 3-board (search)",
          "10_v135": "Best V 135° / y 5.25 mm (search)"}
ORDER = list(TITLES)
ANGLES = (0, 20, 35, 60)


def figs(key):
    if key in STUDY:
        base = FIG / "steering" / STUDY[key] / "measured"
        return (lambda a: base / "3d" / f"steer_{a:02d}.png",
                lambda a: base / "uv" / f"steer_{a:02d}.png",
                lambda a: base / "amplitude" / f"steer_{a:02d}.png")
    base = FIG / "search2" / SEARCH[key]
    return (lambda a: base / "3d" / f"steer_{a:02d}_000.png",
            lambda a: base / "uv" / f"steer_{a:02d}_000.png",
            lambda a: base / "amplitude" / f"steer_{a:02d}_000.png")


def run(text, bold=False):
    return {"text_run": {"content": text,
                         "text_element_style": {"bold": True} if bold else {}}}


def image_size(path, max_w=900):
    w, h = Image.open(path).size
    width = min(w, max_w)
    return width, round(h * width / w)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--drop-old", action="store_true")
    args = ap.parse_args()

    if args.dry_run:
        total = 0
        for key in ORDER:
            f3, fuv, famp = figs(key)
            paths = [p for a in ANGLES for p in (f3(a), fuv(a), famp(a))]
            if key == "10_v135":
                paths.append(FIG / "search2/optimum_v/uv/steer_35_045.png")
            missing = [str(p) for p in paths if not p.exists()]
            print(f"{key:16s} {len(paths)} figures"
                  + ("  MISSING " + ", ".join(missing) if missing else ""))
            total += len(paths)
        print("total figures", total, "blocks", total + 10 * 3 + 1)
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
    root = next(b for b in blocks if b["block_id"] == ROOT)
    root_kids = [b for b in blocks if b.get("parent_id") == ROOT]
    olds = [b for b in root_kids if b["block_type"] == 4
            and text_of(b) == TITLE]
    if args.drop_old:
        if len(olds) != 2:
            sys.exit(f"expected two '{TITLE}' headings, found {len(olds)}")
        old_index = root_kids.index(olds[-1])
        n = len([b for b in blocks if b.get("parent_id") == olds[-1]["block_id"]])
        print(f"deleting old heading {olds[-1]['block_id']} at index "
              f"{old_index} with {n} children")
        r = session.delete(
            f"{BASE}/docx/v1/documents/{DOC}/blocks/{ROOT}/children/"
            f"batch_delete",
            json={"start_index": old_index, "end_index": old_index + 1},
            timeout=60).json()
        print("code", r.get("code"), r.get("msg"))
        return
    if not args.build:
        sys.exit("pass --build or --drop-old (or --dry-run)")
    if len(olds) != 1:
        sys.exit(f"expected exactly one existing '{TITLE}', found {len(olds)}")

    index = 1
    for i, b in enumerate(root_kids):
        if b["block_type"] == 4 and text_of(b) == TITLE:
            index = i

    r = session.post(
        f"{BASE}/docx/v1/documents/{DOC}/blocks/{ROOT}/children",
        json={"children": [{"block_type": 4, "heading2":
                            {"elements": [run(TITLE, True)]}}],
              "index": index}, timeout=60).json()
    if r.get("code") != 0:
        sys.exit(f"heading: {r.get('code')} {r.get('msg')}")
    parent = r["data"]["children"][0]["block_id"]
    print("new heading", parent, "at", index)
    pos = 0

    def create(idx, block, label):
        rr = session.post(
            f"{BASE}/docx/v1/documents/{DOC}/blocks/{parent}/children",
            json={"children": [block], "index": idx}, timeout=60)
        jj = rr.json()
        if jj.get("code") != 0:
            sys.exit(f"{label}: {jj.get('code')} {jj.get('msg')}")
        return jj["data"]["children"][0]["block_id"]

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

    intro = ("Ten layouts, measured element. Each command leads with the "
             "amplitude cut through the steering plane, then the 3D pattern "
             "and its uv map. The card at the end opens the interactive page "
             "(0–70° in 5° steps, datasheet/isotropic, 2 m microphone).")
    create(pos, {"block_type": 2, "text": {"elements": [run(intro)]}}, "intro")
    pos += 1

    for key in ORDER:
        create(pos, {"block_type": 5, "heading3":
                     {"elements": [run(TITLES[key], True)]}}, "h3")
        pos += 1
        f3, fuv, famp = figs(key)
        for angle in ANGLES:
            add_image(pos, famp(angle))
            add_image(pos + 1, f3(angle))
            add_image(pos + 2, fuv(angle))
            pos += 3
            print(f"  {key} {angle}° triplet (amp first)")
            time.sleep(0.25)
        if key == "10_v135":
            add_image(pos, FIG / "search2/optimum_v/uv/steer_35_045.png")
            pos += 1
            print(f"  {key} 35/45 diagonal")
        note = "amplitude cut, 3D pattern and uv map at 0°, 20°, 35°, 60°"
        if key == "10_v135":
            note += ", plus the 35°/45° diagonal uv map"
        create(pos, {"block_type": 2, "text": {
            "elements": [run(f"{TITLES[key]} — {note}, measured element.")],
            "style": {"align": 2}}}, "caption")
        pos += 1
        # card
        child = session.post(
            f"{BASE}/docx/v1/documents/{DOC}/blocks/{parent}/children",
            json={"children": [{"block_type": 23, "file": {"view_type": 1}}],
                  "index": pos}, timeout=60).json()
        if child.get("code") != 0:
            sys.exit(f"file block: {child.get('code')}")
        cb = child["data"]["children"][0]
        fid = cb["block_id"]
        if cb.get("block_type") == 33:
            ids = cb.get("children") or []
            if not ids:
                ids = [b["block_id"] for b in list_all()
                       if b.get("parent_id") == fid and b["block_type"] == 23]
            fid = ids[0]
        path = ASSETS / f"{key}.html"
        data = {"file_name": path.name, "parent_type": "docx_file",
                "parent_node": fid, "size": str(path.stat().st_size)}
        with open(path, "rb") as fh:
            uj = session.post(f"{BASE}/drive/v1/medias/upload_all", data=data,
                              files={"file": (path.name, fh, "text/html")},
                              timeout=180).json()
        if uj.get("code") != 0:
            sys.exit(f"upload {path.name}: {uj.get('code')}")
        pj = session.patch(
            f"{BASE}/docx/v1/documents/{DOC}/blocks/{fid}",
            json={"replace_file": {"token": uj["data"]["file_token"],
                                   "name": path.name}}, timeout=60).json()
        if pj.get("code") != 0:
            sys.exit(f"replace_file {path.name}: {pj.get('code')}")
        pos += 1
        print("  card", path.name)
        time.sleep(0.3)

    print("done. new §2 blocks:", pos)


if __name__ == "__main__":
    main()
