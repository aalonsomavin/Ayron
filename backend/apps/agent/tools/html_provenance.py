import json
import re

PROVENANCE_BRIDGE_SCRIPT = """
(function () {
  var cfg = window.__AYRON_PROVENANCE__ || {};
  var fileId = cfg.fileId || "";

  if (!fileId || window.parent === window) {
    return;
  }

  document.addEventListener(
    "click",
    function (e) {
      var el = e.target.closest("[data-ay-claim]");
      if (!el) return;
      var claimKey = (el.getAttribute("data-ay-claim") || "").trim();
      if (!claimKey) return;
      e.preventDefault();
      e.stopPropagation();
      window.parent.postMessage(
        { type: "ayron:provenance-open", claimKey: claimKey, fileId: fileId },
        "*"
      );
    },
    true
  );

  document.querySelectorAll("[data-ay-claim]").forEach(function (el) {
    el.classList.add("ay-claim-interactive");
    if (!el.getAttribute("title")) {
      el.setAttribute("title", "Ver procedencia");
    }
  });
})();
"""


def inject_provenance_bridge(html: str, file_id: str) -> str:
    if not file_id or not html:
        return html
    if "ay-dash-page" not in html:
        return html

    config_script = (
        "<script>window.__AYRON_PROVENANCE__="
        f"{json.dumps({'fileId': str(file_id)})}"
        ";</script>"
    )
    injection = config_script + f"<script>{PROVENANCE_BRIDGE_SCRIPT.strip()}</script>"

    if re.search(r"</body>", html, re.IGNORECASE):
        return re.sub(
            r"</body>",
            injection + "</body>",
            html,
            count=1,
            flags=re.IGNORECASE,
        )
    return html + injection
