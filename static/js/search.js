// search.js
(function() {
    const { Toast, Auth, API } = window.Services;

    class ImageSearch {
        constructor() {
            this.currentSearchFile = null;
            this.currentPage = 1;
            this.perPage = 12;
            this.setupSearchUI();
            this.setupEventListeners();
        }

        setupSearchUI() {
            // Cache DOM elements
            this.elements = {
                searchTabs: document.querySelector('.search-tabs'),
                textSearchPanel: document.getElementById('text-search'),
                imageSearchPanel: document.getElementById('image-search'),
                textSearchInput: document.querySelector('#text-search .search-input'),
                textSearchBtn: document.querySelector('#text-search .btn-primary'),
                uploadZone: document.querySelector('.upload-zone'),
                fileInput: document.querySelector('.file-input'),
                imageSearchBtn: document.querySelector('#image-search .btn-primary'),
                resultsGrid: document.querySelector('.results-grid'),
                resultCount: document.querySelector('.result-count'),
                sortSelect: document.querySelector('.sort-select'),
                pagination: document.querySelector('.pagination')
            };
        }

        setupEventListeners() {
            // Tab switching
            if (this.elements.searchTabs) {
                this.elements.searchTabs.addEventListener('click', (e) => {
                    const tabBtn = e.target.closest('.tab-btn');
                    if (tabBtn) {
                        this.switchTab(tabBtn.dataset.tab);
                    }
                });
            }

            // Text search
            if (this.elements.textSearchBtn) {
                this.elements.textSearchBtn.addEventListener('click', () => {
                    this.handleTextSearch();
                });

                // Enter key handling
                this.elements.textSearchInput?.addEventListener('keypress', (e) => {
                    if (e.key === 'Enter') {
                        this.handleTextSearch();
                    }
                });
            }
            if (this.elements.fileInput) {
                this.elements.fileInput.addEventListener('change', (e) => {
                    if (e.target.files.length) {
                        this.currentSearchFile = e.target.files[0];
                        this.handleImageUpload(this.currentSearchFile);
                    }
                });
            }
    
            // Image upload and search
            if (this.elements.uploadZone) {
                this.elements.uploadZone.addEventListener('drop', (e) => {
                    e.preventDefault();
                    this.elements.uploadZone.classList.remove('drag-over');
                    if (e.dataTransfer.files.length) {
                        this.currentSearchFile = e.dataTransfer.files[0];
                        this.handleImageUpload(this.currentSearchFile);
                    }
                });
                this.elements.uploadZone.addEventListener('click', () => {
                    this.elements.fileInput?.click();
                });

                this.elements.fileInput?.addEventListener('change', (e) => {
                    if (e.target.files.length) {
                        this.handleImageUpload(e.target.files[0]);
                    }
                });

                // Drag and drop
                this.elements.uploadZone.addEventListener('dragover', (e) => {
                    e.preventDefault();
                    this.elements.uploadZone.classList.add('drag-over');
                });

                this.elements.uploadZone.addEventListener('dragleave', () => {
                    this.elements.uploadZone.classList.remove('drag-over');
                });

                this.elements.uploadZone.addEventListener('drop', (e) => {
                    e.preventDefault();
                    this.elements.uploadZone.classList.remove('drag-over');
                    if (e.dataTransfer.files.length) {
                        this.handleImageUpload(e.dataTransfer.files[0]);
                    }
                });
            }

            // Sorting
            if (this.elements.sortSelect) {
                this.elements.sortSelect.addEventListener('change', () => {
                    this.handleSort();
                });
            }
        }
        
        switchTab(tabId) {
            const tabs = document.querySelectorAll('.tab-btn');
            const panels = document.querySelectorAll('.search-panel');

            tabs.forEach(tab => {
                tab.classList.toggle('active', tab.dataset.tab === tabId);
            });

            panels.forEach(panel => {
                panel.classList.toggle('active', panel.id === `${tabId}-search`);
            });
        }

        async handleTextSearch(page = 1) {
            const query = this.elements.textSearchInput?.value.trim();
            if (!query) {
                Toast.show('Please enter an image description to search', 'error');
                return;
            }
            
            this.showLoading(true);
            try {
                const response = await API.request(`/api/search/text?page=${page}&per_page=12`, {
                    method: 'POST',
                    body: JSON.stringify({ query })
                });
        
                if (!response.ok) throw new Error('Search failed');
        
                const data = await response.json();
                this.renderResults(data.results);
                
                // Hiển thị và cập nhật phân trang nếu có kết quả
                if (data.results.length > 0) {
                    this.updatePagination(data.pagination);
                } else {
                    // Ẩn phân trang nếu không có kết quả
                    if (this.elements.pagination) {
                        this.elements.pagination.style.display = 'none';
                    }
                }
                
                this.updateResultCount(data.pagination.total);
        
            } catch (error) {
                Toast.show(error.message, 'error');
            } finally {
                this.showLoading(false);
            }
        }
        
        updatePagination(pagination,searchFile = null) {
            if (!this.elements.pagination) return;
        
            const { total, pages, current_page } = pagination;
            if (total <= 1) {
                this.elements.pagination.style.display = 'none';
                return;
            }
        
            const getPageNumbers = () => {
                const numbers = [];
                const maxVisible = 5;
                const half = Math.floor(maxVisible / 2);
        
                let start = Math.max(1, current_page - half);
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
            this.elements.pagination.innerHTML = `
                <button class="btn" ${current_page === 1 ? 'disabled' : ''}>Previous</button>
                <div class="page-numbers">
                    ${pageNumbers.map(num => 
                        num === '...' 
                            ? '<span>...</span>'
                            : `<button class="page-btn ${num === current_page ? 'active' : ''}" 
                                      data-page="${num}">${num}</button>`
                    ).join('')}
                </div>
                <button class="btn" ${current_page === pages ? 'disabled' : ''}>Next</button>
            `;
        
            // Add pagination click handlers
            const prevBtn = this.elements.pagination.querySelector('button:first-child');
            const nextBtn = this.elements.pagination.querySelector('button:last-child');
            
            prevBtn?.addEventListener('click', () => {
                if (current_page > 1) {
                    if (searchFile) {
                        this.handleImageUpload(searchFile, current_page - 1);
                    } else {
                        this.handleTextSearch(current_page - 1);
                    }
                }
            });
    
            nextBtn?.addEventListener('click', () => {
                if (current_page < pages) {
                    if (searchFile) {
                        this.handleImageUpload(searchFile, current_page + 1);
                    } else {
                        this.handleTextSearch(current_page + 1);
                    }
                }
            });
    
            this.elements.pagination.querySelectorAll('.page-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    const pageNum = parseInt(btn.dataset.page);
                    if (pageNum !== current_page) {
                        if (searchFile) {
                            this.handleImageUpload(searchFile, pageNum);
                        } else {
                            this.handleTextSearch(pageNum);
                        }
                    }
                });
            });
            this.elements.pagination.style.display = 'flex';
        }

        async handleImageUpload(file, page = 1) {
            if (!file || !file.type.startsWith('image/')) {
                Toast.show('Please select a valid image file', 'error');
                return;
            }
    
            this.showLoading(true);
            try {
                const formData = new FormData();
                formData.append('file', file);
    
                const response = await API.request(`/api/search/image?page=${page}&per_page=12`, {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'Authorization': `Bearer ${Auth.getToken()}`
                    }
                });
    
                if (!response.ok) throw new Error('Image search failed');
    
                const data = await response.json();
                this.renderResults(data.results);
    
                // Hiển thị và cập nhật phân trang nếu có kết quả
                if (data.results.length > 0) {
                    this.updatePagination(data.pagination, file); // Truyền file để tái sử dụng cho phân trang
                } else {
                    if (this.elements.pagination) {
                        this.elements.pagination.style.display = 'none';
                    }
                }
    
                this.updateResultCount(data.pagination.total);
    
            } catch (error) {
                Toast.show(error.message, 'error');
            } finally {
                this.showLoading(false);
            }
        }

        handleSort() {
            // Re-run the current search with new sort
            if (this.elements.textSearchInput?.value) {
                this.handleTextSearch();
            }
        }

        renderResults(results) {
            if (!this.elements.resultsGrid) return;

            if (!results.length) {
                this.elements.resultsGrid.innerHTML = `
                    <div class="no-results">
                        <p>No results found</p>
                    </div>
                `;
                return;
            }

            this.elements.resultsGrid.innerHTML = results.map(result => `
                <div class="result-card">
                    <img src="/api/images/file/${encodeURIComponent(result.file_path)}" 
                         alt="${result.title}" 
                         class="result-image"
                         onerror="this.src='/api/placeholder/250/200'">
                    <div class="result-info">
                        <div class="result-title">${result.title}</div>
                        <div class="result-meta">
                            <span class="result-description">${result.description || ''}</span>
                            <span class="similarity">
                                ${Math.round(result.similarity_score * 100)}% match
                            </span>
                        </div>
                    </div>
                </div>
            `).join('');
        }

        updateResultCount(total) {
            if (this.elements.resultCount) {
                this.elements.resultCount.textContent = `${total} result${total !== 1 ? 's' : ''} found`;
            }
        }

        showLoading(show) {
            const loader = document.querySelector('.loading-overlay');
            if (loader) {
                loader.style.display = show ? 'flex' : 'none';
            }
        }
    }

    // Initialize when DOM is ready
    document.addEventListener('DOMContentLoaded', () => {
        // Check if we're on the search page
        if (document.querySelector('.search-controls')) {
            new ImageSearch();
        }
    });
})();