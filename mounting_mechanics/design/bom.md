# Bill of materials - interlocking fixture, 30 mm clearance

All structural joints are laser-cut **tab/slot press fits**. There are no
heat-set inserts, no dowels, and no glue. The only threaded fasteners are the
**8 PCB through-bolts** at the board mounting holes: M3 x 55 screw + reusable
nut, with a Ø3.4 through-hole in the corner column; the base corner slot is
open. The screw head
is **under the base**; the nut is **on top of the PCB**, so the PCB is removed
by undoing 8 top nuts and the screws stay in the columns.

All dimensions mm. Acrylic must be **cast** acrylic (浇铸板), not extruded
(挤压板). The "Buy" column includes a small spare allowance.

**Exact part count = 23 pieces:** 1 base + 6 fences + 8 corner columns +
4 mid columns + 3 gauges + 1 handle = **23**. The "Buy" column adds spares
(8 fences, 10 corner columns, 6 mid columns) for a total of 29 if you want
spares.

## 1. Laser-cut acrylic

### 12 mm cast acrylic

| Item | Size | Qty | Buy | Notes |
|---|---|---:|---:|---|
| Base plate | 390 x 220, R8 | 1 | 1 | `cut_12mm_sheet.dxf`; 6 fence slots + 12 column slots = 18 rounded slots; no separate base holes |

### 10 mm cast acrylic

| Item | Size | Qty | Buy | Notes |
|---|---|---:|---:|---|
| Corner column | 10 x 10 x 40 | 8 | 10 | 30 above base + 10 tenon; Ø3.4 through-hole; `cut_10mm_sheet.dxf` |

### 6 mm cast acrylic

| Item | Size | Qty | Buy | Notes |
|---|---|---:|---:|---|
| Mid column | 10 x 6 x 40 | 4 | 6 | 30 above base + 10 tenon; no through-hole; `cut_6mm_sheet.dxf` |
| Gap gauge | 4.848 x 30 | 1 | 1 | setting gauge |
| Clear-gap gauge | 1.848 x 30 | 1 | 1 | checks clear gap at B-left fences |
| Y-offset gauge | 5.25 x 30 | 1 | 1 | setting gauge |
| Gauge handle | 20 x 30 | 1 | 1 | optional; cement to gauges |

### 3 mm cast acrylic

| Item | Size | Qty | Buy | Notes |
|---|---|---:|---:|---|
| Datum fence | 30 x 32 body + 8 tab (blank 30 x 40) | 6 | 8 | no holes; `cut_3mm_sheet.dxf` |

## 2. Fasteners

| Item | Specification | Qty | Buy | Use |
|---|---|---:|---:|---|
| M3 x 55 socket-head A2 | DIN 912, A2-70, 2.5 mm hex | 8 | 12 | PCB through-bolts; head under base, nut on top |
| M3 x 55 button-head A2 (alternative) | ISO 7380, A2-70, 2 mm hex | (8) | - | lower-profile alternative to DIN 912 |
| M3 serrated flange nut A2 | DIN 6923, A2-70 | 8 | 12 | **on top of PCB**, reusable |
| M3 standard hex nut A2 (alternative) | DIN 934, A2-70 + Loctite 243 | (8) | - | reusable; use a flat washer |
| M3 flat washer A2 | DIN 125, OD 8, ID 3.2, 1.0 thick | 8 | 30 | under the head, below the base; add 8 if using standard nuts on top |
| M3 nylon washer | OD 8, ID 3.2, 1.5 thick | 8 | 20 | under the top nut / washer on PCB |
| M3 shim washer | ID 3.2, OD 10, 0.05 / 0.10 / 0.20 | 40 assorted | 1 pack | under column shoulders |
| Rubber foot | self-adhesive, 10 mm | 8 | 12 | underside of base |
| Medium threadlocker | Loctite 243 or equivalent | optional | 1 | final assembly |
| Acrylic cement | dichloromethane / Tensol 12 | optional | 1 | gauge handle only |

**No heat-set inserts. No dowels. No M3 x 8, M3 x 12, or M3 x 16. No
female-female standoffs. No structural glue.**

### 2.0 One corner-bolt kit (there are 8 kits)

Every one of the 8 corner columns gets the same kit. From the bottom up:

| Per kit | Item | Note |
|---|---|---|
| 1 | M3 x 55 socket-head screw | inserted from below |
| 1 | M3 flat washer | under the screw head, below the base |
| 1 | M3 serrated flange nut | on top of the PCB; integrated washer |
| 1 | M3 nylon washer | between the PCB and the nut |
| (1) | M3 flat washer | only if using a standard hex nut instead of the flange nut |

So the minimum screw hardware is **8 screws + 8 nuts + 8 flat washers + 8 nylon
washers**. The BOM's "Buy 12/20/30" quantities are just small Taobao packs with
spares; you do not need 30 washers for 8 screws.

### 2.1 Bolt length check

The M3 x 55 assumes a 1.6 mm PCB and the washers above:

| Stack item | Thickness (mm) |
|---|---:|
| socket head (under base) | 3.0 |
| steel washer under head | 1.0 |
| base | 12.0 |
| corner column | 30.0 |
| PCB | 1.6 |
| nylon washer on PCB top | 1.5 |
| steel washer under nut | 1.0 |
| serrated flange nut (or standard) | 3.0 |
| **total** | **53.1** |

M3 x 55 leaves about 1.9 mm beyond the nut. If the PCB measures 2.0-2.4 mm,
M3 x 55 still works (1.1-1.5 mm beyond). If the PCB is thicker than 2.5 mm,
use M3 x 60.

### 2.2 Where the screws go

- 8 screws total, one per **corner column** (10 x 10), at the PCB's four
  mounting holes per board.
- Each screw is inserted **from below**: head + steel washer under the base ->
  open base corner slot -> corner column Ø3.4 -> PCB Ø3.5 -> nylon washer + steel washer ->
  reusable nut on top.
- To remove the PCB, undo the **8 top nuts**; the screws stay in the columns
  and the base. No access under the base is needed.
- The 4 **mid columns** (10 x 6) have no screws; the PCB only rests on them.
- There are no screws at the fences; they are press fits. Removing the PCB does
  not disturb the fence or column press fits.

### 2.3 Minimal screw BOM (3 items, 8 sets)

If you want the fewest screw parts, use **flange-head screws + flange nuts +
nylon washers**. The flange head and flange nut have their washers built in, so
no separate flat washers are needed.

| Item | Specification | Qty | Buy | Position |
|---|---|---:|---:|---|
| M3 x 55 flange-head socket screw A2 | flange head / 带垫, 2.5 mm hex | 8 | 12 | head under the base |
| M3 serrated flange nut A2 | DIN 6923, integrated washer | 8 | 12 | on top of the PCB |
| M3 nylon washer | OD 8, ID 3.2, 1.5 thick | 8 | 20 | under the top nut on PCB |

That is **3 SKUs, 8 pieces each**. No separate flat washers, no nyloc nuts, no
heat-set inserts, no M3 x 8/12/16, no dowels.

The 4 mid columns and the 6 fences still use no screws. The 8 corner columns
use the 8 sets.

### 2.4 Why the BOM has more than 8 screws

The 8 screws are the only threaded fasteners. The other lines are:

- **M3 shims (40 assorted)**: for the **12 columns** (8 corner + 4 mid), to set
  the 30 mm height and coplanarity. This is a small pack; you may use only a
  few per column.
- **Rubber feet (8)**: under the base, so the screw heads under the base do not
  sit on the table.
- **Acrylic parts**: base, 6 fences, 8 corner columns, 4 mid columns; these are
  the fixture, not fasteners.
- **Gauges**: 4.848, 1.848 and 5.25 mm; for checking the gap and y offset.
- **Spares**: the Buy column rounds up to a small pack.

The 4 mid columns have no screws. The 6 fences have no screws. Only the 8
corner columns use the 8 bolt kits.

## 3. Hole and slot specification

All slots are cut through the 12 mm base. Relief circles are cut at the slot
ends. Test-fit on scrap before cutting the base.

| Feature | Nominal | Fit / note |
|---|---|---|
| Fence slot | **3.05 x 30.05** | fence tab 3.00 x 30.00; 0.05 clearance |
| Corner column slot | **10.05 x 10.05** | 10 x 10 tenon; 0.05 clearance |
| Mid column slot | **10.05 x 6.05** | 10 x 6 tenon; 0.05 clearance |
| Corner column through-hole | **Ø3.4** | M3 screw clearance |
| Base corner slot | **10.05 x 10.05 open** | no separate base hole; the bolt passes through the open slot |
| PCB mounting hole | **Ø3.5** | existing PCB hole |
| Slot corner radius | **R1.5** (fence R1.525) | rounded single contour; no separate relief circles |
| Fence tab depth | **8.0** | into 12 mm base |
| Column tenon depth | **10.0** | into 12 mm base |
| PCB underside height | **30.00** | column shoulder on base |

The front mid pad is at local y=3.8, not 3.2: its 6 mm slot then keeps a
**0.75 mm acrylic wall** to the front-fence slot. Do not move it back.

## 4. Purchasing notes (Taobao)

### 4.1 Acrylic laser cutting

Search: **亚克力激光切割定制 浇铸板**. Send the four DXFs:
`cut_12mm_sheet.dxf`, `cut_10mm_sheet.dxf`, `cut_6mm_sheet.dxf`,
`cut_3mm_sheet.dxf`, plus `cut_profiles.dxf` and `cut_profiles.png`.

Message to the shop:

> 按 DXF 1:1 切，单位 mm，不缩放。材料要浇铸板（cast），不是挤压板；
> 透明。12 mm 底板 1；10 mm 角柱 8；6 mm 中柱 4 + 塞规/手柄；3 mm 围栏 6。
> CUT 层切，ENGRAVE 层只刻字。槽宽 3.05 / 10.05 / 6.05 已留 0.05 配合；
> 槽端是 R1.5 圆角（fence 槽 R1.525），每个槽一条闭合轮廓，不要额外的 relief 小圆；孔位按图，不要缩孔。先切同厚度试片确认轻压配合；
> 各件多切 10-20% 备件，贴保护膜。

Do not accept a shop that substitutes extruded sheet or 10 mm for the 12 mm
base without checking the bolt length and slot depth.

### 4.2 Fastener searches

| Item | Taobao search |
|---|---|
| M3 x 55 socket head | `M3*55 304不锈钢 内六角螺丝 DIN912` |
| M3 x 55 button head | `M3*55 304不锈钢 圆头螺丝 ISO7380` |
| M3 serrated flange nut | `M3 带齿法兰螺母 304 DIN6923` |
| M3 standard nut | `M3 六角螺母 304 DIN934` |
| M3 flat washer | `M3 平垫 304 外径8 DIN125` |
| M3 nylon washer | `M3 尼龙垫片 外径8 厚1.5` |
| M3 shim washer | `M3 精密垫片 0.05 0.1 0.2 不锈钢` |
| Rubber foot | `10mm 自粘橡胶脚垫` |
| Threadlocker | `乐泰243` |

## 5. Tools / consumables

- 2.5 mm hex key (DIN 912 socket head); 2 mm hex for ISO 7380 button head.
- Torque wrench 0.1-0.5 Nm.
- Digital calipers 0.01 mm, depth gauge, feeler gauges.
- Soft-jaw vice or small arbor press for the tabs.
- Dial indicator on a bridge or granite straightedge.
- Isopropyl alcohol and lint-free cloth.

## 6. Approximate acrylic area

- 12 mm: base **0.0858 m2**.
- 10 mm: 8 corner columns **0.0032 m2**.
- 6 mm: 4 mid columns + gauges **0.0018 m2**.
- 3 mm: 6 fences **0.0072 m2**.

Order at least 10-20 % extra.

## 7. Why this design

- The fence is a single 3 mm plate with an 8 mm bottom tab. It is the datum;
  the base slot's inner wall sets the datum face. No foot, no glue, no screw.
- The 8 corner columns are 10 x 10 so there is enough acrylic around the
  Ø3.4 through-hole and the M3 washer. The 4 mid columns are 10 x 6, support
  only, and clear the front fence by 0.75 mm.
- Only the 8 PCB mount points use bolts. The screw is inserted from below and
  passes through the base, the column, and the PCB; the reusable nut sits on
  top of the PCB. There is no heat-set insert to pull out, and the PCB is
  removed by undoing the 8 top nuts.
- The 4 mid columns do not have bolts; the PCB rests on them and is held by
  the 8 corner bolts.
