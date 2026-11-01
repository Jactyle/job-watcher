// An interactive 3D globe drawn on a canvas, with no libraries. The land is a grid of dots made from land-110m.json
// (Natural Earth, public domain, via the world-atlas package). Drag to rotate; zoom with the buttons, a pinch, or ctrl/⌘ + scroll.
// Each marker sits at the middle of a country, so this shows the general location of postings, not a street address.

// [latitude, longitude] of the middle of every country that countryOf() in country.js can return.
const COUNTRY_POS = {
  "United States": [39.5, -98.5], "Canada": [56, -96], "United Kingdom": [54, -2.5], "Ireland": [53.3, -8], "India": [21, 78],
  "China": [35, 103], "Japan": [36, 138], "South Korea": [36.5, 127.8], "Taiwan": [23.7, 121], "Singapore": [1.35, 103.82],
  "Malaysia": [4.2, 102], "Philippines": [12.9, 122], "Vietnam": [16, 107.8], "Thailand": [15, 101], "Indonesia": [-2.5, 118],
  "Hong Kong": [22.3, 114.17], "Australia": [-25, 134], "New Zealand": [-41, 173], "Israel": [31.4, 35], "United Arab Emirates": [24, 54],
  "Saudi Arabia": [24, 45], "Egypt": [26.5, 30], "Turkey": [39, 35], "South Africa": [-29, 24.5], "Nigeria": [9, 8], "Kenya": [0.2, 37.9],
  "Morocco": [31.8, -7], "Pakistan": [30, 70], "Germany": [51, 10.4], "France": [46.6, 2.4], "Spain": [40.2, -3.7], "Portugal": [39.6, -8],
  "Italy": [42.8, 12.5], "Netherlands": [52.2, 5.3], "Belgium": [50.6, 4.6], "Luxembourg": [49.8, 6.1], "Switzerland": [46.8, 8.2],
  "Austria": [47.5, 14.5], "Sweden": [62, 15], "Norway": [61, 9], "Denmark": [56, 9.5], "Finland": [64, 26], "Iceland": [64.9, -18.6],
  "Poland": [52, 19.4], "Czech Republic": [49.8, 15.5], "Slovakia": [48.7, 19.5], "Hungary": [47.2, 19.4], "Romania": [45.9, 25],
  "Bulgaria": [42.7, 25.3], "Greece": [39, 22], "Serbia": [44, 21], "Croatia": [45.1, 15.5], "Ukraine": [49, 31.5], "Lithuania": [55.3, 23.9],
  "Latvia": [56.9, 24.9], "Estonia": [58.7, 25.5], "Mexico": [23.6, -102.5], "Brazil": [-10, -52], "Argentina": [-35, -65],
  "Colombia": [4.6, -74], "Chile": [-33, -70.7], "Peru": [-9.2, -75], "Costa Rica": [9.9, -84.2], "Panama": [8.5, -80],
  "Uruguay": [-32.5, -55.8], "Guatemala": [15.5, -90.3], "Armenia": [40.1, 45], "Slovenia": [46.1, 14.8], "Tunisia": [34, 9.5],
  "Qatar": [25.3, 51.2], "Dominican Republic": [18.9, -70.2],
};

// land-110m.json is a TopoJSON file: shared arcs stored as running differences. Turn it into polygons of [lon, lat] rings.
function decodeLand(topo) {
  const [sx, sy] = topo.transform.scale, [tx, ty] = topo.transform.translate;
  const arcs = topo.arcs.map(a => { let x = 0, y = 0; return a.map(([dx, dy]) => [(x += dx) * sx + tx, (y += dy) * sy + ty]); });
  const ring = idx => {
    const pts = [];
    for (const i of idx) { const a = i < 0 ? arcs[~i].slice().reverse() : arcs[i]; pts.push(...(pts.length ? a.slice(1) : a)); }
    return pts;
  };
  const polys = [];
  for (const g of topo.objects.land.geometries) {
    if (g.type === "Polygon") polys.push(g.arcs.map(ring));
    else if (g.type === "MultiPolygon") g.arcs.forEach(p => polys.push(p.map(ring)));
  }
  return polys;
}

const _inRing = (lon, lat, r) => {
  let inside = false;
  for (let i = 0, j = r.length - 1; i < r.length; j = i++) {
    const [xi, yi] = r[i], [xj, yj] = r[j];
    if ((yi > lat) !== (yj > lat) && lon < (xj - xi) * (lat - yi) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
};

// Evenly spaced points over the sphere (fewer per row near the poles), kept where they fall on land.
function landDots(polys, step) {
  const boxes = polys.map(p => { let a = 1e9, b = -1e9, c = 1e9, d = -1e9; for (const [x, y] of p[0]) { a = Math.min(a, x); b = Math.max(b, x); c = Math.min(c, y); d = Math.max(d, y); } return [a, b, c, d]; });
  const out = [];
  for (let lat = -88; lat <= 88; lat += step) {
    const n = Math.max(1, Math.round(360 * Math.cos(lat * Math.PI / 180) / step));
    for (let k = 0; k < n; k++) {
      const lon = -180 + (k + 0.5) * 360 / n;
      for (let i = 0; i < polys.length; i++) {
        const [a, b, c, d] = boxes[i];
        if (lon < a || lon > b || lat < c || lat > d) continue;
        if (polys[i].reduce((in_, r) => in_ !== _inRing(lon, lat, r), false)) { out.push([lon, lat]); break; }
      }
    }
  }
  return out;
}

// hooks: onHover(marker|null, x, y), onSelect(marker|null), onSpin(bool), theme (optional colors: atmo, sphere[3], grid, coast, dots, limb)
function createGlobe(canvas, topo, hooks = {}) {
  const ctx = canvas.getContext("2d"), rad = Math.PI / 180;
  const vec = (lon, lat) => [Math.cos(lat * rad) * Math.cos(lon * rad), Math.cos(lat * rad) * Math.sin(lon * rad), Math.sin(lat * rad)];
  const polys = decodeLand(topo);
  const dots = landDots(polys, 2.2).map(([lo, la]) => vec(lo, la));
  const coast = polys.flatMap(p => p.map(r => r.map(([lo, la]) => vec(lo, la))));
  const grid = [];
  for (let lo = -180; lo < 180; lo += 30) { const l = []; for (let la = -90; la <= 90; la += 5) l.push(vec(lo, la)); grid.push(l); }
  for (let la = -60; la <= 60; la += 30) { const l = []; for (let lo = -180; lo <= 180; lo += 5) l.push(vec(lo, la)); grid.push(l); }

  const T = Object.assign({ atmo: "79,232,224", sphere: ["#134044", "#0a2326", "#030c0e"], grid: "79,232,224", coast: "79,232,224", dots: "#8ff5ee", limb: "1,8,9" }, hooks.theme || {});
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const view = { lon: -40, lat: 22, zoom: 1 };
  let markers = [], color = "255,224,138", selected = null, hover = null, spin = !reduced, size = 400, dpr = 1;
  let anim = null, drag = null, vel = { x: 0, y: 0 }, dirty = true, lastT = 0;
  const pointers = new Map();
  let pinch = 0;

  const basis = () => {
    const l = view.lon * rad, p = view.lat * rad;
    return { c: [Math.cos(p) * Math.cos(l), Math.cos(p) * Math.sin(l), Math.sin(p)], e: [-Math.sin(l), Math.cos(l), 0], u: [-Math.sin(p) * Math.cos(l), -Math.sin(p) * Math.sin(l), Math.cos(p)] };
  };
  const radius = () => size * 0.42 * view.zoom;
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const dot3 = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];

  function resize() {
    const box = canvas.parentElement.getBoundingClientRect();
    size = Math.max(280, Math.min(box.width, innerHeight * 0.82, 820));
    dpr = Math.min(2, devicePixelRatio || 1);
    canvas.style.width = canvas.style.height = size + "px";
    canvas.width = canvas.height = Math.round(size * dpr);
    dirty = true;
  }

  function draw(t) {
    const B = basis(), R = radius(), cx = size / 2, cy = size / 2;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, size, size);
    // atmosphere glow, then the ocean sphere lit from the upper left
    let g = ctx.createRadialGradient(cx, cy, R * 0.96, cx, cy, R * 1.16);
    g.addColorStop(0, `rgba(${T.atmo},.30)`); g.addColorStop(1, `rgba(${T.atmo},0)`);
    ctx.fillStyle = g; ctx.beginPath(); ctx.arc(cx, cy, R * 1.16, 0, 7); ctx.fill();
    g = ctx.createRadialGradient(cx - R * 0.38, cy - R * 0.42, R * 0.1, cx, cy, R);
    g.addColorStop(0, T.sphere[0]); g.addColorStop(0.55, T.sphere[1]); g.addColorStop(1, T.sphere[2]);
    ctx.fillStyle = g; ctx.beginPath(); ctx.arc(cx, cy, R, 0, 7); ctx.fill();
    // graticule
    ctx.strokeStyle = `rgba(${T.grid},.14)`; ctx.lineWidth = 1; ctx.beginPath();
    for (const line of grid) {
      let pen = false;
      for (const v of line) {
        if (dot3(v, B.c) <= 0) { pen = false; continue; }
        const x = cx + R * dot3(v, B.e), y = cy - R * dot3(v, B.u);
        pen ? ctx.lineTo(x, y) : ctx.moveTo(x, y); pen = true;
      }
    }
    ctx.stroke();
    // land: coastline, then dots that fade toward the edge
    ctx.strokeStyle = `rgba(${T.coast},.6)`; ctx.beginPath();
    for (const ringPts of coast) {
      let pen = false;
      for (const v of ringPts) {
        if (dot3(v, B.c) <= 0) { pen = false; continue; }
        const x = cx + R * dot3(v, B.e), y = cy - R * dot3(v, B.u);
        pen ? ctx.lineTo(x, y) : ctx.moveTo(x, y); pen = true;
      }
    }
    ctx.stroke();
    const s = Math.max(1.3, R / 170);
    ctx.fillStyle = T.dots;
    for (const v of dots) {
      const z = dot3(v, B.c); if (z <= 0.02) continue;
      ctx.globalAlpha = 0.2 + 0.7 * z;
      ctx.fillRect(cx + R * dot3(v, B.e) - s / 2, cy - R * dot3(v, B.u) - s / 2, s, s);
    }
    ctx.globalAlpha = 1;
    // limb darkening gives the sphere its depth
    g = ctx.createRadialGradient(cx, cy, R * 0.6, cx, cy, R);
    g.addColorStop(0, "rgba(0,0,0,0)"); g.addColorStop(1, `rgba(${T.limb},.66)`);
    ctx.fillStyle = g; ctx.beginPath(); ctx.arc(cx, cy, R, 0, 7); ctx.fill();
    // markers, big ones first so small ones stay visible on top
    const max = Math.max(1, ...markers.map(m => m.count)), unit = R / 250;
    for (const m of markers) {
      const v = m._v, z = dot3(v, B.c);
      m._z = z; m._x = cx + R * dot3(v, B.e); m._y = cy - R * dot3(v, B.u);
      m._r = Math.max(3.5, (3.5 + 20 * Math.sqrt(m.count / max)) * unit);
    }
    for (const m of markers) {
      if (m._z <= 0.04) continue;
      const fade = Math.min(1, m._z / 0.3), on = m === selected, hot = on || m === hover;
      ctx.globalAlpha = fade;
      g = ctx.createRadialGradient(m._x, m._y, 0, m._x, m._y, m._r * 2.2);
      g.addColorStop(0, `rgba(${color},.55)`); g.addColorStop(1, `rgba(${color},0)`);
      ctx.fillStyle = g; ctx.beginPath(); ctx.arc(m._x, m._y, m._r * 2.2, 0, 7); ctx.fill();
      ctx.fillStyle = `rgba(${color},${hot ? 0.8 : 0.5})`; ctx.strokeStyle = hot ? "#fff" : `rgba(${color},.95)`; ctx.lineWidth = hot ? 2.5 : 1.5;
      ctx.beginPath(); ctx.arc(m._x, m._y, m._r, 0, 7); ctx.fill(); ctx.stroke();
      ctx.fillStyle = "#fff"; ctx.beginPath(); ctx.arc(m._x, m._y, 2, 0, 7); ctx.fill();
      if (on) { ctx.strokeStyle = "rgba(255,255,255,.55)"; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.arc(m._x, m._y, m._r + 6 + 3 * Math.sin(t / 260), 0, 7); ctx.stroke(); }
    }
    ctx.globalAlpha = 1;
  }

  function hit(px, py) {
    let best = null, bd = 1e9;
    for (const m of markers) {
      if (m._z === undefined || m._z <= 0.12) continue;
      const d = Math.hypot(px - m._x, py - m._y), lim = Math.max(m._r, 9);
      if (d <= lim && d / lim < bd) { best = m; bd = d / lim; }
    }
    return best;
  }

  function tick(t) {
    const dt = Math.min(50, t - lastT || 16); lastT = t;
    let busy = dirty || !!selected;
    if (anim) {
      const k = clamp((t - anim.t0) / anim.dur, 0, 1), e = 1 - Math.pow(1 - k, 3);
      view.lon = anim.lon0 + (anim.lon1 - anim.lon0) * e; view.lat = anim.lat0 + (anim.lat1 - anim.lat0) * e; view.zoom = anim.z0 + (anim.z1 - anim.z0) * e;
      if (k >= 1) anim = null; busy = true;
    } else if (!drag && (Math.abs(vel.x) > 0.002 || Math.abs(vel.y) > 0.002)) {
      view.lon += vel.x * dt; view.lat = clamp(view.lat + vel.y * dt, -85, 85);
      vel.x *= 0.94; vel.y *= 0.94; busy = true;
    } else if (spin && !drag && !hover) { view.lon += dt * 0.006; busy = true; }
    if (!anim) { if (view.lon > 180) view.lon -= 360; if (view.lon < -180) view.lon += 360; }
    if (busy) { draw(t); dirty = false; }
    requestAnimationFrame(tick);
  }

  const setSpin = on => { spin = on; hooks.onSpin && hooks.onSpin(on); };
  const rel = e => { const b = canvas.getBoundingClientRect(); return [e.clientX - b.left, e.clientY - b.top]; };
  canvas.addEventListener("pointerdown", e => {
    canvas.setPointerCapture(e.pointerId); pointers.set(e.pointerId, rel(e));
    anim = null; vel = { x: 0, y: 0 };
    if (pointers.size === 1) drag = { x: e.clientX, y: e.clientY, moved: 0, t: performance.now() };
    if (pointers.size === 2) { const [a, b] = [...pointers.values()]; pinch = Math.hypot(a[0] - b[0], a[1] - b[1]); drag = null; }
  });
  canvas.addEventListener("pointermove", e => {
    const p = rel(e);
    if (pointers.has(e.pointerId)) pointers.set(e.pointerId, p);
    if (pointers.size === 2) {
      const [a, b] = [...pointers.values()], d = Math.hypot(a[0] - b[0], a[1] - b[1]);
      if (pinch) view.zoom = clamp(view.zoom * d / pinch, 0.8, 4); pinch = d; dirty = true; return;
    }
    if (drag) {
      const dx = e.clientX - drag.x, dy = e.clientY - drag.y, k = 57.3 / radius();
      drag.moved += Math.abs(dx) + Math.abs(dy);
      if (drag.moved > 4) { if (spin) setSpin(false); hover = null; hooks.onHover && hooks.onHover(null); }
      const dtm = Math.max(1, performance.now() - drag.t); drag.t = performance.now();
      view.lon -= dx * k; view.lat = clamp(view.lat + dy * k, -85, 85);
      vel = { x: -dx * k / dtm, y: dy * k / dtm };
      drag.x = e.clientX; drag.y = e.clientY; dirty = true; canvas.style.cursor = "grabbing";
    } else {
      const m = hit(p[0], p[1]);
      if (m !== hover) { hover = m; dirty = true; hooks.onHover && hooks.onHover(m, p[0], p[1]); }
      else if (m) hooks.onHover && hooks.onHover(m, p[0], p[1]);
      canvas.style.cursor = m ? "pointer" : "grab";
    }
  });
  const up = e => {
    const wasClick = drag && drag.moved <= 4 && pointers.size === 1;
    pointers.delete(e.pointerId); if (pointers.size < 2) pinch = 0;
    if (wasClick) { const p = rel(e), m = hit(p[0], p[1]); hooks.onSelect && hooks.onSelect(m); }
    drag = null; canvas.style.cursor = "grab";
  };
  canvas.addEventListener("pointerup", up); canvas.addEventListener("pointercancel", up);
  canvas.addEventListener("pointerleave", () => { if (hover && !drag) { hover = null; dirty = true; hooks.onHover && hooks.onHover(null); } });
  canvas.addEventListener("wheel", e => { if (!(e.ctrlKey || e.metaKey)) return; e.preventDefault(); view.zoom = clamp(view.zoom * Math.exp(-e.deltaY * 0.01), 0.8, 4); dirty = true; }, { passive: false });
  canvas.addEventListener("keydown", e => {
    const step = 10 / view.zoom, k = e.key;
    if (k === "ArrowLeft") view.lon -= step; else if (k === "ArrowRight") view.lon += step;
    else if (k === "ArrowUp") view.lat = clamp(view.lat + step, -85, 85); else if (k === "ArrowDown") view.lat = clamp(view.lat - step, -85, 85);
    else if (k === "+" || k === "=") view.zoom = clamp(view.zoom * 1.2, 0.8, 4); else if (k === "-") view.zoom = clamp(view.zoom / 1.2, 0.8, 4);
    else return;
    e.preventDefault(); if (spin) setSpin(false); dirty = true;
  });
  new ResizeObserver(resize).observe(canvas.parentElement);
  resize(); requestAnimationFrame(tick);

  return {
    // list: [{name, lat, lon, count}]; rgb: "r,g,b"
    setMarkers(list, rgb) {
      color = rgb || color;
      markers = list.map(m => ({ ...m, _v: vec(m.lon, m.lat) })).sort((a, b) => b.count - a.count);
      selected = selected && markers.find(m => m.name === selected.name) || null; hover = null; dirty = true;
    },
    select(name) { selected = markers.find(m => m.name === name) || null; dirty = true; },
    focus(name, zoomTo) {
      const m = markers.find(x => x.name === name); if (!m) return;
      let d = m.lon - view.lon; while (d > 180) d -= 360; while (d < -180) d += 360;
      anim = { t0: performance.now(), dur: 900, lon0: view.lon, lon1: view.lon + d, lat0: view.lat, lat1: clamp(m.lat, -60, 70), z0: view.zoom, z1: zoomTo || Math.max(view.zoom, 1.35) };
      if (spin) setSpin(false);
    },
    zoomBy(f) { view.zoom = clamp(view.zoom * f, 0.8, 4); dirty = true; },
    reset() { anim = { t0: performance.now(), dur: 700, lon0: view.lon, lon1: -40, lat0: view.lat, lat1: 22, z0: view.zoom, z1: 1 }; },
    setSpin,
    get spinning() { return spin; },
  };
}
