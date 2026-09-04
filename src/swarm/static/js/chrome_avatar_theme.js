/**
 * Settings avatar-theme picker. Same localStorage key as the SPA
 * (`swarm_avatar_theme`) so the choice survives Settings ↔ Chat hops.
 */
(function chromeAvatarTheme() {
  var KEY = "swarm_avatar_theme";
  var EVENT = "swarm:set-avatar-theme";

  function readTheme() {
    try {
      var stored = localStorage.getItem(KEY);
      if (stored === "default" || stored === "blobs") return stored;
    } catch (err) {
      /* storage unavailable */
    }
    return "default";
  }

  function writeTheme(theme) {
    var next = theme === "blobs" ? "blobs" : "default";
    try {
      if (next === "default") {
        localStorage.removeItem(KEY);
      } else {
        localStorage.setItem(KEY, next);
      }
    } catch (err) {
      /* persistence is best-effort */
    }
    try {
      window.dispatchEvent(new CustomEvent(EVENT, { detail: next }));
    } catch (err) {
      /* CustomEvent unavailable */
    }
    return next;
  }

  document.addEventListener("DOMContentLoaded", function () {
    var select = document.getElementById("os-avatar-theme");
    if (!select) return;
    select.value = readTheme();
    select.addEventListener("change", function () {
      writeTheme(select.value);
    });
  });
})();
