# Transducer directivity module — design

Date: 2026-11-25
Status: approved (approach A)
Location: `sim/transducer/`

## Intent

The sim currently models every emitter as an ideal 10 mm baffled piston
(`D(β) = 2J₁(x)/x`, DI 11.4 dB). The real part is the TR4010HC series (10 mm,
40 kHz), whose only directivity data is the measured polar chart in the
photographed datasheet `transducers.jpg`. Encode that measured pattern as a
reproducible, auditable artifact so the later sim update can replace the ideal
piston with the real element, and so the directivity gain is documented with
its uncertainty.

## Goals

- Digitize the polar chart from the jpg with a script (not by hand);
  commit the resulting data and a diagnostic overlay.
- A loader exposing the pattern (`level_db`, `amplitude`) and derived
  quantities (`DI_DB`, `Q`, `beamwidth_6db`).
- Document provenance, method, calibration constants and uncertainty.
- Tests that pin the extraction and the derived numbers.

## Non-goals

- Absolute SPL calibration.
- Azimuth-dependent 3-D interpolation — only one cut exists.
- Swapping the pattern into `field.py` or the sim (a separate update).
- Incorporating competitor/variant datasheets.

## Anti-goals

- Quoting a DI the chart cannot support (e.g. the smoothed 12.0 dB read).
- Treating the chart as two overlaid orthogonal cuts.
- Mixing 2π (half-space) and 4π (standard) directivity conventions.

## Constraints

- Sole source: `transducers.jpg` (2160 × 2250 px). It is a photograph, so the
  chart geometry must be calibrated in the script.
- Datasheet spec: total beam angle −6 dB = 80° ± 12°. Chart rings 0…−30 dB in
  6 dB steps, spokes every 30°, one asymmetric trace.
- Python 3.13, numpy, matplotlib, pytest — the existing requirements.

## Approaches considered

- **A (chosen): measured cut → CSV → loader + tests.** Reproducible from the
  jpg; keeps the real shape, which drives leak and grating-lobe numbers.
- B, scalar DI only — rejected: discards the shape that matters.
- C, analytic fit — rejected: smooths away real side lobes and still needs
  the digitized data underneath.

## Decisions

- **DI convention:** standard 4π. With rotational symmetry,
  `Q = 2 / ∫₀^π P(θ) sinθ dθ` and `DI = 10 log₁₀ Q`. This matches the sim's
  DI metric. Gemini's 9.1 dB "DI₂π" is a different convention and is not used.
- **3-D interpretation:** power-average the left and right halves into one
  axisymmetric pattern. Both halves remain in the data and the spread is
  documented (right 11.8 dB, left 10.6 dB, mean 11.2 dB).
- **Headline number:** DI ≈ 11 dB, uncertainty ±1 dB; the beam-tolerance
  range is 9.4–12.2 dB.
- **Calibration for this image:** chart centre (1506, 1820) px, 0 dB radius
  297 px, 45 px per 6 dB, spokes bridged over ±2.5°. The script asserts the
  image size and writes `overlay.png` for visual verification.
- **Rear response:** keep the measured −30…−36 dB rear floor in the data.
  The sim's "zero behind the board" stays a sim-side baffle assumption.
- **Electrical spec versions:** the user's sheet (105 dB SPL, −73 dB rx,
  2000 pF, 80 Vpp) and the Yujie web page (120 dB, −63 dB, 2550 pF, 100 Vpp)
  both state the same 80° ±12° beam; the directivity work is unaffected.

## Left to the builder

File and API names, test tolerances, README wording, and the exact treatment
of angles near spokes and the chart's geometric distortion.
