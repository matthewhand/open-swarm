/**
 * Django AGENTS sidepane — same hide contract as the SPA AgentSidebar.
 * Persist hidden ids in localStorage.swarm_hidden_agents (no hide-all).
 */
(function agentSidebar() {
  var STORAGE_KEY = "swarm_hidden_agents";
  var MARK_COUNT = 6;

  function loadHidden() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return [];
      var parsed = JSON.parse(raw);
      if (!Array.isArray(parsed)) return [];
      return parsed.filter(function (id) {
        return typeof id === "string" && id.length > 0;
      });
    } catch (err) {
      return [];
    }
  }

  function saveHidden(ids) {
    var unique = [];
    ids.forEach(function (id) {
      if (id && unique.indexOf(id) === -1) unique.push(id);
    });
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(unique));
    } catch (err) {
      /* persistence is best-effort */
    }
    return unique;
  }

  function markIndex(id) {
    var hash = 0;
    for (var i = 0; i < id.length; i += 1) {
      hash = (hash * 31 + id.charCodeAt(i)) >>> 0;
    }
    return String(hash % MARK_COUNT);
  }

  function agentLabel(agent) {
    return agent.name || agent.id;
  }

  function matchesFilter(agent, query) {
    if (!query) return true;
    var hay = (agentLabel(agent) + " " + (agent.id || "") + " " + (agent.description || "")).toLowerCase();
    return hay.indexOf(query) !== -1;
  }

  function init() {
    var listEl = document.getElementById("os-agent-list");
    var hiddenListEl = document.getElementById("os-agent-hidden-list");
    var hiddenWrap = document.getElementById("os-agent-hidden-wrap");
    var hiddenToggle = document.getElementById("os-agent-hidden-toggle");
    var hiddenCount = document.getElementById("os-agent-hidden-count");
    var statusEl = document.getElementById("os-agent-status");
    var filterEl = document.getElementById("os-agent-filter");
    var menuEl = document.getElementById("os-agent-menu");
    var sidebar = document.getElementById("os-agent-sidebar");
    if (!listEl || !hiddenListEl || !statusEl || !menuEl || !sidebar) return;

    var agents = [];
    var hiddenIds = loadHidden();
    var hiddenOpen = false;
    var filter = "";

    function closeMenu() {
      menuEl.hidden = true;
      menuEl.replaceChildren();
      if (menuEl.parentElement && menuEl.parentElement !== document.body) {
        document.body.appendChild(menuEl);
      }
    }

    function openDrawer() {
      sidebar.classList.add("is-open");
      var backdrop = document.getElementById("os-sidebar-backdrop");
      if (backdrop) backdrop.hidden = false;
    }

    function closeDrawer() {
      sidebar.classList.remove("is-open");
      var backdrop = document.getElementById("os-sidebar-backdrop");
      if (backdrop) backdrop.hidden = true;
    }

    function makeLink(agent, hidden) {
      var link = document.createElement("a");
      link.href = "/chat?blueprint=" + encodeURIComponent(agent.id);
      link.className = "os-agent-item";
      var name = agentLabel(agent);
      link.setAttribute("aria-label", name);

      var role = (agent.role || "default").toLowerCase();
      if (["support", "gate", "skeptic", "default"].indexOf(role) === -1) {
        role = "default";
      }
      link.setAttribute("data-role", role);
      link.className = "os-agent-item os-agent-role-" + role;

      var dot = document.createElement("span");
      dot.className = "os-agent-dot";
      dot.setAttribute("data-mark", markIndex(agent.id));
      dot.setAttribute("data-role", role);
      dot.setAttribute("aria-hidden", "true");

      var text = document.createElement("span");
      text.className = "os-agent-item__text";
      var title = document.createElement("span");
      title.className = "os-agent-item__name";
      title.textContent = name;
      text.appendChild(title);
      if (role !== "default") {
        var badge = document.createElement("span");
        badge.className = "os-agent-role-badge os-agent-role-" + role;
        badge.setAttribute("data-role", role);
        badge.textContent = role;
        text.appendChild(badge);
      }
      if (agent.description) {
        var desc = document.createElement("span");
        desc.className = "os-agent-item__desc";
        desc.textContent = agent.description;
        text.appendChild(desc);
      }

      link.appendChild(dot);
      link.appendChild(text);
      link.addEventListener("contextmenu", function (event) {
        event.preventDefault();
        openMenu(event, agent, hidden);
      });
      return link;
    }

    function openMenu(event, agent, hidden) {
      menuEl.replaceChildren();
      var item = document.createElement("button");
      item.type = "button";
      item.setAttribute("role", "menuitem");
      item.className = "os-agent-menu__item";
      item.textContent = hidden ? "Unhide" : "Hide from sidebar";
      item.addEventListener("click", function () {
        if (hidden) {
          hiddenIds = saveHidden(hiddenIds.filter(function (id) { return id !== agent.id; }));
        } else {
          hiddenIds = saveHidden(hiddenIds.concat([agent.id]));
        }
        closeMenu();
        render();
      });
      menuEl.appendChild(item);
      var host = event.currentTarget.parentElement || event.currentTarget;
      host.appendChild(menuEl);
      menuEl.hidden = false;
      menuEl.classList.add("is-anchored");
    }

    function render() {
      var q = filter.trim().toLowerCase();
      var visible = agents.filter(function (agent) {
        return hiddenIds.indexOf(agent.id) === -1 && matchesFilter(agent, q);
      });
      var hidden = agents.filter(function (agent) {
        return hiddenIds.indexOf(agent.id) !== -1 && matchesFilter(agent, q);
      });

      listEl.replaceChildren();
      hiddenListEl.replaceChildren();

      if (!agents.length) {
        statusEl.hidden = false;
        return;
      }
      statusEl.hidden = true;

      if (!visible.length) {
        var empty = document.createElement("p");
        empty.className = "os-agent-status";
        empty.textContent = "No matching agents.";
        listEl.appendChild(empty);
      } else {
        visible.forEach(function (agent) {
          var li = document.createElement("li");
          li.appendChild(makeLink(agent, false));
          listEl.appendChild(li);
        });
      }

      if (hiddenWrap) {
        hiddenWrap.hidden = hidden.length === 0;
      }
      if (hiddenCount) hiddenCount.textContent = "(" + hidden.length + ")";
      hiddenListEl.hidden = !hiddenOpen;
      if (hiddenToggle) hiddenToggle.setAttribute("aria-expanded", hiddenOpen ? "true" : "false");

      hidden.forEach(function (agent) {
        var li = document.createElement("li");
        li.className = "os-agent-hidden__row";
        li.appendChild(makeLink(agent, true));
        var unhide = document.createElement("button");
        unhide.type = "button";
        unhide.className = "os-agent-unhide";
        unhide.setAttribute("aria-label", "Unhide " + agentLabel(agent));
        unhide.textContent = "Unhide";
        unhide.addEventListener("click", function () {
          hiddenIds = saveHidden(hiddenIds.filter(function (id) { return id !== agent.id; }));
          render();
        });
        li.appendChild(unhide);
        hiddenListEl.appendChild(li);
      });
    }

    if (hiddenToggle) {
      hiddenToggle.addEventListener("click", function () {
        hiddenOpen = !hiddenOpen;
        render();
      });
    }
    if (filterEl) {
      filterEl.addEventListener("input", function () {
        filter = filterEl.value;
        render();
      });
    }

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") closeMenu();
    });
    document.addEventListener("mousedown", function (event) {
      if (!menuEl.hidden && !menuEl.contains(event.target)) closeMenu();
    });

    var openBtn = document.getElementById("os-sidebar-open");
    var closeBtn = document.getElementById("os-sidebar-close");
    var backdrop = document.getElementById("os-sidebar-backdrop");
    if (openBtn) openBtn.addEventListener("click", openDrawer);
    if (closeBtn) closeBtn.addEventListener("click", closeDrawer);
    if (backdrop) backdrop.addEventListener("click", closeDrawer);

    fetch("/v1/blueprints/")
      .then(function (res) {
        if (!res.ok) throw new Error("status " + res.status);
        return res.json();
      })
      .then(function (payload) {
        agents = Array.isArray(payload && payload.data) ? payload.data : [];
        if (!agents.length) statusEl.textContent = "No agents yet.";
        render();
      })
      .catch(function () {
        agents = [];
        statusEl.textContent = "Could not load agents.";
        statusEl.hidden = false;
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
