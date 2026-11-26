#!/usr/bin/env python3
"""Append the 26.11.21 section (11.12–11.20 progress) to the LUIS report.

Creates one heading1 at page level (after 26.11.11) and appends the section
body underneath it, so the page keeps its existing 26.11.11 subtree intact.

Images use the three-step flow: empty image block -> medias/upload_all with
parent_node = block id -> PATCH replace_image.

Usage:
    python feishu_add_1121.py --dry-run
    python feishu_add_1121.py
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
ASSETS = Path(__file__).parent / "assets" / "11.21"
PAGE_INDEX = 1  # place the new heading after 26.11.11


def run(content: str, bold: bool = False) -> dict:
    style = {"bold": True} if bold else {}
    return {"text_run": {"content": content, "text_element_style": style}}


def heading(level: int, content: str) -> dict:
    key = {1: "heading1", 2: "heading2", 3: "heading3"}[level]
    return {"block_type": 2 + level, key: {"elements": [run(content, bold=True)]}}


SECTION = [
    ("h1", "26.11.21"),
    ("text", "Progress 11.12 – 11.20: calibration verified on hardware, "
             "per-channel amplitude firmware, dual-board sync, and the fixture."),

    ("h2", "1. Calibration verified (11.12)"),
    ("bullet", "Primary-raw table is applied at the right wire bytes: group 9 slot 0 = 180°, "
               "slot 2 = 0°; group 27 slots 2 / 4 opposite. Measured at the driver pads, 40 kHz."),
    ("bullet", "16 phase bins verified: 1.5625 µs per bin, correct sign, matching steer_2d."),
    ("bullet", "Slot → PCB Q map measured: slot 0=Q0, 1=Q3, 2=Q2, 3=Q4, 4=Q5, 5=Q6, 6=Q7, 7=Q1."),
    ("bullet", "Keep the table in wire order; the permuted variant is unverified and would "
               "undo the calibration."),
    ("image", "11.12.1.jpg"),
    ("text", "Measured wire ↔ physical coordinate map used for the check."),

    ("h2", "2. Per-channel duty amplitude (11.12 – 11.13)"),
    ("bullet", "PhaseLine now drives on/off steps: pulse width sets amplitude, pulse centre is "
               "fixed, so the phase does not move."),
    ("bullet", "Frame unchanged: low nibble phase, high nibble amplitude (0 = legacy full scale, "
               "0x10 = off). Old frames are bit-for-bit identical."),
    ("bullet", "Fit: primary 5,622 / 6,272 LE (90 %), secondary 5,679 / 6,272 (91 %)."),
    ("bullet", "12 RTL tests per board and 186 host tests pass."),
    ("image", "scope_11.12.2.jpg"),
    ("text", "Two channels at 40 kHz, CH1 vs CH2 phase offset on the bench scope."),

    ("h2", "3. Dual board (11.13)"),
    ("bullet", "Geometry: coplanar, same facing, both boards rotated 90° CCW, board B offset "
               "half a pitch (5.25 mm) in x and y. Element seam 15.75 mm, PCB gap 4.85 mm."),
    ("bullet", "Simulation: the 54.75° grating lobes cancel by ~−32 dB while the main beam "
               "adds +6 dB. Tolerance is sharp: ±0.15 mm holds ~−30 dB, ±0.5 mm only ~−15 dB."),
    ("bullet", "Sync: primary sends a one-clock pulse at carrier COUNT = 0 (MISC_D); the "
               "secondary locks to it and is trimmed in 20 ns steps (0xE0 0x5A value)."),
    ("bullet", "Board select: primary 0xC0, secondary 0xC1."),

    ("h2", "4. Bench bring-up (11.18)"),
    ("bullet", "Two independent UART links: primary CH340 (COM8), secondary FTDI (COM6), "
               "TX → port B, 38.4 kBaud."),
    ("bullet", "Individual mode control passes on both boards. The dual sender sends one frame "
               "per board in parallel, ~67 ms per update."),
    ("bullet", "Both boards play the same mode and can start a melody together."),
    ("bullet", "Still to verify: 40 kHz carrier lock (scope MISC_D → MISC_A) and the 54.75° "
               "null trim sweep."),
    ("image", "11.19two_borad.jpg"),
    ("text", "Both boards on the bench, each on its own supply."),
    ("image", "11.19TXD-B.jpg"),
    ("text", "FTDI TX wired to the secondary's port B."),

    ("h2", "5. Fixture (11.13 – 11.19)"),
    ("bullet", "Laser-cut design: 390 × 220 × 12 mm acrylic base, press-fit columns and fences, "
               "8 × M3 × 55 through-bolts, 30 mm underside clearance."),
    ("bullet", "Bench build is MDF; target alignment ±0.15 mm in x/y, ±0.25 mm coplanarity."),
    ("image", "fixture_11.19.1.jpg"),
    ("text", "Trial fixture with the array mounted; laser-cut slots line up."),

    ("h2", "6. Acoustic status and limits"),
    ("text", "Single board, C4 tone, near field: 0° 84 dB, 10° 78 dB, 40° 67 dB, 50° 50 dB, "
             "90° about 40 dB."),
    ("text", "The 54.75° grating lobe is invariant under any per-element phase, amplitude or "
             "on/off pattern. Only the pitch, the carrier or the two-board offset removes it."),

    ("h2", "7. Next"),
    ("bullet", "Scope the sync, run the trim sweep, measure the pair at 1–3 m."),
    ("bullet", "Streaming playback (8–16 kHz) stays the next functional milestone, plan "
               "unchanged from 26.11.11."),
]


def image_size(path: Path, max_w: int = 900) -> tuple[int, int]:
    w, h = Image.open(path).size
    if h > w:  # portrait photos stay narrower
        max_w = 520
    width = min(w, max_w)
    return width, round(h * width / w)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.dry_run:
        for kind, payload in SECTION:
            print(f"{kind:7} {payload[:90]}")
        return

    app_id, app_secret = load_credentials()
    token = get_tenant_token(app_id, app_secret)
    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {token}"})

    # 1) new heading1 at page level, after 26.11.11
    j = get_json(session, f"/docx/v1/documents/{DOC}/blocks", {"page_size": 500})
    items = check(j, "list blocks")["items"]
    page = next(b for b in items if b["block_id"] == DOC)
    existing = page.get("children", [])
    index = len(existing) if PAGE_INDEX > len(existing) else PAGE_INDEX

    r = session.post(
        f"{BASE}/docx/v1/documents/{DOC}/blocks/{DOC}/children",
        json={"children": [heading(1, "26.11.21")], "index": index},
        timeout=60,
    )
    j = r.json()
    if j.get("code") != 0:
        sys.exit(f"create heading failed: {j.get('code')} {j.get('msg')}")
    parent = j["data"]["children"][0]["block_id"]
    print(f"created heading1 26.11.21 at page index {index}: {parent}")
    time.sleep(0.4)

    # 2) body under the new heading
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

            path = ASSETS / payload
            mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
            data = {
                "file_name": path.name,
                "parent_type": "docx_image",
                "parent_node": bid,
                "size": str(path.stat().st_size),
            }
            with open(path, "rb") as fh:
                u = session.post(
                    f"{BASE}/drive/v1/medias/upload_all",
                    data=data,
                    files={"file": (path.name, fh, mime)},
                    timeout=120,
                )
            uj = u.json()
            if uj.get("code") != 0:
                sys.exit(f"upload {payload} failed: {uj.get('code')} {uj.get('msg')}")
            ft = uj["data"]["file_token"]

            w, h = image_size(path)
            p = session.patch(
                f"{BASE}/docx/v1/documents/{DOC}/blocks/{bid}",
                json={"replace_image": {"token": ft, "width": w, "height": h, "align": 2}},
                timeout=60,
            )
            pj = p.json()
            if pj.get("code") != 0:
                sys.exit(f"replace_image {payload} failed: {pj.get('code')} {pj.get('msg')}")
            print(f"  image {payload} -> {bid}")
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
