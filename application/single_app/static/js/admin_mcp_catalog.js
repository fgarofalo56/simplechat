// admin_mcp_catalog.js
// Admin management for MCP Server Catalog entries (CRUD + seed)

(function () {
    "use strict";

    const listContainer = document.getElementById("mcp-catalog-admin-list");
    const countLabel = document.getElementById("mcp-catalog-count-label");
    const seedBtn = document.getElementById("mcp-catalog-seed-btn");
    const addBtn = document.getElementById("mcp-catalog-add-btn");
    const enableCheckbox = document.getElementById("enable_mcp_catalog");
    const settingsDiv = document.getElementById("mcp_catalog_admin_settings");

    if (!listContainer) return;

    // Toggle visibility
    if (enableCheckbox && settingsDiv) {
        enableCheckbox.addEventListener("change", function () {
            settingsDiv.classList.toggle("d-none", !this.checked);
            if (this.checked) loadAdminCatalog();
        });
    }

    // Seed defaults
    if (seedBtn) {
        seedBtn.addEventListener("click", async function () {
            if (!confirm("Seed the catalog with default MCP server entries? Existing defaults will not be overwritten.")) return;
            seedBtn.disabled = true;
            seedBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Seeding...';
            try {
                const resp = await fetch("/api/admin/mcp-catalog/seed", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ force: false })
                });
                const data = await resp.json();
                alert(data.message || `Seeded ${data.count} entries.`);
                loadAdminCatalog();
            } catch (e) {
                alert("Error seeding catalog: " + e.message);
            } finally {
                seedBtn.disabled = false;
                seedBtn.innerHTML = '<i class="bi bi-arrow-repeat me-1"></i>Seed Defaults';
            }
        });
    }

    // Add new entry
    if (addBtn) {
        addBtn.addEventListener("click", function () {
            const name = prompt("Enter MCP server name:");
            if (!name) return;
            createEntry({ name: name, description: "", category: "other", is_active: true });
        });
    }

    async function loadAdminCatalog() {
        listContainer.innerHTML = '<div class="text-center py-3"><span class="spinner-border spinner-border-sm"></span> Loading...</div>';
        try {
            const resp = await fetch("/api/admin/mcp-catalog");
            const data = await resp.json();
            const entries = data.entries || [];
            if (countLabel) countLabel.textContent = `${entries.length} catalog entries`;
            renderAdminList(entries);
        } catch (e) {
            listContainer.innerHTML = '<div class="alert alert-danger">Failed to load catalog.</div>';
        }
    }

    function renderAdminList(entries) {
        listContainer.innerHTML = "";

        if (!entries.length) {
            listContainer.innerHTML = '<div class="alert alert-info">No catalog entries yet. Click "Seed Defaults" to add pre-configured MCP servers.</div>';
            return;
        }

        const table = document.createElement("table");
        table.className = "table table-sm table-striped";
        table.innerHTML = `<thead><tr>
            <th>Name</th><th>Category</th><th>Transport</th><th>Active</th><th style="width:120px">Actions</th>
        </tr></thead>`;

        const tbody = document.createElement("tbody");

        entries.forEach(function (entry) {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td>${escapeHtml(entry.name)}<br><small class="text-muted">${escapeHtml(entry.provider || "")}</small></td>
                <td><span class="badge bg-secondary-subtle text-secondary-emphasis">${escapeHtml(entry.category || "other")}</span></td>
                <td>${escapeHtml(entry.transport || "")}</td>
                <td>${entry.is_active ? '<i class="bi bi-check-circle text-success"></i>' : '<i class="bi bi-x-circle text-danger"></i>'}</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary me-1 admin-catalog-toggle" data-id="${entry.id}" data-active="${entry.is_active}">
                        ${entry.is_active ? "Disable" : "Enable"}
                    </button>
                    <button class="btn btn-sm btn-outline-danger admin-catalog-delete" data-id="${entry.id}" data-name="${escapeHtml(entry.name)}">
                        <i class="bi bi-trash"></i>
                    </button>
                </td>`;
            tbody.appendChild(tr);
        });

        table.appendChild(tbody);
        listContainer.appendChild(table);

        // Bind toggle buttons
        table.querySelectorAll(".admin-catalog-toggle").forEach(function (btn) {
            btn.addEventListener("click", function () {
                const id = this.dataset.id;
                const currentActive = this.dataset.active === "true";
                toggleEntry(id, !currentActive);
            });
        });

        // Bind delete buttons
        table.querySelectorAll(".admin-catalog-delete").forEach(function (btn) {
            btn.addEventListener("click", function () {
                const id = this.dataset.id;
                const name = this.dataset.name;
                if (confirm(`Delete catalog entry "${name}"? This cannot be undone.`)) {
                    deleteEntry(id);
                }
            });
        });
    }

    async function toggleEntry(id, newActive) {
        try {
            await fetch(`/api/admin/mcp-catalog/${id}`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ is_active: newActive })
            });
            loadAdminCatalog();
        } catch (e) {
            alert("Error updating entry: " + e.message);
        }
    }

    async function deleteEntry(id) {
        try {
            await fetch(`/api/admin/mcp-catalog/${id}`, { method: "DELETE" });
            loadAdminCatalog();
        } catch (e) {
            alert("Error deleting entry: " + e.message);
        }
    }

    async function createEntry(data) {
        try {
            const resp = await fetch("/api/admin/mcp-catalog", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data)
            });
            if (resp.ok) {
                loadAdminCatalog();
            } else {
                const err = await resp.json();
                alert("Error: " + (err.error || "Failed to create entry."));
            }
        } catch (e) {
            alert("Error creating entry: " + e.message);
        }
    }

    function escapeHtml(text) {
        const div = document.createElement("div");
        div.textContent = text || "";
        return div.innerHTML;
    }

    // Auto-load when MCP tab is activated
    const mcpTab = document.getElementById("mcp-servers-tab");
    if (mcpTab) {
        mcpTab.addEventListener("shown.bs.tab", function () {
            if (enableCheckbox && enableCheckbox.checked) {
                loadAdminCatalog();
            }
        });
    }

    // Initial load if already visible
    if (enableCheckbox && enableCheckbox.checked && settingsDiv && !settingsDiv.classList.contains("d-none")) {
        loadAdminCatalog();
    }
})();
