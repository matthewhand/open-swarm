// Teams admin page logic (loaded via {% static %} from teams_admin.html).
const modal = document.getElementById('confirmDeleteModal');
if (modal) {
  modal.addEventListener('show.bs.modal', function (event) {
    const button = event.relatedTarget;
    const teamId = button?.getAttribute('data-team-id') || '';
    document.getElementById('deleteTeamId').textContent = teamId;
    document.getElementById('deleteTeamIdInput').value = teamId;
  });
}

function getCsrfToken() {
  const input = document.querySelector("[name=csrfmiddlewaretoken]");
  if (input && input.value) return input.value;
  try {
    const match = document.cookie
      .split("; ")
      .find((row) => row.startsWith("csrftoken="));
    return match ? decodeURIComponent(match.split("=").slice(1).join("=")) : "";
  } catch {
    return "";
  }
}

function setHerdrStatus(message) {
  const el = document.getElementById("herdr-agent-status");
  if (el) el.textContent = message || "";
}

async function addHerdrMember(name, remote) {
  const headers = {
    Accept: "application/json",
    "Content-Type": "application/json",
  };
  const csrf = getCsrfToken();
  if (csrf) headers["X-CSRFToken"] = csrf;
  return fetch("/v1/herdr-agents/", {
    method: "POST",
    headers,
    credentials: "same-origin",
    body: JSON.stringify({ name, remote: remote || "" }),
  });
}

async function discoverHerdrAgents() {
  setHerdrStatus("Discovering live Herdr members…");
  const response = await fetch("/v1/herdr-agents/discover/", {
    headers: { Accept: "application/json" },
    credentials: "same-origin",
  });
  const wrap = document.getElementById("herdr-discover-wrap");
  const list = document.getElementById("herdr-discover-list");
  if (!wrap || !list) return;
  if (!response.ok) {
    setHerdrStatus("Discover failed (" + response.status + ").");
    return;
  }
  const body = await response.json();
  const items = Array.isArray(body.data) ? body.data : [];
  list.replaceChildren();
  wrap.hidden = false;
  if (!items.length) {
    const empty = document.createElement("li");
    empty.textContent = body.herdr_available === false
      ? "herdr CLI not available here (cloud CI mocks it)."
      : "No live Herdr agents or workspaces.";
    list.appendChild(empty);
    setHerdrStatus(empty.textContent);
    return;
  }
  for (const item of items) {
    const li = document.createElement("li");
    li.className = "d-flex align-items-center gap-2 mb-1";
    const label = document.createElement("span");
    label.textContent = (item.name || "") + " · " + (item.source || "agent") + " · localhost";
    li.appendChild(label);
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "btn btn-sm btn-outline-primary";
    btn.textContent = item.added ? "Added" : "Add as member";
    btn.disabled = Boolean(item.added);
    btn.addEventListener("click", async function () {
      const res = await addHerdrMember(item.name, item.remote || "");
      if (res.ok || res.status === 409) {
        btn.textContent = "Added";
        btn.disabled = true;
        setHerdrStatus("Added " + item.name + ".");
        return;
      }
      setHerdrStatus("Add failed (" + res.status + ").");
    });
    li.appendChild(btn);
    list.appendChild(li);
  }
  setHerdrStatus("Found " + items.length + " live Herdr member(s).");
}

document.querySelector("[data-action='discover-herdr-agents']")?.addEventListener("click", function () {
  discoverHerdrAgents();
});
