# Legacy — original ideal-piston study (archived)

This folder holds the first-generation work, kept for reference. It is **not**
part of the current pipelines and its results are superseded by the
measured-transducer work in `sim/transducer` and `sim/optimum_search`.

| Path | What |
|---|---|
| `figures/` | per-layout far-field/near-field PNGs, 3D renders, comparison, Pareto, tolerance and study scans (ideal 10 mm piston, broadside) |
| `web/` | interactive 3D HTML pages, index and two-layout overlay |
| `data/` | `baselines.json`, `best.json`, `candidates.csv`, npz caches |
| `docs/` | original model design and two-board sensitivity notes |
| `sim/` | `run_all.py`, `optimize.py`, `cache.py`, `export_web.py`, finalizers and the scratch fix/add scripts |
| `metrics.csv`, `verdict.json` | original study numbers |

The archived scripts assume their original locations under `sim/`. To rerun
one, move it back (or set `PYTHONPATH` to the current `sim/` and correct its
`ROOT`), and expect the old ideal-piston outputs.
