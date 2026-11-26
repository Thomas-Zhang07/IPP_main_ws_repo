# Interlocking dual SonicSurface mounting fixture, 30 mm clearance

**Status:** interlocking press-fit design, rotated boards, 30 mm clearance.  
**Date:** 2026-11-13  
**Workspace:** `E:\LUIS\IPP\mounting_mechanics` (no changes to `SonicSurface`,
`fpga` or `demo`).

## 0. Result

- Both PCBs rotated **90 deg CCW** in plan, same direction, not mirrored.
- **Seam: 15.750 mm**
- **y offset: 5.250 mm**
- **PCB edge gap: 4.848 mm**
- **PCB underside above base: 30.000 mm**
- Base: **390 x 220 x 12 mm** cast acrylic.
- Support: 8 corner columns **10 x 10**, 4 mid columns **10 x 6**, all
  laser-cut and press-fit into the base.
- Datum: 6 fences, **3 mm thick**, press-fit into the base. No feet, no glue.
- Only threaded fasteners: **8 x M3 x 55 through-bolts** at the PCB mounting
  holes. The screw head is under the base; the reusable nut is on top of the
  PCB, so the board is removed by undoing 8 top nuts.

No heat-set inserts, no dowels, no glue.

## 1. Measured PCB facts that drive the design

| Item | Measurement |
|---|---:|
| Board outline, Gerber GM1 | **185.0921 x 168.4020 mm** |
| Grid | 16 x 16, **10.5000 mm pitch**, 157.500 mm span |
| Unrotated x margins | left 13.7060, right 13.8861 mm |
| Unrotated y margins | bottom 5.4960, top 5.4060 mm |
| Mounting holes | 4 x 3.5 mm, about 3.2 mm from the edges |
| Transducer body | 10 mm nominal; 0.406/0.496 mm to the old top/bottom edges |

After the 90 deg CCW rotation:

```
board width  = 168.4020 mm
board height = 185.0921 mm
x = 5.4060 + 10.500*i    i = 0..15
y = 13.7060 + 10.500*j   j = 0..15
```

## 2. Final geometry

| | x (mm) | y (mm) |
|---|---:|---:|
| Board A lower-left | **20.000** | **20.000** |
| Board A upper-right | 188.402 | 205.092 |
| Board B lower-left | **193.250** | **25.250** |
| Board B upper-right | 361.652 | 210.342 |
| Edge gap | **4.848** | - |

Nearest-element seam:

```
B first x - A last x = 198.656 - 182.906 = 15.750 mm
Y offset             = 38.956 - 33.706 =  5.250 mm
```

The butted seam is `168.402 - 157.500 = 10.902 mm`; the 4.848 mm gap brings it
to 15.750 mm, which is 5.25 mm modulo 10.5 mm.

## 3. How the geometry is enforced

- **A left datum:** two 3 mm fences press-fit into the base, faces at
  x = **20.000**.
- **B left datum:** two 3 mm fences in the 4.848 mm seam gap, faces at
  x = **193.250**. The 3 mm fence leaves 1.848 mm to A's right edge.
- **Front datum:** one 3 mm fence per board, faces at A y = **20.000**, B y =
  **25.250**.
- Each fence has an **8 mm bottom tab** in a **3.05 x 30.05** slot. The slot's
  inner wall is the datum; no foot, no dowel, no screw, no glue.
- The boards are pressed against the three fence faces and held by 8
  **M3 x 55** bolts inserted from below through base, corner column, and PCB;
  reusable nuts are on top of the PCB. To take a board off, undo only the
  8 top nuts; the screws stay in the columns. The 4 mid columns are
  support-only.

### 3.1 Columns

- **8 corner columns**, **10 x 10 x 40**: 30 mm above the base, 10 mm tenon.
  Each has a **Ø3.4** through-hole for the M3 bolt.
- **4 mid columns**, **10 x 6 x 40**: 30 mm above, 10 mm tenon, no hole.
  The 10 mm dimension runs along x, the 6 mm along y.
- The **front mid pad is at local y = 3.8**, not 3.2: its 6 mm slot keeps a
  **0.75 mm acrylic wall** to the front-fence slot. Do not move it back.
- The corner columns are 10 mm wide so there is enough acrylic around the
  Ø3.4 through-hole and washer. The mid columns stay 10 x 6 to clear the
  front fence.

## 4. 30 mm ground clearance

- Column tops at **z = 30.000**; PCB top at **31.600** (assuming 1.6 mm).
- Fence height **32 mm**, so the fence contacts the board side and finishes
  0.4 mm above the PCB top.
- Shims under the column shoulders set coplanarity; mid columns get top
  shims. No rail or crossbar crosses the array.
- 30 mm clearance is enough for through-hole transducer pins and normal
  bottom-side SMD parts, but this is not confirmed by the Gerber data. Check
  the tallest bottom-side part before final assembly.

## 5. Parts

| Part | Material | Size | Qty |
|---|---|---|---:|
| Base plate | 12 mm cast acrylic | 390 x 220, R8 | 1 |
| Datum fence | 3 mm cast acrylic | 30 x 32 + 8 tab (blank 30 x 40) | 6 |
| Corner column | 10 mm cast acrylic | 10 x 10 x 40 | 8 |
| Mid column | 6 mm cast acrylic | 10 x 6 x 40 | 4 |
| Gap gauge | 6 mm acrylic | 4.848 x 30 | 1 |
| Clear-gap gauge | 6 mm acrylic | 1.848 x 30 | 1 |
| Y-offset gauge | 6 mm acrylic | 5.25 x 30 | 1 |
| Gauge handle | 6 mm acrylic | 20 x 30 | 1 |

Fasteners and inserts are in `design/bom.md`.

## 6. Hole and slot specification

| Feature | Nominal |
|---|---|
| Fence slot | **3.05 x 30.05**, through 12 mm |
| Corner column slot | **10.05 x 10.05**, through |
| Mid column slot | **10.05 x 6.05**, through |
| Fence tab | 3.00 x 8.00 deep |
| Corner column tenon | 10 x 10 x 10 deep |
| Mid column tenon | 10 x 6 x 10 deep |
| Corner column through-hole | **Ø3.4** |
| Base corner slot | **10.05 x 10.05 open** (no separate base hole) |
| PCB mounting hole | **Ø3.5** |
| Slot corner radius | **R1.5** (fence R1.525) |
| Press fit | **0.05 mm** nominal |

The slot corners are rounded (R1.5; fence slots R1.525) so each slot is one
closed contour and the corners do not crack. Cut a test coupon
first; the laser kerf changes the fit.

## 7. Tolerance stack

### 7.1 x/y

| Contributor | Estimate (mm) |
|---|---:|
| Base slot position (laser) | 0.05 |
| Fence tab-to-slot clearance | 0.05 |
| Fence thickness / datum face | 0.05 |
| PCB edge-to-element margin, per board (assumed; verify) | 0.10 |
| Seating / bolt shift | 0.05 |
| Measurement | 0.03 |
| RSS | **0.14** |
| Thermal, 5 K (acrylic vs FR4, 173.25 mm datum span) | 0.048 |
| RSS including thermal | **0.15** |

Target +/-0.15 mm is met at a stable temperature, but with little margin.
Measure each board's left-edge-to-first-element and front-edge-to-first-row
distances and correct the B datum by lapping/shimming the 3 mm fence face.

### 7.2 Coplanarity

| Contributor | Estimate (mm) |
|---|---:|
| Column shoulder height adjustment residual | 0.03 |
| Base/column squareness | 0.05 |
| PCB thickness variation | 0.10 |
| Transducer seating | 0.10 |
| Differential board sag | 0.05 |
| Bolt clamp distortion | 0.05 |
| Measurement | 0.03 |
| RSS | **0.17** |

Target relative element-plane step **0.25 mm**. The 8 corner columns plus
4 mid columns reduce the sag; measure the transducer faces, not only the PCB.

### 7.3 Acoustic effect of errors

At the 10.5 mm lattice the grating direction is 54.75 deg. A relative offset
error d in the lattice gives a null depth of approximately

```
20*log10( sin(pi*d/10.5) )
```

- 0.15 mm -> -26.9 dB
- 0.25 mm -> -22.5 dB
- 0.50 mm -> -16.4 dB
- 1.00 mm -> -10.6 dB

The 1 mm mechanical target is easy for this fixture, but the acoustic target
is **0.15 mm** for a 20 dB null. Do not relax the datum to 1 mm if the null
matters.

## 8. Risks / open items

1. **Press-fit wear.** The tabs are light press fits; repeated disassembly
   loosens them. For frequent use, add a Ø1.5 taper pin through one fence tab
   and the base.
2. **0.75 mm wall** between the front-fence slot and the front mid column
   slot. Do not move the mid pad back to 3.2; the wall would be 0.175 mm.
3. **B-left 3 mm fence is inside the 4.848 mm seam gap.** It is below the
   expected transducer faces (0.4 mm above PCB top), but check the actual
   transducer stand-off height; if the faces are flush with the PCB it could
   scatter at the seam.
4. **M3 x 55 length** assumes a 1.6 mm PCB and the listed washers. Check the
   thread beyond the top nut; use M3 x 60 if the board is thicker.
5. **Screw heads under the base** sit below the base; use 8 separate rubber
   feet, not a full rubber sheet, so the heads do not sit on the sheet.
6. **4 mid columns are support-only.** The board sag is about 0.18 mm; if a
   board is bowed more than 0.25 mm, check that the mid pads are not
   over-shimmed.
7. **Acrylic CTE** gives about 0.048 mm seam change per 5 K over the 173.25 mm
   datum span. Keep the fixture temperature-stable.
8. **PCB thickness and underside height are unknown.** Measure both; the
   model assumes 1.6 mm board and 30 mm clearance.

## 9. Files

```
mounting_mechanics/
  README.md
  design/
    mount.scad                       parametric interlocking fixture
    top_view_dimensioned.svg         plan, seam/gap/y offset, supports
    seam_detail_dimensioned.svg      5x seam detail
    side_view_dimensioned.svg        section, 30 mm clearance, bolts
    cut_profiles.svg                 laser preview
    cut_profiles.dxf                 combined cut file
    cut_12mm_sheet.dxf               base: 18 rounded slots
    cut_10mm_sheet.dxf               8 corner columns
    cut_6mm_sheet.dxf                4 mid columns + gauges
    cut_3mm_sheet.dxf                6 fences
    dimensions.json
    fixture_3d_preview.png
    bom.md
    assembly.md
    tools/
      generate_drawings.py
      fixture_3d_viewer.html
  investigation/                     source data and trade studies
```

## 10. Regeneration

```
python -I investigation/scripts/measure_pcb.py "investigation/gerber_extracted/Project Outputs for SonicSurface"
python -I investigation/scripts/array_trade.py
python -I investigation/scripts/plot_pattern.py
python -I design/tools/generate_drawings.py
```

`mount.scad` renders with OpenSCAD 2021.01 without external libraries.
