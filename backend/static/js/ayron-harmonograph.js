(function () {
  const BRAND = [
    [111, 230, 207],
    [147, 239, 102],
    [217, 242, 62],
  ];

  const FILL_RATIO = 0.9;
  const MIN_SCALE = 0.8;
  const MAX_ATTEMPTS = 10;

  function setup(canvas) {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const rect = canvas.getBoundingClientRect();
    const w = rect.width || 560;
    const h = rect.height || 560;
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
    const ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    return { ctx, w, h };
  }

  function posAt(tt, params) {
    const f = params.f;
    const p = params.p;
    const d = params.d;
    const x =
      params.cx +
      params.A * 0.5 * Math.sin(f[0] * tt + p[0]) * Math.exp(-d[0] * tt) +
      params.A * 0.5 * Math.sin(f[1] * tt + p[1]) * Math.exp(-d[1] * tt);
    const y =
      params.cy +
      params.A * 0.5 * Math.sin(f[2] * tt + p[2]) * Math.exp(-d[2] * tt) +
      params.A * 0.5 * Math.sin(f[3] * tt + p[3]) * Math.exp(-d[3] * tt);
    return { x: x, y: y };
  }

  function mapPoint(point, fit) {
    return {
      x: (point.x - fit.anchorX) * fit.scale + fit.anchorX + fit.dx,
      y: (point.y - fit.anchorY) * fit.scale + fit.anchorY + fit.dy,
    };
  }

  function transformedPathBounds(params, tEnd, fit) {
    let minX = Infinity;
    let maxX = -Infinity;
    let minY = Infinity;
    let maxY = -Infinity;

    for (let tt = 0; tt <= tEnd; tt += 0.05) {
      const point = mapPoint(posAt(tt, params), fit);
      minX = Math.min(minX, point.x);
      maxX = Math.max(maxX, point.x);
      minY = Math.min(minY, point.y);
      maxY = Math.max(maxY, point.y);
    }

    return { minX: minX, maxX: maxX, minY: minY, maxY: maxY };
  }

  function fitLimits(canvasW, canvasH, containerW, containerH, strokePad, margins) {
    const canvasLeft = containerW - canvasW;
    return {
      minX: Math.max(strokePad, margins.left - canvasLeft + strokePad),
      maxY: Math.min(canvasH, containerH) - strokePad - margins.bottom,
    };
  }

  function fitViolates(params, tEnd, fit, limits) {
    const bounds = transformedPathBounds(params, tEnd, fit);
    return bounds.minX < limits.minX || bounds.maxY > limits.maxY;
  }

  function cloneFit(fit) {
    return {
      scale: fit.scale,
      dx: fit.dx,
      dy: fit.dy,
      anchorX: fit.anchorX,
      anchorY: fit.anchorY,
    };
  }

  function nudgeFit(params, tEnd, fit, limits) {
    const next = cloneFit(fit);
    for (let i = 0; i < 10; i++) {
      const bounds = transformedPathBounds(params, tEnd, next);
      if (bounds.minX < limits.minX) {
        next.dx += limits.minX - bounds.minX;
      }
      const shifted = transformedPathBounds(params, tEnd, next);
      if (shifted.maxY > limits.maxY) {
        next.dy += limits.maxY - shifted.maxY;
      }
    }
    return next;
  }

  function shrinkToFit(params, tEnd, fit, limits) {
    let next = nudgeFit(params, tEnd, cloneFit(fit), limits);
    while (fitViolates(params, tEnd, next, limits) && next.scale > 0.42) {
      next.scale *= 0.94;
      next.dx = 0;
      next.dy = 0;
      next = nudgeFit(params, tEnd, next, limits);
    }
    return next;
  }

  function expandToFill(params, tEnd, fit, limits, canvasW) {
    const base = nudgeFit(params, tEnd, cloneFit(fit), limits);
    const bounds = transformedPathBounds(params, tEnd, base);
    const pathW = Math.max(bounds.maxX - bounds.minX, 1);
    const pathH = Math.max(bounds.maxY - bounds.minY, 1);
    const availW = Math.max(canvasW - limits.minX, 1);
    const availH = Math.max(limits.maxY, 1);
    const grow = Math.min((availW * FILL_RATIO) / pathW, (availH * FILL_RATIO) / pathH);

    if (grow <= 1.02) {
      return base;
    }

    let lo = base.scale;
    let hi = base.scale * grow;

    for (let i = 0; i < 18; i++) {
      const mid = (lo + hi) / 2;
      let trial = cloneFit(base);
      trial.scale = mid;
      trial.dx = 0;
      trial.dy = 0;
      trial = nudgeFit(params, tEnd, trial, limits);
      if (fitViolates(params, tEnd, trial, limits)) {
        hi = mid;
      } else {
        lo = mid;
      }
    }

    let result = cloneFit(base);
    result.scale = lo;
    result.dx = 0;
    result.dy = 0;
    return nudgeFit(params, tEnd, result, limits);
  }

  function randomParams(w, h, rnd, ampFactor) {
    const anchorX = w * 0.82;
    const anchorY = h * 0.16;
    return {
      cx: anchorX,
      cy: anchorY,
      A: Math.min(w, h) * ampFactor,
      anchorX: anchorX,
      anchorY: anchorY,
      f: [rnd(1.99, 2.01), rnd(2.99, 3.01), rnd(2.99, 3.01), rnd(1.99, 2.01)],
      p: [rnd(0, 6.28), rnd(0, 6.28), rnd(0, 6.28), rnd(0, 6.28)],
      d: [rnd(0.001, 0.003), rnd(0.001, 0.003), rnd(0.001, 0.003), rnd(0.001, 0.003)],
    };
  }

  function buildLayout(params, tEnd, canvasW, canvasH, containerW, containerH, lineWidth) {
    const strokePad = Math.ceil(lineWidth / 2) + 6;
    const margins = { left: 20, bottom: 20 };
    const limits = fitLimits(canvasW, canvasH, containerW, containerH, strokePad, margins);
    const baseFit = {
      scale: 1,
      dx: 0,
      dy: 0,
      anchorX: params.anchorX,
      anchorY: params.anchorY,
    };

    let fit = shrinkToFit(params, tEnd, baseFit, limits);
    fit = expandToFill(params, tEnd, fit, limits, canvasW);
    return fit;
  }

  function brandGradient(ctx, w, h) {
    const gradient = ctx.createLinearGradient(w * 0.95, h * 0.05, w * 0.05, h * 0.95);
    gradient.addColorStop(0, "rgb(" + BRAND[0].join(",") + ")");
    gradient.addColorStop(0.5, "rgb(" + BRAND[1].join(",") + ")");
    gradient.addColorStop(1, "rgb(" + BRAND[2].join(",") + ")");
    return gradient;
  }

  function mount(canvas, opts) {
    if (!canvas || canvas.dataset.harmonoMounted === "true") return;

    const options = opts || {};

    function begin() {
      const container = canvas.parentElement;
      const containerW = container ? container.clientWidth : 0;
      const containerH = container ? container.clientHeight : 0;
      if (containerW < 80 || containerH < 80) {
        requestAnimationFrame(begin);
        return;
      }

      canvas.dataset.harmonoMounted = "true";

      const speed = options.speed || 1.0;
      const alpha = options.alpha == null ? 0.68 : options.alpha;
      const lineWidth = options.lw || 1;
      const { ctx, w, h } = setup(canvas);
      const rnd = function (a, b) {
        return a + Math.random() * (b - a);
      };

      const ampFactor = options.ampFactor || 0.98;
      const tEnd = 70 * Math.PI;
      let params = null;
      let fit = null;

      for (let attempt = 0; attempt < MAX_ATTEMPTS; attempt++) {
        const candidate = randomParams(w, h, rnd, ampFactor);
        const candidateFit = buildLayout(
          candidate,
          tEnd,
          w,
          h,
          containerW,
          containerH,
          lineWidth
        );
        params = candidate;
        fit = candidateFit;
        if (candidateFit.scale >= MIN_SCALE) {
          break;
        }
      }

      const strokeStyle = options.color || brandGradient(ctx, w, h);

      let t = 0;
      const Tend = 70;
      let raf = null;

      function drawPath(tmax) {
        ctx.beginPath();
        for (let tt = 0; tt <= tmax; tt += 0.05) {
          const point = mapPoint(posAt(tt, params), fit);
          if (tt === 0) ctx.moveTo(point.x, point.y);
          else ctx.lineTo(point.x, point.y);
        }
        ctx.strokeStyle = strokeStyle;
        ctx.globalAlpha = alpha;
        ctx.lineWidth = lineWidth;
        ctx.lineJoin = "round";
        ctx.lineCap = "round";
        ctx.stroke();
        ctx.globalAlpha = 1;
      }

      function tick() {
        t += speed;
        const tmax = Math.min(t, Tend * Math.PI);
        ctx.clearRect(0, 0, w, h);
        drawPath(tmax);

        if (t >= Tend * Math.PI) {
          if (raf) cancelAnimationFrame(raf);
          return;
        }
        raf = requestAnimationFrame(tick);
      }

      tick();
    }

    requestAnimationFrame(begin);
  }

  window.AyronHarmonograph = { mount: mount };
})();
