import json
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

path = r"E:\LUIS\IPP\report\blocks_sync2.json"
d = json.load(open(path, encoding="utf-8"))
items = d["items"] if isinstance(d, dict) and "items" in d else d
by = {b["block_id"]: b for b in items}
keys = {2: "text", 3: "heading1", 4: "heading2", 5: "heading3",
        12: "bullet", 13: "ordered", 14: "code", 15: "quote", 17: "todo", 19: "callout"}


def text(b):
    t = b.get("block_type")
    if t == 27:
        return "[image]"
    if t in (23, 33):
        return "[video]"
    k = keys.get(t)
    if not k:
        return ""
    els = b.get(k, {}).get("elements", [])
    return "".join(e.get("text_run", {}).get("content", "")
                   for e in els if isinstance(e, dict))[:70]


def walk(bid, ind=0):
    b = by[bid]
    print("  " * ind + f"{b['block_type']:>2}  {text(b)}")
    for c in b.get("children", []):
        walk(c, ind + 1)


walk("doxcn6jOuHKhJe3XmIIMgqS3k7c")
