// Shared by all three pages: navigation, data loading, helpers.
const PAGES = [["index.html", "Today"], ["browse.html", "Browse"], ["market.html", "Market"]];

function renderNav() {
  const here = location.pathname.split("/").pop() || "index.html";
  const links = PAGES.map(([h, t]) => `<a class="link${h === here ? " on" : ""}" href="${h}">${t}</a>`).join("");
  document.body.insertAdjacentHTML("afterbegin",
    `<header class="nav"><div class="in"><a class="brand" href="index.html">Job Watcher</a>${links}</div></header>` +
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
  return { rows, status: await s.json() };
}

const lastRunDate = (status) => (status.run_time || "").slice(0, 10);
const dayNum = (d) => Date.UTC(+d.slice(0, 4), +d.slice(5, 7) - 1, +d.slice(8, 10)) / 86400000;
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const plural = (n, w) => `${n.toLocaleString()} ${w}${n === 1 ? "" : "s"}`;

function showError(e) {
  document.querySelector("main").innerHTML = `<div class="card">Could not load data: ${esc(e.message)}</div>`;
}

if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(() => {});
renderNav();
