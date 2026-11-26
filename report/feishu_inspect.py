#!/usr/bin/env python3
"""Read-only inspection of a Feishu wiki node backed by a docx document.

Flow:
    app_id + app_secret -> tenant_access_token
    wiki node token     -> get_node -> obj_type + obj_token
    obj_token (docx)    -> document info + full block tree

Credentials are read from FEISHU_APP_ID / FEISHU_APP_SECRET, falling back to
~/.feishu/credentials.env (or FEISHU_ENV_FILE). They are never printed.

Usage:
    python feishu_inspect.py
    python feishu_inspect.py --json blocks.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

import requests

BASE = "https://open.feishu.cn/open-apis"
WIKI_TOKEN = os.environ.get("FEISHU_WIKI_TOKEN", "VZB1wpDNJiyu3skx2PvcsIydnKd")

BLOCK_TYPE = {
    1: "page", 2: "text", 3: "heading1", 4: "heading2", 5: "heading3",
    6: "heading4", 7: "heading5", 8: "heading6", 9: "heading7",
    10: "heading8", 11: "heading9", 12: "bullet", 13: "ordered",
    14: "code", 15: "quote", 17: "todo", 18: "bitable", 19: "callout",
    20: "chat_card", 21: "diagram", 22: "divider", 23: "file", 24: "grid",
    25: "grid_column", 26: "iframe", 27: "image", 28: "isv", 29: "mindnote",
    30: "sheet", 31: "table", 32: "table_cell", 33: "view",
    34: "quote_container", 35: "task", 36: "okr", 40: "add_ons",
    41: "jira_issue", 42: "wiki_catalog", 43: "board", 999: "undefined",
}

# block_type -> key holding its Text payload
TEXT_KEY = {
    2: "text", 3: "heading1", 4: "heading2", 5: "heading3", 6: "heading4",
    7: "heading5", 8: "heading6", 9: "heading7", 10: "heading8",
    11: "heading9", 12: "bullet", 13: "ordered", 14: "code", 15: "quote",
    17: "todo",
}


def load_credentials() -> tuple[str, str]:
    app_id = os.environ.get("FEISHU_APP_ID")
    app_secret = os.environ.get("FEISHU_APP_SECRET")
    if not (app_id and app_secret):
        env_file = Path(
            os.environ.get(
                "FEISHU_ENV_FILE", Path.home() / ".feishu" / "credentials.env"
            )
        )
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8-sig").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key == "FEISHU_APP_ID":
                    app_id = value
                elif key == "FEISHU_APP_SECRET":
                    app_secret = value
    if not (app_id and app_secret):
        sys.exit(
            "Missing credentials. Set FEISHU_APP_ID / FEISHU_APP_SECRET, or create "
            f"{Path.home() / '.feishu' / 'credentials.env'} with those two lines."
        )
    return app_id, app_secret


def check(j: dict, what: str) -> dict:
    if j.get("code") != 0:
        sys.exit(f"{what} failed: code={j.get('code')} msg={j.get('msg')!r}")
    return j.get("data") or {}


def get_tenant_token(app_id: str, app_secret: str) -> str:
    r = requests.post(
        f"{BASE}/auth/v3/tenant_access_token/internal",
        json={"app_id": app_id, "app_secret": app_secret},
        timeout=30,
    )
    j = r.json()
    if j.get("code") != 0:
        sys.exit(
            f"tenant_access_token failed: code={j.get('code')} msg={j.get('msg')!r}\n"
            "  -> check App ID / App Secret under 凭证与基础信息"
        )
    return j["tenant_access_token"]


def get_json(session: requests.Session, path: str, params: dict | None = None) -> dict:
    r = session.get(f"{BASE}{path}", params=params, timeout=60)
    try:
        return r.json()
    except ValueError:
        sys.exit(f"Non-JSON response from {path}: HTTP {r.status_code} {r.text[:200]!r}")


def block_preview(block: dict) -> str:
    key = TEXT_KEY.get(block.get("block_type", 0))
    if not key:
        return ""
    data = block.get(key) or {}
    parts = []
    for el in data.get("elements") or []:
        if "text_run" in el:
            parts.append(el["text_run"].get("content", ""))
        elif "mention_doc" in el:
            parts.append(f"[doc:{el['mention_doc'].get('title', '')}]")
        elif "mention_user" in el:
            parts.append("[user]")
        elif "equation" in el:
            parts.append(f"[eq:{el['equation'].get('content', '')[:20]}]")
        elif "reminder" in el:
            parts.append("[reminder]")
    return "".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", metavar="PATH", help="write raw blocks JSON here")
    parser.add_argument(
        "--probe-write",
        action="store_true",
        help="send a no-op PATCH to verify edit permission",
    )
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    app_id, app_secret = load_credentials()
    token = get_tenant_token(app_id, app_secret)
    masked = (app_id[:10] + "...") if app_id else "?"

    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {token}"

    print(f"app: {masked}  (tenant_access_token OK)")

    node = check(
        get_json(session, "/wiki/v2/spaces/get_node", {"token": WIKI_TOKEN}),
        "wiki get_node",
    ).get("node") or {}

    print(f"node_token : {node.get('node_token')}")
    print(f"title      : {node.get('title')}")
    print(f"obj_type   : {node.get('obj_type')}")
    print(f"obj_token  : {node.get('obj_token')}")
    print(f"space_id   : {node.get('space_id')}")

    if node.get("obj_type") != "docx":
        sys.exit(
            f"\nNot a docx (obj_type={node.get('obj_type')!r}); "
            "the docx block APIs do not apply. Stop here."
        )

    document_id = node["obj_token"]

    meta = check(
        get_json(session, f"/docx/v1/documents/{document_id}"), "document get"
    ).get("document") or {}
    print(f"\ndocument_id: {document_id}")
    print(f"revision   : {meta.get('revision_id')}")
    print(f"doc_title  : {meta.get('title')}")

    blocks: list[dict] = []
    page_token = ""
    while True:
        params = {"page_size": 500}
        if page_token:
            params["page_token"] = page_token
        data = check(
            get_json(session, f"/docx/v1/documents/{document_id}/blocks", params),
            "blocks list",
        )
        blocks.extend(data.get("items") or [])
        if not data.get("has_more"):
            break
        page_token = data.get("page_token") or ""
        if not page_token:
            break

    if args.json:
        Path(args.json).write_text(
            json.dumps(blocks, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\nraw JSON  : {args.json}")

    by_id = {b["block_id"]: b for b in blocks}
    counts = Counter(BLOCK_TYPE.get(b.get("block_type", 0), str(b.get("block_type"))) for b in blocks)
    print(f"\nblocks     : {len(blocks)}")
    print("by type    : " + ", ".join(f"{k}={v}" for k, v in counts.most_common()))

    if args.probe_write:
        target = next((b for b in blocks if b.get("block_type") != 1), None)
        if target is None:
            print("\nwrite probe : skipped (no non-root block)")
        else:
            key = TEXT_KEY.get(target.get("block_type", 0))
            if key:
                elements = (target.get(key) or {}).get("elements") or [
                    {"text_run": {"content": ""}}
                ]
                payload = {"update_text_elements": {"elements": elements}}
            else:
                payload = {
                    "update_text_style": {
                        "style": (target.get(key or "") or {}).get("style", {}),
                        "fields": [1],
                    }
                }
            r = session.patch(
                f"{BASE}/docx/v1/documents/{document_id}/blocks/{target['block_id']}",
                json=payload,
                timeout=60,
            )
            j = r.json()
            print(
                f"\nwrite probe : HTTP {r.status_code} code={j.get('code')} "
                f"msg={j.get('msg')!r}"
            )
            print(
                "              -> EDIT access confirmed"
                if j.get("code") == 0
                else "              -> no EDIT access yet (resource-level permission)"
            )

    root = next((b for b in blocks if b.get("block_type") == 1), None)
    if root is None:
        sys.exit("No page (root) block found in response.")

    print("\n--- block tree ---")

    def walk(block: dict, depth: int) -> None:
        name = BLOCK_TYPE.get(block.get("block_type", 0), str(block.get("block_type")))
        text = block_preview(block).replace("\n", " ")
        if len(text) > 100:
            text = text[:97] + "..."
        print(f"{'  ' * depth}{name:<14} {block.get('block_id')}  {text}")
        for child_id in block.get("children") or []:
            child = by_id.get(child_id)
            if child:
                walk(child, depth + 1)

    walk(root, 0)


if __name__ == "__main__":
    main()
