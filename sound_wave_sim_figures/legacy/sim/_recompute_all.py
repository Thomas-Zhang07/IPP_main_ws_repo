import csv, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cache, geometry, optimize, render_png

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "figures"

def to_row(lay, m):
    return {"key": lay.key, "short": lay.title, "n_boards": len(lay.boards),
            "di_db": m["di_db"], "lobe_54_75_db": m["lobe_54_75_db"],
            "band_max_db": m["band_max_db"],
            "band_energy_pct": m["band_energy_pct"],
            "leak_60_pct": m["leak_60_pct"], "bw6_xz_deg": m["bw6_xz_deg"],
            "bw6_yz_deg": m["bw6_yz_deg"], "on_axis_db": m["on_axis_db"]}

def main():
    rows = []
    for lay in geometry.baseline_layouts():
        if not lay.far_field:
            rows.append({"key": lay.key, "short": lay.title,
                         "n_boards": len(lay.boards), "di_db": None,
                         "lobe_54_75_db": None, "band_max_db": None,
                         "band_energy_pct": None, "leak_60_pct": None,
                         "bw6_xz_deg": None, "bw6_yz_deg": None,
                         "on_axis_db": None})
            continue
        m = cache.analysis(lay, du=0.004)
        render_png.far_field_png(lay, m, FIG / lay.key / "farfield.png")
        rows.append(to_row(lay, m)); print("far", lay.key, round(m["bw6_xz_deg"],2))

    best = json.load(open(ROOT / "data" / "best.json", encoding="utf-8"))
    verdict = json.load(open(ROOT / "verdict.json", encoding="utf-8"))
    verdict["best_pair"] = best["best_pair"]
    verdict["best_three"] = best["best_three"]
    json.dump(verdict, open(ROOT / "verdict.json", "w", encoding="utf-8"), indent=2)
    lay = optimize.layout_from_row(verdict["best_three"])
    m = cache.analysis(lay, du=0.003)
    render_png.far_field_png(lay, m, FIG / "opt3" / "farfield.png")
    rows.append(to_row(lay, m)); print("opt3", round(m["bw6_xz_deg"],2), m["band_max_db"])

    # alternative pair
    cand = list(csv.DictReader(open(ROOT / "data" / "candidates.csv", encoding="utf-8-sig")))
    alt = min([r for r in cand if r["kind"]=="pair" and float(r["lobe_54_75_db"])>-60
               and float(r["on_axis_db"])>-0.5], key=lambda r: float(r["band_max_db"]))
    alt_lay = optimize.layout_from_row(alt); alt_lay.key="05_alt"
    alt_lay.title="Pair 16.54 / 5.25 (no null)"
    am = cache.analysis(alt_lay, du=0.004)
    rows.append(to_row(alt_lay, am)); print("alt", round(am["bw6_xz_deg"],2))

    fields = ["key","short","n_boards","di_db","lobe_54_75_db","band_max_db",
              "band_energy_pct","leak_60_pct","bw6_xz_deg","bw6_yz_deg","on_axis_db"]
    with open(ROOT/"metrics.csv","w",newline="",encoding="utf-8") as fh:
        w=csv.DictWriter(fh,fieldnames=fields); w.writeheader()
        for r in rows:
            w.writerow({k:("" if r.get(k) is None else r.get(k)) for k in fields})
    render_png.comparison_png(rows, FIG/"comparison.png")
    render_png.comparison_png(rows, FIG/"comparison_left.png", only=[0,1,2])
    render_png.comparison_png(rows, FIG/"comparison_right.png", only=[3,4,5])
    cur = next(r for r in rows if r["key"]=="05_coplanar_gap")
    opt = next(r for r in rows if r["key"]=="opt3")
    render_png.pareto_png(cand, FIG/"pareto.png", current=cur, optimal=opt,
                          alternative=alt)
    print("done", len(rows))

if __name__ == "__main__":
    main()
