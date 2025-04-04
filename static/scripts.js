// Check for existing Cloudinary connection on page load
document.addEventListener('DOMContentLoaded', function() {
    loadFiles();
});

// Upload file to Cloudinary
async function uploadFile() {
    let fileInput = document.getElementById("fileInput");
    let uploadStatus = document.getElementById("uploadStatus");
    
    if (!fileInput.files.length) {
        uploadStatus.innerHTML = '<div class="error">Please select a file first</div>';
        return;
    }
    
    let file = fileInput.files[0];
    let formData = new FormData();
    formData.append("file", file);
    
    // Show loading message
    uploadStatus.innerHTML = '<div>Uploading... Please wait</div>';
    
    try {
        let response = await fetch("/upload", {
            method: "POST",
            body: formData
        });
        
        let result = await response.json();
        
        if (response.ok) {
            uploadStatus.innerHTML = `<div class="success">File "${result.filename}" uploaded successfully!</div>`;
            fileInput.value = ""; // Clear file input
            loadFiles(); // Refresh file list
        } else {
            uploadStatus.innerHTML = `<div class="error">Error: ${result.error || 'Upload failed'}</div>`;
        }
    } catch (error) {
        uploadStatus.innerHTML = `<div class="error">Error: ${error.message}</div>`;
    }
}

// Load files from database for current user
async function loadFiles() {
    let fileGrid = document.getElementById("fileGrid");
    fileGrid.innerHTML = '<div>Loading files...</div>';
    
    try {
        let response = await fetch("/files");
        let files = await response.json();
        
        if (response.ok) {
            if (!files.length) {
                fileGrid.innerHTML = '<div>No files found. Upload some files to get started!</div>';
                return;
            }
            
            fileGrid.innerHTML = '';
            
            files.forEach(file => {
                let isImage = file.resource_type === 'image';
                let fileExtension = file.format || getExtensionFromFilename(file.filename);
                
                let fileCard = document.createElement('div');
                fileCard.className = 'file-card';
                
                // Preview section
                let preview = document.createElement('div');
                preview.className = 'file-preview';
                
                if (isImage) {
                    let img = document.createElement('img');
                    img.src = file.url;
                    img.alt = file.filename;
                    preview.appendChild(img);
                } else {
                    // For non-image files show file type
                    preview.innerHTML = `<div>${fileExtension.toUpperCase()}</div>`;
                }
                
                // File info section
                let fileInfo = document.createElement('div');
                fileInfo.className = 'file-info';
                
                let fileName = document.createElement('div');
                fileName.className = 'file-name';
                fileName.textContent = file.filename;
                
                let fileActions = document.createElement('div');
                fileActions.className = 'file-actions';
                
                // View button
                let viewLink = document.createElement('a');
                viewLink.href = file.url;
                viewLink.target = '_blank';
                viewLink.textContent = 'View';
                viewLink.className = 'view-btn';
                
                // Delete button
                let deleteBtn = document.createElement('button');
                deleteBtn.textContent = 'Delete';
                deleteBtn.className = 'delete-btn';
                deleteBtn.onclick = function() {
                    deleteFile(file.id);
                };
                
                fileActions.appendChild(viewLink);
                fileActions.appendChild(deleteBtn);
                
                fileInfo.appendChild(fileName);
                fileInfo.appendChild(fileActions);
                
                fileCard.appendChild(preview);
                fileCard.appendChild(fileInfo);
                
                fileGrid.appendChild(fileCard);
            });
        } else {
            fileGrid.innerHTML = `<div class="error">Error loading files: ${result.error || 'Unknown error'}</div>`;
        }
    } catch (error) {
        fileGrid.innerHTML = `<div class="error">Error: ${error.message}</div>`;
    }
}

// Delete file from database and Cloudinary
async function deleteFile(fileId) {
    if (!confirm('Are you sure you want to delete this file?')) {
        return;
    }
    
    try {
        let response = await fetch(`/delete/${fileId}`, {
            method: "DELETE"
        });
        
        let result = await response.json();
        
        if (response.ok) {
            loadFiles(); // Refresh file list
        } else {
            alert(`Error deleting file: ${result.error || 'Unknown error'}`);
        }
    } catch (error) {
        alert(`Error: ${error.message}`);
    }
}

// Helper function to get file extension from filename
function getExtensionFromFilename(filename) {
    let parts = filename.split('.');
    return parts.length > 1 ? parts[parts.length - 1] : 'file';
}