#!/usr/bin/env python3
"""Write the 26.11.11 report into the Feishu docx "LUIS report".

The Feishu docx API has no Markdown import for an existing doc, so this maps
the local Markdown to docx blocks (headings, text, bullets, code, dividers).

Usage:
    python feishu_write_report.py --dry-run
    python feishu_write_report.py --replace
    python feishu_write_report.py --replace --nest   # all under the first heading
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

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

MD_PATH = Path(__file__).with_name("26.11.11_指向性音箱_路线.md")
BATCH_SIZE = 25
SLEEP_S = 0.5


# ---------------------------------------------------------------- inline text

INLINE_RE = re.compile(r"(\*\*.*?\*\*|`[^`]*`)")
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def _run(content: str, *, bold: bool = False, inline_code: bool = False) -> dict:
    run: dict = {"content": content}
    style: dict = {}
    if bold:
        style["bold"] = True
    if inline_code:
        style["inline_code"] = True
    if style:
        run["text_element_style"] = style
    return {"text_run": run}


def inline_elements(text: str) -> list[dict]:
    text = LINK_RE.sub(r"\1 (\2)", text)
    text = text.replace("\\*", "*")
    elements: list[dict] = []
    pos = 0
    for match in INLINE_RE.finditer(text):
        if match.start() > pos:
            elements.append(_run(text[pos : match.start()]))
        token = match.group(0)
        if token.startswith("**") and token.endswith("**"):
            elements.append(_run(token[2:-2], bold=True))
        elif token.startswith("`") and token.endswith("`"):
            elements.append(_run(token[1:-1], inline_code=True))
        pos = match.end()
    if pos < len(text):
        elements.append(_run(text[pos:]))
    if not elements:
        elements.append(_run(""))
    return elements


def text_block(block_type: int, key: str, text: str, *, bold: bool = False) -> dict:
    elements = inline_elements(text)
    if bold:
        for element in elements:
            if "text_run" in element:
                element["text_run"].setdefault("text_element_style", {})["bold"] = True
    return {"block_type": block_type, key: {"elements": elements}}


def code_block(code: str) -> dict:
    return {"block_type": 14, "code": {"elements": [_run(code.rstrip())]}}


# ---------------------------------------------------------------- Markdown


def parse_table_row(line: str) -> list[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [cell.strip() for cell in line.split("|")]


def parse_markdown(md: str) -> list[dict]:
    lines = md.splitlines()
    blocks: list[dict] = []
    paragraph: list[str] = []

    def flush_paragraph() -> None:
        if not paragraph:
            return
        content = " ".join(part.strip() for part in paragraph).strip()
        paragraph.clear()
        if content:
            blocks.append(text_block(2, "text", content))

    i = 0
    while i < len(lines):
        stripped = lines[i].strip()

        # fenced code
        if stripped.startswith("```"):
            flush_paragraph()
            i += 1
            code_lines: list[str] = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1  # closing fence
            code = "\n".join(code_lines)
            if code.strip():
                blocks.append(code_block(code))
            continue

        # divider
        if stripped in ("---", "***", "___"):
            flush_paragraph()
            blocks.append({"block_type": 22, "divider": {}})
            i += 1
            continue

        # headings
        match = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if match:
            flush_paragraph()
            level = len(match.group(1))
            blocks.append(
                text_block(2 + level, f"heading{level}", match.group(2).strip())
            )
            i += 1
            continue

        # table
        if (
            stripped.startswith("|")
            and i + 1 < len(lines)
            and re.match(r"^\|?\s*:?-{3,}", lines[i + 1].strip())
        ):
            flush_paragraph()
            header = parse_table_row(stripped)
            i += 2  # header + separator
            rows: list[list[str]] = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(parse_table_row(lines[i].strip()))
                i += 1
            if header:
                blocks.append(
                    text_block(12, "bullet", " | ".join(header), bold=True)
                )
            for row in rows:
                if any(cell for cell in row):
                    blocks.append(text_block(12, "bullet", " | ".join(row)))
            continue

        # blockquote
        if stripped.startswith(">"):
            flush_paragraph()
            quote_lines: list[str] = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote_lines.append(lines[i].strip()[1:].strip())
                i += 1
            content = " ".join(part for part in quote_lines if part)
            if content:
                blocks.append(text_block(15, "quote", content))
            continue

        # task list
        match = re.match(r"^[-*+]\s+\[([ xX])\]\s+(.*)$", stripped)
        if match:
            flush_paragraph()
            prefix = "☑ " if match.group(1).lower() == "x" else "☐ "
            blocks.append(text_block(12, "bullet", prefix + match.group(2).strip()))
            i += 1
            continue

        # bullet
        match = re.match(r"^[-*+]\s+(.*)$", stripped)
        if match:
            flush_paragraph()
            blocks.append(text_block(12, "bullet", match.group(1).strip()))
            i += 1
            continue

        # ordered
        match = re.match(r"^\d+[.)]\s+(.*)$", stripped)
        if match:
            flush_paragraph()
            blocks.append(text_block(13, "ordered", match.group(1).strip()))
            i += 1
            continue

        # blank line
        if not stripped:
            flush_paragraph()
            i += 1
            continue

        paragraph.append(stripped)
        i += 1

    flush_paragraph()
    return blocks


# ---------------------------------------------------------------- Feishu API


def list_blocks(session: requests.Session, doc_id: str) -> list[dict]:
    blocks: list[dict] = []
    page_token = ""
    while True:
        params = {"page_size": 500}
        if page_token:
            params["page_token"] = page_token
        data = check(
            get_json(session, f"/docx/v1/documents/{doc_id}/blocks", params),
            "blocks list",
        )
        blocks.extend(data.get("items") or [])
        if not data.get("has_more"):
            break
        page_token = data.get("page_token") or ""
        if not page_token:
            break
    return blocks


def delete_children(
    session: requests.Session, doc_id: str, count: int, label: str
) -> None:
    if count <= 0:
        return
    r = session.delete(
        f"{BASE}/docx/v1/documents/{doc_id}/blocks/{doc_id}/children/batch_delete",
        json={"start_index": 0, "end_index": count},
        timeout=60,
    )
    j = r.json()
    print(f"delete {label}: code={j.get('code')} msg={j.get('msg')!r}")
    check(j, f"delete {label}")
    time.sleep(SLEEP_S)


def create_batches(
    session: requests.Session,
    doc_id: str,
    blocks: list[dict],
    parent_id: str | None = None,
) -> list[dict]:
    parent_id = parent_id or doc_id
    created_all: list[dict] = []
    total = len(blocks)
    for start in range(0, total, BATCH_SIZE):
        chunk = blocks[start : start + BATCH_SIZE]
        r = session.post(
            f"{BASE}/docx/v1/documents/{doc_id}/blocks/{parent_id}/children",
            json={"children": chunk},
            timeout=60,
        )
        j = r.json()
        print(
            f"create {start:>3}..{start + len(chunk) - 1:<3}: "
            f"code={j.get('code')} msg={j.get('msg')!r}"
        )
        if j.get("code") != 0:
            print(j)
            sys.exit(1)
        created_all.extend((j.get("data") or {}).get("children") or [])
        time.sleep(SLEEP_S)
    return created_all


# ---------------------------------------------------------------- main


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="parse only")
    parser.add_argument("--replace", action="store_true", help="delete body + write")
    parser.add_argument(
        "--nest",
        action="store_true",
        help="make the first heading the parent of every other block",
    )
    parser.add_argument("--md", type=Path, default=MD_PATH)
    args = parser.parse_args()

    if not args.dry_run and not args.replace:
        parser.error("choose --dry-run or --replace")

    blocks = parse_markdown(args.md.read_text(encoding="utf-8"))
    print(f"markdown : {args.md}")
    print(f"blocks   : {len(blocks)}")
    for block in blocks[:12]:
        key = next((k for k in block if k != "block_type"), None)
        preview = block_preview(block) if key else ""
        print(
            f"  {block['block_type']:>3} {key or '':<10} "
            f"{preview[:90].replace(chr(10), ' ')}"
        )
    if len(blocks) > 12:
        print(f"  ... {len(blocks) - 12} more")

    if args.dry_run:
        print("\n[DRY RUN] no Feishu writes.")
        return

    app_id, app_secret = load_credentials()
    token = get_tenant_token(app_id, app_secret)
    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {token}"
    session.headers["Content-Type"] = "application/json; charset=utf-8"

    node = check(
        get_json(session, "/wiki/v2/spaces/get_node", {"token": WIKI_TOKEN}),
        "get_node",
    ).get("node") or {}
    if node.get("obj_type") != "docx":
        sys.exit(f"not a docx: {node.get('obj_type')!r}")
    doc_id = node["obj_token"]
    print(f"\ndocument : {doc_id}  ({node.get('title')})")

    # Clear the disposable smoke-test body.
    items = list_blocks(session, doc_id)
    root = next(b for b in items if b.get("block_type") == 1)
    child_ids = root.get("children") or []
    print(f"current children: {len(child_ids)}")
    delete_children(session, doc_id, len(child_ids), "old body")

    # The docx API may leave a single empty paragraph after clearing.
    items = list_blocks(session, doc_id)
    by_id = {b["block_id"]: b for b in items}
    root = next(b for b in items if b.get("block_type") == 1)
    child_ids = root.get("children") or []
    if len(child_ids) == 1:
        only = by_id.get(child_ids[0])
        if only and only.get("block_type") == 2 and not block_preview(only).strip():
            delete_children(session, doc_id, 1, "empty paragraph")

    if args.nest and blocks and 3 <= blocks[0].get("block_type", 0) <= 11:
        first = create_batches(session, doc_id, [blocks[0]], parent_id=doc_id)
        if not first:
            sys.exit("first heading was not created; cannot nest")
        heading_id = first[0]["block_id"]
        print(f"parent   : {heading_id} (first heading)")
        create_batches(session, doc_id, blocks[1:], parent_id=heading_id)
    else:
        create_batches(session, doc_id, blocks)

    # Verify
    items = list_blocks(session, doc_id)
    from collections import Counter
    from feishu_inspect import BLOCK_TYPE

    counts = Counter(
        BLOCK_TYPE.get(b.get("block_type", 0), str(b.get("block_type")))
        for b in items
    )
    root = next(b for b in items if b.get("block_type") == 1)
    print(f"\nverify   : blocks={len(items)} children={len(root.get('children') or [])}")
    print("by type  : " + ", ".join(f"{k}={v}" for k, v in counts.most_common()))


if __name__ == "__main__":
    main()
