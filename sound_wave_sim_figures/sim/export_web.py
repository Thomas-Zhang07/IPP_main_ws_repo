"""Interactive 3D pages: far-field surface + near-field slice planes.

One self-contained page per configuration (Three.js from a pinned CDN), plus
an index.  Field data is precomputed by numpy; the page only renders.
"""

from __future__ import annotations

import base64
import io
import json
from pathlib import Path
from string import Template

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import constants as C
import field
import geometry
import render_png

SURFACE = "#fcfcfb"

TEMPLATE = Template("""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>$title</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>
  :root{
    --bg:#ece9e1; --surface:#fcfcfb; --ink:#17201d; --muted:#5f6964;
    --line:#cfccc2; --accent:#c2410c; --board:#2f6b4f; --panel:rgba(252,252,251,.92);
  }
  *{box-sizing:border-box}
  html,body{margin:0;height:100%;background:var(--bg);color:var(--ink);
    font-family:"IBM Plex Sans","Noto Sans SC",system-ui,sans-serif}
  #app{display:grid;grid-template-columns:1fr 330px;height:100vh}
  #stage{position:relative;min-width:0}
  #stage canvas{display:block;width:100%;height:100%}
  h1{font-size:17px;margin:0 0 4px;font-weight:600;letter-spacing:-.01em}
  .notes{font-size:12px;color:var(--muted);line-height:1.45;margin:0}
  aside{background:var(--panel);border-left:1px solid var(--line);padding:18px;
    overflow:auto;display:flex;flex-direction:column;gap:16px}
  .metrics{font-family:"IBM Plex Mono",monospace;font-size:11.5px;line-height:1.75;
    color:var(--muted)}
  .metrics b{color:var(--ink);font-weight:500}
  .hud{position:absolute;top:12px;left:14px;display:flex;gap:6px;z-index:5}
  .hud button{box-shadow:0 1px 4px rgba(0,0,0,.12);background:var(--panel)}
  .modes{display:flex;gap:6px}
  button{font:inherit;font-size:12px;padding:7px 10px;border:1px solid var(--line);
    background:var(--surface);color:var(--ink);border-radius:6px;cursor:pointer}
  button[aria-pressed="true"]{border-color:var(--accent);color:var(--accent);
    background:#fdf1e9}
  .legend{height:10px;border-radius:5px;margin:6px 0 2px;
    background:linear-gradient(90deg,#fcffa4,#f7d13d,#fb9b06,#ed6925,#cf4446,#a52c60,#781c6d,#4a0c6b,#1b0c41,#000004)}
  .legend-labels{display:flex;justify-content:space-between;font-size:10.5px;
    color:var(--muted);font-family:"IBM Plex Mono",monospace}
  .fine{font-size:11px;color:var(--muted);line-height:1.5}
  table.cmp{width:100%;border-collapse:collapse;font-family:"IBM Plex Mono",monospace;
    font-size:11px;color:var(--muted)}
  table.cmp th{font-weight:500;color:var(--muted);text-align:right;padding:2px 0}
  table.cmp th:first-child{text-align:left}
  table.cmp td{text-align:right;padding:2px 0;color:var(--ink)}
  table.cmp td:first-child{text-align:left;color:var(--muted)}
  .inset{margin:0}
  .inset img{width:100%;border:1px solid var(--line);border-radius:6px;display:block}
  .inset p{font-size:10.5px;color:var(--muted);line-height:1.45;margin:6px 0 0}
  .hint{position:absolute;left:14px;bottom:12px;font-size:11px;color:var(--muted);
    background:var(--panel);border:1px solid var(--line);border-radius:6px;
    padding:5px 9px}
  @media (max-width:820px){
    #app{grid-template-columns:1fr;grid-template-rows:62vh auto;height:auto}
    aside{border-left:0;border-top:1px solid var(--line)}
  }
</style>
<script type="importmap">
{"imports":{
  "three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
  "three/addons/":"https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"
}}
</script>
</head>
<body>
<div id="app">
  <div id="stage">
    <div class="hud">
      <button class="mbtn" data-mode="far" aria-pressed="true">Far field 3D</button>
      <button class="mbtn" data-mode="near" aria-pressed="false">Near-field slices</button>
    </div>
    <div class="hint">drag to rotate · scroll to zoom · right-drag to pan</div>
  </div>
  <aside>
    <div>
      <h1>$title</h1>
      <p class="notes">$notes</p>
    </div>
    <div>
      <div class="legend"></div>
      <div class="legend-labels"><span>0 dB</span><span>−40 dB</span></div>
    </div>
    <div class="metrics">$metrics</div>
    $compare
    $inset
    <p class="fine">Ideal model: uniform phase, 10 mm piston elements, no phase
      errors, no amplitude quantization. Levels relative to the pattern peak.
      The surface radius is linear in dB above the −40 dB floor.</p>
  </aside>
</div>
<script type="module">
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const DATA = $data;

const stage = document.getElementById('stage');
const scene = new THREE.Scene();
scene.background = new THREE.Color('$surface');

const camera = new THREE.PerspectiveCamera(40, stage.clientWidth/stage.clientHeight, 0.01, 50);
camera.position.set(0.75, 0.62, 1.35);

const renderer = new THREE.WebGLRenderer({antialias:true});
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(stage.clientWidth, stage.clientHeight);
stage.appendChild(renderer.domElement);

const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, 0, 0.22);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.maxPolarAngle = Math.PI * 0.92;

const floor = new THREE.GridHelper(2.6, 26, 0xd6d3c9, 0xe7e4dc);
floor.position.y = -0.45;
scene.add(floor);
scene.add(new THREE.HemisphereLight(0xffffff, 0xdfe3e0, 1.5));
const key = new THREE.DirectionalLight(0xffffff, 1.4);
key.position.set(0.8, 1.2, 1.0);
scene.add(key);
const fill = new THREE.DirectionalLight(0xffffff, 0.6);
fill.position.set(-1.0, 0.4, 0.4);
scene.add(fill);

const STOPS = ['#000004','#1b0c41','#4a0c6b','#781c6d','#a52c60',
  '#cf4446','#ed6925','#fb9b06','#f7d13d','#fcffa4'].map(h => new THREE.Color(h));
function ramp(t){
  t = Math.min(1, Math.max(0, t));
  const x = t * (STOPS.length - 1);
  const i = Math.min(STOPS.length - 2, Math.floor(x));
  const f = x - i;
  return STOPS[i].clone().lerp(STOPS[i+1], f);
}
function colorForDb(db){ return ramp((db + 40) / 40); }

// ---- boards -------------------------------------------------------------
const boards = new THREE.Group();
const boardMat = new THREE.MeshStandardMaterial({color:0x2f6b4f, side:THREE.DoubleSide,
  roughness:0.72, metalness:0.05});
const edgeMat = new THREE.LineBasicMaterial({color:0x1d4a35});
const dotGeo = new THREE.SphereGeometry(0.0055, 10, 8);
const dotMat = new THREE.MeshStandardMaterial({color:0xd8c08a, roughness:0.4});
for (const b of DATA.boards){
  const pts = b.outline;
  const w = Math.hypot(pts[1][0]-pts[0][0], pts[1][1]-pts[0][1], pts[1][2]-pts[0][2]);
  const h = Math.hypot(pts[3][0]-pts[0][0], pts[3][1]-pts[0][1], pts[3][2]-pts[0][2]);
  const geo = new THREE.PlaneGeometry(w, h);
  const mesh = new THREE.Mesh(geo, boardMat);
  const cx = (pts[0][0]+pts[2][0])/2, cy = (pts[0][1]+pts[2][1])/2, cz = (pts[0][2]+pts[2][2])/2;
  mesh.position.set(cx, cy, cz);
  // plane normal is +z; rotate about y until it matches the board normal
  const n = b.normal;
  mesh.rotation.y = Math.atan2(n[0], n[2]);
  boards.add(mesh);
  const edges = new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(
    pts.map(p => new THREE.Vector3(...p))), edgeMat);
  edges.material.depthTest = false;
  edges.renderOrder = 12;
  boards.add(edges);
  const dots = new THREE.InstancedMesh(dotGeo, dotMat, b.emitters.length);
  const m = new THREE.Matrix4();
  b.emitters.forEach((p, i) => { m.makeTranslation(p[0], p[1], p[2]); dots.setMatrixAt(i, m); });
  dots.instanceMatrix.needsUpdate = true;
  boards.add(dots);
}
scene.add(boards);

// ---- far-field surface --------------------------------------------------
const farGroup = new THREE.Group();
const u = DATA.u, v = DATA.v, Q = DATA.db, nx = DATA.nu, ny = DATA.nv;
const bytes = (() => { const b = atob(Q); const out = new Uint8Array(b.length);
  for (let i = 0; i < b.length; i++) out[i] = b.charCodeAt(i); return out; })();
const levelAt = (i, j) => { const q = bytes[i * nx + j];
  return q === 255 ? null : q / 250 * 40 - 40; };
const pos = [], col = [], idx = [];
const index = new Map();
function vid(i, j){
  const key = i + ',' + j;
  if (index.has(key)) return index.get(key);
  const uu = u[j], vv = v[i];
  const ww = Math.sqrt(Math.max(0, 1 - uu*uu - vv*vv));
  const level = levelAt(i, j);
  const r = 0.02 + 0.58 * Math.max(0, (level + 40) / 40);
  pos.push(r*uu, r*vv, r*ww);
  const c = colorForDb(level);
  col.push(c.r, c.g, c.b);
  const id = pos.length/3 - 1;
  index.set(key, id);
  return id;
}
for (let i = 0; i < ny-1; i++){
  for (let j = 0; j < nx-1; j++){
    if (levelAt(i,j) === null || levelAt(i+1,j) === null || levelAt(i,j+1) === null || levelAt(i+1,j+1) === null) continue;
    const a = vid(i,j), b = vid(i,j+1), c = vid(i+1,j), d = vid(i+1,j+1);
    idx.push(a, b, d, a, d, c);
  }
}
const geo = new THREE.BufferGeometry();
geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
geo.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
geo.setIndex(idx);
geo.computeVertexNormals();
const surface = new THREE.Mesh(geo, new THREE.MeshLambertMaterial({
  vertexColors:true, side:THREE.DoubleSide
}));
surface.renderOrder = 1;
farGroup.add(surface);

// 54.75 deg grating ring at the array scale
const ug = Math.sin(54.7525 * Math.PI / 180);
const uz = Math.cos(54.7525 * Math.PI / 180);
const ringPts = [];
for (let k = 0; k <= 240; k++){
  const a = k / 240 * Math.PI * 2;
  ringPts.push(new THREE.Vector3(0.42 * ug * Math.cos(a),
                                 0.42 * ug * Math.sin(a), 0.42 * uz));
}
farGroup.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(ringPts),
  new THREE.LineBasicMaterial({color:0x38bdf8, transparent:true, opacity:0.45})));
scene.add(farGroup);

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
  if (lobe.db < -60) continue;
  const e = lobe.az * Math.PI / 180, t = 54.7525 * Math.PI / 180;
  const axis = (lobe.az === 0 || Math.abs(lobe.az) === 180) ? 'x-lobe' : 'y-lobe';
  const text = lobe.db.toFixed(1) + ' dB  ' + axis;
  const r = isNull ? 0.42 : 0.02 + 0.58 * Math.max(0, (lobe.db + 40) / 40);
  const l = makeLabel(text);
  l.position.set(1.18*r*Math.sin(t)*Math.cos(e), 1.18*r*Math.sin(t)*Math.sin(e), 1.18*r*Math.cos(t));
  farGroup.add(l);
}

// ---- near-field planes --------------------------------------------------
const nearGroup = new THREE.Group();
nearGroup.visible = false;
const loader = new THREE.TextureLoader();
for (const p of DATA.planes){
  loader.load(p.img, tex => {
    tex.colorSpace = THREE.SRGBColorSpace;
    tex.anisotropy = 4;
    let w, h;
    if (p.kind === 'xz'){ w = p.x[1]-p.x[0]; h = p.z[1]-p.z[0]; }
    else if (p.kind === 'xy'){ w = p.x[1]-p.x[0]; h = p.y[1]-p.y[0]; }
    else { w = p.y[1]-p.y[0]; h = p.z[1]-p.z[0]; }
    const mat = new THREE.MeshBasicMaterial({map:tex, side:THREE.DoubleSide,
      transparent:true, opacity:0.94, depthWrite:false});
    const plane = new THREE.Mesh(new THREE.PlaneGeometry(w, h), mat);
    if (p.kind === 'xz'){
      plane.rotation.x = -Math.PI/2;
      plane.position.set((p.x[0]+p.x[1])/2, p.y, (p.z[0]+p.z[1])/2);
    } else if (p.kind === 'xy'){
      plane.position.set((p.x[0]+p.x[1])/2, (p.y[0]+p.y[1])/2, p.z[0]);
    } else {
      plane.rotation.y = -Math.PI/2;
      plane.position.set(p.x[0], (p.y[0]+p.y[1])/2, (p.z[0]+p.z[1])/2);
    }
    nearGroup.add(plane);
  });
}
scene.add(nearGroup);

// ---- mode switch --------------------------------------------------------
const modeButtons = [...document.querySelectorAll('.mbtn')];
function setMode(far){
  farGroup.visible = far;
  nearGroup.visible = !far;
  modeButtons.forEach(b => b.setAttribute('aria-pressed',
    b.dataset.mode === (far ? 'far' : 'near') ? 'true' : 'false'));
  if (far){ camera.position.set(0.75, 0.62, 1.35); controls.target.set(0, 0, 0.16); }
  else { camera.position.set(1.8, 1.5, 2.9); controls.target.set(0, 0, 0.6); }
  controls.update();
}
modeButtons.forEach(b => b.onclick = () => setMode(b.dataset.mode === 'far'));
const params = new URLSearchParams(location.search);
if (!DATA.has_far){ setMode(false); modeButtons[0].disabled = true; }
else { setMode(params.get('mode') !== 'near'); }

// ---- render loop --------------------------------------------------------
function resize(){
  const w = stage.clientWidth, h = stage.clientHeight;
  camera.aspect = w/h; camera.updateProjectionMatrix();
  renderer.setSize(w, h);
}
addEventListener('resize', resize);
renderer.render(scene, camera);
renderer.setAnimationLoop(() => { controls.update(); renderer.render(scene, camera); });
</script>

<script>
setTimeout(function(){
  if (document.querySelector('#stage canvas')) return;
  var d = document.createElement('div');
  d.style.cssText = 'position:absolute;inset:0;display:flex;align-items:center;justify-content:center;text-align:center;padding:40px;font:13px/1.5 sans-serif;color:#5f6964;background:#fcfcfb';
  d.textContent = 'The 3D view needs WebGL; the tables and the cut inset on the right work regardless.';
  document.getElementById('stage').appendChild(d);
}, 4000);
</script>
</body>
</html>
""")




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




_REF = None


def _reference():
    """Current-pair metrics, computed once per process on a coarse grid."""
    global _REF
    if _REF is None:
        import geometry
        import cache
        lay = geometry.coplanar_gap()
        _REF = cache.analysis(lay, du=0.004)
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


def _plane_image(values: np.ndarray, peak: float) -> str:
    """Coloured plane as a PNG data URI (file:// pages may not load images)."""
    level = 20.0 * np.log10(
        np.maximum(np.abs(values) / peak, 10 ** (C.DB_FLOOR / 20.0))
    )
    level = np.clip(level, C.DB_FLOOR, 0.0)
    rgb = render_png.RAMP((level - C.DB_FLOOR) / (0.0 - C.DB_FLOOR))[..., :3]
    buf = io.BytesIO()
    plt.imsave(buf, rgb, format="png")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def build_planes(layout, near, img_dir: Path) -> list[dict]:
    img_dir.mkdir(parents=True, exist_ok=True)
    planes = []
    peak = near["peak"]
    X, Z, p_xz = near["X"], near["Z"], near["p_xz"]
    planes.append({
        "kind": "xz", "img": _plane_image(p_xz, peak),
        "x": [float(X.min()), float(X.max())],
        "z": [float(Z.min()), float(Z.max())],
        "y": near["ymid"],
    })
    XY, YY, p_xy = near["XY"], near["YY"], near["p_xy"]
    planes.append({
        "kind": "xy", "img": _plane_image(np.flipud(p_xy), peak),
        "x": [float(XY.min()), float(XY.max())],
        "y": [float(YY.min()), float(YY.max())],
        "z": [float(near["z_plane"]), float(near["z_plane"])],
    })
    # y-z plane at x = 0; rows are y (top = y max after the flip), cols z
    pos = layout.positions
    ys = np.arange(float(pos[:, 1].min()) - 0.25,
                   float(pos[:, 1].max()) + 0.25, 0.006)
    zmax = float(Z.max())
    zs = np.arange(0.02, zmax + 0.006, 0.006)
    Zg, Yg = np.meshgrid(zs, ys, indexing="xy")
    pts = np.column_stack([np.zeros(Yg.size), Yg.ravel(), Zg.ravel()])
    p_yz = field.near_field_points(
        layout.positions, layout.normals, layout.amplitudes(), pts
    ).reshape(Yg.shape)
    planes.append({
        "kind": "yz", "img": _plane_image(np.flipud(p_yz), peak),
        "x": [0.0, 0.0],
        "y": [float(ys.min()), float(ys.max())],
        "z": [float(zs.min()), float(zs.max())],
    })
    return planes


def _metrics_html(m: dict) -> str:
    if m is None:
        return ("Far field: <b>n/a</b> — the boards are opposed, so the pair "
                "radiates into two half-spaces.<br>See the near-field slices.")
    lobe = m["lobe_54_75_db"]
    lobe_txt = f"{lobe:.1f} dB" if lobe > -60 else "&lt; −60 dB (null)"
    rows = [
        ("DI (forward)", f"{m['di_db']:.1f} dB"),
        ("54.75° lobe", lobe_txt),
        ("50–60° band peak", f"{m['band_max_db']:.1f} dB"),
        ("band energy", f"{m['band_energy_pct']:.1f} %"),
        ("leak above 60°", f"{m['leak_60_pct']:.2f} %"),
        ("−6 dB beam x–z", render_png._fmt_deg(m["bw6_xz_deg"])),
        ("−6 dB beam y–z", render_png._fmt_deg(m["bw6_yz_deg"])),
    ]
    return "<br>".join(f"{k}: <b>{v}</b>" for k, v in rows)


def _far_grid(m, du: float = 0.004):
    """Quantise the u-v dB grid to 8 bits and base64-encode it.

    255 marks directions outside the unit disk.  250 steps over -40..0 dB
    (0.16 dB) is finer than the eye can separate on the surface.
    """
    if m is None:
        n = 101
        u = [round(-1.0 + i * 2.0 / (n - 1), 4) for i in range(n)]
        q = bytes([255]) * (n * n)
        return u, list(u), base64.b64encode(q).decode(), n, n
    U2, V2 = m["U"], m["V"]
    db = m["db"]
    step = max(1, int(round(du / m["du"])))
    u = [round(float(x), 4) for x in U2[0, ::step]]
    v = [round(float(x), 4) for x in V2[::step, 0]]
    sub = db[::step, ::step]
    quant = np.full(sub.shape, 255, dtype=np.uint8)
    valid = np.isfinite(sub)
    quant[valid] = np.clip(
        np.round((np.clip(sub[valid], -40.0, 0.0) + 40.0) / 40.0 * 250.0),
        0, 250,
    ).astype(np.uint8)
    return u, v, base64.b64encode(quant.tobytes()).decode(), len(u), len(v)


def write_page(layout, m, near, web_dir: Path, landing: str = "index.html") -> Path:
    page_dir = web_dir / layout.key
    page_dir.mkdir(parents=True, exist_ok=True)
    planes = build_planes(layout, near, page_dir / "img")
    u, v, db, nu, nv = _far_grid(m)
    lobes = []
    if m is not None:
        for az_key, lvl in m["lobe_by_az_db"].items():
            lobes.append({"az": float(az_key), "db": float(lvl)})
    data = {
        "u": u,
        "v": v,
        "nu": nu,
        "nv": nv,
        "db": db,
        "has_far": m is not None,
        "planes": planes,
        "lobes": lobes,
        "boards": [
            {
                "outline": [[round(float(x), 4) for x in p]
                            for p in board.outline],
                "normal": [round(float(x), 4) for x in board.normals[0]],
                "emitters": [[round(float(x), 4) for x in p]
                             for p in board.positions],
            }
            for board in layout.boards
        ],
    }
    inset = _cut_inset(layout) if m is not None else ""
    compare = _compare_html(m)
    html = TEMPLATE.substitute(
        title=layout.title,
        notes=layout.notes,
        metrics=_metrics_html(m),
        compare=compare,
        inset=inset,
        data=json.dumps(data),
        surface=SURFACE,
    )
    path = page_dir / "index.html"
    path.write_text(html, encoding="utf-8")
    return path


INDEX = Template("""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sound-wave simulations — layouts</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>
  body{margin:0;background:#ece9e1;color:#17201d;font-family:"IBM Plex Sans",system-ui,sans-serif}
  header{padding:34px 34px 10px}
  h1{margin:0 0 6px;font-size:24px;letter-spacing:-.02em}
  p{margin:0;color:#5f6964;font-size:13px;max-width:70ch;line-height:1.5}
  main{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:14px;padding:22px 34px 44px}
  a.card{display:block;background:#fcfcfb;border:1px solid #cfccc2;border-radius:10px;
    padding:16px 16px 14px;text-decoration:none;color:inherit;transition:border-color .15s,transform .15s}
  a.card:hover{border-color:#c2410c;transform:translateY(-2px)}
  .tag{font-size:11px;color:#5f6964;font-family:"IBM Plex Mono",monospace;text-transform:uppercase;letter-spacing:.06em}
  .name{font-size:15px;font-weight:600;margin:5px 0 6px;line-height:1.3}
  .stat{font-family:"IBM Plex Mono",monospace;font-size:11.5px;color:#5f6964;line-height:1.6}
</style></head><body>
<header>
  <h1>Sound-wave simulations — board layouts</h1>
  <p>Rotatable far-field patterns and near-field slices for every arrangement.
     Ideal model: uniform phase, 10 mm piston elements at 10.5 mm pitch, 40 kHz.
     Click a card to open the 3D page.</p>
</header>
<main>$cards</main>
</body></html>""")


def write_index(entries: list[dict], web_dir: Path) -> None:
    cards = []
    for e in entries:
        cards.append(
            f'<a class="card" href="{e["key"]}/index.html">'
            f'<div class="tag">{e["tag"]}</div>'
            f'<div class="name">{e["title"]}</div>'
            f'<div class="stat">{e["stat"]}</div></a>'
        )
    (web_dir / "index.html").write_text(
        INDEX.substitute(cards="\n".join(cards)), encoding="utf-8"
    )


OVERLAY_TEMPLATE = Template("""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Overlay two layouts</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>
  :root{--bg:#ece9e1;--surface:#fcfcfb;--ink:#17201d;--muted:#5f6964;
    --line:#cfccc2;--a:#2a78d6;--b:#eb6834}
  *{box-sizing:border-box}
  html,body{margin:0;height:100%;background:var(--bg);color:var(--ink);
    font-family:"IBM Plex Sans",system-ui,sans-serif}
  #app{display:grid;grid-template-columns:1fr 360px;height:100vh}
  #stage{position:relative;min-width:0}
  #stage canvas{display:block;width:100%;height:100%}
  aside{background:rgba(252,252,251,.94);border-left:1px solid var(--line);
    padding:16px;overflow:auto;display:flex;flex-direction:column;gap:14px}
  h1{font-size:16px;margin:0 0 4px}
  .note{font-size:11.5px;color:var(--muted);line-height:1.45;margin:0}
  label.row{display:block;font-size:12px;color:var(--muted)}
  select,input[type=range]{width:100%;margin-top:4px}
  .a{color:var(--a);font-weight:600}
  .b{color:var(--b);font-weight:600}
  table{width:100%;border-collapse:collapse;font-family:"IBM Plex Mono",monospace;font-size:11px}
  th,td{padding:3px 0;text-align:right;color:var(--muted)}
  th:first-child,td:first-child{text-align:left}
  td{color:var(--ink)}
  button{font:inherit;font-size:12px;padding:6px 10px;border:1px solid var(--line);
    background:var(--surface);border-radius:6px;cursor:pointer}
  .hint{position:absolute;left:14px;bottom:12px;font-size:11px;color:var(--muted);
    background:rgba(252,252,251,.92);border:1px solid var(--line);
    border-radius:6px;padding:5px 9px}
  @media (max-width:820px){#app{grid-template-columns:1fr;grid-template-rows:60vh auto;height:auto}}
</style>
<script type="importmap">
{"imports":{
  "three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
  "three/addons/":"https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"
}}
</script>
</head>
<body>
<div id="app">
  <div id="stage"><div class="hint">drag to rotate · scroll to zoom · right-drag to pan</div></div>
  <aside>
    <div>
      <h1>Overlay two layouts</h1>
      <p class="note">Both surfaces are normalised to their own peak, so compare
        shapes and lobe directions, not absolute level. Boards: <span class="a">A</span>
        solid, <span class="b">B</span> wireframe.</p>
    </div>
    <label class="row"><span class="a">A</span> layout
      <select id="selA"></select>
      <input id="opa" type="range" min="10" max="100" value="100">
    </label>
    <label class="row"><span class="b">B</span> layout
      <select id="selB"></select>
      <input id="opb" type="range" min="10" max="100" value="50">
    </label>
    <button id="swap">Swap A / B</button>
    <table id="cmp"><thead><tr><th>measure</th><th class="a">A</th><th class="b">B</th></tr></thead><tbody></tbody></table>
    <p class="note">A and B share the same grid and camera. Slider = surface opacity;
      at 50 % the rear pattern stays readable.</p>
  </aside>
</div>
<script type="module">
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const DATA = $data;
const stage = document.getElementById('stage');
const scene = new THREE.Scene();
scene.background = new THREE.Color('$surface');
const camera = new THREE.PerspectiveCamera(40, stage.clientWidth/stage.clientHeight, 0.01, 50);
camera.position.set(0.85, 0.75, 1.45);
const renderer = new THREE.WebGLRenderer({antialias:true, alpha:false});
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(stage.clientWidth, stage.clientHeight);
stage.appendChild(renderer.domElement);
const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, 0, 0.2);
controls.enableDamping = true;
scene.add(new THREE.HemisphereLight(0xffffff, 0xe4e2da, 1.6));
const floor = new THREE.GridHelper(2.4, 24, 0xd6d3c9, 0xe7e4dc);
floor.position.y = -0.42; scene.add(floor);

const BLUE = ['#eaf2fd','#cde2fb','#9ec5f4','#5598e7','#256abf','#104281']
  .map(h => new THREE.Color(h));
const ORANGE = ['#fff3ea','#fbd9c4','#f6b58c','#ef8a55','#d95926','#8f3410']
  .map(h => new THREE.Color(h));
function ramp(stops, t){
  t = Math.min(1, Math.max(0, t));
  const x = t * (stops.length - 1);
  const i = Math.min(stops.length - 2, Math.floor(x));
  return stops[i].clone().lerp(stops[i+1], x - i);
}
function decode(L){
  const b = atob(L.db), bytes = new Uint8Array(b.length);
  for (let i = 0; i < b.length; i++) bytes[i] = b.charCodeAt(i);
  return { bytes, nx: L.nu, ny: L.nv, u: L.u, v: L.v };
}

const boardsGroup = new THREE.Group(); scene.add(boardsGroup);
const meshA = new THREE.Group(); const meshB = new THREE.Group();
scene.add(meshA); scene.add(meshB);

function buildSurface(L, stops, opacity, target){
  target.clear();
  const { bytes, nx, ny, u, v } = decode(L);
  const pos = [], col = [], idx = [];
  const index = new Map();
  const levelAt = (i, j) => { const q = bytes[i * nx + j];
    return q === 255 ? null : q / 250 * 40 - 40; };
  function vid(i, j){
    const key = i + ',' + j;
    if (index.has(key)) return index.get(key);
    const uu = u[j], vv = v[i];
    const ww = Math.sqrt(Math.max(0, 1 - uu*uu - vv*vv));
    const level = levelAt(i, j);
    const r = 0.02 + 0.58 * Math.max(0, (level + 40) / 40);
    pos.push(r*uu, r*vv, r*ww);
    const c = ramp(stops, (level + 40) / 40);
    col.push(c.r, c.g, c.b);
    const id = pos.length/3 - 1; index.set(key, id); return id;
  }
  for (let i = 0; i < ny-1; i++){
    for (let j = 0; j < nx-1; j++){
      if (levelAt(i,j)===null || levelAt(i+1,j)===null ||
          levelAt(i,j+1)===null || levelAt(i+1,j+1)===null) continue;
      const a = vid(i,j), b = vid(i,j+1), c = vid(i+1,j), d = vid(i+1,j+1);
      idx.push(a, b, d, a, d, c);
    }
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  geo.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
  geo.setIndex(idx); geo.computeVertexNormals();
  const mat = new THREE.MeshBasicMaterial({vertexColors:true, side:THREE.DoubleSide,
    transparent:true, opacity:opacity, depthWrite:false});
  const mesh = new THREE.Mesh(geo, mat);
  mesh.renderOrder = stops === BLUE ? 1 : 2;
  target.add(mesh);
}

function buildBoards(LA, LB){
  boardsGroup.clear();
  const face = new THREE.MeshBasicMaterial({color:0x2f6b4f, transparent:true,
    opacity:0.35, side:THREE.DoubleSide, depthWrite:false});
  const wireA = new THREE.LineBasicMaterial({color:0x2f6b4f, transparent:true, opacity:0.9});
  const wireB = new THREE.LineBasicMaterial({color:0xeb6834, transparent:true, opacity:0.9});
  if (LA) LA.boards.forEach(b => {
    const pts = b.outline.map(p => new THREE.Vector3(...p));
    const geo = new THREE.BufferGeometry().setFromPoints([pts[0],pts[1],pts[2],pts[3]]);
    geo.setIndex([0,1,2,0,2,3]);
    boardsGroup.add(new THREE.Mesh(geo, face));
    boardsGroup.add(new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(pts), wireA));
  });
  if (LB) LB.boards.forEach(b => {
    const pts = b.outline.map(p => new THREE.Vector3(...p));
    boardsGroup.add(new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(pts), wireB));
  });
}

let currentA = null, currentB = null;
function setA(key){
  currentA = DATA.layouts.find(l => l.key === key);
  buildSurface(currentA, BLUE, document.getElementById('opa').value/100, meshA);
  buildBoards(currentA, currentB);
  updateTable();
}
function setB(key){
  currentB = DATA.layouts.find(l => l.key === key);
  buildSurface(currentB, ORANGE, document.getElementById('opb').value/100, meshB);
  buildBoards(currentA, currentB);
  updateTable();
}
function fmt(v, d=1){ return (v===null||v===undefined) ? '—' : v.toFixed(d); }
function updateTable(){
  const rows = [
    ['DI (dB)', m => fmt(m.di_db)],
    ['band peak (dB)', m => fmt(m.band_max_db)],
    ['band energy (%)', m => fmt(m.band_energy_pct)],
    ['leak >60° (%)', m => fmt(m.leak_60_pct, 2)],
    ['54.75° lobe (dB)', m => m.lobe_54_75_db < -60 ? 'null' : fmt(m.lobe_54_75_db)],
  ];
  const tb = document.querySelector('#cmp tbody');
  tb.innerHTML = rows.map(([name, f]) =>
    '<tr><td>' + name + '</td><td>' + (currentA ? f(currentA.metrics) : '—') +
    '</td><td>' + (currentB ? f(currentB.metrics) : '—') + '</td></tr>').join('');
}

const selA = document.getElementById('selA');
const selB = document.getElementById('selB');
for (const l of DATA.layouts){
  selA.add(new Option(l.title, l.key));
  selB.add(new Option(l.title, l.key));
}
selA.value = DATA.defaults.a; selB.value = DATA.defaults.b;
selA.onchange = () => setA(selA.value);
selB.onchange = () => setB(selB.value);
document.getElementById('opa').oninput = e => { if (meshA.children[0]) meshA.children[0].material.opacity = e.target.value/100; };
document.getElementById('opb').oninput = e => { if (meshB.children[0]) meshB.children[0].material.opacity = e.target.value/100; };
document.getElementById('swap').onclick = () => {
  const a = selA.value, b = selB.value;
  selA.value = b; selB.value = a; setA(b); setB(a);
};
setA(selA.value); setB(selB.value);

function resize(){
  const w = stage.clientWidth, h = stage.clientHeight;
  camera.aspect = w/h; camera.updateProjectionMatrix(); renderer.setSize(w, h);
}
addEventListener('resize', resize);
renderer.render(scene, camera);
renderer.setAnimationLoop(() => { controls.update(); renderer.render(scene, camera); });
</script>

<script>
setTimeout(function(){
  if (document.querySelector('#stage canvas')) return;
  var d = document.createElement('div');
  d.style.cssText = 'position:absolute;inset:0;display:flex;align-items:center;justify-content:center;text-align:center;padding:40px;font:13px/1.5 sans-serif;color:#5f6964;background:#fcfcfb';
  d.textContent = 'The 3D view needs WebGL; the tables and the cut inset on the right work regardless.';
  document.getElementById('stage').appendChild(d);
}, 4000);
</script>
</body>
</html>
""")


def write_overlay(layouts: list[dict], path: Path, default_a: str,
                  default_b: str) -> None:
    html = Template(OVERLAY_TEMPLATE.template).substitute(
        data=json.dumps({"layouts": layouts,
                         "defaults": {"a": default_a, "b": default_b}}),
        surface=SURFACE,
    )
    path.write_text(html, encoding="utf-8")
