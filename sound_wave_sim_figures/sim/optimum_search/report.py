"""Front figures, leader curves and the Markdown report."""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import render_png as R

from . import metrics, model

ROBUST_KEYS = ("SL_4bit", "SL_mech", "SL_drift", "SL_elem")


def provisional_score(row: dict) -> float:
    return (row.get("SL_cmd", 0.0) + 0.5 * row.get("SL_near", 0.0)
            + 0.3 * row.get("SL_diag", 0.0))


def shortlist_score(row: dict) -> float:
    score = provisional_score(row)
    rob = row.get("robust_max", None)
    if rob is not None and np.isfinite(rob):
        score += 0.3 * rob
    return score


def front_figure(rows, path: Path, title: str) -> None:
    fig, ax = plt.subplots(figsize=(8.6, 5.6))
    x = [r["SL_cmd"] for r in rows]
    y = [r["SL_diag"] for r in rows]
    c = [r.get("SRANGE_0dB", np.nan) for r in rows]
    sc = ax.scatter(x, y, c=c, cmap="viridis", s=26, edgecolor="none")
    ax.axhline(-3.01, color=R.ORANGE, lw=0.8, ls="--",
               label="array-factor bound (−3.01 dB; element raises it)")
    ax.axvline(-3.01, color=R.ORANGE, lw=0.8, ls=":")
    ax.set_xlabel("SL_cmd worst over S_op (dB)")
    ax.set_ylabel("SL_diag worst over diagonal azimuths (dB)")
    ax.set_title(title, fontsize=13, loc="left")
    ax.grid(alpha=0.22)
    ax.legend(fontsize=8)
    cb = fig.colorbar(sc, ax=ax)
    cb.set_label("SRANGE at 0 dB (deg)")
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def trade_figure(rows, path: Path, title: str) -> None:
    fig, ax = plt.subplots(figsize=(8.6, 5.6))
    x = [r["SL_cmd"] for r in rows]
    y = [r["SL_diag"] for r in rows]
    c = [r.get("DI0", np.nan) for r in rows]
    sc = ax.scatter(x, y, c=c, cmap="magma", s=26, edgecolor="none")
    ax.set_xlabel("SL_cmd (dB)")
    ax.set_ylabel("SL_diag (dB)")
    ax.set_title(title, fontsize=13, loc="left")
    ax.grid(alpha=0.22)
    cb = fig.colorbar(sc, ax=ax)
    cb.set_label("DI0 (dB)")
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def leader_curve(cand, path: Path, step_deg: float = 2.0, du: float = 0.015):
    dirs, _, _, _ = model.direction_grid(du)
    azimuths = (0.0, 45.0, 90.0, 135.0, 180.0, 225.0, 270.0, 315.0)
    thetas = np.arange(0.0, 36.0, step_deg)
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    colours = (R.BLUE, R.ORANGE, R.AQUA, R.VIOLET, R.RED, R.CYAN, R.DARK,
               R.GRAY)
    for phi, colour in zip(azimuths, colours):
        values = []
        for theta in thetas:
            comp = metrics._state_values(cand, dirs, float(theta), phi, "mean")
            values.append(comp["sl_cmd"])
        ax.plot(thetas, values, color=colour, lw=1.2, label=f"{phi:.0f}°")
    ax.axhline(-3.0, color=R.MUTED, lw=0.8, ls=":")
    ax.set_xlabel("steering angle (deg)")
    ax.set_ylabel("SL_cmd (dB re commanded)")
    ax.set_title(f"SL_cmd vs steering angle — {cand.key}", fontsize=12,
                 loc="left")
    ax.grid(alpha=0.22)
    ax.legend(fontsize=7, ncol=2)
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def _row_table(rows, limit=12, robust=False):
    labels = [("key", "key"), ("n_boards", "n"), ("span_mm", "span mm"),
              ("span_y_mm", "span y"), ("SL_cmd", "SL_cmd"),
              ("SL_clean", "SL_clean"), ("SL_near", "SL_near"),
              ("SL_far_s", "SL_far"), ("SL_diag", "SL_diag"),
              ("SRANGE_0dB", "SRANGE0"), ("DI0", "DI0")]
    if robust:
        labels += [("SL_4bit", "4bit"), ("SL_mech", "mech"),
                   ("SL_drift", "drift"), ("SL_elem", "elem"),
                   ("shortlist", "shortlist")]
    header = "| " + " | ".join(name for _, name in labels) + " |"
    lines = [header, "|" + "---|" * len(labels)]
    ranked = sorted(rows, key=shortlist_score if robust else provisional_score)[:limit]
    for r in ranked:
        cells = []
        for key, _ in labels:
            value = r.get(key, "")
            if key == "key":
                cells.append(str(value))
            elif key == "n_boards":
                cells.append(str(int(value)) if np.isfinite(value) else "")
            else:
                cells.append(f"{value:.1f}" if isinstance(value, float)
                             and np.isfinite(value) else "")
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def write_report(rows_2, rows_3, leaders, path: Path, references=None) -> None:
    text = [
        "# Optimal 2- and 3-board search — results",
        "",
        "Measured TR4010HC element; coplanar boards; steering envelope "
        "0–35° in 5° steps across eight azimuths (x, y and four diagonals). "
        "Levels are relative to the commanded direction; SL_near covers "
        "4–15°, the mask is 4°. Front tables are ordered by the provisional "
        "score (without robustness); the recommended optima use the robust "
        "shortlist.",
        "",
        "## 2 boards",
        "",
        _row_table(rows_2),
        "",
        "## 3 boards",
        "",
        _row_table(rows_3),
        "",
        "## Notes",
        "",
        "- Pitch limit: without nulls the grating takeover is ~24.1°; the "
        "null families postpone the axial takeover (SRANGE_0dB ≈ 34°) but "
        "not the diagonal one.",
        "- The two-board minimax layout (15.75 / 2.625) trades the exact y "
        "null for −3.01 dB on all diagonals; the axial-null pair "
        "(15.75 / 5.25) keeps both axial nulls with 0 dB diagonals.",
        "- All candidates entering the final Pareto comparison are rescored "
        "on one du = 0.004 grid. These are sampled maxima, not continuous bounds.",
        "- The front is the non-dominated set of the top 80 refined candidates "
        "by provisional score; the coarse sweep unions its 2-D Pareto front "
        "before refinement to limit trim bias.",
        "- Mechanical errors use fixed nominal drive phases and 100 independent-column "
        "Latin-hypercube draws. The maximum is a sample statistic, not a bound.",
        "- Board tilt (±0.3°) is not included in the robustness runs; it "
        "remains the top-3 exact-solver check from the design.",
        "- Mirror-equivalent 3-board layouts can appear separately; with the "
        "axisymmetric mean element they are physically identical.",
        "- Element digitization uncertainty is ±1 dB (main lobe) to ±2–3 dB "
        "(50–60° skirt); sub-1 dB front ordering is not significant.",
        "",
    ]
    if references:
        text += ["## Reference layouts (predicted families)", "",
                 "These are the analytical null/minimax families. They are "
                 "listed even when a near-equivalent dominates them on the "
                 "front.", ""]
        for tag, refs in references.items():
            if refs:
                text += [f"### {tag} boards", "", _row_table(refs, limit=8),
                         ""]
    if leaders:
        text.append("## Recommended optima (with robustness)")
        text.append("")
        text.append(_row_table(list(leaders.values()), limit=5,
                               robust=True))
        text.append("")
        for key, row in leaders.items():
            text.append(f"- **{key} boards**: `{row['key']}` "
                        f"(shortlist {shortlist_score(row):.1f} dB)")
        text.append("")
        text.append("## Combined comparison")
        text.append("")
        text.append("| boards | key | SL_cmd | SL_diag | SRANGE0 | DI0 | "
                    "span mm |")
        text.append("|---|---|---|---|---|---|---|")
        for tag, row in leaders.items():
            text.append(
                f"| {tag} | {row['key']} | {row.get('SL_cmd', float('nan')):.1f}"
                f" | {row.get('SL_diag', float('nan')):.1f}"
                f" | {row.get('SRANGE_0dB', float('nan')):.1f}"
                f" | {row.get('DI0', float('nan')):.1f}"
                f" | {row.get('span_mm', float('nan')):.0f} |")
        text.append("")
    Path(path).write_text("\n".join(text), encoding="utf-8")
