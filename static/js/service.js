// services.js - Shared services across the application
// Toast Service
const ToastService = {
    init() {
        if (!document.getElementById('toast-container')) {
            const container = document.createElement('div');
            container.id = 'toast-container';
            container.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 1000;
                display: flex;
                flex-direction: column;
                gap: 10px;
            `;
            document.body.appendChild(container);
        }
    },

    show(message, type = 'info') {
        this.init();
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.style.cssText = `
            padding: 12px 24px;
            border-radius: 4px;
            background: white;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            color: #333;
            opacity: 0;
            transform: translateY(20px);
            transition: all 0.3s ease;
            ${type === 'error' ? 'background: #fee2e2; color: #dc2626;' : ''}
            ${type === 'success' ? 'background: #dcfce7; color: #16a34a;' : ''}
        `;
        
        toast.textContent = message;
        container.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '1';
            toast.style.transform = 'translateY(0)';
        }, 50);

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(-20px)';
            setTimeout(() => container.removeChild(toast), 300);
        }, 3000);
    }
};

// Auth Service
const AuthService = {
    getToken() {
        return localStorage.getItem('accessToken');
    },

    getRefreshToken() {
        return localStorage.getItem('refreshToken');
    },

    setTokens(accessToken, refreshToken) {
        localStorage.setItem('accessToken', accessToken);
        if (refreshToken) {
            localStorage.setItem('refreshToken', refreshToken);
        }
    },

    clearTokens() {
        localStorage.removeItem('accessToken');
        localStorage.removeItem('refreshToken');
    },

    async refreshToken() {
        try {
            const refreshToken = this.getRefreshToken();
            if (!refreshToken) throw new Error('No refresh token');

            const response = await fetch('/api/auth/refresh-token', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refresh_token: refreshToken })
            });

            if (!response.ok) throw new Error('Token refresh failed');

            const data = await response.json();
            this.setTokens(data.access_token);
            return data.access_token;
        } catch (error) {
            this.clearTokens();
            throw error;
        }
    },

    async checkAuth() {
        const token = this.getToken();
        if (!token) return false;

        try {
            const response = await fetch('/api/auth/protected', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            return response.ok;
        } catch {
            return false;
        }
    }
};

// API Service
const APIService = {
    endpoints: {
        IMAGES: '/api/images',
        AUTH: '/api/auth'
    },

    async request(endpoint, options = {}) {
        const token = AuthService.getToken();
        const defaults = {
            headers: {
                'Authorization': token ? `Bearer ${token}` : '',
                'Content-Type': 'application/json'
            }
        };

        try {
            const response = await fetch(endpoint, { ...defaults, ...options });
            
            if (response.status === 401) {
                await AuthService.refreshToken();
                // Retry request with new token
                options.headers = {
                    ...options.headers,
                    'Authorization': `Bearer ${AuthService.getToken()}`
                };
                return fetch(endpoint, { ...defaults, ...options });
            }

            return response;
        } catch (error) {
            throw error;
        }
    }
};
// Trong services.js thêm PreviewService
const PreviewService = {
    modal: null,

    init() {
        // Kiểm tra và tạo modal nếu chưa có
        if (!document.getElementById('imagePreviewModal')) {
            const modalHTML = `
                <div id="imagePreviewModal" class="modal" style="display: none;">
                    <div class="modal-content">
                        <span class="close-modal">&times;</span>
                        <img id="modalImage" src="" alt="Preview">
                        <div class="modal-info">
                            <h3 id="modalTitle"></h3>
                            <p id="modalDate"></p>
                        </div>
                    </div>
                </div>
            `;
            document.body.insertAdjacentHTML('beforeend', modalHTML);
        }

        this.modal = {
            container: document.getElementById('imagePreviewModal'),
            image: document.getElementById('modalImage'),
            title: document.getElementById('modalTitle'),
            date: document.getElementById('modalDate'),
            close: document.querySelector('.close-modal')
        };

        // Thiết lập event listeners
        if (this.modal.close) {
            this.modal.close.onclick = () => this.hide();
        }

        window.onclick = (e) => {
            if (e.target === this.modal.container) {
                this.hide();
            }
        };
    },

    show(src, title, date) {
        if (!this.modal) {
            this.init();
        }
        
        this.modal.image.src = src;
        this.modal.title.textContent = title || '';
        this.modal.date.textContent = date ? `Uploaded: ${date}` : '';
        this.modal.container.style.display = 'block';
    },

    hide() {
        if (this.modal && this.modal.container) {
            this.modal.container.style.display = 'none';
        }
    },

    formatDate(dateString) {
        return new Date(dateString).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short', 
            day: 'numeric'
        });
    }
};

// Export services
window.Services = {
    Toast: ToastService,
    Auth: AuthService,
    API: APIService,
    Preview: PreviewService
};
// Trong services.js, thêm vào window.Services
window.Services.AuthMiddleware = {
    protectedPaths: ['/', '/dashboard', '/images', '/search'], // các routes cần bảo vệ

    init() {
        // Check ngay khi vào trang
        this.checkAuth();
        
        // Check khi route thay đổi (nếu dùng client-side routing)
        window.addEventListener('popstate', () => this.checkAuth());
    },

    async checkAuth() {
        const currentPath = window.location.pathname;
        
        // Nếu đang ở protected route
        if (this.protectedPaths.includes(currentPath)) {
            // Kiểm tra token
            const token = window.Services.Auth.getToken();
            
            if (!token) {
                window.location.href = '/login';
                return;
            }

            try {
                // Verify token với server
                const response = await fetch('/api/auth/protected', {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });

                if (!response.ok) {
                    // Token invalid hoặc expired
                    window.Services.Auth.clearTokens();
                    window.location.href = '/login';
                }
            } catch (error) {
                console.error('Auth check failed:', error);
                window.Services.Auth.clearTokens();
                window.location.href = '/login';
            }
        }
    }
};

// Initialize middleware when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.Services.AuthMiddleware.init();
});