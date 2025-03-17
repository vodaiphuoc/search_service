// auth.js
(function() {
    const { Toast, Auth, API } = window.Services;

    // Form Validators
    const Validators = {
        username: value => value.length >= 3 && value.length <= 20,
        email: value => /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(value),
        password: value => /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$/.test(value)
    };

    // Auth Form Handlers
    async function handleLogin(event) {
        event.preventDefault();
        
        const username = document.getElementById('loginUsername').value;
        const password = document.getElementById('loginPassword').value;

        try {
            const response = await API.request(`${API.endpoints.AUTH}/login`, {
                method: 'POST',
                body: JSON.stringify({ username, password })
            });

            const data = await response.json();

            if (!response.ok) throw new Error(data.message);

            Auth.setTokens(data.access_token, data.refresh_token);
            Toast.show('Login successful! Redirecting...', 'success');
            setTimeout(() => window.location.href = '/', 1000);

        } catch (error) {
            Toast.show(error.message, 'error');
        }
    }

    async function handleRegister(event) {
        event.preventDefault();

        const username = document.getElementById('registerUsername').value;
        const email = document.getElementById('registerEmail').value;
        const password = document.getElementById('registerPassword').value;
        const confirmPassword = document.getElementById('confirmPassword').value;

        // Validate inputs
        if (!Validators.username(username)) {
            return Toast.show('Username must be 3-20 characters long', 'error');
        }
        if (!Validators.email(email)) {
            return Toast.show('Invalid email format', 'error');
        }
        if (!Validators.password(password)) {
            return Toast.show('Password does not meet requirements', 'error');
        }
        if (password !== confirmPassword) {
            return Toast.show('Passwords do not match', 'error');
        }

        try {
            const response = await API.request(`${API.endpoints.AUTH}/register`, {
                method: 'POST',
                body: JSON.stringify({ username, email, password })
            });

            const data = await response.json();
            if (!response.ok) throw new Error(data.message);

            Toast.show('Registration successful! Please verify your email.', 'success');
            setTimeout(() => {
                document.getElementById('showLogin')?.click();
            }, 2000);

        } catch (error) {
            Toast.show(error.message, 'error');
        }
    }
    async function handleLogout() {
        try {
            const { Toast, Auth } = window.Services;
            
            // Call API logout
            const response = await fetch('/api/auth/logout', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${Auth.getToken()}`
                }
            });
    
            // Clear tokens trước
            Auth.clearTokens();
            
            // Redirect về login ngay lập tức
            window.location.href = '/login';
            
            // Show toast sau khi đã redirect
            Toast.show('Logged out successfully', 'success');
    
        } catch (error) {
            console.error('Logout error:', error);
            // Nếu có lỗi vẫn clear token và redirect
            Auth.clearTokens();
            window.location.href = '/login';
        }
    }
    // Form UI Handlers
    function setupFormSwitching() {
        const elements = {
            showRegister: document.getElementById('showRegister'),
            showLogin: document.getElementById('showLogin'),
            loginForm: document.querySelector('.login-side'),
            registerForm: document.querySelector('.register-side')
        };

        function switchForm(hide, show) {
            hide.classList.remove('slide-up');
            hide.classList.add('slide-out');
            
            setTimeout(() => {
                hide.style.display = 'none';
                show.style.display = 'flex';
                show.classList.remove('slide-out');
                show.classList.add('slide-up');
            }, 200);
        }

        if (elements.showRegister && elements.loginForm && elements.registerForm) {
            elements.showRegister.addEventListener('click', (e) => {
                e.preventDefault();
                switchForm(elements.loginForm, elements.registerForm);
            });
        }

        if (elements.showLogin && elements.loginForm && elements.registerForm) {
            elements.showLogin.addEventListener('click', (e) => {
                e.preventDefault();
                switchForm(elements.registerForm, elements.loginForm);
            });
        }
    }

    // Initialize Auth Features
    function init() {
        const loginForm = document.getElementById('loginForm');
        const registerForm = document.getElementById('registerForm');
        const logoutBtn = document.getElementById('logoutBtn');

        if (loginForm) loginForm.addEventListener('submit', handleLogin);
        if (registerForm) registerForm.addEventListener('submit', handleRegister);
        if (logoutBtn) logoutBtn.addEventListener('click', handleLogout);

        setupFormSwitching();

        // Check auth status periodically
        setInterval(async () => {
            if (window.location.pathname !== '/login') {
                const isAuthed = await Auth.checkAuth();
                if (!isAuthed) window.location.href = '/login';
            }
        }, 60000);
    }

    // Initialize when DOM is ready
    document.addEventListener('DOMContentLoaded', init);
})();