#!/usr/bin/env python3
"""Remove the old verbose PulseExpander section, keeping the compact one."""
import requests

from feishu_inspect import BASE, get_tenant_token, load_credentials, get_json, check

DOC = "Fvdld3xEGo0UY9xfKszcxU6HnGc"
PARENT = "doxcnKtTvS1zVssoqZUpye3Wajb"


def heading_text(b: dict) -> str:
    key = {3: "heading1", 4: "heading2", 5: "heading3"}.get(b.get("block_type"))
    if not key:
        return ""
    return "".join(
        e.get("text_run", {}).get("content", "")
        for e in b[key].get("elements", [])
    )


def main() -> None:
    app_id, secret = load_credentials()
    token = get_tenant_token(app_id, secret)
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {token}"})

    items = check(get_json(s, f"/docx/v1/documents/{DOC}/blocks",
                           {"page_size": 500}), "list")["items"]
    by = {b["block_id"]: b for b in items}
    children = by[PARENT]["children"]

    start = next(i for i, c in enumerate(children)
                 if heading_text(by[c]).startswith("PulseExpander.vhd"))
    end = next(i for i, c in enumerate(children)
               if i > start and heading_text(by[c]).startswith("PulseExpander 毛刺"))
    print(f"deleting [{start}, {end})")

    r = s.delete(
        f"{BASE}/docx/v1/documents/{DOC}/blocks/{PARENT}/children/batch_delete",
        json={"start_index": start, "end_index": end},
        timeout=60,
    )
    j = r.json()
    print("delete:", j.get("code"), j.get("msg"))

    items = check(get_json(s, f"/docx/v1/documents/{DOC}/blocks",
                           {"page_size": 500}), "list")["items"]
    print("blocks now:", len(items))


if __name__ == "__main__":
    main()
