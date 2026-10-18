/*
  characters.js  -  Doraemon, drawn entirely in code (flat-colour SVG, no images, no voice).

  FRONT VIEW: everything is symmetrical about the centre line x = 130, nothing is tilted.
  Drawn on a 260 x 262 grid from two references (front-view character sheet + waving pose with hand in pocket).

  Animation (all done by CharAnim below with plain SVG attributes, identical in every browser):
    * body stays STILL
    * his right arm (viewer's right) moves: rest -> into the pocket (digging) -> held up with the gadget
    * eyes blink
    * mouth changes: smile (idle) / smile + tongue (digging) / big grin (presenting)
*/
(function () {
  const INK = "#18161c", SW = 1.6;
  const BLUE = "#08a4f7", WHITE = "#ffffff", GREY = "#d5dbe8";
  const RED = "#e0223a", NOSE = "#e01b36";
  const CX = 130;                                   // centre line

  const shape = (d, fill, extra = "") =>
    `<path d="${d}" fill="${fill}" stroke="${INK}" stroke-width="${SW}" stroke-linejoin="round" stroke-linecap="round" ${extra}/>`;
  const plain = (d, fill) => `<path d="${d}" fill="${fill}"/>`;
  const ell = (cx, cy, rx, ry, fill, extra = "") =>
    `<ellipse cx="${cx}" cy="${cy}" rx="${rx}" ry="${ry}" fill="${fill}" stroke="${INK}" stroke-width="${SW}" ${extra}/>`;
  const dot = (cx, cy, rx, ry, fill) => `<ellipse cx="${cx}" cy="${cy}" rx="${rx}" ry="${ry}" fill="${fill}"/>`;
  const line = (d, w = SW) =>
    `<path d="${d}" fill="none" stroke="${INK}" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round"/>`;
  const limb = (d, w, fill) =>
    `<path d="${d}" fill="none" stroke="${INK}" stroke-width="${w + SW * 2}" stroke-linecap="round" stroke-linejoin="round"/>` +
    `<path d="${d}" fill="none" stroke="${fill}" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round"/>`;
  /* mirror a point list about the centre line */
  const mx = x => 2 * CX - x;

  /* round white glove-hand with a soft shadow underneath */
  const hand = (cx, cy, r) =>
    ell(cx, cy, r, r, WHITE) +
    plain(`M${cx - r * 0.85} ${cy + r * 0.45} Q${cx} ${cy + r * 1.15} ${cx + r * 0.85} ${cy + r * 0.45} Q${cx} ${cy + r * 0.95} ${cx - r * 0.85} ${cy + r * 0.45}Z`, GREY);

  /* ---- arm geometry (viewBox units) ---- */
  const SHOULDER = { x: 184, y: 155 };
  const REST     = { x: 198, y: 195 };   // hanging at his side, like the front-view sheet
  const POCKET   = { x: 160, y: 183 };   // hand dipping into the pocket
  const PRESENT  = { x: 235, y: 143 };   // hand held out to his right, holding the gadget
  const ARM_W = 15, HAND_R = 14;

  /* sleeve = curved tube from the shoulder to just short of the hand */
  function armPath(H) {
    const dx = H.x - SHOULDER.x, dy = H.y - SHOULDER.y, len = Math.hypot(dx, dy) || 1;
    const ux = dx / len, uy = dy / len;
    let nx = -uy, ny = ux;
    if (Math.abs(uy) > Math.abs(ux)) { if (nx < 0) { nx = -nx; ny = -ny; } }   // hanging down: bulge outward (right)
    else if (ny > 0) { nx = -nx; ny = -ny; }                                     // reaching sideways: bulge upward
    const ex = H.x - ux * 7, ey = H.y - uy * 7;
    const cx = (SHOULDER.x + ex) / 2 + nx * 5, cy = (SHOULDER.y + ey) / 2 + ny * 5;
    return `M${SHOULDER.x} ${SHOULDER.y} Q${cx.toFixed(1)} ${cy.toFixed(1)} ${ex.toFixed(1)} ${ey.toFixed(1)}`;
  }

  /* whiskers (left side measured from the reference, right side is the mirror image) */
  const WL = [[69, 75, 105, 85], [67, 91, 105, 93], [69, 110, 105, 102]];
  const whiskers = WL.map(([a, b, c, d]) => line(`M${a} ${b} L${c} ${d}`, 1.5) + line(`M${mx(a)} ${b} L${mx(c)} ${d}`, 1.5)).join("");

  const svg = `
    <defs>
      <!-- while digging, only the part of the hand above the pocket's rim shows (the rest is "inside") -->
      <clipPath id="pocketClip"><rect x="0" y="0" width="300" height="177.5"/></clipPath>
    </defs>

    <!-- feet -->
    ${ell(100, 238, 32, 13.5, WHITE)}
    ${ell(162, 238, 33, 13, WHITE)}

    <!-- raised waving arm (still), drawn under the body so it blends into the shoulder -->
    ${limb("M80 158 L47 123", ARM_W, BLUE)}
    ${hand(33, 109, 18)}

    <!-- body -->
    ${plain("M77 146 L83 226 Q130 235 183 226 L187 144 Z", BLUE)}
    ${line("M77 172 L83 226")}${line("M187 150 L183 226")}
    ${line("M120 219.5 L141 219.5", 1.4)}

    <!-- tummy + pocket (centred) -->
    ${ell(129, 184, 44, 33, WHITE)}
    ${shape("M92 176 Q130 180 168 177 C170 200 154 210 130 210 C106 210 90 198 92 176Z", WHITE, `stroke-width="1.5"`)}

    <!-- head: symmetrical dome, big white face -->
    ${shape("M51 72 C49 30 84 3 130 3 C176 3 211 30 209 72 C208 106 178 138 130 138 C82 138 52 106 51 72Z", BLUE)}
    ${shape("M62 100 C60 78 74 62 96 57 L164 57 C186 62 200 78 198 100 C196 128 166 142 130 142 C94 142 64 128 62 100Z", WHITE)}

    <!-- eyes (touching on the centre line) -->
    <g class="eyes">
      ${ell(112.5, 49, 17.5, 21, WHITE, `stroke-width="1.5"`)}
      ${ell(147.5, 49, 17.5, 21, WHITE, `stroke-width="1.5"`)}
      ${dot(119.5, 60, 4.6, 5.8, INK)}${dot(118.4, 58.2, 1.6, 1.8, WHITE)}
      ${dot(140.5, 60, 4.6, 5.8, INK)}${dot(139.4, 58.2, 1.6, 1.8, WHITE)}
    </g>

    <!-- nose + line to the mouth -->
    ${ell(130, 77, 11.5, 11.5, NOSE)}
    ${dot(126.5, 73.5, 3, 2.8, "#ffffff")}
    ${line("M130 89 L130 125", 1.6)}

    <!-- whiskers -->
    ${whiskers}

    <!-- mouth: three expressions, CharAnim shows one at a time -->
    <g class="m-smile">
      ${line("M70 99 C86 124 108 131 130 131 C152 131 174 124 190 99", 1.8)}
      ${line("M70 99 Q64 96 67 90", 1.6)}${line("M190 99 Q196 96 193 90", 1.6)}
    </g>
    <g class="m-tongue" style="display:none">
      ${shape("M164 112 C158 106 162 96 172 95 C182 94 188 101 184 109 C181 116 170 118 164 112Z", "#e8373f", `stroke-width="1.5"`)}
      ${line("M173 100 Q175 107 172 112", 1.3)}
    </g>
    <g class="m-open" style="display:none">
      ${shape("M70 99 Q130 112 190 99 C186 128 160 143 130 143 C100 143 74 128 70 99Z", "#e94a1c")}
      ${shape("M96 130 C104 119 116 116 130 116 C144 116 156 119 164 130 C156 139 144 143 130 143 C116 143 104 139 96 130Z", "#f39a64", `stroke-width="0"`)}
      ${line("M96 130 C104 119 116 116 130 116 C144 116 156 119 164 130", 1.5)}
      ${line("M70 99 Q130 112 190 99", 1.8)}
      ${line("M70 99 Q64 96 67 90", 1.6)}${line("M190 99 Q196 96 193 90", 1.6)}
    </g>

    <!-- red collar + golden bell, centred -->
    ${shape("M76 131 Q131 146 187 131 L188 141 Q131 158 75 141Z", RED, `stroke-width="1.4"`)}
    ${ell(130, 158, 14.5, 14.5, "#f1b134", `stroke-width="1.5"`)}
    ${shape("M116 152.5 Q130 148 144 152.5", "none", `stroke-width="1.4"`)}
    ${dot(130, 161, 3, 3, INK)}${line("M130 163 L130 172", 1.4)}

    <!-- the arm that digs in the pocket / presents the gadget (redrawn every frame by CharAnim) -->
    <g class="act-arm">
      <path class="arm-edge" d="${armPath(REST)}" fill="none" stroke="${INK}" stroke-width="${ARM_W + SW * 2}" stroke-linecap="round" stroke-linejoin="round"/>
      <path class="arm-fill" d="${armPath(REST)}" fill="none" stroke="${BLUE}" stroke-width="${ARM_W}" stroke-linecap="round" stroke-linejoin="round"/>
      <g class="hand-clip"><g class="hand" transform="translate(0 0)">${hand(REST.x, REST.y, HAND_R)}</g></g>
    </g>
  `;

  const CHAR_ART = { pip: { vb: [260, 262], head: "40 0 180 150", pocket: [50, 74], svg } };

  /* Full-body figure for the stage (animated). */
  window.charFigure = function (id, label) {
    const c = CHAR_ART[id] || CHAR_ART.pip;
    return `<svg class="figure" viewBox="0 0 ${c.vb[0]} ${c.vb[1]}" role="img" aria-label="${label || "Doraemon"}">${c.svg}</svg>`;
  };
  window.charAvatar = function (id) {
    const c = CHAR_ART[id] || CHAR_ART.pip;
    return `<svg class="face-crop" viewBox="${c.head}" aria-hidden="true">${c.svg}</svg>`;
  };

  /* ---- CharAnim: spring-driven arm, blinking and expressions ---- */
  const CharAnim = (function () {
    let root = null, edge, fill, handG, clipG, eyesG, mSmile, mTongue, mOpen, raf = 0, last = 0, state = "idle", blinkTimer = 0;
    const pos = { x: REST.x, y: REST.y }, vel = { x: 0, y: 0 };
    const reduce = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;

    function draw() {
      const d = armPath(pos);
      edge.setAttribute("d", d); fill.setAttribute("d", d);
      handG.setAttribute("transform", `translate(${(pos.x - REST.x).toFixed(1)} ${(pos.y - REST.y).toFixed(1)})`);
    }
    function face() {
      if (!mSmile) return;
      mSmile.style.display = state === "present" ? "none" : "";
      mTongue.style.display = state === "rummage" ? "" : "none";
      mOpen.style.display = state === "present" ? "" : "none";
      if (clipG) { if (state === "rummage") clipG.setAttribute("clip-path", "url(#pocketClip)"); else clipG.removeAttribute("clip-path"); }
    }
    function targetFor(t) {
      if (state === "rummage") return reduce ? POCKET : { x: POCKET.x + Math.cos(t * 11) * 6, y: POCKET.y + Math.sin(t * 17) * 3.5 };
      if (state === "present") return reduce ? PRESENT : { x: PRESENT.x, y: PRESENT.y + Math.sin(t * 3.2) * 1.6 };
      return REST;
    }
    function step(now) {
      const dt = Math.min(0.033, (now - last) / 1000 || 0.016); last = now;
      const tg = targetFor(now / 1000);
      const k = reduce ? 900 : 300, c = reduce ? 60 : 21;
      vel.x += (tg.x - pos.x) * k * dt; vel.y += (tg.y - pos.y) * k * dt;
      const damp = Math.exp(-c * dt); vel.x *= damp; vel.y *= damp;
      pos.x += vel.x * dt; pos.y += vel.y * dt;
      draw();
      const settled = state === "idle" && Math.hypot(pos.x - REST.x, pos.y - REST.y) < 0.05 && Math.hypot(vel.x, vel.y) < 0.05;
      if (settled) { pos.x = REST.x; pos.y = REST.y; draw(); raf = 0; return; }
      raf = requestAnimationFrame(step);
    }
    function kick() { if (!raf && root) { last = performance.now(); raf = requestAnimationFrame(step); } }
    function blink() {
      if (!root || !eyesG) return;
      const cy = 49;
      const set = s => eyesG.setAttribute("transform", s === 1 ? "" : `translate(${CX} ${cy}) scale(1 ${s}) translate(${-CX} ${-cy})`);
      set(0.1); setTimeout(() => set(1), 130);
      blinkTimer = setTimeout(blink, 2500 + Math.random() * 3000);
    }
    return {
      attach(svgEl) {
        clearTimeout(blinkTimer); cancelAnimationFrame(raf); raf = 0;
        root = svgEl; if (!root) return;
        edge = root.querySelector(".arm-edge"); fill = root.querySelector(".arm-fill");
        handG = root.querySelector(".hand"); clipG = root.querySelector(".hand-clip"); eyesG = root.querySelector(".eyes");
        mSmile = root.querySelector(".m-smile"); mTongue = root.querySelector(".m-tongue"); mOpen = root.querySelector(".m-open");
        pos.x = REST.x; pos.y = REST.y; vel.x = vel.y = 0; state = "idle"; face();
        if (!reduce) blinkTimer = setTimeout(blink, 1500);
      },
      sync(el) {
        const s = el.classList.contains("present") ? "present" : el.classList.contains("rummage") ? "rummage" : "idle";
        if (s !== state) { state = s; face(); kick(); }
      },
      gadgetSpot: () => ({ x: (PRESENT.x / 260 * 100).toFixed(1) + "%", y: ((PRESENT.y - 30) / 262 * 100).toFixed(1) + "%" }),
    };
  })();
  window.CharAnim = CharAnim;
  window.CHAR_ART = CHAR_ART;
})();
