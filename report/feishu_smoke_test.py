#!/usr/bin/env python3
"""Smoke test: replace the empty body of the LUIS repo docx with real blocks.

Writes: heading1, text paragraph, code block, divider. All via the docx API.
"""

from __future__ import annotations

import sys
import time

import requests

from feishu_inspect import (
    BASE,
    WIKI_TOKEN,
    block_preview,
    check,
    get_json,
    get_tenant_token,
    load_credentials,
)


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    app_id, app_secret = load_credentials()
    token = get_tenant_token(app_id, app_secret)

    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {token}"
    s.headers["Content-Type"] = "application/json; charset=utf-8"

    node = check(
        get_json(s, "/wiki/v2/spaces/get_node", {"token": WIKI_TOKEN}), "get_node"
    )["node"]
    if node.get("obj_type") != "docx":
        sys.exit(f"not a docx: {node.get('obj_type')}")

    doc_id = node["obj_token"]
    print(f"document : {doc_id}  ({node.get('title')})")

    data = check(
        get_json(s, f"/docx/v1/documents/{doc_id}/blocks", {"page_size": 500}),
        "blocks list",
    )
    items = data.get("items") or []
    by_id = {b["block_id"]: b for b in items}
    root = next(b for b in items if b.get("block_type") == 1)
    child_ids = root.get("children") or []
    print(f"children : {len(child_ids)}")

    if len(child_ids) == 1:
        only = by_id.get(child_ids[0])
        if only and only.get("block_type") == 2 and not block_preview(only).strip():
            r = s.delete(
                f"{BASE}/docx/v1/documents/{doc_id}/blocks/{doc_id}/children/batch_delete",
                json={"start_index": 0, "end_index": 1},
                timeout=60,
            )
            j = r.json()
            print(f"delete   : code={j.get('code')} msg={j.get('msg')!r}")
            if j.get("code") != 0:
                sys.exit("could not clear the empty paragraph")
            time.sleep(0.3)
    elif child_ids:
        print("body is not empty; appending instead of clearing")

    code_text = (
        "entity PulseExpander is\n"
        "    generic (OUTPUT_LENGTH_CYCLES : integer := 8);\n"
        "    port (clk_in    : in  STD_LOGIC;\n"
        "          pulse_in  : in  STD_LOGIC;\n"
        "          pulse_out : out STD_LOGIC);\n"
        "end PulseExpander;\n"
    )

    children = [
        {
            "block_type": 3,
            "heading1": {
                "elements": [{"text_run": {"content": "API smoke test"}}]
            },
        },
        {
            "block_type": 2,
            "text": {
                "elements": [
                    {
                        "text_run": {
                            "content": (
                                "This section was written by an agent through the "
                                "Feishu Open Platform docx API, using a "
                                "tenant_access_token. No browser or desktop client "
                                "was involved."
                            )
                        }
                    }
                ]
            },
        },
        {
            "block_type": 14,
            "code": {"elements": [{"text_run": {"content": code_text}}]},
        },
        {"block_type": 22, "divider": {}},
    ]

    r = s.post(
        f"{BASE}/docx/v1/documents/{doc_id}/blocks/{doc_id}/children",
        json={"children": children},
        timeout=60,
    )
    j = r.json()
    print(f"create   : code={j.get('code')} msg={j.get('msg')!r}")
    if j.get("code") != 0:
        print(j)
        sys.exit(1)

    created = (j.get("data") or {}).get("children") or []
    for b in created:
        print(f"  + {b.get('block_type'):>3} {b.get('block_id')}")


if __name__ == "__main__":
    main()
