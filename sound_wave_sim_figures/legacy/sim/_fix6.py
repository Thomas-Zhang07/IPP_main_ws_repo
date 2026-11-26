import pathlib

p = pathlib.Path("sim/export_web.py")
s = p.read_text(encoding="utf-8")


def rep(old, new):
    global s
    if old not in s:
        raise SystemExit("NOT FOUND: " + old[:140])
    s = s.replace(old, new)


# template: inset slot + style
rep('''    <div class="metrics">$metrics</div>''',
'''    <div class="metrics">$metrics</div>
    $inset''')

rep('''  .fine{font-size:11px;color:var(--muted);line-height:1.5}''',
'''  .fine{font-size:11px;color:var(--muted);line-height:1.5}
  .inset{margin:0}
  .inset img{width:100%;border:1px solid var(--line);border-radius:6px;display:block}
  .inset p{font-size:10.5px;color:var(--muted);line-height:1.45;margin:6px 0 0}''')

# inset builder
addition = '''

def _cut_inset(layout) -> str:
    """Elevation cut through the 54.75 deg lobe, current vs butted."""
    import geometry

    butt = geometry.coplanar_butt()
    el = np.arange(44.0, 66.0 + 0.02, 0.02)
    dirs = np.stack([field.dir_from_angles(e, 0.0) for e in el])
    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    for lay, color, label in ((butt, "#8a8983", "butted pair"),
                              (layout, "#2a78d6", "this pair")):
        amps = lay.amplitudes()
        p_axis = abs(field.far_field(lay.positions, lay.normals, amps,
                                     np.array([[0.0, 0.0, 1.0]]))[0])
        level = 20 * np.log10(np.maximum(abs(field.far_field(
            lay.positions, lay.normals, amps, dirs)) / p_axis, 1e-6))
        ax.plot(el, np.clip(level, -50, 0), color=color, lw=1.7, label=label)
    ax.axvline(C.GRATING_ANGLE_DEG, color="#38bdf8", lw=1.0, ls=(0, (4, 3)))
    ax.set_xlim(44, 66)
    ax.set_ylim(-50, 0)
    ax.set_xlabel("elevation through the lobe (deg)", fontsize=8)
    ax.set_ylabel("dB re main peak", fontsize=8)
    ax.tick_params(labelsize=7, length=2)
    ax.grid(color="#e6e5e0", lw=0.6)
    for s_ in ("top", "right"):
        ax.spines[s_].set_visible(False)
    ax.legend(frameon=False, fontsize=7.5, loc="lower left")
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=180, facecolor="#fcfcfb")
    plt.close(fig)
    uri = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    return ('<div class="inset"><img src="' + uri + '" alt="cut through lobe">'
            '<p>The 3D radius and colour compress this: a 2 dB difference is '
            'about 7 % of the radius and a small colour step, while the null '
            'is one point. This cut is the honest view.</p></div>')

'''
s = s.replace("def _plane_image(", addition + "\ndef _plane_image(")

# write the inset only on the current-pair page
rep('''    html = TEMPLATE.substitute(
        title=layout.title,
        notes=layout.notes,
        metrics=_metrics_html(m),
        data=json.dumps(data),
        surface=SURFACE,
    )''',
'''    inset = _cut_inset(layout) if layout.key == "05_coplanar_gap" else ""
    html = TEMPLATE.substitute(
        title=layout.title,
        notes=layout.notes,
        metrics=_metrics_html(m),
        inset=inset,
        data=json.dumps(data),
        surface=SURFACE,
    )''')

p.write_text(s, encoding="utf-8")
print("ok")
