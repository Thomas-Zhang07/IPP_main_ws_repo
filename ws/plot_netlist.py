#!/usr/bin/env python3
"""Plot the PulseExpander bug at netlist level: pre-fix vs fixed netlist.

Reads the two VCDs produced by tb_top (4 ms run) and draws the post-frame
window, aligned on the 0xFD swap:
    swap_out    Distribute output (held high after 0xFD)
    swap_exp    PulseExpander output
    swap_e      LatchBuffer output -> PhaseLine.swap
    current[0]  PhaseLine ch0 s_phaseCurrent
    DATA(0)     practical symptom (channels 0..7 asked to turn off)
"""
import re
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

INK = "#1f2a44"
MUTED = "#8a94a6"
ACCENT = "#c0392b"
SURFACE = "#ffffff"


def parse_vcd(path):
    variables, changes = {}, {}
    t = 0
    with open(path, "r", errors="replace") as fh:
        for raw in fh:
            line = raw.strip()
            if not line:
                continue
            if line.startswith("$var"):
                parts = line.split()
                width = int(parts[2])
                ident = parts[3]
                name = " ".join(parts[4:-1]) if parts[-1] == "$end" else " ".join(parts[4:])
                variables[ident] = (name, width)
                changes.setdefault(ident, [])
            elif line.startswith("$"):
                continue
            elif line.startswith("#"):
                t = int(line[1:])
            elif line[0] in "01xzXZ":
                changes.setdefault(line[1:], []).append((t, line[0]))
            elif line[0] in "bB":
                parts = line.split()
                changes.setdefault(parts[1], []).append((t, parts[0][1:]))
    return variables, changes


def find(variables, *needles):
    for ident, (name, _) in variables.items():
        if all(n in name for n in needles):
            return ident
    return None


def find_bits(variables, *needles):
    """Map bit index -> id for a vector that Questa split into 1-bit vars."""
    out = {}
    for ident, (name, _) in variables.items():
        if all(n in name for n in needles):
            m = re.search(r"\[(\d+)\]\s*$", name)
            if m:
                out[int(m.group(1))] = ident
    return out


def bus_from_bits(changes, bits):
    if not bits:
        return None
    width = max(bits) + 1
    lists = {b: changes.get(ident, []) for b, ident in bits.items()}
    times = sorted({t for lst in lists.values() for t, _ in lst})
    vals = [0] * width
    ptr = {b: 0 for b in lists}
    out_t, out_v = [], []
    for t in times:
        for b, lst in lists.items():
            while ptr[b] < len(lst) and lst[ptr[b]][0] <= t:
                val = lst[ptr[b]][1]
                vals[b] = 0 if val.lower() in "xz" else int(val)
                ptr[b] += 1
        out_t.append(t / 1e6)
        out_v.append(sum(vals[b] << b for b in range(width)))
    tt, vv = [], []
    for t, v in zip(out_t, out_v):
        if not vv or vv[-1] != v:
            tt.append(t)
            vv.append(v)
    return tt, vv


def bits_to_int(text):
    return int(text.lower().replace("x", "0").replace("z", "0"), 2) if text else 0


def series(variables, changes, ident, bus=False):
    if ident is None:
        return None
    times, values = [], []
    for t, val in changes.get(ident, []):
        if bus:
            v = bits_to_int(val)
        else:
            v = 0 if val.lower() in "xz" else int(val)
        times.append(t / 1e6)  # ps -> us
        values.append(v)
    return times, values


def draw(ax, data, bus=False, color=INK, label=""):
    if not data:
        ax.text(0.5, 0.5, f"{label}: not found", transform=ax.transAxes,
                ha="center", va="center", color=MUTED, fontsize=9)
        return
    t, v = data
    if bus:
        # step draw with value labels at the middle of each segment
        ax.step(t, v, where="post", color=color, linewidth=1.6)
        start = 0
        for i in range(1, len(t) + 1):
            end = t[i] if i < len(t) else t[-1]
            if end > start:
                mid = (start + end) / 2
                ax.text(mid, v[i - 1] + 0.6, str(v[i - 1]), ha="center",
                        va="bottom", fontsize=8.5, color=INK)
            start = end
        lo, hi = min(v), max(v)
        ax.set_ylim(lo - 2, hi + 3)
        ax.set_yticks([])
    else:
        ax.step(t, v, where="post", color=color, linewidth=1.4)
        ax.set_ylim(-0.25, 1.35)
        ax.set_yticks([0, 1])
        ax.set_yticklabels(["0", "1"], fontsize=8, color=MUTED)
    ax.set_xlim(left=0)
    ax.grid(True, axis="x", color="#e6e9ef", linewidth=0.8)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color("#d5d9e0")
    ax.tick_params(axis="x", colors=MUTED, labelsize=8)
    ax.set_ylabel(label, rotation=0, ha="right", va="center", fontsize=9, color=INK)


def shifted(data, t0):
    if not data:
        return data
    return [t - t0 for t in data[0]], data[1]


def main():
    old_vcd, new_vcd, out = sys.argv[1], sys.argv[2], sys.argv[3]
    oldv, oldc = parse_vcd(old_vcd)
    newv, newc = parse_vcd(new_vcd)

    def bundle(vars_, ch):
        return {
            "swap_out": series(vars_, ch, find(vars_, "s_swap_out~q")),
            "swap_exp": series(vars_, ch, find(vars_, r"inst|s_pulse_out~q")),
            "swap_e": series(vars_, ch, find(vars_, r"inst5|s_signal_out~q")),
            "current0": bus_from_bits(ch, find_bits(vars_, "insts:0:PhaseLine_inst|s_phaseCurrent")),
            "current1": bus_from_bits(ch, find_bits(vars_, "insts:1:PhaseLine_inst|s_phaseCurrent")),
            "data0": series(vars_, ch, find(vars_, "data", "[0]")),
            "data1": series(vars_, ch, find(vars_, "data", "[1]")),
        }

    old = bundle(oldv, oldc)
    new = bundle(newv, newc)

    # Align on the rising edge of swap_out (the 0xFD swap).
    def rise_time(data):
        if not data:
            return 0.0
        t, v = data
        for i in range(1, len(v)):
            if v[i - 1] == 0 and v[i] == 1:
                return t[i]
        return t[0]

    t0 = rise_time(old["swap_out"])
    t0_new = rise_time(new["swap_out"])
    span = 220.0  # us after the swap

    old = {k: shifted(v, t0) for k, v in old.items()}
    new = {k: shifted(v, t0_new) for k, v in new.items()}

    rows = [
        ("swap_out", "swap_out", False),
        ("swap_exp", "swap_exp", False),
        ("swap_e", "swap_e", False),
        ("current0", "s_phaseCurrent[0]", True),
        ("data0", "DATA(0)", False),
    ]

    fig = plt.figure(figsize=(13.5, 8.2), facecolor=SURFACE)
    gs = GridSpec(len(rows), 2, figure=fig, hspace=0.18, wspace=0.06,
                  left=0.10, right=0.99, top=0.90, bottom=0.08)

    axes = {}
    captions = [
        "swap_exp dips 1 clock every 17 CLK_8 (3.32 us)  ->  swap_e repeats every 26.56 us\n"
        "->  phase flips 16 <-> 0  ->  DATA(0) never goes quiet",
        "swap_exp stays high  ->  one swap for the frame\n"
        "->  phase holds 16  ->  DATA(0) quiet",
    ]
    titles = [
        "BEFORE FIX  —  simulation/modelsim/QuadrupleBuffer.vho",
        "AFTER FIX  —  simulation/questa/QuadrupleBuffer.vho",
    ]
    for col, (data, title) in enumerate([(old, titles[0]), (new, titles[1])]):
        for r, (key, label, bus) in enumerate(rows):
            ax = fig.add_subplot(gs[r, col])
            axes[(r, col)] = ax
            draw(ax, data[key], bus=bus, color=INK, label=label)
            ax.set_xlim(0, span)
            if col == 1:
                ax.set_yticklabels([])
            if r != len(rows) - 1:
                ax.set_xticklabels([])
        fig.text(0.10 + 0.45 * col, 0.955, title, fontsize=11,
                 color=ACCENT if col == 0 else INK, va="top")
        fig.text(0.10 + 0.45 * col, 0.925, captions[col], fontsize=8.8,
                 color=MUTED, va="top", linespacing=1.4)

    fig.text(0.10, 0.045, "time after the 0xFD swap (us)", fontsize=9, color=MUTED)

    fig.savefig(out, dpi=160, facecolor=SURFACE)
    print("wrote", out)


if __name__ == "__main__":
    main()
