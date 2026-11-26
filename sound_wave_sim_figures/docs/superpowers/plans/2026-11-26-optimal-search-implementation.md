# Optimal 2-/3-board Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `sim/optimum_search/` — a validated fast evaluator and staged search that scores coplanar 2- and 3-board arrangements with the measured transducer, reports the multi-rubric Pareto front, and verifies the leaders under quantisation and mechanical tolerances.

**Architecture:** A small package: `model.py` (candidate geometry, separability evaluator, element variants, pruning, exact cross-check), `metrics.py` (SL_cmd/near/far/diag, SRANGE, DI0/BNE0/N54, `score_states`), `search.py` (candidate grids, coarse/refine sweeps, front, CSV), `robustness.py` (4-bit, mechanical, drift, element envelopes), `report.py` (figures and the report table). Coplanar boards let the field factorise into a board Dirichlet factor × a 2–3-term lattice.

**Tech Stack:** Python 3.13, numpy, matplotlib, pytest; Pillow already present. No new dependencies.

**Spec:** `docs/superpowers/plans/2026-11-25-optimal-search.md` (v3)

## Global Constraints

- Element is the measured TR4010HC pattern via `sim/transducer`; variants: `mean`, `left`, `right`, `wide`, `asym` as defined in the spec.
- Coplanar boards only; uniform amplitude; continuous phase except where quantisation is tested.
- Board: 16 × 16, pitch 10.5 mm, span 157.5 mm, 40 kHz, λ = 8.575 mm.
- Masks: main lobe 4°, near 4°–15°, far > 15°. Steering states use geodesic angles.
- `S_op`: θ ∈ {0, 5, …, 35}° × azimuths {0,45,90,135,180,225,270,315}°; `S_clean` = θ ≤ 24.1°.
- `SL_diag`: worst `SL_cmd` over the diagonal azimuths {45,135,225,315}° of `S_op`.
- Random draws seeded `20261126`; all tests deterministic.
- Tests run from the project root with `sys.path.insert(0, ROOT/"sim")` as in `tests/test_field.py`.
- The workspace is not a git repository: no commit steps; each task ends with commands and expected output.
- No absolute paths in code.

## Review Focus

- A direction exactly at the mask boundary or at the first sidelobe (4.2°) → `SL_near` must catch the −13.1 dB lobe; the mask must not swallow it.
- The commanded direction not on the grid → the commanded level is computed analytically (`N·E`), never read from the grid.
- Pruning with a nominal element → a direction that rises under `E_wide`/`E_left` or shifted `k` must still be kept (use max-over-variants, −45 dB margin); otherwise `SL_elem`/`SL_drift` silently miss peaks.
- 4-bit quantisation is per element → the separable evaluator is invalid; robustness must use the element-level batched evaluator.
- `SRANGE` continuity → a candidate passing at 30° after failing at 25° must not report 30°.

---

### Task 1: Package and fast evaluator

**Files:**
- Create: `sim/optimum_search/__init__.py`
- Create: `sim/optimum_search/model.py`
- Modify: `sim/steering_study.py` (`pattern` gains a keyword-only `v0=0.0` used in the steering weights; existing calls unchanged)
- Test: `tests/test_optimum_model.py`

**Interfaces:**
- Consumes: `constants`, `geometry`, `transducer`, `steering_study.pattern`.
- Produces:
  - `Candidate` frozen dataclass: fields `key: str`, `seams_m: tuple[float, ...]`, `offsets_m: tuple[float, ...]`; properties `n_boards`, `span_m`, `span_y_m`, `origins` (shape `(n, 2)`).
  - `pair(s_m: float, o_m: float) -> Candidate` (key `f"pair_{s_m*1e3:.2f}_{o_m*1e3:.2f}"`).
  - `triple(s1_m: float, s2_m: float, o2_m: float, o3_m: float) -> Candidate` (o1 = 0, same key pattern).
  - `board_factor(q, k=C.WAVE_NUMBER, pitch=C.PITCH_M, n=16) -> np.ndarray` — `sin(nβ)/sin(β)`, β = k·pitch·q/2, safe limit `n·cos((n−1)β)` as sin β → 0.
  - `element_amplitude(dirs, variant="mean") -> np.ndarray` — pressure factor; `dirs` is `(N,3)`.
  - `array_factor(cand, dirs, u0, v0=0.0) -> np.ndarray` (complex, no element).
  - `field_fast(cand, dirs, u0, v0=0.0, variant="mean") -> np.ndarray` (complex).
  - `commanded_amp(cand, u0, v0=0.0, variant="mean") -> float` — `256·n_boards·E(θ₀,φ₀)`.
  - `direction_grid(du: float) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]` — `(dirs, el_deg, az_deg, inside)` from `field.uv_grid`.
  - `prune(dirs, cand, u0, v0, floor_db=-45.0) -> np.ndarray` — boolean mask keeping directions whose upper bound `n_boards·16²·max_variant|E|` is within `floor_db` of the commanded level.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_optimum_model.py
import pathlib, sys
import numpy as np, pytest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sim"))
import constants as C
import geometry
import steering_study as S
from optimum_search import model as M

def test_board_factor_limits():
    assert M.board_factor(0.0) == pytest.approx(16.0, abs=1e-9)
    assert M.board_factor(C.WAVELENGTH_M / C.PITCH_M) == pytest.approx(0.0, abs=1e-6)
    for q in (-1.0, -0.5, 0.0, 0.33, 0.8166, 1.0):
        assert np.isfinite(M.board_factor(q))

def test_lattice_minimax():
    # x nulled, y and all diagonals at -3.01 dB for the pair
    cand = M.pair(0.01575, 0.002625)
    ug = C.WAVELENGTH_M / C.PITCH_M
    d = np.array([[ug, 0, 0.1], [0, ug, 0.1], [ug, ug, 0.1]])
    d = d / np.linalg.norm(d, axis=1, keepdims=True)
    f = np.abs(M.array_factor(cand, d, 0.0, 0.0)) / (2 * 256)
    assert f[0] < 1e-6
    assert f[1] == pytest.approx(10 ** (-3.01 / 20), abs=2e-3)
    assert f[2] == pytest.approx(10 ** (-3.01 / 20), abs=2e-3)

def test_fast_matches_exact_with_v0():
    cand = M.triple(0.014, 0.014, 0.0035, 0.0070)
    layout = geometry.coplanar3(0.014, 0.014, (0.0, 0.0035, 0.0070),
                                key="t", title="t")
    rng = np.random.default_rng(1)
    u = rng.uniform(-0.6, 0.6, 400); v = rng.uniform(-0.6, 0.6, 400)
    inside = u*u + v*v < 0.95
    dirs = np.column_stack([u[inside], v[inside], np.sqrt(1-u[inside]**2-v[inside]**2)])
    u0, v0 = np.sin(np.radians(20)), np.sin(np.radians(10))
    fast = M.field_fast(cand, dirs, u0, v0, "mean")
    exact = S.pattern(layout, dirs, u0, "measured", v0=v0)
    rel = np.abs(fast - exact) / np.maximum(np.abs(exact), 1e-12)
    keep = np.abs(exact) > 10 ** (-40 / 20) * np.abs(exact).max()
    assert np.max(rel[keep]) < 1e-3

def test_prune_bound_is_safe():
    cand = M.pair(0.01575, 0.00525)
    dirs, _, _, _ = M.direction_grid(0.02)
    keep = M.prune(dirs, cand, 0.0, 0.0)
    dropped = dirs[~keep]
    assert dropped.shape[0] > 0
    bound = 2 * 256 * np.max([M.element_amplitude(dropped, m)
                             for m in M.VARIANTS])
    assert bound <= M.commanded_amp(cand, 0.0, 0.0) * 10 ** (-45 / 20) * 1.001
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_optimum_model.py -q`
Expected: `ModuleNotFoundError: No module named 'optimum_search'`.

- [ ] **Step 3: Implement Task 1**

- `VARIANTS = ("mean", "left", "right", "wide", "asym")`.
- `element_amplitude`: mean/left/right call `transducer.level_db(θ, half)`; `wide` uses θ·81/92; `asym` uses `φ = atan2(v,u)` and `L = cos²(φ/2)·L_right + sin²(φ/2)·L_left`.
- `array_factor`: `Σ_b exp(i k [(u−u0)x_b + (v−v0)y_b]) × board_factor(u−u0) × board_factor(v−v0)`, with `q_u = u−u0`, `q_v = v−v0`.
- `commanded_amp`: `256·n_boards·element_amplitude([[u0,v0,√(1−u0²−v0²)]], variant)[0]`.
- `prune`: bound on `n_boards·(16²)·max_variant E(q)` (the Dirichlet maxima are 16²).

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_optimum_model.py -q`
Expected: 4 passed.

- [ ] **Step 5: Run the existing suite**

Run: `python -m pytest tests -q`
Expected: all pass (the `v0` keyword is backward compatible).

---

### Task 2: Metrics

**Files:**
- Create: `sim/optimum_search/metrics.py`
- Test: `tests/test_optimum_metrics.py`

**Interfaces:**
- Consumes: `model` from Task 1.
- Produces:
  - `MASK_DEG = 4.0`, `NEAR_MAX_DEG = 15.0`.
  - `sl_components(mag, dirs, d0, cmd_amp, mask_deg=4.0) -> dict` with keys `sl_cmd`, `sl_near`, `sl_far`.
  - `score_states(cand, du, states, variant="mean") -> dict` — `states` is a list of `(theta_deg, phi_deg)`; returns `SL_cmd`, `SL_clean`, `SL_near`, `SL_far_s`, `SL_diag`.
  - `srange(cand, azimuths_deg, variant="mean", step_deg=2.0, thresholds=(0.0, -3.0)) -> dict` — `{threshold: contiguous_range_deg}`; contiguous from 0°, per azimuth, minimum across azimuths.
  - `di0(cand, variant="mean") -> float` — spherical quadrature; rear baffled to zero, documented.
  - `bne0(cand, variant="mean") -> float` — 50–60° forward power fraction.
  - `n54(cand, variant="mean") -> float` — max over ±2° patches at the four 54.75° directions, clamped −60 dB.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_optimum_metrics.py
import pathlib, sys
import numpy as np, pytest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sim"))
import constants as C
from optimum_search import model as M, metrics as X

def test_first_sidelobe_is_captured():
    cand = M.pair(C.CURRENT_SEAM_M, 0.0)
    dirs, el, az, _ = M.direction_grid(0.004)
    mag = np.abs(M.field_fast(cand, dirs, 0.0, 0.0))
    d0 = np.array([0.0, 0.0, 1.0])
    comp = X.sl_components(mag, dirs, d0, M.commanded_amp(cand, 0, 0))
    assert comp["sl_near"] == pytest.approx(-13.1, abs=0.8)

def test_commanded_level_is_geometry_independent():
    a = M.commanded_amp(M.pair(0.01575, 0.00525), np.sin(np.radians(20)), 0.0)
    b = M.commanded_amp(M.pair(0.01575, 0.0), np.sin(np.radians(20)), 0.0)
    assert a == pytest.approx(b, rel=1e-12)

def test_srange_contiguity():
    curve = {0: -30, 5: -20, 10: -2, 15: -20, 20: -1}
    out = X._contiguous(curve, threshold=-3.0)
    assert out == 5.0

def test_di0_range():
    cand = M.pair(0.01575, 0.00525)
    assert 8.0 < X.di0(cand) < 16.0

def test_score_states_keys():
    cand = M.pair(0.01575, 0.00525)
    states = [(0, 0), (20, 0), (20, 45)]
    out = X.score_states(cand, 0.01, states)
    for k in ("SL_cmd", "SL_clean", "SL_near", "SL_far_s", "SL_diag"):
        assert k in out
```

- [ ] **Step 2: Run to fail**

Run: `python -m pytest tests/test_optimum_metrics.py -q`
Expected: import error.

- [ ] **Step 3: Implement**

- `sl_components`: `ang = degrees(arccos(clip(dirs @ d0)))`; outside mask > 4°; `20log10(max/commanded)`; near restricted to ≤15°.
- `score_states`: precompute the grid once (`du`), loop states, `field_fast`, take `max`; `SL_diag` from the diagonal subset of `S_op` states supplied by the caller.
- `_contiguous(curve: dict[float, float], threshold)`: walk sorted θ from 0; stop at the first value above threshold (curve values are SL_cmd in dB; pass ≤ threshold).
- `srange`: for each azimuth build the θ grid 0…70 step, compute `SL_cmd` per θ (pruned dirs for speed), apply `_contiguous`, take the min.
- `di0`/`bne0`: Gauss-Legendre in cos θ ∈ [0,1] × uniform φ (48 × 96), evaluate `field_fast`, sum with weights; raise the quadrature for the final report.
- `n54`: evaluate exact directions θ=54.75°, φ ∈ {0,90,180,270}, max over a ±2° patch (9×9), clamp at −60.

- [ ] **Step 4: Run to pass; then the full suite**

Run: `python -m pytest tests/test_optimum_metrics.py -q` → 5 passed; `python -m pytest tests -q` → all pass.

---

### Task 3: Candidate grids, sweeps, front

**Files:**
- Create: `sim/optimum_search/search.py`
- Test: `tests/test_optimum_search.py`

**Interfaces:**
- Consumes: `model`, `metrics`.
- Produces:
  - `seam_values(two_board: bool) -> np.ndarray` — 0.25 mm snapped grid plus `{0.010902, 0.014, 0.01575, 0.0175, 0.0245, 0.02625}` (3-board uses 0.5 mm).
  - `offset_values(two_board: bool) -> np.ndarray` — 2-board 0…10.5 step 0.25; 3-board 0…10.5 step 1.75 plus `{0.0035, 0.00525, 0.0070, 0.0105}` deduplicated.
  - `two_board_candidates() -> list[Candidate]`, `three_board_candidates() -> list[Candidate]`.
  - `score_rows(cands, du, states, variant="mean") -> list[dict]` — each row has candidate key/spans and the `score_states` metrics.
  - `pareto(rows, minimize=("SL_cmd", "SL_diag"), maximize=("DI0",)) -> list[dict]`.
  - `write_csv(rows, path)`; `REFINE_STATES` and `COARSE_STATES` constants.
  - `run_two_board(...) -> (rows, front)`, `run_three_board(...) -> (rows, front)` — coarse → top `k` → ±step refine → front; SRANGE on the top 200 (`srange` at 2°, then 1° on the top 20).

- [ ] **Step 1: Write failing tests**

```python
# tests/test_optimum_search.py
import pathlib, sys
import numpy as np, pytest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sim"))
import constants as C
from optimum_search import search as Q

def test_candidate_counts_positive():
    assert len(Q.two_board_candidates()) > 2000
    assert len(Q.three_board_candidates()) > 20000

def test_exact_null_seams_present():
    seams = Q.seam_values(two_board=True)
    assert any(abs(s - 0.01575) < 1e-9 for s in seams)
    assert any(abs(s - 0.02625) < 1e-9 for s in seams)

def test_pareto_non_dominated():
    rows = [{"k": 0, "SL_cmd": -3, "SL_diag": -2, "DI0": 10},
            {"k": 1, "SL_cmd": -2, "SL_diag": -3, "DI0": 10},
            {"k": 2, "SL_cmd": -2, "SL_diag": -1, "DI0": 9}]
    front = Q.pareto(rows)
    assert {r["k"] for r in front} == {0, 1}

def test_smoke_two_board_finds_minimax():
    rows = Q.score_rows(
        [Q.model.pair(0.01575, 0.002625), Q.model.pair(0.01575, 0.00525)],
        du=0.01, states=[(0, 0), (20, 45)])
    assert len(rows) == 2
    assert rows[0]["SL_cmd"] <= rows[1]["SL_cmd"] + 2.0
```

- [ ] **Step 2: Run to fail**

Run: `python -m pytest tests/test_optimum_search.py -q`
Expected: import error.

- [ ] **Step 3: Implement**

- Candidate grids as above; deduplicate offsets; keep the exact seam values.
- `score_rows` loops candidates, calls `metrics.score_states` on the reduced `COARSE_STATES` = `[(t, a) for t in (0,10,20,25,30,35) for a in (0,45,90,135)]` for the coarse pass.
- Refinement: take the top 300 by a provisional score `SL_cmd + 0.3·SL_diag`, rescore with full `S_op` + `SL_diag`.
- Front over `(SL_cmd, SL_diag)` during coarse; add `SRANGE_0dB` on the top 200 and use the 3-objective front for the report.
- CSV fields: `key, seams, offsets, n_boards, span_mm, span_y_mm, SL_cmd, SL_near, SL_far_s, SL_diag, SRANGE_0dB, SRANGE_-3dB, DI0, BNE0, SL_near0, SL_far0, SL_shoulder0, N54` (SRANGE fields blank until computed).

- [ ] **Step 4: Run to pass**

Run: `python -m pytest tests/test_optimum_search.py -q` → 4 passed.

---

### Task 4: Robustness

**Files:**
- Create: `sim/optimum_search/robustness.py`
- Test: `tests/test_optimum_robustness.py`

**Interfaces:**
- Consumes: `model`, `metrics`.
- Produces:
  - `sl_4bit(cand, states, variant="mean", n_offsets=8) -> float` — element-level batched evaluator; per-element phase quantised to 2π/16; worst over global offsets `2πk/16`.
  - `sl_mech(cand, variant="mean", n_draws_three=100) -> float` — 2-board sign corners (seam/offset ±0.2 mm, board gain ±1 dB, phase ±10°); 3-board Latin-hypercube draws; per-board separability.
  - `sl_drift(cand, variant="mean", epsilons=(0.0035, -0.0035)) -> float` — analytic with k′.
  - `sl_elem(cand, states) -> float` — max over the five element variants.
  - `robust(cand, states) -> dict` with the four ceilings and `robust_max`.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_optimum_robustness.py
import pathlib, sys
import numpy as np, pytest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sim"))
import constants as C
from optimum_search import model as M, robustness as R

def test_4bit_broadside_equals_continuous():
    from optimum_search import metrics as X
    cand = M.pair(0.01575, 0.00525)
    nominal = X.score_states(cand, 0.01, [(0, 0)])["SL_cmd"]
    assert R.sl_4bit(cand, [(0, 0)], n_offsets=1) == pytest.approx(
        nominal, abs=0.1)

def test_4bit_uses_element_level():
    cand = M.pair(0.01575, 0.00525)
    exact = R.sl_4bit(cand, [(20, 0)], n_offsets=1)
    assert np.isfinite(exact) and exact > -20.0

def test_mech_corner_changes():
    cand = M.pair(0.01575, 0.00525)
    nominal = R.sl_mech(cand, states=[(20, 0)], n_draws_three=1)
    assert np.isfinite(nominal)

def test_elem_envelope_ordering():
    cand = M.pair(0.01575, 0.00525)
    out = R.robust(cand, [(0, 0), (20, 0)])
    assert out["robust_max"] >= max(out["SL_4bit"], out["SL_mech"],
                                    out["SL_drift"], out["SL_elem"])
```

- [ ] **Step 2: Run to fail**

Run: `python -m pytest tests/test_optimum_robustness.py -q`
Expected: import error.

- [ ] **Step 3: Implement**

- Build the element-level `Φ` once per candidate/state set: positions from `candidate.origins` + the 16×16 grid; `exp(i k (u x_j + v y_j))` on the pruned directions; weights per state/draw; `cgemm` with `complex64`.
- 4-bit: quantise `angle(w)` to the nearest `2π/16`; sweep 8 global offsets.
- `sl_mech`: board-level weights only (per-board gain/phase, moved origins), so use the separable model with perturbed origins.
- `sl_drift`: `k′ = k(1±ε)`, recompute the analytic factors.
- `sl_elem`: loop variants through `metrics.score_states` / `field_fast`.

- [ ] **Step 4: Run to pass; full suite**

Run: `python -m pytest tests/test_optimum_robustness.py -q` → 4 passed; `python -m pytest tests -q` → all pass.

---

### Task 5: Report, figures, CLI

**Files:**
- Create: `sim/optimum_search/report.py`
- Create: `sim/optimum_search/__main__.py`
- Create: `sim/optimum_search/__init__.py` exports
- Test: `tests/test_optimum_report.py`

**Interfaces:**
- Consumes: `search`, `robustness`, `render_png` style constants.
- Produces:
  - `front_figure(rows, path)` — SL_cmd vs SL_diag, coloured by SRANGE_0dB; per board count.
  - `trade_figure(rows, path)` — axial vs diagonal scatter with the minimax lines (−3.01 / −3.52 dB).
  - `leader_figures(leaders, out_dir)` — SL_cmd vs θ curves (1°, 0–70) per azimuth for the top 3, plus the 3D/UV renders from `steering_study` helpers.
  - `write_report(rows_2, rows_3, leaders, path)` — front table, rubric columns, recommendations, caveats.
  - `main(argv=None)` — `python -m optimum_search --two --three --out figures/search2`; writes `data/search2/*.csv`, `figures/search2/*.png`, `docs/2026-11-26-optimal-search-report.md`.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_optimum_report.py
import pathlib, sys, csv
import pytest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sim"))
from optimum_search import report as P

ROWS = [{"key": "pair_15.75_2.62", "n_boards": 2, "span_mm": 331.0,
         "SL_cmd": -13.0, "SL_diag": -3.0, "DI0": 38.5,
         "SRANGE_0dB": 24.0, "SRANGE_-3dB": 20.0}]

def test_front_figure(tmp_path):
    out = tmp_path / "front.png"
    P.front_figure(ROWS, out)
    assert out.exists() and out.stat().st_size > 1000

def test_report_contains_front(tmp_path):
    out = tmp_path / "report.md"
    P.write_report(ROWS, ROWS, [], out)
    text = out.read_text(encoding="utf-8")
    assert "pair_15.75_2.62" in text and "SL_cmd" in text
```

- [ ] **Step 2: Run to fail**

Run: `python -m pytest tests/test_optimum_report.py -q`
Expected: import error.

- [ ] **Step 3: Implement** the figures with the existing palette (`render_png` constants), every image a single plot (no montages), and the report table with all rubric columns. `__main__` orchestrates: build candidates → coarse score → refine → SRANGE → robustness on the top 10–20 → front → figures/report.

- [ ] **Step 4: Run the suite**

Run: `python -m pytest tests -q` → all pass.

- [ ] **Step 5: End-to-end smoke**

Run: `python -m optimum_search --two --three --out figures/search2`
Expected: CSVs in `data/search2/`, figures in `figures/search2/`, the report written; the 2-board front contains the minimax and axial-null families; runtime under the budget in the spec.

---

### Task 6: Optimum steering gallery

**Files:**
- Create: `sim/optimum_search/gallery.py`
- Test: `tests/test_optimum_gallery.py`

**Interfaces:**
- Consumes: `model`, `metrics`, `search` (the chosen `Candidate`s), style from `render_png`.
- Produces:
  - `STEERING_STATES = [(theta_deg, phi_deg)]` — θ ∈ {0,5,…,35} × φ ∈ {0,45,90,135,180,225,270,315} (57 states).
  - `render_state(cand, theta, phi, out_dir, du=0.004) -> dict` — writes `3d/steer_TTT_PPP.png`, `polar/…`, `uv/…`, `amplitude/…` for one state; returns its metrics row.
  - `render_optimum(cand, out_dir) -> list[dict]` — loops `STEERING_STATES`, writes `metrics.csv`.
  - Amplitude figure: cut in the **steering plane** (elevation −90…90 along φ), both element cases overlaid, steering and ±54.75° markers.
  - 3D and UV use the compact lit style of `steering_study`; the polar panel is the steering-plane cut.
- The gallery folder per board count is `figures/search2/optimum_2/` and `figures/search2/optimum_3/`. The recommended optimum is the minimum fixed-scale shortlist score on the final front; the runner-up is named in the report.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_optimum_gallery.py
import pathlib, sys
import pytest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sim"))
from optimum_search import gallery as G, model as M

def test_gallery_small(tmp_path):
    cand = M.pair(0.01575, 0.002625)
    rows = G.render_optimum(cand, tmp_path, states=[(0, 0), (20, 45)])
    assert len(rows) == 2
    for sub in ("3d", "polar", "uv", "amplitude"):
        files = list((tmp_path / sub).glob("*.png"))
        assert len(files) == 2 and files[0].stat().st_size > 1000
    assert (tmp_path / "metrics.csv").exists()
```

- [ ] **Step 2: Run to fail** — `python -m pytest tests/test_optimum_gallery.py -q` → import error.

- [ ] **Step 3: Implement** — reuse the fast evaluator on a polar grid for the 3D surface and on the UV grid for the map; the steering-plane cut evaluates a dense elevation arc at azimuth φ; the amplitude overlay evaluates both `isotropic` and `measured`. Ensure directories are created, `metrics.csv` has one row per state (`theta, phi, SL_cmd, SL_near, SL_far`).

- [ ] **Step 4: Run to pass** — `python -m pytest tests -q` → all pass.

- [ ] **Step 5: Render the two galleries** — `python -m optimum_search --gallery` on the chosen optima; expected `2 × 57 × 4 = 456` images plus two `metrics.csv`, runtime within the budget (fast evaluator, `du = 0.004`).

---

## Self-review notes

- Spec coverage: model, metrics, search, robustness, report correspond to §§5–9; the minimax and null families are tested; the mask, commanded level, pruning, 4-bit and SRANGE continuity each have a test.
- Names are used consistently across tasks (`field_fast`, `score_states`, `sl_diag_30`, `robust_max`).
- The plan leaves the exact figure styling and report prose to the implementer; the numeric contract is pinned by tests.
