#!/usr/bin/env python3
"""Diagnose and retry the Feishu image upload for the 26.11.25 section.

The CLI's `image` command creates the block, uploads the media, then patches.
If the upload fails, the empty image block stays behind.  This script lists
the section's children, prints any empty image blocks, and probes the media
upload response without changing the document.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(r"C:\Users\12966\.claude\skills\feishu-docx\scripts")
sys.path.insert(0, str(SCRIPT_DIR))
import feishu  # noqa: E402

URL = "https://sjtu.feishu.cn/wiki/VZB1wpDNJiyu3skx2PvcsIydnKd"
H2 = "doxcnt05zZl6L9FxeBbh1o7t1xt"
PNG = Path(r"E:\LUIS\IPP\measurement\figures\setup_lab_plan.png")


def list_blocks(session, doc_id):
    items = []
    page_token = None
    while True:
        params = {"page_size": 500}
        if page_token:
            params["page_token"] = page_token
        data = feishu.api(
            session, "GET", f"/docx/v1/documents/{doc_id}/blocks",
            params=params, what="list blocks",
        )
        items.extend(data.get("items", []))
        if not data.get("has_more"):
            return items
        page_token = data.get("page_token")


def main():
    session = feishu.open_session()
    doc_id = feishu.resolve(session, URL)["document_id"]
    blocks = list_blocks(session, doc_id)
    kids = [b for b in blocks if b.get("parent_id") == H2]
    print(f"section {H2}: {len(kids)} children")
    images = []
    for b in kids:
        if b.get("block_type") == 27:
            token = (b.get("image") or {}).get("token") or ""
            images.append((b["block_id"], token))
            print(" image", b["block_id"], "token:", repr(token))
    empty = [bid for bid, token in images if not token]
    if not empty:
        print("no empty image block to probe")
        return

    block_id = empty[0]
    print(f"uploading {PNG.name} to empty block {block_id} ...")
    size = PNG.stat().st_size
    with PNG.open("rb") as fh:
        r = session.post(
            f"{feishu.BASE}/drive/v1/medias/upload_all",
            data={
                "parent_type": "docx_image",
                "parent_node": block_id,
                "file_name": PNG.name,
                "size": str(size),
            },
            files={"file": (PNG.name, fh, "application/octet-stream")},
            headers={"Content-Type": None},
            timeout=300,
        )
    print("HTTP", r.status_code)
    print(r.text[:1000])
    if r.status_code != 200:
        return
    token = (r.json().get("data") or {}).get("file_token")
    if not token:
        print("no file_token")
        return
    feishu.api(
        session, "PATCH",
        f"/docx/v1/documents/{doc_id}/blocks/{block_id}",
        payload={"replace_image": {
            "token": token, "align": 2, "width": 720, "height": 233,
        }},
        what="replace_image",
    )
    print("patched", block_id)


if __name__ == "__main__":
    main()
