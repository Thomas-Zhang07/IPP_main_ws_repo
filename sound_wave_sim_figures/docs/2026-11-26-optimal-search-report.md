# Optimal 2- and 3-board search — results

Measured TR4010HC element; coplanar boards; steering envelope 0–35° in 5° steps across eight azimuths (x, y and four diagonals). Levels are relative to the commanded direction; SL_near covers 4–15°, the mask is 4°. Front tables are ordered by the provisional score (without robustness); the recommended optima use the robust shortlist.

## 2 boards

| key | n | span mm | span y | SL_cmd | SL_clean | SL_near | SL_far | SL_diag | SRANGE0 | DI0 |
|---|---|---|---|---|---|---|---|---|---|---|
| pair_16.000_5.250 | 2 | 331.0 | 5.2 | 0.3 | -3.6 | -12.4 | 0.3 | -0.3 | 34.0 | 39.7 |
| pair_15.250_5.250 | 2 | 330.2 | 5.2 | 0.9 | -3.1 | -12.4 | 0.9 | -0.3 | 33.0 | 39.7 |
| pair_15.000_5.250 | 2 | 330.0 | 5.2 | 1.2 | -2.9 | -12.4 | 1.2 | -0.3 | 33.0 | 39.7 |
| pair_14.750_5.250 | 2 | 329.8 | 5.2 | 1.4 | -2.6 | -12.4 | 1.4 | -0.4 | 32.0 | 39.7 |
| pair_25.250_5.250 | 2 | 340.2 | 5.2 | 1.6 | -2.5 | -12.4 | 1.6 | -0.4 | 32.0 | 39.7 |
| pair_14.500_5.250 | 2 | 329.5 | 5.2 | 1.6 | -2.4 | -12.4 | 1.6 | -0.5 | 32.0 | 39.7 |
| pair_14.250_5.250 | 2 | 329.2 | 5.2 | 1.8 | -2.3 | -12.4 | 1.8 | -0.5 | 32.0 | 39.7 |
| pair_14.000_5.250 | 2 | 329.0 | 5.2 | 1.9 | -2.2 | -12.4 | 1.9 | -0.6 | 32.0 | 39.7 |
| pair_26.000_7.000 | 2 | 341.0 | 7.0 | 1.8 | -2.1 | -12.4 | 1.8 | -0.3 | 33.0 | 39.7 |
| pair_26.250_7.000 | 2 | 341.2 | 7.0 | 1.8 | -2.1 | -12.4 | 1.8 | -0.4 | 33.0 | 39.7 |
| pair_16.000_7.250 | 2 | 331.0 | 7.2 | 1.9 | -2.0 | -12.4 | 1.9 | -0.5 | 34.0 | 39.7 |
| pair_15.750_7.250 | 2 | 330.8 | 7.2 | 1.9 | -2.0 | -12.4 | 1.9 | -0.4 | 34.0 | 39.7 |

## 3 boards

| key | n | span mm | span y | SL_cmd | SL_clean | SL_near | SL_far | SL_diag | SRANGE0 | DI0 |
|---|---|---|---|---|---|---|---|---|---|---|
| triple_26.250_16.500_5.250_5.250 | 3 | 515.2 | 5.2 | -0.1 | -3.9 | -12.4 | -0.1 | -2.9 | 37.0 | 41.4 |
| triple_18.500_14.750_10.500_5.250 | 3 | 505.8 | 10.5 | -0.5 | -4.4 | -12.5 | -0.5 | -1.0 | 37.0 | 41.4 |
| triple_16.000_17.000_0.000_5.250 | 3 | 505.5 | 5.2 | 0.0 | -3.7 | -12.4 | 0.0 | -2.9 | 34.0 | 41.4 |
| triple_17.000_16.000_5.250_5.250 | 3 | 505.5 | 5.2 | 0.0 | -3.7 | -12.4 | 0.0 | -2.9 | 34.0 | 41.4 |
| triple_16.500_16.500_10.500_5.250 | 3 | 505.5 | 10.5 | 0.1 | -3.6 | -12.5 | 0.1 | -2.9 | 34.0 | 41.4 |
| triple_15.500_17.500_5.250_5.250 | 3 | 505.5 | 5.2 | -0.3 | -4.0 | -12.4 | -0.3 | -1.7 | 37.0 | 41.4 |
| triple_17.500_15.500_0.000_5.250 | 3 | 505.5 | 5.2 | -0.3 | -4.0 | -12.4 | -0.3 | -1.7 | 37.0 | 41.4 |
| triple_19.000_14.500_0.000_5.250 | 3 | 506.0 | 5.2 | -0.5 | -4.5 | -12.4 | -0.5 | -0.8 | 36.0 | 41.4 |
| triple_14.500_19.000_5.250_5.250 | 3 | 506.0 | 5.2 | -0.5 | -4.5 | -12.4 | -0.5 | -0.8 | 36.0 | 41.4 |
| triple_15.000_19.000_5.250_5.250 | 3 | 506.5 | 5.2 | -0.5 | -4.4 | -12.4 | -0.5 | -0.7 | 37.0 | 41.4 |
| triple_19.000_15.000_0.000_5.250 | 3 | 506.5 | 5.2 | -0.5 | -4.4 | -12.4 | -0.5 | -0.7 | 37.0 | 41.4 |

## Notes

- Pitch limit: without nulls the grating takeover is ~24.1°; the null families postpone the axial takeover (SRANGE_0dB ≈ 34°) but not the diagonal one.
- The two-board minimax layout (15.75 / 2.625) trades the exact y null for −3.01 dB on all diagonals; the axial-null pair (15.75 / 5.25) keeps both axial nulls with 0 dB diagonals.
- All candidates entering the final Pareto comparison are rescored on one du = 0.004 grid. These are sampled maxima, not continuous bounds.
- The front is the non-dominated set of the top 80 refined candidates by provisional score; the coarse sweep unions its 2-D Pareto front before refinement to limit trim bias.
- Mechanical errors use fixed nominal drive phases and 100 independent-column Latin-hypercube draws. The maximum is a sample statistic, not a bound.
- Board tilt (±0.3°) is not included in the robustness runs; it remains the top-3 exact-solver check from the design.
- Mirror-equivalent 3-board layouts can appear separately; with the axisymmetric mean element they are physically identical.
- Element digitization uncertainty is ±1 dB (main lobe) to ±2–3 dB (50–60° skirt); sub-1 dB front ordering is not significant.

## Reference layouts (predicted families)

These are the analytical null/minimax families. They are listed even when a near-equivalent dominates them on the front.

### 2 boards

| key | n | span mm | span y | SL_cmd | SL_clean | SL_near | SL_far | SL_diag | SRANGE0 | DI0 |
|---|---|---|---|---|---|---|---|---|---|---|
| pair_15.750_5.250 | 2 | 330.8 | 5.2 | 0.6 | -3.5 | -12.5 | 0.6 | -0.4 | 34.0 | 39.7 |
| pair_26.250_5.250 | 2 | 341.2 | 5.2 | 0.8 | -3.3 | -12.5 | 0.8 | -0.4 | 33.0 | 39.7 |
| pair_15.750_2.625 | 2 | 330.8 | 2.6 | 2.2 | -1.7 | -12.5 | 2.2 | -0.7 | 34.0 | 39.7 |

### 3 boards

| key | n | span mm | span y | SL_cmd | SL_clean | SL_near | SL_far | SL_diag | SRANGE0 | DI0 |
|---|---|---|---|---|---|---|---|---|---|---|
| triple_14.000_14.000_5.250_0.000 | 3 | 500.5 | 5.2 | 0.9 | -3.1 | -12.6 | 0.9 | -1.0 | 32.0 | 41.4 |
| triple_24.500_24.500_3.500_7.000 | 3 | 521.5 | 7.0 | 1.4 | -2.5 | -12.5 | 1.4 | -0.7 | 32.0 | 41.4 |
| triple_17.500_17.500_3.500_7.000 | 3 | 507.5 | 7.0 | 1.4 | -2.5 | -12.5 | 1.4 | -0.7 | 31.0 | 41.4 |
| triple_14.000_14.000_3.500_7.000 | 3 | 500.5 | 7.0 | 1.4 | -2.5 | -12.5 | 1.4 | -0.6 | 32.0 | 41.4 |
| triple_14.000_24.500_3.500_7.000 | 3 | 511.0 | 7.0 | 1.4 | -2.5 | -12.5 | 1.4 | -0.6 | 32.0 | 41.4 |

## Recommended optima (with robustness)

| key | n | span mm | span y | SL_cmd | SL_clean | SL_near | SL_far | SL_diag | SRANGE0 | DI0 | 4bit | mech | drift | elem | shortlist |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| triple_18.500_14.750_10.500_5.250 | 3 | 505.8 | 10.5 | -0.5 | -4.4 | -12.5 | -0.5 | -1.0 | 37.0 | 41.4 | -0.9 | -0.1 | -0.7 | 0.2 | -7.0 |
| pair_16.000_5.250 | 2 | 331.0 | 5.2 | 0.3 | -3.6 | -12.4 | 0.3 | -0.3 | 34.0 | 39.7 | 0.4 | 0.7 | 0.3 | 1.4 | -5.5 |

- **2 boards**: `pair_16.000_5.250` (shortlist -5.5 dB)
- **3 boards**: `triple_18.500_14.750_10.500_5.250` (shortlist -7.0 dB)

## Combined comparison

| boards | key | SL_cmd | SL_diag | SRANGE0 | DI0 | span mm |
|---|---|---|---|---|---|---|
| 2 | pair_16.000_5.250 | 0.3 | -0.3 | 34.0 | 39.7 | 331 |
| 3 | triple_18.500_14.750_10.500_5.250 | -0.5 | -1.0 | 37.0 | 41.4 | 506 |
