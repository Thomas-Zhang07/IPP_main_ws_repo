import csv, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cache, geometry, render_png, export_web

ROOT = Path(__file__).resolve().parents[1]
lay = geometry.butt_offset()
m = cache.analysis(lay, du=0.004)
near = cache.near(lay, res=0.005)
fig = ROOT / "figures" / lay.key
fig.mkdir(parents=True, exist_ok=True)
render_png.far_field_png(lay, m, fig / "farfield.png")
render_png.near_field_png(lay, near, fig / "nearfield.png")
export_web.write_page(lay, m, near, ROOT / "web")
row = {
    "key": lay.key, "short": lay.title, "n_boards": 2,
    "di_db": m["di_db"], "lobe_54_75_db": m["lobe_54_75_db"],
    "band_max_db": m["band_max_db"], "band_energy_pct": m["band_energy_pct"],
    "leak_60_pct": m["leak_60_pct"], "bw6_xz_deg": m["bw6_xz_deg"],
    "bw6_yz_deg": m["bw6_yz_deg"], "on_axis_db": m["on_axis_db"],
}
fields = ["key", "short", "n_boards", "di_db", "lobe_54_75_db", "band_max_db",
          "band_energy_pct", "leak_60_pct", "bw6_xz_deg", "bw6_yz_deg", "on_axis_db"]
rows = list(csv.DictReader(open(ROOT / "metrics.csv", encoding="utf-8-sig")))
rows = [r for r in rows if r["key"] != lay.key] + [row]
with open(ROOT / "metrics.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows(rows)
rows2 = []
for r in rows:
    for k in ("di_db", "on_axis_db", "lobe_54_75_db", "band_max_db",
              "band_energy_pct", "leak_60_pct", "bw6_xz_deg", "bw6_yz_deg"):
        try: r[k] = float(r[k])
        except (TypeError, ValueError): r[k] = None
    try: r["n_boards"] = int(r["n_boards"])
    except (TypeError, ValueError): r["n_boards"] = 0
    rows2.append(r)
render_png.comparison_png(rows2, ROOT / "figures" / "comparison.png")
import build_overlay
build_overlay.main()
print("done", lay.key)
