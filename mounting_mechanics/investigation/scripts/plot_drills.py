#!/usr/bin/env python3
"""Plot drill hits and pick-place centres for visual verification."""
import re
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

root = sys.argv[1]
out = sys.argv[2]

# Pick place
px, py = [], []
for line in open(root + r"\Pick Place for Main.txt", encoding="utf-8", errors="replace"):
    p = line.split()
    if len(p) >= 8 and p[1] == "Transducer_10mm":
        px.append(float(p[2].replace("mil", "")) * 0.0254)
        py.append(float(p[3].replace("mil", "")) * 0.0254)

# Drills
holes = {}
tool = None
x = y = 0.0
for line in open(root + r"\Main.TXT", encoding="ascii", errors="replace"):
    s = line.strip()
    m = re.match(r"^T(\d+)$", s)
    if m:
        tool = int(m.group(1))
        holes.setdefault(tool, [])
        continue
    if tool is None:
        continue
    mx = re.search(r"X(-?\d+)", s)
    my = re.search(r"Y(-?\d+)", s)
    if mx:
        x = int(mx.group(1)) / 1e5 * 25.4
    if my:
        y = int(my.group(1)) / 1e5 * 25.4
    if mx or my:
        holes[tool].append((x, y))

fig, ax = plt.subplots(figsize=(12, 11))
ax.add_patch(Rectangle((0, 0), 185.0921, 168.402, fill=False, lw=1.0, ec="k"))
colors = {1: "0.8", 2: "tab:orange", 3: "tab:green", 4: "tab:red", 5: "tab:purple", 6: "tab:brown"}
for t, pts in holes.items():
    ax.scatter([p[0] for p in pts], [p[1] for p in pts], s=8 if t == 1 else 20,
               c=colors.get(t, "k"), label="T%d n=%d" % (t, len(pts)), alpha=0.8)
ax.scatter(px, py, s=4, c="tab:blue", label="placement centres")
ax.set_xlim(-5, 190)
ax.set_ylim(-5, 175)
ax.set_aspect("equal")
ax.grid(True, lw=0.3)
ax.legend(loc="upper center", ncol=4, fontsize=7)
ax.set_xlabel("x (mm)")
ax.set_ylabel("y (mm)")
ax.set_title("SonicSurface 1.2 drill data and pick-place transducer centres")
fig.tight_layout()
fig.savefig(out, dpi=150)
print("wrote", out)
