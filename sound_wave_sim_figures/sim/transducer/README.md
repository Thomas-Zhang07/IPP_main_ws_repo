# Transducer directivity — TR4010HC (measured chart)

Measured element directivity for the 10 mm, 40 kHz TR4010HC series
transducer, digitized from the only data available for it: the photographed
datasheet page `../../transducers.jpg`. The sim previously assumed an ideal
10 mm baffled piston; this package carries the real pattern.

## Files

| File | What |
|---|---|
| `digitize.py` | reproduces `directivity.csv` and `overlay.png` from the jpg |
| `directivity.csv` | level vs angle, 0–180°, 0.5° steps: `angle_deg,db_right,db_left,db_mean_power` |
| `overlay.png` | diagnostic: the extracted trace drawn on the chart |
| `directivity.py` | loader and derived quantities |

Regenerate:

```powershell
python sim/transducer/digitize.py
```

## Method

The chart is a photograph, so its geometry is calibrated once and coded as
constants in `digitize.py`: centre (1506, 1820) px, 0 dB ring radius 297 px,
45 px per 6 dB. The light-pink trace is tracked as the largest radius at each
angle; the dark 30° spokes are bridged and the curve is smoothed over 2.25°.
The digitized on-axis value is normalized to 0 dB. The resulting beamwidth is
81.0°, consistent with the datasheet's 80° ±12°.

The chart is a single 360° cut with a visible left/right asymmetry (at 45°
the right side is ~6 dB below the left). The CSV keeps both halves; the
power average is used as the axisymmetric pattern.

## Derived numbers

Standard 4π convention: `Q = 2 / ∫₀^π P(θ) sinθ dθ`, `DI = 10 log₁₀ Q`.

| Quantity | Value |
|---|---|
| DI (power-average pattern) | **11.2 dB** (Q 13.1) |
| DI, right half / left half | 11.8 dB / 10.6 dB |
| −6 dB half-angles | 39.0° (right) / 42.0° (left) |
| −6 dB beamwidth | 81.0° |
| Level at 30° / 45° | −2.7 dB / −12.9 dB |
| Side lobes near 75–80° | −21 … −22 dB |
| Rear (180°) | −36 dB |
| Level at 54.75° (the grating angle) | **≈ −28 dB** |

The last row matters: the ideal piston is −12.8 dB at 54.75°, so the real
element suppresses the grating lobes roughly 15 dB more than the old
assumption. Every 54.75° leak number inherits this.

## Uncertainty

- Digitizing the photographed chart: about ±1 dB on the main lobe, ±2 dB on
  the faint skirt and side lobes.
- The manufacturer's own beam tolerance (80° ±12°) maps to DI 9.4–12.2 dB.
- The steep drop between 42° and 60° is the least certain region of the
  chart (the trace is faint there); treat levels between 50° and 60° with
  ±2–3 dB.
- Only one azimuth plane is available; the axisymmetric use is an
  assumption, not a measurement.

## Use in the simulation

`amplitude(cos β)` is the drop-in replacement for the ideal piston factor in
the far-field sum, evaluated against each element's own board normal:

```python
from transducer import amplitude

field = Σ Aᵢ · amplitude(cos_betaᵢ) · exp(i k u·rᵢ)
```

Differences from the piston model to keep in mind:

- The real element is **not zero behind** (measured ≈ −36 dB). Whether a
  board's baffle blocks the rear is a sim-side assumption, not something
  this package decides.
- The real pattern is **much steeper** beyond 45° than the piston, so
  off-axis and grating-lobe levels will drop substantially.

## Source caveats

- The sheet is a photo, not a PDF; all numbers derived from it carry the
  uncertainty above.
- Two spec revisions of the same family exist: the user's sheet quotes
  105 dB SPL / −73 dB rx / 2000 pF / 80 Vpp, the Shenzhen Yujie page quotes
  120 dB / −63 dB / 2550 pF / 100 Vpp. Both state the same 80° ±12° beam, so
  the directivity work is unaffected; absolute SPL planning should use the
  conservative 105 dB until the physical grade is confirmed.
