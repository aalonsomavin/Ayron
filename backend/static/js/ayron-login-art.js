(function () {
  "use strict";

  var LABELS = {
    hilbert: ["Curva de Hilbert", "orden 6 · 4⁶ vértices"],
    truchet: ["Mosaico de Truchet", "arcos · teselado"],
    maze: ["Laberinto", "backtracker recursivo"],
    golden: ["Espiral áurea", "φ ≈ 1.618"],
    contours: ["Campo de contornos", "Σ sin(·)"],
    triangles: ["Malla triangular", "lattice isométrico"],
  };

  var MOTIF_ORDER = ["hilbert", "truchet", "maze", "golden", "contours", "triangles"];
  var ROTATE_MS = 8000;
  var FADE_MS = 1100;
  var DESKTOP_MQ = window.matchMedia("(min-width: 881px)");

  function rng(seed) {
    var a = seed | 0 || 1;
    return function () {
      a |= 0;
      a = (a + 0x6d2b79f5) | 0;
      var t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function grad(ctx, w, h, palette) {
    var g = ctx.createLinearGradient(0, 0, w, h);
    if (palette === "ayron") {
      g.addColorStop(0, "#cfe96a");
      g.addColorStop(0.5, "#46c193");
      g.addColorStop(1, "#168b80");
    } else {
      g.addColorStop(0, "#9aa7c4");
      g.addColorStop(0.55, "#5b7fe0");
      g.addColorStop(1, "#3b6ef6");
    }
    return g;
  }

  function mHilbert(ctx, w, h, r, pal) {
    var order = 6;
    var side = 1 << order;
    var n = side * side;
    var span = Math.max(w, h) * 1.06;
    var cell = span / (side - 1);
    var ox = (w - cell * (side - 1)) / 2;
    var oy = (h - cell * (side - 1)) / 2;
    function rot(s, x, y, rx, ry) {
      if (ry === 0) {
        if (rx === 1) {
          x = s - 1 - x;
          y = s - 1 - y;
        }
        var t = x;
        x = y;
        y = t;
      }
      return [x, y];
    }
    var pts = [];
    for (var dd = 0; dd < n; dd++) {
      var rx;
      var ry;
      var t = dd;
      var x = 0;
      var y = 0;
      for (var s = 1; s < side; s *= 2) {
        rx = 1 & (t / 2 | 0);
        ry = 1 & (t ^ rx);
        var rr = rot(s, x, y, rx, ry);
        x = rr[0];
        y = rr[1];
        x += s * rx;
        y += s * ry;
        t = Math.floor(t / 4);
      }
      pts.push([ox + x * cell, oy + y * cell]);
    }
    ctx.strokeStyle = grad(ctx, w, h, pal);
    ctx.globalAlpha = 0.9;
    ctx.lineWidth = 1.15;
    ctx.lineJoin = "round";
    ctx.lineCap = "round";
    ctx.beginPath();
    for (var i = 0; i < pts.length; i++) {
      var p = pts[i];
      if (i) ctx.lineTo(p[0], p[1]);
      else ctx.moveTo(p[0], p[1]);
    }
    ctx.stroke();
    ctx.globalAlpha = 1;
  }

  function mTruchet(ctx, w, h, rnd, pal) {
    var cell = Math.max(26, Math.min(w, h) / 13);
    var cols = Math.ceil(w / cell) + 1;
    var rows = Math.ceil(h / cell) + 1;
    var rad = cell / 2;
    ctx.strokeStyle = grad(ctx, w, h, pal);
    ctx.globalAlpha = 0.85;
    ctx.lineWidth = 1.4;
    ctx.lineCap = "round";
    for (var j = 0; j < rows; j++) {
      for (var i = 0; i < cols; i++) {
        var x = i * cell;
        var y = j * cell;
        ctx.beginPath();
        if (rnd() < 0.5) {
          ctx.arc(x, y, rad, 0, Math.PI / 2);
          ctx.moveTo(x + cell, y + cell);
          ctx.arc(x + cell, y + cell, rad, Math.PI, Math.PI * 1.5);
        } else {
          ctx.arc(x + cell, y, rad, Math.PI / 2, Math.PI);
          ctx.moveTo(x, y + cell);
          ctx.arc(x, y + cell, rad, Math.PI * 1.5, Math.PI * 2);
        }
        ctx.stroke();
      }
    }
    ctx.globalAlpha = 1;
  }

  function mMaze(ctx, w, h, rnd, pal) {
    var cell = Math.max(22, Math.min(w, h) / 16);
    var cols = Math.max(2, Math.floor(w / cell));
    var rows = Math.max(2, Math.floor(h / cell));
    var ox = (w - (cols - 1) * cell) / 2;
    var oy = (h - (rows - 1) * cell) / 2;
    function id(x, y) {
      return y * cols + x;
    }
    var vis = new Uint8Array(cols * rows);
    var edges = [];
    var stack = [[0, 0]];
    vis[0] = 1;
    var dirs = [
      [1, 0],
      [-1, 0],
      [0, 1],
      [0, -1],
    ];
    while (stack.length) {
      var c = stack[stack.length - 1];
      var cx = c[0];
      var cy = c[1];
      var nb = [];
      for (var k = 0; k < dirs.length; k++) {
        var d = dirs[k];
        var nx = cx + d[0];
        var ny = cy + d[1];
        if (nx >= 0 && nx < cols && ny >= 0 && ny < rows && !vis[id(nx, ny)]) nb.push([nx, ny]);
      }
      if (nb.length) {
        var n = nb[Math.floor(rnd() * nb.length)];
        vis[id(n[0], n[1])] = 1;
        edges.push([cx, cy, n[0], n[1]]);
        stack.push(n);
      } else stack.pop();
    }
    ctx.strokeStyle = grad(ctx, w, h, pal);
    ctx.globalAlpha = 0.85;
    ctx.lineWidth = 1.7;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.beginPath();
    for (var e = 0; e < edges.length; e++) {
      var e2 = edges[e];
      ctx.moveTo(ox + e2[0] * cell, oy + e2[1] * cell);
      ctx.lineTo(ox + e2[2] * cell, oy + e2[3] * cell);
    }
    ctx.stroke();
    ctx.globalAlpha = 1;
  }

  function mGolden(ctx, w, h, r, pal) {
    var g = grad(ctx, w, h, pal);
    var phi = 1.618033;
    var padR = w * 0.04;
    var availW = w * 0.94;
    var availH = h * 0.92;
    var rw;
    var rh;
    if (availW / availH >= phi) {
      rh = availH;
      rw = rh * phi;
    } else {
      rw = availW;
      rh = rw / phi;
    }
    var x = w - padR - rw;
    var y = (h - rh) / 2;
    var W = rw;
    var H = rh;
    var o = W >= H ? 0 : 1;
    var squares = [];
    var arcs = [];
    var steps = 0;
    while (Math.min(W, H) > 2 && steps < 60) {
      var s = Math.min(W, H);
      if (o === 0) {
        squares.push([x, y, s, s]);
        arcs.push([x + s, y + s, s, Math.PI, Math.PI * 1.5]);
        x += s;
        W -= s;
      } else if (o === 1) {
        squares.push([x, y, s, s]);
        arcs.push([x, y + s, s, Math.PI * 1.5, Math.PI * 2]);
        y += s;
        H -= s;
      } else if (o === 2) {
        squares.push([x + W - s, y, s, s]);
        arcs.push([x + W - s, y, s, 0, Math.PI * 0.5]);
        W -= s;
      } else {
        squares.push([x, y + H - s, s, s]);
        arcs.push([x + s, y + H - s, s, Math.PI * 0.5, Math.PI]);
        H -= s;
      }
      o = (o + 1) % 4;
      steps++;
    }
    ctx.strokeStyle = g;
    ctx.globalAlpha = 0.22;
    ctx.lineWidth = 1;
    ctx.lineJoin = "miter";
    for (var i = 0; i < squares.length; i++) {
      var sq = squares[i];
      ctx.strokeRect(sq[0], sq[1], sq[2], sq[3]);
    }
    ctx.globalAlpha = 0.92;
    ctx.lineWidth = 1.8;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.beginPath();
    for (var a = 0; a < arcs.length; a++) {
      var ar = arcs[a];
      ctx.arc(ar[0], ar[1], ar[2], ar[3], ar[4]);
    }
    ctx.stroke();
    ctx.globalAlpha = 1;
  }

  function mContours(ctx, w, h, r, pal) {
    var gap = Math.max(11, Math.min(w, h) / 22);
    ctx.strokeStyle = grad(ctx, w, h, pal);
    ctx.globalAlpha = 0.72;
    ctx.lineWidth = 1.1;
    ctx.lineJoin = "round";
    for (var by = -gap; by < h + gap; by += gap) {
      ctx.beginPath();
      for (var x = 0; x <= w; x += 4) {
        var yy = by + Math.sin(x * 0.012 + by * 0.03) * gap * 0.62 + Math.sin(x * 0.027 + by * 0.018) * gap * 0.36;
        if (x === 0) ctx.moveTo(x, yy);
        else ctx.lineTo(x, yy);
      }
      ctx.stroke();
    }
    ctx.globalAlpha = 1;
  }

  function mTriangles(ctx, w, h, r, pal) {
    var s = Math.max(28, Math.min(w, h) / 11);
    var dy = s * 0.866;
    ctx.strokeStyle = grad(ctx, w, h, pal);
    ctx.globalAlpha = 0.66;
    ctx.lineWidth = 1;
    ctx.lineJoin = "round";
    ctx.beginPath();
    var row = 0;
    for (var y = -dy; y <= h + dy; y += dy, row++) {
      var xoff = row % 2 ? s / 2 : 0;
      for (var x = -s; x <= w + s; x += s) {
        var px = x + xoff;
        ctx.moveTo(px, y);
        ctx.lineTo(px + s, y);
        ctx.moveTo(px, y);
        ctx.lineTo(px - s / 2, y + dy);
        ctx.moveTo(px, y);
        ctx.lineTo(px + s / 2, y + dy);
      }
    }
    ctx.stroke();
    ctx.globalAlpha = 1;
  }

  var MOTIFS = {
    hilbert: mHilbert,
    truchet: mTruchet,
    maze: mMaze,
    golden: mGolden,
    contours: mContours,
    triangles: mTriangles,
  };

  function updateLabels(motif) {
    var lbl = LABELS[motif] || LABELS.hilbert;
    var le = document.getElementById("ay-motif-label");
    var se = document.getElementById("ay-motif-sub");
    if (le) le.textContent = lbl[0];
    if (se) se.textContent = lbl[1];
  }

  function drawArt(canvas, motif) {
    if (!canvas) return;
    var pal = canvas.getAttribute("data-palette") || "ayron";
    var seed = parseInt(canvas.getAttribute("data-seed"), 10);
    if (isNaN(seed)) seed = 7;
    canvas.setAttribute("data-motif", motif);
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    var rect = canvas.getBoundingClientRect();
    var w = Math.max(1, rect.width);
    var h = Math.max(1, rect.height);
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
    var ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);
    (MOTIFS[motif] || mHilbert)(ctx, w, h, rng(seed), pal);
  }

  var canvasA = document.getElementById("ay-login-art-a");
  var canvasB = document.getElementById("ay-login-art-b");
  var canvases = [canvasA, canvasB].filter(Boolean);
  if (!canvases.length) return;

  var motifIndex = Math.floor(Math.random() * MOTIF_ORDER.length);
  var activeIdx = 0;
  var transitioning = false;
  var rotateTimer = null;
  var resizeObserver = null;
  var active = false;

  function activeCanvas() {
    return canvases[activeIdx];
  }

  function redraw() {
    if (!active) return;
    var motif = MOTIF_ORDER[motifIndex];
    drawArt(activeCanvas(), motif);
    var idle = canvases[1 - activeIdx];
    if (idle) drawArt(idle, motif);
  }

  function setMotif(index, animate) {
    var motif = MOTIF_ORDER[index];
    if (!motif) return;

    if (!animate || canvases.length < 2) {
      drawArt(activeCanvas(), motif);
      updateLabels(motif);
      canvases.forEach(function (c, i) {
        c.classList.toggle("is-active", i === activeIdx);
      });
      return;
    }

    if (transitioning) return;
    transitioning = true;
    var nextIdx = 1 - activeIdx;
    var incoming = canvases[nextIdx];
    var outgoing = canvases[activeIdx];
    drawArt(incoming, motif);
    updateLabels(motif);
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        incoming.classList.add("is-active");
        outgoing.classList.remove("is-active");
        activeIdx = nextIdx;
        window.setTimeout(function () {
          transitioning = false;
        }, FADE_MS);
      });
    });
  }

  function advanceMotif() {
    if (document.hidden || !active) return;
    motifIndex = (motifIndex + 1) % MOTIF_ORDER.length;
    setMotif(motifIndex, true);
  }

  function startRotation() {
    if (rotateTimer) return;
    rotateTimer = window.setInterval(advanceMotif, ROTATE_MS);
  }

  function stopRotation() {
    if (rotateTimer) {
      window.clearInterval(rotateTimer);
      rotateTimer = null;
    }
  }

  function activate() {
    if (active) return;
    active = true;
    canvases.forEach(function (c) {
      c.setAttribute("data-palette", "ayron");
    });
    setMotif(motifIndex, false);
    window.addEventListener("resize", redraw);
    if (window.ResizeObserver) {
      resizeObserver = new ResizeObserver(redraw);
      canvases.forEach(function (c) {
        resizeObserver.observe(c);
      });
    }
    startRotation();
  }

  function deactivate() {
    if (!active) return;
    active = false;
    stopRotation();
    window.removeEventListener("resize", redraw);
    if (resizeObserver) {
      resizeObserver.disconnect();
      resizeObserver = null;
    }
  }

  function syncWithViewport() {
    if (DESKTOP_MQ.matches) activate();
    else deactivate();
  }

  document.addEventListener("visibilitychange", function () {
    if (document.hidden) stopRotation();
    else if (active) startRotation();
  });

  if (typeof DESKTOP_MQ.addEventListener === "function") {
    DESKTOP_MQ.addEventListener("change", syncWithViewport);
  } else if (typeof DESKTOP_MQ.addListener === "function") {
    DESKTOP_MQ.addListener(syncWithViewport);
  }

  syncWithViewport();
})();
