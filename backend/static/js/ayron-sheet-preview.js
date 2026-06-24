(function () {
  var EMPTY_COL_WIDTH = 72;
  var EMPTY_ROW_HEIGHT = 35;
  var MAX_MEASURE_ATTEMPTS = 10;

  function colLetter(index) {
    var letters = "";
    var n = index + 1;
    while (n > 0) {
      n -= 1;
      letters = String.fromCharCode(65 + (n % 26)) + letters;
      n = Math.floor(n / 26);
    }
    return letters;
  }

  function estimateScrollSize(pane, scroll) {
    var root = pane.closest(".ay-sheet-preview");
    var formulaBar = pane.querySelector(".ay-sheet-preview__formula-bar");
    var tabs = root ? root.querySelector(".ay-sheet-preview__tabs") : null;
    var paneW = pane.clientWidth;
    var paneH = pane.clientHeight;
    var chromeH =
      (formulaBar ? formulaBar.offsetHeight : 34) + (tabs ? tabs.offsetHeight : 34);
    return {
      width: scroll.clientWidth || paneW || 480,
      height: scroll.clientHeight || Math.max(240, paneH - chromeH),
    };
  }

  function clearGridPadding(grid) {
    grid.querySelectorAll("[data-pad]").forEach(function (el) {
      el.remove();
    });
    var template = grid.dataset.colsTemplate;
    if (template) {
      grid.style.setProperty("--ay-sheet-cols", template);
    }
    grid.style.minHeight = "";
    grid.style.minWidth = "";
    delete grid.dataset.padded;
  }

  function ensureCanvas(pane) {
    var scroll = pane.querySelector(".ay-sheet-preview__scroll");
    if (!scroll || scroll.querySelector(".ay-sheet-preview__canvas")) return;
    var canvas = document.createElement("div");
    canvas.className = "ay-sheet-preview__canvas";
    canvas.setAttribute("aria-hidden", "true");
    var grid = scroll.querySelector(".ay-sheet-preview__grid");
    if (grid) {
      scroll.insertBefore(canvas, grid);
    } else {
      scroll.appendChild(canvas);
    }
  }

  function padSheetGrid(pane, attempt) {
    var scroll = pane.querySelector(".ay-sheet-preview__scroll");
    var grid = pane.querySelector(".ay-sheet-preview__grid");
    if (!scroll || !grid) return;

    attempt = attempt || 0;
    clearGridPadding(grid);

    var colCount = parseInt(grid.dataset.colCount || "0", 10);
    var dataRows = parseInt(grid.dataset.dataRows || "0", 10);
    if (!colCount) return;

    var target = estimateScrollSize(pane, scroll);
    var scrollW = target.width;
    var scrollH = target.height;

    if ((scroll.clientWidth < 1 || scroll.clientHeight < 1) && attempt < MAX_MEASURE_ATTEMPTS) {
      requestAnimationFrame(function () {
        padSheetGrid(pane, attempt + 1);
      });
      return;
    }

    var totalGridRows = 2 + dataRows;
    var colsPerRow = colCount + 1;
    var gridW = grid.offsetWidth;
    var gridH = grid.offsetHeight;

    var padCols = Math.max(0, Math.ceil((scrollW - gridW) / EMPTY_COL_WIDTH));
    var padRows = Math.max(0, Math.ceil((scrollH - gridH) / EMPTY_ROW_HEIGHT));

    var r;
    var c;
    var rowEndIndex;
    var insertAfter;
    var el;
    var newColCount;

    if (padCols > 0) {
      for (r = totalGridRows - 1; r >= 0; r--) {
        rowEndIndex = (r + 1) * colsPerRow - 1;
        insertAfter = grid.children[rowEndIndex];
        if (!insertAfter) continue;
        for (c = padCols - 1; c >= 0; c--) {
          el = document.createElement("div");
          el.dataset.pad = "1";
          if (r === 0) {
            el.className = "ay-sheet-preview__col-hdr";
            el.textContent = colLetter(colCount + c);
          } else {
            el.className = "ay-sheet-preview__cell ay-sheet-preview__cell--empty";
          }
          insertAfter.after(el);
        }
      }
    }

    newColCount = colCount + padCols;
    grid.style.setProperty(
      "--ay-sheet-cols",
      "38px repeat(" + newColCount + ", minmax(72px, max-content))"
    );

    for (r = 0; r < padRows; r++) {
      el = document.createElement("div");
      el.className = "ay-sheet-preview__row-hdr";
      el.dataset.pad = "1";
      el.textContent = String(1 + dataRows + 1 + r);
      grid.appendChild(el);
      for (c = 0; c < newColCount; c++) {
        el = document.createElement("div");
        el.className = "ay-sheet-preview__cell ay-sheet-preview__cell--empty";
        el.dataset.pad = "1";
        grid.appendChild(el);
      }
    }

    grid.style.minWidth = scrollW + "px";
    grid.style.minHeight = scrollH + "px";
    grid.dataset.padded = "true";
  }

  function padActivePane(root) {
    var pane = root.querySelector(".ay-sheet-preview__pane:not([hidden])");
    if (!pane) {
      pane = root.querySelector(".ay-sheet-preview__pane");
    }
    if (!pane) return;
    ensureCanvas(pane);
    requestAnimationFrame(function () {
      padSheetGrid(pane, 0);
    });
  }

  function activateTab(root, tabName) {
    root.querySelectorAll(".ay-sheet-preview__pane").forEach(function (pane) {
      var active = pane.dataset.sheetName === tabName;
      pane.hidden = !active;
      pane.setAttribute("aria-hidden", active ? "false" : "true");
    });
    root.querySelectorAll(".ay-sheet-preview__tab").forEach(function (tab) {
      tab.classList.toggle("ay-sheet-preview__tab--active", tab.dataset.sheetTab === tabName);
    });
    padActivePane(root);
  }

  function mount(container) {
    var root = container.querySelector(".ay-sheet-preview");
    if (!root) return;
    var body = container.closest(".ay-artifact-panel__body");
    if (body) {
      body.classList.add("ay-artifact-panel__body--sheet-preview");
    }
    root.querySelectorAll(".ay-sheet-preview__tab").forEach(function (tab) {
      tab.addEventListener("click", function () {
        activateTab(root, tab.dataset.sheetTab);
      });
    });

    var scroll = root.querySelector(".ay-sheet-preview__scroll");
    if (scroll && typeof ResizeObserver !== "undefined") {
      if (root._sheetPreviewResizeObserver) {
        root._sheetPreviewResizeObserver.disconnect();
      }
      root._sheetPreviewResizeObserver = new ResizeObserver(function () {
        padActivePane(root);
      });
      root._sheetPreviewResizeObserver.observe(scroll);
    }

    padActivePane(root);
  }

  function teardown(container) {
    var body = container && container.closest(".ay-artifact-panel__body");
    if (body) {
      body.classList.remove("ay-artifact-panel__body--sheet-preview");
    }
    var root = container && container.querySelector(".ay-sheet-preview");
    if (root && root._sheetPreviewResizeObserver) {
      root._sheetPreviewResizeObserver.disconnect();
      delete root._sheetPreviewResizeObserver;
    }
  }

  window.AyronSheetPreview = {
    mount: mount,
    teardown: teardown,
  };
})();
