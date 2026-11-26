#!/usr/bin/env python3
"""Read the existing SonicSurface laser-cut spacer SVG as a cross-check.

The SVG is 2D data from the original mechanical design. It is read, never
executed. Prints circle extents/pitch and path bounding boxes in SVG units.
"""
import re
import sys
import xml.etree.ElementTree as ET

path = sys.argv[1]
text = open(path, encoding="utf-8", errors="replace").read()
root = ET.fromstring(text)
ns = {"svg": "http://www.w3.org/2000/svg"}

circles = []
for c in root.findall(".//svg:circle", ns):
    transform = c.get("transform")
    cx = float(c.get("cx", 0))
    cy = float(c.get("cy", 0))
    r = float(c.get("r", 0))
    parent = c
    circles.append((cx, cy, r))

xs = [c[0] for c in circles]
ys = [c[1] for c in circles]
rs = [c[2] for c in circles]
print("circles:", len(circles))
if circles:
    print("x %.3f..%.3f span %.3f" % (min(xs), max(xs), max(xs) - min(xs)))
    print("y %.3f..%.3f span %.3f" % (min(ys), max(ys), max(ys) - min(ys)))
    print("radii:", sorted(set(round(r, 4) for r in rs)))
    ux = []
    for v in sorted(set(round(v, 3) for v in xs)):
        if not ux or v - ux[-1] > 0.01:
            ux.append(v)
    uy = []
    for v in sorted(set(round(v, 3) for v in ys)):
        if not uy or v - uy[-1] > 0.01:
            uy.append(v)
    print("unique x (%d): %s" % (len(ux), ux[:50]))
    print("unique y (%d): %s" % (len(uy), uy[:50]))
    dx = [round(b - a, 4) for a, b in zip(ux, ux[1:])]
    dy = [round(b - a, 4) for a, b in zip(uy, uy[1:])]
    print("x steps:", sorted(set(dx))[:20])
    print("y steps:", sorted(set(dy))[:20])
    # Large circles (not transducer holes) likely mounting/standoff holes.
    print("large circles:")
    for c in circles:
        if c[2] >= 2.0:
            print("  cx=%.3f cy=%.3f r=%.3f" % c)

# Path bounding boxes from the path 'd' numbers. This only supports absolute
# command coordinates as used by this Inkscape export.
for i, p in enumerate(root.findall(".//svg:path", ns)):
    d = p.get("d", "")
    nums = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", d)]
    if not nums:
        continue
    # Alternating x/y is a reasonable approximation for this drawing.
    px = nums[0::2]
    py = nums[1::2]
    print("path %d: x %.3f..%.3f y %.3f..%.3f n=%d" %
          (i, min(px), max(px), min(py), max(py), len(nums) // 2))
