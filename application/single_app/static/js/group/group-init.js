// group-init.js
// Group workspace initialization: modals, editors, event listeners.
// Extracted from group_workspaces.html inline JS.
// Must be loaded AFTER all other group-*.js files.

// --- Filter toggle button logic ---
(function() {
  // Group Documents tab
  var docsToggleBtn = document.getElementById("group-docs-filters-toggle-btn");
  var docsCollapse = document.getElementById("group-docs-filters-collapse");
  if (docsToggleBtn && docsCollapse) {
    docsCollapse.addEventListener("show.bs.collapse", function() {
      docsToggleBtn.textContent = "Hide Search/Filters";
    });
    docsCollapse.addEventListener("hide.bs.collapse", function() {
      docsToggleBtn.textContent = "Show Search/Filters";
    });
  }
  // Group Prompts tab
  var promptsToggleBtn = document.getElementById("group-prompts-filters-toggle-btn");
  var promptsCollapse = document.getElementById("group-prompts-filters-collapse");
  if (promptsToggleBtn && promptsCollapse) {
    promptsCollapse.addEventListener("show.bs.collapse", function() {
      promptsToggleBtn.textContent = "Hide Search/Filters";
    });
    promptsCollapse.addEventListener("hide.bs.collapse", function() {
      promptsToggleBtn.textContent = "Show Search/Filters";
    });
  }

  // Hide upload status and progress container unless needed (Group)
  var groupUploadStatus = document.getElementById("upload-status");
  var groupUploadProgress = document.getElementById("group-upload-progress-container");
  if (groupUploadStatus) groupUploadStatus.style.display = "none";
  if (groupUploadProgress) groupUploadProgress.style.display = "none";

  function showGroupUploadStatusIfNeeded() {
    if (groupUploadStatus && groupUploadStatus.textContent.trim() !== "") {
      groupUploadStatus.style.display = "";
    } else if (groupUploadStatus) {
      groupUploadStatus.style.display = "none";
    }
    if (groupUploadProgress && groupUploadProgress.children.length > 0) {
      groupUploadProgress.style.display = "";
    } else if (groupUploadProgress) {
      groupUploadProgress.style.display = "none";
    }
  }

  // Patch the upload logic to call showGroupUploadStatusIfNeeded after updates
  var origSetStatus = groupUploadStatus && Object.getOwnPropertyDescriptor(Object.getPrototypeOf(groupUploadStatus), 'textContent')?.set;
  if (groupUploadStatus && origSetStatus) {
    Object.defineProperty(groupUploadStatus, 'textContent', {
      set: function(value) {
        origSetStatus.call(this, value);
        showGroupUploadStatusIfNeeded();
      },
      get: function() {
        return origSetStatus.get ? origSetStatus.get.call(this) : this.innerText;
      }
    });
  }
  if (groupUploadProgress) {
    var observer = new MutationObserver(showGroupUploadStatusIfNeeded);
    observer.observe(groupUploadProgress, { childList: true, subtree: false });
  }
  showGroupUploadStatusIfNeeded();
})();

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

// --- Modals ---
const loadingModal = new bootstrap.Modal(
  document.getElementById("loadingModal")
);
const docMetadataModal = new bootstrap.Modal(
  document.getElementById("docMetadataModal")
); // Ref for doc edit modal
const groupTagManagementModal = new bootstrap.Modal(
  document.getElementById("groupTagManagementModal")
);
const groupTagSelectionModal = new bootstrap.Modal(
  document.getElementById("groupTagSelectionModal")
);

// --- Editors ---
const groupPromptContentEl = document.getElementById("group-prompt-content");
let groupSimplemde = null;

if (groupPromptContentEl && typeof SimpleMDE !== "undefined") {
  try {
    groupSimplemde = new SimpleMDE({
      element: groupPromptContentEl,
      spellChecker: false,
      autoDownloadFontAwesome: false
    });
  } catch (e) {
    console.error("Failed to initialize SimpleMDE for group prompts:", e);
  }
} else if (!groupPromptContentEl) {
  console.warn("Group prompt textarea not found; skipping SimpleMDE init.");
} else {
  console.warn("SimpleMDE library not loaded; skipping init.");
}

document.addEventListener("DOMContentLoaded", () => {
  console.log("Group Workspace initializing...");

  // Initialize group document selection functionality
  const groupDocumentsTable = document.getElementById("group-documents-table");
  if (groupDocumentsTable) {
    // Make sure selection mode is initially off
    groupDocumentsTable.classList.remove('selection-mode');
  }
  
  // Initialize event delegation for group document checkboxes
  document.addEventListener('change', function(event) {
    // Handle changes on group document checkboxes
    if (event.target.classList.contains('document-checkbox')) {
      const documentId = event.target.getAttribute('data-document-id');
      if (window.updateGroupSelectedDocuments) {
        window.updateGroupSelectedDocuments(documentId, event.target.checked);
      }
    }
  });

  // Add event listeners for bulk action buttons
  const groupDeleteSelectedBtn = document.getElementById("group-delete-selected-btn");
  const groupRemoveSelectedBtn = document.getElementById("group-remove-selected-btn");
  const groupClearSelectionBtn = document.getElementById("group-clear-selection-btn");
  
  if (groupDeleteSelectedBtn) {
    groupDeleteSelectedBtn.addEventListener("click", deleteGroupSelectedDocuments);
  }
  if (groupRemoveSelectedBtn) {
    groupRemoveSelectedBtn.addEventListener("click", removeGroupSelectedDocuments);
  }
  if (groupClearSelectionBtn) {
    groupClearSelectionBtn.addEventListener("click", clearGroupSelection);
  }

  // Load initial data
  fetchUserGroups().then(() => {
    // Only fetch data if a group is active
    if (activeGroupId) {
      loadActiveGroupData();
    } else {
      console.log("No active group set initially.");
      // Optionally display a message asking user to select a group
    }
  });

  // --- Event Listeners (Global / Group Selection) ---
  document
    .getElementById("btn-my-groups")
    .addEventListener(
      "click",
      () => (window.location.href = window.groupMyGroupsUrl)
    );
  document
    .getElementById("btn-change-group")
    .addEventListener("click", onChangeActiveGroup);

  // --- Event Listeners (Group Documents Tab) ---
  if (groupUploadBtn)
    groupUploadBtn.addEventListener("click", onGroupUploadClick);
  if (groupDocsPageSizeSelect)
    groupDocsPageSizeSelect.addEventListener(
      "change",
      onGroupDocsPageSizeChange
    );
  if (groupDocsApplyFiltersBtn)
    groupDocsApplyFiltersBtn.addEventListener(
      "click",
      onGroupDocsApplyFilters
    );
  if (groupDocsClearFiltersBtn)
    groupDocsClearFiltersBtn.addEventListener(
      "click",
      onGroupDocsClearFilters
    );
  // Optional: Enter key triggers apply filters
  if (groupDocsSearchInput)
    groupDocsSearchInput.addEventListener("keypress", (e) => {
      if (e.key === "Enter") onGroupDocsApplyFilters();
    });
  [
    groupDocsAuthorFilterInput,
    groupDocsKeywordsFilterInput,
    groupDocsAbstractFilterInput,
  ].forEach((input) => {
    if (input)
      input.addEventListener("keypress", (e) => {
        if (e.key === "Enter") onGroupDocsApplyFilters();
      });
  });

  // Metadata Modal Form Submission Listener
  if (groupDocMetadataForm && docMetadataModal) {
    groupDocMetadataForm.addEventListener("submit", onGroupDocMetadataSave);
  }

  // --- Event Listeners (Group Prompts Tab - Keep Existing) ---
  document
    .getElementById("create-group-prompt-btn")
    ?.addEventListener("click", onCreateGroupPrompt);

  // --- Event Listeners (Tab Switching) ---
  const tabButtons = document.querySelectorAll(
    '#groupWorkspaceTab button[data-bs-toggle="tab"]'
  );
  tabButtons.forEach((button) => {
    button.addEventListener("shown.bs.tab", (event) => {
      console.log(
        `Group Tab shown: ${event.target.getAttribute("data-bs-target")}`
      );
      // Fetch data only if group context is set
      if (activeGroupId) {
        loadActiveGroupData();
      }
    });
  });
}); // End DOMContentLoaded
