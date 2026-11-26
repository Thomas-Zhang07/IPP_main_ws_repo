# Two-board sensitivity to mechanical error

Date: 2026-11-23
Workspace: `E:\LUIS\IPP\sound_wave_sim_figures`
Basis: `sim/optimize.evaluate` (fast exact coplanar model), 512 elements,
40 kHz, λ = 8.575 mm, 10 mm piston elements, uniform phase, ideal model.

## Question

The 2-board search found a pair at seam 16.54 mm / offset 5.25 mm with a
0.7 dB lower 50–60° band peak than the current 15.75 / 5.25 pair. Is that
difference real, or inside the mechanical tolerance of the fixture?

## Method

Each configuration is evaluated on the same direction-cosine grid as the
figures (`du = 0.004`). Metrics:

- **band peak** — maximum level in the 50–60° elevation band, dB re main peak
- **DI** — directivity index over the forward hemisphere
- **exact lobe** — level at the four axial 54.75° directions
- **band energy** — share of forward power in 50–60°
- **leak >60°** — share of forward power above 60°

Reproduce with:

```python
import optimize
r = optimize.evaluate({"kind": "pair", "seam": 0.01575,
                       "offset": 0.00525, "taper": "uniform"})
```

## Seam sweep (offset fixed at 5.25 mm)

| seam (mm) | band peak (dB) | DI (dB) | exact 54.75° lobe (dB) | band energy | leak >60° |
|---|---|---|---|---|---|
| 13.75 (−2) | −13.29 | 38.50 | −17.8 | 23.89 % | 0.69 % |
| 14.75 (−1) | −13.88 | 38.50 | −23.4 | 23.59 % | 0.73 % |
| **15.75 (current)** | **−14.69** | **38.50** | **null** | **23.37 %** | **0.74 %** |
| 16.75 (+1) | −15.24 | 38.51 | −23.4 | 23.31 % | 0.72 % |
| 17.75 (+2) | −14.32 | 38.51 | −17.8 | 23.40 % | 0.66 % |

## Offset sweep (seam fixed at 15.75 mm)

| y offset (mm) | band peak (dB) | DI (dB) | exact 54.75° lobe (dB) | band energy | leak >60° |
|---|---|---|---|---|---|
| 3.25 (−2) | −13.72 | 38.51 | −17.8 | 23.36 % | 0.74 % |
| 4.25 (−1) | −14.45 | 38.50 | −23.4 | 23.37 % | 0.74 % |
| **5.25 (current)** | **−14.69** | **38.50** | **null** | **23.37 %** | **0.74 %** |
| 6.25 (+1) | −14.49 | 38.50 | −23.4 | 23.37 % | 0.74 % |
| 7.25 (+2) | −13.75 | 38.51 | −17.8 | 23.37 % | 0.74 % |

## Combined ±2 mm box (5 × 5 grid)

| quantity | range over the box |
|---|---|
| band peak | −15.24 … −13.29 dB |
| DI | 38.50 … 38.51 dB |
| exact 54.75° lobe | null at (0, 0); −17.8 … −23.4 dB elsewhere |
| band energy | 23.29 … 23.90 % |
| leak >60° | 0.66 … 0.74 % |
| combinations with lobe < −40 dB | 1 of 25 (the nominal point only) |

## Interpretation

- **Directivity is unaffected** by any error in the ±2 mm box (38.50–38.51 dB).
  The mechanical tolerance does not change how directional the pair is.
- **The band peak moves by ~2 dB across ±2 mm and ≤0.6 dB across ±1 mm.**
  The 0.7 dB advantage of the 16.54 mm seam is inside this scatter, so the
  two geometries are not distinguishable in hardware. The current 15.75 /
  5.25 pair is effectively optimal on the robust metrics.
- **The exact null is the only sensitive quantity.** It exists only at the
  nominal geometry. 1 mm of seam or offset error raises it to about −23 dB;
  2 mm to about −18 dB. That is still 10–15 dB below a butted pair's lobe,
  but it is no longer a null.

## Trim coverage

The secondary board's trim is 0–255 steps × 20 ns = 5.1 µs = **73.4°** of
carrier phase at 40 kHz.

At the grating direction, a seam error of 1 mm changes the inter-board phase
by `2π × 1 mm / 10.5 mm = 34.3°`. So:

- ±1 mm seam error needs ±34°, well inside the trim range.
- ±2 mm needs ±69°, just inside the 73.4° range.

The trim can therefore restore the 54.75° null for a seam error up to about
2 mm. Two cautions:

1. The trim is one inter-board phase. The x-axis lobes (φ = 0/180°) depend on
   the **seam**, the y-axis lobes (φ = 90/270°) on the **offset**. If both have
   errors, one trim cannot null both families simultaneously; tune for the
   axis that matters (the report tunes the 54.75° lobe).
2. The trim cannot fix the *angle* of a lobe, only its depth at a chosen
   direction. Band metrics (peak, energy) are the acceptance numbers; the
   null is a tuning result.

## Recommended specification

| requirement | tolerance |
|---|---|
| Directivity / band peak target (±0.5 dB) | ±1 mm on seam and offset |
| Reproducible 54.75° null without relying on trim | ±0.5 mm |
| Null recoverable by trim | ±2 mm (seam), with the caveat above |

## Caveat

Ideal model: no phase errors, no failed elements, no amplitude quantisation,
rigid-baffle piston elements. Real hardware will add scatter of the same order
as the 0.5–1 dB differences discussed here. The separate Monte Carlo
(`figures/tolerance.png`) covers phase, gain and sound-speed drift.
