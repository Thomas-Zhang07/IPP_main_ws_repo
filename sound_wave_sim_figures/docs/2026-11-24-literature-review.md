# Literature review — directional ultrasonic speakers / SonicSurface

Date: 2026-11-24
Source: Gemini web review, then independently checked.
Files: `references.bib` (BibTeX for all 24 papers), this note.

## Verification status

- **Citations: 24 / 24 verified.** Every DOI resolves through `doi.org`, and
  the Crossref record matches the stated first author, year, title and venue.
  Two parsing quirks: Crossref stores "Chuang Shi" as given/family reversed,
  and the Müller 2025 record encodes "ü" oddly. Neither affects the citation.
- **Numbers: only partly verified.** Crossref has abstracts for a few papers.
  Confirmed from abstracts: Chen et al. 2024 (4 mm inter-array path error
  degrades the focus), Morales et al. 2021 (16 × 16 open-hardware board,
  quantisation limits), Tang et al. 2023 (hyperuniform disorder suppresses
  grating lobes and is duplicatable). The specific dB / degree / SPL values in
  the review table were not re-read from the PDFs — check them when you
  download.

## Verified core references

Grouped by what they are useful for. Full BibTeX in `references.bib`.

### Hardware and the board itself

| Paper | DOI | Why it matters here |
|---|---|---|
| Morales et al. 2021, *Applied Sciences* 11(7):2981 — SonicSurface | 10.3390/app11072981 | The exact 16 × 16, 40 kHz, 10 mm-transducer board; open hardware; phase/amplitude quantisation limits. Open access (MDPI). |
| Marzo et al. 2018, *IEEE TUFFC* 65(1):102–111 — Ultraino | 10.1109/TUFFC.2017.2769399 | Chained driver boards; calibrated 10 mm emitter constant `P0 = 0.17 Pa·m/Vpp`; used to convert normalised dB to SPL. |
| Suzuki et al. 2021, *IEEE Trans. Haptics* 14(4):740–749 — AUTD3 | 10.1109/TOH.2021.3069976 | Multi-board tiling; 0.1 ms module sync as printed in the paper; the reference for scaling beyond one board. |
| Hirayama et al. 2019, *Nature* 575:320–323 | 10.1038/s41586-019-1739-5 | Two opposed 16 × 16 boards (512 elements); direct analogue of the `facing` layout. |

### Grating lobes and array layout

| Paper | DOI | Why it matters here |
|---|---|---|
| Shi & Gan 2011, *IEEE TUFFC* 58(2):437–450 | 10.1109/TUFFC.2011.1821 | Primary grating lobes in a steerable parametric array; Dolph–Chebyshev trade-off. |
| Shi, Kajikawa & Gan 2014, *APSIPA* 3:e20 | 10.1017/ATSIP.2014.18 | Survey of directivity-control methods for PALs. |
| Price & Long 2018, *IEEE IUS* | 10.1109/ULTSYM.2018.8580072 | Fibonacci-spiral array: removes periodic grating lobes without sub-λ/2 pitch. |
| Allevato et al. 2022, *IEEE OJUFFC* 2:40–54 | 10.1109/OJUFFC.2022.3142710 | 64-element Fermat spiral, 40 kHz; ±80° field of view; 152 dB max; 2.3° angular resolution (measured). |
| Allevato et al. 2023, *IEEE OJUFFC* 3:113–127 | 10.1109/OJUFFC.2023.3303132 | Two-scale spiral: density shaping instead of amplitude tapering. |
| Tang et al. 2023, *Phys. Rev. Applied* 19:054035 | 10.1103/PhysRevApplied.19.054035 | Tileable hyperuniform disordered 200-element array; the most direct aperiodic benchmark. arXiv:2301.00833. |
| Mordret & Grushin 2025, *Phys. Rev. Applied* 23:034021 | 10.1103/PhysRevApplied.23.034021 | Aperiodic monotile arrays; scale-invariant array-factor result, not a 40 kHz experiment. |
| Zhong et al. 2023, *IEEE/ACM TASLP* 31:3152–3161 | 10.1109/TASLP.2023.3304491 | Sparse random 1D array for a steerable parametric source; simulated vs measured PSL gap. |
| Mei et al. 2026, *Modelling* 7(1):20 | 10.3390/modelling7010020 | PSO non-uniform spacing on a small 8-element PAL; useful only as a method reference. |

### Curved / tilted arrays and multi-board calibration

| Paper | DOI | Why it matters here |
|---|---|---|
| Guasch & Sánchez-Martín 2018, *Appl. Math. Model.* 60:721–738 | 10.1016/j.apm.2018.04.002 | Far-field directivity of emitters on curved surfaces; backs the V and concave layouts. |
| Chen et al. 2024, *JASA* 156(6):3838–3851 | 10.1121/10.0034559 | Multi-unit pose calibration; 4 mm path error already damages the focus. Open access. |
| Müller et al. 2025, *Signal Processing* 230:109812 | 10.1016/j.sigpro.2024.109812 | Per-element gain/phase calibration from measured data. arXiv:2406.14355. |

### Audio-side (parametric) and limits

| Paper | DOI | Why it matters here |
|---|---|---|
| Westervelt 1963, *JASA* 35(4):535–537 | 10.1121/1.1918525 | Parametric-array theory. |
| Yoneyama et al. 1983, *JASA* 73(5):1532–1536 | 10.1121/1.389414 | First airborne audio spotlight. |
| Gan, Yang & Kamakura 2012, *Applied Acoustics* 73(12):1211–1219 | 10.1016/j.apacoust.2012.04.001 | PAL review: modulation, distortion, ~60 dB conversion loss, exposure. |
| Olszewski et al. 2005, *Interspeech* | 10.21437/Interspeech.2005-87 | Early steerable commercial audio beam. |
| Ochiai et al. 2017, *CHI* | 10.1145/3025453.3025989 | Holographic Whisper: focused audible spots instead of a broadside beam. |
| Geng et al. 2022, *Applied Acoustics* 200:109060 | 10.1016/j.apacoust.2022.109060 | Peripheral π-phase inversion as an alternative to amplitude tapering. |
| Malkin et al. 2023, *J. Sound Vib.* 552:117644 | 10.1016/j.jsv.2023.117644 | Nonlinear effects become significant above ~150 dB SPL; no single 165 dB threshold is stated. |
| Zhu et al. 2025, *JASA* 157(2):962–975 | 10.1121/10.0035797 | Multi-channel nonlinear control in reflective rooms; 20 mm spacing fails at 15° steering. |

## Reading the results against our model

1. **Most of these papers do not report our metrics.** They report the
   demodulated audio pattern, focal pressure, or haptic spot size. Our
   `DI`, `-6 dB beamwidth`, `50–60° band peak` and `band energy` are primary
   40 kHz field metrics and are rarely tabulated. Direct comparisons of our
   35.5–40.3 dB DI with their numbers are therefore loose.
2. **The 23 % band-energy figure is a property of the periodic lattice.** The
   four grating lobes of a 10.5 mm grid carry a fixed share of power; a seam or
   half-pitch offset moves energy between the lobe centre and its shoulders,
   it does not remove it. This matches our seam sweep (0.52–0.74 % >60°,
   23.3–24.3 % band energy across all seams).
3. **Aperiodic layouts lower the peak, not necessarily the band energy.**
   Tang et al. spread the grating energy into a pedestal; the peak drops by
   ~15 dB, but energy is redistributed over the hemisphere. If our goal is
   "less power in 50–60°", aperiodic is not automatically better; if the goal
   is "no strong lobe at 54.75°", it is the right route. This distinction is
   worth stating explicitly in the report.
4. **Changing the PCB is the only route to the published aperiodic numbers.**
   With the existing 16 × 16, 10.5 mm boards, the search shows the floor:
   band peak ≈ −14.7 dB (2 boards), −16.0 dB (3 boards), and the exact null
   only with 15.75 / 5.25 plus calibration. A spiral/HUD board could target
   −18 dB, but that is a new PCB, not a fixture change.
5. **Our null is not the benchmark to chase.** Published arrays do not rely on
   a coherent point null; they are judged on peak sidelobe/grating-lobe level
   and steering range. Our tolerance run agrees: random errors leave the null
   deep, but a 0.1 % sound-speed drift lifts it to −38 dB and 0.35 % to about
   −28 dB. Quote the band
   peak, not the null.

## What to aim for

| Metric | Published reference | Our ideal model | Realistic target with current boards |
|---|---|---|---|
| DI (forward hemisphere) | rarely reported; 2.3° angular resolution, 200 mm spiral (Allevato 2022) | 35.5 / 38.5 / 40.3 dB (1/2/3 boards) | ≥ 38 dB measured for the pair |
| −6 dB beamwidth | not reported in the abstract (2.3° is angular resolution) | 3.5 × 3.5° → 1.1 × 3.5° | ≤ 2.0° in x after calibration |
| Grating-band peak | −3.8 dB periodic vs −18.7 dB HUD at 40 kHz, measured (Tang 2023) | −14.7 dB (pair), −16.0 dB (3-board) | ≤ −15 dB measured |
| 50–60° band energy | not tabulated in PAL papers | ~23 % (all periodic layouts) | report honestly; do not claim reduction |
| Exact 54.75° null | not a published metric | < −60 dB ideal | only with phase calibration and temperature stability; not an acceptance criterion |
| Primary SPL at 1 m | > 120 dB (PALs); 152 dB max (Allevato 2022); 154.6–158.6 dB at focus (Hirayama 2019) | not modelled | 130–145 dB at 1 m; nonlinear above ~150 dB |
| Audible output | ~60 dB conversion loss; 60–85 dB at 1–3 m | not modelled | 70–80 dB at 1–2 m, THD < 5 % with SSB/SRAM |
| Multi-board sync / pose | 0.1 ms module sync as printed (AUTD3); 4 mm path error matters (Chen 2024) | ideal | < 1 µs sync; ±1 mm pose, per-channel phase calibration |

## Suggested download order (open access first)

1. **Tang et al. 2023** — arXiv:2301.00833 (the aperiodic benchmark).
2. **Morales et al. 2021** — MDPI `app11072981` (your board).
3. **Allevato et al. 2022** — IEEE OJ / TUprints (spiral, calibration).
4. **Marzo et al. 2018** — IEEE (P0 and chaining).
5. **Suzuki et al. 2021** and **Chen et al. 2024** (multi-board sync and pose).
6. **Shi & Gan 2011** (grating lobes in a steerable PAL).
7. **Gan et al. 2012** (audio modulation and exposure).
8. **Hirayama et al. 2019** (opposed 16 × 16 pair).

Open-access links supplied with the review (check each before downloading):
arXiv 2301.00833, arXiv 2406.14355, arXiv 2408.16476, MDPI
`2076-3417/11/7/2981`, MDPI `2673-3951/7/1/20`, IEEE OJUFFC 2022/2023,
JASA `10.1121/10.0034559`, ISCA `10.21437/Interspeech.2005-87`, Sussex
repository for Hirayama, NTU handle for Gan 2012.

## What to extract from each PDF

- **Tang 2023:** exact array layout, average spacing, measurement distance,
  PSLL definition (peak vs integrated), steering angles, and whether the
  comparison at 40 kHz is primary or demodulated.
- **Morales 2021:** phase/amplitude quantisation curves and the field-error
  metric; confirm the 16 × 16 geometry and driver chain.
- **Allevato 2022:** calibration procedure, measured phase spread, SPL at 1 m,
  and the definition of "grating-lobe-free" (peak level).
- **Marzo 2018:** `P0` and its measurement conditions, so our normalised dB
  can be turned into SPL.
- **Suzuki 2021 / Chen 2024:** sync jitter and the 4 mm pose sensitivity.
- **Shi & Gan 2011:** how primary grating lobes map to the audible product.
- **Gan 2012:** modulation schemes and exposure limits.
- **Hirayama 2019:** opposed-board cavity geometry and SPL calibration.

## Caveats

- Checked against the downloaded PDFs (2026-11-25): Tang's PSLL values
  (−3.8 → −18.7 dB at 40 kHz; −9.3 → −21.8 dB at 30 kHz, measured at 2 m) and
  Allevato's 64 elements / 200 mm / 152 dB / ±80° FoV / 2.3° angular
  resolution are confirmed. Hirayama's focus levels are 154.6–158.6 dB.
  Suzuki reports 0.1 ms module sync as printed (not 0.1 µs). Malkin states
  nonlinearity above ~150 dB SPL, not a 165 dB threshold. No ±40° phase-spread
  figure was found in the Allevato text. Shi & Gan report 8.3–12.0 dB grating
  lobe reduction at the difference frequency for the steered cases.
- Mordret & Grushin 2025 is an aperiodic-array theory paper, not a 40 kHz
  loudspeaker experiment; useful for the tiling concept, not for a measured
  target.
- Most PAL papers optimise demodulated audio, not the 40 kHz primary field.
  Our figures are primary-field, so comparisons must state that.
