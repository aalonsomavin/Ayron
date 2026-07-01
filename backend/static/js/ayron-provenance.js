(function () {
  function escapeHtml(text) {
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function formatDate(iso) {
    if (!iso) return "";
    var date = new Date(iso);
    if (isNaN(date.getTime())) return "";
    return date.toLocaleString("es-MX", {
      day: "numeric",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function formatDefKey(key) {
    var labels = {
      metric: "Métrica",
      dataset_ref: "Dataset",
      base_filters: "Filtros base",
      filters: "Filtros",
      aggregation: "Agregación",
      time_window: "Ventana temporal",
      column: "Columna",
      table: "Tabla",
    };
    var normalized = String(key).toLowerCase().replace(/-/g, "_");
    if (labels[normalized]) return labels[normalized];
    return String(key)
      .replace(/_/g, " ")
      .replace(/\b\w/g, function (char) {
        return char.toUpperCase();
      });
  }

  function defValueClass(key, value) {
    var normalized = String(key).toLowerCase().replace(/-/g, "_");
    var text = String(value);
    if (
      normalized === "metric" ||
      normalized === "dataset_ref" ||
      /^(SELECT|SUM|COUNT|AVG|MAX|MIN)\b/i.test(text) ||
      /^embedded:/.test(text)
    ) {
      return " ay-provenance-panel__def-value--mono";
    }
    return "";
  }

  function definitionHtml(definition) {
    if (!definition || typeof definition !== "object") return "";
    var rows = [];
    Object.keys(definition).forEach(function (key) {
      var value = definition[key];
      if (value === null || value === undefined || value === "") return;
      rows.push(
        '<dt class="ay-provenance-panel__def-key">' +
          escapeHtml(formatDefKey(key)) +
          "</dt>" +
          '<dd class="ay-provenance-panel__def-value' +
          defValueClass(key, value) +
          '">' +
          escapeHtml(String(value)) +
          "</dd>"
      );
    });
    if (!rows.length) return "";
    return (
      '<dl class="ay-provenance-panel__definition">' + rows.join("") + "</dl>"
    );
  }

  function accessMetaHtml(access) {
    if (!access) return "";
    var chips = [];
    if (access.tables && access.tables.length) {
      chips.push(
        '<span class="ay-provenance-panel__meta-chip">' +
          '<span class="ay-provenance-panel__meta-chip-label">Tablas</span> ' +
          escapeHtml(access.tables.join(", ")) +
          "</span>"
      );
    }
    if (access.sheets && access.sheets.length) {
      chips.push(
        '<span class="ay-provenance-panel__meta-chip">' +
          '<span class="ay-provenance-panel__meta-chip-label">Hojas</span> ' +
          escapeHtml(access.sheets.join(", ")) +
          "</span>"
      );
    }
    if (access.columns && access.columns.length) {
      chips.push(
        '<span class="ay-provenance-panel__meta-chip">' +
          '<span class="ay-provenance-panel__meta-chip-label">Columnas</span> ' +
          escapeHtml(access.columns.join(", ")) +
          "</span>"
      );
    }
    if (access.row_count !== null && access.row_count !== undefined) {
      chips.push(
        '<span class="ay-provenance-panel__meta-chip">' +
          escapeHtml(
            String(access.row_count) +
              (access.row_count === 1 ? " fila" : " filas") +
              (access.truncated ? " · truncado" : "")
          ) +
          "</span>"
      );
    }
    if (access.executed_at) {
      chips.push(
        '<span class="ay-provenance-panel__meta-chip ay-provenance-panel__meta-chip--muted">' +
          "Ejecutada " +
          escapeHtml(formatDate(access.executed_at)) +
          "</span>"
      );
    }
    if (!chips.length) return "";
    return (
      '<div class="ay-provenance-panel__meta">' + chips.join("") + "</div>"
    );
  }

  function primaryAccess(payload) {
    if (payload.data_accesses && payload.data_accesses.length) {
      return payload.data_accesses[0];
    }
    return null;
  }

  function renderPanelContent(payload) {
    var claim = payload.claim || {};
    var access = primaryAccess(payload);
    var source = payload.source || (access && access.integration) || null;
    var parts = [];

    parts.push(
      '<div class="ay-provenance-panel__claim-card">' +
        '<div class="ay-provenance-panel__claim-label">' +
        escapeHtml(claim.label || claim.claim_key || "Dato") +
        "</div>" +
        definitionHtml(claim.definition) +
      "</div>"
    );

    if (payload.transformation) {
      parts.push(
        '<div class="ay-provenance-panel__section">' +
          '<div class="ay-provenance-panel__section-label">Transformación</div>' +
          '<p class="ay-provenance-panel__text ay-provenance-panel__text--mono">' +
          escapeHtml(payload.transformation) +
          "</p>" +
        "</div>"
      );
    }

    if (access && access.access_kind === "sql" && access.sql) {
      parts.push(
        '<div class="ay-provenance-panel__section ay-provenance-panel__section--sql">' +
          '<div class="ay-provenance-panel__section-label">Consulta SQL</div>' +
          '<div class="ay-provenance-panel__sql-wrap">' +
            '<div class="ay-provenance-panel__sql-toolbar">' +
              '<button type="button" class="ay-provenance-panel__copy-btn" data-provenance-panel-copy>Copiar</button>' +
            "</div>" +
            '<pre class="ay-provenance-panel__sql"><code>' +
            escapeHtml(access.sql) +
            "</code></pre>" +
          "</div>" +
          accessMetaHtml(access) +
        "</div>"
      );
    } else if (access && access.access_kind === "spreadsheet") {
      parts.push(
        '<div class="ay-provenance-panel__section">' +
          '<div class="ay-provenance-panel__section-label">Datos del archivo</div>' +
          accessMetaHtml(access) +
        "</div>"
      );
    } else if (access) {
      parts.push(accessMetaHtml(access));
    }

    if (source) {
      parts.push(
        '<div class="ay-provenance-panel__source-card">' +
          '<span class="ay-provenance-panel__section-label">Fuente</span>' +
          '<div class="ay-provenance-panel__source-row">' +
            '<span class="ay-provenance-panel__source-value">' +
            escapeHtml(source.source_label || source.name || "") +
            "</span>" +
          "</div>" +
        "</div>"
      );
    }

    if (payload.provenance_links && payload.provenance_links.length > 1) {
      parts.push(
        '<details class="ay-provenance-panel__links">' +
          "<summary>Ver " +
          payload.provenance_links.length +
          " fuentes</summary>" +
          '<ul class="ay-provenance-panel__links-list">' +
          payload.provenance_links
            .map(function (link, index) {
              var label =
                (link.data_access && link.data_access.source_ref) ||
                (link.data_access && link.data_access.tool_call_id) ||
                "Fuente " + (index + 1);
              var detail = link.transformation || "";
              return (
                "<li><strong>" +
                escapeHtml(label) +
                "</strong>" +
                (detail ? " — " + escapeHtml(detail) : "") +
                "</li>"
              );
            })
            .join("") +
          "</ul>" +
        "</details>"
      );
    }

    return parts.join("");
  }

  function renderError(message) {
    return (
      '<div class="ay-provenance-panel__error">' + escapeHtml(message) + "</div>"
    );
  }

  function renderLoading() {
    return (
      '<div class="ay-provenance-panel__loading">' +
      '<span class="ay-provenance-panel__loading-dot" aria-hidden="true"></span>' +
      "Cargando procedencia…" +
      "</div>"
    );
  }

  function claimUrl(fileId, claimKey) {
    return (
      "/provenance/files/" +
      encodeURIComponent(fileId) +
      "/claims/" +
      encodeURIComponent(claimKey) +
      "/"
    );
  }

  function claimByIdUrl(claimId) {
    return "/provenance/claims/" + encodeURIComponent(claimId) + "/";
  }

  function fetchAndRenderClaim(body, url) {
    if (!body) return Promise.resolve();
    body.innerHTML = renderLoading();
    return fetch(url, {
      headers: { Accept: "application/json" },
      credentials: "same-origin",
    })
      .then(function (response) {
        if (!response.ok) {
          throw new Error(response.status === 404 ? "not_found" : "error");
        }
        return response.json();
      })
      .then(function (payload) {
        body.innerHTML = renderPanelContent(payload);
      })
      .catch(function (err) {
        var message =
          err && err.message === "not_found"
            ? "Procedencia no disponible para este dato."
            : "No se pudo cargar la procedencia.";
        body.innerHTML = renderError(message);
      });
  }

  function createOriginButton(claimId) {
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "ay-provenance-origin-btn";
    btn.setAttribute("data-provenance-claim-open", "");
    btn.setAttribute("data-provenance-claim-id", claimId);
    btn.textContent = "Ver datos de origen";
    return btn;
  }

  function appendInlineProvenanceFooter(card, claimId, caption, captionClass) {
    if (!card) return;
    if (!claimId) {
      if (!caption) return;
      var soloCaption = document.createElement("div");
      soloCaption.className = captionClass;
      soloCaption.textContent = caption;
      card.appendChild(soloCaption);
      return;
    }
    var footer = document.createElement("div");
    footer.className = "ay-inline-block__footer";
    var existingCaption = captionClass ? card.querySelector("." + captionClass) : null;
    if (existingCaption) {
      footer.appendChild(existingCaption);
    } else if (caption) {
      var captionEl = document.createElement("div");
      captionEl.className = captionClass;
      captionEl.textContent = caption;
      footer.appendChild(captionEl);
    }
    footer.appendChild(createOriginButton(claimId));
    card.appendChild(footer);
  }

  function getStage(root) {
    return (
      root.querySelector("#ay-dash-detail-stage") ||
      root.querySelector("#ay-artifact-panel-stage") ||
      root
    );
  }

  function getProvenanceHost() {
    var dash = document.getElementById("dashboards-view");
    if (dash && dash.classList.contains("ay-dash-detail") && dash.dataset.fileId) {
      return { root: dash, fileId: dash.dataset.fileId, context: "analiticas" };
    }
    var artifact = document.getElementById("artifact-panel");
    if (artifact && artifact.getAttribute("aria-hidden") === "false") {
      var fileId = artifact.dataset.fileId || "";
      if (!fileId && window.AyronArtifact && window.AyronArtifact.openFile) {
        fileId = window.AyronArtifact.openFile.file_id || "";
      }
      if (fileId) {
        return { root: artifact, fileId: fileId, context: "chat-artifact" };
      }
    }
    return null;
  }

  function bindPreviewIframe(stage) {
    var iframe = stage.querySelector(".ay-dash-detail__iframe, .ay-artifact-panel__iframe");
    if (!iframe) return;
    stage.__ayronPreviewIframe = iframe;
    function syncPreviewWindow() {
      try {
        stage.__ayronPreviewWindow = iframe.contentWindow || null;
      } catch (_err) {
        stage.__ayronPreviewWindow = null;
      }
    }
    syncPreviewWindow();
    if (iframe.dataset.provenanceLoadBound !== "true") {
      iframe.dataset.provenanceLoadBound = "true";
      iframe.addEventListener("load", syncPreviewWindow);
    }
  }

  function getPanel(root) {
    return root.querySelector("#ay-provenance-panel");
  }

  function getPanelBody(root) {
    return root.querySelector("#ay-provenance-panel-body");
  }

  function openPanel(root) {
    var stage = getStage(root);
    var panel = getPanel(root);
    if (!panel) return;
    panel.hidden = false;
    panel.setAttribute("aria-hidden", "false");
    stage.classList.add("ay-dash-detail__stage--panel-open");
  }

  function closePanel(root) {
    var stage = getStage(root);
    var panel = getPanel(root);
    if (!panel) return;
    panel.hidden = true;
    panel.setAttribute("aria-hidden", "true");
    stage.classList.remove("ay-dash-detail__stage--panel-open");
  }

  function bindPanelBodyActions(panel, body, onClose) {
    if (!panel || panel.dataset.actionsBound === "true") return;
    panel.dataset.actionsBound = "true";

    panel.addEventListener("click", function (e) {
      if (e.target.closest("[data-provenance-panel-close]")) {
        if (onClose) onClose();
        return;
      }
      var copyBtn = e.target.closest("[data-provenance-panel-copy]");
      if (!copyBtn || !body) return;
      var code = body.querySelector(".ay-provenance-panel__sql code");
      if (!code) return;
      var text = code.textContent || "";
      if (!text) return;
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text);
      }
    });
  }

  function bindPanelActions(root) {
    var panel = getPanel(root);
    var body = getPanelBody(root);
    if (!panel || panel.dataset.bound === "true") return;
    panel.dataset.bound = "true";
    bindPanelBodyActions(panel, body, function () {
      closePanel(root);
    });
  }

  function loadClaim(root, fileId, claimKey) {
    var body = getPanelBody(root);
    if (!body) return;

    openPanel(root);
    fetchAndRenderClaim(body, claimUrl(fileId, claimKey));
  }

  function openChatClaim(claimId) {
    if (!claimId) return;
    if (window.AyronToolTrace && window.AyronToolTrace.openProvenanceHtmlModal) {
      window.AyronToolTrace.openProvenanceHtmlModal(claimByIdUrl(claimId));
      return;
    }
    var dialog = document.getElementById("ay-provenance-sql-dialog");
    var contentEl = document.getElementById("ay-provenance-sql-content");
    if (!dialog || !contentEl) return;
    if (typeof dialog.showModal === "function") dialog.showModal();
    fetchAndRenderClaim(contentEl, claimByIdUrl(claimId));
  }

  function isPreviewMessageSource(stage, event) {
    if (!event.source || event.source === window) return false;
    var iframe = stage.querySelector(".ay-dash-detail__iframe, .ay-artifact-panel__iframe");
    if (!iframe) {
      return true;
    }
    try {
      if (event.source === iframe.contentWindow) return true;
    } catch (_err) {}
    if (stage.__ayronPreviewWindow && event.source === stage.__ayronPreviewWindow) {
      return true;
    }
    return false;
  }

  function handleProvenanceMessage(root, event, expectedFileId) {
    var stage = getStage(root);
    var data = event.data;

    if (!data || data.type !== "ayron:provenance-open") return;

    expectedFileId = expectedFileId || root.dataset.fileId || "";
    if (!data.claimKey || data.fileId !== expectedFileId) return;
    if (!isPreviewMessageSource(stage, event)) return;

    loadClaim(root, expectedFileId, data.claimKey);
  }

  function initArtifactPanel(panelEl) {
    if (!panelEl) return;
    bindPanelActions(panelEl);
    bindPreviewIframe(getStage(panelEl));
  }

  function initDashboardRoot(root) {
    if (!root || root.dataset.provenanceDashboardBound === "true") return;
    root.dataset.provenanceDashboardBound = "true";

    bindPanelActions(root);
    bindPreviewIframe(getStage(root));
  }

  function destroyDashboardRoot(root) {
    if (!root) return;
    delete root.dataset.provenanceDashboardBound;
  }

  function onWindowMessage(event) {
    if (!event.data || event.data.type !== "ayron:provenance-open") return;
    var host = getProvenanceHost();
    if (!host) return;
    handleProvenanceMessage(host.root, event, host.fileId);
  }

  window.addEventListener("message", onWindowMessage);

  document.body.addEventListener("click", function (e) {
    var btn = e.target.closest("[data-provenance-claim-open]");
    if (!btn) return;
    e.preventDefault();
    var claimId = btn.getAttribute("data-provenance-claim-id");
    if (claimId) openChatClaim(claimId);
  });

  function findDashboardRoot(node) {
    if (!node) return null;
    if (node.id === "dashboards-view" && node.classList.contains("ay-dash-detail")) {
      return node;
    }
    if (node.querySelector) {
      return node.querySelector("#dashboards-view.ay-dash-detail");
    }
    return null;
  }

  function initDashboard() {
    var root = document.getElementById("dashboards-view");
    if (root && root.classList.contains("ay-dash-detail")) {
      initDashboardRoot(root);
    }
  }

  document.body.addEventListener("htmx:afterSwap", function (evt) {
    var target = evt.detail && evt.detail.target;
    if (!target) return;

    var root = findDashboardRoot(target);
    if (root) {
      initDashboardRoot(root);
      return;
    }

    if (target.id === "ay-dash-preview-wrap" || target.closest("#ay-dash-preview-wrap")) {
      var dashboard = document.getElementById("dashboards-view");
      if (dashboard) {
        bindPreviewIframe(getStage(dashboard));
      }
    }
  });

  document.body.addEventListener("htmx:beforeSwap", function (evt) {
    var target = evt.detail && evt.detail.target;
    if (!target) return;
    var root = findDashboardRoot(target);
    if (root) {
      destroyDashboardRoot(root);
    }
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initDashboard);
  } else {
    initDashboard();
  }

  window.AyronProvenance = {
    initDashboard: initDashboard,
    initArtifactPanel: initArtifactPanel,
    openChatClaim: openChatClaim,
    appendInlineProvenanceFooter: appendInlineProvenanceFooter,
    createOriginButton: createOriginButton,
    claimUrl: claimUrl,
    claimByIdUrl: claimByIdUrl,
    renderPanelContent: renderPanelContent,
  };
})();
