/**
 * Shared Light/Dark toggle for Django chrome.
 * Uses the same localStorage key as the SPA (`swarm_theme`) so the preference
 * survives Home ↔ operator page hops. Applies before first paint when possible.
 */
(function chromeTheme() {
  var KEY = "swarm_theme";

  function readTheme() {
    try {
      var stored = localStorage.getItem(KEY);
      if (stored === "light" || stored === "dark") return stored;
    } catch (err) {
      /* storage unavailable */
    }
    return "dark";
  }

  function applyTheme(theme) {
    var root = document.documentElement;
    root.setAttribute("data-bs-theme", theme);
    root.setAttribute("data-os-theme", theme);
    try {
      localStorage.setItem(KEY, theme);
    } catch (err) {
      /* persistence is best-effort */
    }
    var btn = document.getElementById("os-theme-toggle");
    if (btn) {
      btn.setAttribute(
        "aria-label",
        theme === "dark" ? "Switch to light theme" : "Switch to dark theme",
      );
    }
  }

  applyTheme(readTheme());

  document.addEventListener("DOMContentLoaded", function () {
    applyTheme(readTheme());
    var btn = document.getElementById("os-theme-toggle");
    if (!btn) return;
    btn.addEventListener("click", function () {
      applyTheme(readTheme() === "dark" ? "light" : "dark");
    });
  });
})();
