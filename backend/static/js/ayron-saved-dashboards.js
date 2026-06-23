(function () {
  function parseSeries(raw) {
    if (!raw) return [40, 52, 48, 63, 70, 66, 82, 90, 86, 98];
    return raw.split(",").map(function (part) {
      return parseInt(part, 10);
    }).filter(function (n) {
      return !isNaN(n);
    });
  }

  function drawSparkline(canvas, series, tint) {
    if (!canvas || !canvas.getContext) return;
    const ctx = canvas.getContext("2d");
    const w = canvas.width;
    const h = canvas.height;
    const pad = 4;
    const mx = Math.max.apply(null, series);
    const mn = Math.min.apply(null, series);
    const n = series.length;
    if (n < 2) return;

    function xs(i) {
      return pad + (i / (n - 1)) * (w - 2 * pad);
    }

    function ys(v) {
      return h - pad - ((v - mn) / (mx - mn || 1)) * (h - 2 * pad);
    }

    ctx.clearRect(0, 0, w, h);
    ctx.beginPath();
    ctx.moveTo(xs(0), ys(series[0]));
    for (let i = 1; i < n; i++) {
      ctx.lineTo(xs(i), ys(series[i]));
    }
    ctx.lineTo(xs(n - 1), h - pad);
    ctx.lineTo(xs(0), h - pad);
    ctx.closePath();
    const grad = ctx.createLinearGradient(0, 0, 0, h);
    grad.addColorStop(0, tint + "33");
    grad.addColorStop(1, tint + "00");
    ctx.fillStyle = grad;
    ctx.fill();

    ctx.beginPath();
    ctx.moveTo(xs(0), ys(series[0]));
    for (let i = 1; i < n; i++) {
      ctx.lineTo(xs(i), ys(series[i]));
    }
    ctx.strokeStyle = tint;
    ctx.lineWidth = 2;
    ctx.lineJoin = "round";
    ctx.lineCap = "round";
    ctx.stroke();
  }

  function filePayloadFromCard(card) {
    return {
      file_id: card.dataset.fileId,
      name: card.dataset.fileName,
      ext: card.dataset.fileExt || "HTML",
      kind: card.dataset.fileKind || "dashboard",
      meta: card.dataset.fileMeta || "Dashboard",
      version: parseInt(card.dataset.fileVersion || "1", 10),
      download_url: card.dataset.downloadUrl,
      download_pdf_url: card.dataset.downloadPdfUrl || "",
      preview_url: card.dataset.previewUrl,
      open_expanded: card.dataset.openExpanded === "true",
      saved: true,
      pinned: card.dataset.pinned === "true",
    };
  }

  function closeAllMenus(exceptCard) {
    document.querySelectorAll(".ay-saved-card__menu").forEach(function (menu) {
      const card = menu.closest(".ay-saved-card");
      if (!exceptCard || card !== exceptCard) {
        menu.hidden = true;
      }
    });
  }

  function updateCountLabel() {
    const countEl = document.querySelector(".ay-saved-page__count");
    if (!countEl) return;
    const cards = document.querySelectorAll(".ay-saved-card");
    const pinned = document.querySelectorAll('.ay-saved-card[data-pinned="true"]').length;
    const total = cards.length;
    let label = total === 1 ? "1 dashboard" : total + " dashboards";
    if (pinned === 1) label += " · 1 fijado";
    else if (pinned > 1) label += " · " + pinned + " fijados";
    countEl.textContent = label;
  }

  function mountSparklines(root) {
    (root || document).querySelectorAll(".ay-saved-card").forEach(function (card) {
      const canvas = card.querySelector(".ay-saved-card__spark");
      if (!canvas || canvas.dataset.mounted === "true") return;
      canvas.dataset.mounted = "true";
      drawSparkline(
        canvas,
        parseSeries(card.dataset.series),
        card.dataset.tint || "#3b6ef6"
      );
    });
  }

  function filterCards(query) {
    const q = (query || "").trim().toLowerCase();
    const cards = document.querySelectorAll(".ay-saved-card");
    let visible = 0;
    cards.forEach(function (card) {
      const title = (card.dataset.fileName || "").toLowerCase();
      const author = (card.dataset.author || "").toLowerCase();
      const match = !q || title.indexOf(q) >= 0 || author.indexOf(q) >= 0;
      card.hidden = !match;
      if (match) visible += 1;
    });

    const pinnedSection = document.getElementById("saved-pinned");
    const allLabel = document.getElementById("saved-all-label");
    const noResults = document.getElementById("saved-no-results");
    if (pinnedSection) {
      pinnedSection.hidden = Boolean(q) || !pinnedSection.querySelector('.ay-saved-card:not([hidden])');
    }
    if (allLabel) {
      allLabel.textContent = q ? visible + (visible === 1 ? " resultado" : " resultados") : "Todos";
    }
    if (noResults) {
      noResults.hidden = !q || visible > 0;
    }
  }

  function removeCard(card) {
    const pinnedGrid = document.getElementById("saved-pinned-grid");
    const allGrid = document.getElementById("saved-all-grid");
    card.remove();
    updateCountLabel();
    const remaining = document.querySelectorAll(".ay-saved-card").length;
    if (!remaining) {
      window.location.reload();
      return;
    }
    if (pinnedGrid && !pinnedGrid.querySelector(".ay-saved-card")) {
      const pinnedSection = document.getElementById("saved-pinned");
      if (pinnedSection) pinnedSection.hidden = true;
    }
    if (allGrid && !allGrid.querySelector(".ay-saved-card")) {
      allGrid.hidden = true;
    }
  }

  window.AyronSavedDashboards = {
    csrfToken: null,

    init: function (options) {
      this.csrfToken = options.csrfToken || null;
      mountSparklines(document);
      this.bindSearch();
      this.bindCards();
      filterCards("");
      document.addEventListener("click", function () {
        closeAllMenus(null);
      });
    },

    bindSearch: function () {
      const input = document.getElementById("saved-search");
      const clearBtn = document.getElementById("saved-search-clear");
      if (!input) return;

      const syncClear = function () {
        if (!clearBtn) return;
        clearBtn.hidden = !input.value;
      };

      input.addEventListener("input", function () {
        filterCards(input.value);
        syncClear();
      });

      if (clearBtn) {
        clearBtn.addEventListener("click", function () {
          input.value = "";
          filterCards("");
          syncClear();
          input.focus();
        });
      }
    },

    bindCards: function () {
      const self = this;
      document.querySelectorAll(".ay-saved-card").forEach(function (card) {
        const pinBtn = card.querySelector("[data-saved-pin]");
        const menuBtn = card.querySelector("[data-saved-menu]");
        const menu = card.querySelector(".ay-saved-card__menu");
        const openBtn = card.querySelector("[data-saved-open]");
        const renameBtn = card.querySelector("[data-saved-rename]");
        const removeBtn = card.querySelector("[data-saved-remove]");
        const renamePanel = card.querySelector(".ay-saved-card__rename");
        const renameInput = card.querySelector(".ay-saved-card__rename-input");
        const renameSave = card.querySelector(".ay-saved-card__rename-save");
        const renameCancel = card.querySelector(".ay-saved-card__rename-cancel");
        const body = card.querySelector(".ay-saved-card__body");

        if (pinBtn) {
          pinBtn.addEventListener("click", function (e) {
            e.stopPropagation();
            self.togglePin(card);
          });
        }

        if (menuBtn && menu) {
          menuBtn.addEventListener("click", function (e) {
            e.stopPropagation();
            const willOpen = menu.hidden;
            closeAllMenus(card);
            menu.hidden = !willOpen;
          });
          menu.addEventListener("click", function (e) {
            e.stopPropagation();
          });
        }

        if (openBtn) {
          openBtn.addEventListener("click", function () {
            closeAllMenus(null);
            if (window.AyronArtifact) {
              window.AyronArtifact.open(filePayloadFromCard(card));
            }
          });
        }

        card.addEventListener("dblclick", function () {
          if (window.AyronArtifact) {
            window.AyronArtifact.open(filePayloadFromCard(card));
          }
        });

        if (renameBtn && renamePanel && renameInput && body) {
          renameBtn.addEventListener("click", function () {
            closeAllMenus(null);
            renamePanel.hidden = false;
            body.hidden = true;
            renameInput.focus();
            renameInput.select();
          });
        }

        if (renameCancel && renamePanel && body && renameInput) {
          renameCancel.addEventListener("click", function () {
            renameInput.value = card.dataset.fileName;
            renamePanel.hidden = true;
            body.hidden = false;
          });
        }

        if (renameSave && renamePanel && body && renameInput) {
          renameSave.addEventListener("click", function () {
            self.renameCard(card, renameInput.value, renamePanel, body);
          });
          renameInput.addEventListener("keydown", function (e) {
            if (e.key === "Enter") {
              e.preventDefault();
              self.renameCard(card, renameInput.value, renamePanel, body);
            } else if (e.key === "Escape") {
              e.preventDefault();
              renameInput.value = card.dataset.fileName;
              renamePanel.hidden = true;
              body.hidden = false;
            }
          });
        }

        if (removeBtn) {
          removeBtn.addEventListener("click", function () {
            closeAllMenus(null);
            self.unsaveCard(card);
          });
        }
      });
    },

    headers: function () {
      const headers = { "Content-Type": "application/json" };
      if (this.csrfToken) {
        headers["X-CSRFToken"] = typeof this.csrfToken === "function" ? this.csrfToken() : this.csrfToken;
      }
      return headers;
    },

    togglePin: function (card) {
      const self = this;
      const pinned = card.dataset.pinned === "true";
      const next = !pinned;
      fetch("/files/" + card.dataset.fileId + "/pin/", {
        method: "POST",
        credentials: "same-origin",
        headers: this.headers(),
        body: JSON.stringify({ pinned: next }),
      })
        .then(function (r) {
          if (!r.ok) throw new Error("pin failed");
          return r.json();
        })
        .then(function () {
          window.location.reload();
        })
        .catch(function () {});
    },

    renameCard: function (card, rawName, renamePanel, body) {
      const self = this;
      const name = (rawName || "").trim();
      if (!name || name === card.dataset.fileName) {
        renamePanel.hidden = true;
        body.hidden = false;
        return;
      }
      fetch("/files/" + card.dataset.fileId + "/rename/", {
        method: "POST",
        credentials: "same-origin",
        headers: this.headers(),
        body: JSON.stringify({ name: name }),
      })
        .then(function (r) {
          if (!r.ok) throw new Error("rename failed");
          return r.json();
        })
        .then(function (data) {
          card.dataset.fileName = data.name;
          const title = card.querySelector(".ay-saved-card__title");
          const metric = card.querySelector(".ay-saved-card__metric");
          if (title) title.textContent = data.name;
          if (metric) metric.textContent = data.name;
          renamePanel.hidden = true;
          body.hidden = false;
          if (window.AyronArtifact && window.AyronArtifact.openFile &&
              window.AyronArtifact.openFile.file_id === card.dataset.fileId) {
            window.AyronArtifact.openFile.name = data.name;
            window.AyronArtifact.applyPanelTitle(window.AyronArtifact.panelEl, window.AyronArtifact.openFile);
          }
        })
        .catch(function () {});
    },

    unsaveCard: function (card) {
      const self = this;
      fetch("/files/" + card.dataset.fileId + "/unsave/", {
        method: "POST",
        credentials: "same-origin",
        headers: this.headers(),
      })
        .then(function (r) {
          if (!r.ok) throw new Error("unsave failed");
          return r.json();
        })
        .then(function () {
          if (window.AyronArtifact && window.AyronArtifact.openFile &&
              window.AyronArtifact.openFile.file_id === card.dataset.fileId) {
            window.AyronArtifact.close();
          }
          removeCard(card);
        })
        .catch(function () {});
    },
  };
})();
