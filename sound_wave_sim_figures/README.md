# Sound-wave simulation figures — board layouts

Ideal-model simulation of the 16 × 16 SonicSurface boards (10.5 mm pitch,
40 kHz, λ = 8.575 mm, 10 mm piston elements) arranged in the candidate
layouts, plus a search for the best 2- and 3-board arrangement by leak.

## Run

```powershell
$env:PYTHONIOENCODING="utf-8"
python sim/run_all.py            # full run (baselines + search + optima)
python sim/run_all.py --baselines-only
python -m pytest tests -q        # model validation
```

Outputs:

| Path | What |
|---|---|
| `figures/<key>/farfield.png` | direction-cosine map with angle rings and the 54.75° circle, x–z / y–z Cartesian cuts, board sketch, metrics |
| `figures/<key>/nearfield.png` | x–z, x–y and y–z dB maps plus a zoomed Re(p) wavefront panel |
| `web/<key>/index.html` | rotatable translucent 3D surface with a grating ring, and near-field slice planes; mode toggle on the canvas |
| `web/index.html` | index of all pages |
| `web/overlay.html` | **overlay comparison**: any two layouts, independent opacity |
| `figures/comparison.png` | all layouts, five measures, grouped by board count |
| `figures/pareto.png` | Pareto front: directivity index versus 50–60° band peak |
| `figures/leak_compare.png` | cuts through the x- and y-lobes: why the null is invisible in 3D |
| `figures/tolerance.png` | Monte Carlo of the exact null under phase/gain errors |
| `figures/study/*.png` | 2-board seam/offset/yaw scans, 3-board gap heatmap |
| `metrics.csv`, `verdict.json` | numbers behind the figures |

## Layouts

| key | layout |
|---|---|
| 01_single | one board, broadside |
| 02_v150 | two boards, 150° included angle, hinged at the PCB edges |
| 03_v120 | two boards, 120° |
| 04_coplanar_butt | two boards, PCB edges butted (10.902 mm element seam) |
| 05_coplanar_gap | **current**: 15.750 mm seam, 5.250 mm half-pitch y offset |
| 06_facing | two boards facing each other, 400 mm apart (near field only) |
| 07_concave3 | three boards, concave, wings 30° |
| 08_coplanar3 | three boards, coplanar, current 15.750 mm seams |
| 09_pair_seam_only | control: 15.750 mm seam, y offset 0 |
| 10_butt_offset | no PCB gap (10.902 mm seam) **with** the 5.25 mm offset — the buildable no-gap variant |
| opt2 / opt3 | best 2- and 3-board geometry found by the search |

## Physics

- Every emitter is a baffled 10 mm circular piston, `D(β) = 2J₁(x)/x`,
  `x = π d sin β / λ`, zero behind its own board (each element's true normal).
- Far field: coherent sum `Σ Aᵢ Dᵢ exp(i k u·rᵢ)` on a direction-cosine grid.
- Near field: `Σ Aᵢ Dᵢ exp(i k |r−rᵢ|) / |r−rᵢ|` — no Fraunhofer approximation.
- Uniform phase on every board (mechanical arrangement only; no steering).
- Levels are relative to each pattern's peak; absolute SPL is not modelled.

## Metric conventions

- **lobe_54_75_db** — level at the four axial grating directions
  `sin θ = λ/d = 0.8166` (54.75°), φ = 0/90/180/270°. This is the report's
  claim, measured where the lobe is.
- **band_max_db** — maximum over the hemisphere in the 50–60° elevation band;
  the narrow notch at 54.75° does not remove the lobe's shoulders, and this
  number shows that.
- **band_energy_pct** — fraction of forward-hemisphere power in 50–60°.
- **leak_60_pct** — fraction above 60°.
- **DI** — `4π|p_max|² / ∫|p|² dΩ` over the forward hemisphere.
- **bw6** — −6 dB width on the x–z and y–z cuts; a dash means the beam does
  not lie in that cut (e.g. the V layouts).

## Verdict (from the current search)

- **2 boards**: the current 15.75 / 5.25 pair is the only searched pair that
  nulls all four 54.75° lobes. It is not Pareto-optimal in the unconstrained
  sense: a pair at 16.54 / 5.25 mm has the same DI and about 0.7 dB lower
  band peak, but the 54.75° lobe returns to −25 dB. The current geometry is
  the right choice only if the exact null is required; otherwise the
  16.54 / 5.25 pair is better and cheaper.
- **3 boards**: the best found layout is seams **12.48 / 17.20 mm** with y
  offsets **0 / 5.25 / 0 mm**. It gives **+1.8 dB** directivity (40.3 vs
  38.5), a **1.3 dB lower** 50–60° band peak (−16.0 vs −14.7 dB), slightly
  less >60° leak (0.66 % vs 0.74 %) and a narrower beam, for
  three boards and an element span of 502 mm (513 mm PCB) instead of 331 mm
  (342 mm PCB) — a 50 % larger array.
- It does **not** reduce total power in the 50–60° band (23.8 % vs 23.4 %),
  and the exact 54.75° null is lost (lobes −17.1 dB instead of a null).
  Notching four narrow nulls does not remove the broad shoulders — that is
  the report's "grating lobes are unavoidable", made visible.

## Limitations

- The directivity index integrates power only over the forward (+z)
  hemisphere. That is exact for the coplanar baffled boards, but it
  overstates DI for the tilted V/concave layouts, whose baffles also radiate
  below z = 0. Compare their DI with care.
- The 3-board search samples y offsets 0 and 5.25 mm only. A third-pitch
  pattern (0, 3.5, 7.0 mm) would null a three-board y-axis lobe exactly and is
  left for a future sweep.

## Documents

- `docs/2026-11-23-sound-wave-sim-design.md` — model, layouts, method.
- `docs/2026-11-23-two-board-sensitivity.md` — what ±1–2 mm of build error does to the two-board pair, and what the trim can recover.
- `docs/2026-11-24-literature-review.md` — verified literature (24 papers), comparisons and realistic targets; BibTeX in `docs/references.bib`.

## What "optimal" means

Best **within the searched ranges** under the ideal model: no phase errors,
failed elements, amplitude-code quantization, or real element efficiency. The
exact-null requirement for the pair is a design choice, not a Pareto rule.
`figures/tolerance.png` shows the null's robustness: random phase/gain errors
barely fill it (about −51 dB at 15° RMS), but a systematic 0.1 % shift in k
(≈ ±0.6 °C) lifts it to −38 dB, and 0.35 % (≈ ±2 °C) to about −28 dB. The band peak is the
robust number; the null needs a phase lock and temperature stability. Search ranges and
steps are in `docs/2026-11-23-sound-wave-sim-design.md`.

## Validation (`tests/`)

- Single board 54.75° lobe: −12.8 dB (piston-weighted), matches the analytic
  expectation.
- The current pair nulls all four 54.75° lobes; the butted pair does not.
- Control: the 15.75 mm seam alone nulls the x-axis lobe, the 5.25 mm offset
  alone nulls the y-axis lobe — the report's attribution, sharpened.
- Geometry: butted edges exactly 10.902 mm, V normals 60° apart for a 120°
  face angle, concave wings converge and sit forward.
- Near field converges to the far field at 50 m (1/r scaling).

## Optimal 2- and 3-board search (`sim/optimum_search/`)

Measured-element, two-axis steering search (0–35°, eight azimuths) with a
multi-rubric front, robustness ceilings, a report and full-steering galleries
for the recommended optima.

```powershell
cd sim
python -m optimum_search --two --three --gallery
```

Outputs: `data/search2/` (fronts, leaders, reference layouts),
`figures/search2/` (front/trade plots, leader curves, `optimum_2/` and
`optimum_3/` galleries, 57 states each) and
`docs/2026-11-26-optimal-search-report.md`.

Current result: 2-board leader `pair_16.000_5.250` (SL_cmd +0.31 dB,
SL_diag −0.25 dB, SRANGE 34°, DI0 39.7 dB); 3-board leader
`triple_18.500_14.750_10.500_5.250` (SL_cmd −0.51 dB, SL_diag −1.04 dB,
SRANGE 37°, DI0 41.4 dB). Tilted V/concave layouts are excluded: with a
single-aperture phase ramp they do not follow the commanded beam.

