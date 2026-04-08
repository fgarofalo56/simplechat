// mcp_catalog.js
// Renders the MCP Server Catalog: browse, search, filter, and install MCP servers.

import { showToast } from "./chat/chat-toast.js";

let cachedEntries = null;
let cachedCategories = [];

// ---------------------------------------------------------------------------
// Data fetching
// ---------------------------------------------------------------------------

async function fetchCatalog(category, search) {
    const params = new URLSearchParams();
    if (category) params.set("category", category);
    if (search) params.set("search", search);

    const url = `/api/mcp-catalog${params.toString() ? "?" + params : ""}`;
    const response = await fetch(url);
    if (!response.ok) {
        throw new Error("Failed to load MCP catalog.");
    }
    const data = await response.json();
    cachedEntries = data.entries || [];
    cachedCategories = data.categories || [];
    return { entries: cachedEntries, categories: cachedCategories };
}

// ---------------------------------------------------------------------------
// Rendering
// ---------------------------------------------------------------------------

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text || "";
    return div.innerHTML;
}

function renderCatalogEntries(entries, container) {
    container.innerHTML = "";

    if (!entries.length) {
        container.innerHTML = '<p class="text-muted text-center py-3">No MCP servers match your search.</p>';
        return;
    }

    entries.forEach((entry) => {
        const card = document.createElement("div");
        card.className = "card mb-3";

        const body = document.createElement("div");
        body.className = "card-body";

        // Header row
        const header = document.createElement("div");
        header.className = "d-flex justify-content-between align-items-start";

        const titleArea = document.createElement("div");
        titleArea.className = "flex-grow-1";

        const title = document.createElement("h6");
        title.className = "card-title mb-1";
        title.innerHTML = `<i class="${escapeHtml(entry.icon || "bi-plug")} me-2"></i>${escapeHtml(entry.name)}`;
        titleArea.appendChild(title);

        const provider = document.createElement("small");
        provider.className = "text-muted";
        provider.textContent = entry.provider || "";
        titleArea.appendChild(provider);

        header.appendChild(titleArea);

        const installBtn = document.createElement("button");
        installBtn.className = "btn btn-sm btn-outline-primary";
        installBtn.innerHTML = '<i class="bi bi-download me-1"></i>Install';
        installBtn.addEventListener("click", () => openInstallModal(entry));
        header.appendChild(installBtn);

        body.appendChild(header);

        // Description
        const desc = document.createElement("p");
        desc.className = "card-text mt-2 mb-2 small";
        desc.textContent = entry.description || "";
        body.appendChild(desc);

        // Metadata badges
        const metaRow = document.createElement("div");
        metaRow.className = "d-flex flex-wrap gap-1 mb-2";

        const transportBadge = document.createElement("span");
        transportBadge.className = "badge bg-info-subtle text-info-emphasis";
        transportBadge.textContent = (entry.transport || "unknown").replace("_", " ");
        metaRow.appendChild(transportBadge);

        const authBadge = document.createElement("span");
        authBadge.className = "badge bg-warning-subtle text-warning-emphasis";
        authBadge.textContent = `Auth: ${(entry.auth_type || "none").replace("_", " ")}`;
        metaRow.appendChild(authBadge);

        const catBadge = document.createElement("span");
        catBadge.className = "badge bg-secondary-subtle text-secondary-emphasis";
        catBadge.textContent = (entry.category || "other").replace("-", " ");
        metaRow.appendChild(catBadge);

        body.appendChild(metaRow);

        // Tools preview
        if (Array.isArray(entry.tools_preview) && entry.tools_preview.length) {
            const toolsRow = document.createElement("div");
            toolsRow.className = "small text-muted";
            toolsRow.innerHTML = `<strong>Tools:</strong> ${entry.tools_preview.slice(0, 6).map(t => escapeHtml(t)).join(", ")}`;
            if (entry.tools_preview.length > 6) {
                toolsRow.innerHTML += ` <span class="text-muted">+${entry.tools_preview.length - 6} more</span>`;
            }
            body.appendChild(toolsRow);
        }

        // Tags
        if (Array.isArray(entry.tags) && entry.tags.length) {
            const tagsRow = document.createElement("div");
            tagsRow.className = "mt-2";
            entry.tags.slice(0, 5).forEach((tag) => {
                const badge = document.createElement("span");
                badge.className = "badge bg-light text-dark border me-1";
                badge.textContent = tag;
                tagsRow.appendChild(badge);
            });
            body.appendChild(tagsRow);
        }

        // Docs link
        if (entry.documentation_url) {
            const docsLink = document.createElement("a");
            docsLink.href = entry.documentation_url;
            docsLink.target = "_blank";
            docsLink.rel = "noopener noreferrer";
            docsLink.className = "small text-decoration-none mt-2 d-inline-block";
            docsLink.innerHTML = '<i class="bi bi-box-arrow-up-right me-1"></i>Documentation';
            body.appendChild(docsLink);
        }

        card.appendChild(body);
        container.appendChild(card);
    });
}

function renderCategories(categories, selectEl) {
    // Preserve current selection
    const current = selectEl.value;
    selectEl.innerHTML = '<option value="">All Categories</option>';

    categories.forEach((cat) => {
        const opt = document.createElement("option");
        opt.value = cat;
        opt.textContent = cat.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
        selectEl.appendChild(opt);
    });

    if (current) selectEl.value = current;
}

// ---------------------------------------------------------------------------
// Install modal
// ---------------------------------------------------------------------------

function openInstallModal(entry) {
    const modal = document.getElementById("mcpInstallModal");
    if (!modal) return;

    document.getElementById("mcpInstallModalLabel").textContent = `Install: ${entry.name}`;
    document.getElementById("mcp-install-entry-id").value = entry.id;

    // Description
    const descEl = document.getElementById("mcp-install-description");
    descEl.innerHTML = `<p>${escapeHtml(entry.description)}</p>`;

    // Tools preview
    const toolsEl = document.getElementById("mcp-install-tools-preview");
    if (Array.isArray(entry.tools_preview) && entry.tools_preview.length) {
        toolsEl.innerHTML = `<p class="mb-1"><strong>Available tools:</strong></p>
            <div class="d-flex flex-wrap gap-1">
                ${entry.tools_preview.map(t => `<span class="badge bg-primary-subtle text-primary-emphasis">${escapeHtml(t)}</span>`).join("")}
            </div>`;
    } else {
        toolsEl.innerHTML = "";
    }

    // Config fields
    const fieldsContainer = document.getElementById("mcp-install-fields");
    fieldsContainer.innerHTML = "";

    const configFields = entry.config_fields || [];
    configFields.forEach((field) => {
        const div = document.createElement("div");
        div.className = "mb-3";

        const label = document.createElement("label");
        label.className = "form-label";
        label.setAttribute("for", `mcp-field-${field.name}`);
        label.textContent = field.label || field.name;
        if (field.required) {
            const req = document.createElement("span");
            req.className = "text-danger ms-1";
            req.textContent = "*";
            label.appendChild(req);
        }
        div.appendChild(label);

        const input = document.createElement("input");
        input.type = field.type === "secret" ? "password" : "text";
        input.className = "form-control";
        input.id = `mcp-field-${field.name}`;
        input.name = field.name;
        input.placeholder = field.placeholder || "";
        input.required = !!field.required;
        input.dataset.fieldName = field.name;
        div.appendChild(input);

        if (field.help) {
            const helpText = document.createElement("div");
            helpText.className = "form-text";
            helpText.textContent = field.help;
            div.appendChild(helpText);
        }

        fieldsContainer.appendChild(div);
    });

    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
}

async function handleInstall() {
    const entryId = document.getElementById("mcp-install-entry-id").value;
    const scope = document.getElementById("mcp-install-scope").value;

    // Gather config values from form
    const configValues = {};
    const fields = document.querySelectorAll("#mcp-install-fields input[data-field-name]");
    let hasError = false;

    fields.forEach((input) => {
        const name = input.dataset.fieldName;
        const value = input.value.trim();
        if (input.required && !value) {
            input.classList.add("is-invalid");
            hasError = true;
        } else {
            input.classList.remove("is-invalid");
        }
        if (value) configValues[name] = value;
    });

    if (hasError) {
        showToast("Please fill in all required fields.", "warning");
        return;
    }

    const submitBtn = document.getElementById("mcp-install-submit");
    const originalText = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Installing...';

    try {
        const response = await fetch(`/api/mcp-catalog/${entryId}/install`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ config_values: configValues, scope }),
        });

        const data = await response.json();

        if (response.ok) {
            showToast(data.message || "MCP server installed successfully!", "success");
            const modal = bootstrap.Modal.getInstance(document.getElementById("mcpInstallModal"));
            if (modal) modal.hide();
        } else {
            showToast(data.error || "Installation failed.", "danger");
        }
    } catch (error) {
        console.error("Install error:", error);
        showToast("Failed to install MCP server. Please try again.", "danger");
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
    }
}

// ---------------------------------------------------------------------------
// Initialization
// ---------------------------------------------------------------------------

let searchTimeout = null;

async function loadCatalog() {
    const loadingEl = document.getElementById("mcp-catalog-loading");
    const emptyEl = document.getElementById("mcp-catalog-empty");
    const entriesEl = document.getElementById("mcp-catalog-entries");
    const categorySelect = document.getElementById("mcp-catalog-category-filter");
    const searchInput = document.getElementById("mcp-catalog-search");

    if (!loadingEl || !entriesEl) return;

    try {
        const category = categorySelect ? categorySelect.value : "";
        const search = searchInput ? searchInput.value.trim() : "";

        const { entries, categories } = await fetchCatalog(category, search);

        if (loadingEl) loadingEl.classList.add("d-none");

        if (categorySelect) {
            renderCategories(categories, categorySelect);
        }

        if (!entries.length) {
            if (emptyEl) emptyEl.classList.remove("d-none");
            entriesEl.classList.add("d-none");
        } else {
            if (emptyEl) emptyEl.classList.add("d-none");
            entriesEl.classList.remove("d-none");
            renderCatalogEntries(entries, entriesEl);
        }
    } catch (error) {
        console.error("Failed to load MCP catalog:", error);
        if (loadingEl) loadingEl.classList.add("d-none");
        if (emptyEl) {
            emptyEl.classList.remove("d-none");
            emptyEl.innerHTML = '<p class="text-danger text-center py-3">Failed to load catalog. Please try again.</p>';
        }
    }
}

function initMcpCatalog() {
    if (!window.appSettings?.enable_mcp_catalog) return;

    const searchInput = document.getElementById("mcp-catalog-search");
    const categorySelect = document.getElementById("mcp-catalog-category-filter");
    const installBtn = document.getElementById("mcp-install-submit");

    if (searchInput) {
        searchInput.addEventListener("input", () => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => loadCatalog(), 300);
        });
    }

    if (categorySelect) {
        categorySelect.addEventListener("change", () => loadCatalog());
    }

    if (installBtn) {
        installBtn.addEventListener("click", handleInstall);
    }

    // Load catalog when the tab is shown (lazy load)
    const tabBtn = document.getElementById("mcp-catalog-tab-btn");
    if (tabBtn) {
        tabBtn.addEventListener("shown.bs.tab", () => {
            if (!cachedEntries) loadCatalog();
        });
    }
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initMcpCatalog);
} else {
    initMcpCatalog();
}
