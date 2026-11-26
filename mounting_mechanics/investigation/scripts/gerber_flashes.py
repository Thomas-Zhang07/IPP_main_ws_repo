#!/usr/bin/env python3
"""Extract flashed pad/annulus centres from a Gerber layer by aperture code.

Only D03 flashes are recorded. Modal X/Y are supported. Coordinates are
%FSLAX25Y25*% inches, so 5 decimal digits.
"""
import collections
import re
import sys

path = sys.argv[1]
want = set(sys.argv[2:])
text = open(path, encoding="utf-8", errors="replace").read()
# Split on extended commands while retaining normal words.
flashes = collections.defaultdict(list)
ap = None
x = y = 0.0
for line in text.splitlines():
    s = line.strip()
    if s == "D03*":
        flashes[ap].append((x, y))
        continue
    m = re.match(r"^D(\d+)\*$", s)
    if m:
        ap = "D" + m.group(1)
        continue
    mx = re.search(r"X(-?\d+)", s)
    my = re.search(r"Y(-?\d+)", s)
    if mx:
        x = int(mx.group(1)) / 100000.0
    if my:
        y = int(my.group(1)) / 100000.0
print("apertures with flashes:")
for a, pts in sorted(flashes.items(), key=lambda kv: int(kv[0][1:])):
    print("  %s n=%d" % (a, len(pts)))
for a in sorted(want, key=lambda v: int(v[1:])):
    pts = flashes.get(a, [])
    print("\n%s: n=%d" % (a, len(pts)))
    if not pts:
        continue
    xs = [p[0] * 25.4 for p in pts]
    ys = [p[1] * 25.4 for p in pts]
    print("  extents x %.3f..%.3f y %.3f..%.3f mm" % (min(xs), max(xs), min(ys), max(ys)))
    ux = sorted(set(round(v, 3) for v in xs))
    uy = sorted(set(round(v, 3) for v in ys))
    print("  unique x %d: %s" % (len(ux), ux[:40]))
    print("  unique y %d: %s" % (len(uy), uy[:40]))
    print("  first 10: %s" % [(round(a, 3), round(b, 3)) for a, b in zip(xs, ys)][:10])
