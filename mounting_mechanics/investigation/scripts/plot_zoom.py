#!/usr/bin/env python3
"""Zoomed plot of the first transducer rows to verify pin offsets and pitch."""
import re
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

root = sys.argv[1]
out = sys.argv[2]
rows = []
for line in open(root + r"\Pick Place for Main.txt", encoding="utf-8", errors="replace"):
    p = line.split()
    if len(p) >= 8 and p[1] == "Transducer_10mm":
        rows.append((float(p[2].replace("mil", "")) * 0.0254,
                     float(p[3].replace("mil", "")) * 0.0254))
holes = []
tool = None
x = y = 0.0
for line in open(root + r"\Main.TXT", encoding="ascii", errors="replace"):
    s = line.strip()
    m = re.match(r"^T(\d+)$", s)
    if m:
        tool = int(m.group(1))
        continue
    if tool != 4:
        continue
    mx = re.search(r"X(-?\d+)", s)
    my = re.search(r"Y(-?\d+)", s)
    if mx:
        x = int(mx.group(1)) / 1e5 * 25.4
    if my:
        y = int(my.group(1)) / 1e5 * 25.4
    if mx or my:
        holes.append((x, y))

fig, ax = plt.subplots(figsize=(14, 6))
ax.scatter([h[0] for h in holes], [h[1] for h in holes], s=50, c="tab:red",
           label="T4 drill holes (literal 2:5 parse)")
ax.scatter([p[0] for p in rows], [p[1] for p in rows], s=30, c="tab:blue",
           label="placement centres")
for i, (x0, y0) in enumerate(sorted(rows)[:8]):
    ax.annotate("%.3f" % x0, (x0, y0), textcoords="offset points", xytext=(0, 8),
                fontsize=8, color="tab:blue")
ax.set_xlim(0, 55)
ax.set_ylim(0, 30)
ax.set_aspect("equal")
ax.grid(True, lw=0.4)
ax.legend()
fig.tight_layout()
fig.savefig(out, dpi=180)
print("wrote", out)
