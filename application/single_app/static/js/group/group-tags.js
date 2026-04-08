// group-tags.js
// Group tag management modal, tag selection, and document tags display.
// Extracted from group_workspaces.html inline JS.

function isGroupColorLight(hex) {
  if (!hex) return true;
  hex = hex.replace('#', '');
  const r = parseInt(hex.substr(0,2),16), g = parseInt(hex.substr(2,2),16), b = parseInt(hex.substr(4,2),16);
  return (r * 299 + g * 587 + b * 114) / 1000 > 155;
}

function escapeGroupHtml(text) {
  const d = document.createElement('div');
  d.textContent = text;
  return d.innerHTML;
}

// --- Tag Management Modal ---
function showGroupTagManagementModal() {
  loadGroupWorkspaceTags().then(() => {
    refreshGroupTagManagementTable();
    groupTagManagementModal.show();
  });
}

function refreshGroupTagManagementTable() {
  const tbody = document.getElementById('group-existing-tags-tbody');
  if (!tbody) return;
  if (groupWorkspaceTags.length === 0) {
    tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">No tags yet. Add one above.</td></tr>';
    return;
  }
  let html = '';
  groupWorkspaceTags.forEach(tag => {
    const ek = escapeGroupHtml(tag.name);
    html += `<tr>
      <td><div style="width:30px;height:30px;background-color:${tag.color};border-radius:4px;border:1px solid #dee2e6;"></div></td>
      <td><span class="badge" style="background-color:${tag.color};color:${isGroupColorLight(tag.color)?'#000':'#fff'};">${ek}</span></td>
      <td>${tag.count}</td>
      <td>
        <button class="btn btn-sm btn-outline-primary me-1" onclick="window.editGroupTagInModal('${ek}','${tag.color}')"><i class="bi bi-pencil"></i></button>
        <button class="btn btn-sm btn-outline-danger" onclick="window.deleteGroupTagFromModal('${ek}')"><i class="bi bi-trash"></i></button>
      </td>
    </tr>`;
  });
  tbody.innerHTML = html;
}

function groupCancelEditMode() {
  groupEditingTag = null;
  const nameInput = document.getElementById('group-new-tag-name');
  const colorInput = document.getElementById('group-new-tag-color');
  const formTitle = document.getElementById('group-tag-form-title');
  const addBtn = document.getElementById('group-add-tag-btn');
  const cancelBtn = document.getElementById('group-cancel-edit-btn');
  if (nameInput) nameInput.value = '';
  if (colorInput) colorInput.value = '#0d6efd';
  if (formTitle) formTitle.textContent = 'Add New Tag';
  if (addBtn) { addBtn.innerHTML = '<i class="bi bi-plus-circle"></i> Add'; addBtn.classList.remove('btn-success'); addBtn.classList.add('btn-primary'); }
  if (cancelBtn) cancelBtn.classList.add('d-none');
}

window.editGroupTagInModal = function(tagName, currentColor) {
  groupEditingTag = { originalName: tagName, originalColor: currentColor };
  const nameInput = document.getElementById('group-new-tag-name');
  const colorInput = document.getElementById('group-new-tag-color');
  const formTitle = document.getElementById('group-tag-form-title');
  const addBtn = document.getElementById('group-add-tag-btn');
  const cancelBtn = document.getElementById('group-cancel-edit-btn');
  if (nameInput) nameInput.value = tagName;
  if (colorInput) colorInput.value = currentColor;
  if (formTitle) formTitle.textContent = 'Edit Tag';
  if (addBtn) { addBtn.innerHTML = '<i class="bi bi-save"></i> Save'; addBtn.classList.remove('btn-primary'); addBtn.classList.add('btn-success'); }
  if (cancelBtn) cancelBtn.classList.remove('d-none');
  if (nameInput) nameInput.focus();
};

window.deleteGroupTagFromModal = async function(tagName) {
  if (!confirm(`Delete tag "${tagName}"? This will remove it from all documents.`)) return;
  try {
    const resp = await fetch(`/api/group_documents/tags/${encodeURIComponent(tagName)}`, { method: 'DELETE' });
    const data = await resp.json();
    if (resp.ok) {
      await loadGroupWorkspaceTags();
      refreshGroupTagManagementTable();
    } else {
      alert('Error: ' + (data.error || 'Failed to delete tag'));
    }
  } catch (e) { console.error(e); alert('Error deleting tag'); }
};

async function handleGroupAddOrSaveTag() {
  const nameInput = document.getElementById('group-new-tag-name');
  const colorInput = document.getElementById('group-new-tag-color');
  if (!nameInput || !colorInput) return;
  const tagName = nameInput.value.trim().toLowerCase();
  const tagColor = colorInput.value;

  if (!tagName) { alert('Please enter a tag name'); return; }
  if (!/^[a-z0-9_-]+$/.test(tagName)) { alert('Tag name must contain only lowercase letters, numbers, hyphens, and underscores'); return; }

  if (groupEditingTag) {
    // Edit mode - save changes
    const nameChanged = tagName !== groupEditingTag.originalName;
    const colorChanged = tagColor !== groupEditingTag.originalColor;
    if (!nameChanged && !colorChanged) { groupCancelEditMode(); return; }
    if (nameChanged && groupWorkspaceTags.some(t => t.name === tagName && t.name !== groupEditingTag.originalName)) {
      alert('A tag with this name already exists'); return;
    }
    try {
      const body = {};
      if (nameChanged) body.new_name = tagName;
      if (colorChanged) body.color = tagColor;
      const resp = await fetch(`/api/group_documents/tags/${encodeURIComponent(groupEditingTag.originalName)}`, {
        method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
      });
      const data = await resp.json();
      if (resp.ok) {
        groupCancelEditMode();
        await loadGroupWorkspaceTags();
        refreshGroupTagManagementTable();
        if (groupCurrentView === 'grid') renderGroupGridView();
      } else { alert('Error: ' + (data.error || 'Failed to update tag')); }
    } catch (e) { console.error(e); alert('Error updating tag'); }
  } else {
    // Add mode
    if (groupWorkspaceTags.some(t => t.name === tagName)) { alert('A tag with this name already exists'); return; }
    try {
      const resp = await fetch('/api/group_documents/tags', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tag_name: tagName, color: tagColor })
      });
      const data = await resp.json();
      if (resp.ok) {
        nameInput.value = '';
        colorInput.value = '#0d6efd';
        await loadGroupWorkspaceTags();
        refreshGroupTagManagementTable();
        if (groupCurrentView === 'grid') renderGroupGridView();
      } else { alert('Error: ' + (data.error || 'Failed to create tag')); }
    } catch (e) { console.error(e); alert('Error creating tag'); }
  }
}

// --- Tag Selection Modal ---
function showGroupTagSelectionModal() {
  loadGroupWorkspaceTags().then(() => {
    renderGroupTagSelectionList();
    groupTagSelectionModal.show();
  });
}

function renderGroupTagSelectionList() {
  const listContainer = document.getElementById('group-tag-selection-list');
  if (!listContainer) return;
  if (groupWorkspaceTags.length === 0) {
    listContainer.innerHTML = `<div class="text-center p-4">
      <p class="text-muted mb-3">No tags available yet.</p>
      <button type="button" class="btn btn-primary" id="group-create-first-tag-btn"><i class="bi bi-plus-circle"></i> Create Your First Tag</button>
    </div>`;
    document.getElementById('group-create-first-tag-btn')?.addEventListener('click', () => {
      groupTagSelectionModal.hide();
      showGroupTagManagementModal();
    });
    return;
  }
  let html = '';
  groupWorkspaceTags.forEach(tag => {
    const isSelected = groupDocSelectedTags.has(tag.name);
    const textColor = isGroupColorLight(tag.color) ? '#000' : '#fff';
    html += `<label class="list-group-item d-flex align-items-center" style="cursor:pointer;">
      <input class="form-check-input me-3" type="checkbox" value="${escapeGroupHtml(tag.name)}" ${isSelected ? 'checked' : ''}>
      <span class="badge me-2" style="background-color:${tag.color};color:${textColor};">${escapeGroupHtml(tag.name)}</span>
      <span class="ms-auto text-muted small">${tag.count} docs</span>
    </label>`;
  });
  listContainer.innerHTML = html;
  listContainer.querySelectorAll('input[type="checkbox"]').forEach(cb => {
    cb.addEventListener('change', (e) => {
      if (e.target.checked) groupDocSelectedTags.add(e.target.value);
      else groupDocSelectedTags.delete(e.target.value);
    });
  });
}

// --- Document Tags Display ---
function updateGroupDocTagsDisplay() {
  const container = document.getElementById('group-doc-selected-tags-container');
  if (!container) return;
  if (groupDocSelectedTags.size === 0) {
    container.innerHTML = '<span class="text-muted small">No tags selected</span>';
    return;
  }
  let html = '';
  groupDocSelectedTags.forEach(tagName => {
    const tag = groupWorkspaceTags.find(t => t.name === tagName);
    const color = tag ? tag.color : '#6c757d';
    const textColor = isGroupColorLight(color) ? '#000' : '#fff';
    html += `<span class="badge" style="background-color:${color};color:${textColor};">
      ${escapeGroupHtml(tagName)}
      <i class="bi bi-x" style="cursor:pointer;" onclick="window.removeGroupDocSelectedTag('${escapeGroupHtml(tagName)}')"></i>
    </span>`;
  });
  container.innerHTML = html;
}

window.removeGroupDocSelectedTag = function(tagName) {
  groupDocSelectedTags.delete(tagName);
  updateGroupDocTagsDisplay();
};

// --- Wire up events ---
(function initGroupTagManagement() {
  // Manage Tags button (next to view toggle)
  const manageTagsBtn = document.getElementById('group-manage-tags-btn');
  if (manageTagsBtn) {
    manageTagsBtn.addEventListener('click', showGroupTagManagementModal);
  }

  // Manage Tags button inside metadata modal (opens Select Tags)
  const docManageTagsBtn = document.getElementById('group-doc-manage-tags-btn');
  if (docManageTagsBtn) {
    docManageTagsBtn.addEventListener('click', () => {
      showGroupTagSelectionModal();
    });
  }

  // Tag Selection Done button
  const tagSelectDoneBtn = document.getElementById('group-tag-selection-done-btn');
  if (tagSelectDoneBtn) {
    tagSelectDoneBtn.addEventListener('click', () => {
      updateGroupDocTagsDisplay();
      groupTagSelectionModal.hide();
    });
  }

  // Open Manage Tags from within Selection modal
  const openMgmtBtn = document.getElementById('group-open-tag-mgmt-btn');
  if (openMgmtBtn) {
    openMgmtBtn.addEventListener('click', () => {
      groupTagSelectionModal.hide();
      showGroupTagManagementModal();
    });
  }

  // Add/Save tag button in management modal
  const addTagBtn = document.getElementById('group-add-tag-btn');
  if (addTagBtn) addTagBtn.addEventListener('click', handleGroupAddOrSaveTag);

  // Cancel edit button
  const cancelEditBtn = document.getElementById('group-cancel-edit-btn');
  if (cancelEditBtn) cancelEditBtn.addEventListener('click', groupCancelEditMode);

  // Enter key on tag name input
  const tagNameInput = document.getElementById('group-new-tag-name');
  if (tagNameInput) {
    tagNameInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') { e.preventDefault(); handleGroupAddOrSaveTag(); }
    });
  }

  // When tag management modal closes, refresh selection if it was open
  document.getElementById('groupTagManagementModal')?.addEventListener('hidden.bs.modal', () => {
    groupCancelEditMode();
  });
})();

