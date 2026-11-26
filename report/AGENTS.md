# AGENTS.md — Editing the Feishu docx "LUIS report" via API

Operational notes for any agent asked to read or modify the Feishu wiki page
**LUIS report** (originally titled "LUIS repo"). Everything here has been
executed and verified against the live document; the exact block IDs and
revision are from 2026-11-11.

> The generic, doc-agnostic procedure lives in the global skill `feishu-docx`
> (`~/.claude/skills/feishu-docx/`, with `scripts/feishu.py`). This file keeps
> the LUIS-specific identifiers, credentials and live layout notes.

---

## 1. Mission and ground rules

- **Target:** a Feishu docx inside a wiki space on the `sjtu.feishu.cn` tenant.
- **Use the open API only.** No browser automation, no desktop client, no
  scraping the saved HTML.
- **Identity:** `tenant_access_token` from a self-built app. There is no
  anonymous or per-file API access; a URL is an address, not a credential.
- **Do not commit credentials.** They live outside this repo (see §3).
- **Verify after every write** with `feishu_inspect.py` (§5).

> The AI Assistant playground limits (0.5 CPU, 1 GB, 5-minute runtime, network
> restricted to `open.feishu.cn`) **do not apply here**. These scripts run
> locally and call `open.feishu.cn` directly.

---

## 2. Target identifiers

| Item | Value |
|---|---|
| Wiki URL | `https://sjtu.feishu.cn/wiki/VZB1wpDNJiyu3skx2PvcsIydnKd` |
| Wiki node token | `VZB1wpDNJiyu3skx2PvcsIydnKd` |
| `obj_type` | `docx` |
| `obj_token` = `document_id` | `Fvdld3xEGo0UY9xfKszcxU6HnGc` |
| `space_id` | `7544623376594354178` |
| Root page `block_id` | same as `document_id` |
| Current revision | 242 (concise report + streaming architecture + PulseExpander bug section) |

**Never pass the wiki token to docx endpoints.** `wiki/v2/spaces/get_node`
converts it to `obj_token`; only that works with `docx/v1`.

---

## 3. Credentials and app setup

App: **LUIS report** (`cli_aa7e9f120c39dbb5`), self-built, enabled on the SJTU
tenant.

Credentials file, read automatically by the scripts:

```
C:\Users\12966\.feishu\credentials.env
```

Format:

```
FEISHU_APP_ID=cli_xxxxxxxx
FEISHU_APP_SECRET=xxxxxxxx
```

`FEISHU_APP_ID` / `FEISHU_APP_SECRET` environment variables take precedence if
set. The scripts never print the secret.

Required scopes (already approved and published for this app):

- `wiki:node:read` — resolve wiki node → obj token
- `docx:document` — read and edit document content

Scopes alone are not enough: the app must also be a **member of the wiki space
or a collaborator on the node** with 可编辑. That was granted for this document.

**Secret hygiene:** the App Secret was shared in a chat transcript during setup.
Rotate it in 开发者后台 → 凭证与基础信息 when convenient and update
`credentials.env`.

---

## 4. Access chain

```
FEISHU_APP_ID + FEISHU_APP_SECRET
        │  POST /open-apis/auth/v3/tenant_access_token/internal
        ▼
tenant_access_token (2 h)
        │  GET /open-apis/wiki/v2/spaces/get_node?token=VZB1...
        ▼
node.obj_type = docx, node.obj_token = Fvdld3...
        │
        ├─ GET    /open-apis/docx/v1/documents/{doc_id}
        ├─ GET    /open-apis/docx/v1/documents/{doc_id}/blocks
        ├─ GET    /open-apis/docx/v1/documents/{doc_id}/raw_content
        ├─ POST   /open-apis/docx/v1/documents/{doc_id}/blocks/{doc_id}/children
        ├─ PATCH  /open-apis/docx/v1/documents/{doc_id}/blocks/{block_id}
        └─ DELETE /open-apis/docx/v1/documents/{doc_id}/blocks/{doc_id}/children/batch_delete
```

All paths are relative to `https://open.feishu.cn/open-apis`. Header:
`Authorization: Bearer <token>`, `Content-Type: application/json; charset=utf-8`.

---

## 5. Tooling in this directory

### `feishu_inspect.py` — read-only diagnostic

```powershell
$env:PYTHONIOENCODING="utf-8"
python feishu_inspect.py                     # resolve node + print block tree
python feishu_inspect.py --json blocks.json  # dump raw blocks
python feishu_inspect.py --probe-write       # no-op PATCH, verifies edit rights
```

Prints `obj_type`, `obj_token`, revision, block counts, and an indented tree of
`block_type  block_id  text-preview`. Use it after every mutation.

### `feishu_smoke_test.py` — end-to-end write proof

Clears the body (only if it is a single empty text block), then creates a
heading, paragraph, code block, and divider. It has already run; re-running it
will now **append** rather than clear, because the body is non-empty.

### `feishu_write_report.py` — Markdown-to-docx writer

Replaces the doc body with the report in
`26.11.11_指向性音箱_路线.md`. It maps headings, bullets, ordered lists,
code fences, blockquotes and dividers to docx blocks; Markdown tables are
flattened to bullet rows. It deletes the current body first, then creates
blocks in batches of 25 (the API limit is 50 per call; rate limit is 3 req/s).
With `--nest`, the first heading is created at page level and every other block
is created as its child, so the page has exactly one child.

```powershell
$env:PYTHONIOENCODING="utf-8"
python feishu_write_report.py --dry-run          # parse + preview, no writes
python feishu_write_report.py --replace          # destructive: clear body + write
python feishu_write_report.py --replace --nest   # all blocks under the first heading
```

### `feishu_add_1125.py` — the 26.11.25 simulation section

Appends one `heading1` "26.11.25" at the end of the page with 10 figures
from `E:\LUIS\IPP\sound_wave_sim_figures` and two attached HTML file cards
(`web/overlay.html`, `web/05_coplanar_gap/index.html`). Images use the
three-step flow; files use block_type 23 with `view_type: 1`.

```powershell
$env:PYTHONIOENCODING="utf-8"
python feishu_add_1125.py --dry-run
python feishu_add_1125.py
```

### `feishu_add_1121.py` — the 26.11.21 section

Creates one `heading1` at page level (index 1, i.e. after `26.11.11`) and
appends its body underneath it, leaving the existing subtree untouched.
Images are uploaded with the three-step flow. Local copy of the text:
`26.11.21.md`; images from `assets/11.21/`.

```powershell
$env:PYTHONIOENCODING="utf-8"
python feishu_add_1121.py --dry-run
python feishu_add_1121.py
```

Re-running it appends a **second** 26.11.21 heading; delete the old one first
if you need to redo the section.

---

## 6. Block API cheatsheet

### Endpoints

| Operation | Method / path | Body |
|---|---|---|
| Document meta | `GET /docx/v1/documents/{doc}` | — |
| Plain text | `GET /docx/v1/documents/{doc}/raw_content` | — |
| List all blocks | `GET /docx/v1/documents/{doc}/blocks?page_size=500` | paginate on `page_token` / `has_more` |
| Create children | `POST /docx/v1/documents/{doc}/blocks/{parent}/children` | `{"children":[…], "index":0}` |
| Create nested | `POST /docx/v1/documents/{doc}/blocks/{parent}/descendant` | for tables/grids with content |
| Update block | `PATCH /docx/v1/documents/{doc}/blocks/{block}` | one operation object |
| Delete children | `DELETE /docx/v1/documents/{doc}/blocks/{parent}/children/batch_delete` | `{"start_index":0,"end_index":N}` (left-closed, right-open) |
| Batch update | `PATCH /docx/v1/documents/{doc}/blocks/batch_update` | rarely needed |

`index` in create: `0` prepends, a positive value inserts at that child index,
omitted/`-1` appends. The parent for top-level content is always the
**document ID** (= root page block ID).

### Block types (most useful)

```
1  page          2  text          3–11 heading1–9   12 bullet
13 ordered       14 code          15 quote           17 todo
19 callout       22 divider       23 file            24 grid
25 grid_column   27 image         30 sheet           31 table
32 table_cell    34 quote_container
```

Text-bearing types (`2, 3–11, 12, 13, 14, 15, 17`) share the same payload
shape, keyed by type name:

```json
{"block_type": 3, "heading1": {"elements": [
  {"text_run": {"content": "Section title",
                "text_element_style": {"bold": true}}}
]}}
```

Text elements: `text_run` (content), `mention_user`, `mention_doc` (token +
obj_type + url), `equation` (KaTeX), `reminder`. `file` and `inline_block` are
output-only.

### Create example (append a section)

```json
{
  "children": [
    {"block_type": 3,  "heading1": {"elements": [{"text_run": {"content": "Overview"}}]}},
    {"block_type": 2,  "text":     {"elements": [{"text_run": {"content": "…"}}]}},
    {"block_type": 14, "code":     {"elements": [{"text_run": {"content": "entity …"}}]}},
    {"block_type": 22, "divider":  {}}
  ]
}
```

### Patch examples (edit in place)

```json
{"update_text_elements": {"elements": [{"text_run": {"content": "new text"}}]}}
```

```json
{"update_text_style": {"style": {"align": 2}, "fields": [1]}}
```

`fields` indexes: `1` alignment, `2` done, `3` folded, `4` code language,
`5` code wrap, `6` background color, `7` indentation.

### Limits

- **50 blocks** per `children` create call; **5 sheet blocks** per call.
- **3 req/s per app** (`99991400` / HTTP 400); **3 concurrent edits/s per doc**
  (HTTP 429). Back off exponentially; reads are cheap, writes are not.
- `document_revision_id` defaults to `-1` (latest). Do not pin a revision unless
  you need optimistic concurrency.

---

## 7. Error map

| Code | Meaning | Fix |
|---|---|---|
| `99991672` | App missing scope | Add the scope in 权限管理, then publish a new version |
| `131006` | Wiki node permission denied | Add app to wiki space members or as doc collaborator |
| `131005` | Node/document not found | Wrong token, or doc not in wiki |
| `99991400` | App rate limit | Slow down / backoff |
| HTTP 429 | Per-doc concurrent-edit limit | Backoff |
| `1770001` | Invalid param | Check block JSON shape / enum values |
| `1770002` | Block not found | Re-list blocks; IDs change if blocks were recreated |
| `1770024` / `1770025` | Invalid operation for this block type | Check the capability matrix |
| HTTP 403 | No resource-level permission | App not added to the doc |

If `obj_type` is not `docx`, **stop** — these endpoints do not apply.

---

## 8. Recipes

### Append a section at the end
1. `POST …/blocks/{document_id}/children` with all blocks in order, no `index`.
2. Re-run `feishu_inspect.py`; confirm the new blocks appear under `page`.
3. Batch multiple blocks into one call to stay under rate limits.

### Replace the whole body
1. List the root block's `children` (ordered IDs).
2. `DELETE …/blocks/{document_id}/children/batch_delete` with
   `{"start_index": 0, "end_index": len(children)}`.
3. Create the new blocks under `{document_id}`.
   Deleting by index, not by block ID, is the only option for children.

### Edit one paragraph
1. Find `block_id` in the inspect tree.
2. `PATCH …/blocks/{block_id}` with `update_text_elements`.
   This **replaces all elements**, so rebuild any bold/links you want to keep.

### Tables
Create `block_type: 31` with
`{"table": {"property": {"row_size": R, "column_size": C}}}`; cells are created
automatically. Use the returned `table.cells` IDs and create text children under
each `table_cell` (block_type 32). For tables with content in one shot, use the
`descendant` endpoint. Table cells cannot contain tables/sheets/bitable.

### Images / files
1. Create an **empty image block** `{"block_type": 27, "image": {}}`; the
   response gives its `block_id`.2. Upload: `POST /open-apis/drive/v1/medias/upload_all`, multipart with
   `parent_type=docx_image`, `parent_node={block_id}`, `file_name`, `size`,
   `file`.
3. `PATCH …/blocks/{block_id}` with
   `{"replace_image": {"token": "<file_token>", "width": W, "height": H, "align": 2}}`.
   Width/height are optional on the first call; without them the server uses
   the image's pixel size.
   Creating the image block with a token in the `children` payload returns
   `1770001 invalid param` — the three-step flow above is the working one and
   has been exercised on this doc (section `3. PulseExpander 毛刺`).

### Videos (block_type 23 file + 33 view)

A video is a **file block (23) wrapped in a view block (33)**. The view's
`view_type` decides the rendering: `2` = inline video player, `1` = file card.

```json
// create: ask for a video view up front
POST …/blocks/{parent}/children
{"children": [{"block_type": 23, "file": {"view_type": 2}}], "index": N}
// -> data.children[0] is the VIEW; its children[0] is the FILE block
```

Then upload and bind:

```text
POST /drive/v1/medias/upload_all
  parent_type=docx_file  parent_node=<file block id>  file=<mp4>
PATCH …/blocks/<file block id>
{"replace_file": {"token": "<file_token>", "name": "clip.mp4"}}
```

Gotchas verified on this doc (2026-11-21):

- `replace_file` only accepts a token uploaded **for that same file block**.
  Reusing another block's token returns `1770025 operation and block not match`.
- `view_type` cannot be changed after creation (`update_view` / `replace_view`
  both return `1770001`). Create the wrapper with `view_type: 2` or redo it.
- There are no `…/blocks/{id}/file` or `/media` upload endpoints — they 404.
- **The video is a child of the view block, not of the heading.** Deleting a
  text block that has a view nested under it deletes the video too. List the
  subtree before batch-deleting comment blocks.

### Markdown
There is no API that imports Markdown into an **existing** doc. You must map
Markdown to blocks yourself (headings → 3–11, lists → 12/13, fenced code → 14
with `style.language`, paragraphs → 2). `drive/v1/import_tasks` creates a *new*
docx, which would not update this wiki node.

---

## 9. Current document state (2026-11-21, revision 294)

The disposable smoke-test body has been replaced by a concise 26.11.11 report,
nested under a single top-level heading. The long version is kept locally as
`26.11.11_详细版.md`; the main Markdown and the Feishu doc are the concise one.

The live doc is the source of truth for layout and contains manual edits:
the `Directional Speaker Demo` H1, two images / YouTube links, a single-item
FPGA section, and a `流播放架构` subsection after the streaming protocol.
Other manual trims may exist; do **not** run `--replace` without diffing the
live doc first.

The page now has **two** top-level sections: `26.11.11` (the original report
plus the `PulseExpander.vhd` subtree) and `26.11.21` (progress 11.12–11.20,
added 2026-11-21 from the session history). Both are `heading1` children of
the page.

```
page      Fvdld3xEGo0UY9xfKszcxU6HnGc   (title "LUIS report")
├─ heading1  "26.11.11"   doxcnKtTvS1zVssoqZUpye3Wajb
│  ├─ divider
│  ├─ heading1  "Directional Speaker Demo"
│  ├─ image / text links  (manual)
│  ├─ heading2  "1. 提升指向性"
│  ├─ heading3  "主机 Python"
│  ├─ heading3  "FPGA"
│  ├─ heading2  "2. 流播放"
│  ├─ ...
│  │  └─ heading3  "流播放架构"
│  ├─ heading2  "附录：代码位置"
│  └─ heading1  "PulseExpander.vhd"
│     ├─ text "旧代码" + old source
│     ├─ 3 images
│     ├─ text "新代码" + new source
│     └─ 1 image
└─ heading1  "26.11.21"   doxcnLECNharX1sKBy2aVDMfGtf
   ├─ text   intro line
   ├─ heading2 "1. Calibration verified"     + 1 bullet + video + 2 bullets + image
   ├─ heading2 "2. Per-channel duty amplitude" + 3 bullets + video
   ├─ heading2 "3. Dual board"               + 2 text + image + 6 bullets + 2 images + 2 captions
   ├─ heading2 "4. Fixture"                  + image (3D render) + caption
   └─ heading2 "5. Next"                     + 6 bullets
```

Block counts (revision 770, 90 total): page=1, heading1=4, heading2=8,
heading3=4, bullet=32, text=17, ordered=3, code=5, image=11, divider=1,
view=2, file=2.
The `26.11.11` heading owns 51 children; the `26.11.21` heading owns 35.
The page has two children. Block IDs are stable only while the blocks exist;
re-list before editing rather than hard-coding them.

The 26.11.21 section was edited by hand on 2026-11-21: sections "4. Bench
bring-up" and "6. Acoustic status" were removed and their bullets merged into
"3. Dual board"; section numbering was renumbered 5→4 and 7→5; two of the
screenshots were replaced by 10 s mp4 clips. `feishu_edit_1121.py` is the
one-shot log of the comment fixes (its block IDs are already stale).
To regenerate from Markdown, use `feishu_write_report.py --replace --nest`
only after reconciling the manual edits.

---

## 10. Pitfalls checklist

- [ ] Resolve the wiki token every run — never pass it to `docx/v1`.
- [ ] Root parent is `document_id`, not the node token.
- [ ] The `page` block's `elements` hold the **document title**; patching it
      renames the doc.
- [ ] Deleting children is index-based and destructive; list first, compute
      `end_index` from the actual length.
- [ ] `PATCH update_text_elements` replaces the entire element array.
- [ ] `--replace` in `feishu_write_report.py` deletes every root child; it is
      destructive. Run `--dry-run` first and confirm the target doc.
- [ ] Markdown tables are flattened to bullet rows by the writer. For exact
      tables, create block_type 31 tables via the `descendant` endpoint.
- [ ] Keep create batches <= 50 blocks; the writer uses 25 and sleeps 0.5 s
      between calls to stay under 3 req/s.
- [ ] A heading block can be a parent. `--nest` creates the first heading at
      page level and every other block as its child; the page then has exactly
      one child. Use this when the whole report should sit under one date
      heading.
- [ ] Empty docs still contain one empty text block; clear it before writing if
      you want a clean page.
- [ ] Writes change `revision_id`; reads do not. Use the revision to confirm a
      write happened.
- [ ] Do not create `page`, `grid_column`, `table_cell`, `view`, `mindnote`,
      `task`, or `diagram` as ordinary children.
- [ ] Keep the secret out of this file, the repo, and any commit.
