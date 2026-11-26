// SonicSurface dual-board mounting fixture - interlocking, 30 mm clearance
// Both PCBs rotated 90 deg CCW.  All structural joints are laser-cut tab/slot
// press fits.  Only the 8 PCB mount points use M3 x 55 through-bolts: head
// under the base, reusable nut on top.  No heat-set inserts, no glue.
//
// Render modes: part = "assembly" | "base" | "fences" | "columns" | "boards" | "bolts"
// Dimensions mm.  Measured PCB data: investigation/measurements.json.

$fn = 32;
show_elements = false;

// ---- rotated PCB geometry -------------------------------------------------
board_w = 168.4020;
board_h = 185.0921;
board_t = 1.6;
pitch   = 10.5;
elem_x0 = 5.4060;
elem_y0 = 13.7060;
mount_holes = [
    [3.149, 3.221],
    [3.137, 181.917],
    [165.100, 3.221],
    [165.062, 181.917]
];
// front mid pad moved from 3.2 to 3.8 to keep a 0.75 mm wall to the fence slot
mid_supports = [[84.000, 3.800], [84.000, 181.900]];

// ---- acoustic / fixture choice -------------------------------------------
seam     = 15.75;
y_offset = 5.25;
gap      = 4.848;

// ---- base / clearance -----------------------------------------------------
base_x = 390;
base_y = 220;
base_t = 12;
base_r = 8;
clearance = 30;

// ---- interlocking parts ---------------------------------------------------
fit       = 0.05;
fence_t   = 3;
fence_h   = 32;
fence_tab = 8;
fence_len = 30;
fence_slot_w = fence_t + fit;       // 3.05
fence_slot_l = fence_len + fit;     // 30.05

col_w     = 10;
col_mid   = 6;
col_h     = 30;
col_tenon = 10;
col_slot  = col_w + fit;            // 10.05
mid_slot  = col_mid + fit;          // 6.05

bolt_hole = 3.4;
pcb_hole  = 3.5;
relief_d  = 3.0;

a_x = 20;
a_y = 20;
b_x = a_x + 15 * pitch + seam;      // 193.250
b_y = a_y + y_offset;               // 25.250

// axis, fixed datum face, contact centre
fences = [
    [0, a_x, a_y + 50],
    [0, a_x, a_y + 135],
    [1, a_y, a_x + 84],
    [0, b_x, b_y + 50],
    [0, b_x, b_y + 135],
    [1, b_y, b_x + 84]
];

// cx, cy, width, depth, corner through-hole
columns = concat(
    [for (o = [[a_x, a_y], [b_x, b_y]])
        for (p = mount_holes)
            [o[0] + p[0], o[1] + p[1], col_w, col_w, true]],
    [for (o = [[a_x, a_y], [b_x, b_y]])
        for (p = mid_supports)
            [o[0] + p[0], o[1] + p[1], col_w, col_mid, false]]
);

module rounded_rect_2d(w, h, r) {
    hull() {
        for (x = [r, w-r], y = [r, h-r])
            translate([x, y]) circle(r = r);
    }
}

module fence_bounds(f) {
    axis = f[0]; fixed = f[1]; c = f[2];
    if (axis == 0)
        [fixed - fence_t, c - fence_len/2, fence_t, fence_len];
    else
        [c - fence_len/2, fixed - fence_t, fence_len, fence_t];
}

module fence(f) {
    b = fence_bounds(f);
    color([0.80, 0.34, 0.10, 0.95]) {
        // body 32 above base
        translate([b[0], b[1], 0]) cube([b[2], b[3], fence_h]);
        // 8 mm tab into base
        translate([b[0], b[1], -fence_tab]) cube([b[2], b[3], fence_tab]);
    }
}

module column(c) {
    x = c[0]; y = c[1]; w = c[2]; d = c[3]; through = c[4];
    difference() {
        color([0.36, 0.55, 0.68, 0.82]) {
            translate([x - w/2, y - d/2, 0]) cube([w, d, col_h]);
            translate([x - w/2, y - d/2, -col_tenon]) cube([w, d, col_tenon]);
        }
        if (through)
            translate([x, y, -col_tenon - 0.1])
                cylinder(h = col_h + col_tenon + 0.2, d = bolt_hole);
    }
}

module bolt(c) {
    x = c[0]; y = c[1];
    color([0.55, 0.58, 0.62]) {
        // shaft through base + column + PCB
        translate([x, y, -13]) cylinder(h = 47, d = 3.0);
        // head + washer under the base
        translate([x, y, -16]) cylinder(h = 3.0, d = 5.5);
        translate([x, y, -13]) cylinder(h = 1.0, d = 8.0);
    }
    color([0.30, 0.33, 0.35]) {
        // nylon + steel washer + reusable nut on top of the PCB
        translate([x, y, 31.6]) cylinder(h = 1.5, d = 8.0);
        translate([x, y, 33.1]) cylinder(h = 1.0, d = 8.0);
        translate([x, y, 34.1]) cylinder(h = 3.0, d = 6.4, $fn = 6);
    }
}

module base_plate() {
    difference() {
        color([0.55, 0.68, 0.76, 0.90])
            translate([0, 0, -base_t])
                linear_extrude(height = base_t)
                    rounded_rect_2d(base_x, base_y, base_r);
        // fence slots
        for (f = fences) {
            b = fence_bounds(f);
            translate([b[0] - fit/2, b[1] - fit/2, -base_t - 0.1])
                cube([b[2] + fit, b[3] + fit, base_t + 0.2]);
        }
        // column slots
        for (c = columns)
            translate([c[0] - (c[2] + fit)/2, c[1] - (c[3] + fit)/2, -base_t - 0.1])
                cube([c[2] + fit, c[3] + fit, base_t + 0.2]);
        // 8 through-holes for the PCB bolts
        for (c = columns)
            if (c[4])
                translate([c[0], c[1], -base_t - 0.1])
                    cylinder(h = base_t + 0.2, d = bolt_hole);
    }
}

module board(origin) {
    ox = origin[0]; oy = origin[1];
    difference() {
        color([0.05, 0.35, 0.18, 0.72])
            translate([ox, oy, clearance]) cube([board_w, board_h, board_t]);
        for (p = mount_holes)
            translate([ox + p[0], oy + p[1], clearance - 0.2])
                cylinder(h = board_t + 0.4, d = pcb_hole);
    }
    if (show_elements)
        color([0.85, 0.80, 0.55])
            for (i = [0:15], j = [0:15])
                translate([ox + elem_x0 + pitch*i,
                           oy + elem_y0 + pitch*j,
                           clearance + board_t + 0.4])
                    cylinder(h = 0.8, d = 2.0);
}

module assembly() {
    base_plate();
    for (f = fences) fence(f);
    for (c = columns) column(c);
    board([a_x, a_y]);
    board([b_x, b_y]);
    for (c = columns) if (c[4]) bolt(c);
}

part = "assembly";

if (part == "assembly") assembly();
else if (part == "base") base_plate();
else if (part == "fences") for (f = fences) fence(f);
else if (part == "columns") for (c = columns) column(c);
else if (part == "boards") {
    board([a_x, a_y]);
    board([b_x, b_y]);
}
else if (part == "bolts") for (c = columns) if (c[4]) bolt(c);
