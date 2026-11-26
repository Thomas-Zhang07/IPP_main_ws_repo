#!/usr/bin/env python3
"""Apply the user's inline comments in the 26.11.21 section.

Comment blocks to act on (2026-11-21):
  - expand the two duty-amplitude bullets
  - delete the orphaned scope caption / empty texts / [ ... ] notes, keep the video
  - explain the half-pitch offset and its tolerance after the layout image
  - explain the sync mechanism
  - clarify that "little star together" is melody alignment, not carrier sync
  - expand the "still to verify" bullet
  - rewrite "Next" as the concluded todo list, renumber 5->4, 7->5
"""
from __future__ import annotations

import sys
import time

import requests

from feishu_inspect import BASE, check, get_json, get_tenant_token, load_credentials

DOC = "Fvdld3xEGo0UY9xfKszcxU6HnGc"
ROOT = "doxcnLECNharX1sKBy2aVDMfGtf"  # heading1 26.11.21


def run(content: str) -> dict:
    return {"text_run": {"content": content, "text_element_style": {}}}


def elements(*paras: str) -> list:
    els = []
    for i, p in enumerate(paras):
        if i:
            els.append({"text_run": {"content": "\n", "text_element_style": {}}})
        els.append(run(p))
    return els


def block(kind: str, content: str) -> dict:
    if kind == "bullet":
        return {"block_type": 12, "bullet": {"elements": elements(content)}}
    return {"block_type": 2, "text": {"elements": elements(content)}}


# ---- ids from the 2026-11-21 dump -----------------------------------------
PHASELINE = "doxcnjZD6o2XBpzJhrar9LCyuye"
FRAME = "doxcndJBCnBIhDt9jmK4JfLmvu8"
SCOPE_CAPTION = "doxcnhKy1ZbYfs405RYJKPJmuWL"
EMPTY1 = "EX0WdFAySoSAi7xs9KKcgVC1nAP"
CMT_PICTURE = "Ascrd2NVJoguq0xF2XFcSm89nzh"
CMT_VIDEO = "DaHddB3kdoTMyBxlswvcYqppnWe"
EMPTY2 = "NvDUdFvKxo2jJExEK4scoveon0f"
CMT_YGAP = "IZJKdQmiuoa6nwx6GBAcoGiYnJc"
SYNC = "doxcniFdyTdqlUdhgxO5gRT5dLc"
MELODY = "doxcnF1ok8XEyvJwmpQJHC2cCKc"
VERIFY = "doxcndf09ediBwPptTslgl95vtf"
H_FIXTURE = "doxcnCDvi9A5oK8Qqg1fqnB24Bc"
H_NEXT = "doxcnpSSKI2Ffqyo7g81hUppgAd"
NEXT1 = "doxcnzCG4XOwtNeFGjedRO7RVmf"
NEXT2 = "doxcnD9glEhDNGdUjakNSeKyrX1"

DELETE = [EMPTY1, SCOPE_CAPTION, CMT_PICTURE, CMT_VIDEO, EMPTY2]

PATCH = {
    PHASELINE: (
        "PhaseLine now compares the 4-bit phase counter against an on-step and an "
        "off-step. Pulse width = (off − on) mod 16 bins, and the fundamental amplitude "
        "follows roughly sin(π · width / 16), so a narrower pulse is a quieter channel. "
        "Each pulse is shifted by lead = 4 − width / 2 so its centre stays on the "
        "commanded phase bin; if on equals off the channel stays low (off)."
    ),
    FRAME: (
        "Frame unchanged: each payload byte is amplitude (high nibble) + phase (low "
        "nibble). Amplitude code 0 or ≥ 15 gives width 8, the legacy full-scale pulse; "
        "codes 1–14 give width (code + 1) / 2, i.e. 1–8 bins; 0x10 still means OFF. Old "
        "frames carry high nibble 0, so they behave exactly as before."
    ),
    CMT_YGAP: (
        "Why the y offset: at 40 kHz on a 10.5 mm lattice the grating lobes sit at "
        "54.75°, and no per-element phase, amplitude or on/off pattern can suppress "
        "them — the grating direction sees the same weighted sum as the main beam. "
        "That is a physical limit of the single board."
    ),
    SYNC: (
        "Sync: the primary emits a one-clock pulse (about 195 ns) on MISC_D at carrier "
        "COUNT = 0, once every 25 µs. The secondary samples it through a two-flop "
        "synchronizer in its 50 MHz domain, delays it by 0–255 steps of 20 ns "
        "(SyncTrim), then resets its 40 kHz counter to 17 — the count the primary "
        "reaches after the filter and sync latency. Default trim 127 gives zero "
        "measured phase error; the full range covers about ± 36°."
    ),
    MELODY: (
        "Both boards play the same mode, and a parallel mode change restarts both music "
        "players, so Little Star starts together. That is melody alignment within a few "
        "ms — not carrier sync."
    ),
    VERIFY: (
        "Still to verify: (1) 40 kHz carrier lock — scope MISC_D against MISC_A, expect "
        "the pulse every 25 µs at a fixed delay and without double-triggering; (2) trim "
        "sweep 0:255:8 on the secondary with both arrays broadside, to maximise the "
        "54.75° null; (3) acoustic measurement of the pair at 1–3 m."
    ),
    NEXT1: "Assemble the fixture and measure the real seam (15.75 ± 0.15 mm), y offset "
           "(5.25 ± 0.15 mm) and coplanarity (± 0.25 mm).",
    NEXT2: "Run the secondary trim sweep on the pair and record the 54.75° null depth.",
}

INSERT_AFTER = {
    CMT_YGAP: [
        ("text",
         "The half-pitch offset is the workaround. Board B is shifted 5.25 mm — half of "
         "10.5 mm — in both x and y, which puts its 54.75° lobes 180° out of phase with "
         "board A's. They cancel, while the broadside main beam adds (+6 dB, simulated "
         "−32 dB null)."),
        ("text",
         "The catch is that the null is narrow: 0.15 mm of error already costs ~−27 dB, "
         "0.50 mm drops it to ~−16 dB and 1 mm to ~−11 dB. The y offset therefore has to "
         "be set with shims and checked after assembly, which is why the fixture is "
         "specified at ± 0.15 mm."),
    ],
    SYNC: [
        ("bullet",
         "Trim command 0xE0 0x5A value is accepted only between frames, so a payload "
         "byte equal to 0xE0 can never be mistaken for it."),
    ],
    NEXT2: [
        ("bullet", "Measure the pair at 1–3 m: main-lobe width, 54.75° level, and leak above 60°."),
        ("bullet", "After mounting, try Hann / duty tapering to trade main-beam level for side leak."),
        ("bullet", "Streaming playback (8–16 kHz) stays the next functional milestone; plan "
                   "unchanged from 26.11.11."),
    ],
}

RENAME = {H_FIXTURE: "4. Fixture", H_NEXT: "5. Next"}


def main() -> None:
    dry = "--dry-run" in sys.argv
    app_id, app_secret = load_credentials()
    token = get_tenant_token(app_id, app_secret)
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {token}"})

    def children() -> list[str]:
        j = get_json(s, f"/docx/v1/documents/{DOC}/blocks", {"page_size": 500})
        items = check(j, "blocks")["items"]
        root = next(b for b in items if b["block_id"] == ROOT)
        return list(root.get("children", []))

    if dry:
        print("delete:", len(DELETE))
        print("patch:", len(PATCH))
        print("insert groups:", {k: len(v) for k, v in INSERT_AFTER.items()})
        print("rename:", RENAME)
        return

    # 1) delete comment / orphan blocks
    for bid in DELETE:
        idx = children().index(bid)
        r = s.delete(
            f"{BASE}/docx/v1/documents/{DOC}/blocks/{ROOT}/children/batch_delete",
            json={"start_index": idx, "end_index": idx + 1}, timeout=60)
        j = r.json()
        if j.get("code") != 0:
            sys.exit(f"delete {bid} failed: {j.get('code')} {j.get('msg')}")
        print(f"deleted {bid} at {idx}")
        time.sleep(0.4)

    # 2) rename headings
    for bid, text in RENAME.items():
        r = s.patch(f"{BASE}/docx/v1/documents/{DOC}/blocks/{bid}",
                    json={"update_text_elements": {"elements": elements(text)}}, timeout=60)
        j = r.json()
        if j.get("code") != 0:
            sys.exit(f"rename {bid} failed: {j.get('code')} {j.get('msg')}")
        print(f"heading {bid} -> {text}")
        time.sleep(0.4)

    # 3) patch text in place
    for bid, text in PATCH.items():
        r = s.patch(f"{BASE}/docx/v1/documents/{DOC}/blocks/{bid}",
                    json={"update_text_elements": {"elements": elements(text)}}, timeout=60)
        j = r.json()
        if j.get("code") != 0:
            sys.exit(f"patch {bid} failed: {j.get('code')} {j.get('msg')}")
        print(f"patched {bid}: {text[:50]}")
        time.sleep(0.4)

    # 4) insert after anchors (later anchors first does not matter; indexes recomputed)
    for anchor, items in INSERT_AFTER.items():
        pos = children().index(anchor) + 1
        for kind, text in items:
            r = s.post(f"{BASE}/docx/v1/documents/{DOC}/blocks/{ROOT}/children",
                       json={"children": [block(kind, text)], "index": pos}, timeout=60)
            j = r.json()
            if j.get("code") != 0:
                sys.exit(f"insert after {anchor} failed: {j.get('code')} {j.get('msg')}")
            print(f"inserted {kind} after {anchor}: {text[:50]}")
            pos += 1
            time.sleep(0.4)

    j = get_json(s, f"/docx/v1/documents/{DOC}/blocks", {"page_size": 500})
    print("done. blocks now:", len(check(j, "final")["items"]))


if __name__ == "__main__":
    main()
