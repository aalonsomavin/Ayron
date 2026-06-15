(function () {
  const MONO = ["#2a2a30", "#18181b", "#131316"];
  const A = [
    [0.165, 0.8],
    [0.165, 0.175],
    [0.305, 0.095],
    [0.575, 0.44],
  ];
  const R = 0.115;
  const gap = 0.04;
  const bandX0 = 0.3;
  const bandX1 = 0.7;

  const ANIM_STEP = 0.012;

  const states = new WeakMap();

  function roundPoly(P, radii) {
    const sub = function (a, b) {
      return [a[0] - b[0], a[1] - b[1]];
    };
    const add = function (a, b) {
      return [a[0] + b[0], a[1] + b[1]];
    };
    const sc = function (a, t) {
      return [a[0] * t, a[1] * t];
    };
    const len = function (a) {
      return Math.hypot(a[0], a[1]);
    };
    const nrm = function (a) {
      const l = len(a) || 1;
      return [a[0] / l, a[1] / l];
    };
    const bez = function (p0, p1, p2, u) {
      const m = 1 - u;
      return [
        m * m * p0[0] + 2 * m * u * p1[0] + u * u * p2[0],
        m * m * p0[1] + 2 * m * u * p1[1] + u * u * p2[1],
      ];
    };
    const steps = 12;
    const out = [P[0]];
    for (let i = 1; i < P.length - 1; i++) {
      const r = (radii && radii[i]) || 0;
      if (r <= 0) {
        out.push(P[i]);
        continue;
      }
      const prev = P[i - 1];
      const curr = P[i];
      const next = P[i + 1];
      const t = Math.min(r, len(sub(prev, curr)) * 0.5, len(sub(next, curr)) * 0.5);
      const p1 = add(curr, sc(nrm(sub(prev, curr)), t));
      const p2 = add(curr, sc(nrm(sub(next, curr)), t));
      out.push(p1);
      for (let s = 1; s < steps; s++) out.push(bez(p1, curr, p2, s / steps));
      out.push(p2);
    }
    out.push(P[P.length - 1]);
    return out;
  }

  const Ar = roundPoly(A, { 1: 0.12, 2: 0.05 });
  const Br = Ar.map(function (q) {
    return [1 - q[0], 1 - q[1]];
  });

  function setup(canvas) {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const rect = canvas.getBoundingClientRect();
    const w = rect.width || 36;
    const h = rect.height || 36;
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
    const ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const pad = Math.min(w, h) * 0.13;
    const s = Math.min(w, h) - 2 * pad;
    const ox = (w - s) / 2;
    const oy = (h - s) / 2;
    return {
      ctx: ctx,
      w: w,
      h: h,
      map: {
        X: function (u) {
          return ox + u * s;
        },
        Y: function (v) {
          return oy + v * s;
        },
        L: function (q) {
          return q * s;
        },
      },
    };
  }

  function makeGrad(ctx, map) {
    const g = ctx.createLinearGradient(map.X(0.1), map.Y(0.02), map.X(0.95), map.Y(0.98));
    g.addColorStop(0, MONO[0]);
    g.addColorStop(0.5, MONO[1]);
    g.addColorStop(1, MONO[2]);
    return g;
  }

  function strokePath(ctx, map, P) {
    ctx.beginPath();
    for (let i = 0; i < P.length; i++) {
      const x = map.X(P[i][0]);
      const y = map.Y(P[i][1]);
      if (i) ctx.lineTo(x, y);
      else ctx.moveTo(x, y);
    }
    ctx.stroke();
  }

  function pathLen(map, P) {
    let total = 0;
    for (let i = 0; i < P.length - 1; i++) {
      total += Math.hypot(
        map.X(P[i + 1][0]) - map.X(P[i][0]),
        map.Y(P[i + 1][1]) - map.Y(P[i][1])
      );
    }
    return total;
  }

  function strokeReveal(ctx, map, P, p) {
    const L = pathLen(map, P);
    ctx.save();
    ctx.setLineDash([L, L + 2]);
    ctx.lineDashOffset = L * (1 - p);
    strokePath(ctx, map, P);
    ctx.restore();
  }

  function clipBand(ctx, map, yFrom, yTo, w, h) {
    ctx.beginPath();
    ctx.rect(-2, -2, w + 4, h + 4);
    ctx.rect(
      map.X(bandX0),
      map.Y(yFrom),
      map.X(bandX1) - map.X(bandX0),
      map.Y(yTo) - map.Y(yFrom)
    );
    ctx.clip("evenodd");
  }

  function drawMark(canvasState, p) {
    const ctx = canvasState.ctx;
    const map = canvasState.map;
    const w = canvasState.w;
    const h = canvasState.h;
    const cutTop = 0.5 - gap / 2;
    const cutBot = 0.5 + gap / 2;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.lineWidth = map.L(2 * R);
    ctx.strokeStyle = makeGrad(ctx, map);
    ctx.save();
    clipBand(ctx, map, cutTop, 1.5, w, h);
    strokeReveal(ctx, map, Ar, p);
    ctx.restore();
    ctx.save();
    clipBand(ctx, map, -0.5, cutBot, w, h);
    strokeReveal(ctx, map, Br, p);
    ctx.restore();
  }

  function drawAvatar(canvasState, p) {
    const ctx = canvasState.ctx;
    const w = canvasState.w;
    const h = canvasState.h;
    ctx.clearRect(0, 0, w, h);
    drawMark(canvasState, p);
  }

  function getCanvas(root) {
    if (!root) return null;
    if (root.tagName === "CANVAS") return root;
    return root.querySelector(".ay-agent-avatar__canvas");
  }

  function stop(state) {
    if (!state) return;
    if (state.raf) {
      cancelAnimationFrame(state.raf);
      state.raf = null;
    }
    state.active = false;
    if (state.canvasState) drawAvatar(state.canvasState, 1);
  }

  function start(state) {
    if (!state || !state.canvasState) return;
    stop(state);
    state.active = true;
    state.prog = 0;
    function animate() {
      if (!state.active) return;
      state.prog += ANIM_STEP;
      const phase = state.prog % 2;
      const p = phase < 1 ? phase : 2 - phase;
      drawAvatar(state.canvasState, p);
      state.raf = requestAnimationFrame(animate);
    }
    animate();
  }

  function mount(root, options) {
    const canvas = getCanvas(root);
    if (!canvas) return null;
    let state = states.get(canvas);
    if (!state) {
      state = { canvas: canvas, canvasState: setup(canvas), raf: null, active: false, prog: 0 };
      states.set(canvas, state);
    } else {
      state.canvasState = setup(canvas);
    }
    const active = options && options.active;
    if (active) start(state);
    else drawAvatar(state.canvasState, 1);
    return state;
  }

  function mountAll(root) {
    (root || document).querySelectorAll(".ay-agent-avatar").forEach(function (el) {
      mount(el, { active: el.classList.contains("ay-agent-avatar--active") });
    });
  }

  window.AyronAgentAvatar = {
    mount: mount,
    start: function (root) {
      const canvas = getCanvas(root);
      start(states.get(canvas));
    },
    stop: function (root) {
      const canvas = getCanvas(root);
      stop(states.get(canvas));
    },
    mountAll: mountAll,
  };
})();
