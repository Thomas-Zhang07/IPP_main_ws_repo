# Optimal 2- and 3-board search — design and plan (v3)

Date: 2026-11-26
Status: draft for approval (v3 incorporates the second Gemini review of v2)
Depends on: `sim/transducer/`, `figures/steering/`, `sim/geometry.py`,
`sim/optimize.py`

## 1. Intent

Best coplanar 2- and 3-board arrangements with the measured TR4010HC element,
steered in x, y and diagonals, reported as a multi-rubric Pareto front.

## 2. Verified facts driving the design

- Commanded-direction level is identical for every coplanar layout (seams and
  offsets cannot change it) → `MBL` is not an objective.
- Global-peak-referenced `WC_SL` over 0–70° saturates at 0 dB for every
  candidate → use commanded-referenced `SL_cmd` and a bounded envelope.
- A 15° cone hides the −13.1 dB first sidelobe at 4.2° → tight mask + split.
- **Two-board minimax bound (verified numerically):** for any 2-board layout,
  the inter-board array factor at the four axial and four diagonal grating
  directions satisfies `max(A_x, A_y, D_+, D_-) ≥ 1/2` (−3.01 dB). The
  layout `s = 15.75 mm, o = 2.625 mm` attains it: x nulled, y and all four
  diagonals at −3.01 dB. The axial-null pair (15.75 / 5.25) nulls both axes
  but puts **all four diagonals at 0 dB**.
- **Three-board analogue (verified):** seams (14.0, 14.0) with offsets
  (0, 5.25, 0) give x nulled, y −9.5 dB, all four diagonals −3.52 dB; with
  offsets (0, 3.5, 7.0) x and y are nulled but two diagonals sit at 0 dB.
- `S_op ≤ 20°` cannot see the diagonal problem: at 20° diagonal steering the
  diagonal lobe is at 54.4° (−26.4 dB vs commanded); at 30° it is −4.0 dB and
  at 35° −0.2 dB. A dedicated 25–35° diagonal check is required.

## 3. Goals

- Measured element, per element normal, coplanar.
- Two-axis steering plus all four diagonals.
- Multi-rubric front, commanded-referenced, near/far split, diagonal check,
  absolute robustness ceilings.
- Verify leaders with quantisation, placement, drift and element envelopes.

## 4. Non-goals

Tilted layouts; amplitude tapering; absolute SPL; new fixtures.

## 5. Geometry and steering

- 16 × 16, 10.5 mm pitch, 40 kHz, span 157.5 mm.
- Steering `exp(−i k (u₀x + v₀y))`, continuous.
- 2 boards: seam `s ≥ 10.902 mm`, offset `o ∈ [0, 10.5]` (o1 = 0).
- 3 boards: `s1, s2`, `o1 = 0`, `o2, o3 ∈ [0, 10.5]`.

## 6. Scoring rubrics

Levels relative to the commanded-direction level; geodesic angles. Main-lobe
mask `C(4°)`; first-null references: 2.93° broadside in v (not 3.1°), 3.11° in
u at 20°.

### R1 — broadside / report

| Metric | Definition |
|---|---|
| `SL_shoulder0` | max over 2.5°–4° at θ₀ = 0 (residual shoulder diagnostic) |
| `SL_near0` | max over 4°–15° at θ₀ = 0 |
| `SL_far0` | max beyond 15° at θ₀ = 0 |
| `DI0` | forward-hemisphere 4π directivity, spherical quadrature, rear baffled to zero |
| `BNE0` | 50–60° power fraction with solid-angle Jacobian |
| `N54` | max over ±2° patches at the four 54.75° directions, clamped at −60 dB |

### R2 — steering (primary)

`S_op`: θ₀ ∈ 0…**θ_op** in 5° steps × 8 azimuths; θ_op is the operational
requirement (**θ_op = 35°**). `S_clean` = the same azimuths with θ₀ ≤ 24.1°
(the grating crossover) for main-beam quality. The main-lobe mask never meets
the grating lobe: at 25° the grating sits 48° away in angle, so a commanded-
referenced metric can score the full operational range.

| Metric | Definition |
|---|---|
| `SL_cmd` | worst over S_op of `20 log10(max outside C |p| / |p(commanded)|)` |
| `SL_clean` | worst over S_clean (θ ≤ 24.1°) — the layout's clean-regime quality |
| `SL_near` | worst 4°–15° component over S_op |
| `SL_far_s` | worst >15° steered component over S_op |
| `SL_diag` | worst `SL_cmd` over the diagonal azimuths {45,135,225,315} of S_op |
| `SRANGE_ax` | contiguous range from 0 (1° steps) with `SL_cmd ≤ T` along every axial azimuth (0/90/180/270); `T = −3 dB` and `0 dB` |
| `SRANGE_diag` | same along the four diagonal azimuths |

Report `min(SRANGE_ax, SRANGE_diag)` as `SRANGE`. Note: on 1-board-tall y cuts
the main-lobe shoulder approaches the 4° mask above ~44°; the axial crossover
(~24–31°) trips first, so the number is unaffected.

`MBL` is reported once as a sanity check, not scored.

### R3 — robustness (leaders only)

Absolute ceilings. Board-level perturbations keep per-board separability;
per-element quantisation and per-element noise do not, so they use the
element-level batched evaluator.

| Metric | Definition |
|---|---|
| `SL_4bit` | worst `SL_cmd` over 4-bit phase, worst-cased over 8 global phase offsets; element-level `Φ(768) @ W` |
| `SL_mech` | worst `SL_cmd` over mechanical corners: 2 boards, all 2⁴ sign corners of seam ±0.2 mm, offset ±0.2 mm, board gain ±1 dB, board phase ±10°; 3 boards, 100 Latin-hypercube draws; per-board separability |
| `SL_drift` | worst `SL_cmd` for Δk/k = ±0.35 %; analytic with k′ |
| `SL_elem` | worst `SL_cmd` over `E_mean`, `E_left`, `E_right`, `E_wide`, `E_asym`; per-board separability (E changes, positions do not) |

Element variants, defined exactly:
- `E_wide`: mean pattern with the angle stretched, `θ' = θ · 81/92` (datasheet
  80° ± 12° upper bound), clipped at 180°.
- `E_asym`: azimuth blend of the digitized halves, with the right half at
  φ = 0° and the left half at φ = 180°: `E(θ,φ) = 10^(L/20)` where
  `L = cos²(φ/2)·L_right(θ) + sin²(φ/2)·L_left(θ)` (φ measured from +x).
- Board tilt ±0.3°: exact solver on the top 3 only.

### Front and reporting

- Per board count, non-dominated over `(SL_cmd, SL_diag, SRANGE_0dB)`
  (minimise the first two, maximise the third).
- Columns: `SL_near`, `SL_far_s`, `SL_shoulder0`, `DI0`, `SL_4bit`,
  `SL_mech`, `SL_drift`, `SL_elem`, `span_mm`, `span_y_mm`.
- Combined 2-vs-3-board table.
- Shortlist score for reading only, fixed physical scales:
  `SL_cmd + 0.5·SL_near + 0.3·SL_diag + 0.3·max(SL_4bit, SL_mech)`;
  no z-scores.

## 7. Fast evaluator

```
p(u,v; u0,v0) = E(u,v) · A(kp(u−u0)/2) · A(kp(v−v0)/2)
                · Σ_b exp(i k [(u−u0) x_b + (v−v0) y_b])
A(β) = sin(16β)/sin(β), safe limit 16·cos(15β) as sinβ→0 (−16 at β=π)
```

- Initial grid `du = 0.005` on the pruned direction set, plus dense u0/v0
  slices; peaks refined by local search.
- Validation against the exact solver: `|Δ|p|| / |p| < 1e-3` for all
  directions within 40 dB of the peak; peak scalloping < 0.05 dB against
  `du = 0.001`.
- `DI0`/`BNE0` on spherical (cos θ, φ) quadrature; no horizon singularity.
- Pruning uses `max_m |E_m|` across the element variants and a −45 dB margin;
  re-prune per Δk variant for `SL_drift`.
- `SL_mech` (seam/offset/gain/phase per board) keeps per-board separability:
  each board contributes one 16×16 factor per direction; the board shifts,
  gains and phases fold into the 2–3-term sum.
- `SL_4bit` and per-element error draws **do not** preserve separability (each
  element gets its own phase remainder). Run them through the element-level
  batched evaluator: build `Φ` (N_dir × 768, complex64) once per leader on the
  pruned set, stack the weight vectors into `W`, and do one `cgemm` per leader.
- `SL_drift` recomputes the analytic factors with `k′ = k(1+ε)`.

## 8. Search space and stages

- 2-board seams: 0.25 mm snapped grid (11.0 … 26.0) plus
  {10.902, 14.0, 15.75, 17.5, 24.5, 26.25}; offsets 0.25 mm over [0, 10.5].
- 3-board seams: 0.5 mm snapped grid plus the same exact values; offsets
  1.75 mm over [0, 10.5] plus {3.5, 5.25, 7.0, 10.5} (deduplicated).
- Stages:
  1. Evaluator + tests.
  2. 2-board coarse on a reduced steering subset (azimuths 0/45/90/135 at
     0/10/20/25/30/35° across azimuths 0/45/90/135).
  3. 2-board refine, full `S_op`, ±0.5 mm.
  4. 3-board coarse (same subset).
  5. 3-board refine, full `S_op`, ±1.0 mm.
  6. Robustness on the top 10–20 per front.
  7. Report, leader figures, front tables.

Compute budget (pruned direction set ~3–5 k): stage 2 ≈ 2.7 k candidates × ~20
steering states × 5 k ≈ 2.7 × 10⁸; stage 4 ≈ 50 k × ~15 × 3 k ≈ 2.3 × 10⁹
(chunked `complex64`); stage 6 ≈ 20 leaders × ~110 draws × 33 states × 5 k ≈
3.6 × 10⁸, batched GEMM. Target: stage 4 under ~20 min on 8 cores; if not,
coarsen the sieve to `du = 0.008` and rescore survivors.

Expected front candidates (a check, not a target):
- 2 boards: **15.75/2.625** (minimax: x null, y and diagonals −3.01 dB);
  15.75/5.25 and 26.25/5.25 (axial nulls, diagonals 0 dB).
- 3 boards: **14.0/14.0 + (0, 5.25, 0)** (minimax: x null, y −9.5,
  diagonals −3.52 dB); 14.0/14.0 + (0, 3.5, 7.0) (x and y nulls, two diagonals
  0 dB); 17.5/17.5 variants.

If the front contains none of these, the evaluator or the metric is wrong.

## 9. Deliverables

- `sim/optimum_search.py`; `data/search2/{candidates,front_2,front_3}.csv`,
  `leaders.json`.
- `figures/search2/` — front plots, axial-vs-diagonal trade, robustness,
  leader steering figures, **continuous diagonal curves for the leaders**
  (`SL_diag` vs θ at 1°, 0–70°) and a steered-shoulder diagnostic for the
  top 3.
- `figures/search2/optimum_2/` and `optimum_3/` — full steering galleries for
  the recommended optimum per board count: 3D, polar, UV and amplitude/angle
  at every state θ ∈ {0…35}° × eight azimuths, plus a per-state `metrics.csv`.
- `docs/2026-11-26-optimal-search-report.md`.

## 10. Open questions

1. Required maximum scan angle: **resolved, θ_op = 35°** (0–35° in 5° steps ×
   eight azimuths). This includes the diagonal azimuths to 35°, where the
   diagonal lobe reaches ≈ −0.2 dB relative to the commanded beam.
2. Close-in suppression (2.5–15°): required (`SL_near` in the front) or
   diagnostic?
3. Rear radiation: baffled to zero or the measured −36 dB?
5. Are all boards mounted in the same orientation (the chart is L/R
   asymmetric), and what are the mechanical tolerances (seam ±0.2 mm, tilt
   ±0.3°, board gain/phase ±1 dB/±10°)?
6. 4-bit phase (16 steps) — correct?

## 11. Risks

- The pitch sets a hard scan limit: for θ₀ > arcsin(λ/2d) = 24.1° the m = −1
  grating lobe is physically stronger than the commanded beam, for every
  coplanar arrangement. Beyond it the search measures how gracefully a layout
  fails (split-lobe floor, √N), it does not remove the takeover.
- The axial-vs-diagonal trade is fundamental: no 2-board layout can null both.
  The minimax bound is −3.01 dB (2 boards) / −3.52 dB (3 boards) on the
  grating factor; layouts outside these families will be worse somewhere.
- Diagonal lobes are element-suppressed at large θ (e.g. 54° → −28 dB) but
  not at 30–35°, which is why the extended check exists.
- Element digitization ±1 dB main lobe, ±2–3 dB in the 50–60° skirt, and up to
  6 dB L/R asymmetry at 45° — sub-1 dB front differences are noise.
- The fast model assumes coplanar, uniform amplitude, continuous phase; R3
  covers the violations.
