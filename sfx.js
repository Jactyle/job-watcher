// Sound for the terminals. There are no audio files: every sound is made in the browser with the Web Audio API, in the spirit of the
// film's score and screen sounds (a low brass swell, an ambient bed that is different on every page, soft holographic blips with long echoes, bursts of static, sonar pings).
// It is on by default (the speaker icon in the nav bar turns it off), but browsers only let a page make sound after a click, so on every page
// it starts at the first click or key press.
window.sfx = (() => {
  const KEY = "job-watcher-sound";
  let ctx = null, master = null, send = null, enabled = false;
  const last = {};
  enabled = true;   // on by default; the browser lets it start at the first click or key press
  try { if (localStorage.getItem(KEY) === "off") enabled = false; } catch (e) {}
  const live = () => enabled && !matchMedia("(max-width: 900px)").matches && !!(window.AudioContext || window.webkitAudioContext);
  const spaced = (k, ms) => { const t = performance.now(); if (last[k] && t - last[k] < ms) return false; last[k] = t; return true; };

  function context() {
    if (ctx) return ctx;
    const AC = window.AudioContext || window.webkitAudioContext;
    ctx = new AC();
    const comp = ctx.createDynamicsCompressor();
    master = ctx.createGain(); master.gain.value = 0.55; master.connect(comp); comp.connect(ctx.destination);
    // a feedback echo that gives every sound a hall-like tail
    send = ctx.createGain();
    const d = ctx.createDelay(1), fb = ctx.createGain(), lp = ctx.createBiquadFilter();
    d.delayTime.value = 0.21; fb.gain.value = 0.38; lp.type = "lowpass"; lp.frequency.value = 2200;
    send.connect(d); d.connect(lp); lp.connect(fb); fb.connect(d); lp.connect(master);
    return ctx;
  }
  // gesture: true for sounds that answer a click or key press (allowed to wake the audio); false for the rest, which stay silent until it is awake
  function gate(gesture) {
    if (!live()) return null;
    if (!ctx && !gesture) return null;   // nothing is created until the first click or key press, so the browser never warns
    const c = context();
    if (c.state !== "running") { if (gesture) c.resume(); else return null; }
    return c;
  }
  function tone(c, { f, to, dur = 0.1, type = "sine", vol = 0.1, at = 0, echo = 0.35, attack = 0.004 }) {
    const t = c.currentTime + at, o = c.createOscillator(), g = c.createGain(), s = c.createGain();
    o.type = type; o.frequency.setValueAtTime(f, t); if (to) o.frequency.exponentialRampToValueAtTime(to, t + dur);
    g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(vol, t + attack); g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    s.gain.value = echo; o.connect(g); g.connect(master); g.connect(s); s.connect(send);
    o.start(t); o.stop(t + dur + 0.05);
  }
  function noise(c, { dur = 0.15, vol = 0.1, from = 3000, to = 600, q = 4, type = "bandpass", at = 0 }) {
    const t = c.currentTime + at, n = Math.max(1, Math.floor(c.sampleRate * dur)), buf = c.createBuffer(1, n, c.sampleRate), d = buf.getChannelData(0);
    for (let i = 0; i < n; i++) d[i] = Math.random() * 2 - 1;
    const src = c.createBufferSource(), f = c.createBiquadFilter(), g = c.createGain();
    src.buffer = buf; f.type = type; f.Q.value = q; f.frequency.setValueAtTime(from, t); f.frequency.exponentialRampToValueAtTime(to, t + dur);
    g.gain.setValueAtTime(vol, t); g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    src.connect(f); f.connect(g); g.connect(master); src.start(t);
  }
  // a low brass-like swell: stacked, slightly detuned saws through a filter that opens and closes
  function braam(c) {
    const t = c.currentTime, g = c.createGain(), f = c.createBiquadFilter(), s = c.createGain();
    f.type = "lowpass"; f.Q.value = 6; f.frequency.setValueAtTime(90, t); f.frequency.exponentialRampToValueAtTime(900, t + 0.9); f.frequency.exponentialRampToValueAtTime(140, t + 3);
    g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.22, t + 0.5); g.gain.exponentialRampToValueAtTime(0.0001, t + 3.2);
    [55, 55.6, 82.4, 110.3].forEach(fr => { const o = c.createOscillator(); o.type = "sawtooth"; o.frequency.value = fr; o.connect(f); o.start(t); o.stop(t + 3.3); });
    s.gain.value = 0.5; f.connect(g); g.connect(master); g.connect(s); s.connect(send);
  }
  // ---- the ambient loop under each terminal: every page has its own bed of sound ----
  let amb = null, ambId = 0;
  const noiseLoop = c => { const n = c.sampleRate * 2, buf = c.createBuffer(1, n, c.sampleRate), d = buf.getChannelData(0); for (let i = 0; i < n; i++) d[i] = Math.random() * 2 - 1; const s = c.createBufferSource(); s.buffer = buf; s.loop = true; return s; };
  // small building blocks for a scene: an oscillator, a filter, a gain, a slow wobble, and an event that repeats at random times
  function kit(c, bus, nodes, timers, id) {
    const osc = (type, f, dest, detune = 0) => { const o = c.createOscillator(); o.type = type; o.frequency.value = f; o.detune.value = detune; o.connect(dest); o.start(); nodes.push(o); return o; };
    const filt = (type, f, q, dest) => { const x = c.createBiquadFilter(); x.type = type; x.frequency.value = f; x.Q.value = q; x.connect(dest); return x; };
    const gain = (v, dest) => { const x = c.createGain(); x.gain.value = v; x.connect(dest); return x; };
    const wobble = (rate, depth, param) => { const o = c.createOscillator(), d = c.createGain(); o.frequency.value = rate; d.gain.value = depth; o.connect(d); d.connect(param); o.start(); nodes.push(o); };
    const hiss = dest => { const s = noiseLoop(c); s.connect(dest); s.start(); nodes.push(s); };
    const every = (min, max, fn) => { const tick = () => { if (amb && amb.id === id) { if (ctx && ctx.state === "running") fn(); timers.push(setTimeout(tick, (min + Math.random() * (max - min)) * 1000)); } }; timers.push(setTimeout(tick, (min + Math.random() * (max - min)) * 1000)); };
    return { osc, filt, gain, wobble, hiss, every, bus };
  }
  const pick = a => a[Math.floor(Math.random() * a.length)];
  const SCENES = {
    // Today, the radar: a low drone that breathes, a soft sonar ping now and then, and a slow sweep that comes round every sixteen seconds
    today(c, k) {
      const lp = k.filt("lowpass", 220, 3, k.gain(0.05, k.bus)); k.wobble(0.07, 90, lp.frequency);
      k.osc("sine", 41.2, lp); k.osc("sine", 41.5, lp); k.osc("sawtooth", 82.4, lp);
      k.every(6, 9, () => tone(c, { f: pick([740, 880, 988]), to: 700, dur: 1.5, vol: 0.022, echo: 0.75 }));
      k.every(15.5, 16.5, () => noise(c, { dur: 2.6, vol: 0.018, from: 300, to: 2200, q: 2 }));
    },
    // Browse, the monitor: the hum of mains power, a film transport whirring, and chirps of data
    browse(c, k) {
      const hum = k.gain(0.03, k.bus); k.osc("sine", 60, hum); k.osc("sine", 120, k.gain(0.5, hum)); k.osc("sine", 180, k.gain(0.2, hum));
      k.osc("sawtooth", 60, k.filt("lowpass", 300, 1, k.gain(0.012, k.bus)));
      const whirr = k.gain(0.0, k.bus); const bp = k.filt("bandpass", 1100, 4, whirr); k.hiss(bp); k.wobble(7, 0.006, whirr.gain); whirr.gain.value = 0.008;
      k.every(1.8, 4.5, () => { const n = 2 + Math.floor(Math.random() * 3); for (let i = 0; i < n; i++) tone(c, { f: 1500 + Math.random() * 1700, dur: 0.035, type: "square", vol: 0.012, at: i * 0.05, echo: 0.2 }); });
    },
    // Market, the biometrics lab: a soft three-note pad, a sequencer picking out notes, and a slow heartbeat
    market(c, k) {
      const lp = k.filt("lowpass", 900, 1, k.gain(0.035, k.bus)); const trem = k.gain(1, lp);
      [110, 164.81, 246.94].forEach((f, i) => k.osc("sine", f, trem, i * 4));
      k.wobble(0.2, 0.35, trem.gain);
      k.every(0.9, 2.2, () => tone(c, { f: pick([880, 987.8, 1174.7, 1318.5, 1568]), dur: 0.2, vol: 0.018, echo: 0.55 }));
      k.every(2.5, 2.7, () => { tone(c, { f: 62, to: 44, dur: 0.22, vol: 0.05, echo: 0.1 }); tone(c, { f: 58, to: 42, dur: 0.2, vol: 0.035, at: 0.27, echo: 0.1 }); });
    },
    // Globe, the point cloud: a deep rumble, wind across it, and far-off pings that fall in pitch
    globe(c, k) {
      const rum = k.filt("lowpass", 160, 2, k.gain(0.06, k.bus)); k.osc("sine", 32.7, rum); k.osc("sine", 33.1, rum); k.osc("triangle", 65.4, rum);
      const wind = k.gain(0.03, k.bus); const lp = k.filt("lowpass", 500, 1, wind); k.hiss(lp); k.wobble(0.06, 250, lp.frequency);
      k.every(8, 14, () => { const f = 420 + Math.random() * 480; tone(c, { f, to: f * 0.8, dur: 1.8, vol: 0.03, echo: 0.8 }); });
    },
  };
  function startDrone(c) {
    if (amb) return;
    const t = c.currentTime, g = c.createGain(), nodes = [], timers = [], id = ++ambId;
    g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(1, t + 4); g.connect(master);
    amb = { g, nodes, timers, id };
    (SCENES[document.documentElement.dataset.theme] || SCENES.today)(c, kit(c, g, nodes, timers, id));
  }
  function stopDrone() {
    if (!amb || !ctx) return;
    const { g, nodes, timers } = amb, t = ctx.currentTime;
    timers.forEach(clearTimeout); amb = null;
    g.gain.cancelScheduledValues(t); g.gain.setValueAtTime(Math.max(g.gain.value, 0.0001), t); g.gain.exponentialRampToValueAtTime(0.0001, t + 0.6);
    nodes.forEach(o => { try { o.stop(t + 0.7); } catch (e) {} });
  }
  // the ambient loop stops while the tab is hidden and comes back when it is shown again
  document.addEventListener("visibilitychange", () => {
    if (!ctx || !live()) return;
    if (document.hidden) { if (ctx.state === "running") ctx.suspend(); } else if (ctx.state === "suspended") ctx.resume();
  });
  const play = (gesture, ms, key, fn) => { const c = gate(gesture); if (c && spaced(key, ms)) fn(c); };

  return {
    get on() { return enabled; },
    // the SND switch: turning it on plays the brass swell and starts the drone
    set(on) {
      enabled = on;
      try { localStorage.setItem(KEY, on ? "on" : "off"); } catch (e) {}
      if (on) { const c = gate(true); if (c) { braam(c); startDrone(c); } } else stopDrone();
    },
    // called at the first click or key press on a page: if sound was left on, bring the drone back
    wake() { if (enabled && !amb) { const c = gate(true); if (c) startDrone(c); } },
    blip: (f = 1250) => play(true, 40, "blip", c => { tone(c, { f, to: f * 1.18, dur: 0.09, vol: 0.09 }); tone(c, { f: f / 2, dur: 0.06, vol: 0.03, echo: 0.1 }); }),
    tick: () => play(false, 45, "tick", c => tone(c, { f: 2600, to: 2000, dur: 0.022, type: "triangle", vol: 0.03, echo: 0.1 })),
    chime: () => play(true, 150, "chime", c => { tone(c, { f: 784, dur: 0.55, vol: 0.08, echo: 0.5 }); tone(c, { f: 1175, dur: 0.65, vol: 0.06, at: 0.07, echo: 0.55 }); }),
    low: () => play(true, 150, "low", c => tone(c, { f: 330, to: 220, dur: 0.16, vol: 0.08 })),
    glitch: () => play(false, 700, "glitch", c => { noise(c, { dur: 0.14, vol: 0.12, from: 4200, to: 500, q: 6 }); tone(c, { f: 62, to: 40, dur: 0.1, type: "square", vol: 0.1, echo: 0.1 }); }),
    // the monitor switching on: a relay thunk, a low thump, the tube's whine rising, and the brass swell
    poweron: () => play(true, 600, "poweron", c => {
      noise(c, { dur: 0.1, vol: 0.18, from: 900, to: 90, q: 1, type: "lowpass" });
      tone(c, { f: 52, to: 34, dur: 0.35, vol: 0.2, echo: 0.1 });
      tone(c, { f: 700, to: 2600, dur: 0.55, vol: 0.035, at: 0.05, echo: 0.3 });
      tone(c, { f: 2600, to: 1800, dur: 0.5, vol: 0.02, at: 0.6, echo: 0.3 });
      braam(c);
    }),
    powerdown: () => play(true, 300, "pd", c => { noise(c, { dur: 0.24, vol: 0.15, from: 5000, to: 80, q: 1, type: "lowpass" }); tone(c, { f: 260, to: 38, dur: 0.24, vol: 0.16, echo: 0.2 }); }),
    scan: () => play(true, 300, "scan", c => tone(c, { f: 260, to: 1900, dur: 0.4, vol: 0.06, echo: 0.5 })),
    ping: (f = 520, strong = false) => play(strong, 120, "ping", c => { tone(c, { f, dur: 1.1, vol: strong ? 0.11 : 0.06, echo: 0.7 }); tone(c, { f: f * 2.01, dur: 0.5, vol: strong ? 0.04 : 0.02, echo: 0.6 }); }),
    decode: () => play(false, 500, "decode", c => { for (let i = 0; i < 6; i++) tone(c, { f: 900 + i * 180, dur: 0.05, type: "triangle", vol: 0.04, at: i * 0.055, echo: 0.2 }); }),
  };
})();
