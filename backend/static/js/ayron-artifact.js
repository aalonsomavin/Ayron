(function () {
  function iconSvg(name) {
    const icons = {
      filetext:
        '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/></svg>',
      download:
        '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/></svg>',
      copy:
        '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg>',
      expand:
        '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 3h6v6"/><path d="m21 3-7 7"/><path d="m3 21 7-7"/><path d="M9 21H3v-6"/></svg>',
      collapse:
        '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m14 10 7-7"/><path d="M20 10h-6V4"/><path d="m3 21 7-7"/><path d="M4 14h6v6"/></svg>',
      close:
        '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>',
    };
    return icons[name] || "";
  }

  function filePayloadFromEl(el) {
    return {
      file_id: el.dataset.fileId,
      name: el.dataset.fileName,
      ext: el.dataset.fileExt || "DOCX",
      meta: el.dataset.fileMeta || "",
      version: parseInt(el.dataset.fileVersion || "1", 10),
      download_url: el.dataset.downloadUrl,
      download_pdf_url: el.dataset.downloadPdfUrl || "",
      preview_url: el.dataset.previewUrl,
    };
  }

  function filePayloadFromEvent(event) {
    return {
      file_id: event.file_id,
      name: event.name,
      ext: event.ext || "DOCX",
      meta: event.meta || "",
      version: event.version || 1,
      download_url: event.download_url,
      download_pdf_url: event.download_pdf_url || "",
      preview_url: event.preview_url,
    };
  }

  function metaSuffix(meta) {
    return (meta || "").replace(/^Document · /, "").replace(/^Report · /, "");
  }

  function createFileCard(file, active) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "ay-file-card" + (active ? " ay-file-card--active" : "");
    btn.dataset.fileId = file.file_id;
    btn.dataset.fileName = file.name;
    btn.dataset.fileExt = file.ext || "DOCX";
    btn.dataset.fileMeta = file.meta || "";
    btn.dataset.fileVersion = String(file.version || 1);
    btn.dataset.downloadUrl = file.download_url;
    btn.dataset.downloadPdfUrl = file.download_pdf_url || "";
    btn.dataset.previewUrl = file.preview_url;
    const metaSuffixText = metaSuffix(file.meta);
    btn.innerHTML =
      '<span class="ay-file-card__icon">' + iconSvg("filetext") + "</span>" +
      '<span class="ay-file-card__body">' +
        '<span class="ay-file-card__name"></span>' +
        '<span class="ay-file-card__meta">' +
          '<span class="ay-file-card__ext"></span>' +
          "<span>· " + metaSuffixText + "</span>" +
        "</span>" +
      "</span>" +
      '<span class="ay-file-card__chev"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m9 18 6-6-6-6"/></svg></span>';
    btn.querySelector(".ay-file-card__name").textContent = file.name;
    btn.querySelector(".ay-file-card__ext").textContent = file.ext || "DOCX";
    return btn;
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

      this.panelEl.hidden = true;
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
        const url =
          self.openFile.ext === "HTML" && self.openFile.download_pdf_url
            ? self.openFile.download_pdf_url
            : self.openFile.download_url;
        if (url) window.location.href = url;
      });
      const htmlDownloadBtn = this.panelEl.querySelector("[data-artifact-download-html]");
      if (htmlDownloadBtn) {
        htmlDownloadBtn.addEventListener("click", function () {
          if (self.openFile && self.openFile.download_url) {
            window.location.href = self.openFile.download_url;
          }
        });
      }
      this.panelEl.querySelector("[data-artifact-copy]").addEventListener("click", function () {
        const body = self.panelEl.querySelector(".ay-artifact-panel__body");
        if (!body) return;
        const text = body.innerText || "";
        if (navigator.clipboard && text) {
          navigator.clipboard.writeText(text);
        }
      });

      document.addEventListener("click", function (e) {
        const card = e.target.closest(".ay-file-card");
        if (!card) return;
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
      this.openFile = file;
      this.panelEl.hidden = false;
      this.mainEl.classList.add("ay-main--artifact-open");
      this.panelEl.querySelector(".ay-artifact-panel__name").textContent = file.name;
      this.panelEl.querySelector(".ay-artifact-panel__ext").textContent = file.ext || "DOCX";
      const metaEl = this.panelEl.querySelector(".ay-artifact-panel__meta-suffix");
      if (metaEl) {
        metaEl.textContent = metaSuffix(file.meta);
      }
      const htmlDownloadBtn = this.panelEl.querySelector("[data-artifact-download-html]");
      const downloadBtn = this.panelEl.querySelector("[data-artifact-download]");
      const isHtml = file.ext === "HTML";
      if (htmlDownloadBtn) {
        htmlDownloadBtn.hidden = !isHtml;
      }
      if (downloadBtn) {
        downloadBtn.title = isHtml ? "Download PDF" : "Download";
      }

      const body = this.panelEl.querySelector(".ay-artifact-panel__body");
      body.innerHTML = '<div class="ay-artifact-panel__loading">Loading preview…</div>';

      fetch(file.preview_url, { credentials: "same-origin" })
        .then(function (r) {
          if (!r.ok) throw new Error("preview failed");
          return r.text();
        })
        .then(function (html) {
          if (self.openFile && self.openFile.file_id === file.file_id) {
            body.innerHTML = html;
            if (isHtml) {
              body.innerHTML = html;
            } else if (window.AyronDocPreview) {
              window.AyronDocPreview.mount(body);
            }
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
      });
    },

    close: function () {
      this.openFile = null;
      this.expanded = false;
      this.panelEl.hidden = true;
      this.mainEl.classList.remove("ay-main--artifact-open", "ay-main--artifact-expanded");
      this.setActiveCard(null);
      const expandBtn = this.panelEl.querySelector("[data-artifact-expand]");
      if (expandBtn) expandBtn.innerHTML = iconSvg("expand");
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

      const existing = document.querySelector('.ay-file-card[data-file-id="' + file.file_id + '"]');
      if (event.type === "file_updated" && existing) {
        existing.dataset.fileVersion = String(file.version || 1);
        existing.dataset.fileName = file.name;
        existing.dataset.fileMeta = file.meta || "";
        existing.querySelector(".ay-file-card__name").textContent = file.name;
        this.refreshIfOpen(file);
        return;
      }

      const container = ensureFilesContainer(contentEl);
      this.renderFileCard(file, container);
    },
  };
})();
