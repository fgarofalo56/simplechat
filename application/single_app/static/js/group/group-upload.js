// group-upload.js
// Group document upload, drag-and-drop, and file input handling.
// Extracted from group_workspaces.html inline JS.

// --- Group Upload: Auto-upload on file select and drag-and-drop ---
/**
 * Upload files utility for group workspace.
 * @param {FileList|File[]} files - The files to upload.
 */
async function uploadGroupFiles(files) {
  if (!files || files.length === 0) {
    alert("Please select file(s) to upload.");
    return;
  }

  // Client-side file size validation
  const maxFileSizeMB = window.max_file_size_mb || 16; // Default to 16MB if not set
  const maxFileSizeBytes = maxFileSizeMB * 1024 * 1024;
  
  for (const file of files) {
      if (file.size > maxFileSizeBytes) {
          const fileSizeMB = (file.size / (1024 * 1024)).toFixed(1);
          alert(`File "${file.name}" (${fileSizeMB} MB) exceeds the maximum allowed size of ${maxFileSizeMB} MB. Please select a smaller file.`);
          return;
      }
  }

  groupUploadStatusSpan.textContent = `Preparing ${files.length} file(s)...`;

  // Per-file progress container
  const progressContainer = document.getElementById("group-upload-progress-container");
  if (progressContainer) progressContainer.innerHTML = "";

  let completed = 0;
  let failed = 0;

  // Helper to create a unique ID for each file
  function makeId(file) {
    return 'group-progress-' + Math.random().toString(36).slice(2, 10) + '-' + encodeURIComponent(file.name.replace(/\W+/g, ''));
  }

  // Helper to create progress bar/status for a file
  function createProgressBar(file, id) {
    const wrapper = document.createElement('div');
    wrapper.className = 'mb-2';
    wrapper.id = id + '-wrapper';
    wrapper.innerHTML = `
      <div class="progress" style="height: 10px;" title="Status: Uploading ${escapeHtml(file.name)} (0%)">
        <div id="${id}" class="progress-bar progress-bar-striped progress-bar-animated bg-info" role="progressbar" style="width: 0%;" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100"></div>
      </div>
      <div class="text-muted text-end small" id="${id}-text">Uploading ${escapeHtml(file.name)} (0%)</div>
    `;
    return wrapper;
  }

  // Upload each file individually with progress
  Array.from(files).forEach(file => {
    const id = makeId(file);
    if (progressContainer) progressContainer.appendChild(createProgressBar(file, id));

    const progressBar = document.getElementById(id);
    const statusText = document.getElementById(id + '-text');

    const formData = new FormData();
    formData.append("file", file, file.name);

    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/group_documents/upload", true);

    xhr.upload.onprogress = function (e) {
      if (e.lengthComputable) {
        const percent = Math.round((e.loaded / e.total) * 100);
        if (progressBar) {
          progressBar.style.width = percent + '%';
          progressBar.setAttribute('aria-valuenow', percent);
        }
        if (statusText) {
          statusText.textContent = `Uploading ${file.name} (${percent}%)`;
        }
      }
    };

    xhr.onload = function () {
      if (xhr.status >= 200 && xhr.status < 300) {
        if (progressBar) {
          progressBar.classList.remove('bg-info');
          progressBar.classList.add('bg-success');
          progressBar.classList.remove('progress-bar-animated');
        }
        if (statusText) {
          statusText.textContent = `Uploaded ${file.name} (100%)`;
        }
        completed++;
      } else {
        if (progressBar) {
          progressBar.classList.remove('bg-info');
          progressBar.classList.add('bg-danger');
          progressBar.classList.remove('progress-bar-animated');
        }
        if (statusText) {
          statusText.textContent = `Failed to upload ${file.name}`;
        }
        failed++;
      }
      // Update summary status
      groupUploadStatusSpan.textContent = `Uploaded ${completed}/${files.length}${failed ? `, Failed: ${failed}` : ''}`;
      if (completed + failed === files.length) {
        groupFileInput.value = '';
        groupDocsCurrentPage = 1;
        fetchGroupDocuments();
        // Clear upload progress bars after all uploads and table refresh
        if (progressContainer) progressContainer.innerHTML = '';
      }
    };

    xhr.onerror = function () {
      if (progressBar) {
        progressBar.classList.remove('bg-info');
        progressBar.classList.add('bg-danger');
        progressBar.classList.remove('progress-bar-animated');
      }
      if (statusText) {
        statusText.textContent = `Failed to upload ${file.name}`;
      }
      failed++;
      groupUploadStatusSpan.textContent = `Uploaded ${completed}/${files.length}${failed ? `, Failed: ${failed}` : ''}`;
      if (completed + failed === files.length) {
        groupFileInput.value = '';
        groupDocsCurrentPage = 1;
        fetchGroupDocuments();
        if (progressContainer) progressContainer.innerHTML = '';
      }
    };

    xhr.send(formData);
  });
}

// Manual button click (fallback)
const uploadArea = document.getElementById("upload-area");
if (groupFileInput && uploadArea && groupUploadStatusSpan) {
  // Auto-upload on file selection (with user agreement check)
  groupFileInput.addEventListener("change", () => {
    if (groupFileInput.files && groupFileInput.files.length > 0) {
      // Check for user agreement before uploading
      if (window.UserAgreementManager && activeGroupId) {
        window.UserAgreementManager.checkBeforeUpload(
          groupFileInput.files,
          'group',
          activeGroupId,
          function(files) {
            uploadGroupFiles(files);
          }
        );
      } else {
        uploadGroupFiles(groupFileInput.files);
      }
    }
  });

  // Click on area triggers file input
  uploadArea.addEventListener("click", (e) => {
    if (e.target !== groupFileInput) {
      groupFileInput.click();
    }
  });

  // Drag-and-drop support
  uploadArea.addEventListener("dragover", (e) => {
    e.preventDefault();
    uploadArea.classList.add("dragover");
    uploadArea.style.borderColor = "#0d6efd";
  });
  uploadArea.addEventListener("dragleave", (e) => {
    e.preventDefault();
    uploadArea.classList.remove("dragover");
    uploadArea.style.borderColor = "";
  });
  uploadArea.addEventListener("drop", (e) => {
    e.preventDefault();
    uploadArea.classList.remove("dragover");
    uploadArea.style.borderColor = "";
    if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      // Check for user agreement before uploading (drag-and-drop)
      if (window.UserAgreementManager && activeGroupId) {
        window.UserAgreementManager.checkBeforeUpload(
          e.dataTransfer.files,
          'group',
          activeGroupId,
          function(files) {
            uploadGroupFiles(files);
          }
        );
      } else {
        uploadGroupFiles(e.dataTransfer.files);
      }
    }
  });
}

async function onGroupUploadClick() {
  // --- File selection and validation ---
  const files = groupFileInput.files;
  if (!files || files.length === 0) {
    alert("Please select file(s) to upload.");
    return;
  }

  // Client-side file size validation
  const maxFileSizeMB = window.max_file_size_mb || 16; // Default to 16MB if not set
  const maxFileSizeBytes = maxFileSizeMB * 1024 * 1024;
  
  for (const file of files) {
      if (file.size > maxFileSizeBytes) {
          const fileSizeMB = (file.size / (1024 * 1024)).toFixed(1);
          alert(`File "${file.name}" (${fileSizeMB} MB) exceeds the maximum allowed size of ${maxFileSizeMB} MB. Please select a smaller file.`);
          return;
      }
  }

  groupUploadBtn.disabled = true;
  groupUploadBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Preparing...`;
  groupUploadStatusSpan.textContent = `Preparing ${files.length} file(s)...`;

  // Per-file progress container
  const progressContainer = document.getElementById("group-upload-progress-container");
  if (progressContainer) progressContainer.innerHTML = "";

  let completed = 0;
  let failed = 0;

  // Helper to create a unique ID for each file
  function makeId(file) {
    return 'group-progress-' + Math.random().toString(36).slice(2, 10) + '-' + encodeURIComponent(file.name.replace(/\W+/g, ''));
  }

  // Helper to create progress bar/status for a file
  function createProgressBar(file, id) {
    const wrapper = document.createElement('div');
    wrapper.className = 'mb-2';
    wrapper.id = id + '-wrapper';
    wrapper.innerHTML = `
      <div class="progress" style="height: 10px;" title="Status: Uploading ${escapeHtml(file.name)} (0%)">
        <div id="${id}" class="progress-bar progress-bar-striped progress-bar-animated bg-info" role="progressbar" style="width: 0%;" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100"></div>
      </div>
      <div class="text-muted text-end small" id="${id}-text">Uploading ${escapeHtml(file.name)} (0%)</div>
    `;
    return wrapper;
  }

  // Upload each file individually with progress
  Array.from(files).forEach(file => {
    const id = makeId(file);
    if (progressContainer) progressContainer.appendChild(createProgressBar(file, id));

    const progressBar = document.getElementById(id);
    const statusText = document.getElementById(id + '-text');

    const formData = new FormData();
    formData.append("file", file, file.name);

    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/group_documents/upload", true);

    xhr.upload.onprogress = function (e) {
      if (e.lengthComputable) {
        const percent = Math.round((e.loaded / e.total) * 100);
        if (progressBar) {
          progressBar.style.width = percent + '%';
          progressBar.setAttribute('aria-valuenow', percent);
        }
        if (statusText) {
          statusText.textContent = `Uploading ${file.name} (${percent}%)`;
        }
      }
    };

    xhr.onload = function () {
      if (xhr.status >= 200 && xhr.status < 300) {
        if (progressBar) {
          progressBar.classList.remove('bg-info');
          progressBar.classList.add('bg-success');
          progressBar.classList.remove('progress-bar-animated');
        }
        if (statusText) {
          statusText.textContent = `Uploaded ${file.name} (100%)`;
        }
        completed++;
      } else {
        if (progressBar) {
          progressBar.classList.remove('bg-info');
          progressBar.classList.add('bg-danger');
          progressBar.classList.remove('progress-bar-animated');
        }
        if (statusText) {
          statusText.textContent = `Failed to upload ${file.name}`;
        }
        failed++;
      }
      // Update summary status
      groupUploadStatusSpan.textContent = `Uploaded ${completed}/${files.length}${failed ? `, Failed: ${failed}` : ''}`;
      if (completed + failed === files.length) {
        groupFileInput.value = '';
        groupDocsCurrentPage = 1;
        fetchGroupDocuments();
        groupUploadBtn.disabled = false;
        groupUploadBtn.innerHTML = "Upload Document(s)";
        // Clear upload progress bars after all uploads and table refresh
        if (progressContainer) progressContainer.innerHTML = '';
      }
    };

    xhr.onerror = function () {
      if (progressBar) {
        progressBar.classList.remove('bg-info');
        progressBar.classList.add('bg-danger');
        progressBar.classList.remove('progress-bar-animated');
      }
      if (statusText) {
        statusText.textContent = `Failed to upload ${file.name}`;
      }
      failed++;
      groupUploadStatusSpan.textContent = `Uploaded ${completed}/${files.length}${failed ? `, Failed: ${failed}` : ''}`;
      if (completed + failed === files.length) {
        groupFileInput.value = '';
        groupDocsCurrentPage = 1;
        fetchGroupDocuments();
        groupUploadBtn.disabled = false;
        groupUploadBtn.innerHTML = "Upload Document(s)";
        if (progressContainer) progressContainer.innerHTML = '';
      }
    };

    xhr.send(formData);
  });
}
