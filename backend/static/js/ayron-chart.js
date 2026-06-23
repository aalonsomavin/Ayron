(function () {
  const instances = new WeakMap();

  function cssVar(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }

  function chartColors() {
    const colors = [];
    for (let i = 1; i <= 8; i += 1) {
      colors.push(cssVar("--ay-chart-" + i) || "#3b6ef6");
    }
    return colors;
  }

  function formatCurrencyAmount(value) {
    var num = Number(value);
    if (Number.isNaN(num)) return String(value);
    return "$" + Math.round(num).toLocaleString("es-MX");
  }

  function formatValue(value, valueFormat) {
    const num = Number(value);
    if (Number.isNaN(num)) return String(value);
    if (valueFormat === "currency") {
      return formatCurrencyAmount(num);
    }
    if (valueFormat === "percent") {
      return num.toFixed(1) + "%";
    }
    if (Math.abs(num - Math.round(num)) < 1e-9) {
      return Math.round(num).toLocaleString("es-MX");
    }
    return num.toLocaleString("es-MX", { maximumFractionDigits: 2 });
  }

  function datasetColors(chart, dataset, palette) {
    if (chart.chart_type === "pie") {
      const indices =
        dataset.color_indices ||
        (dataset.data || []).map(function (_value, i) {
          return i;
        });
      return indices.map(function (idx) {
        return palette[idx % palette.length];
      });
    }
    const idx = dataset.color_index != null ? dataset.color_index : 0;
    return palette[idx % palette.length];
  }

  function hexWithAlpha(hex, alpha) {
    if (!hex || hex.charAt(0) !== "#") return hex;
    var h = hex.slice(1);
    if (h.length === 3) {
      h = h
        .split("")
        .map(function (c) {
          return c + c;
        })
        .join("");
    }
    var r = parseInt(h.slice(0, 2), 16);
    var g = parseInt(h.slice(2, 4), 16);
    var b = parseInt(h.slice(4, 6), 16);
    return "rgba(" + r + "," + g + "," + b + "," + alpha + ")";
  }

  function buildChartConfig(chart, liveOpts) {
    const palette = chartColors();
    const valueFormat = chart.value_format || "number";
    const currencyLabel = chart.currency_label || "";
    const textMuted = cssVar("--ay-text-muted") || "#8a8a92";
    const borderSubtle = cssVar("--ay-border-subtle") || "#ededee";
    const fontSans = cssVar("--ay-font-sans") || "Geist, sans-serif";
    const fontMono = cssVar("--ay-font-mono") || "Geist Mono, monospace";
    const chartType = chart.chart_type || "bar";

    const datasets = (chart.datasets || []).map(function (dataset) {
      const color = datasetColors(chart, dataset, palette);
      const entry = {
        label: dataset.label,
        data: dataset.data,
      };
      if (chartType === "pie") {
        entry.backgroundColor = color;
        entry.borderWidth = 0;
      } else if (chartType === "line") {
        entry.borderColor = color;
        entry.backgroundColor = color;
        entry.pointBackgroundColor = color;
        entry.pointRadius = 3;
        entry.pointHoverRadius = 4;
        entry.borderWidth = 2;
        entry.tension = 0.3;
        entry.fill = false;
      } else {
        if (Array.isArray(dataset.backgroundColors)) {
          entry.backgroundColor = dataset.backgroundColors;
        } else {
          entry.backgroundColor = color;
        }
        entry.borderRadius = 3;
        entry.maxBarThickness = 18;
        if (Array.isArray(dataset.borderColors)) {
          entry.borderColor = dataset.borderColors;
          entry.borderWidth = dataset.borderWidth != null ? dataset.borderWidth : 2;
        }
      }
      return entry;
    });

    const scales =
      chartType === "pie"
        ? {}
        : {
            x: {
              grid: { display: false },
              ticks: {
                color: textMuted,
                font: { family: fontSans, size: 11 },
                maxRotation: 0,
                autoSkip: true,
              },
              border: { color: borderSubtle },
            },
            y: {
              grid: { color: borderSubtle },
              title: currencyLabel && valueFormat === "currency"
                ? {
                    display: true,
                    text: currencyLabel,
                    color: textMuted,
                    font: { family: fontSans, size: 11 },
                  }
                : undefined,
              ticks: {
                color: textMuted,
                font: { family: fontMono, size: 11 },
                callback: function (value) {
                  return formatValue(value, valueFormat);
                },
              },
              border: { display: false },
            },
          };

    const options = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: chartType === "pie" || datasets.length > 1,
            position: "bottom",
            labels: {
              color: textMuted,
              font: { family: fontSans, size: 12 },
              boxWidth: 8,
              boxHeight: 8,
              usePointStyle: true,
              pointStyle: "rectRounded",
            },
          },
          tooltip: {
            callbacks: {
              label: function (context) {
                const label = context.dataset.label || "";
                const value = context.parsed.y != null ? context.parsed.y : context.parsed;
                const formatted = formatValue(value, valueFormat);
                if (chartType === "pie") {
                  return (context.label || label) + ": " + formatted;
                }
                return label ? label + ": " + formatted : formatted;
              },
            },
          },
        },
        scales: scales,
      };

    if (liveOpts && liveOpts.crossFilter && chartType !== "pie") {
      options.onClick = function (_evt, elements) {
        if (!elements.length || !liveOpts.scope) return;
        const idx = elements[0].index;
        const label = (chart.labels || [])[idx];
        if (label == null) return;
        liveOpts.scope.toggle(liveOpts.crossFilter, label);
      };
    }

    return {
      type: chartType,
      data: {
        labels: chart.labels || [],
        datasets: datasets,
      },
      options: options,
    };
  }

  function createChart(canvas, chart, liveOpts) {
    if (typeof Chart === "undefined") return null;
    const config = buildChartConfig(chart, liveOpts);
    return new Chart(canvas, config);
  }

  function readPayload(node) {
    const scriptId = node.dataset.chartId;
    if (!scriptId) return null;
    const script = document.getElementById(scriptId);
    if (!script) return null;
    try {
      return JSON.parse(script.textContent);
    } catch (_err) {
      return null;
    }
  }

  function destroyChart(node) {
    const instance = instances.get(node);
    if (instance) {
      instance.destroy();
      instances.delete(node);
    }
  }

  function buildElement(chart) {
    const wrapper = document.createElement("div");
    wrapper.className = "ay-chart";
    const chartId = "chart-stream-" + Date.now() + "-" + Math.random().toString(36).slice(2, 8);
    wrapper.dataset.chartId = chartId;

    const script = document.createElement("script");
    script.type = "application/json";
    script.id = chartId;
    script.textContent = JSON.stringify(chart);
    wrapper.appendChild(script);

    const card = document.createElement("div");
    card.className = "ay-card ay-chart__card";

    if (chart.title) {
      const title = document.createElement("div");
      title.className = "ay-chart__title";
      title.textContent = chart.title;
      card.appendChild(title);
    }

    const plot = document.createElement("div");
    plot.className = "ay-chart__plot";
    const canvas = document.createElement("canvas");
    canvas.className = "ay-chart__canvas";
    plot.appendChild(canvas);
    card.appendChild(plot);

    if (chart.caption) {
      const caption = document.createElement("div");
      caption.className = "ay-chart__caption";
      caption.textContent = chart.caption;
      card.appendChild(caption);
    }

    wrapper.appendChild(card);
    return wrapper;
  }

  function scheduleResize(instance) {
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        instance.resize();
      });
    });
  }

  function update(node, chart, liveOpts) {
    const instance = instances.get(node);
    if (!instance) return;
    const config = buildChartConfig(chart, liveOpts);
    instance.config.type = config.type;
    instance.data.labels = config.data.labels;
    instance.data.datasets = config.data.datasets;
    instance.options = config.options;
    instance.update("none");
  }

  function buildLivePayload(scope, node) {
    const dimension = node.dataset.dimension;
    const measure = node.dataset.measure;
    const crossFilter = node.dataset.crossFilter || dimension;
    const meta = readPayload(node) || {};
    const aggregated = scope.aggregate(measure, dimension, dimension);
    const labels = aggregated.labels || [];
    const values = aggregated.values || [];
    const palette = chartColors();
    const colorIdx =
      meta.datasets && meta.datasets[0] && meta.datasets[0].color_index != null
        ? meta.datasets[0].color_index
        : 0;
    const baseColor = palette[colorIdx % palette.length];
    const dimState = scope.getState()[crossFilter] || [];
    const hasActive = dimState.length > 0;
    const backgroundColors = labels.map(function (label) {
      if (!hasActive || scope.has(crossFilter, label)) return baseColor;
      return hexWithAlpha(baseColor, 0.28);
    });
    const borderColors = labels.map(function (label) {
      if (!hasActive || scope.has(crossFilter, label)) return baseColor;
      return hexWithAlpha(baseColor, 0.28);
    });

    return {
      chart_type: meta.chart_type || "bar",
      title: meta.title,
      caption: meta.caption,
      value_format: meta.value_format || "number",
      currency_label: meta.currency_label || "",
      labels: labels,
      datasets: [
        {
          label:
            meta.datasets && meta.datasets[0] && meta.datasets[0].label
              ? meta.datasets[0].label
              : measure,
          data: values,
          color_index: colorIdx,
          backgroundColors: backgroundColors,
          borderColors: borderColors,
          borderWidth: hasActive ? 2 : 0,
        },
      ],
    };
  }

  function mountLive(scope, node) {
    if (!node || node.dataset.ayChartLiveMounted) return;
    node.dataset.ayChartLiveMounted = "1";
    const crossFilter = node.dataset.crossFilter || node.dataset.dimension;
    const liveOpts = { scope: scope, crossFilter: crossFilter };

    function refresh() {
      const payload = buildLivePayload(scope, node);
      const canvas = node.querySelector(".ay-chart__canvas");
      if (!canvas) return;
      const instance = instances.get(node);
      if (instance) {
        update(node, payload, liveOpts);
      } else {
        const created = createChart(canvas, payload, liveOpts);
        if (created) {
          instances.set(node, created);
          scheduleResize(created);
        }
      }
    }

    scope.onChange(refresh);
    refresh();
  }

  function mount(node) {
    if (!node) return;
    const existing = instances.get(node);
    if (existing) {
      scheduleResize(existing);
      return;
    }
    const chart = readPayload(node);
    const canvas = node.querySelector(".ay-chart__canvas");
    if (!chart || !canvas) return;
    const instance = createChart(canvas, chart);
    if (instance) {
      instances.set(node, instance);
      scheduleResize(instance);
    }
  }

  function mountAll(root) {
    (root || document).querySelectorAll(".ay-chart:not(.ay-chart--live)").forEach(mount);
  }

  function resizeAll(root) {
    (root || document).querySelectorAll(".ay-chart").forEach(function (node) {
      const instance = instances.get(node);
      if (instance) scheduleResize(instance);
      else if (!node.classList.contains("ay-chart--live")) mount(node);
    });
  }

  function destroyAll(root) {
    (root || document).querySelectorAll(".ay-chart").forEach(destroyChart);
  }

  function render(chart) {
    const wrapper = buildElement(chart);
    mount(wrapper);
    return wrapper;
  }

  window.AyronChart = {
    create: buildElement,
    render: render,
    mount: mount,
    mountLive: mountLive,
    mountAll: mountAll,
    update: update,
    resizeAll: resizeAll,
    destroyAll: destroyAll,
    buildLivePayload: buildLivePayload,
  };
})();
