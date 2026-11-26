# Sound-wave simulation figures — SonicSurface board layouts

Acoustic modelling for the 16 × 16 SonicSurface boards (10.5 mm pitch,
40 kHz, λ = 8.575 mm, 10 mm emitters): direction-cosine far-field maps, near
field slices, interactive 3D pages, a measured-transducer element model, a
seven-setup steering study, and an optimal 2-/3-board search.

The workspace has two generations:

1. **Original study** — ideal 10 mm piston elements, broadside only, leak
   metrics at the 54.75° grating directions. Kept as the historical baseline.
2. **Current study** — the measured TR4010HC element, steering in x, y and
   diagonals, and the multi-rubric optimal search. This is what the latest
   results and recommendations use.

## Quick start

```powershell
$env:PYTHONIOENCODING="utf-8"
python sim/steering_study.py          # 7 layouts, isotropic vs measured, 0–70°
cd sim
python -m optimum_search --two --three --gallery
cd ..
python -m pytest tests -q
```

The original ideal-piston run (`legacy/sim/run_all.py`) is archived; see
`legacy/README.md`.

Dependencies: Python 3.13, numpy, matplotlib, pytest, Pillow
(`requirements.txt`).

## Repository layout

```
sim/                     shared model + the current packages
  constants.py           board, element, PCB and fixture constants
  geometry.py            board layouts (single, V, coplanar, concave)
  field.py               far/near field sums and metrics
  render_png.py          PNG style and shared renderers
  steering_study.py      7-setup steering study (measured element)
  transducer/            digitized transducer directivity (measured)
  optimum_search/        measured-element 2-/3-board optimal search
legacy/                  archived original ideal-piston study
  sim/                   run_all.py, optimize.py, export_web.py, caches
  figures/  web/  data/  docs/  metrics.csv  verdict.json
tests/                   model, digitizer, steering, search tests
figures/                 current figures: steering/, search2/
data/                    current search fronts: search2/
docs/                    current design notes, literature review, report, plans
literature/              downloaded papers, extracted text and setup crops
transducers.jpg          datasheet photograph — the only element source
```

## Physics model

- **Original element:** baffled 10 mm circular piston,
  `D(β) = 2J₁(x)/x`, `x = π d sin β / λ`, zero behind its own board.
- **Current element:** the measured TR4010HC pattern digitized from
  `transducers.jpg` (see below). It is evaluated per element against that
  element's own board normal, so tilted boards tilt their element pattern.
- **Far field:** coherent sum `Σ Aᵢ Dᵢ exp(i k u·rᵢ)` on a direction-cosine
  grid.
- **Near field (ideal piston):** `Σ Aᵢ Dᵢ exp(−i k Rᵢ) / Rᵢ`,
  `Rᵢ = |r−rᵢ|`, with time convention `exp(+iωt)`. At large range,
  removing the common `exp(−ikR)/R` gives the far-field sum above, including
  for complex drive weights. This is a point-source array model, not a
  calculation of the field on a vibrating face; the spreading denominator
  is capped inside one emitter radius.
- **Amplitude:** uniform on every element unless a taper is named.
- **Phase:** mechanical arrangement only in the original study; the current
  studies apply a continuous steering ramp `exp(−i k (u₀x + v₀y))`.
- **Levels** are relative carrier-pressure levels, not absolute SPL, audible
  program level, or exposure data. The datasheet supplies one magnitude cut,
  not element phase, assembled-array calibration, mutual coupling, or room reflections.

## Transducer directivity (`sim/transducer/`)

The only element data is the photographed datasheet polar chart
(`transducers.jpg`). The module digitizes it reproducibly:

- DI **11.2 dB** (Q 13.1, 4π), −6 dB beam **81.0°**, side lobes ≈ −21 dB,
  rear ≈ −36 dB, level at 54.75° ≈ **−28.2 dB**.
- `directivity.csv` holds both halves of the asymmetric cut and their power
  average; `digitize.py` regenerates it from the jpg; `overlay.png` is the
  extraction check.
- API: `level_db`, `amplitude(cos β)`, `di_db`, `half_angle_6db`,
  `beamwidth_6db`.

Electrical spec versions: the photographed sheet (105 dB SPL min, −73 dB rx,
2000 pF, 80 Vpp) and the Yujie web page (120 dB, −63 dB, 2550 pF, 100 Vpp)
share the same 80° ±12° beam; directivity work is unaffected.

## Board layouts

| key | layout |
|---|---|
| 01_single | one board, broadside |
| 02_v150 | two boards, 150° included angle, hinged at the PCB edges |
| 03_v120 | two boards, 120° |
| 04_coplanar_butt | two boards, PCB edges butted (10.902 mm element seam) |
| 05_coplanar_gap | **current fixture**: 15.750 mm seam, 5.250 mm y offset |
| 06_facing | two boards facing each other, 400 mm apart (near field only) |
| 07_concave3 | three boards, concave, wings 30° |
| 08_coplanar3 | three boards, coplanar, current 15.750 mm seams |
| 09_pair_seam_only | control: 15.750 mm seam, y offset 0 |
| 10_butt_offset | no PCB gap (10.902 mm seam) with the 5.25 mm offset |
| opt2 / opt3 | original broadside search optima (historical) |

## Steering study (`figures/steering/`)

Open [the offline field explorer](docs/array-demo.html) in a browser.
Choose the single board, current pair, V120, V150, search pair, or search
triple. Drag the 3D pattern to rotate; switch between the far field and
a 2 m microphone sphere without changing the drive. Run
`python sim/demo.py` to rebuild from the saved layout choices.

Seven setups (single, V120, V150, current pair, same-seam/y=0, concave 3,
coplanar 3) × two element models × steering 0–70° in 5° steps. **This batch
steers in x only**; the two-axis evidence comes from the optimal search and
its galleries.

Per setup: `isotropic/` and `measured/` each with `3d/`, `polar/`, `uv/`,
`amplitude/` (per-case level-vs-angle), plus `amplitude/` overlays,
`summary/` charts and `metrics.csv`. `summary_all/` holds the cross-layout
measured charts. Details and metric definitions: `figures/steering/README.md`.

Headline results with the measured element:

- Broadside strongest sample outside 15°: single −24.1 dB, current pair −24.5 dB,
  coplanar 3-board −24.1 dB (the 15° cone in that batch is now known to hide
  the −13.1 dB near-in sidelobes; the search uses a 4° mask).
- At the single board's four axial broadside grating orders (54.75°), the
  measured-element model gives −28.2 dB, versus −12.8 dB for the ideal
  piston and 0 dB for isotropic elements. These are exact-direction samples;
  the element envelope can shift the local peak slightly inward.
- Under 20° steering the pair's strongest sample outside 15° is −3.5 dB
  (single −1.0 dB).
- V120 and V150 use all three emitter coordinates to steer a plane wave;
  the flat layouts give the same result with or without the depth term.
  Both compensated V layouts peak at broadside for a 0° command. Their
  strongest samples outside 15° are −4.8 dB (V120) and −8.3 dB (V150).
  These are forward-hemisphere, continuous-phase predictions, not SPL.

## Optimal 2-/3-board search (`sim/optimum_search/`)

Measured element, coplanar boards, steering envelope 0–35° in 5° steps across
eight azimuths (x ±, y ±, four diagonals). The field factorises for coplanar
boards, so a full sweep is fast:

```
p(u,v;u0,v0) = E(u,v) · A(kp(u−u0)/2) · A(kp(v−v0)/2)
               · Σ_b exp(i k [(u−u0)x_b + (v−v0)y_b])
```

### Rubrics

- **R1 broadside/report:** `SL_near0` (4–15°), `SL_far0` (>15°), `SL_shoulder0`
  (2.5–4°), `DI0` (spherical quadrature), `BNE0` (50–60° power fraction),
  `N54` (±2° patch at 54.75°).
- **R2 steering:** `SL_cmd` (strongest lobe outside a 4° cone around the
  commanded direction, referenced to the commanded level), `SL_clean`
  (θ ≤ 24.1°), `SL_near`, `SL_far`, `SL_diag` (diagonal azimuths),
  `SRANGE_0dB`/`SRANGE_-3dB` (largest contiguous steering from 0°, 1° steps,
  min over azimuths).

  `SL_cmd` is **not** the maximum of all physical sidelobes. At broadside
  the current two-board pair's first x-cut sidelobe is −12.5 dB at 2.06°;
  the search's 4° exclusion and even its 2.5° shoulder cutoff miss it.
  The first y-cut sidelobe (−13.2 dB at 4.19°) is included. Use unmasked
  principal cuts to assess close-in lobes before comparing board counts.
- **R3 robustness:** sampled maxima (not worst-case guarantees) `SL_4bit` (element-level 4-bit phase,
  8 global offsets), `SL_mech` (seam/offset ±0.2 mm, board gain ±1 dB, phase
  ±10°, 100 Latin-hypercube draws, fixed nominal drive phases), `SL_drift` (±0.35 % k), `SL_elem`
  (mean/left/right/wide/asym element envelope).

The front is non-dominated over `(SL_cmd, SL_diag, SRANGE_0dB)`, computed over
the top 80 refined candidates by provisional score; the coarse 2-D Pareto
front is unioned into the refinement to limit trim bias. The recommended
optimum per board count uses the robust shortlist.

### Current results

| boards | key | SL_cmd | SL_diag | SRANGE_0dB | DI0 | span |
|---|---|---|---|---|---|---|
| 2 | `pair_16.000_5.250` | +0.31 dB | −0.25 dB | 34° | 39.7 dB | 331 mm |
| 3 | `triple_18.500_14.750_10.500_5.250` | −0.46 dB | −1.03 dB | 37° | 41.4 dB | 506 mm |

- 2-board robustness: 4-bit +0.4, mech +0.7, drift +0.3, element +1.4 dB.
- 3-board robustness: 4-bit −0.9, mech −0.1, drift −0.7, element +0.2 dB.
- The analytic reference families are reported separately: the two-board
  minimax (`15.75/2.625`, −3.01 dB array factor on y/diagonals) and the axial
  nulls (`15.75/5.25`, `26.25/5.25`); the three-board seams
  {14.0, 17.5, 24.5} with offsets (0, 3.5, 7.0). Axial nulls force the
  diagonal array factor to 0 dB — the central design trade.
- Steering beyond ~24.1° is grating-dominated for a 10.5 mm pitch; the null
  families postpone the axial takeover (SRANGE_0dB ≈ 34–37°) but not the
  diagonal one.

### Galleries

`figures/search2/optimum_2/` and `optimum_3/` render the recommended optima at
57 states (0° plus 5–35° × eight azimuths): 3D surface, steering-plane polar
cut, UV map, and level-vs-angle (isotropic + measured) per state, plus a
per-state `metrics.csv`.

### Run and outputs

```powershell
cd sim
python -m optimum_search --two --three --gallery
python -m optimum_search --gallery          # re-render from saved fronts
```

- `data/search2/front_2.csv`, `front_3.csv` — front rows with all rubric and
  robustness columns.
- `data/search2/leaders.json` — the recommended optimum per board count.
- `figures/search2/` — front/trade plots, leader curves, galleries.
- `docs/2026-11-26-optimal-search-report.md` — tables, notes, residuals.

### Residual risks

- Board tilt (±0.3°) is not in the robustness runs; the design's top-3
  exact-solver tilt check remains outstanding.
- Mirror-equivalent 3-board layouts can appear separately; with the
  axisymmetric mean element they are physically identical.
- `E_asym` is an assumption about how the chart's left/right cut maps to
  azimuth.
- Element digitization is estimated at ±1 dB (main lobe) to ±2–3 dB
  (50–60° skirt); small simulated score differences do not establish a
  hardware ranking.

## Metric conventions

Original study:

- **lobe_54_75_db** — level at the four axial grating directions
  `sin θ = λ/d = 0.8166` (54.75°), φ = 0/90/180/270°.
- **band_max_db** — maximum in the 50–60° elevation band.
- **band_energy_pct** — forward-hemisphere power fraction in 50–60°.
- **leak_60_pct** — power fraction above 60°.
- **DI** — `4π|p_max|² / ∫|p|² dΩ` over the forward hemisphere.
- **bw6** — −6 dB width on the x–z / y–z cuts.

Search study: `SL_*` values are relative to the commanded-direction level
(a grating takeover is positive dB); `DI0` and `BNE0` use spherical
quadrature with the forward-hemisphere (baffled-rear) convention.

## Original ideal-piston study (historical)

The original findings, superseded for design decisions by the measured-element
search:

- **2 boards:** the current 15.75/5.25 pair is the only searched pair that
  nulls all four 54.75° lobes. A pair at 16.54/5.25 mm has the same DI and
  ~0.7 dB lower band peak but loses the null. The null is worth requiring only
  if the exact zero is needed.
- **3 boards:** the best broadside layout found was seams 12.48/17.20 mm with
  y offsets 0/5.25/0 mm: +1.8 dB DI (40.3 vs 38.5), 1.3 dB lower 50–60° band
  peak, slightly less >60° leak, narrower beam, for a 50 % larger aperture.
  It does not reduce total band power (23.8 % vs 23.4 %) and loses the exact
  54.75° null.
- The transducer already suppresses 54.75° by ~28 dB, so notching those four
  directions changes less than the original ideal-piston model implied; the
  binding number is the moving grating lobe under steering.

## Outputs

| Path | What |
|---|---|
| `figures/steering/…` | 7-setup steering study (x-only batch) |
| `figures/search2/…` | optimal search fronts, leader curves, galleries |
| `data/search2/…` | search fronts, leaders, reference rows |
| `legacy/figures/<key>/farfield.png` | historical direction-cosine map, cuts, board sketch |
| `legacy/figures/<key>/nearfield.png` | historical near-field maps and Re(p) wavefront |
| `legacy/web/<key>/index.html` | historical rotatable 3D surface, grating ring, planes |
| `legacy/web/index.html`, `legacy/web/overlay.html` | historical page index, two-layout overlay |
| `legacy/figures/comparison.png` | historical all-layout comparison |
| `legacy/figures/pareto.png` | historical DI vs 50–60° band peak |
| `legacy/figures/leak_compare.png` | historical x/y lobe cuts |
| `legacy/figures/tolerance.png` | historical null tolerance |
| `legacy/figures/study/*.png` | historical seam/offset/yaw scans |
| `legacy/metrics.csv`, `legacy/verdict.json` | original study numbers |

## Limitations

- The historical DI integrates only the forward hemisphere; it overstates DI
  for tilted V/concave layouts whose baffles also radiate below z = 0.
- The steering batch is x-only; y/diagonal evidence comes from the search.
- The optimization search is coplanar-only. The separate steering study
  includes depth compensation on V120 and V150 but keeps the three-board
  concave layout on its original projected drive as a control.
- The search's front is over the top 80 refined candidates; unrefined
  candidates may be missing from the table (the coarse Pareto union limits the
  bias).
- Gallery cuts show only the steering plane. Regenerated galleries share
  one sampled peak across cut, surface and map for each element model;
  scores in the CSV use the commanded direction, not that peak.

## Documents

- `legacy/docs/2026-11-23-sound-wave-sim-design.md` — original model, layouts,
  method.
- `legacy/docs/2026-11-23-two-board-sensitivity.md` — build-error sensitivity.
- `docs/2026-11-24-literature-review.md` — verified literature (24 papers),
  comparisons and targets; BibTeX in `docs/references.bib`.
- `docs/2026-11-25-transducer-directivity-design.md` — measured element and
  module design.
- `docs/superpowers/plans/2026-11-25-optimal-search.md` — search design v3.
- `docs/superpowers/plans/2026-11-26-optimal-search-implementation.md` —
  implementation plan.
- `docs/2026-11-26-optimal-search-report.md` — generated results and
  residuals.

## Validation (`tests/`)

`python -m pytest tests -q` covers:

- the original model: 54.75° lobe level, pair nulls, seam/offset controls,
  geometry, near/far convergence, V normals, concave wings;
- the transducer digitizer: reproducible extraction, DI and beamwidth,
  amplitude clipping, range checks;
- the steering study: grating algebra, isotropic vs measured levels, main
  peak at the commanded angle;
- the optimal search: Dirichlet limits, minimax lattice levels, fast-vs-exact
  agreement (with v0), commanded-level invariance, first-sidelobe capture,
  DI0 convergence, SRANGE contiguity, robustness routing and the drift fix,
  front/gallery round-trips.

## Reproducibility and runtime

- Caches live in `data/cache/` (keyed by emitter positions and grid size);
  deleting them is safe.
- The archived original run: ~15–25 min; `steering_study.py`: ~7 min; the
  optimal search with galleries: ~45–60 min. All figures are regenerable from
  the scripts.
- Random draws are seeded (`20261126`); results are deterministic.

## Review history

The optimal search was reviewed externally (agy) after implementation.
Its high-severity findings — an under-sampled DI0/BNE0 quadrature, robustness
states missing the 35° envelope, a stale ranking path, and coarse-search trim
bias — were fixed and verified: `DI0` is now 39.7 / 41.4 dB (matching the
converged quadrature), the leaders' robustness includes all 35° azimuths, and
the front uses the specified `(SL_cmd, SL_diag, SRANGE_0dB)` objective.
