#!/usr/bin/env python3
"""Build 26.12.2 "Acoustic array workbench" in the LUIS report.

Additive only: appends headings, figures, tables and per-setup HTML cards
under the existing heading1 block.  Nothing outside that heading is touched.

    python feishu_workbench_1126.py --dry-run
    python feishu_workbench_1126.py
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
HEADING = "26.12.2"
SIM = Path(r"E:\LUIS\IPP\sound_wave_sim_figures")
ASSETS = Path(r"E:\LUIS\IPP\report\assets\11.26")


# ------------------------------------------------------------------ content

def fig(*parts: str) -> Path:
    return SIM.joinpath("figures", *parts)


LAYOUTS = [
    ("01_single", "Single board",
     fig("steering/01_single/measured/3d/steer_35.png"),
     fig("steering/01_single/measured/uv/steer_35.png")),
    ("04_current_pair", "Current pair (as built)",
     fig("steering/05_coplanar_gap/measured/3d/steer_35.png"),
     fig("steering/05_coplanar_gap/measured/uv/steer_35.png")),
    ("05_seam_only", "Same seam, y = 0",
     fig("steering/09_pair_seam_only/measured/3d/steer_35.png"),
     fig("steering/09_pair_seam_only/measured/uv/steer_35.png")),
    ("07_coplanar3", "Coplanar 3-board",
     fig("steering/08_coplanar3/measured/3d/steer_35.png"),
     fig("steering/08_coplanar3/measured/uv/steer_35.png")),
    ("06_concave3", "Concave 3-board (30°, projected drive)",
     fig("steering/07_concave3/measured/3d/steer_35.png"),
     fig("steering/07_concave3/measured/uv/steer_35.png")),
    ("02_v120", "V 120°",
     fig("steering/03_v120/measured/3d/steer_35.png"),
     fig("steering/03_v120/measured/uv/steer_35.png")),
    ("03_v150", "V 150°",
     fig("steering/02_v150/measured/3d/steer_35.png"),
     fig("steering/02_v150/measured/uv/steer_35.png")),
    ("08_pair_leader", "Best 2-board (search)",
     fig("search2/optimum_2/3d/steer_35_000.png"),
     fig("search2/optimum_2/uv/steer_35_000.png")),
    ("09_triple_leader", "Best 3-board (search)",
     fig("search2/optimum_3/3d/steer_35_000.png"),
     fig("search2/optimum_3/uv/steer_35_000.png")),
    ("10_v135", "Best V 135° / y 5.25 mm (search)",
     fig("search2/optimum_v/3d/steer_35_000.png"),
     fig("search2/optimum_v/uv/steer_35_045.png")),
]

T_ELEMENT = [
    ["Quantity", "Measured value"],
    ["Directivity index", "11.2 dB (Q ≈ 13.1)"],
    ["−6 dB beamwidth", "81° (42° left, 39° right)"],
    ["Side lobes", "≈ −21 dB"],
    ["Rear radiation", "≈ −36 dB"],
    ["Level at the 54.75° grating angle", "−28.2 dB"],
]

T_RUBRIC = [
    ["Rubric", "Worst case over"],
    ["SL_cmd", "every sample outside the 4° main-lobe cone"],
    ["SL_diag", "the four diagonal azimuths (45/135/225/315°)"],
    ["SL_clean", "steering up to 24.1°, below grating takeover"],
    ["SRANGE₀", "largest contiguous 0 dB range, 1° steps"],
    ["DI0", "on-axis directivity, forward hemisphere"],
    ["Robustness", "4-bit phase, placement error, k drift, element variants"],
]

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

T_MIC = [
    ["Layout", "Level at 2 m, re coherent bound", "Emitter path spread"],
    ["V 120°", "−7.65 dB", "6.8 mm"],
    ["V 150°", "−10.47 dB", "7.9 mm"],
]


def items() -> list[tuple]:
    seq: list[tuple] = [
        ("text", "Measured element, every layout, steering with and without "
                 "the transducer pattern, the optimal search and V shapes. "
                 "40 kHz, 10.5 mm pitch. The measured element numbers here "
                 "supersede the ideal-piston figures in 26.11.25 §1."),

        ("h2", "1. Measured transducer"),
        ("img", fig("report/element_pattern.png"),
         "Digitized from the datasheet polar chart: 81° at −6 dB, side lobes "
         "−21 dB, rear −36 dB. The ideal 10 mm piston is narrower."),
        ("img", SIM / "sim/transducer/overlay.png",
         "Digitization check: the traced curve over the photographed chart."),
        ("table", T_ELEMENT),

        ("h2", "2. Layouts, measured vs ideal"),
        ("text", "Each layout: 35° steer with the measured element, then its "
                 "uv map. The file card opens the interactive 3D page "
                 "(0–70°, all five degrees, measured/isotropic, far field/2 m)."),
    ]
    for key, label, p3d, puv in LAYOUTS:
        seq += [("img", p3d, label + " — far field at 35°, measured element"),
                ("img", puv, label + " — uv map at 35°"),
                ("card", ASSETS / "3d" / f"{key}.html")]

    seq += [
        ("h2", "3. Steering, with and without the element"),
        ("img", fig("steering/summary_all/all_main_direction.png"),
         "Main-lobe direction against command, all seven study layouts."),
        ("img", fig("steering/summary_all/all_main_level.png"),
         "Main-lobe level: the measured element costs 1–3 dB off broadside."),
        ("img", fig("steering/summary_all/all_sidelobe_level.png"),
         "Worst sidelobe: flat layouts sit ~20 dB below the main lobe."),
        ("img", fig("steering/summary_all/all_sidelobe_minus_main.png"),
         "Sidelobe relative to the main lobe — the number the search minimises."),
        ("img", fig("steering/05_coplanar_gap/measured/amplitude/steer_35.png"),
         "Current pair, measured element, 35°."),
        ("img", fig("steering/05_coplanar_gap/isotropic/amplitude/steer_35.png"),
         "Same command, isotropic control."),
        ("img", fig("steering/03_v120/measured/uv/steer_35.png"),
         "V 120°, measured uv map."),
        ("img", fig("steering/03_v120/isotropic/uv/steer_35.png"),
         "V 120°, isotropic uv map: the measured element trims the grating ring."),
        ("img", fig("steering/02_v150/isotropic/3d/steer_35.png"),
         "V 150° without the element pattern, for comparison with §2."),
        ("img", fig("steering/08_coplanar3/measured/amplitude/steer_35.png"),
         "Coplanar 3-board, measured, 35°."),
        ("img", fig("steering/08_coplanar3/isotropic/amplitude/steer_35.png"),
         "Coplanar 3-board, isotropic."),

        ("h2", "4. Optimal search"),
        ("h3", "4.1 Rubrics"),
        ("table", T_RUBRIC),
        ("h3", "4.2 Two-board front"),
        ("img", fig("search2/front_2.png"),
         "Pareto front: worst sidelobe against contiguous 0 dB range."),
        ("img", fig("search2/leader_2.png"),
         "Leader curves across all 57 steering states."),
        ("img", fig("search2/trade_2.png"),
         "Trade between the axial null and the diagonal level."),
        ("h3", "4.3 Three-board front"),
        ("img", fig("search2/front_3.png"),
         "Three boards: gain and range improve, worst sidelobe does not."),
        ("img", fig("search2/leader_3.png"),
         "3-board leader, 57 states."),
        ("img", fig("search2/trade_3.png"),
         "3-board trade-off."),
        ("h3", "4.4 V pairs"),
        ("img", fig("search2/front_v.png"),
         "Included angle 60–180° with and without the 5.25 mm hinge offset."),
        ("img", fig("search2/optimum_v/3d/steer_35_000.png"),
         "V 135° / y 5.25 mm at 35°."),
        ("img", fig("search2/optimum_v/uv/steer_35_045.png"),
         "Same layout on the diagonal, 35° / 45°."),
        ("img", fig("search2/optimum_v/amplitude/steer_35_000.png"),
         "Amplitude cut, measured vs isotropic."),
        ("h3", "4.5 Robustness"),
        ("table", T_ROBUST),
        ("h3", "4.6 Winners"),
        ("img", fig("report/winners.png"),
         "All three families on the same metrics; circles mark the picks."),
        ("table", T_WINNERS),
        ("bullet", "Recommendation: the 3-board triple if three boards are "
                   "allowed — best on every rubric and the only one whose "
                   "robustness moves nothing by more than 1 dB."),
        ("bullet", "Two boards: the coplanar pair for range and gain, the V "
                   "for a 0.6 dB lower worst sidelobe and a flatter element "
                   "envelope, at 3 dB and 3° of range."),

        ("h2", "5. Microphone at 2 m"),
        ("img", fig("report/mic2m.png"),
         "Level on the commanded ray at 2 m, phase depth-compensated."),
        ("table", T_MIC),
        ("text", "The V layouts lose level at the microphone because their "
                 "curvature spreads emitter paths; the coplanar pair does not."),
    ]
    return seq


# ---------------------------------------------------------------- mechanics

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


def list_all(session) -> list[dict]:
    items: list[dict] = []
    token = None
    while True:
        params = {"page_size": 500}
        if token:
            params["page_token"] = token
        j = get_json(session, f"/docx/v1/documents/{DOC}/blocks", params)
        data = check(j, "list")
        items += data["items"]
        token = data.get("page_token")
        if not data.get("has_more") or not token:
            return items


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    seq = items()
    if args.dry_run:
        missing = []
        for kind, *rest in seq:
            if kind == "img":
                if not rest[0].exists():
                    missing.append(str(rest[0]))
                print(f"img   {rest[0].name:44s} {rest[1][:46]}")
            elif kind == "card":
                if not rest[0].exists():
                    missing.append(str(rest[0]))
                print(f"card  {rest[0].name}")
            elif kind == "table":
                print(f"table {len(rest[0])}x{len(rest[0][0])}")
            else:
                print(f"{kind:6}{rest[0][:60]}")
        if missing:
            sys.exit("missing files:\n" + "\n".join(missing))
        return

    app_id, app_secret = load_credentials()
    session = requests.Session()
    session.headers.update(
        {"Authorization": f"Bearer {get_tenant_token(app_id, app_secret)}"})

    allb = list_all(session)
    target = None
    for b in allb:
        if b["block_type"] == 3:
            txt = "".join(e.get("text_run", {}).get("content", "")
                          for e in b.get("heading1", {}).get("elements", []))
            if txt.strip() == HEADING:
                target = b
                break
    if target is None:
        sys.exit(f"heading {HEADING} not found")
    kids = [k for k in allb if k.get("parent_id") == target["block_id"]]
    if kids:
        sys.exit(f"{HEADING} already has {len(kids)} children — refusing to "
                 "duplicate; delete them first or extend this script")
    root = target["block_id"]
    print(f"heading {HEADING} -> {root}")

    counts: dict[str, int] = {root: 0}
    parent = root

    def create(par, pos, block, label):
        r = session.post(
            f"{BASE}/docx/v1/documents/{DOC}/blocks/{par}/children",
            json={"children": [block], "index": pos}, timeout=60)
        jj = r.json()
        if jj.get("code") != 0:
            sys.exit(f"{label}: {jj.get('code')} {jj.get('msg')}")
        return jj["data"]["children"][0]["block_id"]

    for kind, *rest in seq:
        pos = counts[parent]
        if kind == "h2":
            bid = create(root, counts[root], heading(2, rest[0]), "h2")
            counts[root] += 1
            parent = bid
            counts[bid] = 0
            print(f"  h2 {rest[0]} -> {bid}")
        elif kind == "h3":
            bid = create(parent, pos, heading(3, rest[0]), "h3")
            counts[parent] += 1
            parent = bid
            counts[bid] = 0
            print(f"  h3 {rest[0]} -> {bid}")
        elif kind == "img":
            path, caption = rest
            bid = create(parent, pos, {"block_type": 27, "image": {}}, "img")
            counts[parent] += 1
            data = {"file_name": path.name, "parent_type": "docx_image",
                    "parent_node": bid, "size": str(path.stat().st_size)}
            with open(path, "rb") as fh:
                uj = session.post(f"{BASE}/drive/v1/medias/upload_all",
                                  data=data,
                                  files={"file": (path.name, fh, "image/png")},
                                  timeout=180).json()
            if uj.get("code") != 0:
                sys.exit(f"upload {path.name}: {uj.get('code')} {uj.get('msg')}")
            w, h = image_size(path)
            pj = session.patch(
                f"{BASE}/docx/v1/documents/{DOC}/blocks/{bid}",
                json={"replace_image": {"token": uj["data"]["file_token"],
                                        "width": w, "height": h, "align": 2}},
                timeout=60).json()
            if pj.get("code") != 0:
                sys.exit(f"replace_image {path.name}: {pj.get('code')}")
            cap = create(parent, counts[parent],
                         {"block_type": 2,
                          "text": {"elements": [run(caption)],
                                   "style": {"align": 2}}}, "caption")
            counts[parent] += 1
            print(f"  img {path.name}")
        elif kind == "card":
            path = rest[0]
            child = session.post(
                f"{BASE}/docx/v1/documents/{DOC}/blocks/{parent}/children",
                json={"children": [{"block_type": 23,
                                    "file": {"view_type": 1}}],
                      "index": counts[parent]}, timeout=60).json()
            if child.get("code") != 0:
                sys.exit(f"file block: {child.get('code')}")
            counts[parent] += 1
            cb = child["data"]["children"][0]
            bid = cb["block_id"]
            if cb.get("block_type") == 33:
                kids = cb.get("children") or []
                if not kids:
                    kids = [b["block_id"] for b in list_all(session)
                            if b.get("parent_id") == bid
                            and b["block_type"] == 23]
                bid = kids[0]
            data = {"file_name": path.name, "parent_type": "docx_file",
                    "parent_node": bid, "size": str(path.stat().st_size)}
            with open(path, "rb") as fh:
                uj = session.post(f"{BASE}/drive/v1/medias/upload_all",
                                  data=data,
                                  files={"file": (path.name, fh, "text/html")},
                                  timeout=180).json()
            if uj.get("code") != 0:
                sys.exit(f"upload file {path.name}: {uj.get('code')}")
            pj = session.patch(
                f"{BASE}/docx/v1/documents/{DOC}/blocks/{bid}",
                json={"replace_file": {"token": uj["data"]["file_token"],
                                       "name": path.name}}, timeout=60).json()
            if pj.get("code") != 0:
                sys.exit(f"replace_file: {pj.get('code')}")
            print(f"  card {path.name}")
        elif kind == "table":
            rows = rest[0]
            R, C = len(rows), len(rows[0])
            bid = create(parent, pos,
                         {"block_type": 31,
                          "table": {"property": {"row_size": R,
                                                 "column_size": C}}}, "table")
            counts[parent] += 1
            allb2 = list_all(session)
            tb = next(b for b in allb2 if b["block_id"] == bid)
            cells = tb.get("children", []) or [
                b["block_id"] for b in allb2 if b.get("parent_id") == bid]
            if len(cells) != R * C:
                sys.exit(f"table cells {len(cells)} != {R * C}")
            for i, cell in enumerate(cells):
                create(cell, 0,
                       {"block_type": 2, "text": {"elements":
                                                  [run(rows[i // C][i % C],
                                                       bold=(i < C))]}},
                       "cell")
                time.sleep(0.12)
            print(f"  table {R}x{C} -> {bid}")
        else:
            block = {"block_type": 2, "text": {"elements": [run(rest[0])]}}
            if kind == "bullet":
                block = {"block_type": 12,
                         "bullet": {"elements": [run(rest[0])]}}
            create(parent, pos, block, kind)
            counts[parent] += 1
            print(f"  {kind} {rest[0][:44]}")
        time.sleep(0.4)

    print("done. total blocks", len(list_all(session)))


if __name__ == "__main__":
    main()
