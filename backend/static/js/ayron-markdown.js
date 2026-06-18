(function () {
  const buffers = new WeakMap();
  let hooksInstalled = false;

  function configureParser() {
    if (typeof marked === "undefined") return;
    marked.setOptions({
      breaks: true,
      gfm: true,
    });
  }

  function configureSanitizer() {
    if (typeof DOMPurify === "undefined" || hooksInstalled) return;
    DOMPurify.addHook("afterSanitizeAttributes", function (node) {
      if (node.tagName === "A") {
        node.setAttribute("target", "_blank");
        node.setAttribute("rel", "noopener noreferrer");
      }
    });
    hooksInstalled = true;
  }

  function sanitize(html) {
    if (typeof DOMPurify === "undefined") return "";
    return DOMPurify.sanitize(html, {
      FORBID_TAGS: ["table", "thead", "tbody", "tr", "th", "td"],
    });
  }

  function parseMarkdown(source) {
    if (!source || typeof marked === "undefined") return "";
    return sanitize(marked.parse(source));
  }

  function countFenceMarkers(source) {
    const matches = source.match(/^```/gm);
    return matches ? matches.length : 0;
  }

  function hasIncompleteInline(line) {
    if (!line) return false;
    if ((line.match(/\*\*/g) || []).length % 2 !== 0) return true;
    if ((line.match(/__/g) || []).length % 2 !== 0) return true;

    let backticks = 0;
    for (let i = 0; i < line.length; i += 1) {
      if (line[i] === "`") backticks += 1;
    }
    if (backticks % 2 !== 0) return true;

    const linkStart = line.lastIndexOf("[");
    if (linkStart !== -1) {
      const parenStart = line.indexOf("(", linkStart);
      if (parenStart !== -1 && line.indexOf(")", parenStart) === -1) return true;
    }

    return false;
  }

  function splitStableMarkdown(source) {
    if (!source) return ["", ""];

    if (countFenceMarkers(source) % 2 === 1) {
      const lastFence = source.lastIndexOf("```");
      return [source.slice(0, lastFence), source.slice(lastFence)];
    }

    const lines = source.split("\n");
    const lastLine = lines[lines.length - 1];
    if (lines.length > 0 && hasIncompleteInline(lastLine)) {
      const stable = lines.slice(0, -1).join("\n");
      const tail = (stable.length ? "\n" : "") + lastLine;
      return [stable, tail];
    }

    return [source, ""];
  }

  function appendTail(el, tail) {
    if (!tail) return;
    const tailEl = document.createElement("span");
    tailEl.className = "ay-markdown__tail";
    tailEl.textContent = tail;
    el.appendChild(tailEl);
  }

  function render(el, source, opts) {
    if (!el) return source || "";
    configureParser();
    configureSanitizer();
    el.classList.add("ay-markdown");
    const markdown = source != null ? source : buffers.get(el) || el.textContent || "";
    buffers.set(el, markdown);
    el.innerHTML = parseMarkdown(markdown);
    return markdown;
  }

  function renderStreaming(el, source, opts) {
    if (!el) return source || "";
    configureParser();
    configureSanitizer();
    el.classList.add("ay-markdown");
    const markdown = source != null ? source : "";
    buffers.set(el, markdown);
    const parts = splitStableMarkdown(markdown);
    const stable = parts[0];
    const tail = parts[1];
    el.innerHTML = stable ? parseMarkdown(stable) : "";
    appendTail(el, tail);
    return markdown;
  }

  function mount(el) {
    if (!el || el.dataset.mdMounted === "true") {
      return buffers.get(el) || "";
    }
    const source = el.textContent || "";
    el.dataset.mdMounted = "true";
    return render(el, source);
  }

  function mountAll(root) {
    (root || document).querySelectorAll(".ay-msg-agent__text").forEach(mount);
  }

  function getBuffer(el) {
    return buffers.get(el) || "";
  }

  window.AyronMarkdown = {
    render: render,
    renderStreaming: renderStreaming,
    mount: mount,
    mountAll: mountAll,
    getBuffer: getBuffer,
    splitStableMarkdown: splitStableMarkdown,
  };
})();
