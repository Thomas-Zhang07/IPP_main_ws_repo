# FPGA setup cheatsheet — two-board directional speaker

Updated 2026-11-25. Everything here was run on the bench unless marked
"verify".

## 0. Current state

| Item | State |
|---|---|
| Primary firmware | 2026-11-13 carrier-pulse build (`8e44d2e`), JIC `0x1A8AAA16`, flashed 14:38 |
| Secondary firmware | 2026-11-13 SyncTrim build (`0ed0561`), JIC `0x1A8DFE61`, flashed 14:34 |
| Carrier / protocol | 40 kHz, 16 phase bins, 5.12 MHz clock, 38.4 kBaud, 8N1 |
| Sync cable | primary `MISC_D` (PIN_120) → secondary `MISC_A` (PIN_65), common GND |
| Serial ports | primary = CH340 (`1A86:7523`), secondary = FTDI (`0403:6001`) |
| Port numbers | **COM7** = CH340, **COM6** = FTDI on 2026-11-25; were COM8/COM6 on 11-18 |
| Driver state (11-25) | CH340 bound to the bad 3.9.2024.9; FTDI bound to a matched 2.12.36.20 pair |
| Acoustic alignment (11-25) | boards add in phase; best secondary **trim 16** (≈32° correction) |
| Trim after power cycle | resets to **127** — re-send `--trim 16` |

Both boards report the same JTAG IDCODE `020F10DD` and look identical to
`jtagconfig`. Power only the target board when flashing, or double-check the
cable.

## 1. Power

- FPGA core board: **5.0 V**, ~1 A, its own supply/barrel jack.
- SonicSurface array PCB: **12 V** nominal (TC1426 drivers; keep ≤16 V), ~3–4 A.
- Common ground between the two boards — required for both the sync wire and
  the UART.
- The USB-Blaster does **not** power the board; power it separately.
- Set the voltage before connecting. On a bench supply, red = +, black = −;
  green (earth) stays unconnected to the board.

## 2. Pin map (EP4CE6E22C8, from the QSF)

| Net | Pin | Direction / use |
|---|---|---|
| `MISC_A` | `PIN_65` | secondary: sync input |
| `MISC_B` | `PIN_60` | both: UART RX (adapter TX → here) |
| `MISC_C` | `PIN_67` | frame-staging strobe (assigned, not implemented) |
| `MISC_D` | `PIN_120` | primary: sync output; secondary: unused |
| `MISC_E` | `PIN_124` | unused |
| `MISC_F` | `PIN_115` | intended strobe input (not implemented) |

Adapter wiring on both boards: **TX → MISC_B**, **GND → GND**, **RX left
unconnected**. An RX-to-B connection produces no data.

## 3. Flashing the EPCS16 (USB-Blaster)

Tools live in `D:\altera\quartus\bin64\` (not on PATH).

```bash
cd /d/altera/quartus/bin64
jtagconfig
# expect: 1) USB-Blaster [USB-0]   020F10DD   10CL006/10CL010
```

1. Load the factory Serial Flash Loader:

```bash
quartus_pgm -c "USB-Blaster [USB-0]" -m jtag \
  -o "p;D:/altera/quartus/common/devinfo/programmer/sfl_enhanced_01_020f10dd.sof"
```

2. Program the image (`-i` reconfigures from flash afterwards):

```bash
# primary
quartus_pgm -c "USB-Blaster [USB-0]" -m jtag -i \
  -o "p;E:/LUIS/IPP/fpga/primary/QuadrupleBuffer_primary.jic"

# secondary
quartus_pgm -c "USB-Blaster [USB-0]" -m jtag -i \
  -o "p;E:/LUIS/IPP/fpga/secondary/QuadrupleBuffer_secondary.jic"
```

Success looks like: `Device 1 silicon ID is 0x14`, erase, program,
`Successfully performed operation(s)`, and **0 errors**. A direct JIC write
without step 1 fails with `Flash Loader IP not loaded on device 1`.

Regenerate a JIC after a rebuild:

```bash
quartus_cpf -c -d EPCS16 -s EP4CE6 output_files/QuadrupleBuffer.sof <name>.jic
```

## 4. Firmware roles

- **Primary** enables on select byte `0xC0`, disables on `0xC1`.
- **Secondary** is reversed: enables on `0xC1`, disables on `0xC0`.
- Mode bytes `0xC8..0xCB` are decoded **before** the enable check, so a mode
  command changes the mode on every board that hears it.
- Mode values: `0xC8` normal (no modulation), `0xC9` C4, `0xCA` Little Star,
  `0xCB` 200 Hz envelope.
- **Frame:** `0xFE` + 256 payload bytes + `0xFD` = 258 bytes, ~67 ms at
  38.4 kBaud.
- **Payload byte:** low nibble = phase bin 0–15; high nibble = amplitude code
  0–15 (`0` = full scale); `0x10` = transducer OFF.
- **Trim (secondary only):** `0xE0 0x5A N`, `N = 0..255`, **20 ns/step**
  (0.288° at 40 kHz), default **127**, full range 73.4°. Only recognised
  between frames.
- Every frame trailer swaps the current/previous phase registers on **both**
  boards, so each payload must be sent **twice** (the host scripts already do
  this).

## 5. Host commands (from `E:\LUIS\IPP\demo`)

```bash
# list ports
python mode_control.py --list-ports

# set modes on independent links (COM7 = primary, COM6 = secondary on 11-25)
python mode_control.py --port COM7 --board a --mode c4
python mode_control.py --port COM6 --board b --mode c4

# mute / hold the latched frame
python mode_control.py --port COM7 --board a --frame off
python mode_control.py --port COM6 --board b --frame keep

# dual sender, two independent ports
python dual_directional_speaker.py --board-a-port COM7 --board-b-port COM6

# dual sender, one shared UART net (both port-B lines tied)
python dual_directional_speaker.py --bus-port COM7

# trim and trim sweep (secondary); best on 11-25 was 16
python dual_directional_speaker.py --board-a-port COM7 --board-b-port COM6 --trim 16
python dual_directional_speaker.py --board-a-port COM7 --board-b-port COM6 \
  --trim-sweep 0:255:8 --trim-dwell 2

# per-board constant phase shift, in bins (8 bins = 180 deg); not needed on 11-25
python dual_directional_speaker.py --board-a-port COM7 --board-b-port COM6 \
  --board-a-phase-offset 0 --board-b-phase-offset 0
```

Useful geometry/shaping flags: `--seam 0.01575`, `--offset-y 0.00525`,
`--rotation 90`, `--alpha`, `--beta`, `--focus-z 1.5`,
`--amplitude-window {none,hann,gaussian,blackman,tukey}`, `--optimize-sweeps`.
Always try `--dry-run` first.

On a shared bus, the primary also sees the trim value byte; `--bus-port`
automatically filters the unsafe values `150, 151, 192, 193, 200–203, 253`.

## 6. Scope checks

**Sync (no mic, no UART needed):**

- CH1 on primary `MISC_D` (PIN_120), CH2 on secondary `MISC_A` (PIN_65),
  probes at the FPGA pins, 10×, DC, common ground.
- Expect one **~195 ns** pulse every **25.000 µs** (40 kHz) on both.
- CH1→CH2 delay: a few ns. Edge jitter: **<100 ns**, typically a couple of ns.
- No missed or doubled pulses on CH2. `MISC_D` is 2.5 V logic; the secondary
  input threshold is fine.

**Carrier and trim:**

- Probe a transducer driver pad: 40 kHz, 50 % duty.
- Each trim step moves the secondary carrier by **20 ns**; sweep and find the
  minimum inter-board skew (or the 54.75° null once a mic is available).

**Acoustic alignment with a spare transducer (no mic needed):**

- Use a spare 40 kHz transducer as a receiver: one pin to the probe tip, the
  other to the probe ground, **AC coupling, 10× probe, 10–20 mV/div**.
- Fix it on the combined-aperture centre (the seam midpoint), ~0.75–1 m out,
  facing the array. Do not move it between settings.
- Measure Pk-Pk with the primary only, secondary only, and both. If
  `both ≈ primary + secondary` the boards add in phase; if
  `both ≈ |primary − secondary|` they cancel.
- Sweep trim and watch Pk-Pk:
  `dual_directional_speaker.py --board-a-port COM7 --board-b-port COM6
  --trim-sweep 0:255:8 --trim-dwell 2`.
  On 2026-11-25 the peak was **trim 16** (1.88 / 2.72 / 4.40 Vpp at 127).
- Keep the receiver still; only the phase changes. A hand-held receiver is
  usable for a sweep because the peak trim does not depend on position.

**LEDs (from the 11-12 build; verify):**

| LED | Meaning |
|---|---|
| L1 / `LED[0]` | divider heartbeat, ~0.5 Hz |
| L2 / `LED[1]` | `debug_swap`, toggles on every `0xFD` |
| L3 / `LED[2]` | board enable (on when its select byte is active) |
| L4 / `LED[3]` | shift-clock enable |

## 7. Drivers and port identity

- `pnputil /enum-drivers` → check for `ch341ser` **3.9.2024.9** (known-bad on
  this machine) and for FTDI `ftdibus`/`ftdiport` versions.
- `Get-CimInstance Win32_PnPSignedDriver | ? DeviceName -match 'CH34|USB Serial'`
  → shows the version each half actually bound.
- FTDI bus and port must be the **same** version. A mixed pair (2.12.36.20 bus
  + 2.12.28.0 port) caused a `0x139` crash on 2026-11-18.
- CH340 driver 3.9.2024.9 caused `0x50`/`0x139` blue screens. If it is used:
  plug both adapters in **before** starting, do not hot-plug during a run, and
  prefer short commands over long streams.
- Identify the ports by VID/PID or by sending a distinct mode and listening:
  CH340 = `1A86:7523` (**COM7** on 2026-11-25), FTDI = `0403:6001`
  (**COM6**). Re-check after every Windows update. Distinguish boards with
  **Little Star on one port alone**, not two steady tones.

## 8. Troubleshooting

| Symptom | Check |
|---|---|
| `jtagconfig`: "No JTAG hardware available" | cable, USB port, board powered; try another USB port |
| `Flash Loader IP not loaded on device 1` | run the SFL step first |
| No `MISC_D` pulse | wrong image on that board, or it did not boot; reflash, then power-cycle |
| No COM port | driver missing or wrong; Device Manager, replug once, re-check VID/PID |
| Both boards respond on one port | the two port-B lines are tied; use `--bus-port` |
| Only one board responds | select polarity: primary `0xC0`, secondary `0xC1` |
| Mode changes but no sound | send the frame again with `--frame on` |
| Secondary not locking | `MISC_D`→`MISC_A` wire, common ground, pulse present at the secondary pin |
| Port number changed | re-identify by VID/PID; Windows reassigns after updates/replugs |

## 9. File paths

```
fpga/primary/QuadrupleBuffer_primary.jic       0x1A8AAA16
fpga/secondary/QuadrupleBuffer_secondary.jic   0x1A8DFE61
fpga/primary/output_files/QuadrupleBuffer.sof
fpga/secondary/output_files/QuadrupleBuffer.sof
D:/altera/quartus/bin64/{quartus_pgm,quartus_cpf,jtagconfig}.exe
D:/altera/quartus/common/devinfo/programmer/sfl_enhanced_01_020f10dd.sof
demo/                                          host scripts
measurement/prompt_2026-11-24.md               measurement-session brief
```

## 10. Do-not list

- Do not flash without confirming which board the USB-Blaster is on — same
  IDCODE on both.
- Do not hot-plug a USB serial adapter during a streaming run.
- Do not connect the adapter RX to `MISC_B`.
- Do not trust the port numbers from an earlier session; re-identify them.
- Do not leave the array driving at full power unattended; it heats.
