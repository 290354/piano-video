/* Nocturne — every frame drawn by code.
   Scene is a pure function of time: drawFrame(t). */
(() => {
  const W = 1920, H = 1080;
  const cvs = document.getElementById('c');
  const ctx = cvs.getContext('2d', { alpha: false });
  const DATA = window.NOTES;
  const NOTES = DATA.notes;
  const BEAT = DATA.beat;
  const CFG = window.CONFIG || {};
  const PX = CFG.pixelRatio || 1;
  if (PX !== 1) { cvs.width = W * PX; cvs.height = H * PX; }
  const DUR = CFG.dur || 74.0;
  const TITLE = CFG.title || '夜  曲';
  const TITLE_EN = CFG.titleEn || 'NOCTURNE';
  const SUBTITLE = CFG.subtitle || 'A  MINOR   ·   72  BPM   ·   SOLO  PIANO';
  const END_WORD = CFG.endWord || '曲 终';
  // where the coda starts: leave the last notes room to land before the card
  const LAST_ON = NOTES.reduce((m, n) => Math.max(m, n.t), 0);
  const END_START = Math.min(Math.max(DUR - 8.6, LAST_ON + 1.0), DUR - 4.4);
  const CREDIT1 = CFG.credit1 || '画面由代码逐帧绘制';
  const CREDIT2 = CFG.credit2 || '钢琴采样 · Salamander Grand Piano';

  // ---------------------------------------------------------------- layout
  const LOW = CFG.low || 40, HIGH = CFG.high || 84;   // E2 .. C6
  const KX0 = 112, KX1 = 1808;
  const KEY_Y = 790;                    // top edge of the white keys
  const WHITE_H = 178;
  const BLACK_H = 104;
  const FALL = 5.2;                    // seconds a note takes to reach the keys
  const TOP = -70;

  const BLACK_PC = new Set([1, 3, 6, 8, 10]);
  const isBlack = m => BLACK_PC.has(((m % 12) + 12) % 12);

  const whites = [];
  for (let m = LOW; m <= HIGH; m++) if (!isBlack(m)) whites.push(m);
  const KW = (KX1 - KX0) / whites.length;
  const BW = KW * 0.50;

  const KEY = {};                        // midi -> {x, w, black, wi}
  let wi = 0;
  for (let m = LOW; m <= HIGH; m++) {
    if (!isBlack(m)) {
      KEY[m] = { x: KX0 + wi * KW, w: KW, black: false, wi };
      wi++;
    } else {
      KEY[m] = { x: KX0 + wi * KW - BW / 2, w: BW, black: true, wi: wi - 1 };
    }
  }
  const noteX = m => {
    const k = KEY[m];
    if (!k) return null;
    return k.black ? k.x + k.w / 2 : k.x + k.w / 2;
  };
  const noteW = m => {
    const k = KEY[m];
    return k ? (k.black ? k.w * 0.92 : k.w * 0.74) : 0;
  };

  const COL = Object.assign({
    melody:  { a: '244,176,96', b: '255,224,182' },
    sparkle: { a: '255,216,166', b: '255,244,226' },
    harmony: { a: '126,196,184', b: '196,236,226' },
    bass:    { a: '118,132,206', b: '186,196,246' },
  }, CFG.col || {});

  // ---------------------------------------------------------------- static layers
  const bg = ctx.createLinearGradient(0, 0, 0, H);
  bg.addColorStop(0, '#07080d');
  bg.addColorStop(0.42, '#0d0e15');
  bg.addColorStop(0.74, '#151016');
  bg.addColorStop(1, '#08070a');

  // film grain tile
  const grain = document.createElement('canvas');
  grain.width = 220; grain.height = 140;
  {
    const g = grain.getContext('2d');
    const img = g.createImageData(grain.width, grain.height);
    let s = 1234567;
    const rnd = () => (s = (s * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff;
    for (let i = 0; i < img.data.length; i += 4) {
      const v = 110 + rnd() * 120;
      img.data[i] = img.data[i + 1] = img.data[i + 2] = v;
      img.data[i + 3] = 255;
    }
    g.putImageData(img, 0, 0);
  }
  const grainPattern = ctx.createPattern(grain, 'repeat');

  // dust motes
  const motes = (() => {
    let s = 987654321;
    const rnd = () => (s = (s * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff;
    return Array.from({ length: 110 }, () => ({
      x: rnd() * W,
      y: rnd() * H,
      r: 0.6 + rnd() * 1.8,
      sp: 6 + rnd() * 22,
      ph: rnd() * Math.PI * 2,
      a: 0.05 + rnd() * 0.18,
    }));
  })();

  // reflective stage under the keyboard
  const reflCanvas = document.createElement('canvas');
  reflCanvas.width = W; reflCanvas.height = WHITE_H;
  const rctx = reflCanvas.getContext('2d');
  function drawReflection() {
    const KH = WHITE_H;
    rctx.clearRect(0, 0, W, KH);
    rctx.drawImage(cvs, 0, KEY_Y, W, KH, 0, 0, W, KH);
    ctx.save();
    ctx.globalAlpha = 0.38;
    ctx.filter = 'blur(7px)';
    ctx.translate(0, KEY_Y + KH);
    ctx.scale(1, -0.62);
    ctx.drawImage(reflCanvas, 0, 0, W, KH, 0, 0, W, KH);
    ctx.restore();
    const f = ctx.createLinearGradient(0, KEY_Y + KH, 0, H);
    f.addColorStop(0, 'rgba(8,7,9,0.02)');
    f.addColorStop(0.55, 'rgba(8,7,9,0.55)');
    f.addColorStop(1, 'rgba(8,7,9,0.96)');
    ctx.fillStyle = f;
    ctx.fillRect(0, KEY_Y + KH, W, H - KEY_Y - KH);
  }

  // ---------------------------------------------------------------- helpers
  // a soft horizontal band behind typography: notes fade out under the words,
  // so the type stays readable without looking like a pasted-on box
  function textBand(yTop, yBot, k, peak) {
    if (k <= 0.001) return;
    const g = ctx.createLinearGradient(0, yTop, 0, yBot);
    g.addColorStop(0, 'rgba(5,5,7,0)');
    g.addColorStop(0.26, `rgba(5,5,7,${peak * k})`);
    g.addColorStop(0.74, `rgba(5,5,7,${peak * k})`);
    g.addColorStop(1, 'rgba(5,5,7,0)');
    ctx.fillStyle = g;
    ctx.fillRect(0, yTop, W, yBot - yTop);
  }

  function roundRect(x, y, w, h, r) {
    const rr = Math.min(r, w / 2, h / 2);
    ctx.beginPath();
    ctx.moveTo(x + rr, y);
    ctx.arcTo(x + w, y, x + w, y + h, rr);
    ctx.arcTo(x + w, y + h, x, y + h, rr);
    ctx.arcTo(x, y + h, x, y, rr);
    ctx.arcTo(x, y, x + w, y, rr);
    ctx.closePath();
  }

  function drawBackground(t) {
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, W, H);

    // slow stage haze
    const g1 = ctx.createRadialGradient(960 + 260 * Math.sin(t * 0.11), 470, 40, 960, 520, 980);
    g1.addColorStop(0, 'rgba(96,74,58,0.16)');
    g1.addColorStop(1, 'rgba(96,74,58,0)');
    ctx.fillStyle = g1;
    ctx.fillRect(0, 0, W, H);

    // key-light from below the keyboard
    const phase = (t % BEAT) / BEAT;
    const pulse = Math.exp(-phase * 3.6);
    const g2 = ctx.createRadialGradient(960, KEY_Y + 40, 30, 960, KEY_Y + 40, 760);
    g2.addColorStop(0, `rgba(255,176,92,${0.13 + 0.06 * pulse})`);
    g2.addColorStop(0.5, `rgba(255,150,70,${0.035 + 0.02 * pulse})`);
    g2.addColorStop(1, 'rgba(255,150,70,0)');
    ctx.fillStyle = g2;
    ctx.fillRect(0, 0, W, H);

    // a night light far behind the keys
    const mx = 1420 + 30 * Math.sin(t * 0.05), my = 232;
    const moon = ctx.createRadialGradient(mx, my, 20, mx, my, 460);
    moon.addColorStop(0, 'rgba(228,216,198,0.085)');
    moon.addColorStop(0.30, 'rgba(206,192,172,0.035)');
    moon.addColorStop(1, 'rgba(206,192,172,0)');
    ctx.fillStyle = moon;
    ctx.fillRect(mx - 460, my - 460, 920, 920);

    // out-of-focus bokeh
    const bok = [[330, 200, 90], [640, 330, 55], [1180, 150, 70], [1710, 420, 110], [880, 120, 45]];
    for (let i = 0; i < bok.length; i++) {
      const [bx, by, br] = bok[i];
      const a = 0.007 + 0.005 * Math.sin(t * 0.3 + i);
      const bg2 = ctx.createRadialGradient(bx, by, 0, bx, by, br);
      bg2.addColorStop(0, `rgba(255,208,158,${a})`);
      bg2.addColorStop(0.75, `rgba(255,208,158,${a * 0.5})`);
      bg2.addColorStop(1, 'rgba(255,208,158,0)');
      ctx.fillStyle = bg2;
      ctx.beginPath(); ctx.arc(bx, by, br, 0, Math.PI * 2); ctx.fill();
    }

    // five faint staff lines, only while the title is up
    const sa = Math.max(0, Math.min(ease((t - 0.6) / 1.4), 1 - ease((t - 4.8) / 1.4))) * 0.055;
    if (sa > 0.001) {
      ctx.strokeStyle = `rgba(226,204,176,${sa})`;
      ctx.lineWidth = 1;
      for (let i = 0; i < 5; i++) {
        const y = 214 + i * 27;
        ctx.beginPath(); ctx.moveTo(300, y); ctx.lineTo(W - 300, y); ctx.stroke();
      }
    }
  }

  function drawMotes(t) {
    ctx.save();
    for (const m of motes) {
      const y = ((m.y - t * m.sp) % (H + 80) + H + 80) % (H + 80) - 40;
      const x = m.x + Math.sin(t * 0.5 + m.ph) * 14;
      const a = m.a * (0.55 + 0.45 * Math.sin(t * 0.9 + m.ph));
      ctx.fillStyle = `rgba(255,214,164,${Math.max(0, a).toFixed(3)})`;
      ctx.beginPath();
      ctx.arc(x, y, m.r, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.restore();
  }

  function drawNotes(t) {
    const speed = (KEY_Y - TOP) / FALL;
    // notes ease in while the title is up, so nothing cuts through the type
    const intro = Math.min(1, Math.max(0, (t - 0.9) / 2.6));
    ctx.save();
    ctx.globalAlpha = intro;
    for (const n of NOTES) {
      if (t < n.t - FALL || t > n.t + 3.0) continue;
      if (n.p === 'bass') continue;
      const x = noteX(n.m);
      if (x == null) continue;
      const w = noteW(n.m);
      const yHit = KEY_Y - (n.t - t) * speed;
      const h = Math.max(13, Math.min(n.d, 1.55) * speed);
      const y = yHit - h;
      if (y > KEY_Y) continue;

      const held = Math.min(n.d, 0.78);
      const age = t - n.t;
      const tail = n.t > DUR - 8 ? 5.5 : 1.15;
      let fade = 1;
      if (age > held) fade = Math.max(0, 1 - (age - held) / tail);
      if (fade <= 0.01) continue;

      const c = COL[n.p] || COL.harmony;
      const alpha = (n.p === 'harmony' ? 0.52 + 0.3 * n.v : 0.68 + 0.3 * n.v) * fade;
      const topY = Math.max(y, TOP);
      const botY = Math.min(yHit, KEY_Y);
      if (botY - topY < 2) continue;

      // soft halo just above the strike line
      if (n.p !== 'bass') {
        const cy = Math.min(botY, KEY_Y) - 26;
        const halo = ctx.createRadialGradient(x, cy, 2, x, cy, w * 1.45);
        halo.addColorStop(0, `rgba(${c.b},${0.075 * fade})`);
        halo.addColorStop(1, `rgba(${c.b},0)`);
        ctx.fillStyle = halo;
        ctx.fillRect(x - w * 1.45, cy - w * 1.45, w * 2.9, w * 2.9);
      }

      const grad = ctx.createLinearGradient(0, topY, 0, botY);
      grad.addColorStop(0, `rgba(${c.a},${alpha * 0.20})`);
      grad.addColorStop(0.55, `rgba(${c.a},${alpha * 0.68})`);
      grad.addColorStop(1, `rgba(${c.b},${alpha})`);

      if (n.p === 'melody' || n.p === 'sparkle') {
        ctx.shadowColor = `rgba(${c.b},0.50)`;
        ctx.shadowBlur = 26;
      } else {
        ctx.shadowColor = `rgba(${c.a},0.22)`;
        ctx.shadowBlur = 12;
      }
      ctx.fillStyle = grad;
      roundRect(x - w / 2, topY, w, botY - topY, Math.min(7, w * 0.22));
      ctx.fill();
      ctx.shadowBlur = 0;

      // bright leading edge
      if (yHit > TOP && yHit < KEY_Y + 2) {
        ctx.fillStyle = `rgba(255,250,238,${(0.45 + 0.4 * n.v) * fade})`;
        roundRect(x - w / 2, Math.min(yHit - 3.5, KEY_Y - 3.5), w, 3.5, 2);
        ctx.fill();
      }
      // faint trail rising off the top edge
      const trail = ctx.createLinearGradient(0, topY - 62, 0, topY);
      trail.addColorStop(0, `rgba(${c.a},0)`);
      trail.addColorStop(1, `rgba(${c.a},${0.10 * alpha * fade})`);
      ctx.fillStyle = trail;
      roundRect(x - w * 0.34, topY - 62, w * 0.68, 62, 4);
      ctx.fill();

      // inner light on the left edge
      ctx.fillStyle = `rgba(255,255,255,${0.10 * fade})`;
      ctx.fillRect(x - w / 2 + 2, topY + 2, 1.5, Math.max(0, botY - topY - 4));
    }
    ctx.restore();
  }

  function pressed(m, t) {
    const k = KEY[m];
    if (!k) return 0;
    let v = 0;
    for (const n of NOTES) {
      if (n.m !== m) continue;
      const hold = n.t > DUR - 8 ? 4.6 : 0.9;
      if (t >= n.t && t <= n.t + Math.min(n.d, hold)) {
        const age = t - n.t;
        v = Math.max(v, (1 - age / hold) * (0.65 + 0.35 * n.v));
      }
    }
    return v;
  }

  function drawKeyboard(t) {
    // keyboard bed / felt
    const bed = ctx.createLinearGradient(0, KEY_Y - 34, 0, KEY_Y);
    bed.addColorStop(0, 'rgba(0,0,0,0)');
    bed.addColorStop(1, 'rgba(0,0,0,0.55)');
    ctx.fillStyle = bed;
    ctx.fillRect(KX0 - 8, KEY_Y - 34, KX1 - KX0 + 16, 34);

    // warm rim light along the key bed
    const rim = ctx.createLinearGradient(KX0, 0, KX1, 0);
    rim.addColorStop(0, 'rgba(255,186,120,0)');
    rim.addColorStop(0.5, 'rgba(255,196,136,0.30)');
    rim.addColorStop(1, 'rgba(255,186,120,0)');
    ctx.fillStyle = rim;
    ctx.fillRect(KX0 - 40, KEY_Y - 16, KX1 - KX0 + 80, 2);

    // felt strip
    ctx.fillStyle = 'rgba(96,26,36,0.75)';
    ctx.fillRect(KX0 - 8, KEY_Y - 12, KX1 - KX0 + 16, 12);
    ctx.fillStyle = 'rgba(150,52,62,0.35)';
    ctx.fillRect(KX0 - 8, KEY_Y - 12, KX1 - KX0 + 16, 3);

    // white keys
    for (const m of whites) {
      const k = KEY[m];
      const p = pressed(m, t);
      const g = ctx.createLinearGradient(0, KEY_Y, 0, KEY_Y + WHITE_H);
      if (p > 0.01) {
        g.addColorStop(0, `rgb(${236},${206 - 26 * p},${172 - 50 * p})`);
        g.addColorStop(0.13, `rgb(226,${210 - 24 * p},${186 - 44 * p})`);
        g.addColorStop(1, `rgb(${176 - 18 * p},${164 - 20 * p},${144 - 22 * p})`);
      } else {
        const warm = ((m * 37) % 11) / 11 * 8;
        g.addColorStop(0, `rgb(${241 - warm * 0.3},${231 - warm * 0.4},${213 - warm})`);
        g.addColorStop(0.13, `rgb(${233 - warm * 0.3},${223 - warm * 0.4},${205 - warm})`);
        g.addColorStop(1, `rgb(${199 - warm * 0.2},${187 - warm * 0.3},${168 - warm * 0.5})`);
      }
      ctx.fillStyle = g;
      roundRect(k.x + 0.8, KEY_Y, k.w - 1.6, WHITE_H, 4);
      ctx.fill();

      // front edge shadow
      const sh = ctx.createLinearGradient(0, KEY_Y + WHITE_H - 16, 0, KEY_Y + WHITE_H);
      sh.addColorStop(0, 'rgba(90,70,45,0)');
      sh.addColorStop(1, 'rgba(60,45,30,0.30)');
      ctx.fillStyle = sh;
      ctx.fillRect(k.x + 1, KEY_Y + WHITE_H - 16, k.w - 2, 16);

      if (p > 0.01) {
        const gl = ctx.createLinearGradient(0, KEY_Y, 0, KEY_Y + 70);
        gl.addColorStop(0, `rgba(255,178,92,${0.22 * p})`);
        gl.addColorStop(1, 'rgba(255,178,92,0)');
        ctx.fillStyle = gl;
        ctx.fillRect(k.x + 1, KEY_Y, k.w - 2, 70);
        // small bloom where the key is struck
        const bl = ctx.createRadialGradient(k.x + k.w / 2, KEY_Y + 6, 1, k.x + k.w / 2, KEY_Y + 6, k.w * 0.9);
        bl.addColorStop(0, `rgba(255,206,150,${0.26 * p})`);
        bl.addColorStop(1, 'rgba(255,206,150,0)');
        ctx.fillStyle = bl;
        ctx.fillRect(k.x - k.w, KEY_Y - k.w, k.w * 3, k.w * 2);
      }
    }

    // black keys
    for (let m = LOW; m <= HIGH; m++) {
      if (!isBlack(m)) continue;
      const k = KEY[m];
      const p = pressed(m, t);
      const g = ctx.createLinearGradient(0, KEY_Y, 0, KEY_Y + BLACK_H);
      g.addColorStop(0, p > 0.01 ? `rgb(${58 + 40 * p},${44 + 30 * p},${40 + 20 * p})` : '#24252b');
      g.addColorStop(0.08, p > 0.01 ? `rgb(${40 + 40 * p},${34 + 28 * p},${32 + 18 * p})` : '#15161b');
      g.addColorStop(1, p > 0.01 ? '#3a2f2a' : '#0a0b0e');
      ctx.fillStyle = g;
      roundRect(k.x, KEY_Y - 4, k.w, BLACK_H + 4, 3);
      ctx.fill();

      // shadow cast on the white keys below
      const bs = ctx.createLinearGradient(0, KEY_Y + BLACK_H - 4, 0, KEY_Y + BLACK_H + 11);
      bs.addColorStop(0, 'rgba(16,10,8,0.26)');
      bs.addColorStop(1, 'rgba(16,10,8,0)');
      ctx.fillStyle = bs;
      ctx.fillRect(k.x - 1, KEY_Y + BLACK_H - 4, k.w + 2, 15);

      // front edge catch-light
      ctx.fillStyle = 'rgba(255,255,255,0.06)';
      ctx.fillRect(k.x + 1.5, KEY_Y + BLACK_H - 4, k.w - 3, 1.5);
      ctx.fillStyle = 'rgba(255,255,255,0.10)';
      ctx.fillRect(k.x + 2, KEY_Y + 1, k.w - 4, 1.5);

      if (p > 0.01) {
        ctx.fillStyle = `rgba(255,178,92,${0.28 * p})`;
        roundRect(k.x + 1, KEY_Y + BLACK_H - 16, k.w - 2, 14, 2);
        ctx.fill();
        const bl2 = ctx.createRadialGradient(k.x + k.w / 2, KEY_Y + 4, 1, k.x + k.w / 2, KEY_Y + 4, k.w * 0.8);
        bl2.addColorStop(0, `rgba(255,206,150,${0.26 * p})`);
        bl2.addColorStop(1, 'rgba(255,206,150,0)');
        ctx.fillStyle = bl2;
        ctx.fillRect(k.x - k.w, KEY_Y - k.w, k.w * 3, k.w * 2);
      }
    }

    // soft shadow falling from the case onto the keys
    const shade = ctx.createLinearGradient(0, KEY_Y, 0, KEY_Y + 34);
    shade.addColorStop(0, 'rgba(24,16,12,0.20)');
    shade.addColorStop(1, 'rgba(24,16,12,0)');
    ctx.fillStyle = shade;
    ctx.fillRect(KX0 - 8, KEY_Y, KX1 - KX0 + 16, 34);

    // front rail (key slip) under the keys
    const slipY = KEY_Y + WHITE_H;
    const slip = ctx.createLinearGradient(0, slipY, 0, slipY + 16);
    slip.addColorStop(0, '#2b1d18');
    slip.addColorStop(0.30, '#4b3128');
    slip.addColorStop(1, '#140d0b');
    ctx.fillStyle = slip;
    ctx.fillRect(KX0 - 14, slipY, KX1 - KX0 + 28, 16);
    ctx.fillStyle = 'rgba(255,186,120,0.20)';
    ctx.fillRect(KX0 - 14, slipY, KX1 - KX0 + 28, 1.2);

    // glossy floor reflection
    drawReflection();
  }

  function drawHits(t) {
    for (const n of NOTES) {
      const age = t - n.t;
      if (age < 0 || age > 0.75) continue;
      const x = noteX(n.m);
      if (x == null) continue;
      if (t > n.t + n.d + 0.2) continue;
      const k = age / 0.75;
      const r = 6 + 46 * Math.sqrt(k);
      ctx.strokeStyle = `rgba(255,206,150,${0.5 * (1 - k) * (0.5 + n.v)})`;
      ctx.lineWidth = 1.6;
      ctx.beginPath();
      ctx.ellipse(x, KEY_Y + 4, r, r * 0.32, 0, 0, Math.PI * 2);
      ctx.stroke();
    }
  }

  function drawVignette() {
    // keep the vignette above the keys so the keyboard stays clean
    const v = ctx.createRadialGradient(W / 2, H * 0.46, 240, W / 2, H * 0.46, 1150);
    v.addColorStop(0, 'rgba(0,0,0,0)');
    v.addColorStop(0.62, 'rgba(0,0,0,0.26)');
    v.addColorStop(1, 'rgba(0,0,0,0.74)');
    ctx.fillStyle = v;
    ctx.fillRect(0, 0, W, KEY_Y + 24);

    // floor falls off into the dark
    const b = ctx.createLinearGradient(0, KEY_Y + WHITE_H - 6, 0, H);
    b.addColorStop(0, 'rgba(0,0,0,0)');
    b.addColorStop(1, 'rgba(0,0,0,0.55)');
    ctx.fillStyle = b;
    ctx.fillRect(0, KEY_Y + WHITE_H - 6, W, H - KEY_Y - WHITE_H + 6);
  }

  function drawGrain(t) {
    ctx.save();
    ctx.globalAlpha = 0.035;
    ctx.globalCompositeOperation = 'overlay';
    const off = (t * 37) % 140;
    ctx.translate(-((t * 61) % 220), -off);
    ctx.fillStyle = grainPattern;
    ctx.fillRect(0, 0, W + 240, H + 160);
    ctx.restore();
  }

  const ease = (x) => x < 0 ? 0 : x > 1 ? 1 : x * x * (3 - 2 * x);

  function drawTitle(t) {
    const a = Math.min(ease((t - 0.55) / 1.5), 1 - ease((t - 4.9) / 1.1));
    if (a <= 0.001) return;
    ctx.save();
    ctx.globalAlpha = a;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    const y0 = 286 - (1 - ease((t - 0.55) / 1.9)) * 14;

    textBand(y0 - 158, y0 + 214, a, 0.82);

    ctx.letterSpacing = '14px';
    ctx.font = '500 24px "Noto Serif Display", "Noto Serif", serif';
    ctx.fillStyle = 'rgba(214,188,152,0.82)';
    ctx.fillText(TITLE_EN, W / 2 + 7, y0 - 74);

    ctx.letterSpacing = '10px';
    ctx.font = '600 104px "Noto Serif CJK SC", "Noto Serif Display", serif';
    ctx.fillStyle = 'rgba(244,230,208,0.96)';
    ctx.fillText(TITLE, W / 2 + 5, y0 + 24);

    // hairline
    const lw = 150 * ease((t - 1.1) / 1.4);
    const line = ctx.createLinearGradient(W / 2 - lw, 0, W / 2 + lw, 0);
    line.addColorStop(0, 'rgba(226,190,140,0)');
    line.addColorStop(0.5, 'rgba(226,190,140,0.75)');
    line.addColorStop(1, 'rgba(226,190,140,0)');
    ctx.fillStyle = line;
    ctx.fillRect(W / 2 - lw, y0 + 96, lw * 2, 1);

    ctx.letterSpacing = '7px';
    ctx.font = '400 19px "Noto Serif Display", "Noto Serif", serif';
    ctx.fillStyle = 'rgba(196,172,143,0.78)';
    ctx.fillText(SUBTITLE, W / 2 + 3, y0 + 136);
    ctx.restore();
  }

  function drawEndCard(t) {
    const a = Math.min(ease((t - END_START) / 1.9), 1 - ease((t - (DUR - 0.8)) / 0.9));
    if (a <= 0.001) return;
    ctx.save();
    ctx.globalAlpha = a;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    textBand(330, 600, a, 0.72);

    ctx.letterSpacing = '8px';
    ctx.font = '400 32px "Noto Serif CJK SC", "Noto Serif Display", serif';
    ctx.fillStyle = 'rgba(244,231,212,0.94)';
    ctx.fillText(END_WORD, W / 2 + 4, 424);

    ctx.letterSpacing = '6px';
    ctx.font = '400 17px "Noto Serif CJK SC", "Noto Serif", serif';
    ctx.fillStyle = 'rgba(206,186,160,0.80)';
    ctx.fillText(CREDIT1, W / 2 + 3, 486);
    ctx.fillText(CREDIT2, W / 2 + 3, 522);

    ctx.restore();
  }

  function drawProgress(t) {
    ctx.fillStyle = 'rgba(255,255,255,0.05)';
    ctx.fillRect(0, 0, W, 2);
    ctx.fillStyle = 'rgba(247,196,132,0.34)';
    ctx.fillRect(0, 0, W * Math.min(1, t / DUR), 2);
  }

  function drawFrame(t) {
    ctx.setTransform(PX, 0, 0, PX, 0, 0);
    ctx.save();
    // a slow, almost imperceptible push-in
    const z = 1.0 + 0.020 * ease(t / DUR) + 0.0025 * Math.sin(t * 0.11);
    ctx.transform(z, 0, 0, z, W / 2 * (1 - z), H * 0.60 * (1 - z));
    drawBackground(t);
    drawMotes(t);
    drawNotes(t);
    drawKeyboard(t);
    drawHits(t);
    drawVignette();
    drawGrain(t);
    ctx.restore();

    ctx.save();
    drawTitle(t);
    drawEndCard(t);
    drawProgress(t);
    // final fade
    const fade = Math.max(ease((t - (DUR - 0.9)) / 0.9), t > DUR - 0.05 ? 1 : 0);
    if (fade > 0) {
      ctx.fillStyle = `rgba(0,0,0,${fade})`;
      ctx.fillRect(0, 0, W, H);
    }
    ctx.restore();
  }

  window.drawFrame = drawFrame;
  window.VIDEO = { width: W * PX, height: H * PX, fps: 30, duration: DUR };
  drawFrame(0);
})();
