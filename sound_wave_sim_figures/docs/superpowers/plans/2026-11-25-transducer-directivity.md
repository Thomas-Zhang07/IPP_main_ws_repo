# Transducer Directivity Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Digitize the TR4010HC measured polar chart from `transducers.jpg` into committed, reproducible data, and expose it through a small `sim/transducer` package for later simulation use.

**Architecture:** `digitize.py` calibrates the photographed chart (fixed centre, 0 dB radius, 6 dB ring spacing), extracts the trace for both halves of the asymmetric cut, writes `directivity.csv` and a diagnostic `overlay.png`. `directivity.py` loads that CSV and exposes the pattern plus derived 4π directivity and −6 dB beamwidth. Tests pin the extraction and the derived numbers.

**Tech Stack:** Python 3.13, numpy, Pillow (new dependency), pytest.

**Spec:** `docs/2026-11-25-transducer-directivity-design.md`

## Global Constraints

- Sole data source is `transducers.jpg` at the project root (2160 × 2250 px). No other vendor data.
- Directivity convention is standard **4π**: `Q = 2 / ∫₀^π P(θ) sinθ dθ`, `DI = 10 log₁₀ Q`.
- Digitizing constants are tied to this image: centre `(cx, cy) = (1506, 1820)`, 0 dB radius `R0 = 297.0` px, `45.0` px per 6 dB.
- Dependencies: existing `numpy>=2.0`, `matplotlib>=3.9`, `pytest>=8.0`; add `pillow>=10`.
- Tests run from the project root: `python -m pytest tests -q`; new tests insert `sim/` on `sys.path` exactly as `tests/test_field.py` does.
- The workspace is **not** a git repository, so there are no commit steps; each task ends with commands and expected output.
- No absolute paths in code; locate the image and CSV relative to the module/test file.

## Review Focus

- Image missing or renamed → `digitize.extract` raises `FileNotFoundError` with the path, while the loader still works from the committed CSV.
- A different photo fed to the digitizer → `check_image` rejects anything but 2250 × 2160 × 3, and `overlay.png` shows whether the trace was tracked.
- Angle outside 0–180° passed to `level_db` → `ValueError`, not silent extrapolation.
- `cos β` outside [−1, 1] (numerical noise) → clipped, finite result.
- Stale or hand-edited CSV → tests pin DI ≈ 10.8 dB, half-angles and a fresh extraction match the CSV within 1 dB RMS.

---

### Task 1: Chart digitizer and committed data

**Files:**
- Create: `sim/transducer/digitize.py`
- Create: `sim/transducer/directivity.csv` (generated, then committed)
- Create: `sim/transducer/overlay.png` (generated, then committed)
- Modify: `requirements.txt` (add `pillow>=10`)
- Test: `tests/test_transducer_digitize.py`

**Interfaces:**
- Consumes: `transducers.jpg` at the project root.
- Produces:
  - `check_image(img: np.ndarray) -> None` — raises `ValueError` unless `img.shape == (2250, 2160, 3)`.
  - `extract(image_path: Path | str) -> dict` with keys `angles_deg` (361 values, 0.0…180.0 at 0.5°), `db_right`, `db_left`, `db_mean_power` (each shape `(361,)`), `q` (float), `di_db` (float), `half_right_deg` (float), `half_left_deg` (float).
  - `write_outputs(result: dict, out_dir: Path) -> tuple[Path, Path]` — writes `directivity.csv` (header `angle_deg,db_right,db_left,db_mean_power`) and `overlay.png`.
  - `main(argv=None) -> None` — CLI entry; default image is `<project root>/transducers.jpg`, default out dir is the module directory.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_transducer_digitize.py
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sim"))

import transducer.digitize as dg  # noqa: E402

IMAGE = ROOT / "transducers.jpg"
CSV = ROOT / "sim" / "transducer" / "directivity.csv"


@pytest.fixture(scope="module")
def extracted():
    if not IMAGE.exists():
        pytest.skip("source image not present")
    return dg.extract(IMAGE)


def test_check_image_rejects_wrong_shape():
    with pytest.raises(ValueError):
        dg.check_image(np.zeros((10, 10, 3), dtype=int))


def test_extract_grid(extracted):
    assert extracted["angles_deg"].shape == (361,)
    assert extracted["angles_deg"][0] == 0.0
    assert extracted["angles_deg"][-1] == 180.0
    assert extracted["db_right"].shape == (361,)
    assert extracted["db_left"].shape == (361,)
    assert extracted["db_mean_power"].shape == (361,)
    assert np.all(np.isfinite(extracted["db_mean_power"]))


def test_derived_numbers(extracted):
    assert extracted["di_db"] == pytest.approx(11.2, abs=0.6)
    assert 38.5 <= extracted["half_right_deg"] <= 43.5
    assert 41.0 <= extracted["half_left_deg"] <= 45.0


def test_missing_image_raises():
    with pytest.raises(FileNotFoundError):
        dg.extract(ROOT / "no_such_image.jpg")


def test_csv_matches_extraction(extracted):
    if not CSV.exists():
        pytest.skip("csv not generated yet")
    tab = np.genfromtxt(CSV, delimiter=",", names=True)
    rms = np.sqrt(np.mean((tab["db_mean_power"] - extracted["db_mean_power"]) ** 2))
    assert rms < 1.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_transducer_digitize.py -q`
Expected: collection error — `ModuleNotFoundError: No module named 'transducer'`.

- [ ] **Step 3: Implement `sim/transducer/digitize.py`**

Exact pipeline (the constants are calibrated on this photograph):

1. `check_image(img)` — assert `img.shape == (2250, 2160, 3)`, else `ValueError`.
2. Load with `PIL.Image.open(path).convert("RGB")` → `np.asarray(..., dtype=int)`; missing file naturally raises `FileNotFoundError`.
3. Pink trace mask: `(R - G > 14) & (R - B > 8) & (R > 170) & (G > 135)` (the curve is light pink; the dB labels are darker red and fail `G > 135`).
4. For each angle `a = 0, 0.25, …, 359.75` (1440 samples), walk radius `r = 15.0 … 329.5` in 0.5 px steps from centre `(1506, 1820)` with `y = cy - r*cos(a)`, `x = cx + r*sin(a)`; record the largest pink radius, else `NaN`.
5. Blank every sample within ±2.5° of a 30° spoke (`0, 30, …, 330`) — the dark axis lines overwrite the curve — then linearly interpolate across the resulting gaps.
6. Convert: `db = -6.0 * (297.0 - r) / 45.0`.
7. Smooth circularly with a 9-point box filter (2.25° at this sampling).
8. Collapse to `0…180` at 0.5° via `np.interp`: `db_right(θ) = profile(θ)`, `db_left(θ) = profile(360 - θ)`, `db_mean_power = 10*log10((10**(right/10) + 10**(left/10))/2)`.
9. Derived numbers from the collapsed grid:
   - `q = 2 / np.trapezoid(10**(db_mean_power/10) * sin(radians(angles)), radians(angles))`
   - `di_db = 10*log10(q)`
   - `half_right_deg` / `half_left_deg` = first angle where the respective level ≤ −6.0.
10. `write_outputs` writes the CSV with `f"{a:.2f},{r:.3f},{l:.3f},{m:.3f}"` rows and draws the detected points (blue) onto a crop `(1150, 1500, 1980, 2180)` of the original, saved as `overlay.png`.
11. `main()` prints `DI … dB`, `half-angles …`, `Q …` and the two written paths.

- [ ] **Step 4: Generate the data**

Run: `python sim/transducer/digitize.py`
Expected: `directivity.csv` (361 rows + header) and `overlay.png` written; printed DI ≈ 10.8 dB, half-angles ≈ 41° / 43°.

- [ ] **Step 5: Inspect the overlay**

Open `sim/transducer/overlay.png` and check the blue points sit on the pink trace all the way round, including the side lobes. If they do not, the calibration constants are wrong — stop and fix before continuing.

- [ ] **Step 6: Run the tests**

Run: `python -m pytest tests/test_transducer_digitize.py -q`
Expected: 5 passed.

- [ ] **Step 7: Add the dependency**

Append `pillow>=10` to `requirements.txt`.

---

### Task 2: Loader, package surface, documentation

**Files:**
- Create: `sim/transducer/directivity.py`
- Create: `sim/transducer/__init__.py`
- Create: `sim/transducer/README.md`
- Test: `tests/test_transducer_directivity.py`

**Interfaces:**
- Consumes: `sim/transducer/directivity.csv` from Task 1.
- Produces (re-exported from `transducer/__init__.py`):
  - `load(path=DATA_PATH) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]` — `(angles_deg, db_right, db_left, db_mean_power)`.
  - `level_db(theta_deg, half="mean") -> float | np.ndarray` — `half ∈ {"left", "right", "mean"}`; `ValueError` if any angle outside 0–180 or unknown `half`.
  - `amplitude(cos_beta) -> float | np.ndarray` — `10**(level_db(degrees(arccos(clip(cos_beta, -1, 1))), "mean") / 20)`; equals 1.0 on axis.
  - `q() -> float`, `di_db() -> float`, module constant `DI_DB`.
  - `half_angle_6db(half) -> float` (`"left"` or `"right"`), `beamwidth_6db() -> float` = left + right.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_transducer_directivity.py
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sim"))

import transducer  # noqa: E402
from transducer import directivity as tr  # noqa: E402


def test_public_api():
    for name in ("level_db", "amplitude", "di_db", "q",
                 "half_angle_6db", "beamwidth_6db", "DI_DB"):
        assert hasattr(transducer, name)


def test_on_axis():
    assert tr.level_db(0.0) == pytest.approx(0.0, abs=0.3)
    assert tr.amplitude(1.0) == pytest.approx(1.0, abs=1e-6)


def test_di_and_q():
    assert tr.di_db() == pytest.approx(11.2, abs=0.6)
    assert tr.q() == pytest.approx(10 ** (tr.di_db() / 10.0), rel=1e-6)
    assert tr.DI_DB == pytest.approx(tr.di_db(), rel=1e-9)


def test_beamwidth():
    right = tr.half_angle_6db("right")
    left = tr.half_angle_6db("left")
    assert 38.5 <= right <= 43.5
    assert 41.0 <= left <= 45.0
    assert tr.beamwidth_6db() == pytest.approx(left + right, rel=1e-9)


def test_asymmetry_is_kept():
    assert tr.level_db(45.0, "left") - tr.level_db(45.0, "right") > 3.0


def test_amplitude_clips_outside_unit_range():
    clipped = tr.amplitude(np.array([-1.5, 1.5]))
    exact = tr.amplitude(np.array([-1.0, 1.0]))
    assert np.allclose(clipped, exact)
    assert np.all(np.isfinite(clipped))


def test_angle_out_of_range_raises():
    with pytest.raises(ValueError):
        tr.level_db(200.0)


def test_rear_is_not_zero():
    assert tr.level_db(180.0) < -30.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_transducer_directivity.py -q`
Expected: `ModuleNotFoundError: No module named 'transducer'` (the package exists only once `__init__.py` is written).

- [ ] **Step 3: Implement `sim/transducer/directivity.py`**

- Load with `np.genfromtxt(DATA_PATH, delimiter=",", names=True)` inside a module-level memoised function; `DATA_PATH = Path(__file__).with_name("directivity.csv")`.
- `level_db`: validate `half`; `np.interp` over the chosen half; raise `ValueError` when `np.min(theta) < 0` or `np.max(theta) > 180`.
- `q()`: the 4π integral from the mean-power curve (same formula as Task 1).
- Cache the arrays and derived numbers at module level; `DI_DB = di_db()`.

- [ ] **Step 4: Implement `sim/transducer/__init__.py`**

Re-export `load`, `level_db`, `amplitude`, `q`, `di_db`, `DI_DB`, `half_angle_6db`, `beamwidth_6db`, and define `__all__`.

- [ ] **Step 5: Run the tests**

Run: `python -m pytest tests -q`
Expected: all tests pass (existing 9 + new 5 + new 8).

- [ ] **Step 6: Write `sim/transducer/README.md`**

Cover, in plain language: the sole source (`transducers.jpg`, TR4010HC series, 10 mm, 40 kHz); the sheet's 80° ±12° −6 dB beam; the extraction method and calibration constants; the 4π convention; the derived numbers (DI ≈ 10.8 dB, Q ≈ 12, half-angles ≈ 41°/43°, side lobes ≈ −21 dB at ±75–80°, rear −31…−36 dB); uncertainty ±1 dB plus the spec-tolerance range 9.4–12.2 dB; that the pattern is used as a power-average of the two halves (axisymmetric) with both halves retained in the CSV; how a future sim update should use `amplitude(cos β)` in place of `field.piston_directivity`, with the "zero behind the board" baffle assumption left as a sim-side decision; and the two electrical spec versions (user sheet vs Yujie page) that share the same 80° beam.

---

## Self-review notes

- Spec coverage: digitizer, loader, data, docs, tests, uncertainty and conventions are all in Tasks 1–2. Non-goals (SPL, azimuth interpolation, sim integration) are untouched.
- Numeric pins match the pixel verification after on-axis normalization: right half DI 11.8 dB, left 10.6 dB, mean 11.2 dB; half-angles 39.0° / 42.0° (beamwidth 81°).
- Types and names are used consistently across both tasks (`extract` dict keys = CSV columns = `load` outputs).
