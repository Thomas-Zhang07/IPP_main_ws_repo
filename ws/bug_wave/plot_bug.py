#!/usr/bin/env python3
"""Parse a VCD from the buggy tb_glue run and plot the relevant signals."""
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def parse_vcd(path):
    variables = {}
    changes = {}
    t = 0
    with open(path, "r", errors="replace") as fh:
        for raw in fh:
            line = raw.strip()
            if not line:
                continue
            if line.startswith("$var"):
                parts = line.split()
                # $var wire 1 ! name $end
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


def bits_to_int(text):
    text = text.lower().replace("x", "0").replace("z", "0")
    return int(text, 2) if text else 0


def find_ident(variables, wanted, bit=None):
    for ident, (name, width) in variables.items():
        clean = name.lower().replace("(", "[").replace(")", "]")
        if bit is not None:
            if clean.endswith(f"{wanted.lower()}[{bit}]"):
                return ident
        if clean.endswith(wanted.lower()):
            return ident
    return None


def series(variables, changes, wanted, bit=None):
    ident = find_ident(variables, wanted, bit)
    if ident is None:
        return None
    width = variables[ident][1]
    times, values = [], []
    for t, val in changes.get(ident, []):
        if len(val) == 1 and val in "01":
            v = int(val)
        else:
            v = bits_to_int(val)
            if bit is not None:
                v = (v >> bit) & 1
        times.append(t)
        values.append(v)
    if not times:
        return None
    # VCD time is in the simulator resolution (1 ps here); convert to us.
    return [t / 1e6 for t in times], values


def main():
    vcd_path, out_path = sys.argv[1], sys.argv[2]
    variables, changes = parse_vcd(vcd_path)

    specs = [
        ("serial_in", None, "serial_in"),
        ("swap_raw", None, "swap_raw  (Distribute.swap_out, held high)"),
        ("swap_exp", None, "swap_exp  (PulseExpander output -> glitches)"),
        ("swap_e", None, "swap_e    (LatchBuffer output -> repeated edges)"),
        ("music_out", 0, "music_out[0]  (DATA(0))"),
        ("music_out", 1, "music_out[1]  (DATA(1))"),
    ]

    fig, axes = plt.subplots(len(specs), 1, figsize=(15, 10), sharex=True)
    if len(specs) == 1:
        axes = [axes]

    for ax, (name, bit, label) in zip(axes, specs):
        data = series(variables, changes, name, bit)
        if data is None:
            ax.text(0.5, 0.5, f"{label}: not found in VCD", ha="center", va="center",
                    transform=ax.transAxes)
        else:
            times, values = data
            ax.step(times, values, where="post", color="#1f77b4", linewidth=1.2)
            ax.set_ylim(-0.2, 1.4)
            ax.set_yticks([0, 1])
        ax.set_ylabel(label, rotation=0, ha="right", va="center", fontsize=8)
        ax.grid(True, axis="x", alpha=0.3)
        ax.spines[["top", "right"]].set_visible(False)

    axes[-1].set_xlabel("time (us)")
    fig.suptitle("tb_glue with the pre-fix PulseExpander (bug reproduced)", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(out_path, dpi=150)
    print("wrote", out_path)


if __name__ == "__main__":
    main()
