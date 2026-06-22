(function () {
  function iconSvg(name, size) {
    size = size || 16;
    const paths = {
      filetext:
        '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/>',
      dashboard:
        '<rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/>',
      download:
        '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/>',
      expand:
        '<path d="M15 3h6v6"/><path d="m21 3-7 7"/><path d="m3 21 7-7"/><path d="M9 21H3v-6"/>',
      collapse:
        '<path d="m14 10 7-7"/><path d="M20 10h-6V4"/><path d="m3 21 7-7"/><path d="M4 14h6v6"/>',
      close:
        '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
    };
    const inner = paths[name];
    if (!inner) return "";
    return (
      '<svg width="' +
      size +
      '" height="' +
      size +
      '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
      inner +
      "</svg>"
    );
  }

  function fileKind(file) {
    if (file.kind === "dashboard") return "dashboard";
    if (file.kind === "doc") return "doc";
    const meta = file.meta || "";
    if (meta === "Dashboard" || meta.indexOf("Dashboard ·") === 0) return "dashboard";
    if (file.open_expanded && (file.ext || "") === "HTML") return "dashboard";
    return "doc";
  }

  function fileIconName(kind) {
    return kind === "dashboard" ? "dashboard" : "filetext";
  }

  function applyFileCardIcon(card, kind) {
    const iconEl = card.querySelector(".ay-file-card__icon");
    if (!iconEl) return;
    iconEl.className = "ay-file-card__icon ay-file-card__icon--" + kind;
    iconEl.innerHTML = iconSvg(fileIconName(kind), 19);
    card.dataset.fileKind = kind;
  }

  function applyPanelFileIcon(panelEl, kind) {
    const iconEl = panelEl.querySelector(".ay-artifact-panel__file-icon");
    if (!iconEl) return;
    iconEl.className = "ay-artifact-panel__file-icon ay-artifact-panel__file-icon--" + kind;
    iconEl.innerHTML = iconSvg(fileIconName(kind), 17);
  }

  function applyPanelExpandVisibility(panelEl, file, expanded) {
    const expandBtn = panelEl.querySelector("[data-artifact-expand]");
    if (!expandBtn) return;
    const hideExpand = fileKind(file) === "dashboard";
    expandBtn.hidden = hideExpand;
    expandBtn.innerHTML = expanded ? iconSvg("collapse") : iconSvg("expand");
    const divider = expandBtn.previousElementSibling;
    if (divider && divider.classList.contains("ay-artifact-panel__divider")) {
      divider.hidden = hideExpand;
    }
  }

  function resetPanelExpandVisibility(panelEl) {
    const expandBtn = panelEl.querySelector("[data-artifact-expand]");
    if (!expandBtn) return;
    expandBtn.hidden = false;
    expandBtn.innerHTML = iconSvg("expand");
    const divider = expandBtn.previousElementSibling;
    if (divider && divider.classList.contains("ay-artifact-panel__divider")) {
      divider.hidden = false;
    }
  }

  function filePayloadFromEl(el) {
    return {
      file_id: el.dataset.fileId,
      name: el.dataset.fileName,
      ext: el.dataset.fileExt || "DOCX",
      kind: el.dataset.fileKind || "",
      meta: el.dataset.fileMeta || "",
      version: parseInt(el.dataset.fileVersion || "1", 10),
      download_url: el.dataset.downloadUrl,
      download_pdf_url: el.dataset.downloadPdfUrl || "",
      preview_url: el.dataset.previewUrl,
      open_expanded: el.dataset.openExpanded === "true",
    };
  }

  function filePayloadFromEvent(event) {
    return {
      file_id: event.file_id,
      name: event.name,
      ext: event.ext || "DOCX",
      kind: event.kind || "",
      meta: event.meta || "",
      version: event.version || 1,
      download_url: event.download_url,
      download_pdf_url: event.download_pdf_url || "",
      preview_url: event.preview_url,
      open_expanded: Boolean(event.open_expanded),
    };
  }

  function metaSuffix(meta) {
    return (meta || "").replace(/^Document · /, "").replace(/^Report · /, "").replace(/^Dashboard · /, "");
  }

  function displayFileName(file) {
    const name = file.name || "";
    if (fileKind(file) !== "dashboard") return name;
    return /\.html$/i.test(name) ? name.slice(0, -5) : name;
  }

  function createFileCard(file, active) {
    const kind = fileKind(file);
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "ay-file-card" + (active ? " ay-file-card--active" : "");
    btn.dataset.fileId = file.file_id;
    btn.dataset.fileName = file.name;
    btn.dataset.fileExt = file.ext || "DOCX";
    btn.dataset.fileKind = kind;
    btn.dataset.fileMeta = file.meta || "";
    btn.dataset.fileVersion = String(file.version || 1);
    btn.dataset.downloadUrl = file.download_url;
    btn.dataset.downloadPdfUrl = file.download_pdf_url || "";
    btn.dataset.previewUrl = file.preview_url;
    btn.dataset.openExpanded = file.open_expanded ? "true" : "false";
    const metaSuffixText = metaSuffix(file.meta);
    const bodyHtml =
      kind === "dashboard"
        ? '<span class="ay-file-card__body"><span class="ay-file-card__name"></span></span>'
        : '<span class="ay-file-card__body">' +
            '<span class="ay-file-card__name"></span>' +
            '<span class="ay-file-card__meta">' +
              '<span class="ay-file-card__ext"></span>' +
              "<span>· " + metaSuffixText + "</span>" +
            "</span>" +
          "</span>";
    btn.innerHTML =
      '<span class="ay-file-card__icon ay-file-card__icon--' +
      kind +
      '">' +
      iconSvg(fileIconName(kind), 19) +
      "</span>" +
      bodyHtml +
      '<span class="ay-file-card__chev"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m9 18 6-6-6-6"/></svg></span>';
    btn.querySelector(".ay-file-card__name").textContent = displayFileName(file);
    if (kind !== "dashboard") {
      btn.querySelector(".ay-file-card__ext").textContent = file.ext || "DOCX";
    }
    return btn;
  }

  function downloadUrlForFile(file) {
    if (fileKind(file) === "dashboard") {
      return file.download_url;
    }
    if (file.ext === "HTML" && file.download_pdf_url) {
      return file.download_pdf_url;
    }
    return file.download_url;
  }

  function ensureFilesContainer(contentEl) {
    let container = contentEl.querySelector(".ay-msg-agent__files");
    if (!container) {
      container = document.createElement("div");
      container.className = "ay-msg-agent__files";
      contentEl.appendChild(container);
    }
    return container;
  }

  window.AyronArtifact = {
    panelEl: null,
    mainEl: null,
    openFile: null,
    expanded: false,
    panelWidth: 680,

    init: function (options) {
      this.panelEl = options.panelEl;
      this.mainEl = options.mainEl;
      if (!this.panelEl) return;

      this.panelEl.removeAttribute("hidden");
      this.mainEl.classList.remove("ay-main--artifact-open", "ay-main--artifact-expanded", "ay-main--artifact-resizing");
      this.setPanelWidth(this.panelWidth);

      const self = this;
      this.initResize();
      this.panelEl.querySelector("[data-artifact-close]").addEventListener("click", function () {
        self.close();
      });
      this.panelEl.querySelector("[data-artifact-expand]").addEventListener("click", function () {
        self.toggleExpand();
      });
      this.panelEl.querySelector("[data-artifact-download]").addEventListener("click", function () {
        if (!self.openFile) return;
        const url = downloadUrlForFile(self.openFile);
        if (url) window.location.href = url;
      });

      document.addEventListener("click", function (e) {
        const card = e.target.closest(".ay-file-card");
        if (!card) return;
        if (window.AyronSidebar) window.AyronSidebar.close();
        self.open(filePayloadFromEl(card));
        self.setActiveCard(card);
      });
    },

    setPanelWidth: function (width) {
      const minWidth = 320;
      const maxWidth = Math.max(minWidth, Math.floor(this.mainEl.clientWidth * 0.85));
      const clamped = Math.min(maxWidth, Math.max(minWidth, width));
      this.panelWidth = clamped;
      this.mainEl.style.setProperty("--artifact-panel-width", clamped + "px");
      return clamped;
    },

    initResize: function () {
      const handle = this.panelEl.querySelector("[data-artifact-resize]");
      if (!handle) return;

      const self = this;
      handle.addEventListener("pointerdown", function (e) {
        if (self.expanded) return;
        e.preventDefault();
        const startX = e.clientX;
        const startWidth = self.panelWidth;
        handle.setPointerCapture(e.pointerId);
        self.mainEl.classList.add("ay-main--artifact-resizing");

        function onMove(ev) {
          self.setPanelWidth(startWidth + (startX - ev.clientX));
        }

        function onUp(ev) {
          if (handle.hasPointerCapture(ev.pointerId)) {
            handle.releasePointerCapture(ev.pointerId);
          }
          self.mainEl.classList.remove("ay-main--artifact-resizing");
          document.removeEventListener("pointermove", onMove);
          document.removeEventListener("pointerup", onUp);
          document.removeEventListener("pointercancel", onUp);
        }

        document.addEventListener("pointermove", onMove);
        document.addEventListener("pointerup", onUp);
        document.addEventListener("pointercancel", onUp);
      });
    },

    renderFileCard: function (file, container) {
      const card = createFileCard(file, false);
      container.appendChild(card);
      return card;
    },

    setActiveCard: function (activeCard) {
      document.querySelectorAll(".ay-file-card--active").forEach(function (el) {
        el.classList.remove("ay-file-card--active");
      });
      if (activeCard) activeCard.classList.add("ay-file-card--active");
    },

    open: function (file) {
      const self = this;
      if (window.AyronSidebar) window.AyronSidebar.close();
      this.openFile = file;
      this.expanded = Boolean(file.open_expanded);
      this.mainEl.classList.add("ay-main--artifact-open");
      this.mainEl.classList.toggle("ay-main--artifact-expanded", this.expanded);
      this.panelEl.setAttribute("aria-hidden", "false");
      applyPanelExpandVisibility(this.panelEl, file, this.expanded);
      applyPanelFileIcon(this.panelEl, fileKind(file));
      const panelKind = fileKind(file);
      this.panelEl.querySelector(".ay-artifact-panel__name").textContent = displayFileName(file);
      const metaLine = this.panelEl.querySelector(".ay-artifact-panel__meta-line");
      if (metaLine) {
        metaLine.hidden = panelKind === "dashboard";
      }
      if (panelKind !== "dashboard") {
        this.panelEl.querySelector(".ay-artifact-panel__ext").textContent = file.ext || "DOCX";
        const metaEl = this.panelEl.querySelector(".ay-artifact-panel__meta-suffix");
        if (metaEl) {
          metaEl.textContent = metaSuffix(file.meta);
        }
      }

      const isHtml = file.ext === "HTML";
      const body = this.panelEl.querySelector(".ay-artifact-panel__body");
      body.innerHTML =
        '<div class="ay-artifact-panel__loading" role="status" aria-label="Loading preview">' +
        '<span class="ay-spinner" aria-hidden="true"></span>' +
        "</div>";

      fetch(file.preview_url, { credentials: "same-origin" })
        .then(function (r) {
          if (!r.ok) throw new Error("preview failed");
          return r.text();
        })
        .then(function (html) {
          if (!self.openFile || self.openFile.file_id !== file.file_id) return;
          body.innerHTML = html;
          if (isHtml) {
            if (window.AyronDashboard) {
              window.AyronDashboard.mountAll(body);
            }
            if (window.AyronChart) {
              window.AyronChart.mountAll(body);
            }
          } else if (!isHtml && window.AyronDocPreview) {
            window.AyronDocPreview.mount(body);
          }
        })
        .catch(function () {
          if (self.openFile && self.openFile.file_id === file.file_id) {
            body.innerHTML = '<div class="ay-artifact-panel__error">Preview unavailable.</div>';
          }
        });
    },

    refreshIfOpen: function (file) {
      if (!this.openFile || this.openFile.file_id !== file.file_id) return;
      if ((file.version || 1) > (this.openFile.version || 1)) {
        this.open(file);
      }
      document.querySelectorAll('.ay-file-card[data-file-id="' + file.file_id + '"]').forEach(function (card) {
        card.dataset.fileVersion = String(file.version || 1);
        card.dataset.fileName = file.name;
        card.dataset.fileMeta = file.meta || "";
        card.dataset.openExpanded = file.open_expanded ? "true" : "false";
        applyFileCardIcon(card, fileKind(file));
      });
    },

    close: function () {
      this.openFile = null;
      this.expanded = false;
      this.mainEl.classList.remove("ay-main--artifact-open", "ay-main--artifact-expanded");
      this.panelEl.setAttribute("aria-hidden", "true");
      this.setActiveCard(null);
      resetPanelExpandVisibility(this.panelEl);
      const metaLine = this.panelEl.querySelector(".ay-artifact-panel__meta-line");
      if (metaLine) metaLine.hidden = false;
    },

    toggleExpand: function () {
      this.expanded = !this.expanded;
      this.mainEl.classList.toggle("ay-main--artifact-expanded", this.expanded);
      const expandBtn = this.panelEl.querySelector("[data-artifact-expand]");
      if (expandBtn) {
        expandBtn.innerHTML = this.expanded ? iconSvg("collapse") : iconSvg("expand");
      }
    },

    appendFileBlock: function (bubble, event) {
      const contentEl = bubble.querySelector(".ay-msg-agent__content");
      if (!contentEl) return;
      const file = filePayloadFromEvent(event);
      const container = ensureFilesContainer(contentEl);
      this.renderFileCard(file, container);
    },

    handleEvent: function (bubble, event) {
      const file = filePayloadFromEvent(event);
      const contentEl = bubble.querySelector(".ay-msg-agent__content");
      if (!contentEl) return;

      const existingInBubble = contentEl.querySelector(
        '.ay-file-card[data-file-id="' + file.file_id + '"]'
      );
      if (event.type === "file_updated" && existingInBubble) {
        existingInBubble.dataset.fileVersion = String(file.version || 1);
        existingInBubble.dataset.fileName = file.name;
        existingInBubble.dataset.fileMeta = file.meta || "";
        existingInBubble.querySelector(".ay-file-card__name").textContent = displayFileName(file);
        applyFileCardIcon(existingInBubble, fileKind(file));
        this.refreshIfOpen(file);
        return;
      }

      const container = ensureFilesContainer(contentEl);
      this.renderFileCard(file, container);
    },
  };
})();
