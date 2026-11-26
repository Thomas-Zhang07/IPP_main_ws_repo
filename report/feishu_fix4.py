#!/usr/bin/env python3
"""Repair 26.12.2: re-parent §4.2–4.6 under "4. Optimal search" and tidy cells.

The first insert nested each h3 under the previous h3, and table cells were
filled by adding a paragraph instead of replacing the default empty one.
This script deletes the bad §4.2 chain, rebuilds §4.2–4.6 as siblings, and
rewrites the three remaining tables cell by cell.

    python feishu_fix4.py --dry-run
    python feishu_fix4.py
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
FIG = SIM / "figures"

T_ROBUST = [
    ["Candidate", "4-bit phase", "Mechanical", "k drift", "Element", "Worst"],
    ["3-board triple", "−0.94", "−0.14", "−0.68", "+0.21 dB", "−0.14 dB"],
    ["2-board pair", "+0.39", "+0.75", "+0.30", "+1.41 dB", "+1.41 dB"],
    ["V 135°", "not run", "not run", "not run", "+0.35 dB", "+0.35 dB"],
]
T_WINNERS = [
    ["Rank", "Layout", "Boards", "Span", "SL_cmd", "SL_diag", "SRANGE₀", "DI0"],
    ["1", "triple 18.50 / 14.75 / 10.50 / 5.25", "3", "506 mm",
     "−0.46", "−0.86", "35°", "41.4 dB"],
    ["2", "pair 16.00 / 5.25", "2", "331 mm", "+0.31", "−0.18", "34°", "39.7 dB"],
    ["3", "V 135° / y 5.25 mm", "2", "301 mm", "−0.30", "−0.61", "31°", "36.6 dB"],
]

SEQUENCE = [
    ("h3", "4.2 Two-board front"),
    ("img", FIG / "search2/front_2.png",
     "Pareto front: worst sidelobe against contiguous 0 dB range."),
    ("img", FIG / "search2/leader_2.png",
     "Leader curves across all 57 steering states."),
    ("img", FIG / "search2/trade_2.png",
     "Trade between the axial null and the diagonal level."),
    ("h3", "4.3 Three-board front"),
    ("img", FIG / "search2/front_3.png",
     "Three boards: gain and range improve, worst sidelobe does not."),
    ("img", FIG / "search2/leader_3.png",
     "3-board leader, 57 states."),
    ("img", FIG / "search2/trade_3.png",
     "3-board trade-off."),
    ("h3", "4.4 V pairs"),
    ("img", FIG / "search2/front_v.png",
     "Included angle 60–180° with and without the 5.25 mm hinge offset."),
    ("img", FIG / "search2/optimum_v/3d/steer_35_000.png",
     "V 135° / y 5.25 mm at 35°."),
    ("img", FIG / "search2/optimum_v/uv/steer_35_045.png",
     "Same layout on the diagonal, 35° / 45°."),
    ("img", FIG / "search2/optimum_v/amplitude/steer_35_000.png",
     "Amplitude cut, measured vs isotropic."),
    ("h3", "4.5 Robustness"),
    ("table", T_ROBUST),
    ("h3", "4.6 Winners"),
    ("img", FIG / "report/winners.png",
     "All three families on the same metrics; circles mark the picks."),
    ("table", T_WINNERS),
    ("bullet", "Recommendation: the 3-board triple if three boards are "
               "allowed — best on every rubric and the only one whose "
               "robustness moves nothing by more than 1 dB."),
    ("bullet", "Two boards: the coplanar pair for range and gain, the V "
               "for a 0.6 dB lower worst sidelobe and a flatter element "
               "envelope, at 3 dB and 3° of range."),
]


def run(text: str, bold: bool = False) -> dict:
    return {"text_run": {"content": text,
                         "text_element_style": {"bold": True} if bold else {}}}


def heading(level: int, text: str) -> dict:
    key = {2: "heading2", 3: "heading3"}[level]
    return {"block_type": level + 2, key: {"elements": [run(text, True)]}}


def image_size(path: Path, max_w: int = 900) -> tuple[int, int]:
    w, h = Image.open(path).size
    width = min(w, max_w)
    return width, round(h * width / w)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skip-rebuild", action="store_true")
    ap.add_argument("--rebuild-only", action="store_true")
    args = ap.parse_args()

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
    print("debug blocks", len(blocks))
    kids = lambda pid: [b for b in blocks if b.get("parent_id") == pid]
    h2 = next(b for b in blocks if b["block_type"] == 4
              and text_of(b) == "4. Optimal search")
    h41 = next(b for b in blocks if b["block_type"] == 5
               and text_of(b) == "4.1 Rubrics")
    children = kids(h41["block_id"])
    bad = [c for c in children if c["block_type"] == 5]
    print("h2", h2["block_id"], "4.1 children", len(children),
          "bad h3 chain", [text_of(c) for c in bad])
    if args.dry_run:
        for kind, *rest in SEQUENCE:
            print(f"{kind:7s} {str(rest[0])[:70]}")
        return

    # 1. delete the nested 4.2 chain (cascade)
    if args.rebuild_only or not bad:
        start = None
    else:
        start = children.index(bad[0])
    if start is not None:
        r = session.delete(
            f"{BASE}/docx/v1/documents/{DOC}/blocks/{h41['block_id']}"
            "/children/batch_delete",
            json={"start_index": start, "end_index": len(children)},
            timeout=60)
        j = r.json()
        if j.get("code") != 0:
            sys.exit(f"delete chain: {j.get('code')} {j.get('msg')}")
        print("deleted", len(children) - start, "blocks from 4.1")
        time.sleep(0.6)

    def create(parent, pos, block, label):
        r = session.post(
            f"{BASE}/docx/v1/documents/{DOC}/blocks/{parent}/children",
            json={"children": [block], "index": pos}, timeout=60)
        j = r.json()
        if j.get("code") != 0:
            sys.exit(f"{label}: {j.get('code')} {j.get('msg')}")
        return j["data"]["children"][0]["block_id"]

    def add_image(parent, pos, path, caption):
        bid = create(parent, pos, {"block_type": 27, "image": {}}, "img")
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
        create(parent, pos + 1,
               {"block_type": 2, "text": {"elements": [run(caption)],
                                          "style": {"align": 2}}}, "caption")
        print("  img", path.name)

    def add_table(parent, pos, rows):
        R, C = len(rows), len(rows[0])
        bid = create(parent, pos,
                     {"block_type": 31,
                      "table": {"property": {"row_size": R,
                                             "column_size": C}}}, "table")
        time.sleep(0.4)
        allb = list_all()
        tb = next(b for b in allb if b["block_id"] == bid)
        cells = tb.get("children") or [
            b["block_id"] for b in allb if b.get("parent_id") == bid]
        if len(cells) != R * C:
            sys.exit(f"cells {len(cells)} != {R * C}")
        for i, cell in enumerate(cells):
            label = rows[i // C][i % C]
            ck = [b for b in allb if b.get("parent_id") == cell]
            if ck:
                pj = session.patch(
                    f"{BASE}/docx/v1/documents/{DOC}/blocks/{ck[0]['block_id']}",
                    json={"update_text_elements":
                          {"elements": [run(label, bold=(i < C))]}},
                    timeout=60).json()
                if pj.get("code") != 0:
                    sys.exit(f"cell patch: {pj.get('code')}")
            else:
                create(cell, 0, {"block_type": 2,
                                 "text": {"elements": [run(label,
                                                           bold=(i < C))]}},
                       "cell")
            time.sleep(0.1)
        print(f"  table {R}x{C} -> {bid}")
        return bid

    if not args.skip_rebuild:
        pos = len(kids(h2["block_id"]))
        cur, cpos = h2["block_id"], pos
        for kind, *rest in SEQUENCE:
            if kind == "h3":
                hid = create(h2["block_id"], pos, heading(3, rest[0]), "h3")
                pos += 1
                cur, cpos = hid, 0
                print("  h3", rest[0])
            elif kind == "img":
                add_image(cur, cpos, rest[0], rest[1])
                cpos += 2
            elif kind == "table":
                add_table(cur, cpos, rest[0])
                cpos += 1
            else:
                block = {"block_type": 12, "bullet":
                         {"elements": [run(rest[0])]}}
                create(cur, cpos, block, kind)
                cpos += 1
                print("  bullet", rest[0][:40])
            time.sleep(0.4)

    # 3. rewrite the three surviving tables in place
    blocks = list_all()
    targets = []
    for b in blocks:
        if b["block_type"] != 31:
            continue
        prop = (b.get("table") or {}).get("property") or {}
        parent_text = text_of(next((p for p in blocks
                                    if p["block_id"] == b.get("parent_id")),
                                   {}))
        if parent_text in ("1. Measured transducer", "4.1 Rubrics",
                           "5. Microphone at 2 m"):
            targets.append(b)
    print("tables to tidy:", len(targets))
    for tbl in targets:
        cells = tbl.get("children") or [
            b["block_id"] for b in blocks if b.get("parent_id") == tbl["block_id"]]
        changed = 0
        for cell in cells:
            ck = [b for b in blocks if b.get("parent_id") == cell]
            if len(ck) >= 2:
                body = text_of(ck[-1])
                pj = session.patch(
                    f"{BASE}/docx/v1/documents/{DOC}/blocks/{ck[0]['block_id']}",
                    json={"update_text_elements": {"elements": [run(body)]}},
                    timeout=60).json()
                if pj.get("code") != 0:
                    sys.exit(f"tidy patch: {pj.get('code')}")
                r = session.delete(
                    f"{BASE}/docx/v1/documents/{DOC}/blocks/{cell}/children/"
                    "batch_delete",
                    json={"start_index": 1, "end_index": len(ck)},
                    timeout=60).json()
                if r.get("code") != 0:
                    sys.exit(f"tidy delete: {r.get('code')}")
                changed += 1
                time.sleep(0.18)
        print(f"  tidied {tbl['block_id']}: {changed} cells")
        time.sleep(0.3)

    print("done. total blocks", len(list_all()))


if __name__ == "__main__":
    main()
