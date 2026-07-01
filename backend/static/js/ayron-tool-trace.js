(function () {
  var VISIBLE_STEP_LIMIT = 5;

  var ICONS = {
    database:
      '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/><path d="M3 12c0 1.66 4 3 9 3s9-1.34 9-3"/></svg>',
    terminal:
      '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="4 17 10 11 4 5"/><line x1="12" x2="20" y1="19" y2="19"/></svg>',
    "file-doc":
      '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 13h4"/><path d="M10 17h4"/></svg>',
    "file-sheet":
      '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M8 13h2"/><path d="M14 13h2"/><path d="M8 17h2"/><path d="M14 17h2"/></svg>',
    chart:
      '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 3v18h18"/><path d="M7 16v-5"/><path d="M12 16V8"/><path d="M17 16v-9"/></svg>',
    code:
      '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>',
    "list-checks":
      '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M11 6h9"/><path d="M11 12h9"/><path d="M11 18h9"/><path d="M4 6h1"/><path d="M4 12h1"/><path d="M4 18h1"/></svg>',
    "check-circle":
      '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/></svg>',
    file:
      '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/></svg>',
  };

  function iconHtml(name) {
    return ICONS[name] || ICONS.file;
  }

  function populateItemIcon(item) {
    var iconEl = item.querySelector(".ay-tool-trace__icon");
    if (!iconEl || iconEl.dataset.populated === "true") return;
    iconEl.innerHTML = iconHtml(item.dataset.icon || "file");
    iconEl.dataset.populated = "true";
  }

  function populateTraceIcons(trace) {
    if (!trace) return;
    trace.querySelectorAll(".ay-tool-trace__item").forEach(populateItemIcon);
  }

  function buildItemHtml(options) {
    var tagHtml = options.tag
      ? '<span class="ay-tool-trace__tag">' + escapeHtml(options.tag) + "</span>"
      : "";
    var detailHtml = options.detail
      ? '<span class="ay-tool-trace__detail">' + escapeHtml(options.detail) + "</span>"
      : "";
    return (
      '<span class="ay-tool-trace__icon"></span>' +
      '<div class="ay-tool-trace__body">' +
        '<span class="ay-tool-trace__verb"></span>' +
        tagHtml +
        detailHtml +
      "</div>"
    );
  }

  function escapeHtml(text) {
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function stepItems(trace) {
    return Array.prototype.filter.call(
      trace.querySelectorAll(".ay-tool-trace__item"),
      function (item) {
        return item.dataset.tool !== "done";
      }
    );
  }

  function hiddenStepCount(trace) {
    var count = stepItems(trace).length;
    return Math.max(0, count - VISIBLE_STEP_LIMIT);
  }

  function ensureExpandStepsButton(trace) {
    var button = trace.querySelector(".ay-tool-trace__expand-steps");
    if (!button) {
      button = document.createElement("button");
      button.type = "button";
      button.className = "ay-tool-trace__expand-steps";
      trace.appendChild(button);
    }
    return button;
  }

  function expandStepsLabel(count) {
    return count === 1 ? "Ver 1 paso más" : "Ver " + count + " pasos más";
  }

  function syncStepVisibility(trace) {
    if (!trace) return;

    var items = stepItems(trace);
    var hiddenCount = hiddenStepCount(trace);
    var button = ensureExpandStepsButton(trace);

    items.forEach(function (item, index) {
      var overflow = index >= VISIBLE_STEP_LIMIT;
      item.classList.toggle("ay-tool-trace__item--overflow", overflow);
      if (overflow && item.classList.contains("is-running")) {
        item.classList.remove("ay-tool-trace__item--overflow");
      }
    });

    if (hiddenCount === 0) {
      trace.classList.remove("is-steps-collapsed");
      button.hidden = true;
      return;
    }

    button.hidden = false;
    var expanded = button.getAttribute("aria-expanded") === "true";
    trace.classList.toggle("is-steps-collapsed", !expanded);
    if (expanded) {
      button.textContent = "Ver menos";
    } else {
      button.textContent = expandStepsLabel(hiddenCount);
    }
  }

  function initStepExpand(trace) {
    if (!trace || trace.dataset.stepsToggleBound === "true") return;
    trace.dataset.stepsToggleBound = "true";

    var button = ensureExpandStepsButton(trace);
    button.addEventListener("click", function () {
      var hiddenCount = hiddenStepCount(trace);
      if (hiddenCount === 0) return;

      var expanded = button.getAttribute("aria-expanded") === "true";
      expanded = !expanded;
      button.setAttribute("aria-expanded", expanded ? "true" : "false");
      trace.classList.toggle("is-steps-collapsed", !expanded);
      button.textContent = expanded ? "Ver menos" : expandStepsLabel(hiddenCount);
    });

    if (!button.hasAttribute("aria-expanded")) {
      button.setAttribute("aria-expanded", "false");
    }
    syncStepVisibility(trace);
  }

  function isSqlTraceItem(item) {
    return (
      item &&
      item.dataset.tool === "run_sql_query" &&
      item.dataset.toolCallId &&
      item.dataset.toolCallId !== "done"
    );
  }

  function markSqlTraceItem(item) {
    if (!isSqlTraceItem(item)) return;
    item.classList.add("ay-tool-trace__item--sql");
    item.setAttribute("role", "button");
    item.setAttribute("tabindex", "0");
    item.setAttribute("title", "Ver origen de los datos");
  }

  function markSqlTraceItems(root) {
    (root || document).querySelectorAll(".ay-tool-trace__item").forEach(markSqlTraceItem);
  }

  function provenanceDataAccessUrl(toolCallId) {
    var shell = document.getElementById("ay-shell");
    var baseUrl = shell && shell.dataset.provenanceDataAccessUrl;
    if (!baseUrl || !toolCallId) return "";
    return baseUrl + "?tool_call_id=" + encodeURIComponent(toolCallId);
  }

  function ensureProvenanceDialog() {
    var dialog = document.getElementById("ay-provenance-sql-dialog");
    if (!dialog) {
      dialog = document.createElement("dialog");
      dialog.id = "ay-provenance-sql-dialog";
      dialog.className = "ay-provenance-sql-dialog";
      dialog.innerHTML =
        '<div id="ay-provenance-sql-content" class="ay-provenance-sql-dialog__content"></div>';
      document.body.appendChild(dialog);
    }
    return dialog;
  }

  function closeProvenanceDialog() {
    var dialog = document.getElementById("ay-provenance-sql-dialog");
    if (dialog) dialog.close();
  }

  function bindProvenanceDialogActions(contentEl) {
    var closeBtn = contentEl.querySelector("[data-provenance-close]");
    if (closeBtn) {
      closeBtn.addEventListener("click", closeProvenanceDialog);
    }

    var askBtn = contentEl.querySelector("[data-provenance-ask]");
    if (askBtn) {
      askBtn.addEventListener("click", function () {
        var message = askBtn.getAttribute("data-ask-message") || "";
        var contextRaw = askBtn.getAttribute("data-provenance-context") || "";
        var context = null;
        if (contextRaw) {
          try {
            context = JSON.parse(contextRaw);
          } catch (err) {
            return;
          }
        }
        if (!window.AyronChat || !window.AyronChat.submitMessage) return;
        var sent = window.AyronChat.submitMessage(message, context);
        if (sent) closeProvenanceDialog();
      });
    }
  }

  function openProvenanceHtmlModal(url) {
    if (!url) return;

    var dialog = ensureProvenanceDialog();
    var contentEl = document.getElementById("ay-provenance-sql-content");
    contentEl.innerHTML = '<div class="ay-provenance-sql__loading">Cargando…</div>';

    if (!dialog.open) dialog.showModal();

    dialog.onclick = function (event) {
      if (event.target === dialog) closeProvenanceDialog();
    };

    fetch(url, { headers: { Accept: "text/html" }, credentials: "same-origin" })
      .then(function (response) {
        if (!response.ok) throw new Error("not found");
        return response.text();
      })
      .then(function (html) {
        contentEl.innerHTML = html;
        bindProvenanceDialogActions(contentEl);
      })
      .catch(function () {
        contentEl.innerHTML =
          '<div class="ay-provenance-sql__error">No se encontró el detalle de esta consulta.</div>';
      });
  }

  function openProvenanceSqlModal(toolCallId) {
    openProvenanceHtmlModal(provenanceDataAccessUrl(toolCallId));
  }

  function handleSqlTraceActivate(event) {
    var item = event.target.closest(".ay-tool-trace__item--sql");
    if (!item || !isSqlTraceItem(item)) return;
    if (event.type === "keydown" && event.key !== "Enter" && event.key !== " ") return;
    if (event.type === "keydown") event.preventDefault();
    openProvenanceSqlModal(item.dataset.toolCallId);
  }

  function initSqlProvenance(root) {
    if (document.documentElement.dataset.provenanceBound === "true") return;
    document.documentElement.dataset.provenanceBound = "true";

    markSqlTraceItems(root);

    document.addEventListener("click", function (event) {
      if (event.target.closest(".ay-tool-trace__toggle, .ay-tool-trace__expand-steps")) return;
      handleSqlTraceActivate(event);
    });

    document.addEventListener("keydown", function (event) {
      handleSqlTraceActivate(event);
    });
  }

  function initTrace(trace) {
    populateTraceIcons(trace);
    initStepExpand(trace);
    markSqlTraceItems(trace);
  }

  window.AyronToolTrace = {
    VISIBLE_STEP_LIMIT: VISIBLE_STEP_LIMIT,
    iconHtml: iconHtml,
    populateItemIcon: populateItemIcon,
    populateTraceIcons: populateTraceIcons,
    buildItemHtml: buildItemHtml,
    syncStepVisibility: syncStepVisibility,
    initStepExpand: initStepExpand,
    initTrace: initTrace,
    markSqlTraceItem: markSqlTraceItem,
    initSqlProvenance: initSqlProvenance,
    openProvenanceHtmlModal: openProvenanceHtmlModal,
    openProvenanceSqlModal: openProvenanceSqlModal,
    closeProvenanceDialog: closeProvenanceDialog,
  };
})();
