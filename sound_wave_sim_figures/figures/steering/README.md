# Steering study — all candidate arrangements

Seven setups, each steered in x with a continuous linear phase ramp from
0° to 70° in 5° steps, in two element models.

| Setup dir | Layout |
|---|---|
| `01_single` | one board, broadside |
| `03_v120` | two boards, V 120° |
| `02_v150` | two boards, V 150° |
| `05_coplanar_gap` | current pair, 15.75 mm seam / 5.25 mm y offset |
| `09_pair_seam_only` | same seam, y offset 0 (control) |
| `07_concave3` | three boards, concave, wings 30° |
| `08_coplanar3` | three boards, coplanar, current seams |

Element models:

- **isotropic** — array factor only; no transducer directivity.
- **measured** — the digitized TR4010HC pattern, evaluated per element against
  that element's own board normal (tilted boards tilt their element patterns).

V120 and V150 steer using `exp(−i k (u₀x + v₀y + w₀z))`, where the
forward command is a unit vector. This cancels the propagation phase in
that direction even when emitter heights differ. Flat boards at z = 0
reduce to the original x/y ramp. The 3-board concave setup retains its
projected drive as a control. The CSVs label the drive in `phase_law`.
The equal-phase baseline galleries are a separate experiment, not this drive.

## Files

```
<setup>/{isotropic,measured}/{3d,polar,uv}/steer_XX.png   one image per angle
<setup>/amplitude/steer_XX.png                            both cases overlaid
<setup>/summary/*.png                                     four charts
<setup>/metrics.csv
summary_all/*.png                                         cross-layout, measured
metrics_all.csv
```

Every image holds one plot; there are no montages.

The images and CSVs for all seven layouts use the shared normalization.
V120 and V150 include the depth correction described above.

## Metric definitions

- **Main beam** — the local maximum in the x–z cut within ±12° of the
  commanded steering angle. The 0 dB reference is the largest sample across
  the UV grid, fine x–z cut and 3D mesh together, not a continuous maximum.
- **Strongest sidelobe** (CSV column name) — largest sample outside a
  15° cone around the main-beam direction. Reported with its elevation and
  azimuth, and relative to the same global peak.

For the measured single board at broadside these are three distinct features:
the ordinary first sidelobe near 4° (inside the mask), the strongest sample
outside 15° (−24.1 dB at 16.25°), and the level at the axial first-order
grating direction (−28.2 dB at 54.75°). The fixed ring is a *broadside*
reference, not a prediction of a steered lobe's position.

With a broadside command the corrected V120 and V150 both peak at 0°.
The strongest sample outside 15° is −4.8 and −8.3 dB respectively with the
datasheet-based element model. Compensation does not remove grating lobes:
at a 20° command the margins are just 0.24 and 4.72 dB. A coherent command
need not be the strongest direction once element directivity is included.

## What a microphone at 2 m measures

The steering plots use a plane-wave limit. Moving a microphone does not
change the drive. For a 40 kHz receiver at (0, 0, 2 m), measured from the
hinge on the array's horizontal centerline, `v_microphone_2m.csv` instead
sums spherical paths for the **same broadside drive** and element model:

| Layout | Residual path spread beyond plane-wave model | Phase spread | Pressure relative to fully coherent sum at this mic |
|---|---:|---:|---:|
| V120 | 6.78 mm | 285° | −7.65 dB |
| V150 | 7.88 mm | 331° | −10.47 dB |

The last column compares each layout to its **own** sum of individual
pressure magnitudes at the mic; it is not a comparison of absolute SPL,
a measured loss, or a change to the drive. Focusing at 2 m would be a
different experiment. A different mic position needs its own path calculation.

## Reproduce

```powershell
python sim/steering_study.py    # ~7 minutes, writes everything above
python sim/steering_study.py --phase-law projected_xy --out old-drive-control
```
