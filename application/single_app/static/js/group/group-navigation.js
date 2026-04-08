// group-navigation.js
// Group workspace navigation, state management, and role/status logic.
// Extracted from group_workspaces.html inline JS.

// --- Global State ---
let userRoleInActiveGroup = null;
let userGroups = [];
let activeGroupId = null; // Crucial for group context
let activeGroupName = ""; // Store name for display

function notifyGroupWorkspaceContext() {
  window.groupWorkspaceContext = {
    activeGroupId,
    activeGroupName,
    userRole: userRoleInActiveGroup,
    requireOwnerForAgentManagement: window.requireOwnerForAgentManagement || false
  };
  window.dispatchEvent(new CustomEvent('groupWorkspace:context-changed', {
    detail: window.groupWorkspaceContext
  }));
}

notifyGroupWorkspaceContext();

function updateGroupStatusAlert() {
  const activeGroup = userGroups.find(g => g.id === activeGroupId);
  const alertBox = document.getElementById("group-status-alert");
  
  if (!activeGroup || !alertBox) {
    return;
  }
  
  const status = activeGroup.status || 'active';
  const statusMessages = {
    'locked': {
      type: 'warning',
      icon: 'bi-lock-fill',
      title: '🔒 Locked (Read-Only)',
      message: 'Group is in read-only mode',
      details: [
        '❌ New document uploads',
        '❌ Document deletions',
        '❌ Creating, editing, or deleting prompts, agents, and actions',
        '✅ Viewing existing documents',
        '✅ Chat and search with existing documents',
        '✅ Using existing prompts, agents, and actions'
      ]
    },
    'upload_disabled': {
      type: 'info',
      icon: 'bi-cloud-slash-fill',
      title: '📁 Upload Disabled',
      message: 'Restrict new content but allow other operations',
      details: [
        '❌ New document uploads',
        '✅ Document deletions (cleanup)',
        '✅ Full chat and search functionality',
        '✅ Creating, editing, and deleting prompts, agents, and actions'
      ]
    },
    'inactive': {
      type: 'danger',
      icon: 'bi-exclamation-triangle-fill',
      title: '⭕ Inactive',
      message: 'Group is disabled',
      details: [
        '❌ ALL operations (uploads, chat, document access)',
        '❌ Creating, editing, or deleting prompts, agents, and actions',
        '✅ Only admin viewing of group information',
        'Use case: Decommissioned projects, suspended groups, compliance holds'
      ]
    }
  };
  
  if (status === 'active') {
    alertBox.classList.add('d-none');
  } else {
    const config = statusMessages[status];
    if (config) {
      alertBox.classList.remove('d-none', 'alert-warning', 'alert-info', 'alert-danger');
      alertBox.classList.add(`alert-${config.type}`);
      
      const detailsList = config.details.map(d => `<li class="mb-1">${d}</li>`).join('');
      
      alertBox.innerHTML = `
        <div class="d-flex align-items-start">
          <i class="bi ${config.icon} me-2 flex-shrink-0" style="font-size: 1.2rem;"></i>
          <div>
            <strong>${config.title}</strong> - ${config.message}
            <ul class="mb-0 mt-2 small">
              ${detailsList}
            </ul>
          </div>
        </div>
      `;
    }
  }
}

/**
 * Hide/show UI elements based on the active group's status
 */
function updateGroupUIBasedOnStatus() {
  const activeGroup = userGroups.find(g => g.id === activeGroupId);
  
  if (!activeGroup) {
    return;
  }
  
  const status = activeGroup.status || 'active';
  
  // Define elements to hide/show (note: upload-section is handled by updateRoleDisplay)
  const createPromptBtn = document.getElementById('create-group-prompt-btn');
  const createAgentBtn = document.getElementById('create-group-agent-btn');
  const createPluginBtn = document.getElementById('create-group-plugin-btn');
  const deleteSelectedBtn = document.getElementById('group-delete-selected-btn');
  
  // Determine what operations are allowed based on status
  const canCreateItems = (status === 'active');
  const canModifyItems = (status === 'active'); // locked and inactive cannot modify
  const canDeleteDocs = (status === 'active' || status === 'upload_disabled'); // Can delete in upload_disabled
  const canChat = (status !== 'inactive'); // Chat disabled only for inactive
  
  // Hide/show create buttons based on permissions
  if (createPromptBtn) {
    createPromptBtn.style.display = canCreateItems ? '' : 'none';
  }
  if (createAgentBtn) {
    createAgentBtn.style.display = canCreateItems ? '' : 'none';
  }
  if (createPluginBtn) {
    createPluginBtn.style.display = canCreateItems ? '' : 'none';
  }
  
  // Hide/show delete button for documents (shown only if can delete)
  // Note: This will be further refined by role permissions in updateRoleDisplay
  if (deleteSelectedBtn && !canDeleteDocs) {
    deleteSelectedBtn.style.display = 'none';
  }
  
  // Store status globally so other functions can check it
  window.currentGroupStatus = status;
  window.currentGroupCanModify = canModifyItems;
  window.currentGroupCanChat = canChat;
  
  console.log(`UI updated for group ${activeGroupId} with status: ${status}`);
}

function fetchUserGroups() {
  console.log("Fetching user groups...");
  // Add loading state to group selector?
  const sel = document.getElementById("group-select");
  const dropdownButton = document.getElementById("group-dropdown-button");
  const dropdownItems = document.getElementById("group-dropdown-items");
  const searchContainer = document.querySelector(".group-search-container");

  // Show loading state
  dropdownButton.disabled = true;
  dropdownButton.querySelector(".selected-group-text").textContent = "Loading groups...";
  dropdownItems.innerHTML = '<div class="text-center py-2"><div class="spinner-border spinner-border-sm" role="status"></div> Loading...</div>';
  document.getElementById("btn-change-group").disabled = true;

  // Set a large page_size to get all groups at once
  return fetch("/api/groups?page_size=1000") // Request up to 1000 groups to avoid pagination
    .then((r) => {
      if (!r.ok) {
        // Handle HTTP errors (like 401, 500)
        return r
          .json()
          .then((err) => Promise.reject(err))
          .catch(() =>
            Promise.reject({
              error: `Server responded with status ${r.status}`,
            })
          );
      }
      return r.json();
    })
    .then((data) => {
      // Assign the array from data.groups, or default to empty array
      userGroups = data.groups || [];

      // Clear loading message
      sel.innerHTML = ""; 
      dropdownItems.innerHTML = "";
      
      // Element removed from HTML, only keep role element reference
      const activeGroupNameRoleEl = document.getElementById(
        "active-group-name-role"
      );

      let foundActive = false;
      
      // Show/hide search based on number of groups
      if (userGroups.length > 10) {
        searchContainer.classList.remove("d-none");
      } else {
        searchContainer.classList.add("d-none");
      }

      if (userGroups.length === 0) {
        dropdownItems.innerHTML = '<div class="dropdown-item disabled">No groups found</div>';
        sel.innerHTML = "<option>No groups found</option>";
      } else {
        userGroups.forEach((g) => {
          // Create option for hidden select (compatibility)
          const opt = document.createElement("option");
          opt.value = g.id;
          opt.text = g.name;
          
          // Create dropdown item for custom dropdown
          const dropdownItem = document.createElement("button");
          dropdownItem.type = "button";
          dropdownItem.classList.add("dropdown-item");
          dropdownItem.setAttribute("data-group-id", g.id);
          dropdownItem.textContent = g.name;
          dropdownItems.appendChild(dropdownItem);

          if (g.isActive) {
            opt.selected = true;
            dropdownItem.classList.add("active");
            dropdownButton.querySelector(".selected-group-text").textContent = g.name;
            activeGroupId = g.id;
            userRoleInActiveGroup = g.userRole;
            activeGroupName = g.name;
            foundActive = true;
          }
          sel.appendChild(opt);
        });

        // Add click event listeners to dropdown items
        document.querySelectorAll("#group-dropdown-items .dropdown-item").forEach(item => {
          item.addEventListener("click", function() {
            const groupId = this.getAttribute("data-group-id");
            const groupName = this.textContent;
            
            // Update hidden select
            sel.value = groupId;
            
            // Update dropdown button text
            dropdownButton.querySelector(".selected-group-text").textContent = groupName;
            
            // Update active state
            document.querySelectorAll("#group-dropdown-items .dropdown-item").forEach(i => {
              i.classList.remove("active");
            });
            this.classList.add("active");
            
            // Close dropdown
            const dropdownInstance = bootstrap.Dropdown.getInstance(dropdownButton);
            if (dropdownInstance) {
              dropdownInstance.hide();
            }
          });
        });

        // Initialize search functionality
        const searchInput = document.getElementById("group-search-input");
        if (searchInput) {
          searchInput.addEventListener("input", function() {
            const searchTerm = this.value.toLowerCase().trim();
            document.querySelectorAll("#group-dropdown-items .dropdown-item").forEach(item => {
              const groupName = item.textContent.toLowerCase();
              if (groupName.includes(searchTerm)) {
                item.style.display = "";
              } else {
                item.style.display = "none";
              }
            });
          });

          // Stop event propagation to prevent dropdown from closing when clicking on search input
          searchInput.addEventListener("click", function(e) {
            e.stopPropagation();
          });
        }
      }

      if (foundActive) {
        // Only update role element since heading element was removed
        activeGroupNameRoleEl.textContent = activeGroupName;
        updateRoleDisplay(); // Update role display and UI elements
        updateGroupStatusAlert(); // Update status alert box
        updateGroupUIBasedOnStatus(); // Hide/show UI elements based on status
      } else {
        // Reset state if no active group found among the user's groups
        activeGroupId = null;
        userRoleInActiveGroup = null;
        activeGroupName = "";
        document.getElementById("user-role-display").style.display = "none";
        // Clear tables or show message
        if (groupDocumentsTableBody)
          groupDocumentsTableBody.innerHTML =
            '<tr><td colspan="4" class="text-center p-4 text-muted">Please select an active group.</td></tr>';
        // Clear prompts table too if needed
        const promptsTbody = document.querySelector(
          "#group-prompts-table tbody"
        );
        if (promptsTbody)
          promptsTbody.innerHTML =
            '<tr><td colspan="2" class="text-center p-4 text-muted">Please select an active group.</td></tr>';
        // Disable upload section if no group active
        if (uploadSection) uploadSection.style.display = "none";
        if (uploadHr) uploadHr.style.display = "none";
      }

      notifyGroupWorkspaceContext();
    })
    .catch((err) => {
      console.error("Error fetching groups", err);
      alert(
        "Could not fetch your groups: " +
          (err.error || err.message || "Unknown error")
      );
      sel.innerHTML = "<option>Error loading groups</option>"; // Show error in dropdown
      dropdownButton.querySelector(".selected-group-text").textContent = "Error loading groups";
      dropdownItems.innerHTML = '<div class="dropdown-item disabled">Error loading groups</div>';
      notifyGroupWorkspaceContext();
    })
    .finally(() => {
      // Re-enable controls after fetch completes
      sel.disabled = false;
      dropdownButton.disabled = false;
      document.getElementById("btn-change-group").disabled = false;
    });
}

function setActiveGroup(groupId) {
  // Show loading state?
  return fetch("/api/groups/setActive", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ groupId }),
  })
    .then((r) => r.json())
    .then((data) => {
      if (data.error) {
        alert("Error setting active group: " + data.error);
        throw new Error(data.error);
      }
      console.log("Active group set successfully");
    });
  // Note: We refetch groups and data *after* this promise resolves in onChangeActiveGroup
}

function onChangeActiveGroup() {
  const sel = document.getElementById("group-select");
  const newGroupId = sel.value;
  if (newGroupId === activeGroupId) return; // No change

  console.log(`Attempting to change active group to: ${newGroupId}`);
  // Add loading indicator?
  const changeButton = document.getElementById("btn-change-group");
  changeButton.disabled = true;
  changeButton.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Changing...`;

  setActiveGroup(newGroupId)
    .then(() => fetchUserGroups()) // Refetch groups to update state (activeGroupId, role)
    .then(() => {
      // Check if active group was successfully set
      if (activeGroupId === newGroupId) {
        loadActiveGroupData(); // Load data for the new group
      } else {
        // This case might happen if setActiveGroup failed but didn't throw an error network-wise
        console.error("Failed to confirm active group change.");
        alert("Could not change active group. Please try again.");
      }
    })
    .catch((err) => {
      console.error("Error during group change process:", err);
      // fetchUserGroups might have already updated state, check if we need to revert UI
    })
    .finally(() => {
      changeButton.disabled = false;
      changeButton.textContent = "Change Active Group";
    });
}

function loadActiveGroupData() {
  console.log(`Loading data for active group: ${activeGroupId}`);
  if (!activeGroupId) {
    console.warn("Cannot load data: No active group ID set.");
    return;
  }
  const activeTab = document.querySelector(
    "#groupWorkspaceTab .nav-link.active"
  );
  const targetId = activeTab
    ? activeTab.getAttribute("data-bs-target")
    : "#documents-tab"; // Default to documents

  if (targetId === "#documents-tab") {
    fetchGroupDocuments();
    loadGroupWorkspaceTags();
  } else if (targetId === "#prompts-tab") {
    fetchGroupPrompts();
  } else if (targetId === "#group-agents-tab") {
    if (window.fetchGroupAgents) {
      window.fetchGroupAgents();
    }
  } else if (targetId === "#group-plugins-tab") {
    if (window.fetchGroupPlugins) {
      window.fetchGroupPlugins();
    }
  }
  // Update UI elements dependent on role (applies to both tabs potentially)
  updateRoleDisplay();
  updateGroupPromptsRoleUI(); // This is specific to prompts tab UI elements
}

function updateRoleDisplay() {
  const canManageDocs = ["Owner", "Admin", "DocumentManager"].includes(
    userRoleInActiveGroup
  );
  const roleDisplay = document.getElementById("user-role-display");
  const roleSpan = document.getElementById("user-role");
  const activeGroupNameRoleEl = document.getElementById(
    "active-group-name-role"
  );

  if (userRoleInActiveGroup && activeGroupName) {
    roleSpan.innerText = userRoleInActiveGroup;
    activeGroupNameRoleEl.textContent = activeGroupName; // Ensure name is shown in role display
    roleDisplay.style.display = "block";
  } else {
    roleDisplay.style.display = "none";
  }

  // Control visibility of upload section and its divider
  // Check BOTH role AND group status - must have permission AND group must be active
  const activeGroup = userGroups.find(g => g.id === activeGroupId);
  const groupStatus = activeGroup ? (activeGroup.status || 'active') : 'active';
  const groupAllowsUpload = (groupStatus === 'active');
  const showUpload = canManageDocs && groupAllowsUpload;
  
  if (uploadSection)
    uploadSection.style.display = showUpload ? "block" : "none";
  if (uploadHr) uploadHr.style.display = showUpload ? "block" : "none";

  notifyGroupWorkspaceContext();
}

