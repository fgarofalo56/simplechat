// group-grid-view.js
// Group workspace grid/folder view, view switching, and folder rendering.
// Extracted from group_workspaces.html inline JS.

function loadGroupWorkspaceTags() {
  if (!activeGroupId) return Promise.resolve();
  return fetch(`/api/group_documents/tags?group_ids=${activeGroupId}`)
    .then(r => r.ok ? r.json() : Promise.reject('Failed to load tags'))
    .then(data => {
      groupWorkspaceTags = data.tags || [];
      // Update tags filter select
      const sel = document.getElementById('group-docs-tags-filter');
      if (sel) {
        const prev = Array.from(sel.selectedOptions).map(o => o.value);
        sel.innerHTML = '';
        groupWorkspaceTags.forEach(t => {
          const opt = document.createElement('option');
          opt.value = t.name;
          opt.textContent = `${t.name} (${t.count})`;
          if (prev.includes(t.name)) opt.selected = true;
          sel.appendChild(opt);
        });
      }
      // Update bulk tag modal list
      updateGroupBulkTagsList();
      // Refresh grid if visible
      if (groupCurrentView === 'grid') renderGroupGridView();
    })
    .catch(err => console.error('Error loading group workspace tags:', err));
}

function setupGroupViewSwitcher() {
  const listRadio = document.getElementById('group-docs-view-list');
  const gridRadio = document.getElementById('group-docs-view-grid');
  if (listRadio) listRadio.addEventListener('change', () => { if (listRadio.checked) switchGroupView('list'); });
  if (gridRadio) gridRadio.addEventListener('change', () => { if (gridRadio.checked) switchGroupView('grid'); });
}

function switchGroupView(view) {
  groupCurrentView = view;
  localStorage.setItem('groupWorkspaceViewPreference', view);
  const listView = document.getElementById('group-documents-list-view');
  const gridView = document.getElementById('group-documents-grid-view');
  const viewInfo = document.getElementById('group-docs-view-info');
  const gridControls = document.getElementById('group-grid-controls-bar');
  const filterBtn = document.getElementById('group-docs-filters-toggle-btn');
  const filterCollapse = document.getElementById('group-docs-filters-collapse');
  const bulkBar = document.getElementById('groupBulkActionsBar');

  if (view === 'list') {
    groupCurrentFolder = null;
    groupCurrentFolderType = null;
    groupFolderCurrentPage = 1;
    groupFolderSortBy = '_ts';
    groupFolderSortOrder = 'desc';
    groupFolderSearchTerm = '';
    const tagContainer = document.getElementById('group-tag-folders-container');
    if (tagContainer) tagContainer.className = 'row g-2';
    if (listView) listView.style.display = 'block';
    if (gridView) gridView.style.display = 'none';
    if (gridControls) gridControls.style.display = 'none';
    if (filterBtn) filterBtn.style.display = '';
    if (viewInfo) viewInfo.textContent = '';
    fetchGroupDocuments();
  } else {
    if (listView) listView.style.display = 'none';
    if (gridView) gridView.style.display = 'block';
    if (gridControls) gridControls.style.display = 'flex';
    if (filterBtn) filterBtn.style.display = 'none';
    if (filterCollapse) {
      const bsCollapse = bootstrap.Collapse.getInstance(filterCollapse);
      if (bsCollapse) bsCollapse.hide();
    }
    if (bulkBar) bulkBar.style.display = 'none';
    renderGroupGridView();
  }
}

async function renderGroupGridView() {
  const container = document.getElementById('group-tag-folders-container');
  if (!container || !activeGroupId) return;

  if (groupCurrentFolder && groupCurrentFolder !== '__untagged__' && groupCurrentFolder !== '__unclassified__') {
    if (groupCurrentFolderType === 'classification') {
      const categories = window.classification_categories || [];
      if (!categories.some(cat => cat.label === groupCurrentFolder)) {
        groupCurrentFolder = null; groupCurrentFolderType = null; groupFolderCurrentPage = 1;
      }
    } else {
      if (!groupWorkspaceTags.some(t => t.name === groupCurrentFolder)) {
        groupCurrentFolder = null; groupCurrentFolderType = null; groupFolderCurrentPage = 1;
      }
    }
  }

  if (groupCurrentFolder) { renderGroupFolderContents(groupCurrentFolder); return; }

  const viewInfo = document.getElementById('group-docs-view-info');
  if (viewInfo) viewInfo.textContent = '';
  container.className = 'row g-2';
  container.innerHTML = '<div class="col-12 text-center text-muted py-5"><div class="spinner-border spinner-border-sm me-2" role="status"><span class="visually-hidden">Loading...</span></div>Loading tag folders...</div>';

  try {
    const docsResponse = await fetch(`/api/group_documents?page_size=1000`);
    const docsData = await docsResponse.json();
    const allDocs = docsData.documents || [];
    const untaggedCount = allDocs.filter(doc => !doc.tags || doc.tags.length === 0).length;

    const classificationEnabled = (window.enable_document_classification === true || window.enable_document_classification === "true");
    const categories = classificationEnabled ? (window.classification_categories || []) : [];
    const classificationCounts = {};
    let unclassifiedCount = 0;
    if (classificationEnabled) {
      allDocs.forEach(doc => {
        const cls = doc.document_classification;
        if (!cls || cls === '' || cls.toLowerCase() === 'none') { unclassifiedCount++; }
        else { classificationCounts[cls] = (classificationCounts[cls] || 0) + 1; }
      });
    }

    const folderItems = [];
    if (untaggedCount > 0) {
      folderItems.push({ type: 'tag', key: '__untagged__', displayName: 'Untagged', count: untaggedCount, icon: 'bi-folder2-open', color: '#6c757d', isSpecial: true });
    }
    if (classificationEnabled && unclassifiedCount > 0) {
      folderItems.push({ type: 'classification', key: '__unclassified__', displayName: 'Unclassified', count: unclassifiedCount, icon: 'bi-bookmark', color: '#6c757d', isSpecial: true });
    }
    groupWorkspaceTags.forEach(tag => {
      folderItems.push({ type: 'tag', key: tag.name, displayName: tag.name, count: tag.count, icon: 'bi-folder-fill', color: tag.color, isSpecial: false, tagData: tag });
    });
    if (classificationEnabled) {
      categories.forEach(cat => {
        const count = classificationCounts[cat.label] || 0;
        if (count > 0) {
          folderItems.push({ type: 'classification', key: cat.label, displayName: cat.label, count: count, icon: 'bi-bookmark-fill', color: cat.color || '#6c757d', isSpecial: false });
        }
      });
    }

    folderItems.sort((a, b) => {
      if (a.isSpecial && !b.isSpecial) return -1;
      if (!a.isSpecial && b.isSpecial) return 1;
      if (groupGridSortBy === 'name') {
        const cmp = a.displayName.localeCompare(b.displayName, undefined, { sensitivity: 'base' });
        return groupGridSortOrder === 'asc' ? cmp : -cmp;
      }
      const cmp = a.count - b.count;
      return groupGridSortOrder === 'asc' ? cmp : -cmp;
    });

    updateGroupGridSortIcons();

    const canManageTags = ['Owner', 'Admin', 'DocumentManager'].includes(userRoleInActiveGroup);
    let html = '';
    folderItems.forEach(item => {
      const ek = escapeHtml(item.key);
      const en = escapeHtml(item.displayName);
      const cl = `${item.count} file${item.count !== 1 ? 's' : ''}`;
      let actionsHtml = '';
      if (item.type === 'tag' && !item.isSpecial && canManageTags) {
        actionsHtml = `<div class="tag-folder-actions"><div class="dropdown">
          <button class="tag-folder-menu-btn" type="button" data-bs-toggle="dropdown" onclick="event.stopPropagation();"><i class="bi bi-three-dots-vertical"></i></button>
          <ul class="dropdown-menu">
            <li><a class="dropdown-item" href="#" onclick="chatWithGroupFolder('tag','${ek}'); return false;"><i class="bi bi-chat-dots me-2"></i>Chat</a></li>
            <li><a class="dropdown-item" href="#" onclick="renameGroupTag('${ek}'); return false;"><i class="bi bi-pencil me-2"></i>Rename Tag</a></li>
            <li><a class="dropdown-item" href="#" onclick="changeGroupTagColor('${ek}','${item.tagData.color}'); return false;"><i class="bi bi-palette me-2"></i>Change Color</a></li>
            <li><hr class="dropdown-divider"></li>
            <li><a class="dropdown-item text-danger" href="#" onclick="deleteGroupTag('${ek}'); return false;"><i class="bi bi-trash me-2"></i>Delete Tag</a></li>
          </ul></div></div>`;
      } else if (item.type === 'classification') {
        actionsHtml = `<div class="tag-folder-actions"><div class="dropdown">
          <button class="tag-folder-menu-btn" type="button" data-bs-toggle="dropdown" onclick="event.stopPropagation();"><i class="bi bi-three-dots-vertical"></i></button>
          <ul class="dropdown-menu">
            <li><a class="dropdown-item" href="#" onclick="chatWithGroupFolder('classification','${ek}'); return false;"><i class="bi bi-chat-dots me-2"></i>Chat</a></li>
          </ul></div></div>`;
      } else if (item.type === 'tag' && item.isSpecial) {
        actionsHtml = `<div class="tag-folder-actions"><div class="dropdown">
          <button class="tag-folder-menu-btn" type="button" data-bs-toggle="dropdown" onclick="event.stopPropagation();"><i class="bi bi-three-dots-vertical"></i></button>
          <ul class="dropdown-menu">
            <li><a class="dropdown-item" href="#" onclick="chatWithGroupFolder('tag','${ek}'); return false;"><i class="bi bi-chat-dots me-2"></i>Chat</a></li>
          </ul></div></div>`;
      }
      html += `<div class="col-6 col-sm-4 col-md-3 col-lg-2">
        <div class="tag-folder-card" data-tag="${ek}" data-folder-type="${item.type}" title="${en} (${cl})">
          ${actionsHtml}
          <div class="tag-folder-icon"><i class="bi ${item.icon}" style="color: ${item.color};"></i></div>
          <div class="tag-folder-name${item.isSpecial ? ' text-muted' : ''}">${en}</div>
          <div class="tag-folder-count">${cl}</div>
        </div></div>`;
    });

    if (folderItems.length === 0) {
      html = '<div class="col-12 text-center text-muted py-5"><i class="bi bi-folder2-open display-1 mb-3"></i><p>No folders yet. Add tags to documents to organize them.</p></div>';
    }
    container.innerHTML = html;
    container.querySelectorAll('.tag-folder-card').forEach(card => {
      card.addEventListener('click', (e) => {
        if (e.target.closest('.tag-folder-actions')) return;
        groupCurrentFolder = card.getAttribute('data-tag');
        groupCurrentFolderType = card.getAttribute('data-folder-type') || 'tag';
        groupFolderCurrentPage = 1;
        groupFolderSortBy = '_ts'; groupFolderSortOrder = 'desc'; groupFolderSearchTerm = '';
        renderGroupFolderContents(groupCurrentFolder);
      });
    });
  } catch (error) {
    console.error('Error rendering group grid view:', error);
    container.innerHTML = '<div class="col-12 text-center text-danger py-5"><i class="bi bi-exclamation-triangle display-4 mb-2"></i><p>Error loading tag folders</p></div>';
  }
}

function buildGroupBreadcrumbHtml(displayName, tagColor, folderType) {
  const icon = folderType === 'classification' ? 'bi-bookmark-fill' : 'bi-folder-fill';
  return `<div class="folder-breadcrumb">
    <a href="#" class="group-folder-back-btn"><i class="bi bi-arrow-left me-1"></i>All Folders</a>
    <span class="mx-2">/</span>
    <i class="bi ${icon} me-1" style="color: ${tagColor};"></i>
    <strong>${escapeHtml(displayName)}</strong>
  </div>`;
}

function wireGroupBackButton(container) {
  container.querySelectorAll('.group-folder-back-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      groupCurrentFolder = null; groupCurrentFolderType = null;
      groupFolderCurrentPage = 1; groupFolderSearchTerm = '';
      const gridControls = document.getElementById('group-grid-controls-bar');
      if (gridControls) gridControls.style.display = 'flex';
      renderGroupGridView();
    });
  });
}

function buildGroupFolderDocumentsTable(docs) {
  let sortIconFn = (field) => {
    if (groupFolderSortBy === field) {
      return groupFolderSortOrder === 'asc' ? 'bi-sort-up' : 'bi-sort-down';
    }
    return 'bi-arrow-down-up text-muted';
  };
  let html = `<table class="table table-striped table-sm"><thead><tr>
    <th style="width:50px;"></th>
    <th class="folder-sortable-header" data-sort-field="file_name" style="cursor:pointer;user-select:none;">File Name <i class="bi ${sortIconFn('file_name')} small"></i></th>
    <th class="folder-sortable-header" data-sort-field="title" style="cursor:pointer;user-select:none;">Title <i class="bi ${sortIconFn('title')} small"></i></th>
    <th style="width:240px;">Actions</th>
  </tr></thead><tbody>`;

  const groupStatus = window.currentGroupStatus || 'active';
  const canManage = ["Owner", "Admin", "DocumentManager"].includes(userRoleInActiveGroup);
  const canModify = (groupStatus === 'active');
  const canChat = (groupStatus !== 'inactive');

  docs.forEach(doc => {
    const docId = doc.id;
    const pctStr = String(doc.percentage_complete);
    const pct = /^\d+(\.\d+)?$/.test(pctStr) ? parseFloat(pctStr) : 0;
    const docStatus = doc.status || '';
    const isComplete = pct >= 100
        || docStatus.toLowerCase().includes('complete')
        || docStatus.toLowerCase().includes('error');
    const hasError = docStatus.toLowerCase().includes('error');

    // First column: expand/collapse or status indicator
    let firstColHtml = '';
    if (isComplete && !hasError) {
      firstColHtml = `<button class="btn btn-link p-0" onclick="onEditGroupDocument('${docId}')" title="View Metadata"><span class="bi bi-chevron-right"></span></button>`;
    } else if (hasError) {
      firstColHtml = `<span class="text-danger" title="Processing Error: ${escapeHtml(docStatus)}"><i class="bi bi-exclamation-triangle-fill"></i></span>`;
    } else {
      firstColHtml = `<span class="text-muted" title="Processing: ${escapeHtml(docStatus)} (${pct.toFixed(0)}%)"><i class="bi bi-hourglass-split"></i></span>`;
    }

    // Chat button
    let chatButton = '';
    if (isComplete && !hasError && canChat) {
      chatButton = `<button class="btn btn-sm btn-primary me-1 action-btn-wide text-start" onclick="searchGroupDocumentInChat('${docId}')" title="Open Chat for Document" aria-label="Open Chat for Document: ${escapeHtml(doc.file_name || 'Untitled')}"><i class="bi bi-chat-dots-fill me-1" aria-hidden="true"></i>Chat</button>`;
    }

    // Actions dropdown
    let actionsDropdown = '';
    if (isComplete && !hasError) {
      actionsDropdown = `<div class="dropdown action-dropdown d-inline-block"><button class="btn btn-sm btn-outline-secondary dropdown-toggle" type="button" data-bs-toggle="dropdown" aria-expanded="false"><i class="bi bi-three-dots-vertical"></i></button><ul class="dropdown-menu dropdown-menu-end"><li><a class="dropdown-item select-btn" href="#" onclick="toggleGroupSelectionMode(); return false;"><i class="bi bi-check-square me-2"></i>Select</a></li>`;

      if (canModify) {
        actionsDropdown += `<li><hr class="dropdown-divider"></li><li><a class="dropdown-item" href="#" onclick="onEditGroupDocument('${docId}'); return false;"><i class="bi bi-pencil-fill me-2"></i>Edit Metadata</a></li>`;
        if (window.enable_extract_meta_data === true || window.enable_extract_meta_data === "true") {
          actionsDropdown += `<li><a class="dropdown-item" href="#" onclick="onExtractGroupMetadata('${docId}', event); return false;"><i class="bi bi-magic me-2"></i>Extract Metadata</a></li>`;
        }
      }

      if (canChat) {
        actionsDropdown += `<li><a class="dropdown-item" href="#" onclick="searchGroupDocumentInChat('${docId}'); return false;"><i class="bi bi-chat-dots-fill me-2"></i>Chat</a></li>`;
      }

      if (canManage) {
        const canShare = (groupStatus === 'active' || groupStatus === 'upload_disabled');
        if (canShare) {
          actionsDropdown += `<li><hr class="dropdown-divider"></li><li><a class="dropdown-item" href="#" onclick="shareGroupDocument('${escapeHtml(docId)}', '${escapeHtml(doc.file_name || '')}'); return false;"><i class="bi bi-share-fill me-2"></i>Share<span class="badge bg-secondary ms-1">${doc.shared_group_ids ? doc.shared_group_ids.length : 0}</span></a></li>`;
        }
        const canDelete = (groupStatus === 'active' || groupStatus === 'upload_disabled');
        if (canDelete) {
          actionsDropdown += `<li><hr class="dropdown-divider"></li><li><a class="dropdown-item text-danger" href="#" onclick="deleteGroupDocument('${escapeHtml(docId)}', event); return false;"><i class="bi bi-trash-fill me-2"></i>Delete</a></li>`;
        }
      }

      actionsDropdown += `</ul></div>`;
    } else if (canManage) {
      const canDelete = (groupStatus === 'active' || groupStatus === 'upload_disabled');
      if (canDelete) {
        actionsDropdown = `<div class="dropdown action-dropdown d-inline-block"><button class="btn btn-sm btn-outline-secondary dropdown-toggle" type="button" data-bs-toggle="dropdown" aria-expanded="false"><i class="bi bi-three-dots-vertical"></i></button><ul class="dropdown-menu dropdown-menu-end"><li><a class="dropdown-item text-danger" href="#" onclick="deleteGroupDocument('${escapeHtml(docId)}', event); return false;"><i class="bi bi-trash-fill me-2"></i>Delete</a></li></ul></div>`;
      }
    }

    html += `<tr>
      <td class="align-middle">${firstColHtml}</td>
      <td class="align-middle" title="${escapeHtml(doc.file_name || '')}" style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${escapeHtml(doc.file_name || '')}</td>
      <td class="align-middle" title="${escapeHtml(doc.title || '')}" style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${escapeHtml(doc.title || 'N/A')}</td>
      <td class="align-middle">${chatButton}${actionsDropdown}</td>
    </tr>`;
  });
  html += '</tbody></table>';
  return html;
}

async function renderGroupFolderContents(tagName) {
  const container = document.getElementById('group-tag-folders-container');
  if (!container) return;
  const gridControls = document.getElementById('group-grid-controls-bar');
  if (gridControls) gridControls.style.display = 'none';
  container.className = '';

  const isClassification = (groupCurrentFolderType === 'classification');
  let displayName, tagColor;
  if (tagName === '__untagged__') { displayName = 'Untagged Documents'; tagColor = '#6c757d'; }
  else if (tagName === '__unclassified__') { displayName = 'Unclassified Documents'; tagColor = '#6c757d'; }
  else if (isClassification) {
    const cat = (window.classification_categories || []).find(c => c.label === tagName);
    displayName = tagName; tagColor = cat?.color || '#6c757d';
  } else {
    const tagInfo = groupWorkspaceTags.find(t => t.name === tagName);
    displayName = tagName; tagColor = tagInfo?.color || '#6c757d';
  }

  const viewInfo = document.getElementById('group-docs-view-info');
  if (viewInfo) viewInfo.textContent = `Viewing: ${displayName}`;

  container.innerHTML = buildGroupBreadcrumbHtml(displayName, tagColor, groupCurrentFolderType || 'tag') +
    '<div class="text-center text-muted py-4"><div class="spinner-border spinner-border-sm me-2" role="status"><span class="visually-hidden">Loading...</span></div>Loading documents...</div>';
  wireGroupBackButton(container);

  try {
    let docs, totalCount;
    if (tagName === '__untagged__') {
      const resp = await fetch(`/api/group_documents?page_size=1000${groupFolderSearchTerm ? '&search=' + encodeURIComponent(groupFolderSearchTerm) : ''}`);
      const data = await resp.json();
      let allUntagged = (data.documents || []).filter(d => !d.tags || d.tags.length === 0);
      if (groupFolderSortBy !== '_ts') {
        allUntagged.sort((a, b) => {
          const va = (a[groupFolderSortBy] || '').toLowerCase();
          const vb = (b[groupFolderSortBy] || '').toLowerCase();
          const cmp = va.localeCompare(vb);
          return groupFolderSortOrder === 'asc' ? cmp : -cmp;
        });
      }
      totalCount = allUntagged.length;
      const start = (groupFolderCurrentPage - 1) * groupFolderPageSize;
      docs = allUntagged.slice(start, start + groupFolderPageSize);
    } else if (tagName === '__unclassified__') {
      const params = new URLSearchParams({ page: groupFolderCurrentPage, page_size: groupFolderPageSize, classification: 'none' });
      if (groupFolderSearchTerm) params.append('search', groupFolderSearchTerm);
      if (groupFolderSortBy !== '_ts') params.append('sort_by', groupFolderSortBy);
      if (groupFolderSortOrder !== 'desc') params.append('sort_order', groupFolderSortOrder);
      const resp = await fetch(`/api/group_documents?${params.toString()}`);
      const data = await resp.json();
      docs = data.documents || []; totalCount = data.total_count || docs.length;
    } else if (isClassification) {
      const params = new URLSearchParams({ page: groupFolderCurrentPage, page_size: groupFolderPageSize, classification: tagName });
      if (groupFolderSearchTerm) params.append('search', groupFolderSearchTerm);
      if (groupFolderSortBy !== '_ts') params.append('sort_by', groupFolderSortBy);
      if (groupFolderSortOrder !== 'desc') params.append('sort_order', groupFolderSortOrder);
      const resp = await fetch(`/api/group_documents?${params.toString()}`);
      const data = await resp.json();
      docs = data.documents || []; totalCount = data.total_count || docs.length;
    } else {
      const params = new URLSearchParams({ page: groupFolderCurrentPage, page_size: groupFolderPageSize, tags: tagName });
      if (groupFolderSearchTerm) params.append('search', groupFolderSearchTerm);
      if (groupFolderSortBy !== '_ts') params.append('sort_by', groupFolderSortBy);
      if (groupFolderSortOrder !== 'desc') params.append('sort_order', groupFolderSortOrder);
      const resp = await fetch(`/api/group_documents?${params.toString()}`);
      const data = await resp.json();
      docs = data.documents || []; totalCount = data.total_count || docs.length;
    }

    let html = buildGroupBreadcrumbHtml(displayName, tagColor, groupCurrentFolderType || 'tag');
    html += `<div class="d-flex align-items-center gap-2 mb-2">
      <div class="input-group input-group-sm" style="max-width: 320px;">
        <input type="search" id="group-folder-search-input" class="form-control form-control-sm" placeholder="Search file name or title..." value="${escapeHtml(groupFolderSearchTerm)}">
        <button class="btn btn-outline-secondary" type="button" id="group-folder-search-btn"><i class="bi bi-search"></i></button>
      </div>
      <span class="text-muted small">${totalCount} document(s)</span>
      <div class="ms-auto">
        <select id="group-folder-page-size-select" class="form-select form-select-sm d-inline-block" style="width:auto;">
          <option value="10"${groupFolderPageSize === 10 ? ' selected' : ''}>10</option>
          <option value="20"${groupFolderPageSize === 20 ? ' selected' : ''}>20</option>
          <option value="50"${groupFolderPageSize === 50 ? ' selected' : ''}>50</option>
        </select>
        <span class="ms-1 small text-muted">per page</span>
      </div>
    </div>`;

    if (docs.length === 0) {
      html += '<div class="text-center text-muted py-4"><i class="bi bi-folder2-open display-4 d-block mb-2"></i><p>No documents found in this folder.</p></div>';
    } else {
      html += buildGroupFolderDocumentsTable(docs);
      html += '<div id="group-folder-pagination" class="d-flex justify-content-center mt-3"></div>';
    }

    container.innerHTML = html;
    wireGroupBackButton(container);

    // Wire search
    const si = document.getElementById('group-folder-search-input');
    const sb = document.getElementById('group-folder-search-btn');
    if (si) {
      const doSearch = () => { groupFolderSearchTerm = si.value.trim(); groupFolderCurrentPage = 1; renderGroupFolderContents(groupCurrentFolder); };
      sb?.addEventListener('click', doSearch);
      si.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); doSearch(); } });
      si.addEventListener('search', doSearch);
    }

    // Wire page size
    const fps = document.getElementById('group-folder-page-size-select');
    if (fps) fps.addEventListener('change', (e) => { groupFolderPageSize = parseInt(e.target.value, 10); groupFolderCurrentPage = 1; renderGroupFolderContents(groupCurrentFolder); });

    // Wire sortable headers
    container.querySelectorAll('.folder-sortable-header').forEach(th => {
      th.addEventListener('click', () => {
        const field = th.getAttribute('data-sort-field');
        if (groupFolderSortBy === field) { groupFolderSortOrder = groupFolderSortOrder === 'asc' ? 'desc' : 'asc'; }
        else { groupFolderSortBy = field; groupFolderSortOrder = 'asc'; }
        groupFolderCurrentPage = 1;
        renderGroupFolderContents(groupCurrentFolder);
      });
    });

    if (docs.length > 0) renderGroupFolderPagination(groupFolderCurrentPage, groupFolderPageSize, totalCount);
  } catch (error) {
    console.error('Error loading group folder contents:', error);
    container.innerHTML = buildGroupBreadcrumbHtml(displayName, tagColor, groupCurrentFolderType || 'tag') +
      '<div class="text-center text-danger py-4"><i class="bi bi-exclamation-triangle display-4 d-block mb-2"></i><p>Error loading documents.</p></div>';
    wireGroupBackButton(container);
  }
}

function renderGroupFolderPagination(currentPage, pageSize, totalCount) {
  const container = document.getElementById('group-folder-pagination');
  if (!container) return;
  const totalPages = Math.ceil(totalCount / pageSize);
  if (totalPages <= 1) { container.innerHTML = ''; return; }
  let html = '';
  html += `<button class="btn btn-sm btn-outline-secondary${currentPage <= 1 ? ' disabled' : ''}" onclick="groupFolderGoToPage(${currentPage - 1})">&laquo;</button>`;
  for (let i = 1; i <= totalPages; i++) {
    if (i === currentPage) html += `<button class="btn btn-sm btn-primary">${i}</button>`;
    else if (i <= 2 || i > totalPages - 2 || Math.abs(i - currentPage) <= 1) html += `<button class="btn btn-sm btn-outline-secondary" onclick="groupFolderGoToPage(${i})">${i}</button>`;
    else if (i === 3 && currentPage > 4) html += '<span class="px-1">...</span>';
    else if (i === totalPages - 2 && currentPage < totalPages - 3) html += '<span class="px-1">...</span>';
  }
  html += `<button class="btn btn-sm btn-outline-secondary${currentPage >= totalPages ? ' disabled' : ''}" onclick="groupFolderGoToPage(${currentPage + 1})">&raquo;</button>`;
  container.innerHTML = html;
}
window.groupFolderGoToPage = function(page) {
  groupFolderCurrentPage = page;
  renderGroupFolderContents(groupCurrentFolder);
};

function chatWithGroupFolder(folderType, folderName) {
  const encoded = encodeURIComponent(folderName);
  if (folderType === 'classification') {
    window.location.href = `/chats?search_documents=true&doc_scope=group&classification=${encoded}&group_id=${activeGroupId}`;
  } else {
    window.location.href = `/chats?search_documents=true&doc_scope=group&tags=${encoded}&group_id=${activeGroupId}`;
  }
}
window.chatWithGroupFolder = chatWithGroupFolder;

function renameGroupTag(tagName) {
  const newName = prompt(`Rename tag "${tagName}" to:`, tagName);
  if (!newName || newName.trim() === tagName) return;
  fetch(`/api/group_documents/tags/${encodeURIComponent(tagName)}`, {
    method: 'PATCH', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ new_name: newName.trim() })
  }).then(r => r.json().then(d => ({ ok: r.ok, data: d })))
    .then(({ ok, data }) => {
      if (ok) { alert(data.message); loadGroupWorkspaceTags(); if (groupCurrentView === 'grid') renderGroupGridView(); else fetchGroupDocuments(); }
      else alert('Error: ' + (data.error || 'Failed to rename'));
    }).catch(e => { console.error(e); alert('Error renaming tag'); });
}
window.renameGroupTag = renameGroupTag;

function changeGroupTagColor(tagName, currentColor) {
  const newColor = prompt(`Enter new hex color for "${tagName}":`, currentColor || '#0d6efd');
  if (!newColor || newColor === currentColor) return;
  fetch(`/api/group_documents/tags/${encodeURIComponent(tagName)}`, {
    method: 'PATCH', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ color: newColor.trim() })
  }).then(r => r.json().then(d => ({ ok: r.ok, data: d })))
    .then(({ ok, data }) => {
      if (ok) { alert(data.message); loadGroupWorkspaceTags(); if (groupCurrentView === 'grid') renderGroupGridView(); }
      else alert('Error: ' + (data.error || 'Failed to change color'));
    }).catch(e => { console.error(e); alert('Error changing tag color'); });
}
window.changeGroupTagColor = changeGroupTagColor;

function deleteGroupTag(tagName) {
  if (!confirm(`Delete tag "${tagName}" from all documents?`)) return;
  fetch(`/api/group_documents/tags/${encodeURIComponent(tagName)}`, { method: 'DELETE' })
    .then(r => r.json().then(d => ({ ok: r.ok, data: d })))
    .then(({ ok, data }) => {
      if (ok) { alert(data.message); loadGroupWorkspaceTags(); if (groupCurrentView === 'grid') renderGroupGridView(); else fetchGroupDocuments(); }
      else alert('Error: ' + (data.error || 'Failed to delete'));
    }).catch(e => { console.error(e); alert('Error deleting tag'); });
}
window.deleteGroupTag = deleteGroupTag;

function updateGroupListSortIcons() {
  document.querySelectorAll('#group-documents-table .sortable-header .sort-icon').forEach(icon => {
    const field = icon.closest('.sortable-header').getAttribute('data-sort-field');
    icon.className = 'bi small sort-icon';
    if (groupDocsSortBy === field) {
      icon.classList.add(groupDocsSortOrder === 'asc' ? 'bi-sort-up' : 'bi-sort-down');
    } else {
      icon.classList.add('bi-arrow-down-up', 'text-muted');
    }
  });
}

function updateGroupGridSortIcons() {
  const bar = document.getElementById('group-grid-controls-bar');
  if (!bar) return;
  bar.querySelectorAll('.group-grid-sort-icon').forEach(icon => {
    const field = icon.getAttribute('data-sort');
    icon.className = 'bi ms-1 group-grid-sort-icon';
    icon.setAttribute('data-sort', field);
    if (groupGridSortBy === field) {
      icon.classList.add(field === 'name' ? (groupGridSortOrder === 'asc' ? 'bi-sort-alpha-down' : 'bi-sort-alpha-up') : (groupGridSortOrder === 'asc' ? 'bi-sort-numeric-down' : 'bi-sort-numeric-up'));
    } else {
      icon.classList.add('bi-arrow-down-up', 'text-muted');
    }
  });
}

function updateGroupBulkTagsList() {
  const listEl = document.getElementById('group-bulk-tags-list');
  if (!listEl) return;
  if (groupWorkspaceTags.length === 0) {
    listEl.innerHTML = '<div class="text-muted w-100 text-center py-3">No tags available. Create some first.</div>';
    return;
  }
  listEl.innerHTML = '';
  groupWorkspaceTags.forEach(tag => {
    const el = document.createElement('span');
    el.className = `tag-badge ${isColorLight(tag.color) ? 'text-dark' : 'text-light'}`;
    el.style.backgroundColor = tag.color;
    el.style.border = groupBulkSelectedTags.has(tag.name) ? '3px solid #000' : '3px solid transparent';
    el.textContent = tag.name;
    el.style.cursor = 'pointer';
    el.addEventListener('click', () => {
      if (groupBulkSelectedTags.has(tag.name)) { groupBulkSelectedTags.delete(tag.name); el.style.border = '3px solid transparent'; }
      else { groupBulkSelectedTags.add(tag.name); el.style.border = '3px solid #000'; }
    });
    listEl.appendChild(el);
  });
}

async function applyGroupBulkTagChanges() {
  const action = document.getElementById('group-bulk-tag-action').value;
  const selectedTags = Array.from(groupBulkSelectedTags);
  const documentIds = Array.from(groupSelectedDocuments);
  if (documentIds.length === 0) { alert('No documents selected'); return; }
  if (selectedTags.length === 0) { alert('Please select at least one tag'); return; }

  const applyBtn = document.getElementById('group-bulk-tag-apply-btn');
  const btnText = applyBtn.querySelector('.button-text');
  const btnLoad = applyBtn.querySelector('.button-loading');
  applyBtn.disabled = true; btnText.classList.add('d-none'); btnLoad.classList.remove('d-none');

  try {
    const response = await fetch('/api/group_documents/bulk-tag', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ document_ids: documentIds, action: action, tags: selectedTags })
    });
    const result = await response.json();
    if (response.ok) {
      const sc = result.success?.length || 0;
      const ec = result.errors?.length || 0;
      let msg = `Tags updated for ${sc} document(s)`;
      if (ec > 0) msg += `\n${ec} document(s) had errors`;
      alert(msg);
      await loadGroupWorkspaceTags();
      fetchGroupDocuments();
      groupSelectedDocuments.clear();
      const bar = document.getElementById('groupBulkActionsBar');
      if (bar) bar.style.display = 'none';
      const modal = bootstrap.Modal.getInstance(document.getElementById('groupBulkTagModal'));
      if (modal) modal.hide();
    } else { alert('Error: ' + (result.error || 'Failed to update tags')); }
  } catch (e) { console.error(e); alert('Error updating tags'); }
  finally { applyBtn.disabled = false; btnText.classList.remove('d-none'); btnLoad.classList.add('d-none'); }
}

// Wire up grid view events on DOMContentLoaded
(function initGroupGridView() {
  setupGroupViewSwitcher();

  // Load saved view preference
  const savedView = localStorage.getItem('groupWorkspaceViewPreference');
  if (savedView === 'grid') {
    const gridRadio = document.getElementById('group-docs-view-grid');
    if (gridRadio) { gridRadio.checked = true; switchGroupView('grid'); }
  }

  // Wire sortable headers in list view
  document.querySelectorAll('#group-documents-table .sortable-header').forEach(th => {
    th.addEventListener('click', () => {
      const field = th.getAttribute('data-sort-field');
      if (groupDocsSortBy === field) { groupDocsSortOrder = groupDocsSortOrder === 'asc' ? 'desc' : 'asc'; }
      else { groupDocsSortBy = field; groupDocsSortOrder = 'asc'; }
      groupDocsCurrentPage = 1;
      updateGroupListSortIcons();
      fetchGroupDocuments();
    });
  });

  // Wire grid sort buttons
  document.querySelectorAll('#group-grid-controls-bar .group-grid-sort-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const field = btn.getAttribute('data-sort');
      if (groupGridSortBy === field) { groupGridSortOrder = groupGridSortOrder === 'asc' ? 'desc' : 'asc'; }
      else { groupGridSortBy = field; groupGridSortOrder = field === 'name' ? 'asc' : 'desc'; }
      renderGroupGridView();
    });
  });

  // Wire grid page size
  const gps = document.getElementById('group-grid-page-size-select');
  if (gps) gps.addEventListener('change', (e) => { groupFolderPageSize = parseInt(e.target.value, 10); groupFolderCurrentPage = 1; if (groupCurrentFolder) renderGroupFolderContents(groupCurrentFolder); });

  // Wire bulk tag modal
  const bulkTagModal = document.getElementById('groupBulkTagModal');
  if (bulkTagModal) {
    bulkTagModal.addEventListener('show.bs.modal', () => {
      document.getElementById('group-bulk-tag-doc-count').textContent = groupSelectedDocuments.size;
      groupBulkSelectedTags.clear();
      updateGroupBulkTagsList();
    });
  }
  const bulkApply = document.getElementById('group-bulk-tag-apply-btn');
  if (bulkApply) bulkApply.addEventListener('click', applyGroupBulkTagChanges);

  // Wire bulk create tag button
  const bulkCreate = document.getElementById('group-bulk-create-tag-btn');
  if (bulkCreate) {
    bulkCreate.addEventListener('click', async () => {
      const name = prompt('Enter new tag name:');
      if (!name) return;
      try {
        const resp = await fetch('/api/group_documents/tags', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ tag_name: name.trim() })
        });
        const data = await resp.json();
        if (resp.ok) { await loadGroupWorkspaceTags(); updateGroupBulkTagsList(); }
        else alert('Error: ' + (data.error || 'Failed to create tag'));
      } catch (e) { console.error(e); alert('Error creating tag'); }
    });
  }
})();

// ============ Group Tag Management & Selection Functions ============
