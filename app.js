// Shared by all four pages: navigation, data loading, helpers, screen effects and sound.
const PAGES = [["index.html", "Today"], ["browse.html", "Browse"], ["market.html", "Market"], ["globe.html", "Globe"]];

function renderNav() {
  const here = location.pathname.split("/").pop() || "index.html";
  const links = PAGES.map(([h, t]) => `<a class="link${h === here ? " on" : ""}" href="${h}">${t}</a>`).join("");
  document.body.insertAdjacentHTML("afterbegin",
    `<header class="nav"><div class="in"><a class="brand" href="index.html" aria-label="Job Watcher home"><i class="logo"></i><span>Job Watcher</span></a>${links}<span class="navchip" id="navchip"></span><button class="fxbtn" id="fxbtn" type="button" aria-pressed="true" title="Screen effects (jitter, glitches, scanning light): on or off">FX</button><button class="fxbtn icon" id="sndbtn" type="button" aria-pressed="true" aria-label="Sound effects" title="Sound effects: on or off"><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="square" stroke-linejoin="miter" aria-hidden="true"><path d="M3 9.5h3.5L11 5.5v13L6.5 14.5H3z"/><path class="w1" d="M14.5 9.2a4 4 0 0 1 0 5.6"/><path class="w2" d="M17.3 6.8a7.5 7.5 0 0 1 0 10.4"/><path class="x" d="M15 9l6 6M21 9l-6 6"/></svg></button></div></header>` +
    `<div class="offline" id="offline">Offline: showing the last data this device loaded.</div>`);
}

function parseCSV(text) {
  const rows = []; let row = [], cell = "", q = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (q) {
      if (c === '"') { if (text[i + 1] === '"') { cell += '"'; i++; } else q = false; } else cell += c;
    } else if (c === '"') q = true;
    else if (c === ",") { row.push(cell); cell = ""; }
    else if (c === "\n") { row.push(cell); rows.push(row); row = []; cell = ""; }
    else if (c !== "\r") cell += c;
  }
  if (cell || row.length) { row.push(cell); rows.push(row); }
  const head = rows.shift() || [];
  return rows.filter(r => r.length === head.length).map(r => {
    const o = {}; head.forEach((h, i) => (o[h] = r[i])); return o;
  });
}

async function loadData() {
  const [h, s] = await Promise.all([
    fetch("data/history.csv", { cache: "no-store" }),
    fetch("data/status.json", { cache: "no-store" }),
  ]);
  if (!h.ok || !s.ok) throw new Error("data unavailable");
  if (h.headers.get("x-from-cache") || s.headers.get("x-from-cache")) document.getElementById("offline").style.display = "block";
  const rows = parseCSV(await h.text());
  for (const r of rows) { r.in_role = r.in_role === "true"; r.first_run = r.first_run === "true"; }
  const status = await s.json();
  const chip = document.getElementById("navchip");
  if (chip && status.run_time) chip.textContent = `Last run ${status.run_time.slice(0, 10)} ${status.run_time.slice(11, 16)} UTC`;
  return { rows, status };
}

const lastRunDate = (status) => (status.run_time || "").slice(0, 10);
const dayNum = (d) => Date.UTC(+d.slice(0, 4), +d.slice(5, 7) - 1, +d.slice(8, 10)) / 86400000;
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const safeUrl = (u) => (/^https?:\/\//i.test(u) ? u : "#");
// The employer mark: a letter tile with the employer's logo on top.
const mono = (employer, big = false, source = "") => {
  const letter = esc(String(employer || "?").trim().charAt(0).toUpperCase());
  // The employer's logo (logos/<source>.png) sits on top of the letter tile; if it will not load, the letter shows.
  const img = source ? `<img src="logos/${esc(source)}.png" alt="" loading="lazy" decoding="async" onerror="this.parentNode.classList.remove('has-logo');this.remove()">` : "";
  return `<span class="mono${big ? " big" : ""}${img ? " has-logo" : ""}"><b>${letter}</b>${img}</span>`;
};
// Source keys in status.json are lowercase ("taketwo"); show each source as its employer's name ("Take-Two Interactive").
const sourceNames = (rows) => { const m = {}; for (const r of rows) if (r.source && r.employer && !m[r.source]) m[r.source] = r.employer; return m; };
// "In role" is decided by the title rule in pipeline/rules.py. This is the same rule in plain words, shown from any "?" button.
const ROLE_TIP = "In role: the title looks like a financial analyst or data analyst job. Click the ? button for the full rule.";
function showRoleHelp() {
  let d = document.getElementById("roleDialog");
  if (!d) {
    d = document.createElement("dialog"); d.id = "roleDialog"; d.setAttribute("aria-labelledby", "roleDialogTitle");
    d.innerHTML = `<h2 id="roleDialogTitle">What “in role” means</h2>
      <p>This tool watches for <b>financial analyst and data analyst</b> jobs. A posting is marked <b>in role</b> when its <em>title</em> passes three checks:</p>
      <ol>
        <li>The title contains the word <b>analyst</b>.</li>
        <li>It also names a <b>finance</b> topic (finance or financial, FP&amp;A, accounting, treasury, credit, investment, revenue, pricing, budget, forecast, controller, audit, equity, portfolio, valuation, capital markets, corporate development, business planning) <b>or</b> a <b>data</b> topic (data but not data center, analytics, business intelligence, BI, insights, reporting, quantitative, product, game, gameplay, player).</li>
        <li>It does <b>not</b> contain intern, sales, recruiter, support or engineer.</li>
      </ol>
      <div class="eg"><p class="yes"><b>✓ In role:</b> Senior Treasury Analyst · Data Analyst, Card · FP&amp;A Analyst · Product Analyst</p>
        <p class="no"><b>✗ Not in role:</b> Business Analyst (no finance or data word) · Data Engineer (not an analyst) · Financial Analyst Intern · Sales Analyst</p></div>
      <p class="meta">Only the title is read, not the job description, so a few relevant jobs can be missed and a few others included. “All postings” shows every posting, in role or not.</p>
      <p class="actions"><button class="btn primary" type="button" data-close>Got it</button></p>`;
    d.addEventListener("click", e => { if (e.target === d || e.target.closest("[data-close]")) d.close(); });
    document.body.appendChild(d);
  }
  d.showModal(); snd.scan();
}
document.addEventListener("click", e => { if (e.target.closest("[data-rolehelp]")) showRoleHelp(); });
const ROLE_BTN = '<button class="info" type="button" data-rolehelp aria-label="What does in role mean?" title="What does “in role” mean?">?</button>';
const plural = (n, w) => `${n.toLocaleString()} ${w}${n === 1 ? "" : "s"}`;

function showError(e) {
  document.querySelector("main").innerHTML = `<div class="card">Could not load data: ${esc(e.message)}</div>`;
}

if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(() => {});
renderNav();

// the sound module (sfx.js); if it is missing, every call is a no-op
const snd = window.sfx || new Proxy({}, { get: (t, k) => (k === "on" ? false : () => {}) });

// ---- Screen effects: the worn, glitching glass of the film's screens. One FX switch turns them all off; they never run for people who ask for reduced motion. ----
const FX_KEY = "job-watcher-fx";
const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
const narrowScreen = () => matchMedia("(max-width: 900px)").matches;
let fxOn = !reducedMotion;
try { if (localStorage.getItem(FX_KEY) === "off") fxOn = false; } catch (e) {}
function setFX(on, save) {
  fxOn = on && !reducedMotion;
  document.documentElement.classList.toggle("no-fx", !fxOn);
  const b = document.getElementById("fxbtn"); if (b) { b.classList.toggle("on", fxOn); b.setAttribute("aria-pressed", fxOn); }
  if (save) { try { localStorage.setItem(FX_KEY, fxOn ? "on" : "off"); } catch (e) {} }
}
// a rolling refresh band sits over the page (CSS animates it)
document.body.insertAdjacentHTML("beforeend", '<div class="fx-roll" aria-hidden="true"></div>');
const fxButton = document.getElementById("fxbtn");
if (reducedMotion) fxButton.hidden = true; else fxButton.onclick = () => setFX(!fxOn, true);
setFX(fxOn, false);

// every few seconds something on screen tears sideways for an instant, with a red and blue split
(function glitchLoop() {
  if (fxOn && !narrowScreen() && !document.hidden) {
    const el = document.elementFromPoint(40 + Math.random() * (innerWidth - 80), 90 + Math.random() * (innerHeight - 130));
    const target = el && el.closest("h1, .stat, .section:not(.bare), .tile, .job, .pill, .rank li, .gsel, header.nav .link, .navchip, .brand, .count");
    if (target) { target.classList.add("fx-glitch"); setTimeout(() => target.classList.remove("fx-glitch"), 240); snd.glitch(); }
  }
  setTimeout(glitchLoop, 1500 + Math.random() * 4500);
})();

// big numbers scramble and then resolve, like a readout locking on (the final text is always the real value)
function fxDecode(el) {
  const final = el.textContent;
  if (!fxOn || !/\d/.test(final)) return;
  const start = performance.now(), dur = 650, digits = "0123456789";
  const step = now => {
    const k = Math.min(1, (now - start) / dur);
    el.textContent = [...final].map((c, i) => (/\d/.test(c) && i / final.length >= k ? digits[Math.floor(Math.random() * 10)] : c)).join("");
    if (k < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
  setTimeout(() => { el.textContent = final; }, dur + 400);
}
if (document.documentElement.dataset.theme === "today") {   // only Today has the big counts
  const watcher = new MutationObserver(() => {
    const fresh = document.querySelectorAll(".stat .n:not([data-fx])");
    if (!fresh.length) return;
    fresh.forEach(n => { n.dataset.fx = "1"; fxDecode(n); }); if (fxOn) snd.decode();
    watcher.disconnect();   // the counts are drawn once, so stop watching
  });
  watcher.observe(document.body, { childList: true, subtree: true });
}

// moving between pages plays a screen power-down first, so each page feels like a new terminal switching on
document.addEventListener("click", e => {
  const a = e.target.closest("header.nav a.link, header.nav a.brand");
  if (!a || !fxOn || narrowScreen() || e.button || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
  if ((new URL(a.href, location.href)).pathname === location.pathname) return;
  e.preventDefault();
  // collapse toward the middle of what is on screen, however tall the page is and wherever it is scrolled
  const m = document.querySelector("main");
  if (m) m.style.transformOrigin = `50% ${Math.round(scrollY + innerHeight * 0.45 - (m.getBoundingClientRect().top + scrollY))}px`;
  document.body.insertAdjacentHTML("beforeend", '<div class="fx-off" aria-hidden="true"></div>');
  document.documentElement.classList.add("switching"); snd.powerdown();
  setTimeout(() => { location.href = a.href; }, 230);
});
addEventListener("pageshow", () => { document.documentElement.classList.remove("switching"); document.querySelectorAll(".fx-off").forEach(n => n.remove()); const m = document.querySelector("main"); if (m) m.style.transformOrigin = ""; });

// ---- Sound (see sfx.js): off until the SND button is pressed ----
const sndButton = document.getElementById("sndbtn");
const syncSnd = () => { sndButton.classList.toggle("on", !!snd.on); sndButton.setAttribute("aria-pressed", !!snd.on); };
if (!window.sfx || !(window.AudioContext || window.webkitAudioContext)) sndButton.hidden = true;
sndButton.onclick = () => { snd.set(!snd.on); syncSnd(); };
syncSnd();
addEventListener("pointerdown", () => snd.wake(), { passive: true });
addEventListener("keydown", () => snd.wake(), true);
// clicks: a blip (higher for filters, lower for the main action), a chime when something is saved, a lower tone when it is removed
document.addEventListener("click", e => {
  if (!snd.on || e.target.closest("#sndbtn, header.nav a")) return;
  const star = e.target.closest(".star, #saveBtn");
  if (star) { (star.classList.contains("on") || /saved/i.test(star.textContent) ? snd.low : snd.chime)(); return; }
  const t = e.target.closest(".btn, button.pill, .job, .tile, .rank button, button.info, .fxbtn, a.apply, .linkbtn, .emps a");
  if (t) snd.blip(t.matches(".btn.primary") ? 880 : t.matches("button.pill, .rank button") ? 1500 : 1180);
});
// a faint tick as the pointer moves onto something clickable
let hoverEl = null;
document.addEventListener("pointerover", e => {
  if (!snd.on) return;
  const t = e.target.closest(".tile.post, .job, .btn, button.pill, .rank button, header.nav a.link, .star, button.info, .fxbtn");
  if (t && t !== hoverEl) { hoverEl = t; snd.tick(); } else if (!t) hoverEl = null;
}, true);

// ---- Startup: a dead black monitor with one dim hairline fills the screen, and a click boots it up. ----
// The look is the Wallace Corporation's: pure black, warm gold-white light, hairline geometry. The line stretches across the screen, the picture opens from it
// in a flash of light, and the page rolls and locks in. Once per browser session. The page decides this before it paints (see the small script in each page's
// head), so it is never shown for reduced motion, with the FX switch off, on a deep link or in an automated browser. It waits for you: a click, or Enter or Space.
(function () {
  const root = document.documentElement;
  if (!root.classList.contains("intro")) return;
  if (!fxOn) { root.classList.remove("intro"); return; }
  document.body.insertAdjacentHTML("beforeend",
    '<div class="crt" id="crt" role="button" tabindex="0" aria-label="Turn on the screen. Click, or press Enter or Space.">' +
    '<div class="crt-half top"></div><div class="crt-half bottom"></div>' +
    '<div class="crt-bloom"></div><i class="crt-dormant"></i><div class="crt-line"></div></div>');
  const crt = document.getElementById("crt");
  crt.focus({ preventScroll: true });
  let started = false;
  const powerOn = () => {
    if (started) return; started = true;
    try { sessionStorage.setItem("job-watcher-booted", "1"); } catch (e) {}
    snd.poweron(); snd.wake();                       // the switch-on sound, and the ambient loop under it
    crt.classList.add("fading", "line");             // the dim line goes out and a bright line shoots across the middle
    setTimeout(() => {
      crt.classList.add("opening");                  // the picture opens outward from the line, in a flash of light
      root.classList.remove("intro"); root.classList.add("booting");   // and the page rolls and locks in behind it
      setTimeout(() => crt.remove(), 650);
    }, 330);
  };
  crt.addEventListener("click", powerOn);
  addEventListener("keydown", e => { if (!started && (e.key === "Enter" || e.key === " ") && !e.metaKey && !e.ctrlKey && !e.altKey) { e.preventDefault(); powerOn(); } }, true);
})();

// ---- A looping background for each terminal, behind the page (decoration only; the FX switch, reduced motion and phones turn it off) ----
(function backgroundLoop() {
  const theme = document.documentElement.dataset.theme;
  const layers = {
    today: '<i class="sweep"></i><i class="ring r1"></i><i class="ring r2"></i><i class="ring r3"></i>',   // a radar sweep with rings pulsing out
    browse: '<i class="film l"></i><i class="film r"></i><i class="scanbar"></i>',                           // film advancing down both edges, a scan bar
    market: '<div class="lenswrap"><i class="lens a"></i><i class="lens b"></i></div><i class="scanline"></i>',   // optical lens rings turning, a line scanning across
    globe: "",                                                                                               // drifting particles, below
  };
  if (!(theme in layers)) return;
  let html = layers[theme];
  if (theme === "globe") {
    let seed = 7; const rnd = () => (seed = (seed * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff;
    const field = (n, color) => Array.from({ length: n }, () => { const x = (rnd() * 100).toFixed(1), y = (rnd() * 100).toFixed(1); return `${x}vw ${y}vh ${color}, ${x}vw ${(+y + 100).toFixed(1)}vh ${color}`; }).join(",");
    html = `<i class="stars s1" style="box-shadow:${field(70, "rgba(79,232,224,.55)")}"></i><i class="stars s2" style="box-shadow:${field(45, "rgba(255,224,138,.6)")}"></i><i class="stars s3" style="box-shadow:${field(22, "rgba(255,241,220,.8)")}"></i>`;
  }
  document.body.insertAdjacentHTML("afterbegin", `<div class="bgloop bg-${theme}" aria-hidden="true">${html}</div>`);
})();
