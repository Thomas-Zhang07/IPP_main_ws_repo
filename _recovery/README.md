# IPP workspace — recovery snapshot

Snapshot of the whole `E:\LUIS\IPP` working directory, taken **2026-11-26**, so the
project can be restored if the local disk is lost.

## What is included

Everything in the workspace except regenerable build output:

- All source code, Quartus project files (`.qpf`, `.qsf`, `.sdc`, …), constraints,
  testbenches, scripts, docs, reports.
- All images (PNG/JPG), figures, HTML, PDFs, videos, measured data and CSVs.
- The standalone ZIP archives that were sitting in the workspace root.
- The **complete working tree of every embedded git repository** as ordinary
  files, including uncommitted changes that existed at snapshot time.
- A full-history git bundle of every embedded repository, under
  `_recovery/bundles/`.

## What is NOT included (regenerable)

- Quartus / ModelSim / Questa build output: `db/`, `incremental_db/`,
  `output_files/` (except `*.sof`), `work/` simulation libraries, `*.qpg`,
  `*.qtl`, `*.qdb`, `*.cdb`, `*.hdb`, `*.ddb`, `*.vho`, `*.sdo`, `*.rpt`,
  `*.summary`, waveforms (`*.wlf`, `*.vcd`), `*.jic`, `*.qws`.
- Python caches (`__pycache__/`, `.pytest_cache/`, …).

Regenerate them by recompiling in Quartus / re-running the simulation.
The `*.jic` flash images were left out because they are rebuilt from the kept
`*.sof` (e.g. with `quartus_cpf`) and because of GitHub's 100 MB per-file limit.

## Embedded repositories

Each embedded repo exists twice in this snapshot:

1. its working tree as ordinary files (all files preserved, `.git` excluded), and
2. `_recovery/bundles/<name>.bundle` with its complete commit history.

| Path | Bundle | Remote | Branch | HEAD |
|---|---|---|---|---|
| `demo/` | `demo.bundle` | https://github.com/Thomas-Zhang07/LUIS_IPP_demo.git | main | `024d19e` |
| `fpga/primary/` | `fpga_primary.bundle` | https://github.com/Thomas-Zhang07/sonic_surface_directional_speaker_fpga_primary.git | main | `1413277` |
| `fpga/secondary/` | `fpga_secondary.bundle` | https://github.com/Thomas-Zhang07/sonic_surface_directional_speaker_fpga_secondary.git | main | `32cf5b1` |
| `fpga/reference/secondary-original/` | `fpga_reference_secondary-original.bundle` | *(none — bundle is the only copy)* | master | `5d3c00c` |
| `other_fpga_code/fpga_code_bak/` | `other_fpga_code_fpga_code_bak.bundle` | https://github.com/Thomas-Zhang07/LUIS_demo_fpga.git | main | `101551b` |
| `SonicSurface/` | `SonicSurface.bundle` | https://github.com/upnalab/SonicSurface.git | main | `d254d69` |

### Restoring a repo's history in place

Run from the snapshot root (the folder containing `demo/`, `fpga/`, …):

```powershell
powershell -ExecutionPolicy Bypass -File _recovery/restore-nested-repos.ps1
```

The script attaches each bundle's history to the existing working tree
(`git init` + `git fetch` + `git reset`), so uncommitted snapshot changes stay
visible as normal modifications.

To get a clean copy of one repo instead:

```bash
git clone _recovery/bundles/demo.bundle demo-restored
```
