(function () {
  var WIDTH_KEY = "ayron-sidebar-width";
  var POPOVER_SHOW_DELAY = 320;
  var POPOVER_HIDE_DELAY = 120;
  var POPOVER_SUPPRESS_MS = 450;

  window.AyronSidebar = {
    shellEl: null,
    sidebarEl: null,
    toggleEl: null,
    toggleWrapEl: null,
    popoverEl: null,
    width: 256,
    collapsed: false,
    popoverShowTimer: null,
    popoverHideTimer: null,
    popoverSuppressUntil: 0,

    init: function (options) {
      this.shellEl = options.shellEl;
      this.sidebarEl = options.sidebarEl;
      if (!this.shellEl || !this.sidebarEl) return;

      this.toggleEl = this.shellEl.querySelector("[data-sidebar-open]");
      this.toggleWrapEl = this.shellEl.querySelector("[data-sidebar-toggle-wrap]");
      this.popoverEl = this.shellEl.querySelector("[data-sidebar-popover]");

      localStorage.removeItem("ayron-sidebar-collapsed");

      var storedWidth = parseInt(localStorage.getItem(WIDTH_KEY) || "", 10);
      if (!isNaN(storedWidth)) {
        this.width = storedWidth;
      }

      this.setWidth(this.width);
      this.open();

      var self = this;
      this.initResize();

      var closeBtn = this.sidebarEl.querySelector("[data-sidebar-close]");
      if (closeBtn) {
        closeBtn.addEventListener("click", function () {
          self.close();
        });
      }
      if (this.toggleEl) {
        this.toggleEl.addEventListener("click", function () {
          self.hidePopover();
          self.open();
        });
      }
      this.initPopoverHover();
    },

    hidePopover: function () {
      if (!this.popoverEl) return;
      clearTimeout(this.popoverShowTimer);
      clearTimeout(this.popoverHideTimer);
      this.popoverEl.classList.remove("is-visible");
      this.popoverEl.setAttribute("aria-hidden", "true");
    },

    initPopoverHover: function () {
      if (!this.toggleWrapEl || !this.popoverEl) return;

      var self = this;

      function scheduleShow() {
        if (!self.collapsed) return;
        if (Date.now() < self.popoverSuppressUntil) return;
        clearTimeout(self.popoverHideTimer);
        clearTimeout(self.popoverShowTimer);
        self.popoverShowTimer = setTimeout(function () {
          if (!self.collapsed) return;
          if (Date.now() < self.popoverSuppressUntil) return;
          self.popoverEl.classList.add("is-visible");
          self.popoverEl.setAttribute("aria-hidden", "false");
        }, POPOVER_SHOW_DELAY);
      }

      function scheduleHide() {
        clearTimeout(self.popoverShowTimer);
        clearTimeout(self.popoverHideTimer);
        self.popoverHideTimer = setTimeout(function () {
          self.hidePopover();
        }, POPOVER_HIDE_DELAY);
      }

      this.toggleWrapEl.addEventListener("mouseenter", scheduleShow);
      this.toggleWrapEl.addEventListener("mouseleave", scheduleHide);
      this.popoverEl.addEventListener("mouseenter", function () {
        clearTimeout(self.popoverHideTimer);
      });
      this.popoverEl.addEventListener("mouseleave", scheduleHide);
    },

    setWidth: function (width) {
      var minWidth = 200;
      var maxWidth = Math.min(420, Math.max(minWidth, Math.floor(window.innerWidth * 0.4)));
      var clamped = Math.min(maxWidth, Math.max(minWidth, width));
      this.width = clamped;
      this.shellEl.style.setProperty("--sidebar-width", clamped + "px");
      localStorage.setItem(WIDTH_KEY, String(clamped));
      return clamped;
    },

    initResize: function () {
      var handle = this.sidebarEl.querySelector("[data-sidebar-resize]");
      if (!handle) return;

      var self = this;
      handle.addEventListener("pointerdown", function (e) {
        if (self.collapsed) return;
        e.preventDefault();
        var startX = e.clientX;
        var startWidth = self.width;
        handle.setPointerCapture(e.pointerId);
        self.shellEl.classList.add("ay-shell--sidebar-resizing");

        function onMove(ev) {
          self.setWidth(startWidth + (ev.clientX - startX));
        }

        function onUp(ev) {
          if (handle.hasPointerCapture(ev.pointerId)) {
            handle.releasePointerCapture(ev.pointerId);
          }
          self.shellEl.classList.remove("ay-shell--sidebar-resizing");
          document.removeEventListener("pointermove", onMove);
          document.removeEventListener("pointerup", onUp);
          document.removeEventListener("pointercancel", onUp);
        }

        document.addEventListener("pointermove", onMove);
        document.addEventListener("pointerup", onUp);
        document.addEventListener("pointercancel", onUp);
      });
    },

    updateToggle: function () {
      if (!this.toggleEl) return;
      this.toggleEl.setAttribute("aria-hidden", this.collapsed ? "false" : "true");
    },

    close: function () {
      if (!this.shellEl) return;
      this.collapsed = true;
      this.popoverSuppressUntil = Date.now() + POPOVER_SUPPRESS_MS;
      this.hidePopover();
      this.shellEl.classList.add("ay-shell--sidebar-collapsed");
      this.updateToggle();
    },

    open: function () {
      if (!this.shellEl) return;
      this.collapsed = false;
      this.hidePopover();
      this.shellEl.classList.remove("ay-shell--sidebar-collapsed");
      this.updateToggle();
    },
  };
})();
