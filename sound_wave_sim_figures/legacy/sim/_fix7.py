import pathlib

p = pathlib.Path("sim/export_web.py")
s = p.read_text(encoding="utf-8")


def rep(old, new):
    global s
    if old not in s:
        raise SystemExit("NOT FOUND: " + old[:140])
    s = s.replace(old, new)


# ---------------- template: comparison table placeholder + styles
rep('''    <div class="metrics">$metrics</div>
    $inset''',
'''    <div class="metrics">$metrics</div>
    $compare
    $inset''')

rep('''  .inset{margin:0}''',
'''  table.cmp{width:100%;border-collapse:collapse;font-family:"IBM Plex Mono",monospace;
    font-size:11px;color:var(--muted)}
  table.cmp th{font-weight:500;color:var(--muted);text-align:right;padding:2px 0}
  table.cmp th:first-child{text-align:left}
  table.cmp td{text-align:right;padding:2px 0;color:var(--ink)}
  table.cmp td:first-child{text-align:left;color:var(--muted)}
  .inset{margin:0}''')

# ---------------- reference metrics + compare table + three-curve inset
addition = '''

_REF = None


def _reference():
    """Current-pair metrics, computed once per process on a coarse grid."""
    global _REF
    if _REF is None:
        import geometry
        lay = geometry.coplanar_gap()
        _REF = field.analyse(lay.positions, lay.normals, lay.amplitudes(),
                             du=0.02)
    return _REF


def _delta(value, ref, good="up"):
    if value is None or ref is None:
        return "—"
    d = value - ref
    if abs(d) < 0.05:
        return "±0.0"
    sign = "+" if d > 0 else "−"
    return f"{sign}{abs(d):.1f}"


def _compare_html(m) -> str:
    if m is None:
        return ('<p class="fine">No far-field numbers: the boards are '
                'opposed, so this pair radiates into two half-spaces.</p>')
    ref = _reference()

    def cell(val, refv, fmt="{:.1f}", good="up"):
        d = _delta(val, refv)
        return f"<td>{fmt.format(val)}</td><td>{d}</td>"

    rows = [
        ("DI (dB)", cell(m["di_db"], ref["di_db"]),
         "up"),
        ("band peak (dB)", cell(m["band_max_db"], ref["band_max_db"]),
         "down"),
        ("band energy (%)", cell(m["band_energy_pct"],
                                 ref["band_energy_pct"]), "down"),
        ("leak >60° (%)", cell(m["leak_60_pct"], ref["leak_60_pct"],
                               "{:.2f}"), "down"),
    ]
    body = "".join(f"<tr><td>{name}</td>{cells}</tr>"
                   for name, cells, _ in rows)
    return (
        '<table class="cmp"><thead><tr><th>measure</th><th>this</th>'
        '<th>vs current</th></tr></thead><tbody>' + body + '</tbody></table>'
        '<p class="fine">Green direction: DI up, the rest down. '
        'Delta is this layout minus the current 15.75 / 5.25 pair.</p>'
    )


def _cut_inset(layout) -> str:
    """Elevation cut through the 54.75 deg lobe, this vs current vs butted."""
    import geometry

    curves = [(geometry.coplanar_butt(), "#8a8983", "butted")]
    current = geometry.coplanar_gap()
    if layout.key != current.key:
        curves.append((current, "#104281", "current"))
    curves.append((layout, "#2a78d6", "this layout"))

    el = np.arange(44.0, 66.0 + 0.02, 0.02)
    dirs = np.stack([field.dir_from_angles(e, 0.0) for e in el])
    fig, ax = plt.subplots(figsize=(6.2, 3.5))
    for lay, color, label in curves:
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
            '<p>The 3D radius and colour compress this: 2 dB is about 7 % of '
            'the radius and a small colour step, while the null is one point. '
            'This cut is the honest comparison.</p></div>')

'''
s = s.replace("def _plane_image(", addition + "\ndef _plane_image(")

# ---------------- data: lobe labels for the 3D scene
rep('''    data = {
        "u": u,''',
'''    lobes = []
    if m is not None:
        for az_key, db in m["lobe_by_az_db"].items():
            lobes.append({"az": float(az_key), "db": float(db)})
    data = {
        "u": u,''')

rep('''        "boards": [''',
'''        "lobes": lobes,
        "boards": [''')

# ---------------- substitute compare + inset on every page
rep('''    inset = _cut_inset(layout) if layout.key == "05_coplanar_gap" else ""
    html = TEMPLATE.substitute(
        title=layout.title,
        notes=layout.notes,
        metrics=_metrics_html(m),
        inset=inset,''',
'''    inset = _cut_inset(layout) if m is not None else ""
    compare = _compare_html(m)
    html = TEMPLATE.substitute(
        title=layout.title,
        notes=layout.notes,
        metrics=_metrics_html(m),
        compare=compare,
        inset=inset,''')

# ---------------- 3D: sprite labels for the main beam and grating lobes
rep('''scene.add(farGroup);''',
'''scene.add(farGroup);

// ---- data labels ------------------------------------------------------
function makeLabel(text){
  const c = document.createElement('canvas');
  c.width = 320; c.height = 72;
  const ctx = c.getContext('2d');
  ctx.fillStyle = 'rgba(8,10,10,0.72)';
  const r = 16;
  ctx.beginPath();
  ctx.moveTo(r,0); ctx.lineTo(c.width-r,0); ctx.quadraticCurveTo(c.width,0,c.width,r);
  ctx.lineTo(c.width,c.height-r); ctx.quadraticCurveTo(c.width,c.height,c.width-r,c.height);
  ctx.lineTo(r,c.height); ctx.quadraticCurveTo(0,c.height,0,c.height-r);
  ctx.lineTo(0,r); ctx.quadraticCurveTo(0,0,r,0); ctx.fill();
  ctx.fillStyle = '#ffffff';
  ctx.font = '500 26px "IBM Plex Mono", monospace';
  ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.fillText(text, c.width/2, c.height/2 + 1);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  const spr = new THREE.Sprite(new THREE.SpriteMaterial({
    map: tex, transparent: true, depthTest: false
  }));
  spr.scale.set(0.22, 0.0495, 1);
  spr.renderOrder = 20;
  return spr;
}
const beam = makeLabel('0 dB  main beam');
beam.position.set(0, 0, 0.62);
farGroup.add(beam);
for (const lobe of (DATA.lobes || [])){
  const e = lobe.az * Math.PI / 180, t = 54.7525 * Math.PI / 180;
  const r = 0.02 + 0.58 * Math.max(0, (lobe.db + 40) / 40);
  const l = makeLabel(lobe.db.toFixed(1) + ' dB  ' + (lobe.az === 0 || Math.abs(lobe.az) === 180 ? 'x-lobe' : 'y-lobe'));
  l.position.set(1.25*r*Math.sin(t)*Math.cos(e), 1.25*r*Math.sin(t)*Math.sin(e), 1.25*r*Math.cos(t));
  farGroup.add(l);
}''')

p.write_text(s, encoding="utf-8")
print("export_web updated")
