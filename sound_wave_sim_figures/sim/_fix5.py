import pathlib

# ---- render: tolerance two panels, pareto fixes, comparison null label
r = pathlib.Path("sim/render_png.py")
s = r.read_text(encoding="utf-8")


def rep(old, new):
    global s
    if old not in s:
        raise SystemExit("RENDER NOT FOUND: " + old[:120])
    s = s.replace(old, new)


# comparison: clipped-null label outside the bar
rep('''            if clip and raw <= -60.0:
                ax.text(-56.0, yi, "< −60", va="center", ha="left",
                        fontsize=7.5, color=INK_2)
                continue''',
'''            if clip and raw <= -60.0:
                ax.text(1.0, yi, "< −60 (null)", va="center", ha="left",
                        fontsize=7.5, color=INK_2)
                continue''')

# pareto: focus range, no numeric labels, better optimum annotation
rep("""        if _kind_family(r) in ("pair", "v", "three", "control"):
            pts.append((float(di), float(pk), r))""",
"""        if di < 33.0:
            continue
        if _kind_family(r) in ("pair", "v", "three", "control"):
            pts.append((float(di), float(pk), r))""")
rep("""        low = min(front, key=lambda p: p[1])
        top = max(front, key=lambda p: p[0])
        for p_, dx, dy, ha in ((low, 10, -12, "left"), (top, -8, 8, "right")):
            ax.annotate(f"{p_[1]:.1f} dB", (p_[0], p_[1]), xytext=(dx, dy),
                        textcoords="offset points", fontsize=7.5,
                        color=INK_2, ha=ha)
""", "")
rep("""        ax.annotate("optimum", (optimal["di_db"], optimal["band_max_db"]),
                    xytext=(14, -14), textcoords="offset points",
                    fontsize=8.5, color=INK)""",
"""        ax.annotate("optimum", (optimal["di_db"], optimal["band_max_db"]),
                    xytext=(-16, 12), textcoords="offset points",
                    fontsize=8.5, color=INK, ha="right")""")

# tolerance: two panels, y-range that shows the null
start = s.index("def tolerance_png")
new = '''def tolerance_png(layout, path: Path, sigmas=(0, 2, 5, 10, 15), trials=24,
                  seed=0) -> None:
    """Random errors barely fill the null; a systematic k shift moves it."""
    rng = np.random.default_rng(seed)
    U2, V2, mask, dirs, el, az, _ = field.uv_grid(0.02)
    band = (el >= 50.0) & (el <= 60.0)
    lobe_dirs = np.stack([
        field.dir_from_angles(C.GRATING_ANGLE_DEG, a)
        for a in (0.0, 90.0, 180.0, -90.0)
    ])
    amps = layout.amplitudes()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.2, 4.9))

    band_med, lobe_med = [], []
    for sigma in sigmas:
        bp, lb = [], []
        for _ in range(trials):
            phases = np.radians(rng.normal(0.0, sigma, len(amps)))
            gain = amps * 10 ** (rng.normal(0.0, 0.5, len(amps)) / 20.0)
            p_axis = abs(field.far_field(
                layout.positions, layout.normals, gain,
                np.array([[0.0, 0.0, 1.0]]), phases=phases)[0])
            grid = abs(field.far_field(layout.positions, layout.normals, gain,
                                       dirs, phases=phases))
            db = 20 * np.log10(np.maximum(grid / p_axis, 1e-9))
            bp.append(float(db[band].max()))
            lobe = abs(field.far_field(layout.positions, layout.normals, gain,
                                       lobe_dirs, phases=phases))
            lb.append(float(20 * np.log10(max(lobe.max() / p_axis, 1e-9))))
        band_med.append(np.median(bp))
        lobe_med.append(np.median(lb))

    x = np.array(sigmas, dtype=float)
    ax1.plot(x, np.clip(band_med, -80, 0), marker="o", color=BLUE, lw=2,
             label="50–60° band peak")
    ax1.plot(x, np.clip(lobe_med, -80, 0), marker="s", color=ORANGE, lw=2,
             label="exact 54.75° lobe")
    ax1.set_xlabel("random phase error, RMS (deg); gain error 0.5 dB RMS")
    ax1.set_ylabel("level (dB re main peak)")
    ax1.set_ylim(-80, -8)
    ax1.set_title("Random errors: the null barely fills", fontsize=10,
                  loc="left", color=INK_2)
    ax1.grid(color=GRID, lw=0.7)
    ax1.legend(frameon=False, fontsize=8.5, loc="center right")

    deltas = np.array([0.0, 0.1, 0.2, 0.35, 0.5, 1.0])
    lobe_shift = []
    for delta in deltas:
        k = C.WAVE_NUMBER * (1.0 + delta / 100.0)
        p_axis = abs(field.far_field(
            layout.positions, layout.normals, amps,
            np.array([[0.0, 0.0, 1.0]]), wavenumber=k)[0])
        lobe = abs(field.far_field(layout.positions, layout.normals, amps,
                                   lobe_dirs, wavenumber=k))
        lobe_shift.append(float(20 * np.log10(max(lobe.max() / p_axis, 1e-9))))

    ax2.plot(deltas, np.clip(lobe_shift, -80, 0), marker="o", color=ORANGE,
             lw=2, label="exact 54.75° lobe")
    ax2.axvspan(0.0, 0.35, color=RED, alpha=0.06, linewidth=0)
    ax2.text(0.17, -76, "±2 °C in air", color=RED, fontsize=7.5, ha="center")
    ax2.set_xlabel("carrier / sound-speed offset (%)")
    ax2.set_ylabel("level at the nominal 54.75° direction (dB)")
    ax2.set_ylim(-80, -8)
    ax2.set_title("Systematic shift: the null moves away",
                  fontsize=10, loc="left", color=INK_2)
    ax2.grid(color=GRID, lw=0.7)

    for ax in (ax1, ax2):
        ax.tick_params(labelsize=8, length=2)
        for s_ in ("top", "right"):
            ax.spines[s_].set_visible(False)

    fig.suptitle("Tolerance of the current pair", fontsize=13,
                 fontweight="bold", x=0.012, ha="left", color=INK, y=0.98)
    fig.text(0.012, 0.905,
             "Left: 24 Monte Carlo trials per point. Right: uniform +1 % "
             "change in k, as a temperature or sound-speed drift.",
             fontsize=8.5, color=INK_2, ha="left", va="top")
    fig.subplots_adjust(left=0.06, right=0.98, top=0.80, bottom=0.15,
                        wspace=0.22)
    fig.savefig(path, dpi=300)
    plt.close(fig)
'''
s = s[:start] + new
r.write_text(s, encoding="utf-8")
print("render ok")
