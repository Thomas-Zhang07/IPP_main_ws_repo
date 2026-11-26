#!/usr/bin/env python3
"""Generate the interlocking, 30 mm-clearance fixture drawings and laser DXFs.

All structural joints are laser-cut tab/slot press fits.  The only threaded
fasteners are the 8 PCB through-bolts: M3 x 55 bolt + washer + nut, with a
through-hole in the corner column; the base corner slot is open.  No heat-set
inserts, no glue.

Run: python -I generate_drawings.py
Requires ezdxf.
"""
from __future__ import annotations

import json
import math
import os

import ezdxf
from ezdxf import units

OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# ---- rotated board geometry (mm) -----------------------------------------
BOARD_W = 168.4020          # old height
BOARD_H = 185.0921          # old width
PITCH = 10.5
EX = 5.4060
EY = 13.7060
SEAM = 15.75
YOFF = 5.25
GAP = 4.848

A_X, A_Y = 20.0, 20.0
B_X = A_X + 15 * PITCH + SEAM      # 193.250
B_Y = A_Y + YOFF                    # 25.250

BASE_W, BASE_H, BASE_T = 390.0, 220.0, 12.0
CLEARANCE = 30.0

# ---- interlocking parts (mm) ---------------------------------------------
FIT = 0.05                  # slot oversize per side pair
FENCE_T = 3.0               # fence thickness
FENCE_H = 32.0              # fence height above base
FENCE_TAB = 8.0             # fence tab depth into base
FENCE_LEN = 30.0            # fence length
FENCE_BLANK_H = FENCE_H + FENCE_TAB          # 40
FENCE_SLOT_W = FENCE_T + FIT                 # 3.05
FENCE_SLOT_L = FENCE_LEN + FIT               # 30.05

COL_W = 10.0                # corner column width/depth
COL_D_MID = 6.0             # mid column depth (y)
COL_H = 30.0                # column height above base
COL_TENON = 10.0            # column tenon into base
COL_BLANK_H = COL_H + COL_TENON              # 40
COL_SLOT = COL_W + FIT                       # 10.05
MID_SLOT = COL_D_MID + FIT                   # 6.05

BOLT_HOLE = 3.4             # through-hole for M3 bolt
PCB_HOLE = 3.5              # existing PCB mounting hole
# Rounded slot corners replace the old separate relief circles.
FENCE_SLOT_R = FENCE_SLOT_W / 2   # 1.525, stadium ends
COL_SLOT_R = 1.5                  # corner and mid column slots

MOUNT = [(3.149, 3.221), (3.137, 181.917), (165.100, 3.221), (165.062, 181.917)]
# Front mid pad moved from y=3.2 to 3.8 so its 10 x 6 slot keeps a 0.75 mm
# acrylic wall to the front-fence slot.  Back pad unchanged.
MID = [(84.000, 3.800), (84.000, 181.900)]

# axis, fixed datum face, contact centre
FENCES = [
    (0, A_X, A_Y + 50),
    (0, A_X, A_Y + 135),
    (1, A_Y, A_X + 84),
    (0, B_X, B_Y + 50),
    (0, B_X, B_Y + 135),
    (1, B_Y, B_X + 84),
]

# cx, cy, width, depth, corner-through-hole
COLUMNS = []
for ox, oy in [(A_X, A_Y), (B_X, B_Y)]:
    for hx, hy in MOUNT:
        COLUMNS.append((ox + hx, oy + hy, COL_W, COL_W, True))
    for mx, my in MID:
        COLUMNS.append((ox + mx, oy + my, COL_W, COL_D_MID, False))

ELEM_A = [(A_X + EX + PITCH * i, A_Y + EY + PITCH * j) for i in range(16) for j in range(16)]
ELEM_B = [(B_X + EX + PITCH * i, B_Y + EY + PITCH * j) for i in range(16) for j in range(16)]


class SVG:
    def __init__(self, path, w, h, title, ox, oy, flip=True):
        self.path, self.w, self.h = path, w, h
        self.ox, self.oy = ox, oy
        self.flip = flip
        self.sx = self.sy = 1.0
        self.lines = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}mm" height="{h}mm" '
            f'viewBox="0 0 {w} {h}">',
            f"<title>{title}</title>",
            '<rect width="100%" height="100%" fill="white"/>',
            '<g font-family="Arial, Helvetica, sans-serif" font-size="3.2" fill="#111">',
        ]

    def X(self, x): return self.ox + x * self.sx

    def Y(self, y): return self.oy - y * self.sy if self.flip else self.oy + y * self.sy

    def line(self, x1, y1, x2, y2, color="#111", w=0.25, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.lines.append(f'<line x1="{self.X(x1):.3f}" y1="{self.Y(y1):.3f}" '
                          f'x2="{self.X(x2):.3f}" y2="{self.Y(y2):.3f}" '
                          f'stroke="{color}" stroke-width="{w}"{d}/>')

    def rect(self, x, y, w, h, stroke="#111", fill="none", sw=0.3, rx=0, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        xa, xb = self.X(x), self.X(x + w)
        ya, yb = self.Y(y), self.Y(y + h)
        self.lines.append(f'<rect x="{min(xa,xb):.3f}" y="{min(ya,yb):.3f}" '
                          f'width="{abs(xb-xa):.3f}" height="{abs(yb-ya):.3f}" '
                          f'rx="{rx*self.sx:.3f}" stroke="{stroke}" fill="{fill}" '
                          f'stroke-width="{sw}"{d}/>')

    def circle(self, x, y, r, stroke="#111", fill="none", sw=0.25):
        rs = r * (self.sx + self.sy) / 2
        self.lines.append(f'<circle cx="{self.X(x):.3f}" cy="{self.Y(y):.3f}" '
                          f'r="{rs:.3f}" stroke="{stroke}" fill="{fill}" stroke-width="{sw}"/>')

    def text(self, x, y, s, size=3.2, anchor="start", color="#111", weight="normal", rot=0):
        tr = f' transform="rotate({rot} {self.X(x):.3f} {self.Y(y):.3f})"' if rot else ""
        parts = str(s).split("\n")
        if len(parts) == 1:
            body = s
        else:
            body = "".join(
                f'<tspan x="{self.X(x):.3f}" dy="{0 if i==0 else size*1.2:.3f}">{p}</tspan>'
                for i, p in enumerate(parts))
        self.lines.append(f'<text x="{self.X(x):.3f}" y="{self.Y(y):.3f}" '
                          f'font-size="{size}" text-anchor="{anchor}" fill="{color}" '
                          f'font-weight="{weight}"{tr}>{body}</text>')

    def arrow(self, x, y, ang, color="#111"):
        L, W = 1.5, 0.55
        pts = [(0, 0), (-L, W), (-L, -W)]
        c, s = math.cos(ang), math.sin(ang)
        p = [(x + c*px - s*py, y + s*px + c*py) for px, py in pts]
        self.lines.append('<polygon points="' + " ".join(
            f"{self.X(px):.3f},{self.Y(py):.3f}" for px, py in p) + f'" fill="{color}"/>')

    def dim_h(self, x1, x2, y, label, color="#b02020", size=3.2):
        self.line(x1, y, x1, y, color, 0.18)
        self.line(x1, y, x2, y, color, 0.25)
        self.arrow(x1, y, 0, color)
        self.arrow(x2, y, math.pi, color)
        self.text((x1+x2)/2, y+1.4, label, size, "middle", color)

    def dim_v(self, y1, y2, x, label, off=0, color="#b02020", size=3.2):
        xd = x + off
        self.line(x, y1, xd, y1, color, 0.18)
        self.line(x, y2, xd, y2, color, 0.18)
        self.line(xd, y1, xd, y2, color, 0.25)
        self.arrow(xd, y1, math.pi/2, color)
        self.arrow(xd, y2, -math.pi/2, color)
        self.text(xd-1.2, (y1+y2)/2, label, size, "middle", color, rot=-90)

    def finish(self):
        self.lines.append("</g></svg>")
        with open(self.path, "w", encoding="utf-8") as f:
            f.write("\n".join(self.lines))


def fence_body(axis, fixed, centre):
    if axis == 0:
        return (fixed - FENCE_T, centre - FENCE_LEN/2, FENCE_T, FENCE_LEN)
    return (centre - FENCE_LEN/2, fixed - FENCE_T, FENCE_LEN, FENCE_T)


def fence_slot(axis, fixed, centre):
    if axis == 0:
        return (fixed - FENCE_SLOT_W, centre - FENCE_SLOT_L/2,
                FENCE_SLOT_W, FENCE_SLOT_L)
    return (centre - FENCE_SLOT_L/2, fixed - FENCE_SLOT_W,
            FENCE_SLOT_L, FENCE_SLOT_W)


def col_slot(cx, cy, w, d):
    return (cx - (w + FIT)/2, cy - (d + FIT)/2, w + FIT, d + FIT)


def top_view():
    s = SVG(os.path.join(OUT, "design", "top_view_dimensioned.svg"),
            540, 310, "Interlocking rotated fixture - top view (mm)", 40, 280)
    s.rect(0, 0, BASE_W, BASE_H, "#333", "#f4f4f0", 0.7, 8)
    # boards
    s.rect(A_X, A_Y, BOARD_W, BOARD_H, "#0d5a30", "#e8f5e9", 0.8)
    s.rect(B_X, B_Y, BOARD_W, BOARD_H, "#0d5a30", "#e8f5e9", 0.8)
    for x, y in ELEM_A + ELEM_B:
        s.circle(x, y, 0.72, "#b02020", "#b02020", 0.1)
    # 6 fences, direct into the base
    for axis, fixed, centre in FENCES:
        x, y, w, h = fence_body(axis, fixed, centre)
        s.rect(x, y, w, h, "#d06010", "#f8d8b8", 0.4)
    # 8 corner + 4 mid interlocking columns
    for cx, cy, w, d, through in COLUMNS:
        s.rect(cx - w/2, cy - d/2, w, d, "#1f5f9f", "#dceafa", 0.4)
        if through:
            s.circle(cx, cy, BOLT_HOLE/2, "#333", "white", 0.25)
    # section line A-A for the side view
    s.line(-8, 110, 395, 110, "#555", 0.35, "3,2")
    s.text(-11, 110, "A", 4, "end", "#555", "bold")
    s.text(396, 110, "A", 4, "start", "#555", "bold")
    # labels
    s.text(A_X+70, A_Y+BOARD_H-10, "BOARD A (rotated 90 CCW)", 4.0, "start", "#0d5a30", "bold")
    s.text(B_X+70, B_Y+BOARD_H-10, "BOARD B (same rotation)", 4.0, "start", "#0d5a30", "bold")
    s.text(A_X+50, A_Y+90, "168.402 x 185.092\n16 x 16 at 10.500", 3.2, "middle", "#0d5a30")
    s.text(B_X+50, B_Y+90, "168.402 x 185.092\n16 x 16 at 10.500", 3.2, "middle", "#0d5a30")
    # dimensions
    s.dim_h(A_X+EX+15*PITCH, B_X+EX, 215, "15.75 seam", size=3.4)
    s.dim_h(A_X+BOARD_W, B_X, 14, "4.848 edge gap", size=3.2)
    s.dim_v(A_Y+EY, B_Y+EY, 375, "5.25 y offset", off=8, size=3.2)
    s.dim_h(0, BASE_W, -12, "390 base width", size=3.2)
    s.text(5, 230, "6 x 3 mm fences direct into base; 8 x 10x10 + 4 x 10x6 interlocking columns.", 2.6)
    s.text(5, 225, "Only 8 x M3 through-bolts at PCB mounts. No heat-set inserts, no glue.", 2.6)
    s.finish()


def seam_detail():
    scale = 5.0
    x0, x1, y0, y1 = 178.0, 204.0, 24.0, 56.0
    w = (x1-x0)*scale + 95
    h = (y1-y0)*scale + 75
    s = SVG(os.path.join(OUT, "design", "seam_detail_dimensioned.svg"),
            w, h, "Rotated seam detail (5x, mm)", 55, h-35)
    s.X = lambda x: 55 + (x-x0)*scale
    s.Y = lambda y: (h-35) - (y-y0)*scale
    s.sx = s.sy = scale
    for gx in range(178, 205, 2):
        s.line(gx, y0, gx, y1, "#ececec", 0.15)
    for gy in range(24, 57, 2):
        s.line(x0, gy, x1, gy, "#ececec", 0.15)
    s.rect(178, y0, 10.402, y1-y0, "#0d5a30", "#eef8f0", 0.8)
    s.rect(193.25, y0, 10.75, y1-y0, "#0d5a30", "#eef8f0", 0.8)
    s.line(188.402, y0, 188.402, y1, "#0d5a30", 1.2)
    s.line(193.250, y0, 193.250, y1, "#0d5a30", 1.2)
    for x, y in ELEM_A + ELEM_B:
        if x0 <= x <= x1 and y0 <= y <= y1:
            s.circle(x, y, 0.36, "#b02020", "#b02020", 0.15)
    s.text(185.0, 25.8, "A right edge", 3.0, "middle", "#0d5a30", "bold")
    s.text(196.5, 25.8, "B left edge", 3.0, "middle", "#0d5a30", "bold")
    s.text(A_X+EX+15*PITCH, 54.2, "A last element", 3.0, "middle", "#b02020")
    s.text(B_X+EX, 54.2, "B first element", 3.0, "middle", "#b02020")
    s.dim_h(A_X+EX+15*PITCH, B_X+EX, 50, "15.75 seam", size=3.2)
    s.dim_h(188.402, 193.250, 45, "4.848 gap", size=3.1)
    s.dim_v(A_Y+EY, B_Y+EY, 202.0, "5.25", size=3.1)
    s.text(179, 55.4, "5x detail. Board edge x = 188.402 / 193.250.", 2.7)
    s.finish()


def side_view():
    hs, vs = 1.1, 4.0
    x0, z0 = -12, -16
    w, h = 500, 300
    s = SVG(os.path.join(OUT, "design", "side_view_dimensioned.svg"),
            w, h, "Section A-A: interlocking fixture, 30 mm clearance (vertical 4x)", 40, 270)
    s.X = lambda x: 40 + (x-x0)*hs
    s.Y = lambda z: 265 - (z-z0)*vs
    s.sx, s.sy = hs, vs
    s.rect(0, -12, BASE_W, 12, "#333", "#eeeeea", 0.7)
    # 8 corner + 4 mid columns (projected)
    for cx, cy, cw, cd, through in COLUMNS:
        s.rect(cx - cw/2, 0, cw, COL_H, "#777", "#dcdcdc", 0.35)
        if through:
            # head under the base, reusable nut on top of the PCB
            s.line(cx, 31.6, cx, -15, "#333", 0.6)
            s.rect(cx-2.8, 31.6, 5.6, 3.0, "#333", "#aaaaaa", 0.3)
            s.rect(cx-2.8, -15, 5.6, 3.0, "#333", "#aaaaaa", 0.3)
    # boards
    s.rect(A_X, 30, BOARD_W, 1.6, "#0d5a30", "#d8f0df", 0.9)
    s.rect(B_X, 30, BOARD_W, 1.6, "#0d5a30", "#d8f0df", 0.9)
    # 3 mm fences
    s.rect(A_X-3, 0, 3, 32, "#d06010", "#f8d8b8", 0.5)
    s.rect(B_X-3, 0, 3, 32, "#d06010", "#f8d8b8", 0.5)
    for fx in (89.0, 262.25):
        s.rect(fx, 0, 30, 32, "#d06010", "#f8d8b8", 0.5)
    # dims
    s.dim_v(-12, 0, 330, "12 base", size=3.0)
    s.dim_v(0, 30, 330, "30 clearance", size=3.0)
    s.dim_v(30, 31.6, 330, "1.6 PCB", size=3.0)
    s.dim_h(A_X+BOARD_W, B_X, 35, "4.848 gap", size=3.0)
    s.text(5, 39, "Board underside z=30. 8 x M3 x 55; head under base, reusable nut on top. Element faces not modelled.", 2.7)
    s.text(5, 36, "6 x 3 mm fences, 8 mm tab into base; 8 x 10x10 + 4 x 10x6 columns, 10 mm tenon.", 2.7)
    s.text(5, -19, "30 mm ground clearance. Base 12 cast acrylic; fences 3 mm; columns 10 mm; board 1.6 mm (measure).", 2.7)
    s.finish()


# ---- cut profiles --------------------------------------------------------
CUT_FENCES = [(10 + i*40, 245) for i in range(6)]
CUT_CORNER_COLS = [(10 + i*15, 290) for i in range(8)]   # 10 mm sheet
CUT_MID_COLS = [(140 + i*15, 290) for i in range(4)]      # 6 mm sheet
CUT_GAUGES = [("GAP", 10, 335, GAP, 30), ("Y", 30, 335, YOFF, 30),
              ("CLR", 80, 335, 1.848, 30), ("HANDLE", 50, 335, 20, 30)]


def cut_svg():
    s = SVG(os.path.join(OUT, "design", "cut_profiles.svg"),
            600, 400, "Interlocking fixture laser profiles (1:1, mm)", 10, 390)
    s.text(10, 385, "12 mm cast acrylic: BASE 390 x 220 x 12", 4.0, "start", "#111", "bold")
    s.text(10, 235, "3 mm: 6 fences 30 x 40. 10 mm: 8 corner columns 10 x 40. 6 mm: 4 mid columns 10 x 40 + gauges.", 3.2, "start", "#111", "bold")
    # base
    s.rect(10, 20, BASE_W, BASE_H, "#111", "#fbfbfb", 0.6, 8)
    for axis, fixed, centre in FENCES:
        sx, sy, sw, sh = fence_slot(axis, fixed, centre)
        s.rect(10+sx, 20+sy, sw, sh, "#111", "white", 0.4, FENCE_SLOT_R)
    for cx, cy, w, d, through in COLUMNS:
        sx, sy, sw, sh = col_slot(cx, cy, w, d)
        s.rect(10+sx, 20+sy, sw, sh, "#111", "white", 0.4, COL_SLOT_R)
    s.text(10+195, 24, "BASE 390 x 220 x 12, R8 — 18 rounded slots", 3.0, "middle")
    # fences: 30 x 40 blanks
    for i, (x, y) in enumerate(CUT_FENCES):
        s.rect(x, y, 30, 40, "#111", "#fbfbfb", 0.5)
        s.text(x+15, y-2, "FENCE", 2.4, "middle")
    # 8 corner columns on 10 mm sheet; 4 mid columns on 6 mm sheet
    for x, y in CUT_CORNER_COLS:
        s.rect(x, y, 10, 40, "#111", "#fbfbfb", 0.5)
        s.circle(x+5, y+20, BOLT_HOLE/2, "#111", "white", 0.35)
        s.text(x+5, y-2, "COL10", 2.0, "middle")
    for x, y in CUT_MID_COLS:
        s.rect(x, y, 10, 40, "#111", "#fbfbfb", 0.5)
        s.text(x+5, y-2, "COL6", 2.0, "middle")
    # gauges
    for name, x, y, w, h in CUT_GAUGES:
        s.rect(x, y, w, h, "#111", "#fbfbfb", 0.5)
        s.text(x+w/2, y-2, name, 2.4, "middle")
    s.text(10, 10, "Slots: fence 3.05 x 30.05; corner column 10.05 x 10.05; mid column 10.05 x 6.05. Corner column hole 3.4; PCB 3.5; slot corners R1.5 (fence R1.525). Fit 0.05. No glue, no inserts.", 2.4)
    s.finish()


def add_rect(msp, x, y, w, h, layer="CUT"):
    msp.add_lwpolyline([(x, y), (x+w, y), (x+w, y+h), (x, y+h)],
                       close=True, dxfattribs={"layer": layer})


def add_round_rect(msp, x, y, w, h, r, layer="CUT"):
    """Closed rounded rectangle as a single LWPOLYLINE with arc bulges."""
    import math as _m
    b = _m.tan(_m.pi / 8)  # 90 deg arc bulge
    pts = [
        (x + r, y, 0.0),
        (x + w - r, y, b),
        (x + w, y + r, 0.0),
        (x + w, y + h - r, b),
        (x + w - r, y + h, 0.0),
        (x + r, y + h, b),
        (x, y + h - r, 0.0),
        (x, y + r, b),
    ]
    msp.add_lwpolyline(pts, format="xyb", close=True,
                       dxfattribs={"layer": layer})


def new_doc():
    doc = ezdxf.new("R2010")
    doc.units = units.MM
    doc.header["$INSUNITS"] = 4
    for lname, color in [("CUT", 1), ("ENGRAVE", 3)]:
        if lname not in doc.layers:
            doc.layers.add(lname, color=color)
    return doc


def draw_base(msp, x, y):
    w, h, r = BASE_W, BASE_H, 8
    msp.add_line((x+r, y), (x+w-r, y), dxfattribs={"layer": "CUT"})
    msp.add_arc((x+w-r, y+r), r, 270, 360, dxfattribs={"layer": "CUT"})
    msp.add_line((x+w, y+r), (x+w, y+h-r), dxfattribs={"layer": "CUT"})
    msp.add_arc((x+w-r, y+h-r), r, 0, 90, dxfattribs={"layer": "CUT"})
    msp.add_line((x+w-r, y+h), (x+r, y+h), dxfattribs={"layer": "CUT"})
    msp.add_arc((x+r, y+h-r), r, 90, 180, dxfattribs={"layer": "CUT"})
    msp.add_line((x, y+h-r), (x, y+r), dxfattribs={"layer": "CUT"})
    msp.add_arc((x+r, y+r), r, 180, 270, dxfattribs={"layer": "CUT"})
    # fence slots: rounded (stadium) single contours
    for axis, fixed, centre in FENCES:
        sx, sy, sw, sh = fence_slot(axis, fixed, centre)
        add_round_rect(msp, x+sx, y+sy, sw, sh, FENCE_SLOT_R)
    # column slots: rounded single contours.  The corner slot is open through
    # the base, so no separate base through-hole is needed.
    for cx, cy, cw, cd, through in COLUMNS:
        sx, sy, sw, sh = col_slot(cx, cy, cw, cd)
        add_round_rect(msp, x+sx, y+sy, sw, sh, COL_SLOT_R)
    msp.add_text("BASE 390 x 220 x 12 R8 - interlocking", height=4,
                 dxfattribs={"layer": "ENGRAVE"}).set_placement((x+5, y+h+4))


def draw_simple(msp, name, x, y, w, h, holes=()):
    add_rect(msp, x, y, w, h, "CUT")
    for hx, hy, d in holes:
        msp.add_circle((x+hx, y+hy), d/2, dxfattribs={"layer": "CUT"})
    msp.add_text(name, height=2.4, dxfattribs={"layer": "ENGRAVE"}).set_placement((x+1, y-4))


def dxf():
    doc = new_doc(); msp = doc.modelspace()
    draw_base(msp, 0, 0)
    for x, y in CUT_FENCES:
        draw_simple(msp, "FENCE", x, y, 30, 40)
    for x, y in CUT_CORNER_COLS:
        draw_simple(msp, "COL10", x, y, 10, 40, [(5, 20, BOLT_HOLE)])
    for x, y in CUT_MID_COLS:
        draw_simple(msp, "COL6", x, y, 10, 40)
    for name, x, y, w, h in CUT_GAUGES:
        draw_simple(msp, name, x, y, w, h)
    doc.saveas(os.path.join(OUT, "design", "cut_profiles.dxf"))

    doc = new_doc(); msp = doc.modelspace(); draw_base(msp, 0, 0)
    doc.saveas(os.path.join(OUT, "design", "cut_12mm_sheet.dxf"))

    doc = new_doc(); msp = doc.modelspace()
    for x, y in CUT_FENCES:
        draw_simple(msp, "FENCE", x, y, 30, 40)
    doc.saveas(os.path.join(OUT, "design", "cut_3mm_sheet.dxf"))

    doc = new_doc(); msp = doc.modelspace()
    for x, y in CUT_CORNER_COLS:
        draw_simple(msp, "COL10", x, y, 10, 40, [(5, 20, BOLT_HOLE)])
    doc.saveas(os.path.join(OUT, "design", "cut_10mm_sheet.dxf"))

    doc = new_doc(); msp = doc.modelspace()
    for x, y in CUT_MID_COLS:
        draw_simple(msp, "COL6", x, y, 10, 40)
    for name, x, y, w, h in CUT_GAUGES:
        draw_simple(msp, name, x, y, w, h)
    doc.saveas(os.path.join(OUT, "design", "cut_6mm_sheet.dxf"))


def dims_json():
    data = {
        "orientation": "both boards rotated 90 deg CCW in plan",
        "board_width_mm": BOARD_W, "board_height_mm": BOARD_H,
        "pitch_mm": PITCH, "element_x0_mm": EX, "element_y0_mm": EY,
        "seam_mm": SEAM, "y_offset_mm": YOFF, "edge_gap_mm": GAP,
        "board_A_lower_left_mm": [A_X, A_Y],
        "board_B_lower_left_mm": [B_X, B_Y],
        "base_mm": [BASE_W, BASE_H, BASE_T],
        "clearance_mm": CLEARANCE,
        "mounting_holes_rotated": MOUNT,
        "mid_supports_local": MID,
        "connection": "laser tab/slot press fit; only 8 PCB through-bolts",
        "fit_mm": FIT,
        "fences": {
            "body_mm": [FENCE_LEN, FENCE_H, FENCE_T],
            "tab_mm": [FENCE_LEN, FENCE_TAB],
            "blank_mm": [FENCE_LEN, FENCE_BLANK_H],
            "qty": 6,
            "slot_mm": [FENCE_SLOT_L, FENCE_SLOT_W],
        },
        "columns_corner": {
            "cross_section_mm": [COL_W, COL_W],
            "height_above_mm": COL_H,
            "tenon_mm": COL_TENON,
            "blank_mm": [COL_W, COL_BLANK_H],
            "through_hole_mm": BOLT_HOLE,
            "qty": 8,
            "slot_mm": [COL_SLOT, COL_SLOT],
        },
        "columns_mid": {
            "cross_section_mm": [COL_W, COL_D_MID],
            "height_above_mm": COL_H,
            "tenon_mm": COL_TENON,
            "blank_mm": [COL_W, COL_BLANK_H],
            "qty": 4,
            "slot_mm": [COL_SLOT, MID_SLOT],
        },
        "bolts": {
            "spec": "M3 x 55", "qty": 8, "nut": "M3", "washers": 16,
            "base_slot_mm": [COL_SLOT, COL_SLOT],
            "corner_column_hole_mm": BOLT_HOLE,
            "pcb_hole_mm": PCB_HOLE,
        },
        "slot_corner_r_mm": {"fence": FENCE_SLOT_R,
                             "column": COL_SLOT_R,
                             "mid": COL_SLOT_R},
        "datum_faces_mm": {"A_left": A_X, "B_left": B_X,
                           "A_front": A_Y, "B_front": B_Y},
    }
    with open(os.path.join(OUT, "design", "dimensions.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


if __name__ == "__main__":
    top_view(); seam_detail(); side_view(); cut_svg(); dxf(); dims_json()
    print("generated interlocking fixture drawings in", os.path.join(OUT, "design"))
