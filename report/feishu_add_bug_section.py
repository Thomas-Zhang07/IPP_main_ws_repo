#!/usr/bin/env python3
"""Append the PulseExpander bug section (old/new) under the 26.11.11 heading.

Images in docx cannot be created with a token in the children payload:
 1. create an empty image block   {"block_type":27,"image":{}}
 2. upload the PNG with parent_node = that block's id
 3. PATCH the block with replace_image {token, width, height, align}

The section is inserted just before the 附录 heading. Read-only verification
afterwards with feishu_inspect.py.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import requests
from PIL import Image

from feishu_inspect import BASE, check, get_json, get_tenant_token, load_credentials

DOC = "Fvdld3xEGo0UY9xfKszcxU6HnGc"
PARENT = "doxcnKtTvS1zVssoqZUpye3Wajb"  # heading1 "26.11.11"
ASSETS = Path(__file__).parent / "assets" / "11.11"
DISPLAY_W = 1000


def run(content: str, bold: bool = False) -> dict:
    style = {"bold": True} if bold else {}
    return {"text_run": {"content": content, "text_element_style": style}}


def text_block(content: str) -> dict:
    return {"block_type": 2, "text": {"elements": [run(content)]}}


def heading(level: int, content: str) -> dict:
    key = {1: "heading1", 2: "heading2", 3: "heading3"}[level]
    return {"block_type": 2 + level, key: {"elements": [run(content, bold=True)]}}


def bullet(content: str) -> dict:
    return {"block_type": 12, "bullet": {"elements": [run(content)]}}


def code_block(content: str) -> dict:
    return {"block_type": 14, "code": {"elements": [run(content.rstrip())]}}


def preview(b: dict) -> str:
    for key in ("heading1", "heading2", "heading3", "text", "bullet"):
        if key in b:
            return "".join(
                e.get("text_run", {}).get("content", "")
                for e in b[key].get("elements", [])
            )
    return ""


OLD_CODE = (ASSETS / "PulseExpand_old.vhd").read_text(encoding="utf-8", errors="replace")
NEW_CODE = (Path(__file__).parent.parent / "fpga_code" / "src" / "PulseExpander.vhd").read_text(
    encoding="utf-8", errors="replace"
)

# ("kind", payload) in document order.  kind: h1/h2/h3/text/bullet/code/image
SECTION = [
    ("h1", "PulseExpander 毛刺（修复前 / 修复后）"),
    ("text", "旧代码"),
    ("code", OLD_CODE),
    ("image", "bug.png"),
    ("image", "bug2.png"),
    ("image", "bug3.png"),
    ("text", "新代码"),
    ("code", NEW_CODE),
    ("image", "fixed.png"),
]


def main() -> None:
    app_id, app_secret = load_credentials()
    token = get_tenant_token(app_id, app_secret)
    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {token}"})

    j = get_json(session, f"/docx/v1/documents/{DOC}/blocks", {"page_size": 500})
    items = check(j, "list blocks")["items"]
    by_id = {b["block_id"]: b for b in items}
    parent = by_id.get(PARENT)
    if not parent:
        sys.exit("26.11.11 heading not found")

    children = parent.get("children", [])
    start = None
    for i, cid in enumerate(children):
        text = preview(by_id.get(cid, {}))
        if text.startswith(("PulseExpander 毛刺", "3. PulseExpander")):
            start = i
            break

    if start is not None:
        end = next(
            (i for i, cid in enumerate(children)
             if i > start and preview(by_id.get(cid, {})).startswith("附录")),
            len(children),
        )
        r = session.delete(
            f"{BASE}/docx/v1/documents/{DOC}/blocks/{PARENT}/children/batch_delete",
            json={"start_index": start, "end_index": end},
            timeout=60,
        )
        j = r.json()
        if j.get("code") != 0:
            sys.exit(f"delete old section failed: {j.get('code')} {j.get('msg')}")
        print(f"deleted old section [{start}, {end})")
        time.sleep(0.4)
        # refresh tree after deletion
        j = get_json(session, f"/docx/v1/documents/{DOC}/blocks", {"page_size": 500})
        items = check(j, "relist blocks")["items"]
        by_id = {b["block_id"]: b for b in items}
        parent = by_id[PARENT]
        children = parent.get("children", [])

    index = len(children)
    print(f"appending {len(SECTION)} blocks at child index {index}")

    pos = index
    for kind, payload in SECTION:
        if kind == "image":
            # 1) empty image block
            r = session.post(
                f"{BASE}/docx/v1/documents/{DOC}/blocks/{PARENT}/children",
                json={"children": [{"block_type": 27, "image": {}}], "index": pos},
                timeout=60,
            )
            j = r.json()
            if j.get("code") != 0:
                sys.exit(f"create empty image block failed: {j.get('code')} {j.get('msg')}")
            bid = j["data"]["children"][0]["block_id"]

            # 2) upload with parent_node = block id
            path = ASSETS / payload
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
                    files={"file": (path.name, fh, "image/png")},
                    timeout=120,
                )
            uj = u.json()
            if uj.get("code") != 0:
                sys.exit(f"upload {payload} failed: {uj.get('code')} {uj.get('msg')}")
            ft = uj["data"]["file_token"]

            # 3) bind + display size
            w, h = Image.open(path).size
            disp_h = round(h * DISPLAY_W / w)
            p = session.patch(
                f"{BASE}/docx/v1/documents/{DOC}/blocks/{bid}",
                json={"replace_image": {"token": ft, "width": DISPLAY_W,
                                        "height": disp_h, "align": 2}},
                timeout=60,
            )
            pj = p.json()
            if pj.get("code") != 0:
                sys.exit(f"replace_image {payload} failed: {pj.get('code')} {pj.get('msg')}")
            print(f"  image {payload}: block={bid} token={ft}")
        else:
            block = {"h1": heading(1, payload), "h2": heading(2, payload),
                     "h3": heading(3, payload), "text": text_block(payload),
                     "bullet": bullet(payload), "code": code_block(payload)}[kind]
            r = session.post(
                f"{BASE}/docx/v1/documents/{DOC}/blocks/{PARENT}/children",
                json={"children": [block], "index": pos},
                timeout=60,
            )
            j = r.json()
            if j.get("code") != 0:
                sys.exit(f"create {kind} failed: {j.get('code')} {j.get('msg')}")
            print(f"  {kind}: {payload[:40]}")
        pos += 1
        time.sleep(0.4)

    j = get_json(session, f"/docx/v1/documents/{DOC}/blocks", {"page_size": 500})
    print(f"done. blocks now: {len(check(j, 'final list')['items'])}")


if __name__ == "__main__":
    main()
