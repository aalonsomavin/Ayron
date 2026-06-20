(function () {
  var DEFAULT_WIDTH_PX = 816;
  var DEFAULT_HEIGHT_PX = 1056;
  var DEFAULT_MARGIN_PX = 72;
  var resizeObserver = null;
  var observedContainer = null;
  var resizeTimer = null;

  function isMeaningfulNode(node) {
    if (node.nodeType === Node.ELEMENT_NODE) {
      return true;
    }
    if (node.nodeType === Node.TEXT_NODE) {
      return Boolean(node.textContent && node.textContent.trim());
    }
    return false;
  }

  function normalizePreview(container) {
    var preview = container.querySelector(".ay-doc-preview");
    if (preview) {
      return preview;
    }

    var legacyPage = container.querySelector(".ay-doc-preview__page");
    if (!legacyPage) {
      return null;
    }

    preview = document.createElement("div");
    preview.className = "ay-doc-preview";
    preview.setAttribute("data-page-width-px", String(DEFAULT_WIDTH_PX));
    preview.setAttribute("data-page-height-px", String(DEFAULT_HEIGHT_PX));
    preview.setAttribute("data-page-margin-px", String(DEFAULT_MARGIN_PX));

    var source = document.createElement("div");
    source.className = "ay-doc-preview__source";
    while (legacyPage.firstChild) {
      source.appendChild(legacyPage.firstChild);
    }
    preview.appendChild(source);

    var pagesHost = document.createElement("div");
    pagesHost.className = "ay-doc-preview__pages";
    preview.appendChild(pagesHost);

    legacyPage.replaceWith(preview);
    return preview;
  }

  function readMetrics(preview) {
    var width = parseInt(preview.getAttribute("data-page-width-px"), 10) || DEFAULT_WIDTH_PX;
    var height = parseInt(preview.getAttribute("data-page-height-px"), 10) || DEFAULT_HEIGHT_PX;
    var margin = parseInt(preview.getAttribute("data-page-margin-px"), 10) || DEFAULT_MARGIN_PX;
    var bodyHeight = height - margin * 2;
    return { width: width, height: height, margin: margin, bodyHeight: bodyHeight };
  }

  function ensureViewport(preview) {
    var pagesHost = preview.querySelector(".ay-doc-preview__pages");
    if (!pagesHost) {
      return null;
    }

    var viewport = preview.querySelector(".ay-doc-preview__viewport");
    if (!viewport) {
      viewport = document.createElement("div");
      viewport.className = "ay-doc-preview__viewport";
      pagesHost.parentNode.insertBefore(viewport, pagesHost);
      viewport.appendChild(pagesHost);
    }

    return { viewport: viewport, pagesHost: pagesHost };
  }

  function contentWidth(container) {
    var style = window.getComputedStyle(container);
    var padLeft = parseFloat(style.paddingLeft) || 0;
    var padRight = parseFloat(style.paddingRight) || 0;
    return Math.max(0, container.clientWidth - padLeft - padRight);
  }

  function fitPreview(container, preview) {
    var parts = ensureViewport(preview);
    if (!parts) {
      return;
    }

    var viewport = parts.viewport;
    var pagesHost = parts.pagesHost;
    var metrics = readMetrics(preview);
    var availableWidth = contentWidth(container);
    var scale = 1;

    if (availableWidth > 0 && availableWidth < metrics.width) {
      scale = availableWidth / metrics.width;
    }

    if (scale < 1) {
      pagesHost.style.transform = "scale(" + scale + ")";
      pagesHost.style.transformOrigin = "top left";
    } else {
      pagesHost.style.transform = "";
      pagesHost.style.transformOrigin = "";
      scale = 1;
    }

    var naturalHeight = pagesHost.offsetHeight;
    viewport.style.width = Math.round(metrics.width * scale) + "px";
    viewport.style.height = Math.round(naturalHeight * scale) + "px";
    viewport.style.marginLeft = "auto";
    viewport.style.marginRight = "auto";
  }

  function applyPageLayout(page, metrics) {
    page.style.width = metrics.width + "px";
    page.style.height = metrics.height + "px";
    page.style.minHeight = metrics.height + "px";
    page.style.padding = metrics.margin + "px";
    page.style.boxSizing = "border-box";

    var body = page.querySelector(".ay-doc-preview__page-body");
    body.style.height = metrics.bodyHeight + "px";
    body.style.maxHeight = metrics.bodyHeight + "px";
    body.style.overflow = "hidden";
  }

  function markOverflowPage(page, metrics) {
    page.classList.add("ay-doc-preview__page--overflow");
    page.style.height = "auto";
    page.style.minHeight = metrics.height + "px";
    var body = page.querySelector(".ay-doc-preview__page-body");
    body.style.height = "auto";
    body.style.maxHeight = "none";
    body.style.overflow = "visible";
  }

  function headerMarkup() {
    return (
      '<div class="ay-doc-preview__page-header-row">' +
        '<span class="ay-doc-preview__page-header-title"></span>' +
        '<span class="ay-doc-preview__page-header-meta"></span>' +
      "</div>" +
      '<div class="ay-doc-preview__page-header-rule"></div>'
    );
  }

  function footerMarkup() {
    return (
      '<div class="ay-doc-preview__page-footer-rule"></div>' +
      '<div class="ay-doc-preview__page-footer-row">' +
        '<div class="ay-doc-preview__page-footer-brand">' +
          '<span class="ay-doc-preview__page-footer-dot" aria-hidden="true"></span>' +
          '<span class="ay-doc-preview__page-footer-attribution"></span>' +
        "</div>" +
        '<span class="ay-doc-preview__page-footer-pages"></span>' +
      "</div>"
    );
  }

  function createPage(metrics) {
    var page = document.createElement("article");
    page.className = "ay-doc-preview__page";

    var header = document.createElement("div");
    header.className = "ay-doc-preview__page-header";
    header.innerHTML = headerMarkup();
    page.appendChild(header);

    var body = document.createElement("div");
    body.className = "ay-doc-preview__page-body";
    page.appendChild(body);

    var footer = document.createElement("div");
    footer.className = "ay-doc-preview__page-footer";
    footer.innerHTML = footerMarkup();
    page.appendChild(footer);

    applyPageLayout(page, metrics);
    return page;
  }

  function bodyOverflows(body, metrics) {
    return body.scrollHeight > metrics.bodyHeight + 1;
  }

  function isPreviewTable(node) {
    return (
      node &&
      node.nodeType === Node.ELEMENT_NODE &&
      node.tagName === "TABLE" &&
      node.classList.contains("ay-doc-preview__table")
    );
  }

  function buildTableFragment(thead, rowNodes, continued) {
    var table = document.createElement("table");
    table.className = "ay-doc-preview__table" + (continued ? " ay-doc-preview__table--continued" : "");
    if (thead) {
      table.appendChild(thead.cloneNode(true));
    }
    var tbody = document.createElement("tbody");
    rowNodes.forEach(function (row) {
      tbody.appendChild(row);
    });
    table.appendChild(tbody);
    return table;
  }

  function createPageFlow(pagesHost, metrics) {
    var page = createPage(metrics);
    pagesHost.appendChild(page);
    var body = page.querySelector(".ay-doc-preview__page-body");

    function startNewPage() {
      page = createPage(metrics);
      pagesHost.appendChild(page);
      body = page.querySelector(".ay-doc-preview__page-body");
    }

    function placeBlock(node) {
      body.appendChild(node);
      if (bodyOverflows(body, metrics)) {
        body.removeChild(node);
        startNewPage();
        body.appendChild(node);
        if (bodyOverflows(body, metrics)) {
          markOverflowPage(page, metrics);
        }
      }
    }

    function placeTable(sourceTable) {
      var thead = sourceTable.querySelector("thead");
      var rows = Array.prototype.map.call(sourceTable.querySelectorAll("tbody tr"), function (row) {
        return row.cloneNode(true);
      });

      if (!rows.length) {
        placeBlock(sourceTable.cloneNode(true));
        return;
      }

      var index = 0;
      var continuesTable = false;

      while (index < rows.length) {
        var pageContinuesTable = continuesTable;
        var chunk = [];

        while (index < rows.length) {
          var candidate = rows[index];
          var trial = buildTableFragment(thead, chunk.concat([candidate]), pageContinuesTable && !chunk.length);
          body.appendChild(trial);

          if (!bodyOverflows(body, metrics)) {
            body.removeChild(trial);
            chunk.push(candidate);
            index += 1;
            continue;
          }

          body.removeChild(trial);

          if (chunk.length) {
            body.appendChild(buildTableFragment(thead, chunk, pageContinuesTable));
            chunk = [];
            continuesTable = true;
            startNewPage();
            pageContinuesTable = true;
            continue;
          }

          if (body.childElementCount > 0) {
            startNewPage();
            pageContinuesTable = true;
            continuesTable = true;
          }

          var rowTable = buildTableFragment(thead, [candidate], pageContinuesTable);
          body.appendChild(rowTable);
          if (bodyOverflows(body, metrics)) {
            markOverflowPage(page, metrics);
          }
          index += 1;
        }

        if (chunk.length) {
          body.appendChild(buildTableFragment(thead, chunk, pageContinuesTable));
        }
      }
    }

    return {
      placeBlock: placeBlock,
      placeTable: placeTable,
    };
  }

  function removeEmptyPages(pagesHost) {
    Array.prototype.forEach.call(pagesHost.querySelectorAll(".ay-doc-preview__page"), function (pageEl) {
      var pageBody = pageEl.querySelector(".ay-doc-preview__page-body");
      if (pageBody && !pageBody.children.length) {
        pageEl.remove();
      }
    });
  }

  function paginate(preview) {
    var source = preview.querySelector(".ay-doc-preview__source");
    if (!source) {
      return;
    }

    if (!source.dataset.template) {
      source.dataset.template = source.innerHTML;
    }
    source.innerHTML = source.dataset.template;

    var pagesHost = preview.querySelector(".ay-doc-preview__pages");
    if (!pagesHost) {
      pagesHost = document.createElement("div");
      pagesHost.className = "ay-doc-preview__pages";
      preview.appendChild(pagesHost);
    }
    pagesHost.innerHTML = "";
    pagesHost.style.transform = "";

    var nodes = Array.from(source.childNodes).filter(isMeaningfulNode);
    source.innerHTML = "";

    if (!nodes.length) {
      return;
    }

    var metrics = readMetrics(preview);
    var flow = createPageFlow(pagesHost, metrics);

    nodes.forEach(function (node) {
      if (isPreviewTable(node)) {
        flow.placeTable(node);
      } else {
        flow.placeBlock(node);
      }
    });

    removeEmptyPages(pagesHost);

    var total = pagesHost.children.length;
    var attribution = preview.getAttribute("data-footer-attribution") || "Generado con Ayron";
    var headerTitle = preview.getAttribute("data-page-header-title") || "";
    var headerSubtitle = preview.getAttribute("data-page-header-subtitle") || "";
    Array.prototype.forEach.call(pagesHost.querySelectorAll(".ay-doc-preview__page"), function (pageEl, index) {
      var pageHeader = pageEl.querySelector(".ay-doc-preview__page-header");
      if (pageHeader) {
        var titleEl = pageHeader.querySelector(".ay-doc-preview__page-header-title");
        var metaEl = pageHeader.querySelector(".ay-doc-preview__page-header-meta");
        if (titleEl) {
          titleEl.textContent = headerTitle;
        }
        if (metaEl) {
          metaEl.textContent = headerSubtitle;
        }
        if (!headerTitle) {
          pageHeader.style.display = "none";
        }
      }
      var footer = pageEl.querySelector(".ay-doc-preview__page-footer");
      if (footer) {
        var attributionEl = footer.querySelector(".ay-doc-preview__page-footer-attribution");
        var pagesEl = footer.querySelector(".ay-doc-preview__page-footer-pages");
        if (attributionEl) {
          attributionEl.textContent = attribution;
        }
        if (pagesEl) {
          pagesEl.textContent = String(index + 1) + " de " + String(total);
        }
      }
      pageEl.setAttribute("aria-label", "Página " + String(index + 1) + " de " + String(total));
    });
  }

  function mount(container) {
    if (!container) {
      return;
    }
    var preview = normalizePreview(container);
    if (!preview) {
      return;
    }
    paginate(preview);
    fitPreview(container, preview);
  }

  function mountWhenReady(container) {
    window.requestAnimationFrame(function () {
      window.requestAnimationFrame(function () {
        mount(container);
        observe(container);
      });
    });
  }

  function observe(container) {
    if (!container) {
      return;
    }
    observedContainer = container;

    if (!window.ResizeObserver) {
      return;
    }

    if (resizeObserver) {
      resizeObserver.disconnect();
    }

    resizeObserver = new ResizeObserver(function () {
      if (resizeTimer) {
        window.clearTimeout(resizeTimer);
      }
      resizeTimer = window.setTimeout(function () {
        var preview = container.querySelector(".ay-doc-preview");
        if (preview) {
          fitPreview(container, preview);
        }
      }, 50);
    });
    resizeObserver.observe(container);
  }

  window.AyronDocPreview = {
    mount: mountWhenReady,
    paginate: paginate,
    fit: fitPreview,
    observe: observe,
  };
})();
