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

Steering is `exp(−i k u₀ x)` across every element of the aperture. No per-board
correction for the board tilt is applied — this is the same steering law for all
setups, so the comparison is like-for-like.

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

## Metric definitions

- **Main beam** — the local maximum in the x–z cut within ±12° of the
  commanded steering angle. Its level is relative to the pattern's global peak.
- **Strongest sidelobe** — the global maximum on the UV hemisphere outside a
  15° cone around the main-beam direction. Reported with its elevation and
  azimuth, and relative to the same global peak.

For the coplanar setups this follows the familiar picture: the commanded beam
holds, and the grating lobe climbs from about −24 dB at broadside to 0 dB once
its direction is within ~25–40° of the beam.

For the tilted setups (V 120°, V 150°) the **strongest lobe is along the board
normals, not at the commanded direction**: the main-beam level chart sits at
−10 … −25 dB while the sidelobe chart sits at 0 dB. That is a real property of
the geometry under a single aperture-wide phase ramp, not a plotting error. The
concave 3-board behaves like the coplanar layouts up to ~40°, then its wings'
lobes dominate.

## Reproduce

```powershell
python sim/steering_study.py    # ~7 minutes, writes everything above
```
