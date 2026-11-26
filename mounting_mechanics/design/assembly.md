# Assembly and alignment - interlocking fixture, 30 mm clearance

This builds the rotated, all-interlocking fixture:

- seam between nearest element centres: **15.750 mm**
- PCB edge gap: **4.848 mm**
- y offset between first rows: **5.250 mm**
- PCB underside above base: **30.000 mm**
- element planes coplanar within **0.25 mm relative**

Both boards are rotated 90 deg CCW, same direction, not mirrored. The only
threaded fasteners are the **8 PCB through-bolts** (M3 x 55, head under the
base, reusable nut on top). Fences and columns are laser-cut tab/slot press
fits. No heat-set inserts, no glue.

## 0. Before you start

1. Measure the PCB thickness at four points. Record it. The model assumes
   1.6 mm.
2. Measure the underside height of the tallest component. The design gives
   30 mm; if any part exceeds 28 mm, revise the column height.
3. Measure each board's left-edge-to-first-element `mA`, `mB` (nominal
   5.406 mm), A's right-edge-to-last-element `rA` (nominal 5.496 mm), and
   front-edge-to-first-row `nA`, `nB` (nominal 13.706 mm).
4. Inspect the 3.5 mm PCB holes and clean burrs.
5. Test-fit one fence tab in one base slot, and one column tenon in one
   column slot, on scrap. The press should be light; do not hammer.

## 1. Base preparation

1. Clean the 18 base slots. Remove laser dust.
2. Check the rounded slot corners; do not enlarge the slots.
3. Dry-fit all 6 fences and all 12 columns without force. If a tab will not
   start, lightly file the tab edge; do not file the slot.
4. Remove all parts after the dry fit.

## 2. Install the six fences

1. Press each 3 mm fence into its 3.05 x 30.05 base slot. The fence's
   board-side face is the datum:
   - A-left-1/A-left-2: x = **20.000**
   - B-left-1/B-left-2: x = **193.250** (in the 4.848 gap)
   - A-front: y = **20.000**
   - B-front: y = **25.250**
2. The fence top is **z = 32.0**; the PCB top will be at 31.6.
3. Check with calipers:
   - A-left to B-left faces: **173.250 mm**
   - A-front to B-front faces: **5.250 mm**
4. If a datum face is off by more than 0.10 mm, correct it by lapping the
   fence face or adding shim stock; the slot itself locates the fence.
5. B-left fences sit in the 4.848 gap; the 3 mm fence leaves 1.848 mm clear
   to A's right edge.

## 3. Install the twelve columns

1. Press the **8 corner columns** (10 x 10) into their 10.05 x 10.05 slots.
   The Ø3.4 through-hole must line up with the open base corner slot.
2. Press the **4 mid columns** (10 x 6) into their 10.05 x 6.05 slots. The
   10 mm dimension runs along x, the 6 mm along y.
3. The column shoulders sit on the base. Check the top faces with a
   straightedge: all at **z = 30.0 +/- 0.1** before loading.
4. If a column is low, add 0.05/0.10 shim under its shoulder. Do not shim
   only one side; the column must sit flat.
5. The 4 mid columns are support-only. Do not drill or tap them.

## 4. Install the boards and the eight through-bolts

1. Lower board A onto its six supports with the old top edge on the left.
2. Press A against the two A-left fences and the A-front fence. Check with a
   0.02 mm feeler gauge that it touches all three datums.
3. Insert four **M3 x 55** bolts from below:
   - steel washer + socket head under the base,
   - through the open base corner slot,
   - through corner column Ø3.4,
   - through PCB Ø3.5,
   - nylon washer + steel washer + reusable nut **on top of the PCB**.
4. Tighten the top nut to **0.20 Nm**. Do not over-tighten: the PCB is
   supported only at the six pads. The screw stays in the column when the nut
   is removed; to take the PCB off, undo only the 8 top nuts.
5. Repeat for board B against the B-left and B-front fences.
6. Re-check that each board is still against its datums after tightening.
7. The 4 mid columns have no bolts; the boards only rest on them.

## 5. Verify the geometry

1. **Edge gap**: A right PCB edge x=188.402; B left PCB edge x=193.250.
   The gap is **4.848 mm**. Use the 4.848 gauge at y about 42 and 110 mm;
   the B-left fences block a 30 mm gauge at other y positions. At y about
   190 use calipers. Use the 1.848 gauge in the clear gap at a fence.
2. **Y offset**: B front edge is **5.250 mm** above A front edge. Check at
   two x positions with a height gauge or the 5.25 gauge.
3. **Seam by element centres**: `seam = 4.848 + rA + mB`; nominal
   5.496 + 5.406 = 10.902, so target 15.750 mm.
4. **Repeatability**: loosen one bolt pair, re-seat the board against its
   datums, re-tighten; the edge gap should repeat within 0.05 mm.

## 6. Set coplanarity

1. Measure the PCB top at the four corners and the two mid pads of each
   board. Measure the transducer faces at the corners and centre.
2. Use board A as the reference. Add/remove shims under the B column
   shoulders to bring the heights together.
3. For the mid columns, trim with thin shims on top; the board must just
   touch, not be pushed upward.
4. Iterate until all relative corner measurements are within **0.15 mm** and
   the worst element-plane step is within **0.25 mm**.
5. Record the shim stack under all 12 columns.

## 7. Final records

Record:

- PCB thickness and measured margins `mA`, `mB`, `nA`, `nB`
- edge gap at three y positions
- y step at two x positions
- computed seam
- shim stacks under all 12 columns
- coplanarity at eight PCB points and at least four transducer faces
- ambient temperature, date, operator

## 8. Disassembly and reassembly

- Remove the 8 **top nuts** and lift the boards vertically. The screws stay in
  the corner columns and the base; no access under the base is needed.
- If the screw turns while undoing the nut, hold the head under the base with
  a 2.5 mm hex key.
- The fences and columns are light press fits; pull them straight out. Do
  not twist a 3 mm fence in its slot.
- The base slots and the fence/column tabs are matched; keep the parts in
  their labelled positions.
- Reassembly: clean the slots, press the fences and columns back, seat the
  boards against the datums, install the bolts, re-check the gap and y step.
- Repeated disassembly wears the press fits. For frequent use, add a Ø1.5
  taper pin through one fence tab and the base.

## 9. Torque limits

| Fastener | Torque |
|---|---:|
| M3 x 55 through-bolt into reusable nut | 0.20 Nm |
| M3 gauge handle (optional) | hand-tight |

Acrylic cracks under point loads. Use the steel washer under the nut and the
nylon washer under the head. Do not use an impact driver. Keep the fixture
out of direct sun and hot cars; acrylic CTE is about 70 ppm/K.

## 10. Hole / slot specification

| Feature | Nominal |
|---|---|
| Fence slot | 3.05 x 30.05, through |
| Corner column slot | 10.05 x 10.05, through |
| Mid column slot | 10.05 x 6.05, through |
| Fence tab | 3.00 x 8.00 deep |
| Corner column tenon | 10 x 10 x 10 deep |
| Mid column tenon | 10 x 6 x 10 deep |
| Corner column through-hole | Ø3.4 |
| Base corner slot | 10.05 x 10.05 open |
| PCB mounting hole | Ø3.5 |
| Slot corner radius | R1.5 (fence R1.525) |
| Press fit | 0.05 mm nominal |

The front mid pad is at local y=3.8; its slot keeps a 0.75 mm acrylic wall to
the front-fence slot. Do not move it back.
