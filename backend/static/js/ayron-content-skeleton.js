(function () {
  const REVEAL_MS = 460;
  const SKELETON_FADE_MS = 280;
  const CHART_W = 640;
  const CHART_H = 200;
  const CHART_PL = 46;
  const CHART_PR = 14;
  const CHART_PT = 14;
  const CHART_PB = 30;

  function shimmerEl() {
    const el = document.createElement("div");
    el.className = "ay-content-block__shimmer";
    el.innerHTML = '<div class="ay-content-block__shimmer-bar"></div>';
    return el;
  }

  function svgEl(viewBox, className) {
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", viewBox);
    svg.setAttribute("class", className);
    svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
    return svg;
  }

  function chartPlotWrap(chartType, child) {
    const wrap = document.createElement("div");
    wrap.className =
      "ay-content-block__skeleton-chart ay-content-block__skeleton-chart--" + chartType;
    wrap.appendChild(child);
    return wrap;
  }

  function axisTicks(svg, count, yBase, yStep) {
    for (let i = 0; i < count; i += 1) {
      const y = yBase + i * yStep;
      const tick = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      tick.setAttribute("x", "22");
      tick.setAttribute("y", String(y - 3));
      tick.setAttribute("width", "18");
      tick.setAttribute("height", "7");
      tick.setAttribute("rx", "3");
      tick.setAttribute("class", "ay-content-block__skeleton-axis-tick");
      svg.appendChild(tick);
    }
  }

  function gridLines(svg, count, yBase, yStep) {
    for (let i = 0; i < count; i += 1) {
      const y = yBase + i * yStep;
      const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
      line.setAttribute("x1", String(CHART_PL));
      line.setAttribute("x2", String(CHART_W - 10));
      line.setAttribute("y1", String(y));
      line.setAttribute("y2", String(y));
      line.setAttribute("class", "ay-content-block__skeleton-grid-line");
      svg.appendChild(line);
    }
  }

  function xLabelBars(count) {
    const labels = document.createElement("div");
    labels.className = "ay-content-block__skeleton-x-labels";
    for (let i = 0; i < count; i += 1) {
      const bar = document.createElement("span");
      bar.className = "ay-content-block__skeleton-x-label";
      labels.appendChild(bar);
    }
    return labels;
  }

  function lineSkeleton() {
    const iw = CHART_W - CHART_PL - CHART_PR;
    const ih = CHART_H - CHART_PT - CHART_PB;
    const baseY = CHART_PT + ih;
    const pointCount = 6;
    const xs = function (i) {
      return CHART_PL + (i / (pointCount - 1)) * iw;
    };
    const ys = function (v) {
      return CHART_PT + (1 - v / 90) * ih;
    };
    const values = [34, 37, 35, 42, 39, 45];

    const svg = svgEl("0 0 " + CHART_W + " " + CHART_H, "ay-content-block__skeleton-svg");
    gridLines(svg, 4, CHART_PT, ih / 4);
    axisTicks(svg, 4, CHART_PT + 7, ih / 4);

    const points = values
      .map(function (v, i) {
        return xs(i).toFixed(1) + "," + ys(v + 3 * Math.sin(i * 1.1)).toFixed(1);
      })
      .join(" ");

    const polyline = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
    polyline.setAttribute("points", points);
    polyline.setAttribute("class", "ay-content-block__skeleton-line-path");
    svg.appendChild(polyline);

    values.forEach(function (v, i) {
      const dot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      dot.setAttribute("cx", String(xs(i)));
      dot.setAttribute("cy", String(ys(v + 3 * Math.sin(i * 1.1))));
      dot.setAttribute("r", "3.2");
      dot.setAttribute("class", "ay-content-block__skeleton-line-dot");
      svg.appendChild(dot);
    });

    const wrap = chartPlotWrap("line", svg);
    wrap.appendChild(xLabelBars(6));
    return wrap;
  }

  function barSkeleton() {
    const iw = CHART_W - CHART_PL - CHART_PR;
    const ih = CHART_H - CHART_PT - CHART_PB;
    const baseY = CHART_PT + ih;
    const barCount = 8;
    const barWidth = 36;
    const slot = iw / barCount;
    const heights = [0.92, 0.78, 0.46, 0.42, 0.4, 0.32, 0.27, 0.27];

    const svg = svgEl("0 0 " + CHART_W + " " + CHART_H, "ay-content-block__skeleton-svg");
    gridLines(svg, 5, CHART_PT, ih / 4);
    axisTicks(svg, 5, CHART_PT + 4, ih / 4);

    heights.forEach(function (frac, i) {
      const x = CHART_PL + i * slot + (slot - barWidth) / 2;
      const height = frac * ih;
      const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      rect.setAttribute("x", String(x));
      rect.setAttribute("y", String(baseY - height));
      rect.setAttribute("width", String(barWidth));
      rect.setAttribute("height", String(height));
      rect.setAttribute("rx", "4");
      rect.setAttribute("class", "ay-content-block__skeleton-bar-col");
      rect.style.animationDelay = i * 0.08 + "s";
      svg.appendChild(rect);
    });

    const wrap = chartPlotWrap("bar", svg);
    wrap.appendChild(xLabelBars(barCount));
    return wrap;
  }

  function pieSkeleton() {
    const cx = 120;
    const cy = 100;
    const r = 86;

    const svg = svgEl("0 0 240 200", "ay-content-block__skeleton-svg ay-content-block__skeleton-svg--pie");
    const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    circle.setAttribute("cx", String(cx));
    circle.setAttribute("cy", String(cy));
    circle.setAttribute("r", String(r));
    circle.setAttribute("class", "ay-content-block__skeleton-pie-disc");
    svg.appendChild(circle);

    for (let i = 0; i < 5; i += 1) {
      const angle = -Math.PI / 2 + i * 1.05;
      const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
      line.setAttribute("x1", String(cx));
      line.setAttribute("y1", String(cy));
      line.setAttribute("x2", String(cx + r * Math.cos(angle)));
      line.setAttribute("y2", String(cy + r * Math.sin(angle)));
      line.setAttribute("class", "ay-content-block__skeleton-pie-spoke");
      svg.appendChild(line);
    }

    const plot = chartPlotWrap("pie", svg);

    const legend = document.createElement("div");
    legend.className = "ay-content-block__skeleton-pie-legend";
    [54, 44, 90, 52, 40, 70, 52, 42].forEach(function (w) {
      const item = document.createElement("div");
      item.className = "ay-content-block__skeleton-pie-legend-item";
      const dot = document.createElement("span");
      dot.className = "ay-content-block__skeleton-pie-dot";
      const bar = document.createElement("span");
      bar.className = "ay-content-block__skeleton-pie-label";
      bar.style.width = w + "px";
      item.appendChild(dot);
      item.appendChild(bar);
      legend.appendChild(item);
    });

    const wrap = document.createElement("div");
    wrap.className = "ay-content-block__skeleton-pie-wrap";
    wrap.appendChild(plot);
    wrap.appendChild(legend);
    return wrap;
  }

  function tableSkeleton(columnCount) {
    const cols = Math.max(columnCount || 3, 2);
    const wrap = document.createElement("div");
    wrap.className = "ay-content-block__skeleton-table";
    wrap.style.setProperty("--ay-skel-cols", String(cols));

    const head = document.createElement("div");
    head.className = "ay-content-block__skeleton-table-head";
    for (let i = 0; i < cols; i += 1) {
      const cell = document.createElement("span");
      cell.className = "ay-content-block__skeleton-table-cell";
      head.appendChild(cell);
    }
    wrap.appendChild(head);

    const body = document.createElement("div");
    body.className = "ay-content-block__skeleton-table-body";
    for (let r = 0; r < 8; r += 1) {
      const row = document.createElement("div");
      row.className = "ay-content-block__skeleton-table-row";
      for (let c = 0; c < cols; c += 1) {
        const cell = document.createElement("span");
        cell.className = "ay-content-block__skeleton-table-cell";
        cell.style.width = (40 + ((r + c) % 4) * 18) + "%";
        row.appendChild(cell);
      }
      body.appendChild(row);
    }
    wrap.appendChild(body);
    return wrap;
  }

  function buildSkeletonShape(options) {
    const kind = options.kind || "chart";
    const chartType = options.chartType || "bar";

    if (kind === "table") {
      return tableSkeleton(options.columnCount);
    }
    if (chartType === "line") return lineSkeleton();
    if (chartType === "pie") return pieSkeleton();
    return barSkeleton();
  }

  function normalizeChartType(chartType) {
    const key = (chartType || "").toLowerCase();
    if (key === "line" || key === "pie" || key === "bar") return key;
    return null;
  }

  function createPlaceholder(options) {
    const opts = options || {};
    const kind = opts.kind || "chart";
    let chartType = null;
    if (kind === "chart") {
      chartType = normalizeChartType(opts.chartType);
      if (!chartType) return null;
    }
    const wrapper = document.createElement("div");
    wrapper.className = "ay-content-block ay-content-block--" + (opts.kind || "chart");
    if (opts.toolCallId) wrapper.dataset.toolCallId = opts.toolCallId;
    wrapper.dataset.kind = opts.kind || "chart";
    if (opts.kind === "chart" || !opts.kind) {
      wrapper.dataset.chartType = chartType;
    }

    const content = document.createElement("div");
    content.className = "ay-content-block__content";
    wrapper.appendChild(content);

    const skeleton = document.createElement("div");
    skeleton.className = "ay-content-block__skeleton ay-card";
    skeleton.appendChild(buildSkeletonShape({ kind: kind, chartType: chartType, columnCount: opts.columnCount }));
    skeleton.appendChild(shimmerEl());
    wrapper.appendChild(skeleton);

    return wrapper;
  }

  function findPlaceholder(bubble, kind, toolCallId) {
    if (!bubble) return null;
    const pending = ':not(.is-revealed):not([data-filled="true"])';
    if (toolCallId) {
      const byId = bubble.querySelector(
        '.ay-content-block[data-tool-call-id="' + toolCallId + '"]' + pending
      );
      if (byId) return byId;
    }
    return bubble.querySelector(
      '.ay-content-block[data-kind="' + kind + '"]' + pending
    );
  }

  function reveal(wrapper, contentNode, options) {
    const opts = options || {};
    const animate = opts.animate !== false;
    if (!wrapper) {
      if (contentNode && contentNode.parentNode) return contentNode;
      return contentNode;
    }

    const contentLayer = wrapper.querySelector(".ay-content-block__content");
    const skeletonLayer = wrapper.querySelector(".ay-content-block__skeleton");
    if (!contentLayer) return wrapper;

    contentLayer.innerHTML = "";
    if (contentNode) {
      contentLayer.appendChild(contentNode);
      wrapper.dataset.filled = "true";
    }

    if (!animate) {
      wrapper.classList.add("is-revealed", "is-revealed--instant");
      if (skeletonLayer) skeletonLayer.remove();
      return wrapper;
    }

    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        wrapper.classList.add("is-revealed");
        window.setTimeout(function () {
          if (skeletonLayer && skeletonLayer.parentNode) skeletonLayer.remove();
          wrapper.classList.remove("is-revealed--instant");
        }, Math.max(REVEAL_MS, SKELETON_FADE_MS) + 20);
      });
    });

    return wrapper;
  }

  function remove(wrapper) {
    if (wrapper && wrapper.parentNode) wrapper.parentNode.removeChild(wrapper);
  }

  function removePending(wrapper) {
    if (!wrapper || wrapper.dataset.filled === "true") return;
    remove(wrapper);
  }

  function removePendingForTool(bubble, kind, toolCallId) {
    if (!bubble) return;
    let wrapper = null;
    if (toolCallId) {
      wrapper = bubble.querySelector(
        '.ay-content-block[data-tool-call-id="' + toolCallId + '"]'
      );
    }
    if (!wrapper) {
      wrapper = findPlaceholder(bubble, kind, null);
    }
    removePending(wrapper);
  }

  window.AyronContentSkeleton = {
    createPlaceholder: createPlaceholder,
    findPlaceholder: findPlaceholder,
    reveal: reveal,
    remove: remove,
    removePendingForTool: removePendingForTool,
    normalizeChartType: normalizeChartType,
  };
})();
