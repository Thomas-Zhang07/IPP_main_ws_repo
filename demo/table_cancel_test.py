#!/usr/bin/env python3
"""Temporarily cancel the FPGA phase table for a two-board scope test.

The firmware drives  drive = (command + PHASE_CORRECTION[wire]) mod 16.
To make the FPGA output exactly the commanded phase, pre-subtract the table:
    command = (desired - table[wire]) mod 16

This sends an all-on frame with every channel commanded to phase 0 *after*
correction (so the command bytes are 0 or 8), to both boards:
    primary port   -> select 0xC0
    secondary port -> select 0xC1

The table is read from the current `fpga/primary/src/Distribute.vhd` (the
primary and secondary tables are identical as of 2026-11-25).

Examples:
    python table_cancel_test.py --dry-run
    python table_cancel_test.py --port-a COM7 --port-b COM6
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

DEMO = Path(__file__).resolve().parent
sys.path.insert(0, str(DEMO))

import protocol  # noqa: E402

DISTRIBUTE = DEMO.parent / "fpga" / "primary" / "src" / "Distribute.vhd"


def read_table(path):
    """Return the first 256-entry phase table line in the file."""
    text = Path(path).read_text(encoding="utf-8", errors="ignore")
    for line in text.splitlines():
        if line.count(",") < 100:
            continue
        values = [int(v) for v in re.findall(r"\d+", line)][:256]
        if len(values) == 256:
            return values
    raise ValueError(f"no 256-entry table found in {path}")


def build_payload(table, desired=0):
    """All channels ON (amplitude 0 = full) with the table pre-subtracted."""
    phases = [(desired - t) % 16 for t in table]
    return bytes([protocol.HEADER]) + bytes(phases) + bytes([protocol.FOOTER])


def send(port, select, mode, payload, repeats=2):
    with protocol.open_serial(port) as conn:
        conn.write(bytes([mode]))
        conn.flush()
        for _ in range(repeats):
            conn.write(bytes([select]) + payload)
            conn.flush()
    return len(payload) * repeats + 1


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--port-a", help="primary port (select 0xC0)")
    p.add_argument("--port-b", help="secondary port (select 0xC1)")
    p.add_argument("--table-file", default=str(DISTRIBUTE))
    p.add_argument("--mode", type=int, default=0xC8,
                   help="0xC8 normal (default), 0xC9 C4, 0xCA Little Star, 0xCB 200 Hz")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)

    table = read_table(args.table_file)
    payload = build_payload(table)
    print(f"table: {args.table_file}")
    print(f"  first 16: {table[:16]}")
    print(f"  entries of 8 (180 deg): {sum(1 for v in table if v == 8)} / 256")
    print(f"  pre-subtracted command, first 16: {list(payload[1:17])}")
    print(f"  frame: {len(payload)} bytes, all channels ON, output phase 0")
    if args.dry_run:
        print("[dry run] nothing sent")
        return 0
    if not args.port_a or not args.port_b:
        print("both --port-a and --port-b are required (or use --dry-run)",
              file=sys.stderr)
        return 2
    n_a = send(args.port_a, 0xC0, args.mode, payload)
    n_b = send(args.port_b, 0xC1, args.mode, payload)
    print(f"sent {n_a} B to {args.port_a} (0xC0) and {n_b} B to {args.port_b} (0xC1)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
