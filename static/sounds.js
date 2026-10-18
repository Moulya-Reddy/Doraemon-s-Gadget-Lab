/*
  sounds.js  -  cartoon sound effects, synthesized live with the Web Audio API.
  No audio files, no libraries, no voice. Every effect is an original sound made from oscillators and noise.

  Want the "real" sounds? Drop files named  rustle  pull  gadget  bell  pop  blip  correct  wrong
  (.mp3 / .wav / .ogg) into  static/sounds/  and they replace the synthesized version automatically.

  Each effect is  fn(ctx, out, t)  so it can also be rendered offline for testing.
*/
(function () {
  /* ---------- tiny synth toolbox ---------- */
  const noiseCache = new WeakMap();
  function noise(ctx) {
    if (!noiseCache.has(ctx)) {
      const len = ctx.sampleRate * 1, buf = ctx.createBuffer(1, len, ctx.sampleRate), d = buf.getChannelData(0);
      for (let i = 0; i < len; i++) d[i] = Math.random() * 2 - 1;
      noiseCache.set(ctx, buf);
    }
    return noiseCache.get(ctx);
  }
  /* oscillator with a pitch glide and a fast-attack / exponential-release envelope */
  function tone(ctx, out, t, { f0, f1 = f0, dur = 0.2, type = "sine", gain = 0.3, attack = 0.008, detune = 0 }) {
    const o = ctx.createOscillator(), g = ctx.createGain();
    o.type = type; o.detune.value = detune;
    o.frequency.setValueAtTime(f0, t);
    if (f1 !== f0) o.frequency.exponentialRampToValueAtTime(f1, t + dur);
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(gain, t + attack);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    o.connect(g); g.connect(out); o.start(t); o.stop(t + dur + 0.02);
  }
  /* filtered noise burst, optional filter sweep */
  function hiss(ctx, out, t, { f0 = 2000, f1 = f0, q = 1, dur = 0.1, gain = 0.2, type = "bandpass", attack = 0.01 }) {
    const s = ctx.createBufferSource(), f = ctx.createBiquadFilter(), g = ctx.createGain();
    s.buffer = noise(ctx); f.type = type; f.Q.value = q;
    f.frequency.setValueAtTime(f0, t);
    if (f1 !== f0) f.frequency.exponentialRampToValueAtTime(f1, t + dur);
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(gain, t + attack);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    s.connect(f); f.connect(g); g.connect(out); s.start(t, Math.random() * 0.5); s.stop(t + dur + 0.02);
  }
  const PENTA = [523.25, 587.33, 659.25, 783.99, 880, 1046.5];   // C major pentatonic (always sounds happy)

  /* ---------- the effects ---------- */
  const FX = {
    /* one rustle while he rummages in the pocket: paper-bag scrape + a soft thud */
    rustle(ctx, out, t) {
      hiss(ctx, out, t, { f0: 1800 + Math.random() * 1800, f1: 3500 + Math.random() * 2500, q: 0.8, dur: 0.09, gain: 0.16 });
      hiss(ctx, out, t + 0.05, { f0: 900, f1: 600, q: 0.7, dur: 0.07, gain: 0.08 });
      if (Math.random() < 0.55) tone(ctx, out, t, { f0: 150, f1: 70, dur: 0.07, gain: 0.18 });
    },
    /* "searching" bloop: a wobbly little rising blip */
    search(ctx, out, t) {
      const f = PENTA[Math.floor(Math.random() * 4)] / 2;
      tone(ctx, out, t, { f0: f * 0.8, f1: f * 1.5, dur: 0.11, gain: 0.1, type: "triangle" });
    },
    /* gadget leaves the pocket: whoosh up, then "pop" */
    pull(ctx, out, t) {
      hiss(ctx, out, t, { f0: 300, f1: 4200, q: 1.4, dur: 0.34, gain: 0.3, attack: 0.12 });
      tone(ctx, out, t, { f0: 220, f1: 1100, dur: 0.3, gain: 0.12, type: "triangle", attack: 0.1 });
      // pop
      tone(ctx, out, t + 0.33, { f0: 1000, f1: 160, dur: 0.07, gain: 0.35 });
      hiss(ctx, out, t + 0.33, { f0: 3000, q: 0.6, dur: 0.03, gain: 0.25, type: "highpass", attack: 0.002 });
    },
    /* original "ta-da" gadget fanfare: quick rising run, held top note, sparkle */
    gadget(ctx, out, t) {
      const run = [392, 523.25, 659.25, 783.99];                                  // G4 C5 E5 G5
      run.forEach((f, i) => {
        const at = t + i * 0.085;
        tone(ctx, out, at, { f0: f, dur: 0.14, gain: 0.16, type: "square" });      // toy-trumpet body
        tone(ctx, out, at, { f0: f * 2, dur: 0.14, gain: 0.07, type: "triangle" });
      });
      const top = t + run.length * 0.085 + 0.02;                                   // held high C
      [1046.5, 1318.5, 1568].forEach((f, i) => {                                   // C6 + E6 + G6 chord
        tone(ctx, out, top, { f0: f, dur: 0.75, gain: 0.13 - i * 0.025, type: "square", detune: i * 4 });
        tone(ctx, out, top, { f0: f * 2.01, dur: 0.5, gain: 0.05, type: "sine" });
      });
      for (let i = 0; i < 7; i++)                                                  // sparkle
        tone(ctx, out, top + 0.05 + i * 0.07, { f0: 2093 + Math.random() * 2400, dur: 0.12, gain: 0.07, attack: 0.003 });
    },
    /* Doraemon's golden bell: ding-ling-ling */
    bell(ctx, out, t) {
      [0, 0.12, 0.25].forEach((dt, i) => {
        const g = 0.2 - i * 0.04;
        tone(ctx, out, t + dt, { f0: 1568, dur: 0.7, gain: g });
        tone(ctx, out, t + dt, { f0: 2093, dur: 0.55, gain: g * 0.7 });
        tone(ctx, out, t + dt, { f0: 4186 * 1.005, dur: 0.3, gain: g * 0.35 });
        hiss(ctx, out, t + dt, { f0: 7000, q: 0.5, dur: 0.02, gain: 0.08, type: "highpass", attack: 0.002 });
      });
    },
    /* answer card opens */
    pop(ctx, out, t) {
      tone(ctx, out, t, { f0: 500, f1: 1400, dur: 0.09, gain: 0.2 });
      tone(ctx, out, t + 0.09, { f0: 1400, f1: 900, dur: 0.1, gain: 0.12, type: "triangle" });
    },
    /* button tap */
    blip(ctx, out, t) { tone(ctx, out, t, { f0: 880, f1: 1320, dur: 0.06, gain: 0.14, type: "triangle", attack: 0.004 }); },
    /* quiz right: two happy notes */
    correct(ctx, out, t) {
      tone(ctx, out, t, { f0: 784, dur: 0.14, gain: 0.2, type: "triangle" });
      tone(ctx, out, t + 0.11, { f0: 1175, dur: 0.35, gain: 0.2, type: "triangle" });
      tone(ctx, out, t + 0.11, { f0: 2350, dur: 0.25, gain: 0.06 });
    },
    /* quiz wrong / error: cartoon "bonk" + sliding-down wobble */
    wrong(ctx, out, t) {
      tone(ctx, out, t, { f0: 300, f1: 90, dur: 0.12, gain: 0.3 });
      tone(ctx, out, t + 0.12, { f0: 392, f1: 196, dur: 0.38, gain: 0.14, type: "sawtooth" });
    },
  };

  /* ---------- player ---------- */
  const KEY = "dm_sound";
  let ctx = null, master = null, overrides = {}, rumTimer = 0, rumN = 0;
  let enabled = true;
  try { enabled = localStorage.getItem(KEY) !== "off"; } catch (_) {}

  function ensure() {
    if (!enabled) return null;
    if (!ctx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return null;
      ctx = new AC();
      master = ctx.createGain(); master.gain.value = 1.0;
      const comp = ctx.createDynamicsCompressor();             // keeps overlapping effects from clipping
      master.connect(comp); comp.connect(ctx.destination);
    }
    if (ctx.state === "suspended") ctx.resume();
    return ctx;
  }

  function playFile(name) {
    const c = ensure(); if (!c || !overrides[name]) return false;
    const s = c.createBufferSource(); s.buffer = overrides[name]; s.connect(master); s.start();
    return true;
  }

  const Sound = {
    FX,
    get enabled() { return enabled; },
    play(name) {
      try {
        if (playFile(name)) return;
        const c = ensure(); if (!c || !FX[name]) return;
        FX[name](c, master, c.currentTime + 0.01);
      } catch (_) {}
    },
    startRummage() {
      this.stopRummage();
      const c = ensure(); if (!c) return;
      rumN = 0;
      const tick = () => {
        rumN++;
        if (!playFile("rustle")) {
          FX.rustle(c, master, c.currentTime + 0.01);
          if (rumN % 3 === 0) FX.search(c, master, c.currentTime + 0.08);
        }
      };
      tick(); rumTimer = setInterval(tick, 190);
    },
    stopRummage() { clearInterval(rumTimer); rumTimer = 0; },
    setEnabled(on) {
      enabled = !!on;
      try { localStorage.setItem(KEY, enabled ? "on" : "off"); } catch (_) {}
      if (!enabled) this.stopRummage();
    },
    /* optional real recordings from static/sounds/ */
    async loadOverrides() {
      try {
        const list = await (await fetch("/api/sounds")).json();
        const AC = window.AudioContext || window.webkitAudioContext; if (!AC || !list.length) return;
        const tmp = new AC();
        for (const file of list) {
          const name = file.replace(/\.[^.]+$/, "");
          if (!FX[name] && name !== "rustle") continue;
          try { overrides[name] = await tmp.decodeAudioData(await (await fetch("/static/sounds/" + file)).arrayBuffer()); } catch (_) {}
        }
        tmp.close && tmp.close();
      } catch (_) {}
    },
  };
  window.Sound = Sound;
})();
