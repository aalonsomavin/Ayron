(function () {
  var MAX_EXPR_LENGTH = 256;
  var ALLOWED_FUNCTIONS = {
    min: Math.min,
    max: Math.max,
    round: Math.round,
    abs: Math.abs,
  };

  function readJsonScript(el) {
    var script = el.querySelector('script[type="application/json"]');
    if (!script) return null;
    try {
      return JSON.parse(script.textContent || "");
    } catch (_err) {
      return null;
    }
  }

  function tokenizeExpression(expr) {
    var tokens = [];
    var i = 0;
    while (i < expr.length) {
      var ch = expr[i];
      if (/\s/.test(ch)) {
        i += 1;
        continue;
      }
      if (/[0-9.]/.test(ch)) {
        var start = i;
        i += 1;
        while (i < expr.length && /[0-9.]/.test(expr[i])) i += 1;
        tokens.push({ type: "number", value: parseFloat(expr.slice(start, i)) });
        continue;
      }
      if (/[a-zA-Z_]/.test(ch)) {
        var nameStart = i;
        i += 1;
        while (i < expr.length && /[a-zA-Z0-9_]/.test(expr[i])) i += 1;
        var name = expr.slice(nameStart, i);
        if (i < expr.length && expr[i] === "(") {
          tokens.push({ type: "call", name: name });
        } else {
          tokens.push({ type: "ident", name: name });
        }
        continue;
      }
      if ("+-*/(),".indexOf(ch) !== -1) {
        tokens.push({ type: "op", value: ch });
        i += 1;
        continue;
      }
      throw new Error("Invalid character in expression");
    }
    return tokens;
  }

  function parseExpression(tokens, pos) {
    pos = pos || { i: 0 };

    function parsePrimary() {
      var token = tokens[pos.i];
      if (!token) throw new Error("Unexpected end of expression");
      if (token.type === "number") {
        pos.i += 1;
        return token.value;
      }
      if (token.type === "ident") {
        pos.i += 1;
        return { type: "var", name: token.name };
      }
      if (token.type === "call") {
        pos.i += 1;
        if (tokens[pos.i].value !== "(") throw new Error("Expected ( after function");
        pos.i += 1;
        var args = [];
        if (tokens[pos.i] && tokens[pos.i].value !== ")") {
          args.push(parseAddSub());
          while (tokens[pos.i] && tokens[pos.i].value === ",") {
            pos.i += 1;
            args.push(parseAddSub());
          }
        }
        if (!tokens[pos.i] || tokens[pos.i].value !== ")") throw new Error("Expected )");
        pos.i += 1;
        return { type: "call", name: token.name, args: args };
      }
      if (token.type === "op" && token.value === "(") {
        pos.i += 1;
        var inner = parseAddSub();
        if (!tokens[pos.i] || tokens[pos.i].value !== ")") throw new Error("Expected )");
        pos.i += 1;
        return inner;
      }
      if (token.type === "op" && token.value === "-") {
        pos.i += 1;
        return { type: "unary", op: "-", arg: parsePrimary() };
      }
      throw new Error("Unexpected token");
    }

    function parseMulDiv() {
      var node = parsePrimary();
      while (tokens[pos.i] && tokens[pos.i].type === "op" && (tokens[pos.i].value === "*" || tokens[pos.i].value === "/")) {
        var op = tokens[pos.i].value;
        pos.i += 1;
        node = { type: "binary", op: op, left: node, right: parsePrimary() };
      }
      return node;
    }

    function parseAddSub() {
      var node = parseMulDiv();
      while (tokens[pos.i] && tokens[pos.i].type === "op" && (tokens[pos.i].value === "+" || tokens[pos.i].value === "-")) {
        var op = tokens[pos.i].value;
        pos.i += 1;
        node = { type: "binary", op: op, left: node, right: parseMulDiv() };
      }
      return node;
    }

    var ast = parseAddSub();
    if (pos.i !== tokens.length) throw new Error("Unexpected trailing tokens");
    return ast;
  }

  function evalAst(node, scope) {
    if (typeof node === "number") return node;
    if (node.type === "var") {
      if (!Object.prototype.hasOwnProperty.call(scope, node.name)) {
        throw new Error("Unknown variable: " + node.name);
      }
      return scope[node.name];
    }
    if (node.type === "unary") {
      return -evalAst(node.arg, scope);
    }
    if (node.type === "binary") {
      var left = evalAst(node.left, scope);
      var right = evalAst(node.right, scope);
      if (node.op === "+") return left + right;
      if (node.op === "-") return left - right;
      if (node.op === "*") return left * right;
      if (node.op === "/") return right === 0 ? NaN : left / right;
    }
    if (node.type === "call") {
      var fn = ALLOWED_FUNCTIONS[node.name];
      if (!fn) throw new Error("Unknown function: " + node.name);
      var args = node.args.map(function (arg) {
        return evalAst(arg, scope);
      });
      return fn.apply(null, args);
    }
    throw new Error("Invalid AST node");
  }

  function evaluateExpression(expr, scope) {
    if (!expr || typeof expr !== "string") throw new Error("Expression required");
    if (expr.length > MAX_EXPR_LENGTH) throw new Error("Expression too long");
    var tokens = tokenizeExpression(expr.trim());
    var ast = parseExpression(tokens, { i: 0 });
    var value = evalAst(ast, scope || {});
    if (typeof value !== "number" || !Number.isFinite(value)) return NaN;
    return value;
  }

  function formatCalcValue(value, valueFormat) {
    if (typeof value !== "number" || !Number.isFinite(value)) return "—";
    if (valueFormat === "currency") {
      var rounded = Math.round(value);
      return "€" + rounded.toLocaleString("es-ES");
    }
    if (valueFormat === "percent") {
      return (value * 100).toFixed(1) + "%";
    }
    if (Math.abs(value - Math.round(value)) < 1e-9) {
      return Math.round(value).toLocaleString("es-ES");
    }
    return value.toLocaleString("es-ES", { maximumFractionDigits: 2 });
  }

  function resolveTabPanels(tabsEl) {
    var panelsEl = tabsEl.querySelector(":scope > .ay-dash-tab-panels");
    if (panelsEl) return panelsEl;
    var targetSel = tabsEl.getAttribute("data-panels-target");
    if (!targetSel) return null;
    var scopeRoot = tabsEl.closest(".ay-dash-tab-scope") || tabsEl.parentElement;
    return scopeRoot ? scopeRoot.querySelector(targetSel) : null;
  }

  function mountTabs(container) {
    container.querySelectorAll(".ay-dash-tabs").forEach(function (tabsEl) {
      if (tabsEl.dataset.ayDashMounted) return;
      tabsEl.dataset.ayDashMounted = "1";

      var panelsEl = resolveTabPanels(tabsEl);
      if (!panelsEl) return;

      var panels = panelsEl.querySelectorAll(
        ":scope > .ay-dash-tab-panel[data-page]"
      );
      if (!panels.length) return;

      var scopeRoot = tabsEl.closest(".ay-dash-tab-scope") || tabsEl.parentElement;
      var navHost = tabsEl;
      var nav = document.createElement("div");
      nav.className = "ay-dash-tab-nav";
      nav.setAttribute("role", "tablist");

      panels.forEach(function (panel, idx) {
        var pageId = panel.getAttribute("data-page");
        var label = panel.getAttribute("data-label") || pageId;
        var btn = document.createElement("button");
        btn.type = "button";
        btn.className =
          "ay-dash-tab-btn" + (idx === 0 ? " ay-dash-tab-btn--active" : "");
        btn.setAttribute("role", "tab");
        btn.setAttribute("aria-selected", idx === 0 ? "true" : "false");
        btn.setAttribute("data-page", pageId);
        btn.textContent = label;
        nav.appendChild(btn);
        panel.hidden = idx !== 0;
      });

      var externalPanels = panelsEl.parentElement !== tabsEl;
      if (
        externalPanels ||
        tabsEl.classList.contains("ay-dash-tabs--header")
      ) {
        navHost.appendChild(nav);
      } else {
        navHost.insertBefore(nav, panelsEl);
      }

      nav.addEventListener("click", function (event) {
        var btn = event.target.closest(".ay-dash-tab-btn");
        if (!btn) return;
        var pageId = btn.getAttribute("data-page");
        nav.querySelectorAll(".ay-dash-tab-btn").forEach(function (item) {
          var active = item === btn;
          item.classList.toggle("ay-dash-tab-btn--active", active);
          item.setAttribute("aria-selected", active ? "true" : "false");
        });
        panels.forEach(function (panel) {
          panel.hidden = panel.getAttribute("data-page") !== pageId;
        });
        if (window.AyronChart && window.AyronChart.resizeAll) {
          window.AyronChart.resizeAll(scopeRoot || container);
        }
      });
    });
  }

  function applyFilters(filters, root) {
    filters.forEach(function (filter) {
      var select = root.querySelector('[data-filter-id="' + filter.id + '"]');
      if (!select) return;
      var value = select.value;
      var target = root.querySelector(filter.target);
      if (!target) return;
      var attr = filter.attr || "data-filter";
      target.querySelectorAll("tbody tr").forEach(function (row) {
        if (!value || value === "Todas" || value === "All") {
          row.hidden = false;
        } else {
          row.hidden = row.getAttribute(attr) !== value;
        }
      });
    });
  }

  function mountFilters(container) {
    container.querySelectorAll(".ay-dash-filter-bar").forEach(function (barEl) {
      if (barEl.dataset.ayDashMounted) return;
      barEl.dataset.ayDashMounted = "1";

      var config = readJsonScript(barEl);
      if (!config || !config.filters) return;

      var controls = document.createElement("div");
      controls.className = "ay-dash-filter-controls";

      config.filters.forEach(function (filter) {
        var wrap = document.createElement("div");
        wrap.className = "ay-dash-filter";

        var label = document.createElement("label");
        label.className = "ay-dash-filter__label";
        label.textContent = filter.label || filter.id;

        var select = document.createElement("select");
        select.className = "ay-dash-filter__select";
        select.dataset.filterId = filter.id;

        (filter.options || []).forEach(function (optionValue) {
          var option = document.createElement("option");
          option.value = optionValue;
          option.textContent = optionValue;
          select.appendChild(option);
        });

        wrap.appendChild(label);
        wrap.appendChild(select);
        controls.appendChild(wrap);

        select.addEventListener("change", function () {
          applyFilters(config.filters, container);
        });
      });

      barEl.appendChild(controls);
    });
  }

  function parseCellValue(cell, numeric) {
    var text = (cell.textContent || "").trim();
    if (!numeric) return text.toLowerCase();
    var cleaned = text.replace(/[^\d.,\-]/g, "").replace(",", ".");
    var num = parseFloat(cleaned);
    return Number.isNaN(num) ? text.toLowerCase() : num;
  }

  function mountSortableTables(container) {
    container.querySelectorAll("table.ay-dash-table--sortable").forEach(function (table) {
      if (table.dataset.ayDashMounted) return;
      table.dataset.ayDashMounted = "1";

      var thead = table.querySelector("thead");
      if (!thead) return;

      var headers = thead.querySelectorAll("th");
      headers.forEach(function (th, colIdx) {
        th.classList.add("ay-dash-th-sortable");
        th.addEventListener("click", function () {
          var tbody = table.querySelector("tbody");
          if (!tbody) return;

          var ascending = th.dataset.sortDir !== "asc";
          headers.forEach(function (header) {
            delete header.dataset.sortDir;
            header.classList.remove(
              "ay-dash-th-sortable--asc",
              "ay-dash-th-sortable--desc"
            );
          });
          th.dataset.sortDir = ascending ? "asc" : "desc";
          th.classList.add(
            ascending ? "ay-dash-th-sortable--asc" : "ay-dash-th-sortable--desc"
          );

          var numeric = th.classList.contains("ay-dash-th-numeric");
          var rows = Array.from(tbody.querySelectorAll("tr"));
          rows.sort(function (a, b) {
            var aCell = a.children[colIdx];
            var bCell = b.children[colIdx];
            var aVal = parseCellValue(aCell, numeric);
            var bVal = parseCellValue(bCell, numeric);
            if (aVal < bVal) return ascending ? -1 : 1;
            if (aVal > bVal) return ascending ? 1 : -1;
            return 0;
          });
          rows.forEach(function (row) {
            tbody.appendChild(row);
          });
        });
      });
    });
  }

  function rebuildScenarioVars(scenarioVarsByInput) {
    var merged = {};
    Object.keys(scenarioVarsByInput).forEach(function (key) {
      Object.assign(merged, scenarioVarsByInput[key] || {});
    });
    return merged;
  }

  function createCalcField(input, ctx) {
    var field = document.createElement("div");
    field.className = "ay-dash-calc-field";

    var label = document.createElement("label");
    label.className = "ay-dash-calc-label";
    label.textContent = input.label || input.id;

    if (input.type === "select") {
      var select = document.createElement("select");
      select.className = "ay-dash-calc-input ay-dash-calc-select";
      select.dataset.calcInputId = input.id;
      (input.options || []).forEach(function (opt, idx) {
        var option = document.createElement("option");
        option.value = String(idx);
        option.textContent = opt.label || "Option " + (idx + 1);
        select.appendChild(option);
      });
      if ((input.options || []).length) {
        ctx.scenarioVarsByInput[input.id] = Object.assign(
          {},
          (input.options[0].values || {})
        );
      }
      select.addEventListener("change", function () {
        var opt = (input.options || [])[Number(select.value)] || {};
        ctx.scenarioVarsByInput[input.id] = Object.assign({}, opt.values || {});
        ctx.refresh();
      });
      field.appendChild(label);
      field.appendChild(select);
    } else if (input.type === "range") {
      var range = document.createElement("input");
      range.type = "range";
      range.className = "ay-dash-calc-input ay-dash-calc-range";
      range.dataset.calcInputId = input.id;
      if (input.min != null) range.min = input.min;
      if (input.max != null) range.max = input.max;
      if (input.step != null) range.step = input.step;
      range.value = input.default != null ? input.default : range.min || 0;
      ctx.inputValues[input.id] = Number(range.value);
      range.addEventListener("input", function () {
        ctx.inputValues[input.id] = Number(range.value);
        ctx.refresh();
      });
      field.appendChild(label);
      field.appendChild(range);
    } else {
      var numberInput = document.createElement("input");
      numberInput.type = "number";
      numberInput.className = "ay-dash-calc-input ay-dash-calc-number";
      numberInput.dataset.calcInputId = input.id;
      if (input.min != null) numberInput.min = input.min;
      if (input.max != null) numberInput.max = input.max;
      if (input.step != null) numberInput.step = input.step;
      numberInput.value = input.default != null ? input.default : 0;
      ctx.inputValues[input.id] = Number(numberInput.value);
      numberInput.addEventListener("input", function () {
        ctx.inputValues[input.id] = Number(numberInput.value);
        ctx.refresh();
      });
      field.appendChild(label);
      field.appendChild(numberInput);
    }

    return field;
  }

  function buildCalcScope(config, inputValues, scenarioVars) {
    var scope = Object.assign({}, config.constants || {}, scenarioVars || {});
    (config.inputs || []).forEach(function (input) {
      if (input.type === "select") return;
      if (Object.prototype.hasOwnProperty.call(inputValues, input.id)) {
        scope[input.id] = inputValues[input.id];
      } else if (input.default != null) {
        scope[input.id] = Number(input.default);
      }
    });
    return scope;
  }

  function recalculateOutputs(calcEl, config, scope) {
    (config.outputs || []).forEach(function (output) {
      var slot = calcEl.querySelector('[data-calc-output="' + output.id + '"]');
      if (!slot) return;
      var valueEl =
        slot.querySelector(".ay-dash-kpi-value") ||
        slot.querySelector("[data-calc-output-value]");
      if (!valueEl) return;
      var labelEl = slot.querySelector(".ay-dash-kpi-label");
      if (labelEl && output.label && !labelEl.textContent.trim()) {
        labelEl.textContent = output.label;
      }
      var value;
      try {
        value = evaluateExpression(output.expr, scope);
        scope[output.id] = value;
      } catch (_err) {
        value = NaN;
      }
      valueEl.textContent = formatCalcValue(value, output.format || "number");
    });
  }

  function readScopeScripts(scopeEl) {
    var dataset = null;
    var config = null;
    scopeEl.querySelectorAll('script[type="application/json"]').forEach(function (script) {
      try {
        var parsed = JSON.parse(script.textContent || "");
        if (parsed && Array.isArray(parsed.rows)) {
          dataset = parsed;
        } else if (parsed && Array.isArray(parsed.slicers)) {
          config = parsed;
        }
      } catch (_err) {
        return;
      }
    });
    return { dataset: dataset, config: config };
  }

  function parseMeasure(spec) {
    if (!spec) return { fn: "count", field: null };
    var parts = String(spec).split(":");
    return { fn: parts[0], field: parts[1] || null };
  }

  function computeMeasure(rows, measure) {
    if (measure.fn === "sum") {
      return rows.reduce(function (acc, row) {
        return acc + (Number(row[measure.field]) || 0);
      }, 0);
    }
    if (measure.fn === "count_distinct") {
      var seen = {};
      rows.forEach(function (row) {
        seen[String(row[measure.field])] = true;
      });
      return Object.keys(seen).length;
    }
    return rows.length;
  }

  function sortGroupKeys(keys) {
    return keys.slice().sort(function (a, b) {
      var na = Number(a);
      var nb = Number(b);
      if (!Number.isNaN(na) && !Number.isNaN(nb)) return na - nb;
      return String(a).localeCompare(String(b));
    });
  }

  function createFilterScope(rows, slicers) {
    var state = {};
    var listeners = [];
    slicers.forEach(function (s) {
      state[s.id] = [];
    });

    function notify() {
      listeners.forEach(function (fn) {
        fn();
      });
    }

    function rowsFor(excludeDim) {
      return rows.filter(function (row) {
        return slicers.every(function (s) {
          if (s.id === excludeDim) return true;
          var active = state[s.id];
          if (!active.length) return true;
          var val = row[s.field];
          return active.some(function (item) {
            return String(item) === String(val);
          });
        });
      });
    }

    function aggregate(measureSpec, groupByField, excludeDim) {
      var filtered = rowsFor(excludeDim != null ? excludeDim : null);
      if (!groupByField) {
        return computeMeasure(filtered, parseMeasure(measureSpec));
      }
      var groups = {};
      filtered.forEach(function (row) {
        var key = String(row[groupByField]);
        if (!groups[key]) groups[key] = [];
        groups[key].push(row);
      });
      var keys = sortGroupKeys(Object.keys(groups));
      return {
        labels: keys,
        values: keys.map(function (key) {
          return computeMeasure(groups[key], parseMeasure(measureSpec));
        }),
      };
    }

    return {
      slicers: slicers,
      getState: function () {
        return state;
      },
      rowsFor: rowsFor,
      aggregate: aggregate,
      toggle: function (dim, val) {
        if (!Object.prototype.hasOwnProperty.call(state, dim)) return;
        var arr = state[dim].slice();
        var strVal = String(val);
        var idx = arr.findIndex(function (item) {
          return String(item) === strVal;
        });
        if (idx < 0) arr.push(val);
        else arr.splice(idx, 1);
        state[dim] = arr;
        notify();
      },
      clearAll: function () {
        slicers.forEach(function (s) {
          state[s.id] = [];
        });
        notify();
      },
      has: function (dim, val) {
        return (state[dim] || []).some(function (item) {
          return String(item) === String(val);
        });
      },
      onChange: function (fn) {
        listeners.push(fn);
      },
    };
  }

  function uniqueFieldValues(rows, field) {
    var seen = {};
    var values = [];
    rows.forEach(function (row) {
      var val = row[field];
      var key = String(val);
      if (seen[key]) return;
      seen[key] = true;
      values.push(val);
    });
    return sortGroupKeys(values.map(String)).map(function (key) {
      var sample = rows.find(function (row) {
        return String(row[field]) === key;
      });
      return sample ? sample[field] : key;
    });
  }

  function isNumericLikeValues(values) {
    return (
      values.length > 0 &&
      values.every(function (val) {
        return String(val).trim() !== "" && !Number.isNaN(Number(val));
      })
    );
  }

  function slicerUsesDropdown(slicer, values) {
    if (slicer.control === "dropdown") return true;
    if (slicer.control === "pills") return false;
    return !isNumericLikeValues(values);
  }

  function createChevronSvg() {
    var svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("width", "12");
    svg.setAttribute("height", "12");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("fill", "none");
    svg.setAttribute("stroke", "currentColor");
    svg.setAttribute("stroke-width", "2.4");
    svg.setAttribute("stroke-linecap", "round");
    svg.setAttribute("stroke-linejoin", "round");
    svg.setAttribute("class", "ay-dash-slicer-dropdown__chevron");
    var path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", "M6 9l6 6 6-6");
    svg.appendChild(path);
    return svg;
  }

  function createDropdownCheck(checked) {
    var box = document.createElement("span");
    box.className =
      "ay-dash-slicer-dropdown__check" +
      (checked ? " ay-dash-slicer-dropdown__check--on" : "");
    if (checked) {
      var svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      svg.setAttribute("width", "10");
      svg.setAttribute("height", "10");
      svg.setAttribute("viewBox", "0 0 24 24");
      svg.setAttribute("fill", "none");
      svg.setAttribute("stroke", "#fff");
      svg.setAttribute("stroke-width", "3.4");
      svg.setAttribute("stroke-linecap", "round");
      svg.setAttribute("stroke-linejoin", "round");
      var path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      path.setAttribute("d", "M20 6L9 17l-5-5");
      svg.appendChild(path);
      box.appendChild(svg);
    }
    return box;
  }

  function refreshPillSlicer(slicerEl, slicer, scope) {
    slicerEl.querySelectorAll(".ay-dash-slicer__pill").forEach(function (pill) {
      var active = scope.has(slicer.id, pill.dataset.slicerValue || pill.textContent);
      pill.classList.toggle("ay-dash-slicer__pill--active", active);
    });
  }

  function refreshDropdownSlicer(slicerEl, slicer, scope) {
    var state = scope.getState()[slicer.id] || [];
    var trigger = slicerEl.querySelector(".ay-dash-slicer-dropdown__trigger");
    var countEl = slicerEl.querySelector(".ay-dash-slicer-dropdown__count");
    if (trigger) {
      trigger.classList.toggle("ay-dash-slicer-dropdown__trigger--active", state.length > 0);
    }
    if (countEl) {
      countEl.hidden = state.length === 0;
      countEl.textContent = String(state.length);
    }
    slicerEl.querySelectorAll(".ay-dash-slicer-dropdown__item").forEach(function (item) {
      var val = item.dataset.slicerValue;
      var active = scope.has(slicer.id, val);
      item.classList.toggle("ay-dash-slicer-dropdown__item--active", active);
      var check = item.querySelector(".ay-dash-slicer-dropdown__check");
      if (check) {
        var next = createDropdownCheck(active);
        check.replaceWith(next);
      }
    });
  }

  function mountPillSlicer(barEl, scope, slicer, values) {
    var wrap = document.createElement("div");
    wrap.className = "ay-dash-slicer ay-dash-slicer--pills";
    wrap.dataset.slicerId = slicer.id;

    var label = document.createElement("span");
    label.className = "ay-dash-slicer__label";
    label.textContent = slicer.label || slicer.id;
    wrap.appendChild(label);

    var pills = document.createElement("div");
    pills.className = "ay-dash-slicer__pills";

    values.forEach(function (val) {
      var pill = document.createElement("button");
      pill.type = "button";
      pill.className = "ay-dash-slicer__pill";
      pill.dataset.slicerValue = String(val);
      pill.textContent = String(val);
      pill.addEventListener("click", function () {
        scope.toggle(slicer.id, val);
      });
      pills.appendChild(pill);
    });

    wrap.appendChild(pills);
    barEl.appendChild(wrap);

    scope.onChange(function () {
      refreshPillSlicer(wrap, slicer, scope);
    });
    refreshPillSlicer(wrap, slicer, scope);
    return wrap;
  }

  function mountDropdownSlicer(barEl, scope, slicer, values, closeMenus) {
    var wrap = document.createElement("div");
    wrap.className = "ay-dash-slicer ay-dash-slicer--dropdown";
    wrap.dataset.slicerId = slicer.id;

    var trigger = document.createElement("button");
    trigger.type = "button";
    trigger.className = "ay-dash-slicer-dropdown__trigger";

    var triggerLabel = document.createElement("span");
    triggerLabel.className = "ay-dash-slicer-dropdown__trigger-label";
    triggerLabel.textContent = slicer.label || slicer.id;

    var countEl = document.createElement("span");
    countEl.className = "ay-dash-slicer-dropdown__count";
    countEl.hidden = true;

    trigger.appendChild(triggerLabel);
    trigger.appendChild(countEl);
    trigger.appendChild(createChevronSvg());

    var menu = document.createElement("div");
    menu.className = "ay-dash-slicer-dropdown__menu";
    menu.hidden = true;

    values.forEach(function (val) {
      var item = document.createElement("button");
      item.type = "button";
      item.className = "ay-dash-slicer-dropdown__item";
      item.dataset.slicerValue = String(val);
      item.appendChild(createDropdownCheck(scope.has(slicer.id, val)));
      var text = document.createElement("span");
      text.className = "ay-dash-slicer-dropdown__item-label";
      text.textContent = String(val);
      item.appendChild(text);
      item.addEventListener("click", function (event) {
        event.stopPropagation();
        scope.toggle(slicer.id, val);
      });
      menu.appendChild(item);
    });

    trigger.addEventListener("click", function (event) {
      event.stopPropagation();
      var wasOpen = !menu.hidden;
      closeMenus();
      if (!wasOpen) {
        menu.hidden = false;
        trigger.classList.add("ay-dash-slicer-dropdown__trigger--open");
      }
    });

    wrap.appendChild(trigger);
    wrap.appendChild(menu);
    barEl.appendChild(wrap);

    scope.onChange(function () {
      refreshDropdownSlicer(wrap, slicer, scope);
    });
    refreshDropdownSlicer(wrap, slicer, scope);
    return wrap;
  }

  function mountSlicerBar(scopeEl, scope) {
    var barEl = scopeEl.querySelector(".ay-dash-slicer-bar");
    if (!barEl || barEl.dataset.ayDashMounted) return;
    barEl.dataset.ayDashMounted = "1";
    barEl.innerHTML = "";

    function closeMenus() {
      barEl.querySelectorAll(".ay-dash-slicer-dropdown__menu").forEach(function (menu) {
        menu.hidden = true;
      });
      barEl.querySelectorAll(".ay-dash-slicer-dropdown__trigger").forEach(function (trigger) {
        trigger.classList.remove("ay-dash-slicer-dropdown__trigger--open");
      });
    }

    if (!barEl.dataset.ayDashDropdownListener) {
      barEl.dataset.ayDashDropdownListener = "1";
      document.addEventListener("click", function () {
        closeMenus();
      });
    }

    var sawPills = false;
    var sawDropdown = false;

    scope.slicers.forEach(function (slicer) {
      var values = uniqueFieldValues(scope.rowsFor(slicer.id), slicer.field);
      var useDropdown = slicerUsesDropdown(slicer, values);

      if (useDropdown && sawPills && !sawDropdown) {
        var divider = document.createElement("span");
        divider.className = "ay-dash-slicer-bar__divider";
        divider.setAttribute("aria-hidden", "true");
        barEl.appendChild(divider);
      }

      if (useDropdown) {
        mountDropdownSlicer(barEl, scope, slicer, values, closeMenus);
        sawDropdown = true;
      } else {
        mountPillSlicer(barEl, scope, slicer, values);
        sawPills = true;
      }
    });
  }

  function mountFilterChips(scopeEl, scope) {
    var chipsEl = scopeEl.querySelector(".ay-dash-filter-chips");
    if (!chipsEl || chipsEl.dataset.ayDashMounted) return;
    chipsEl.dataset.ayDashMounted = "1";

    function render() {
      chipsEl.innerHTML = "";
      var state = scope.getState();
      var chips = [];
      scope.slicers.forEach(function (slicer) {
        (state[slicer.id] || []).forEach(function (val) {
          chips.push({ dim: slicer.id, label: slicer.label || slicer.id, val: val });
        });
      });

      if (!chips.length) {
        var empty = document.createElement("span");
        empty.className = "ay-dash-filter-chips__empty";
        empty.textContent = "Sin filtros · mostrando todo";
        chipsEl.appendChild(empty);
        return;
      }

      chips.forEach(function (chip) {
        var btn = document.createElement("button");
        btn.type = "button";
        btn.className = "ay-dash-filter-chip";
        btn.textContent = chip.label + ": " + String(chip.val);
        btn.addEventListener("click", function () {
          scope.toggle(chip.dim, chip.val);
        });
        chipsEl.appendChild(btn);
      });

      var clearBtn = document.createElement("button");
      clearBtn.type = "button";
      clearBtn.className = "ay-dash-filter-chip ay-dash-filter-chip__clear";
      clearBtn.textContent = "Limpiar";
      clearBtn.addEventListener("click", function () {
        scope.clearAll();
      });
      chipsEl.appendChild(clearBtn);
    }

    scope.onChange(render);
    render();
  }

  function mountScopeTables(scopeEl, scope) {
    scopeEl.querySelectorAll("table.ay-dash-table tbody").forEach(function (tbody) {
      if (tbody.dataset.ayDashScopeTable) return;
      tbody.dataset.ayDashScopeTable = "1";
      scope.onChange(function () {
        tbody.querySelectorAll("tr").forEach(function (row) {
          var visible = scope.slicers.every(function (slicer) {
            var active = scope.getState()[slicer.id];
            if (!active.length) return true;
            var attr = "data-" + slicer.field;
            var rowVal = row.getAttribute(attr);
            return active.some(function (item) {
              return String(item) === String(rowVal);
            });
          });
          row.hidden = !visible;
        });
      });
      tbody.querySelectorAll("tr").forEach(function (row) {
        row.hidden = false;
      });
    });
  }

  function mountLiveKpis(scopeEl, scope) {
    scopeEl.querySelectorAll(".ay-dash-kpi-live").forEach(function (kpiEl) {
      if (kpiEl.dataset.ayDashMounted) return;
      kpiEl.dataset.ayDashMounted = "1";
      var agg = kpiEl.getAttribute("data-agg");
      var valueFormat = kpiEl.getAttribute("data-format") || "number";
      var valueEl = kpiEl.querySelector(".ay-dash-kpi-value");
      if (!valueEl || !agg) return;

      scope.onChange(function () {
        var value = scope.aggregate(agg, null, null);
        valueEl.textContent = formatCalcValue(value, valueFormat);
      });
      var initial = scope.aggregate(agg, null, null);
      valueEl.textContent = formatCalcValue(initial, valueFormat);
    });
  }

  function mountFilterScopes(container) {
    container.querySelectorAll(".ay-dash-filter-scope").forEach(function (scopeEl) {
      if (scopeEl.dataset.ayDashMounted) return;
      var scripts = readScopeScripts(scopeEl);
      if (!scripts.dataset || !scripts.config) return;
      scopeEl.dataset.ayDashMounted = "1";

      var rows = scripts.dataset.rows || [];
      var slicers = scripts.config.slicers || [];
      if (!slicers.length) return;

      var scope = createFilterScope(rows, slicers);
      mountSlicerBar(scopeEl, scope);
      mountFilterChips(scopeEl, scope);
      mountScopeTables(scopeEl, scope);
      mountLiveKpis(scopeEl, scope);

      if (window.AyronChart && window.AyronChart.mountLive) {
        scopeEl.querySelectorAll(".ay-chart--live").forEach(function (chartEl) {
          window.AyronChart.mountLive(scope, chartEl);
        });
      }

      scope.onChange(function () {
        if (window.AyronChart && window.AyronChart.resizeAll) {
          window.AyronChart.resizeAll(scopeEl);
        }
      });
    });
  }

  function mountCalculators(container) {
    container.querySelectorAll(".ay-dash-calculator").forEach(function (calcEl) {
      if (calcEl.dataset.ayDashMounted) return;
      calcEl.dataset.ayDashMounted = "1";

      var config = readJsonScript(calcEl);
      if (!config) return;

      var controlsHost = calcEl.querySelector(".ay-dash-calculator__controls");
      var controlsWrap = document.createElement("div");
      controlsWrap.className = "ay-dash-calculator__controls-inner";

      var inputValues = {};
      var scenarioVarsByInput = {};

      function refresh() {
        var scenarioVars = rebuildScenarioVars(scenarioVarsByInput);
        var scope = buildCalcScope(config, inputValues, scenarioVars);
        recalculateOutputs(calcEl, config, scope);
      }

      var ctx = {
        inputValues: inputValues,
        scenarioVarsByInput: scenarioVarsByInput,
        refresh: refresh,
      };

      (config.inputs || []).forEach(function (input) {
        var slot = calcEl.querySelector('[data-calc-input="' + input.id + '"]');
        var field = createCalcField(input, ctx);
        if (slot) {
          var mountTarget = slot;
          var card = slot.querySelector(".ay-dash-card");
          if (card) {
            card.innerHTML = "";
            card.classList.add("ay-dash-card--calc-input");
            mountTarget = card;
          } else {
            slot.innerHTML = "";
            slot.classList.add("ay-dash-card", "ay-dash-card--calc-input");
          }
          mountTarget.classList.add("ay-dash-calc-slot");
          mountTarget.appendChild(field);
        } else {
          controlsWrap.appendChild(field);
        }
      });

      if (controlsWrap.childNodes.length) {
        if (controlsHost) {
          controlsHost.hidden = false;
          controlsHost.innerHTML = "";
          controlsHost.appendChild(controlsWrap);
        } else {
          controlsWrap.classList.add("ay-dash-calculator__controls-fallback");
          var scriptEl = calcEl.querySelector('script[type="application/json"]');
          if (scriptEl && scriptEl.nextSibling) {
            calcEl.insertBefore(controlsWrap, scriptEl.nextSibling);
          } else {
            calcEl.insertBefore(controlsWrap, calcEl.firstChild);
          }
        }
      } else if (controlsHost) {
        controlsHost.hidden = true;
      }

      refresh();
    });
  }

  window.AyronDashboard = {
    mountAll: function (container) {
      container = container || document;
      mountTabs(container);
      mountFilters(container);
      mountFilterScopes(container);
      mountSortableTables(container);
      mountCalculators(container);
    },
    evaluateExpression: evaluateExpression,
    formatCalcValue: formatCalcValue,
    createFilterScope: createFilterScope,
  };
})();
