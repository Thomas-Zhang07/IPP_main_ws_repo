#!/usr/bin/env python3
"""Read binary STL files and report bounds; render top/front silhouette views.

Supports the two STL encodings in the SonicSurface Mech folder:
  - STLB ATF ... binary
  - STLEXP Object01 ... header followed by binary triangles (80-byte header)
"""
import os
import struct
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def read_stl(path):
    data = open(path, "rb").read()
    if data[:5] == b"STLB ":
        # 3D Builder binary STL: 80-byte header, uint32 count, 50-byte tris
        n = struct.unpack("<I", data[80:84])[0]
        off = 84
    elif data[:6] == b"STLEXP":
        # STLEXP header is still 80 bytes for binary STL
        n = struct.unpack("<I", data[80:84])[0]
        off = 84
    else:
        n = None
        off = None
    if n is None:
        raise ValueError("not binary STL")
    tris = np.empty((n, 3, 3), dtype=np.float64)
    norms = np.empty((n, 3), dtype=np.float64)
    for i in range(n):
        rec = data[off + i * 50: off + (i + 1) * 50]
        vals = struct.unpack("<12fH", rec)
        norms[i] = vals[0:3]
        tris[i] = np.array(vals[3:12]).reshape(3, 3)
    return tris


def main():
    stl = sys.argv[1]
    out = sys.argv[2]
    tris = read_stl(stl)
    pts = tris.reshape(-1, 3)
    print(os.path.basename(stl), "triangles", len(tris))
    print("bounds x %.3f..%.3f y %.3f..%.3f z %.3f..%.3f" %
          (pts[:, 0].min(), pts[:, 0].max(), pts[:, 1].min(), pts[:, 1].max(),
           pts[:, 2].min(), pts[:, 2].max()))
    print("size %.3f x %.3f x %.3f" %
          (np.ptp(pts[:, 0]), np.ptp(pts[:, 1]), np.ptp(pts[:, 2])))

    fig, axs = plt.subplots(1, 2, figsize=(14, 7))
    # Top view: all triangle edges projected XY
    ax = axs[0]
    for t in tris:
        ax.plot(t[[0, 1, 2, 0], 0], t[[0, 1, 2, 0], 1], lw=0.15, color="0.2")
    ax.set_aspect("equal")
    ax.set_title("XY (top) all edges")
    ax.grid(True, lw=0.3)
    # Front view XZ
    ax = axs[1]
    for t in tris:
        ax.plot(t[[0, 1, 2, 0], 0], t[[0, 1, 2, 0], 2], lw=0.15, color="0.2")
    ax.set_aspect("equal")
    ax.set_title("XZ (front) all edges")
    ax.grid(True, lw=0.3)
    fig.tight_layout()
    fig.savefig(out, dpi=120)
    print("wrote", out)


if __name__ == "__main__":
    main()
