#!/usr/bin/env python3
"""Single-column netlist waveform: the pre-fix PulseExpander bug.

Signals come from the VCD written by tb_top while running the
simulation/modelsim/QuadrupleBuffer.vho netlist (the same build the
teammate used).  Time is aligned on the 0xFD swap.
"""
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

from plot_netlist import (parse_vcd, find, find_bits, bus_from_bits,
                          series, draw, shifted, INK, MUTED, ACCENT, SURFACE)


def rise(data):
    t, v = data
    for i in range(1, len(v)):
        if v[i - 1] == 0 and v[i] == 1:
            return t[i]
    return t[0]


def extend_to(data, x_end):
    """A VCD only records changes; draw the last value through the window."""
    if not data:
        return data
    t, v = list(data[0]), list(data[1])
    if t and t[-1] < x_end:
        t.append(x_end)
        v.append(v[-1])
    return t, v


def main():
    vcd, out = sys.argv[1], sys.argv[2]
    vars_, ch = parse_vcd(vcd)

    sig = {
        "swap_out": series(vars_, ch, find(vars_, "s_swap_out~q")),
        "swap_exp": series(vars_, ch, find(vars_, "inst|s_pulse_out~q")),
        "swap_e": series(vars_, ch, find(vars_, "inst5|s_signal_out~q")),
        "cur0": bus_from_bits(ch, find_bits(vars_, "insts:0:PhaseLine_inst|s_phaseCurrent")),
        "data0": series(vars_, ch, find(vars_, "data", "[0]")),
    }

    t0 = rise(sig["swap_out"])
    span = 220.0
    sig = {k: extend_to(shifted(v, t0), span) for k, v in sig.items()}

    rows = [
        ("swap_out", "swap_out", False),
        ("swap_exp", "swap_exp", False),
        ("swap_e", "swap_e", False),
        ("cur0", "s_phaseCurrent[0]", True),
        ("data0", "DATA(0)", False),
    ]

    fig = plt.figure(figsize=(13.5, 8.6), facecolor=SURFACE)
    gs = GridSpec(len(rows), 1, figure=fig, hspace=0.18,
                  left=0.105, right=0.985, top=0.90, bottom=0.08)

    for r, (key, label, bus) in enumerate(rows):
        ax = fig.add_subplot(gs[r, 0])
        draw(ax, sig[key], bus=bus, color=INK, label=label)
        ax.set_xlim(0, span)
        if r != len(rows) - 1:
            ax.set_xticklabels([])

    fig.text(0.105, 0.958,
             "PRE-FIX NETLIST  —  tb_top, frame ending in 0xFD",
             fontsize=12, color=ACCENT, va="top")
    fig.text(0.105, 0.928,
             "swap_exp dips 1 clock every 17 CLK_8 (3.32 us)  ->  swap_e gets a rising edge every 26.56 us\n"
             "->  s_phaseCurrent flips 16 <-> 0  ->  DATA(0) keeps toggling  (tb_top FAIL: 8 edges, expected 0)",
             fontsize=9, color=MUTED, va="top", linespacing=1.4)
    fig.text(0.105, 0.045, "time after the 0xFD swap (us)", fontsize=9, color=MUTED)

    fig.savefig(out, dpi=160, facecolor=SURFACE)
    print("wrote", out)


if __name__ == "__main__":
    main()
