// group-prompts.js
// Group prompts listing, CRUD operations, filtering, and pagination.
// Extracted from group_workspaces.html inline JS.

/* ===================== GROUP PROMPTS ===================== */
// — State —
let groupPromptsCurrentPage = 1;
let groupPromptsPageSize = 10;
let groupPromptsSearchTerm = "";

// — DOM Elements —
const groupPromptsTableBody = document.querySelector(
  "#group-prompts-table tbody"
);
const groupPromptsSearchInput = document.getElementById(
  "group-prompts-search-input"
);
const groupPromptsApplyFiltersBtn = document.getElementById(
  "group-prompts-apply-filters-btn"
);
const groupPromptsClearFiltersBtn = document.getElementById(
  "group-prompts-clear-filters-btn"
);
const groupPromptsPageSizeSelect = document.getElementById(
  "group-prompts-page-size-select"
);
const groupPromptsPagination = document.getElementById(
  "group-prompts-pagination-container"
);

const createGroupPromptBtn = document.getElementById(
  "create-group-prompt-btn"
);
const groupPromptModalEl = new bootstrap.Modal(
  document.getElementById("groupPromptModal")
);
const groupPromptForm = document.getElementById("group-prompt-form");
const groupPromptIdEl = document.getElementById("group-prompt-id");
const groupPromptNameEl = document.getElementById("group-prompt-name");

// — Fetch & render group prompts —
function fetchGroupPrompts() {
  groupPromptsTableBody.innerHTML = `
    <tr class="table-loading-row">
      <td colspan="2">
        <div class="spinner-border spinner-border-sm me-2"></div>
        Loading group prompts…
      </td>
    </tr>`;
  groupPromptsPagination.innerHTML = "";

  const params = new URLSearchParams({
    page: groupPromptsCurrentPage,
    page_size: groupPromptsPageSize,
  });
  if (groupPromptsSearchTerm) {
    params.append("search", groupPromptsSearchTerm);
  }

  fetch(`/api/group_prompts?${params}`)
    .then((r) =>
      r.ok ? r.json() : r.json().then((err) => Promise.reject(err))
    )
    .then((data) => {
      groupPromptsTableBody.innerHTML = "";
      if (!data.prompts || data.prompts.length === 0) {
        groupPromptsTableBody.innerHTML = `
          <tr>
            <td colspan="2" class="text-center p-4 text-muted">
              ${
                groupPromptsSearchTerm
                  ? "No group prompts found."
                  : "No group prompts created yet."
              }
            </td>
          </tr>`;
      } else {
        data.prompts.forEach((p) => renderGroupPromptRow(p));
      }
      renderGroupPromptsPagination(
        data.page,
        data.page_size,
        data.total_count
      );
    })
    .catch((err) => {
      console.error("Error loading group prompts:", err);
      groupPromptsTableBody.innerHTML = `
        <tr>
          <td colspan="2" class="text-center text-danger p-3">
            Error: ${err.error || err.message || "Unknown error"}
          </td>
        </tr>`;
    });
}

function renderGroupPromptRow(p) {
  const tr = document.createElement("tr");
  
  // Check if group allows modifications
  const groupStatus = window.currentGroupStatus || 'active';
  const canModify = (groupStatus === 'active');
  
  let actionsHtml = '';
  if (canModify) {
    actionsHtml = `
      <button class="btn btn-sm btn-primary" onclick="onEditGroupPrompt('${p.id}')" title="Edit">
        <i class="bi bi-pencil-fill"></i>
      </button>
      <button class="btn btn-sm btn-danger ms-1" onclick="onDeleteGroupPrompt('${p.id}', event)" title="Delete">
        <i class="bi bi-trash-fill"></i>
      </button>
    `;
  } else {
    actionsHtml = '<span class="text-muted small">—</span>';
  }
  
  tr.innerHTML = `
    <td title="${p.name}">${p.name}</td>
    <td>${actionsHtml}</td>`;
  groupPromptsTableBody.appendChild(tr);
}

function renderGroupPromptsPagination(page, pageSize, totalCount) {
  groupPromptsPagination.innerHTML = "";
  const totalPages = Math.ceil(totalCount / pageSize);
  if (totalPages <= 1) return;

  const ul = document.createElement("ul");
  ul.classList.add("pagination", "pagination-sm", "mb-0");

  // prev
  const prev = document.createElement("li");
  prev.classList.add("page-item", page <= 1 && "disabled");
  prev.innerHTML = `<a class="page-link" href="#">«</a>`;
  prev.querySelector("a").onclick = (e) => {
    e.preventDefault();
    if (page > 1) {
      groupPromptsCurrentPage--;
      fetchGroupPrompts();
    }
  };
  ul.append(prev);

  // pages
  for (let p = 1; p <= totalPages; p++) {
    const li = document.createElement("li");
    li.classList.add("page-item", p === page && "active");
    li.innerHTML = `<a class="page-link" href="#">${p}</a>`;
    li.querySelector("a").onclick = (e) => {
      e.preventDefault();
      if (p !== groupPromptsCurrentPage) {
        groupPromptsCurrentPage = p;
        fetchGroupPrompts();
      }
    };
    ul.append(li);
  }

  // next
  const next = document.createElement("li");
  next.classList.add("page-item", page >= totalPages && "disabled");
  next.innerHTML = `<a class="page-link" href="#">»</a>`;
  next.querySelector("a").onclick = (e) => {
    e.preventDefault();
    if (page < totalPages) {
      groupPromptsCurrentPage++;
      fetchGroupPrompts();
    }
  };
  ul.append(next);

  groupPromptsPagination.appendChild(ul);
}

// — Handlers —
createGroupPromptBtn?.addEventListener("click", () => {
  groupPromptIdEl.value = "";
  groupPromptNameEl.value = "";
  if (groupSimplemde) {
    // Clear the editor completely
    groupSimplemde.codemirror.setValue("");
    groupSimplemde.value("");
  }
  else groupPromptContentEl.value = "";
  document.getElementById("groupPromptModalLabel").textContent =
    "Create Group Prompt";
  groupPromptModalEl.show();
  
  // Force refresh after modal is fully shown
  setTimeout(() => {
    if (groupSimplemde) {
      groupSimplemde.codemirror.refresh();
      groupSimplemde.codemirror.focus();
    }
  }, 300);
});

// Add event listener for modal shown event
document.getElementById("groupPromptModal")?.addEventListener('shown.bs.modal', function () {
  if (groupSimplemde) {
    groupSimplemde.codemirror.refresh();
    groupSimplemde.codemirror.focus();
  }
});

groupPromptForm?.addEventListener("submit", (e) => {
  e.preventDefault();
  const id = groupPromptIdEl.value;
  const url = id ? `/api/group_prompts/${id}` : "/api/group_prompts";
  const method = id ? "PATCH" : "POST";
  const name = groupPromptNameEl.value.trim();
  const content = (
    groupSimplemde ? groupSimplemde.value() : groupPromptContentEl.value
  ).trim();
  if (!name || !content) return alert("Name & content are required.");

  const btn = document.getElementById("group-prompt-save-btn");
  btn.disabled = true;
  btn.innerHTML = `<span class="spinner-border spinner-border-sm me-1"></span>Saving…`;

  fetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, content }),
  })
    .then((r) =>
      r.ok ? r.json() : r.json().then((err) => Promise.reject(err))
    )
    .then(() => {
      groupPromptModalEl.hide();
      fetchGroupPrompts();
    })
    .catch((err) => {
      console.error("Error saving group prompt:", err);
      alert(err.error || err.message || "Unknown error");
    })
    .finally(() => {
      btn.disabled = false;
      btn.textContent = "Save Prompt";
    });
});

window.onEditGroupPrompt = (promptId) => {
  fetch(`/api/group_prompts/${promptId}`)
    .then((r) =>
      r.ok ? r.json() : r.json().then((err) => Promise.reject(err))
    )
    .then((data) => {
      document.getElementById(
        "groupPromptModalLabel"
      ).textContent = `Edit: ${data.name}`;
      groupPromptIdEl.value = data.id;
      groupPromptNameEl.value = data.name;
      
      // Clear the editor completely first
      if (groupSimplemde) {
        groupSimplemde.codemirror.setValue("");
        groupSimplemde.value(data.content || "");
      }
      else groupPromptContentEl.value = data.content || "";
      
      groupPromptModalEl.show();
      
      // Force refresh after modal is fully shown
      setTimeout(() => {
        if (groupSimplemde) {
          groupSimplemde.codemirror.refresh();
          groupSimplemde.codemirror.focus();
        }
      }, 300);
    })
    .catch((err) => {
      console.error("Error loading prompt:", err);
      alert(err.error || err.message || "Unable to load prompt");
    });
};

window.onDeleteGroupPrompt = (promptId, ev) => {
  if (!confirm("Delete this prompt?")) return;
  const btn = ev.target.closest("button");
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner-border spinner-border-sm"></span>`;
  }
  fetch(`/api/group_prompts/${promptId}`, { method: "DELETE" })
    .then((r) =>
      r.ok ? fetchGroupPrompts() : r.json().then((err) => Promise.reject(err))
    )
    .catch((err) => {
      console.error("Error deleting prompt:", err);
      alert(err.error || err.message || "Could not delete");
    });
};

// — Filters & pagination hooks —
groupPromptsApplyFiltersBtn?.addEventListener("click", () => {
  groupPromptsSearchTerm = groupPromptsSearchInput.value.trim();
  groupPromptsCurrentPage = 1;
  fetchGroupPrompts();
});
// Define the clear filters function
function clearGroupPromptsFilters() {
  console.log("Clearing group prompt filters...");
  groupPromptsSearchInput.value = "";
  groupPromptsSearchTerm = "";
  groupPromptsCurrentPage = 1;
  fetchGroupPrompts();
}

// Remove any existing event listeners to prevent duplicates
groupPromptsClearFiltersBtn?.removeEventListener("click", clearGroupPromptsFilters);

// Add the event listener
groupPromptsClearFiltersBtn?.addEventListener("click", clearGroupPromptsFilters);

// Make the function globally available for other components to use
window.clearGroupPromptsFilters = clearGroupPromptsFilters;
groupPromptsPageSizeSelect?.addEventListener("change", (e) => {
  groupPromptsPageSize = +e.target.value;
  groupPromptsCurrentPage = 1;
  fetchGroupPrompts();
});
groupPromptsSearchInput?.addEventListener("keypress", (e) => {
  if (e.key === "Enter") groupPromptsApplyFiltersBtn.click();
});

// — Role‑based UI toggles —
function updateGroupPromptsRoleUI() {
  const canManage = ["Owner", "Admin", "PromptManager"].includes(
    userRoleInActiveGroup
  );
  // show/hide “New Prompt” button & edit/delete
  document.getElementById("create-group-prompt-section").style.display =
    canManage ? "block" : "none";
  document.getElementById("group-prompts-role-warning").style.display =
    canManage ? "none" : "block";
}

// — Expose & initial load —
window.fetchGroupPrompts = fetchGroupPrompts;
window.onCreateGroupPrompt = createGroupPromptBtn?.onclick;

