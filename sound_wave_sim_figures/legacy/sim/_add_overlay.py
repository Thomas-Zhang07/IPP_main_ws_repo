"""Add an overlay comparison page: two layouts, independent opacity."""

import pathlib

p = pathlib.Path("sim/export_web.py")
s = p.read_text(encoding="utf-8")

addition = '''

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

function buildBoards(L){
  boardsGroup.clear();
  const face = new THREE.MeshBasicMaterial({color:0x2f6b4f, transparent:true,
    opacity:0.35, side:THREE.DoubleSide, depthWrite:false});
  const wire = new THREE.LineBasicMaterial({color:0xeb6834, transparent:true, opacity:0.9});
  L.boards.forEach((b, k) => {
    const pts = b.outline.map(p => new THREE.Vector3(...p));
    if (k === 0){
      const geo = new THREE.BufferGeometry().setFromPoints([pts[0],pts[1],pts[2],pts[3]]);
      geo.setIndex([0,1,2,0,2,3]);
      boardsGroup.add(new THREE.Mesh(geo, face));
    }
    boardsGroup.add(new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(pts), wire));
  });
}

let currentA = null, currentB = null;
function setA(key){
  currentA = DATA.layouts.find(l => l.key === key);
  buildSurface(currentA, BLUE, document.getElementById('opa').value/100, meshA);
  buildBoards(currentA);
  updateTable();
}
function setB(key){
  currentB = DATA.layouts.find(l => l.key === key);
  buildSurface(currentB, ORANGE, document.getElementById('opb').value/100, meshB);
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
renderer.setAnimationLoop(() => { controls.update(); renderer.render(scene, camera); });
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
'''

s = s + addition
p.write_text(s, encoding="utf-8")
print("overlay template added")
