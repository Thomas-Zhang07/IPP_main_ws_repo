import pathlib

p = pathlib.Path("sim/render_png.py")
s = p.read_text(encoding="utf-8")

addition = '''

def decomposition_png(layout, path: Path) -> None:
    """Board A, board B and the coherent sum, on the same grid and scale."""
    assert len(layout.boards) == 2, "decomposition needs a two-board layout"
    U, V, mask, dirs, el, az, _ = field.uv_grid(0.006)
    a, b = layout.boards
    pa = field.far_field(a.positions, a.normals, a.amplitudes(), dirs)
    pb = field.far_field(b.positions, b.normals, b.amplitudes(), dirs)
    ps = pa + pb
    peak = float(abs(ps).max())
    ring = math.sin(math.radians(C.GRATING_ANGLE_DEG))
    circle = np.linspace(0, 2 * math.pi, 300)

    fig, axes = plt.subplots(2, 2, figsize=(11.4, 9.6))
    ax_a, ax_b, ax_s, ax_c = axes.ravel()
    for ax, data, title in (
        (ax_a, pa, "Board A alone"),
        (ax_b, pb, "Board B alone"),
        (ax_s, ps, "A + B, coherent sum"),
    ):
        db = 20 * np.log10(np.maximum(abs(data) / peak, 10 ** (FLOOR / 20)))
        Z = np.full(U.shape, np.nan)
        Z[mask] = np.clip(db, FLOOR, 0)
        mesh = ax.pcolormesh(U, V, Z, cmap=RAMP, vmin=FLOOR, vmax=0,
                             shading="auto", rasterized=True)
        ax.plot(ring * np.cos(circle), ring * np.sin(circle), color=CYAN,
                lw=1.1, ls=(0, (4, 3)))
        for ux, uy in ((ring, 0), (-ring, 0), (0, ring), (0, -ring)):
            ax.plot([ux], [uy], marker="+", ms=8, color=CYAN, mew=1.3)
        ax.set_xlim(-1.02, 1.02)
        ax.set_ylim(-1.02, 1.02)
        ax.set_aspect("equal")
        ax.set_xlabel("u$_x$")
        ax.set_ylabel("u$_y$")
        ax.set_title(title, fontsize=10, loc="left", color=INK_2)
        for s_ in ("top", "right"):
            ax.spines[s_].set_visible(False)
    cb = fig.colorbar(mesh, ax=[ax_a, ax_b, ax_s], pad=0.015, fraction=0.03)
    cb.set_label("dB re the sum's main peak", fontsize=8)
    cb.ax.tick_params(labelsize=7, length=2)
    cb.outline.set_edgecolor(GRID)

    elc = np.arange(44.0, 66.0 + 0.02, 0.02)
    dirc = np.stack([field.dir_from_angles(e, 0.0) for e in elc])
    fa = field.far_field(a.positions, a.normals, a.amplitudes(), dirc)
    fb = field.far_field(b.positions, b.normals, b.amplitudes(), dirc)
    fs = field.far_field(layout.positions, layout.normals,
                         layout.amplitudes(), dirc)
    for data, color, label in ((fa, GRAY, "A alone"), (fb, ORANGE, "B alone"),
                               (fs, BLUE, "A + B")):
        lev = 20 * np.log10(np.maximum(abs(data) / peak, 1e-6))
        ax_c.plot(elc, np.clip(lev, -50, 0), color=color, lw=1.7, label=label)
    ax_c.axvline(C.GRATING_ANGLE_DEG, color=CYAN, lw=1.1, ls=(0, (4, 3)))
    ax_c.set_xlim(44, 66)
    ax_c.set_ylim(-50, 0)
    ax_c.set_xlabel("elevation through the φ = 0 lobe (deg)")
    ax_c.set_ylabel("dB re the sum's main peak")
    ax_c.set_title("Cut through the lobe", fontsize=10, loc="left", color=INK_2)
    ax_c.grid(color=GRID, lw=0.7)
    ax_c.legend(frameon=False, fontsize=8.5, loc="lower left")
    for s_ in ("top", "right"):
        ax_c.spines[s_].set_visible(False)

    fig.suptitle(f"Far-field decomposition — {layout.title}", fontsize=13,
                 fontweight="bold", x=0.012, ha="left", color=INK, y=0.98)
    fig.text(0.012, 0.935,
             "Both boards are identical 16 x 16 arrays, so their individual "
             "patterns are the same; the null exists only in the coherent "
             "sum. Cyan = 54.75° grating ring.",
             fontsize=8.5, color=INK_2, ha="left", va="top")
    fig.subplots_adjust(left=0.07, right=0.92, top=0.90, bottom=0.07,
                        wspace=0.25, hspace=0.28)
    fig.savefig(path, dpi=300)
    plt.close(fig)
'''

s = s + addition
p.write_text(s, encoding="utf-8")

q = pathlib.Path("sim/run_all.py")
t = q.read_text(encoding="utf-8")
t = t.replace('''    render_png.comparison_png(rows, FIG / "comparison.png")''',
'''    if not args.baselines_only:
        render_png.decomposition_png(geometry.coplanar_gap(),
                                     FIG / "decomposition.png")
    render_png.comparison_png(rows, FIG / "comparison.png")''')
q.write_text(t, encoding="utf-8")
print("added")
