// Global variables
let dragCounter = 0;
let isUploading = false;
let currentFolderId = null;
let selectedFileId = null;
let autoBackupEnabled = false;

document.addEventListener('DOMContentLoaded', function() {
    // Set current folder ID from the data attribute
    const folderElement = document.getElementById('current-folder');
    if (folderElement) {
        currentFolderId = folderElement.dataset.folderId;
    }

    // Setup drag and drop for file upload
    setupDragAndDrop();
    
    // Setup key generation
    setupKeyGeneration();
    
    // Setup folder actions
    setupFolderActions();
    
    // Setup file selection
    setupFileSelection();
    
    // Setup QR code functionality
    setupQrCode();
    
    // Setup auto-backup toggle
    setupAutoBackup();
    
    // Setup folder lock status indicator
    updateFolderLockStatus();
});

function setupDragAndDrop() {
    const dropZone = document.getElementById('drop-zone');
    if (!dropZone) return;
    
    // Prevent default behavior for drag events on the entire document
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        document.addEventListener(eventName, preventDefaults, false);
    });
    
    // Handle drag enter/leave effects
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, highlight, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, unhighlight, false);
    });
    
    // Handle drop event
    dropZone.addEventListener('drop', handleDrop, false);
    
    // File input change event
    const fileInput = document.getElementById('file-input');
    if (fileInput) {
        fileInput.addEventListener('change', handleFileSelect, false);
    }
    
    // Click on drop zone to trigger file selector
    dropZone.addEventListener('click', function() {
        if (fileInput) {
            fileInput.click();
        }
    });
}

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

function highlight(e) {
    const dropZone = document.getElementById('drop-zone');
    if (dropZone) {
        dropZone.classList.add('highlight');
    }
}

function unhighlight(e) {
    const dropZone = document.getElementById('drop-zone');
    if (dropZone) {
        dropZone.classList.remove('highlight');
    }
}

function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;
    handleFiles(files);
}

function handleFileSelect(e) {
    const files = e.target.files;
    handleFiles(files);
}

function handleFiles(files) {
    if (files.length === 0) return;
    
    if (!currentFolderId) {
        showAlert('Error: No folder selected for upload.', 'danger');
        return;
    }
    
    if (isUploading) {
        showAlert('A file upload is already in progress. Please wait.', 'warning');
        return;
    }
    
    isUploading = true;
    
    // Create FormData and append files
    const formData = new FormData();
    formData.append('folder_id', currentFolderId);
    
    // Add all files to form data
    for (let i = 0; i < files.length; i++) {
        formData.append('file', files[i]);
    }
    
    // Show upload progress
    const progressContainer = document.getElementById('upload-progress-container');
    const progressBar = document.getElementById('upload-progress-bar');
    const progressText = document.getElementById('upload-progress-text');
    
    if (progressContainer && progressBar && progressText) {
        progressContainer.style.display = 'block';
        progressBar.style.width = '0%';
        progressText.textContent = 'Starting upload...';
    }
    
    // Create XMLHttpRequest to track upload progress
    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/upload', true);
    
    xhr.upload.onprogress = function(e) {
        if (e.lengthComputable) {
            const percentComplete = Math.round((e.loaded / e.total) * 100);
            
            if (progressBar) {
                progressBar.style.width = percentComplete + '%';
                progressBar.setAttribute('aria-valuenow', percentComplete);
            }
            
            if (progressText) {
                progressText.textContent = `Uploading: ${percentComplete}%`;
            }
        }
    };
    
    xhr.onload = function() {
        isUploading = false;
        
        if (xhr.status === 200) {
            if (progressText) {
                progressText.textContent = 'Upload complete!';
            }
            
            // Reload the page to show new files
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            if (progressText) {
                progressText.textContent = 'Upload failed!';
            }
            
            showAlert('File upload failed. Please try again.', 'danger');
        }
    };
    
    xhr.onerror = function() {
        isUploading = false;
        if (progressText) {
            progressText.textContent = 'Upload failed!';
        }
        showAlert('Network error occurred during upload.', 'danger');
    };
    
    // Send the data
    xhr.send(formData);
}

function setupKeyGeneration() {
    const generateKeyBtn = document.getElementById('generate-key-btn');
    const keyInput = document.getElementById('key-input');
    const copyKeyBtn = document.getElementById('copy-key-btn');
    const lockFolderBtn = document.getElementById('lock-folder-btn');
    const unlockFolderBtn = document.getElementById('unlock-folder-btn');
    
    if (generateKeyBtn) {
        generateKeyBtn.addEventListener('click', function() {
            fetch('/generate_key', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({})
            })
            .then(response => response.json())
            .then(data => {
                if (keyInput) {
                    keyInput.value = data.key;
                    showAlert('64-byte key generated successfully. Save it securely - if lost, access to your files will be permanently lost!', 'warning');
                }
            })
            .catch(error => {
                console.error('Error generating key:', error);
                showAlert('Failed to generate key. Please try again.', 'danger');
            });
        });
    }
    
    if (copyKeyBtn && keyInput) {
        copyKeyBtn.addEventListener('click', function() {
            keyInput.select();
            document.execCommand('copy');
            showAlert('Key copied to clipboard!', 'success');
        });
    }
}

function setupFolderActions() {
    // Create folder button
    const createFolderBtn = document.getElementById('create-folder-btn');
    const folderNameInput = document.getElementById('folder-name-input');
    
    if (createFolderBtn && folderNameInput) {
        createFolderBtn.addEventListener('click', function() {
            const folderName = folderNameInput.value.trim();
            if (folderName === '') {
                showAlert('Please enter a folder name.', 'warning');
                return;
            }
            
            // Create a form to submit
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = '/create_folder';
            
            // Add folder name input
            const nameInput = document.createElement('input');
            nameInput.type = 'hidden';
            nameInput.name = 'folder_name';
            nameInput.value = folderName;
            form.appendChild(nameInput);
            
            // Add parent folder ID input
            const parentInput = document.createElement('input');
            parentInput.type = 'hidden';
            parentInput.name = 'parent_id';
            parentInput.value = currentFolderId || '';
            form.appendChild(parentInput);
            
            // Add form to document and submit
            document.body.appendChild(form);
            form.submit();
        });
    }
    
    // Delete folder buttons
    const deleteFolderBtns = document.querySelectorAll('.delete-folder-btn');
    deleteFolderBtns.forEach(btn => {
        btn.addEventListener('click', function(e) {
            if (!confirm('Are you sure you want to delete this folder and all its contents? This action cannot be undone.')) {
                e.preventDefault();
            }
        });
    });
}

function setupFileSelection() {
    // File selection
    const fileItems = document.querySelectorAll('.file-item');
    fileItems.forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Remove selection from all files
            fileItems.forEach(f => f.classList.remove('selected'));
            
            // Add selection to this file
            item.classList.add('selected');
            
            // Get file ID
            selectedFileId = item.dataset.fileId;
            
            // Load file details
            loadFileDetails(selectedFileId);
        });
    });
    
    // Delete file buttons
    const deleteFileBtns = document.querySelectorAll('.delete-file-btn');
    deleteFileBtns.forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.stopPropagation(); // Prevent triggering the file selection
            
            if (!confirm('Are you sure you want to delete this file? This action cannot be undone.')) {
                e.preventDefault();
            }
        });
    });
}

function loadFileDetails(fileId) {
    fetch(`/file_details/${fileId}`)
        .then(response => response.json())
        .then(data => {
            const detailsPanel = document.getElementById('file-details-panel');
            if (!detailsPanel) return;
            
            if (data.error) {
                detailsPanel.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
                return;
            }
            
            // Determine if file is previewable
            const isImage = ['jpg', 'jpeg', 'png', 'gif', 'svg'].includes(data.file_type.toLowerCase());
            const isPdf = data.file_type.toLowerCase() === 'pdf';
            
            let previewHtml = '';
            if (isImage) {
                previewHtml = `
                    <div class="file-preview mb-3">
                        <img src="${data.download_url}" class="img-fluid" alt="${data.name}">
                    </div>
                `;
            } else if (isPdf) {
                previewHtml = `
                    <div class="file-preview mb-3">
                        <iframe src="${data.download_url}" width="100%" height="300" style="border: none;"></iframe>
                    </div>
                `;
            }
            
            // Format file size
            let fileSize = data.size;
            let sizeUnit = 'bytes';
            
            if (fileSize >= 1024 * 1024 * 1024) {
                fileSize = (fileSize / (1024 * 1024 * 1024)).toFixed(2);
                sizeUnit = 'GB';
            } else if (fileSize >= 1024 * 1024) {
                fileSize = (fileSize / (1024 * 1024)).toFixed(2);
                sizeUnit = 'MB';
            } else if (fileSize >= 1024) {
                fileSize = (fileSize / 1024).toFixed(2);
                sizeUnit = 'KB';
            }
            
            // Update details panel
            detailsPanel.innerHTML = `
                ${previewHtml}
                <h4>${data.name}</h4>
                <ul class="list-group mb-3">
                    <li class="list-group-item">
                        <strong>Size:</strong> ${fileSize} ${sizeUnit}
                    </li>
                    <li class="list-group-item">
                        <strong>Type:</strong> ${data.file_type.toUpperCase()}
                    </li>
                    <li class="list-group-item">
                        <strong>Uploaded:</strong> ${data.created_at}
                    </li>
                </ul>
                <div class="d-grid gap-2">
                    <a href="${data.download_url}" class="btn btn-primary">
                        <i class="fas fa-download"></i> Download
                    </a>
                    <form action="/delete_file/${data.id}" method="POST">
                        <button type="submit" class="btn btn-danger w-100 delete-file-btn">
                            <i class="fas fa-trash"></i> Delete
                        </button>
                    </form>
                </div>
            `;
            
            // Re-attach event listener to delete button
            const deleteBtn = detailsPanel.querySelector('.delete-file-btn');
            if (deleteBtn) {
                deleteBtn.addEventListener('click', function(e) {
                    if (!confirm('Are you sure you want to delete this file? This action cannot be undone.')) {
                        e.preventDefault();
                    }
                });
            }
        })
        .catch(error => {
            console.error('Error loading file details:', error);
            const detailsPanel = document.getElementById('file-details-panel');
            if (detailsPanel) {
                detailsPanel.innerHTML = `<div class="alert alert-danger">Error loading file details. Please try again.</div>`;
            }
        });
}

function setupQrCode() {
    const qrCodeContainer = document.getElementById('qr-code-container');
    const qrEnlargeBtn = document.getElementById('qr-enlarge-btn');
    
    if (qrEnlargeBtn && qrCodeContainer) {
        qrEnlargeBtn.addEventListener('click', function() {
            // Extract the QR code image
            const qrImg = qrCodeContainer.querySelector('img');
            
            if (!qrImg) return;
            
            // Create modal with larger QR code
            const modal = document.createElement('div');
            modal.className = 'modal fade';
            modal.id = 'qrModal';
            modal.tabIndex = '-1';
            modal.setAttribute('aria-labelledby', 'qrModalLabel');
            modal.setAttribute('aria-hidden', 'true');
            
            modal.innerHTML = `
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="qrModalLabel">Scan to upload files from mobile</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body text-center">
                            <img src="${qrImg.src}" class="img-fluid" style="max-width: 300px;">
                            <p class="mt-3 text-muted">Scan this QR code with your mobile device to upload files directly to this folder.</p>
                        </div>
                    </div>
                </div>
            `;
            
            document.body.appendChild(modal);
            
            // Show the modal
            const bsModal = new bootstrap.Modal(modal);
            bsModal.show();
            
            // Clean up on modal close
            modal.addEventListener('hidden.bs.modal', function() {
                document.body.removeChild(modal);
            });
        });
    }
}

function setupAutoBackup() {
    const autoBackupToggle = document.getElementById('auto-backup-toggle');
    
    if (autoBackupToggle) {
        autoBackupToggle.addEventListener('change', function() {
            autoBackupEnabled = this.checked;
            
            // Save preference to localStorage
            localStorage.setItem('autoBackupEnabled', autoBackupEnabled);
            
            if (autoBackupEnabled) {
                showAlert('Auto-backup enabled. Files will be automatically uploaded when scanned from mobile.', 'info');
            } else {
                showAlert('Auto-backup disabled. Files will require manual selection on mobile.', 'info');
            }
        });
        
        // Load saved preference
        const savedPreference = localStorage.getItem('autoBackupEnabled');
        if (savedPreference !== null) {
            autoBackupEnabled = savedPreference === 'true';
            autoBackupToggle.checked = autoBackupEnabled;
        }
    }
}

function updateFolderLockStatus() {
    const folderLockStatus = document.getElementById('folder-lock-status');
    const folderLockAlert = document.getElementById('folder-lock-alert');
    
    if (!folderLockStatus) return;
    
    const isLocked = folderLockStatus.dataset.locked === 'True';
    
    if (isLocked) {
        // Folder is locked
        if (folderLockAlert) {
            folderLockAlert.style.display = 'none';
        }
    } else {
        // Folder is unlocked - show warning
        if (folderLockAlert) {
            folderLockAlert.style.display = 'block';
        }
    }
}

function showAlert(message, type = 'info') {
    const alertContainer = document.getElementById('alert-container');
    if (!alertContainer) return;
    
    const alertId = 'alert-' + Math.random().toString(36).substr(2, 9);
    
    const alertHtml = `
        <div id="${alertId}" class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;
    
    alertContainer.innerHTML += alertHtml;
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        const alertElement = document.getElementById(alertId);
        if (alertElement) {
            const bsAlert = new bootstrap.Alert(alertElement);
            bsAlert.close();
        }
    }, 5000);
}
