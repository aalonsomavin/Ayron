(function () {
  var ICONS = {
    database:
      '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"></ellipse><path d="M3 5v14c0 1.7 4 3 9 3s9-1.3 9-3V5"></path></svg>',
    sheet:
      '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"></rect><path d="M3 9h18M3 15h18M9 3v18"></path></svg>',
    file:
      '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><path d="M14 2v6h6"></path></svg>',
    merge:
      '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#2f5fd6" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M9 17H7A5 5 0 0 1 7 7h2"></path><path d="M15 7h2a5 5 0 0 1 0 10h-2"></path><path d="M8 12h8"></path></svg>',
    expand:
      '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 3h6v6"/><path d="m21 3-7 7"/><path d="m3 21 7-7"/><path d="M9 21H3v-6"/></svg>',
    close:
      '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>',
    arrow:
      '<svg class="ay-origin-diagram__arrow" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m9 18 6-6-6-6"></path></svg>',
    arrowAccent:
      '<svg class="ay-origin-diagram__arrow ay-origin-diagram__arrow--accent" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m9 18 6-6-6-6"></path></svg>',
    convergeIn:
      '<svg width="24" height="72" viewBox="0 0 24 72" fill="none"><path d="M2 8 C10 8 10 36 14 36" stroke="currentColor" stroke-width="1.7"/><path d="M2 64 C10 64 10 36 14 36" stroke="currentColor" stroke-width="1.7"/></svg>',
    convergeInThree:
      '<svg width="24" height="96" viewBox="0 0 24 96" fill="none"><path d="M2 8 C10 8 10 48 14 48" stroke="currentColor" stroke-width="1.7"/><path d="M2 48 H14" stroke="currentColor" stroke-width="1.7"/><path d="M2 88 C10 88 10 48 14 48" stroke="currentColor" stroke-width="1.7"/></svg>',
    arrowOut:
      '<svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M2 12 H16" stroke="currentColor" stroke-width="1.8"/><path d="M12 7 L17 12 L12 17" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  };

  var dialogEl = null;
  var dialogBodyEl = null;

  function readPayload(node) {
    var scriptId = node.dataset.diagramId;
    if (!scriptId) return null;
    var script = document.getElementById(scriptId);
    if (!script) return null;
    try {
      return JSON.parse(script.textContent);
    } catch (_err) {
      return null;
    }
  }

  function escapeText(value) {
    return String(value == null ? "" : value);
  }

  function createNode(options) {
    var node = document.createElement("button");
    node.type = "button";
    node.className = "ay-origin-diagram__node " + (options.className || "");
    node.dataset.nodeKind = options.kind || "source";
    node.dataset.nodeLabel = options.label || "";

    if (options.detail) {
      node.dataset.nodeDetail = options.detail;
    }

    if (options.kicker) {
      var kicker = document.createElement("div");
      kicker.className = "ay-origin-diagram__node-kicker";
      kicker.textContent = options.kicker;
      node.appendChild(kicker);
    }

    if (options.mergeIcon) {
      var mergeIconWrap = document.createElement("div");
      mergeIconWrap.className = "ay-origin-diagram__node-merge-icon";
      mergeIconWrap.innerHTML = ICONS.merge;
      node.appendChild(mergeIconWrap);
    }

    if (options.icon) {
      var head = document.createElement("div");
      head.className = "ay-origin-diagram__node-head";
      var iconWrap = document.createElement("span");
      iconWrap.className =
        "ay-origin-diagram__node-icon ay-origin-diagram__node-icon--" + options.icon;
      iconWrap.innerHTML = ICONS[options.icon] || "";
      head.appendChild(iconWrap);
      var labelEl = document.createElement("span");
      labelEl.className = "ay-origin-diagram__node-label";
      labelEl.textContent = options.label;
      head.appendChild(labelEl);
      node.appendChild(head);
    } else {
      var plainLabel = document.createElement("div");
      plainLabel.className = "ay-origin-diagram__node-label";
      plainLabel.textContent = options.label;
      node.appendChild(plainLabel);
    }

    var subtitle = options.subtitle || options.meta || "";
    if (subtitle) {
      var subtitleEl = document.createElement("div");
      subtitleEl.className = "ay-origin-diagram__node-subtitle";
      subtitleEl.textContent = subtitle;
      node.appendChild(subtitleEl);
    }

    return node;
  }

  function createConnector(className, svgKey) {
    var connector = document.createElement("div");
    connector.className = "ay-origin-diagram__connector " + className;
    connector.innerHTML = ICONS[svgKey] || "";
    connector.setAttribute("aria-hidden", "true");
    return connector;
  }

  function renderBranchLayout(diagram, patternClass) {
    var layout = document.createElement("div");
    layout.className =
      "ay-origin-diagram__layout ay-origin-diagram__layout--" + patternClass;

    var sourcesCol = document.createElement("div");
    sourcesCol.className = "ay-origin-diagram__col ay-origin-diagram__col--sources";
    (diagram.sources || []).forEach(function (source) {
      sourcesCol.appendChild(
        createNode({
          className: "ay-origin-diagram__node--source",
          kind: "source",
          label: source.label,
          subtitle: source.subtitle || source.meta,
          icon: source.icon,
          detail: source.detail,
        })
      );
    });

    var mergeCol = document.createElement("div");
    mergeCol.className = "ay-origin-diagram__col ay-origin-diagram__col--merge";
    if (diagram.merge) {
      mergeCol.appendChild(
        createNode({
          className: "ay-origin-diagram__node--merge",
          kind: "merge",
          label: diagram.merge.label,
          subtitle: diagram.merge.detail,
          mergeIcon: true,
          detail: diagram.merge.detail,
        })
      );
    }

    var resultCol = document.createElement("div");
    resultCol.className = "ay-origin-diagram__col ay-origin-diagram__col--result";
    if (diagram.result) {
      resultCol.appendChild(
        createNode({
          className: "ay-origin-diagram__node--result",
          kind: "result",
          kicker: "Resultado",
          label: diagram.result.label,
          subtitle: diagram.result.subtitle,
          detail: diagram.result.detail,
        })
      );
    }

    var sourceCount = (diagram.sources || []).length;
    layout.appendChild(sourcesCol);
    layout.appendChild(
      createConnector(
        "ay-origin-diagram__connector--in",
        sourceCount > 2 ? "convergeInThree" : "convergeIn"
      )
    );
    layout.appendChild(mergeCol);
    layout.appendChild(createConnector("ay-origin-diagram__connector--out", "arrowOut"));
    layout.appendChild(resultCol);
    return layout;
  }

  function renderChainLayout(diagram) {
    var layout = document.createElement("div");
    layout.className = "ay-origin-diagram__layout ay-origin-diagram__layout--chain";

    var source = (diagram.sources || [])[0];
    if (source) {
      layout.appendChild(
        createNode({
          className: "ay-origin-diagram__node--source",
          kind: "source",
          label: source.label,
          subtitle: source.subtitle || source.meta,
          icon: source.icon,
          detail: source.detail,
        })
      );
    }

    (diagram.transforms || []).forEach(function (transform) {
      var arrow = document.createElement("div");
      arrow.innerHTML = ICONS.arrow;
      layout.appendChild(arrow.firstChild);
      layout.appendChild(
        createNode({
          className: "ay-origin-diagram__node--transform",
          kind: "transform",
          label: transform.label,
          subtitle: transform.detail,
          detail: transform.detail,
        })
      );
    });

    if (diagram.result) {
      var resultArrow = document.createElement("div");
      resultArrow.innerHTML = ICONS.arrowAccent;
      layout.appendChild(resultArrow.firstChild);
      layout.appendChild(
        createNode({
          className: "ay-origin-diagram__node--result",
          kind: "result",
          kicker: "Resultado",
          label: diagram.result.label,
          subtitle: diagram.result.subtitle,
          detail: diagram.result.detail,
        })
      );
    }

    return layout;
  }

  function renderStage(diagram) {
    if (diagram.pattern === "multi_source") {
      return renderBranchLayout(diagram, "multi_source");
    }
    if (diagram.pattern === "chain") {
      return renderChainLayout(diagram);
    }
    return renderBranchLayout(diagram, "converge");
  }

  function showDetail(card, node) {
    var detailEl = card.querySelector(".ay-origin-diagram__detail");
    if (!detailEl) return;

    var detailText = node.dataset.nodeDetail || "";
    var label = node.dataset.nodeLabel || "";
    card.querySelectorAll(".ay-origin-diagram__node.is-active").forEach(function (active) {
      active.classList.remove("is-active");
    });

    if (!detailText) {
      detailEl.hidden = true;
      detailEl.innerHTML = "";
      return;
    }

    node.classList.add("is-active");
    detailEl.hidden = false;
    detailEl.innerHTML =
      '<div class="ay-origin-diagram__detail-title">' +
      escapeText(label) +
      "</div>" +
      '<div class="ay-origin-diagram__detail-body">' +
      escapeText(detailText) +
      "</div>";
  }

  function bindInteractions(card) {
    if (!card) return;
    card.querySelectorAll(".ay-origin-diagram__node").forEach(function (node) {
      node.addEventListener("click", function () {
        showDetail(card, node);
      });
    });
  }

  function buildToolbar(options) {
    var toolbar = document.createElement("div");
    toolbar.className = "ay-origin-diagram__header";

    var title = document.createElement("p");
    title.className = "ay-origin-diagram__header-title";
    title.textContent = options.title || "Origen de los datos";
    toolbar.appendChild(title);

    var actions = document.createElement("div");
    actions.className = "ay-origin-diagram__header-actions";

    if (!options.hideExpand) {
      var expandBtn = document.createElement("button");
      expandBtn.type = "button";
      expandBtn.className = "ay-origin-diagram__header-btn";
      expandBtn.dataset.originDiagramExpand = "true";
      expandBtn.title = "Pantalla completa";
      expandBtn.setAttribute("aria-label", "Pantalla completa");
      expandBtn.innerHTML = ICONS.expand;
      actions.appendChild(expandBtn);
    }

    toolbar.appendChild(actions);
    return toolbar;
  }

  function buildCard(diagram, options) {
    options = options || {};
    var card = document.createElement("div");
    card.className = "ay-card ay-origin-diagram__card";
    if (options.expanded) {
      card.classList.add("ay-origin-diagram__card--expanded");
    }

    if (!options.hideToolbar) {
      card.appendChild(
        buildToolbar({
          title: options.title,
          hideExpand: options.hideExpand,
        })
      );
    }

    var scroll = document.createElement("div");
    scroll.className = "ay-origin-diagram__scroll";

    var stage = document.createElement("div");
    stage.className = "ay-origin-diagram__stage";
    stage.appendChild(renderStage(diagram));
    scroll.appendChild(stage);
    card.appendChild(scroll);

    if (diagram.caption || diagram.hint) {
      var footer = document.createElement("div");
      footer.className = "ay-origin-diagram__footer";
      if (diagram.caption) {
        var caption = document.createElement("div");
        caption.className = "ay-origin-diagram__caption";
        caption.textContent = diagram.caption;
        footer.appendChild(caption);
      }
      if (diagram.hint) {
        var hint = document.createElement("div");
        hint.className = "ay-origin-diagram__hint";
        hint.textContent = diagram.hint;
        footer.appendChild(hint);
      }
      card.appendChild(footer);
    }

    var detail = document.createElement("div");
    detail.className = "ay-origin-diagram__detail";
    detail.hidden = true;
    card.appendChild(detail);

    bindInteractions(card);
    return card;
  }

  function ensureDialog() {
    if (dialogEl) return dialogEl;
    dialogEl = document.getElementById("ay-origin-diagram-dialog");
    dialogBodyEl = document.getElementById("ay-origin-diagram-dialog-body");
    if (!dialogEl || !dialogBodyEl) return null;

    if (dialogEl.dataset.bound === "true") return dialogEl;
    dialogEl.dataset.bound = "true";

    dialogEl.querySelectorAll("[data-origin-diagram-close]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        dialogEl.close();
      });
    });

    dialogEl.addEventListener("click", function (event) {
      if (event.target === dialogEl) dialogEl.close();
    });

    dialogEl.addEventListener("close", function () {
      dialogBodyEl.innerHTML = "";
    });

    return dialogEl;
  }

  function openFullscreen(wrapper) {
    var dialog = ensureDialog();
    var diagram = readPayload(wrapper);
    if (!dialog || !diagram) return;

    dialogBodyEl.innerHTML = "";
    var card = buildCard(diagram, {
      expanded: true,
      hideExpand: true,
      hideToolbar: false,
      title: "Origen de los datos",
    });
    dialogBodyEl.appendChild(card);

    if (typeof dialog.showModal === "function") {
      dialog.showModal();
    }
  }

  function bindWrapper(wrapper) {
    var expandBtn = wrapper.querySelector("[data-origin-diagram-expand]");
    if (expandBtn && !expandBtn.dataset.bound) {
      expandBtn.dataset.bound = "true";
      expandBtn.addEventListener("click", function () {
        openFullscreen(wrapper);
      });
    }
  }

  function buildElement(diagram) {
    var wrapper = document.createElement("div");
    wrapper.className = "ay-origin-diagram";
    var diagramId =
      "origin-stream-" + Date.now() + "-" + Math.random().toString(36).slice(2, 8);
    wrapper.dataset.diagramId = diagramId;

    var script = document.createElement("script");
    script.type = "application/json";
    script.id = diagramId;
    script.textContent = JSON.stringify(diagram);
    wrapper.appendChild(script);
    wrapper.appendChild(buildCard(diagram));
    bindWrapper(wrapper);
    return wrapper;
  }

  function mount(node) {
    if (!node || node.dataset.originDiagramMounted) return;
    node.dataset.originDiagramMounted = "1";
    var diagram = readPayload(node);
    var card = node.querySelector(".ay-origin-diagram__card");
    if (!diagram || !card) return;

    if (!card.querySelector(".ay-origin-diagram__header")) {
      card.insertBefore(buildToolbar({}), card.firstChild);
    }

    var stage = card.querySelector(".ay-origin-diagram__stage");
    if (stage && !stage.firstChild) {
      stage.appendChild(renderStage(diagram));
    }

    if (!card.querySelector(".ay-origin-diagram__scroll") && stage) {
      var scroll = document.createElement("div");
      scroll.className = "ay-origin-diagram__scroll";
      if (stage.parentNode === card) {
        card.replaceChild(scroll, stage);
        scroll.appendChild(stage);
      }
    }

    bindInteractions(card);
    bindWrapper(node);
  }

  function mountAll(root) {
    (root || document).querySelectorAll(".ay-origin-diagram").forEach(mount);
    ensureDialog();
  }

  window.AyronOriginDiagram = {
    create: buildElement,
    mount: mount,
    mountAll: mountAll,
    openFullscreen: openFullscreen,
  };
})();
