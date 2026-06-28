window.AyronUI = (function () {
  var dialog = null;
  var form = null;
  var activeInput = null;
  var titleEl = null;
  var bodyEl = null;
  var defaultTitle = "";
  var defaultBody = "";
  var toastStack = null;
  var dismissMs = 4000;

  function init() {
    dialog = document.getElementById("ay-confirm-dialog");
    form = document.getElementById("ay-confirm-delete-form");
    activeInput = document.getElementById("ay-confirm-delete-active");
    titleEl = document.getElementById("ay-confirm-dialog-title");
    bodyEl = document.getElementById("ay-confirm-dialog-body");
    toastStack = document.getElementById("ay-toast-stack");

    if (titleEl) defaultTitle = titleEl.textContent;
    if (bodyEl) defaultBody = bodyEl.textContent;

    document.body.addEventListener("click", function (e) {
      var btn = e.target.closest("[data-confirm-delete]");
      if (!btn) return;
      e.preventDefault();
      openConfirmDelete({
        url: btn.getAttribute("data-delete-url"),
        target: btn.getAttribute("data-delete-target"),
        active: btn.getAttribute("data-delete-active") === "1",
        swap: btn.getAttribute("data-delete-swap") || "delete",
        select: btn.getAttribute("data-delete-select") || "",
        include: btn.getAttribute("data-delete-include") || "",
        title: btn.getAttribute("data-confirm-title") || "",
        body: btn.getAttribute("data-confirm-body") || "",
      });
      var details = btn.closest("details");
      if (details) details.open = false;
    });

    var cancelBtn = document.getElementById("ay-confirm-delete-cancel");
    if (cancelBtn) {
      cancelBtn.addEventListener("click", closeConfirm);
    }

    if (dialog) {
      dialog.addEventListener("click", function (e) {
        if (e.target === dialog) closeConfirm();
      });
    }

    document.body.addEventListener("ayronToast", function (e) {
      showToast(e.detail || {});
    });

    if (form) {
      form.addEventListener("htmx:afterRequest", function (e) {
        if (!e.detail.successful) return;
        var target = form.getAttribute("hx-target") || "";
        if (target.indexOf("#sidebar-chat-") === 0) {
          var chatId = target.slice("#sidebar-chat-".length);
          document.querySelectorAll('[data-sidebar-chat-id="' + chatId + '"]').forEach(function (el) {
            el.remove();
          });
        }
        if (target.indexOf("#saved-card-") === 0) {
          var cardId = target.slice("#saved-card-".length);
          document.querySelectorAll('[data-saved-card-id="' + cardId + '"]').forEach(function (el) {
            el.remove();
          });
        }
        closeConfirm();
      });
    }

    document.addEventListener("click", function (e) {
      document.querySelectorAll(".ay-sidebar__menu-wrap[open], .ay-saved-card__menu-wrap[open]").forEach(function (details) {
        if (!details.contains(e.target)) {
          details.open = false;
        }
      });
    });

    function resetSavedCardRenameToggles() {
      document.querySelectorAll(".ay-saved-card__rename-toggle:checked").forEach(function (toggle) {
        toggle.checked = false;
      });
    }

    resetSavedCardRenameToggles();
    window.addEventListener("pageshow", resetSavedCardRenameToggles);

    document.body.addEventListener("htmx:afterSwap", function (e) {
      if (!e.detail.target || !e.detail.target.classList || !e.detail.target.classList.contains("ay-saved-card")) return;
      var toggle = e.detail.target.querySelector(".ay-saved-card__rename-toggle");
      if (toggle) toggle.checked = false;
    });
  }

  function openConfirmDelete(opts) {
    if (!form || !dialog) return;
    form.setAttribute("hx-post", opts.url || "");
    form.setAttribute("hx-target", opts.target || "");
    form.setAttribute("hx-swap", opts.swap || "delete");
    if (opts.select) {
      form.setAttribute("hx-select", opts.select);
    } else {
      form.removeAttribute("hx-select");
    }
    if (opts.include) {
      form.setAttribute("hx-include", opts.include);
    } else {
      form.removeAttribute("hx-include");
    }
    if (titleEl) {
      titleEl.textContent = opts.title || defaultTitle;
    }
    if (bodyEl) {
      bodyEl.textContent = opts.body || defaultBody;
    }
    if (activeInput) {
      activeInput.value = opts.active ? "1" : "";
    }
    if (window.htmx) window.htmx.process(form);
    dialog.showModal();
  }

  function closeConfirm() {
    if (dialog) dialog.close();
  }

  function showToast(detail) {
    var message = detail.message || "";
    if (!message || !toastStack) return;

    var toast = document.createElement("div");
    toast.className = "ay-toast";
    toast.setAttribute("role", "status");

    toast.innerHTML =
      '<span class="ay-toast__icon" aria-hidden="true">' +
      '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
      '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg></span>' +
      '<span class="ay-toast__message"></span>' +
      '<button type="button" class="ay-toast__close" aria-label="Cerrar">' +
      '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
      '<path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg></button>';

    toast.querySelector(".ay-toast__message").textContent = message;

    var closeBtn = toast.querySelector(".ay-toast__close");
    var timer = window.setTimeout(function () {
      removeToast(toast);
    }, dismissMs);

    closeBtn.addEventListener("click", function () {
      window.clearTimeout(timer);
      removeToast(toast);
    });

    toastStack.appendChild(toast);
  }

  function removeToast(toast) {
    if (!toast || !toast.parentNode) return;
    toast.classList.add("ay-toast--leaving");
    window.setTimeout(function () {
      if (toast.parentNode) toast.parentNode.removeChild(toast);
    }, 180);
  }

  return {
    init: init,
    showToast: showToast,
    openConfirmDelete: openConfirmDelete,
    closeConfirm: closeConfirm,
  };
})();

document.addEventListener("DOMContentLoaded", function () {
  if (window.AyronUI) window.AyronUI.init();
});
