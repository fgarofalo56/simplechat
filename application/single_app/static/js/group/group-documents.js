// group-documents.js
// Group document listing, CRUD operations, filtering, selection, and pagination.
// Extracted from group_workspaces.html inline JS.

// Document specific state
let groupDocsCurrentPage = 1;
let groupDocsPageSize = 10;
let groupDocsSearchTerm = "";
let groupDocsClassificationFilter = "";
let groupDocsAuthorFilter = "";
let groupDocsKeywordsFilter = "";
let groupDocsAbstractFilter = "";
const groupActivePolls = new Set(); // Separate polling set for group docs
const groupActivePollIntervals = new Map(); // documentId -> intervalId for visibility pause/resume

// Page Visibility API: pause group polling when tab is hidden, resume when visible
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        for (const [docId, intervalId] of groupActivePollIntervals.entries()) {
            clearInterval(intervalId);
        }
    } else {
        for (const docId of groupActivePolls) {
            if (!groupActivePollIntervals.has(docId)) continue;
            groupActivePolls.delete(docId);
            groupActivePollIntervals.delete(docId);
            pollGroupDocumentStatus(docId);
        }
    }
});

// Document selection state for group documents
let groupSelectedDocuments = new Set();
let groupSelectionMode = false;

// Grid/folder view state
let groupCurrentView = 'list';
let groupCurrentFolder = null;
let groupCurrentFolderType = null;
let groupFolderCurrentPage = 1;
let groupFolderPageSize = 10;
let groupGridSortBy = 'count';
let groupGridSortOrder = 'desc';
let groupFolderSortBy = '_ts';
let groupFolderSortOrder = 'desc';
let groupFolderSearchTerm = '';
let groupWorkspaceTags = [];
let groupDocsSortBy = '_ts';
let groupDocsSortOrder = 'desc';
let groupDocsTagsFilter = '';
let groupBulkSelectedTags = new Set();
let groupDocSelectedTags = new Set();
let groupEditingTag = null;


// --- DOM Elements (Group Documents Tab) ---
const groupDocumentsTableBody = document.querySelector(
  "#group-documents-table tbody"
);
const groupDocsPaginationContainer = document.getElementById(
  "group-docs-pagination-container"
);
const groupDocsPageSizeSelect = document.getElementById(
  "group-docs-page-size-select"
);
const groupFileInput = document.getElementById("file-input");
const groupUploadBtn = document.getElementById("upload-btn");
const groupUploadStatusSpan = document.getElementById("upload-status");
const groupDocMetadataForm = document.getElementById("doc-metadata-form");
const uploadSection = document.getElementById("upload-section");
const uploadHr = document.getElementById("upload-hr");

// --- Filter elements (Group Documents Tab) ---
const groupDocsSearchInput = document.getElementById(
  "group-docs-search-input"
);
const groupDocsClassificationFilterSelect =
    (window.enable_document_classification === true ||
     window.enable_document_classification === "true")
      ? document.getElementById("group-docs-classification-filter")
      : null;
const groupDocsAuthorFilterInput =
  window.enable_extract_meta_data === true ||
  window.enable_extract_meta_data === "true"
    ? document.getElementById("group-docs-author-filter")
    : null;
const groupDocsKeywordsFilterInput =
  window.enable_extract_meta_data === true ||
  window.enable_extract_meta_data === "true"
    ? document.getElementById("group-docs-keywords-filter")
    : null;
const groupDocsAbstractFilterInput =
  window.enable_extract_meta_data === true ||
  window.enable_extract_meta_data === "true"
    ? document.getElementById("group-docs-abstract-filter")
    : null;
const groupDocsApplyFiltersBtn = document.getElementById(
  "group-docs-apply-filters-btn"
);
const groupDocsClearFiltersBtn = document.getElementById(
  "group-docs-clear-filters-btn"
);

function escapeHtml(unsafe) {
  if (unsafe === null || typeof unsafe === "undefined") return "";
  return unsafe
    .toString()
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function isColorLight(hexColor) {
  // Copied from workspace-documents.js
  if (!hexColor) return true;
  const cleanHex = hexColor.startsWith("#")
    ? hexColor.substring(1)
    : hexColor;
  if (cleanHex.length < 3) return true;
  let r, g, b;
  try {
    if (cleanHex.length === 3) {
      r = parseInt(cleanHex[0] + cleanHex[0], 16);
      g = parseInt(cleanHex[1] + cleanHex[1], 16);
      b = parseInt(cleanHex[2] + cleanHex[2], 16);
    } else if (cleanHex.length >= 6) {
      r = parseInt(cleanHex.substring(0, 2), 16);
      g = parseInt(cleanHex.substring(2, 4), 16);
      b = parseInt(cleanHex.substring(4, 6), 16);
    } else {
      return true;
    }
  } catch (e) {
    console.warn("Could not parse hex color:", hexColor, e);
    return true;
  }
  if (isNaN(r) || isNaN(g) || isNaN(b)) return true;
  const luminance = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
  return luminance > 0.5;
}

function updateGroupSelectedDocuments(documentId, isSelected) {
  if (isSelected) {
    groupSelectedDocuments.add(documentId);
  } else {
    groupSelectedDocuments.delete(documentId);
  }
  updateGroupBulkActionButtons();
}

function updateGroupBulkActionButtons() {
  const bulkActionsBar = document.getElementById("groupBulkActionsBar");
  const selectedCountSpan = document.getElementById("groupSelectedCount");
  const deleteBtn = document.getElementById("group-delete-selected-btn");
  const removeBtn = document.getElementById("group-remove-selected-btn");
  
  if (groupSelectedDocuments.size > 0) {
    // Show bulk actions bar with count
    if (bulkActionsBar) {
      bulkActionsBar.style.display = "block";
    }
    if (selectedCountSpan) {
      selectedCountSpan.textContent = groupSelectedDocuments.size;
    }
    
    // Check if user can manage documents (delete permission)
    const canManage = ["Owner", "Admin", "DocumentManager"].includes(userRoleInActiveGroup);
    
    // Show/hide delete and remove buttons based on permissions
    if (deleteBtn) {
      deleteBtn.style.display = canManage ? "inline-block" : "none";
    }
    
    // Remove button is available for group documents
    if (removeBtn) {
      removeBtn.style.display = "inline-block";
    }
  } else {
    // Hide bulk actions bar
    if (bulkActionsBar) {
      bulkActionsBar.style.display = "none";
    }
  }
}

function toggleGroupSelectionMode() {
  const table = document.getElementById("group-documents-table");
  const checkboxes = document.querySelectorAll('.document-checkbox');
  const expandContainers = document.querySelectorAll('.expand-collapse-container');
  const bulkActionsBar = document.getElementById("groupBulkActionsBar");
  
  groupSelectionMode = !groupSelectionMode;
  
  if (groupSelectionMode) {
    // Enter selection mode
    table.classList.add("selection-mode");
    
    // Show checkboxes and hide expand buttons
    checkboxes.forEach(checkbox => {
      checkbox.style.display = 'inline-block';
    });
    
    expandContainers.forEach(container => {
      container.style.display = 'none';
    });
  } else {
    // Exit selection mode
    table.classList.remove("selection-mode");
    
    // Hide checkboxes and show expand buttons
    checkboxes.forEach(checkbox => {
      checkbox.style.display = 'none';
      checkbox.checked = false;
    });
    
    expandContainers.forEach(container => {
      container.style.display = 'inline-block';
    });
    
    // Hide bulk actions bar
    if (bulkActionsBar) {
      bulkActionsBar.style.display = 'none';
    }
    
    // Clear selected documents
    groupSelectedDocuments.clear();
  }
}

// Clear group selection
function clearGroupSelection() {
  const checkboxes = document.querySelectorAll('.document-checkbox');
  checkboxes.forEach(checkbox => {
    checkbox.checked = false;
  });
  groupSelectedDocuments.clear();
  updateGroupBulkActionButtons();
}

function deleteGroupSelectedDocuments() {
  if (groupSelectedDocuments.size === 0) return;
  
  if (!confirm(`Are you sure you want to delete ${groupSelectedDocuments.size} selected document(s)? This action cannot be undone.`)) {
    return;
  }

  const deleteBtn = document.getElementById("group-delete-selected-btn");
  if (deleteBtn) {
    deleteBtn.disabled = true;
    deleteBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-1"></span>Deleting...`;
  }

  const deletePromises = Array.from(groupSelectedDocuments).map(docId =>
    fetch(`/api/group_documents/${docId}`, { method: "DELETE" })
      .then(response => response.ok ? response.json() : Promise.reject(response))
  );

  Promise.allSettled(deletePromises)
    .then(results => {
      const successful = results.filter(r => r.status === 'fulfilled').length;
      const failed = results.filter(r => r.status === 'rejected').length;
      
      if (failed > 0) {
        alert(`Deleted ${successful} document(s). ${failed} failed to delete.`);
      } else {
        console.log(`Successfully deleted ${successful} document(s)`);
      }
      
      groupSelectedDocuments.clear();
      updateGroupBulkActionButtons();
      fetchGroupDocuments();
    })
    .finally(() => {
      if (deleteBtn) {
        deleteBtn.disabled = false;
        deleteBtn.innerHTML = `<i class="bi bi-trash"></i> Delete`;
      }
    });
}

function removeGroupSelectedDocuments() {
  if (groupSelectedDocuments.size === 0) return;
  
  // In group context, "remove" typically means removing the document from the group
  // but this depends on backend implementation. For now, we'll treat it as delete
  // since group documents are typically owned by the group, not individuals
  
  if (!confirm(`Are you sure you want to remove ${groupSelectedDocuments.size} selected document(s) from this group? This action cannot be undone.`)) {
    return;
  }

  const removeBtn = document.getElementById("group-remove-selected-btn");
  if (removeBtn) {
    removeBtn.disabled = true;
    removeBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-1"></span>Removing...`;
  }

  // For group documents, removal is typically the same as deletion
  // This could be modified to use a different endpoint if the backend supports
  // removing documents from groups without deleting them entirely
  const documentIds = Array.from(groupSelectedDocuments);
  let completed = 0;
  let failed = 0;
  
  // Process each document removal sequentially
  documentIds.forEach(docId => {
    fetch(`/api/group_documents/${docId}`, { method: "DELETE" })
      .then(response => {
        if (response.ok) {
          completed++;
          const docRow = document.getElementById(`group-doc-row-${docId}`);
          const detailsRow = document.getElementById(`group-details-row-${docId}`);
          const statusRow = document.getElementById(`group-status-row-${docId}`);
          if (docRow) docRow.remove();
          if (detailsRow) detailsRow.remove();
          if (statusRow) statusRow.remove();
        } else {
          failed++;
        }
        
        // Update status when all operations complete
        if (completed + failed === documentIds.length) {
          if (failed > 0) {
            alert(`Removed ${completed} document(s) from group, but failed to remove ${failed} document(s).`);
          } else {
            console.log(`Successfully removed ${completed} document(s) from group`);
          }
          
          // Refresh the documents list
          fetchGroupDocuments();
          
          // Exit selection mode
          toggleGroupSelectionMode();
        }
      })
      .catch(error => {
        failed++;
        console.error("Error removing document from group:", error);
        
        // Update status when all operations complete
        if (completed + failed === documentIds.length) {
          alert(`Removed ${completed} document(s) from group, but failed to remove ${failed} document(s).`);
          
          // Refresh the documents list
          fetchGroupDocuments();
          
          // Exit selection mode
          toggleGroupSelectionMode();
        }
      });
  });
  
  // Reset button state after operations complete
  if (removeBtn) {
    setTimeout(() => {
      if (document.body.contains(removeBtn)) {
        removeBtn.disabled = false;
        removeBtn.innerHTML = `<i class="bi bi-x-circle"></i> Remove`;
      }
    }, 2000);
  }
}

// Make functions globally available
window.updateGroupSelectedDocuments = updateGroupSelectedDocuments;
window.toggleGroupSelectionMode = toggleGroupSelectionMode;
window.deleteGroupSelectedDocuments = deleteGroupSelectedDocuments;
window.removeGroupSelectedDocuments = removeGroupSelectedDocuments;

function onGroupDocsPageSizeChange(e) {
  groupDocsPageSize = parseInt(e.target.value, 10);
  groupDocsCurrentPage = 1; // Reset to first page
  fetchGroupDocuments();
}

function onGroupDocsApplyFilters() {
  // Read values from group-specific filter inputs
  groupDocsSearchTerm = groupDocsSearchInput
    ? groupDocsSearchInput.value.trim()
    : "";
  groupDocsClassificationFilter = groupDocsClassificationFilterSelect
    ? groupDocsClassificationFilterSelect.value
    : "";
  groupDocsAuthorFilter = groupDocsAuthorFilterInput
    ? groupDocsAuthorFilterInput.value.trim()
    : "";
  groupDocsKeywordsFilter = groupDocsKeywordsFilterInput
    ? groupDocsKeywordsFilterInput.value.trim()
    : "";
  groupDocsAbstractFilter = groupDocsAbstractFilterInput
    ? groupDocsAbstractFilterInput.value.trim()
    : "";
  // Tags filter
  const tagsSelect = document.getElementById('group-docs-tags-filter');
  if (tagsSelect) {
    const selectedOpts = Array.from(tagsSelect.selectedOptions).map(o => o.value);
    groupDocsTagsFilter = selectedOpts.join(',');
  } else {
    groupDocsTagsFilter = '';
  }
  groupDocsCurrentPage = 1; // Reset page
  fetchGroupDocuments();
}

function onGroupDocsClearFilters() {
  console.log("Clearing group document filters...");
  // Clear group-specific filter inputs and state
  if (groupDocsSearchInput) groupDocsSearchInput.value = "";
  if (groupDocsClassificationFilterSelect)
    groupDocsClassificationFilterSelect.value = "";
  if (groupDocsAuthorFilterInput) groupDocsAuthorFilterInput.value = "";
  if (groupDocsKeywordsFilterInput) groupDocsKeywordsFilterInput.value = "";
  if (groupDocsAbstractFilterInput) groupDocsAbstractFilterInput.value = "";
  groupDocsSearchTerm = "";
  groupDocsClassificationFilter = "";
  groupDocsAuthorFilter = "";
  groupDocsKeywordsFilter = "";
  groupDocsAbstractFilter = "";
  groupDocsTagsFilter = "";
  groupDocsSortBy = '_ts';
  groupDocsSortOrder = 'desc';
  const tagsSelect = document.getElementById('group-docs-tags-filter');
  if (tagsSelect) { Array.from(tagsSelect.options).forEach(o => o.selected = false); }
  updateGroupListSortIcons();
  groupDocsCurrentPage = 1; // Reset page
  fetchGroupDocuments();
}
// Make the function globally available for other components to use
window.onGroupDocsClearFilters = onGroupDocsClearFilters;

function fetchGroupDocuments() {
  if (!groupDocumentsTableBody || !activeGroupId) return; // Need table and active group

  const placeholder = document.getElementById(
    "group-legacy-update-prompt-placeholder"
  );
  if (placeholder) {
    // remove old alert div if present
    const old = placeholder.querySelector("#group-legacy-update-alert");
    if (old) old.remove();
  }

  // Show loading state
  groupDocumentsTableBody.innerHTML = `<tr class="table-loading-row"><td colspan="4"><div class="spinner-border spinner-border-sm me-2" role="status"></div> Loading group documents...</td></tr>`;
  if (groupDocsPaginationContainer)
    groupDocsPaginationContainer.innerHTML = ""; // Clear pagination

  // Build query parameters for group documents endpoint
  const params = new URLSearchParams({
    page: groupDocsCurrentPage,
    page_size: groupDocsPageSize,
    // Crucially, the backend /api/group_documents needs to know WHICH group
    // It gets this from the user's active group setting server-side.
    // We add filters here:
  });
  if (groupDocsSearchTerm) params.append("search", groupDocsSearchTerm);
  if (groupDocsClassificationFilter)
    params.append("classification", groupDocsClassificationFilter);
  if (groupDocsAuthorFilter) params.append("author", groupDocsAuthorFilter);
  if (groupDocsKeywordsFilter)
    params.append("keywords", groupDocsKeywordsFilter);
  if (groupDocsAbstractFilter)
    params.append("abstract", groupDocsAbstractFilter);
  if (groupDocsTagsFilter) params.append("tags", groupDocsTagsFilter);
  if (groupDocsSortBy !== '_ts') params.append("sort_by", groupDocsSortBy);
  if (groupDocsSortOrder !== 'desc') params.append("sort_order", groupDocsSortOrder);

  console.log("Fetching group documents with params:", params.toString());

  fetch(`/api/group_documents?${params.toString()}`) // Use group endpoint
    .then((response) =>
      response.ok
        ? response.json()
        : response.json().then((err) => Promise.reject(err))
    )
    .then((data) => {
      if (data.needs_legacy_update_check) {
        showGroupLegacyUpdatePrompt();
      } else {
        const placeholder = document.getElementById(
          "group-legacy-update-prompt-placeholder"
        );
        placeholder?.querySelector("#group-legacy-update-alert")?.remove();
      }
      groupDocumentsTableBody.innerHTML = ""; // Clear loading/existing rows
      if (!data.documents || data.documents.length === 0) {
        const filtersActive =
          groupDocsSearchTerm ||
          groupDocsClassificationFilter ||
          groupDocsAuthorFilter ||
          groupDocsKeywordsFilter ||
          groupDocsAbstractFilter ||
          groupDocsTagsFilter;
        groupDocumentsTableBody.innerHTML = `<tr><td colspan="4" class="text-center p-4 text-muted">
                  ${
                    filtersActive
                      ? "No group documents found matching filters."
                      : "No documents found in this group."
                  }
                  ${
                    filtersActive
                      ? '<br><button class="btn btn-link btn-sm p-0" onclick="onGroupDocsClearFilters()">Clear filters</button>.'
                      : ""
                  }
               </td></tr>`;
      } else {
        // IMPORTANT: Pass userRoleInActiveGroup to render function for permission checks
        data.documents.forEach((doc) =>
          renderGroupDocumentRow(doc, userRoleInActiveGroup)
        );
      }
      renderGroupDocsPaginationControls(
        data.page,
        data.page_size,
        data.total_count
      );
    })
    .catch((error) => {
      console.error("Error fetching group documents:", error);
      groupDocumentsTableBody.innerHTML = `<tr><td colspan="4" class="text-center text-danger p-4">Error loading group documents: ${escapeHtml(
        error.error || error.message || "Unknown error"
      )}</td></tr>`;
      renderGroupDocsPaginationControls(1, groupDocsPageSize, 0);
    });
}

function renderGroupDocumentRow(doc, userRole) {
  // Added userRole param
  if (!groupDocumentsTableBody) return;
  const docId = doc.id;
  const pctString = String(doc.percentage_complete);
  const pct = /^\d+(\.\d+)?$/.test(pctString) ? parseFloat(pctString) : 0;
  const docStatus = doc.status || "";
  const isComplete =
    pct >= 100 ||
    docStatus.toLowerCase().includes("complete") ||
    docStatus.toLowerCase().includes("error");
  const hasError = docStatus.toLowerCase().includes("error");
  const canManage = ["Owner", "Admin", "DocumentManager"].includes(userRole); // Check role for actions

  const docRow = document.createElement("tr");
  docRow.id = `group-doc-row-${docId}`; // Use distinct prefix
  docRow.classList.add("document-row");
  
  // First column with checkbox and expand/collapse
  let firstColumnHtml = `
      <td class="align-middle">
          <input type="checkbox" class="document-checkbox" data-document-id="${docId}" style="display: none;">
          <span class="expand-collapse-container">
          ${isComplete && !hasError ?
              `<button class="btn btn-link p-0" onclick="toggleGroupDetails('${docId}')" title="Show/Hide Details">
                  <span id="group-arrow-icon-${docId}" class="bi bi-chevron-right"></span>
                  </button>` :
                  (hasError ? `<span class="text-danger" title="Processing Error: ${escapeHtml(docStatus)}"><i class="bi bi-exclamation-triangle-fill"></i></span>`
                           : `<span class="text-muted" title="Processing: ${escapeHtml(docStatus)} (${pct.toFixed(0)}%)"><i class="bi bi-hourglass-split"></i></span>`)
          }
          </span>
      </td>
  `;
  
  // Create the actions dropdown menu and chat button
  let actionsDropdown = '';
  let chatButton = '';
  
  // Get current group status
  const groupStatus = window.currentGroupStatus || 'active';
  const canChat = (groupStatus !== 'inactive');
  
  // Chat button for everyone with access (outside dropdown) - but only if group allows chat
  if (isComplete && !hasError && canChat) {
      chatButton = `
          <button class="btn btn-sm btn-primary me-1 action-btn-wide text-start"
              onclick="searchGroupDocumentInChat('${docId}')"
              title="Open Chat for Document"
              aria-label="Open Chat for Document: ${escapeHtml(doc.file_name || 'Untitled')}"
          >
              <i class="bi bi-chat-dots-fill me-1" aria-hidden="true"></i>
              Chat
          </button>
      `;
  }
  
  if (isComplete && !hasError) {
      actionsDropdown = `
      <div class="dropdown action-dropdown d-inline-block">
          <button class="btn btn-sm btn-outline-secondary dropdown-toggle" type="button" data-bs-toggle="dropdown" aria-expanded="false">
              <i class="bi bi-three-dots-vertical"></i>
          </button>
          <ul class="dropdown-menu dropdown-menu-end">
              <li><a class="dropdown-item select-btn" href="#" onclick="toggleGroupSelectionMode(); return false;">
                  <i class="bi bi-check-square me-2"></i>Select
              </a></li>
      `;
      
      // Get current group status
      const groupStatus = window.currentGroupStatus || 'active';
      const canModify = (groupStatus === 'active');
      const canChat = (groupStatus !== 'inactive');
      
      // Edit/Extract Metadata - only for active groups
      if (canModify) {
          actionsDropdown += `
              <li><hr class="dropdown-divider"></li>
              <li><a class="dropdown-item" href="#" onclick="onEditGroupDocument('${docId}'); return false;">
                  <i class="bi bi-pencil-fill me-2"></i>Edit Metadata
              </a></li>
          `;
          
          // Add Extract Metadata option if enabled
          if (window.enable_extract_meta_data === true || window.enable_extract_meta_data === "true") {
              actionsDropdown += `
                  <li><a class="dropdown-item" href="#" onclick="onExtractGroupMetadata('${docId}', event); return false;">
                      <i class="bi bi-magic me-2"></i>Extract Metadata
                  </a></li>
              `;
          }
      }
      
      // Chat - only if chat is allowed (not inactive)
      if (canChat) {
          actionsDropdown += `
              <li><a class="dropdown-item" href="#" onclick="searchGroupDocumentInChat('${docId}'); return false;">
                  <i class="bi bi-chat-dots-fill me-2"></i>Chat
              </a></li>
          `;
      }
      
      // Add sharing and delete/remove actions based on user role AND group status
      if (canManage) {
          // Share only available for active and upload_disabled groups (not locked or inactive)
          const canShare = (groupStatus === 'active' || groupStatus === 'upload_disabled');
          if (canShare) {
              actionsDropdown += `
                  <li><hr class="dropdown-divider"></li>
                  <li><a class="dropdown-item" href="#" onclick="shareGroupDocument('${docId}', '${escapeHtml(doc.file_name || '')}'); return false;">
                      <i class="bi bi-share-fill me-2"></i>Share
                      <span class="badge bg-secondary ms-1">${doc.shared_group_ids ? doc.shared_group_ids.length : 0}</span>
                  </a></li>
              `;
          }
          
          // Delete only available for active and upload_disabled groups (not locked or inactive)
          const canDelete = (groupStatus === 'active' || groupStatus === 'upload_disabled');
          if (canDelete) {
              actionsDropdown += `
                  <li><hr class="dropdown-divider"></li>
                  <li><a class="dropdown-item text-danger" href="#" onclick="deleteGroupDocument('${docId}', event); return false;">
                      <i class="bi bi-trash-fill me-2"></i>Delete
                  </a></li>
              `;
          }
      } else {
          // Non-manager actions - in group context, regular members typically can't remove documents
          // This could be extended to support "request removal" or similar functionality
          // For now, we don't show any destructive actions for non-managers
      }
      
      actionsDropdown += `
          </ul>
      </div>
      `;
  } else if (canManage) {
      // Only managers can delete incomplete/error documents
      actionsDropdown = `
      <div class="dropdown action-dropdown">
          <button class="btn btn-sm btn-outline-secondary dropdown-toggle" type="button" data-bs-toggle="dropdown" aria-expanded="false">
              <i class="bi bi-three-dots-vertical"></i>
          </button>
          <ul class="dropdown-menu dropdown-menu-end">
              <li><a class="dropdown-item text-danger" href="#" onclick="deleteGroupDocument('${docId}', event); return false;">
                  <i class="bi bi-trash-fill me-2"></i>Delete
              </a></li>
          </ul>
      </div>
      `;
  } else {
      // Non-managers cannot perform any actions on incomplete/error documents
      actionsDropdown = '';
  }
  
  // Complete row HTML
  docRow.innerHTML = `
      ${firstColumnHtml}
      <td class="align-middle" title="${escapeHtml(doc.file_name || "")}">${escapeHtml(doc.file_name || "")}</td>
      <td class="align-middle" title="${escapeHtml(doc.title || "")}">${escapeHtml(doc.title || "N/A")}</td>
      <td class="align-middle">
          ${chatButton}
          ${actionsDropdown}
      </td>
  `;
  docRow.__docData = doc; // Attach the full doc object for reference
  groupDocumentsTableBody.appendChild(docRow);

  // Details Row (only if complete and no error)
  if (isComplete && !hasError) {
    const detailsRow = document.createElement("tr");
    detailsRow.id = `group-details-row-${docId}`; // Distinct prefix
    detailsRow.style.display = "none";

    let classificationDisplayHTML = "";
    if (
      window.enable_document_classification === true ||
      window.enable_document_classification === "true"
    ) {
      classificationDisplayHTML += `<p class="mb-1"><strong>Classification:</strong> `;
      const currentLabel = doc.document_classification || null;
      const categories = window.classification_categories || [];
      const category = categories.find((cat) => cat.label === currentLabel);
      if (category) {
        const bgColor = category.color || "#6c757d";
        const useDarkText = isColorLight(bgColor);
        classificationDisplayHTML += `<span class="classification-badge ${
          useDarkText ? "text-dark" : ""
        }" style="background-color: ${escapeHtml(bgColor)};">${escapeHtml(
          category.label
        )}</span>`;
      } else if (currentLabel) {
        classificationDisplayHTML += `<span class="badge bg-warning text-dark" title="Category config not found">${escapeHtml(
          currentLabel
        )} (?)</span>`;
      } else {
        classificationDisplayHTML += `<span class="badge bg-secondary">None</span>`;
      }
      classificationDisplayHTML += `</p>`;
    }

    let detailsHtml = `
          <td colspan="4"> <div class="bg-light p-3 border rounded small">
              ${classificationDisplayHTML}
              <p class="mb-1"><strong>Version:</strong> ${escapeHtml(
                doc.version || "N/A"
              )}</p>
              <p class="mb-1"><strong>Authors:</strong> ${escapeHtml(
                Array.isArray(doc.authors)
                  ? doc.authors.join(", ")
                  : doc.authors || "N/A"
              )}</p>
              <p class="mb-1"><strong>Pages/Chunks:</strong> ${escapeHtml(
                doc.number_of_pages || "N/A"
              )}</p> <!-- Assuming number_of_pages stores chunk count -->
              <p class="mb-1"><strong>Citations:</strong> ${
                doc.enhanced_citations
                  ? '<span class="badge bg-success">Enhanced</span>'
                  : '<span class="badge bg-secondary">Standard</span>'
              }</p>
              <p class="mb-1"><strong>Publication Date:</strong> ${escapeHtml(
                doc.publication_date || "N/A"
              )}</p>
              <p class="mb-1"><strong>Keywords:</strong> ${escapeHtml(
                Array.isArray(doc.keywords)
                  ? doc.keywords.join(", ")
                  : doc.keywords || "N/A"
              )}</p>
              <p class="mb-0"><strong>Abstract:</strong> ${escapeHtml(
                doc.abstract || "N/A"
              )}</p>
              <hr class="my-2">
              <div class="d-flex flex-wrap gap-2">`;

    // Edit/Extract buttons only shown if user has management role AND group allows modification
    const groupStatus = window.currentGroupStatus || 'active';
    const canModify = (groupStatus === 'active');
    
    if (canManage && canModify) {
      detailsHtml += `
                <button class="btn btn-sm btn-info" onclick="onEditGroupDocument('${docId}')" title="Edit Metadata"> <i class="bi bi-pencil-fill"></i> Edit Metadata </button>`;
      if (
        window.enable_extract_meta_data === true ||
        window.enable_extract_meta_data === "true"
      ) {
        detailsHtml += `
                    <button class="btn btn-sm btn-warning" onclick="onExtractGroupMetadata('${docId}', event)" title="Re-run Metadata Extraction"> <i class="bi bi-magic"></i> Extract Metadata </button>`;
      }
    }
    detailsHtml += `</div></div></td>`; // Close buttons div, details div, td
    detailsRow.innerHTML = detailsHtml;
    groupDocumentsTableBody.appendChild(detailsRow);
  }

  // Status Row (if not complete OR has error)
  if (!isComplete || hasError) {
    const statusRow = document.createElement("tr");
    statusRow.id = `group-status-row-${docId}`; // Distinct prefix
    if (hasError) {
      statusRow.innerHTML = `<td colspan="4"><div class="alert alert-danger alert-sm py-1 px-2 mb-0 small"><i class="bi bi-exclamation-triangle-fill me-1"></i> Error: ${escapeHtml(
        docStatus
      )}</div></td>`;
    } else if (pct < 100) {
      // Still processing
      statusRow.innerHTML = `<td colspan="4"> <div class="progress" style="height: 10px;" title="Status: ${escapeHtml(
        docStatus
      )} (${pct.toFixed(
        0
      )}%)"> <div id="group-progress-bar-${docId}" class="progress-bar progress-bar-striped progress-bar-animated bg-info" role="progressbar" style="width: ${pct}%;" aria-valuenow="${pct}" aria-valuemin="0" aria-valuemax="100"></div> </div> <div class="text-muted text-end small" id="group-status-text-${docId}">${escapeHtml(
        docStatus
      )} (${pct.toFixed(0)}%)</div> </td>`;
    } else {
      statusRow.innerHTML = `<td colspan="4"><small class="text-muted">Status: Finalizing...</small></td>`;
    }
    groupDocumentsTableBody.appendChild(statusRow);
    if (!isComplete && !hasError) {
      pollGroupDocumentStatus(docId);
    } // Poll if processing
  }
}

function toggleGroupDetails(docId) {
  // Renamed function
  const detailsRow = document.getElementById(`group-details-row-${docId}`);
  const arrowIcon = document.getElementById(`group-arrow-icon-${docId}`);
  if (!detailsRow || !arrowIcon) return;
  if (detailsRow.style.display === "none") {
    detailsRow.style.display = "";
    arrowIcon.className = "bi bi-chevron-down";
  } else {
    detailsRow.style.display = "none";
    arrowIcon.className = "bi bi-chevron-right";
  }
}
// Make globally available if called directly from HTML onclick
window.toggleGroupDetails = toggleGroupDetails;

function renderGroupDocsPaginationControls(page, pageSize, totalCount) {
  // Renamed function
  if (!groupDocsPaginationContainer) return;
  groupDocsPaginationContainer.innerHTML = "";
  const totalPages = Math.ceil(totalCount / pageSize);
  if (totalPages <= 1) return;

  const createPageLink = (p, text, isDisabled, isActive) => {
    const li = document.createElement("li");
    li.classList.add("page-item");
    if (isDisabled) li.classList.add("disabled");
    if (isActive) {
      li.classList.add("active");
      li.setAttribute("aria-current", "page");
    }
    const a = document.createElement("a");
    a.classList.add("page-link");
    a.href = "#";
    a.innerHTML = text;
    if (!isDisabled) {
      a.addEventListener("click", (e) => {
        e.preventDefault();
        groupDocsCurrentPage = p;
        fetchGroupDocuments();
      }); // Call correct fetch
    }
    li.appendChild(a);
    return li;
  };

  const ul = document.createElement("ul");
  ul.classList.add("pagination", "pagination-sm", "mb-0");
  ul.appendChild(createPageLink(page - 1, "«", page <= 1)); // Previous

  const maxPagesToShow = 5;
  let startPage = 1,
    endPage = totalPages;
  if (totalPages > maxPagesToShow) {
    let maxBefore = Math.floor(maxPagesToShow / 2),
      maxAfter = Math.ceil(maxPagesToShow / 2) - 1;
    if (page <= maxBefore) {
      endPage = maxPagesToShow;
    } else if (page + maxAfter >= totalPages) {
      startPage = totalPages - maxPagesToShow + 1;
    } else {
      startPage = page - maxBefore;
      endPage = page + maxAfter;
    }
  }
  if (startPage > 1) {
    ul.appendChild(createPageLink(1, "1"));
    if (startPage > 2) ul.appendChild(createPageLink(0, "...", true));
  } // First & Ellipsis
  for (let p = startPage; p <= endPage; p++) {
    ul.appendChild(createPageLink(p, p, false, p === page));
  } // Page Numbers
  if (endPage < totalPages) {
    if (endPage < totalPages - 1)
      ul.appendChild(createPageLink(0, "...", true));
    ul.appendChild(createPageLink(totalPages, totalPages));
  } // Ellipsis & Last
  ul.appendChild(createPageLink(page + 1, "»", page >= totalPages)); // Next
  groupDocsPaginationContainer.appendChild(ul);
}


function pollGroupDocumentStatus(documentId) {
  // Renamed function
  if (groupActivePolls.has(documentId)) return;
  groupActivePolls.add(documentId);
  const intervalId = setInterval(() => {
    // Skip polling tick if tab is hidden
    if (document.hidden) return;

    const docRow = document.getElementById(`group-doc-row-${documentId}`);
    const statusRow = document.getElementById(
      `group-status-row-${documentId}`
    );
    if (!docRow && !statusRow) {
      clearInterval(intervalId);
      groupActivePolls.delete(documentId);
      groupActivePollIntervals.delete(documentId);
      return;
    }

    fetch(`/api/group_documents/${documentId}`) // Use group endpoint
      .then((r) =>
        r.ok
          ? r.json()
          : r.status === 404
          ? Promise.reject(new Error("404"))
          : r.json().then((err) => Promise.reject(err))
      )
      .then((doc) => {
        const pctString = String(doc.percentage_complete);
        const pct = /^\d+(\.\d+)?$/.test(pctString)
          ? parseFloat(pctString)
          : 0;
        const docStatus = doc.status || "";
        const isComplete =
          pct >= 100 ||
          docStatus.toLowerCase().includes("complete") ||
          docStatus.toLowerCase().includes("error");
        const hasError = docStatus.toLowerCase().includes("error");

        if (!isComplete && statusRow) {
          // Update progress
          const progressBar = statusRow.querySelector(
            `#group-progress-bar-${documentId}`
          );
          const statusText = statusRow.querySelector(
            `#group-status-text-${documentId}`
          );
          if (progressBar) {
            progressBar.style.width = pct + "%";
            progressBar.setAttribute("aria-valuenow", pct);
            progressBar.parentNode.setAttribute(
              "title",
              `Status: ${escapeHtml(docStatus)} (${pct.toFixed(0)}%)`
            );
          }
          if (statusText) {
            statusText.textContent = `${escapeHtml(docStatus)} (${pct.toFixed(
              0
            )}%)`;
          }
        } else {
          // Complete or Error
          clearInterval(intervalId);
          groupActivePolls.delete(documentId);
          groupActivePollIntervals.delete(documentId);
          if (statusRow) statusRow.remove();
          if (docRow) {
            // Re-render the main row
            const parent = docRow.parentNode;
            const detailsRow = document.getElementById(
              `group-details-row-${documentId}`
            );
            docRow.remove();
            if (detailsRow) detailsRow.remove();
            // Pass current role when re-rendering
            renderGroupDocumentRow(doc, userRoleInActiveGroup);
          } else {
            fetchGroupDocuments();
          } // Fallback refresh
        }
      })
      .catch((err) => {
        console.error(`Error polling group document ${documentId}:`, err);
        clearInterval(intervalId);
        groupActivePolls.delete(documentId);
        groupActivePollIntervals.delete(documentId);
        if (statusRow)
          statusRow.innerHTML = `<td colspan="4"><div class="alert alert-warning alert-sm py-1 px-2 mb-0 small"><i class="bi bi-exclamation-triangle-fill me-1"></i>Could not retrieve status: ${escapeHtml(
            err.message || "Polling failed"
          )}</div></td>`;
        if (docRow && docRow.cells[0]) {
          /* Update icon? */
        }
      });
  }, 5000); // Poll every 5 seconds
  groupActivePollIntervals.set(documentId, intervalId);
}

function onEditGroupDocument(docId) {
  // Renamed function
  if (!docMetadataModal) return;
  // Fetch using the group document GET endpoint
  fetch(`/api/group_documents/${docId}`)
    .then((r) =>
      r.ok ? r.json() : r.json().then((err) => Promise.reject(err))
    )
    .then((doc) => {
      // Populate the SAME modal elements as workspace.html uses
      document.getElementById("doc-id").value = doc.id;
      document.getElementById("doc-title").value = doc.title || "";
      document.getElementById("doc-abstract").value = doc.abstract || "";
      document.getElementById("doc-keywords").value = Array.isArray(
        doc.keywords
      )
        ? doc.keywords.join(", ")
        : doc.keywords || "";
      document.getElementById("doc-publication-date").value =
        doc.publication_date || "";
      document.getElementById("doc-authors").value = Array.isArray(
        doc.authors
      )
        ? doc.authors.join(", ")
        : doc.authors || "";
      const classificationSelect =
        document.getElementById("doc-classification");
      if (
        (window.enable_document_classification === true ||
          window.enable_document_classification === "true") &&
        classificationSelect
      ) {
        const currentClassification = doc.document_classification || "none";
        classificationSelect.value = currentClassification;
        if (
          ![...classificationSelect.options].some(
            (o) => o.value === classificationSelect.value
          )
        ) {
          classificationSelect.value = "none";
        }
        classificationSelect.closest(".mb-3").style.display = "";
      } else if (classificationSelect) {
        classificationSelect.closest(".mb-3").style.display = "none";
      }
      // Load tags for the document
      groupDocSelectedTags = new Set(Array.isArray(doc.tags) ? doc.tags : []);
      updateGroupDocTagsDisplay();
      docMetadataModal.show();
    })
    .catch((err) => {
      console.error("Error retrieving group document for edit:", err);
      alert("Error: " + (err.error || err.message));
    });
}
window.onEditGroupDocument = onEditGroupDocument; // Expose globally

function onGroupDocMetadataSave(e) {
  // Renamed function
  e.preventDefault();
  const docSaveBtn = document.getElementById("doc-save-btn");
  if (!docSaveBtn) return;
  docSaveBtn.disabled = true;
  docSaveBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>Saving...`;

  const docId = document.getElementById("doc-id").value;
  const payload = {
    title: document.getElementById("doc-title")?.value.trim() || null,
    abstract: document.getElementById("doc-abstract")?.value.trim() || null,
    keywords: document.getElementById("doc-keywords")?.value.trim() || null,
    publication_date:
      document.getElementById("doc-publication-date")?.value.trim() || null,
    authors: document.getElementById("doc-authors")?.value.trim() || null,
  };
  // Convert lists
  if (payload.keywords) {
    payload.keywords = payload.keywords
      .split(",")
      .map((kw) => kw.trim())
      .filter(Boolean);
  } else {
    payload.keywords = [];
  }
  if (payload.authors) {
    payload.authors = payload.authors
      .split(",")
      .map((a) => a.trim())
      .filter(Boolean);
  } else {
    payload.authors = [];
  }

  // Add classification
  if (
    window.enable_document_classification === true ||
    window.enable_document_classification === "true"
  ) {
    const classificationSelect =
      document.getElementById("doc-classification");
    let selectedClassification = classificationSelect?.value || null;
    if (selectedClassification === "none") selectedClassification = null;
    payload.document_classification = selectedClassification;
  }

  // Add tags
  payload.tags = Array.from(groupDocSelectedTags);

  // Use the group PATCH endpoint
  fetch(`/api/group_documents/${docId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })
    .then((r) =>
      r.ok ? r.json() : r.json().then((err) => Promise.reject(err))
    )
    .then((updatedDoc) => {
      if (docMetadataModal) docMetadataModal.hide();
      fetchGroupDocuments(); // Refresh group documents list
      loadGroupWorkspaceTags(); // Refresh tag counts
    })
    .catch((err) => {
      alert("Error updating document: " + (err.error || err.message));
    })
    .finally(() => {
      docSaveBtn.disabled = false;
      docSaveBtn.textContent = "Save Metadata";
    });
}


function onExtractGroupMetadata(docId, event) {
  // Renamed function
  if (
    !(
      window.enable_extract_meta_data === true ||
      window.enable_extract_meta_data === "true"
    )
  )
    return;
  if (!confirm("Run metadata extraction for this group document?")) return;

  const extractBtn = event ? event.target.closest("button") : null;
  if (extractBtn) {
    extractBtn.disabled = true;
    extractBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-1"></span>Extracting...`;
  }

  // Use the group metadata extraction endpoint
  fetch(`/api/group_documents/${docId}/extract_metadata`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  })
    .then((r) =>
      r.ok ? r.json() : r.json().then((err) => Promise.reject(err))
    )
    .then((data) => {
      //alert(data.message || "Metadata extraction process initiated.");
      // Refresh after delay
      setTimeout(fetchGroupDocuments, 1500);
      const detailsRow = document.getElementById(
        `group-details-row-${docId}`
      );
      if (detailsRow && detailsRow.style.display !== "none")
        toggleGroupDetails(docId);
    })
    .catch((err) => {
      alert("Error extracting metadata: " + (err.error || err.message));
    })
    .finally(() => {
      if (extractBtn && document.body.contains(extractBtn)) {
        extractBtn.disabled = false;
        extractBtn.innerHTML = '<i class="bi bi-magic"></i> Extract Metadata';
      }
    });
}
window.onExtractGroupMetadata = onExtractGroupMetadata; // Expose globally

function deleteGroupDocument(documentId, event) {
  // Renamed function
  // Permission check should happen server-side, but can add UI check too
  if (
    !["Owner", "Admin", "DocumentManager"].includes(userRoleInActiveGroup)
  ) {
    alert("You do not have permission to delete documents in this group.");
    return;
  }
  if (
    !confirm(
      "Are you sure you want to delete this group document? This action cannot be undone."
    )
  )
    return;

  const deleteBtn = event ? event.target.closest("button") : null;
  if (deleteBtn) {
    deleteBtn.disabled = true;
    deleteBtn.innerHTML = `<span class="spinner-border spinner-border-sm"></span>`;
  }

  // Stop polling
  if (groupActivePolls.has(documentId)) {
    const existingInterval = groupActivePollIntervals.get(documentId);
    if (existingInterval) clearInterval(existingInterval);
    groupActivePolls.delete(documentId);
    groupActivePollIntervals.delete(documentId);
  }

  // Use the group DELETE endpoint. Pass group_id as query param IF backend requires it.
  // Assuming backend gets active_group_id from session/context.
  // If needed: `/api/group_documents/${documentId}?group_id=${activeGroupId}`
  fetch(`/api/group_documents/${documentId}`, { method: "DELETE" })
    .then((response) =>
      response.ok
        ? response.json()
        : response.json().then((err) => Promise.reject(err))
    )
    .then((data) => {
      console.log("Group document deleted:", data);
      const docRow = document.getElementById(`group-doc-row-${documentId}`);
      const detailsRow = document.getElementById(
        `group-details-row-${documentId}`
      );
      const statusRow = document.getElementById(
        `group-status-row-${documentId}`
      );
      if (docRow) docRow.remove();
      if (detailsRow) detailsRow.remove();
      if (statusRow) statusRow.remove();
      // Refresh to update pagination etc.
      fetchGroupDocuments();
    })
    .catch((error) => {
      alert("Error deleting document: " + (error.error || error.message));
      if (deleteBtn && document.body.contains(deleteBtn)) {
        deleteBtn.disabled = false;
        deleteBtn.innerHTML = '<i class="bi bi-trash-fill"></i>';
      }
    });
}
window.deleteGroupDocument = deleteGroupDocument; // Expose globally

function showGroupLegacyUpdatePrompt() {
  if (document.getElementById("group-legacy-update-alert")) return;
  const placeholder = document.getElementById(
    "group-legacy-update-prompt-placeholder"
  );
  if (!placeholder) return;

  placeholder.innerHTML = `
  <div
    id="group-legacy-update-alert"
    class="alert alert-info alert-dismissible fade show mt-3"
    role="alert"
  >
    <h5 class="alert-heading">
      <i class="bi bi-info-circle-fill me-2"></i>
      Update Older Group Documents
    </h5>
    <p class="mb-2 small">
      Some documents in this group were uploaded with an older version.
      Updating them now will restore full compatibility (metadata, search, etc.).
    </p>
    <button
      type="button"
      class="btn btn-primary btn-sm me-2"
      id="confirm-group-legacy-update-btn"
    >
      Update Now
    </button>
    <button
      type="button"
      class="btn btn-secondary btn-sm"
      data-bs-dismiss="alert"
      aria-label="Close"
    >
      Maybe Later
    </button>
  </div>
`;
  document
    .getElementById("confirm-group-legacy-update-btn")
    .addEventListener("click", handleGroupLegacyUpdateConfirm);
}


async function handleGroupLegacyUpdateConfirm() {
  const btn = document.getElementById("confirm-group-legacy-update-btn");
  btn.disabled = true;
  btn.innerHTML = `
  <span
    class="spinner-border spinner-border-sm me-2"
    role="status"
    aria-hidden="true"
  ></span>Updating...
`;

  try {
    const res = await fetch("/api/group_documents/upgrade_legacy", {
      method: "POST",
    });
    const json = await res.json();
    if (!res.ok) throw new Error(json.error || res.statusText);

    alert(json.message || "Group documents upgraded.");
    document.getElementById("group-legacy-update-alert")?.remove();
    fetchGroupDocuments();
  } catch (err) {
    console.error("Legacy upgrade failed", err);
    alert("Failed to upgrade group documents: " + err.message);
    btn.disabled = false;
    btn.textContent = "Update Now";
  }
}


function searchGroupDocumentInChat(docId) {
  // Renamed function
  // Redirect to chat page with group scope and document ID
  window.location.href = `/chats?search_documents=true&doc_scope=group&document_id=${docId}&group_id=${activeGroupId}`;
}
window.searchGroupDocumentInChat = searchGroupDocumentInChat; // Expose globally

// --- Chat with Selected Group Documents ---
function chatWithGroupSelected() {
  if (groupSelectedDocuments.size === 0) return;
  const idsParam = encodeURIComponent(Array.from(groupSelectedDocuments).join(','));
  window.location.href = `/chats?search_documents=true&doc_scope=group&document_ids=${idsParam}&group_id=${activeGroupId}`;
}
window.chatWithGroupSelected = chatWithGroupSelected;
