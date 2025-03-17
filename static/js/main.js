// main.js
(function() {
    const { Toast, Auth, API,Preview } = window.Services;
    let currentPage = 1;
    const PER_PAGE = 10;

    class ImageGallery {
        constructor() {
            this.preview = Preview;
            this.setupModal();
            this.setupEventListeners();
            this.setupUploader();
            this.setupSelectionControls(); 
            this.loadImages();
            this.selectedImages = new Set();
        }

        setupModal() {
            this.modal = {
                container: document.getElementById('imagePreviewModal'),
                image: document.getElementById('modalImage'),
                title: document.getElementById('modalTitle'),
                date: document.getElementById('modalDate'),
                close: document.querySelector('.close-modal')
            };

            if (this.modal.close) {
                this.modal.close.onclick = () => this.hideModal();
            }

            window.onclick = (e) => {
                if (e.target === this.modal.container) {
                    this.hideModal();
                }
            };
        }

        setupEventListeners() {
            document.addEventListener('click', (e) => {
                const deleteBtn = e.target.closest('.delete-btn');
                const previewImg = e.target.closest('.image-preview');
    
                if (deleteBtn) {
                    e.preventDefault();
                    e.stopPropagation();
                    this.handleDelete(deleteBtn.closest('.image-card'));
                } else if (previewImg) {
                    e.preventDefault();
                    const card = previewImg.closest('.image-card');
                    this.handlePreview(card);
                }
            });
        }
        setupUploader() {
            const uploadSection = document.querySelector('.upload-section');
            if (!uploadSection) return;

            const fileInput = document.createElement('input');
            fileInput.type = 'file';
            fileInput.multiple = true;
            fileInput.accept = 'image/*';
            fileInput.style.display = 'none';
            uploadSection.appendChild(fileInput);

            uploadSection.addEventListener('click', () => fileInput.click());
            fileInput.addEventListener('change', (e) => this.handleFileSelect(e));

            // Drag and drop
            uploadSection.addEventListener('dragover', (e) => {
                e.preventDefault();
                uploadSection.classList.add('drag-over');
            });

            uploadSection.addEventListener('dragleave', () => {
                uploadSection.classList.remove('drag-over');
            });

            uploadSection.addEventListener('drop', (e) => {
                e.preventDefault();
                uploadSection.classList.remove('drag-over');
                const files = Array.from(e.dataTransfer.files).filter(file => 
                    file.type.startsWith('image/'));
                if (files.length) this.uploadFiles(files);
            });
        }

        // showModal(src, title, date) {
        //     if (!this.modal.container) return;
            
        //     this.modal.image.src = src;
        //     this.modal.title.textContent = title;
        //     this.modal.date.textContent = `Uploaded: ${date}`;
        //     this.modal.container.style.display = 'block';
        // }

        // hideModal() {
        //     if (this.modal.container) {
        //         this.modal.container.style.display = 'none';
        //     }
        // }

        async handleDelete(card) {
            if (!card || !confirm('Are you sure you want to delete this image?')) return;
            
            const imageId = card.dataset.id;
            if (!imageId) return;

            try {
                const response = await API.request(`${API.endpoints.IMAGES}/${imageId}`, {
                    method: 'DELETE'
                });

                if (!response.ok) throw new Error('Failed to delete image');

                // Animate and remove card
                card.style.opacity = '0';
                card.style.transform = 'scale(0.9)';
                setTimeout(() => card.remove(), 300);

                Toast.show('Image deleted successfully', 'success');

                // Reload if page is empty
                const remainingCards = document.querySelectorAll('.image-card');
                if (remainingCards.length <= 1) {
                    await this.loadImages(Math.max(1, currentPage - 1));
                }

            } catch (error) {
                Toast.show(error.message, 'error');
            }
        }

        handlePreview(card) {
            if (!card) return;
            
            const img = card.querySelector('.image-preview');
            const title = card.querySelector('.image-title')?.textContent || '';
            const meta = card.querySelector('.image-meta')?.textContent || '';
            
            this.preview.show(img.src, title, this.preview.formatDate(meta));
        }    

        async handleFileSelect(e) {
            const files = Array.from(e.target.files);
            await this.uploadFiles(files);
            e.target.value = ''; // Reset input
        }

        async uploadFiles(files) {
            this.showLoading(true);
            let successCount = 0;

            try {
                for (const file of files) {
                    const formData = new FormData();
                    formData.append('file', file);
                    formData.append('title', file.name);

                    const response = await API.request(`${API.endpoints.IMAGES}/`, {
                        method: 'POST',
                        headers: {
                            // Don't set Content-Type here, let browser set it with boundary
                            'Authorization': `Bearer ${Auth.getToken()}`
                        },
                        body: formData
                    });

                    if (response.ok) successCount++;
                }

                if (successCount > 0) {
                    Toast.show(`Successfully uploaded ${successCount} image${successCount > 1 ? 's' : ''}`, 'success');
                    await this.loadImages(1); // Reload first page
                }
                
                if (successCount < files.length) {
                    Toast.show(`Failed to upload ${files.length - successCount} image${files.length - successCount > 1 ? 's' : ''}`, 'error');
                }

            } catch (error) {
                Toast.show('Upload failed. Please try again.', 'error');
            } finally {
                this.showLoading(false);
            }
        }

        async loadImages(page = 1) {
            this.showLoading(true);
            try {
                const response = await API.request(
                    `${API.endpoints.IMAGES}?page=${page}&per_page=${PER_PAGE}`
                );
        
                if (!response.ok) throw new Error('Failed to load images');
        
                const data = await response.json();
                
                // Render gallery TRƯỚC KHI update pagination
                this.renderGallery(data.images);
                
                // Cập nhật UI phân trang với dữ liệu mới
                this.updatePagination(data.pagination);
                
                // Lưu trang hiện tại
                currentPage = page;
                
                // Scroll lên đầu gallery sau khi load trang mới
                document.querySelector('.gallery')?.scrollIntoView({ behavior: 'smooth' });
        
            } catch (error) {
                Toast.show('Failed to load images', 'error');
            } finally {
                this.showLoading(false);
            }
        }
        setupSelectionControls() {
            // Setup Select All button
            const selectAllBtn = document.querySelector('.action-buttons .btn:not(.btn-danger)');
            if (selectAllBtn) {
                selectAllBtn.addEventListener('click', () => this.handleSelectAll());
            }
    
            // Setup Delete Selected button
            const deleteSelectedBtn = document.querySelector('.action-buttons .btn-danger');
            if (deleteSelectedBtn) {
                deleteSelectedBtn.addEventListener('click', () => this.handleDeleteSelected());
            }
    
            // Setup individual checkbox listeners
            document.addEventListener('change', (e) => {
                const checkbox = e.target.closest('.select-checkbox');
                if (checkbox) {
                    const card = checkbox.closest('.image-card');
                    if (card) {
                        this.handleImageSelection(card, checkbox.checked);
                    }
                }
            });
        }
    
        handleSelectAll() {
            const allCheckboxes = document.querySelectorAll('.select-checkbox');
            const allSelected = Array.from(allCheckboxes).every(cb => cb.checked);
            
            allCheckboxes.forEach(checkbox => {
                checkbox.checked = !allSelected;
                const card = checkbox.closest('.image-card');
                if (card) {
                    this.handleImageSelection(card, !allSelected);
                }
            });
    
            // Update button text
            const selectAllBtn = document.querySelector('.action-buttons .btn:not(.btn-danger)');
            if (selectAllBtn) {
                selectAllBtn.textContent = !allSelected ? 'Deselect All' : 'Select All';
            }
        }
    
        handleImageSelection(card, isSelected) {
            const imageId = card.dataset.id;
            if (isSelected) {
                this.selectedImages.add(imageId);
                card.classList.add('selected');
            } else {
                this.selectedImages.delete(imageId);
                card.classList.remove('selected');
            }
    
            // Update Delete Selected button state
            const deleteSelectedBtn = document.querySelector('.action-buttons .btn-danger');
            if (deleteSelectedBtn) {
                deleteSelectedBtn.disabled = this.selectedImages.size === 0;
            }
    
            // Update Select All button text
            const selectAllBtn = document.querySelector('.action-buttons .btn:not(.btn-danger)');
            const allCheckboxes = document.querySelectorAll('.select-checkbox');
            const allSelected = Array.from(allCheckboxes).every(cb => cb.checked);
            if (selectAllBtn) {
                selectAllBtn.textContent = allSelected ? 'Deselect All' : 'Select All';
            }
        }
    
        async handleDeleteSelected() {
            if (this.selectedImages.size === 0) return;
    
            if (!confirm(`Are you sure you want to delete ${this.selectedImages.size} selected images?`)) {
                return;
            }
    
            const { Toast, API } = window.Services;
            let deletedCount = 0;
            let errorCount = 0;
    
            try {
                for (const imageId of this.selectedImages) {
                    try {
                        const response = await API.request(`${API.endpoints.IMAGES}/${imageId}`, {
                            method: 'DELETE'
                        });
    
                        if (response.ok) {
                            const card = document.querySelector(`.image-card[data-id="${imageId}"]`);
                            if (card) {
                                card.style.opacity = '0';
                                card.style.transform = 'scale(0.9)';
                                setTimeout(() => card.remove(), 300);
                            }
                            deletedCount++;
                        } else {
                            errorCount++;
                        }
                    } catch (error) {
                        console.error(`Error deleting image ${imageId}:`, error);
                        errorCount++;
                    }
                }
    
                // Clear selection after deletion
                this.selectedImages.clear();
                this.updateSelectionUI();
    
                // Show results
                if (deletedCount > 0) {
                    Toast.show(`Successfully deleted ${deletedCount} image${deletedCount !== 1 ? 's' : ''}`, 'success');
                }
                if (errorCount > 0) {
                    Toast.show(`Failed to delete ${errorCount} image${errorCount !== 1 ? 's' : ''}`, 'error');
                }
    
                // Reload if page is empty
                const remainingCards = document.querySelectorAll('.image-card');
                if (remainingCards.length === 0) {
                    await this.loadImages(Math.max(1, currentPage - 1));
                }
    
            } catch (error) {
                Toast.show('Error deleting selected images', 'error');
            }
        }
    
        updateSelectionUI() {
            // Reset all checkboxes
            document.querySelectorAll('.select-checkbox').forEach(checkbox => {
                checkbox.checked = false;
            });
    
            // Reset all card selections
            document.querySelectorAll('.image-card').forEach(card => {
                card.classList.remove('selected');
            });
    
            // Reset buttons
            const deleteSelectedBtn = document.querySelector('.action-buttons .btn-danger');
            if (deleteSelectedBtn) {
                deleteSelectedBtn.disabled = true;
            }
    
            const selectAllBtn = document.querySelector('.action-buttons .btn:not(.btn-danger)');
            if (selectAllBtn) {
                selectAllBtn.textContent = 'Select All';
            }
        }
    
        // Cập nhật method renderGallery để thêm checkbox
        renderGallery(images) {
            const gallery = document.querySelector('.gallery');
            if (!gallery) return;
    
            gallery.innerHTML = images.map(image => `
                <div class="image-card selectable" data-id="${image.image_id}">
                    <div class="image-select">
                        <input type="checkbox" class="select-checkbox">
                    </div>
                    <img src="/api/images/file/${encodeURIComponent(image.file_path)}" 
                         alt="${image.title}" 
                         class="image-preview"
                         onerror="this.src='/api/placeholder/250/200'">
                    <div class="image-info">
                        <div class="image-title">${image.title}</div>
                        <div class="image-meta">
                            Uploaded ${this.formatDate(image.uploaded_at)}
                        </div>
                        <div class="image-actions">
                            <button class="action-btn delete-btn" title="Delete">
                                <svg width="16" height="16" fill="currentColor" viewBox="0 0 24 24">
                                    <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/>
                                </svg>
                            </button>
                        </div>
                    </div>
                </div>
            `).join('');
    
            // Reset selection state after rendering
            this.selectedImages.clear();
            this.updateSelectionUI();
        }

        updatePagination(pagination) {
            const container = document.querySelector('.pagination');
            if (!container) return;

            const { total, pages, current_page: current } = pagination;
            if (total === 0) {
                container.style.display = 'none';
                return;
            }

            const getPageNumbers = () => {
                const numbers = [];
                const maxVisible = 5;
                const half = Math.floor(maxVisible / 2);

                let start = Math.max(1, current - half);
                let end = Math.min(pages, start + maxVisible - 1);

                if (end - start + 1 < maxVisible) {
                    start = Math.max(1, end - maxVisible + 1);
                }

                if (start > 1) numbers.push(1, '...');
                for (let i = start; i <= end; i++) numbers.push(i);
                if (end < pages) numbers.push('...', pages);

                return numbers;
            };

            const pageNumbers = getPageNumbers();
            container.innerHTML = `
                <button class="btn" ${current === 1 ? 'disabled' : ''}>Previous</button>
                <div class="page-numbers">
                    ${pageNumbers.map(num => 
                        num === '...' 
                            ? '<span>...</span>'
                            : `<button class="page-btn ${num === current ? 'active' : ''}" 
                                      data-page="${num}">${num}</button>`
                    ).join('')}
                </div>
                <button class="btn" ${current === pages ? 'disabled' : ''}>Next</button>
            `;
            const prevBtn = container.querySelector('button:first-child');
            if (prevBtn) {
                prevBtn.addEventListener('click', () => {
                    if (current > 1) {
                        this.loadImages(current - 1);
                    }
                });
            }
            container.querySelectorAll('.page-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    const pageNum = parseInt(btn.dataset.page);
                    if (pageNum !== current) {
                        this.loadImages(pageNum);
                    }
                });
            });
            const nextBtn = container.querySelector('button:last-child');
            if (nextBtn) {
                nextBtn.addEventListener('click', () => {
                    if (current < pages) {
                        this.loadImages(current + 1);
                    }
                });
            }
            container.style.display = 'flex';
        }

        showLoading(show) {
            const loader = document.querySelector('.loading-overlay');
            if (loader) {
                loader.style.display = show ? 'flex' : 'none';
            }
        }

        formatDate(dateString) {
            return new Date(dateString).toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric'
            });
        }
    }

    // Initialize when DOM is ready
    document.addEventListener('DOMContentLoaded', () => {
        // Check if we're on a page that needs the gallery
        if (document.querySelector('.gallery')) {
            new ImageGallery();
        }
    });
})();