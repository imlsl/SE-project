// 登录页入口控制器 - 统一登录、注册和角色跳转逻辑
document.addEventListener('DOMContentLoaded', () => {
    const authManager = new AuthManager();

    const loginTabBtn = document.getElementById('loginTabBtn');
    const registerTabBtn = document.getElementById('registerTabBtn');
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');
    const toRegisterBtn = document.getElementById('toRegisterBtn');
    const toLoginBtn = document.getElementById('toLoginBtn');
    const authMessage = document.getElementById('authMessage');

    if (!loginTabBtn || !registerTabBtn || !loginForm || !registerForm || !authMessage) {
        return;
    }

    function showLoginTab() {
        loginForm.style.display = 'block';
        registerForm.style.display = 'none';
        loginTabBtn.classList.add('active');
        registerTabBtn.classList.remove('active');
        authMessage.innerHTML = '';
    }

    function showRegisterTab() {
        loginForm.style.display = 'none';
        registerForm.style.display = 'block';
        registerTabBtn.classList.add('active');
        loginTabBtn.classList.remove('active');
        authMessage.innerHTML = '';
    }

    loginTabBtn.addEventListener('click', showLoginTab);
    registerTabBtn.addEventListener('click', showRegisterTab);

    if (toRegisterBtn) {
        toRegisterBtn.addEventListener('click', showRegisterTab);
    }

    if (toLoginBtn) {
        toLoginBtn.addEventListener('click', showLoginTab);
    }

    document.getElementById('doLoginBtn')?.addEventListener('click', async () => {
        const username = document.getElementById('loginUsername')?.value.trim();
        const password = document.getElementById('loginPassword')?.value;

        if (!username || !password) {
            authMessage.innerHTML = '请输入用户名和密码';
            return;
        }

        const loginBtn = document.getElementById('doLoginBtn');
        const originalText = loginBtn.textContent;
        loginBtn.textContent = '登录中...';
        loginBtn.disabled = true;

        const result = await authManager.login(username, password);

        loginBtn.textContent = originalText;
        loginBtn.disabled = false;

        if (result.success) {
            authMessage.innerHTML = '登录成功，跳转中...';
            authMessage.style.color = '#10b981';
            setTimeout(() => {
                redirectByRole(result.user.role);
            }, 500);
        } else {
            authMessage.innerHTML = `错误：${result.message}`;
            authMessage.style.color = '#f97316';
        }
    });

    document.getElementById('doRegisterBtn')?.addEventListener('click', async () => {
        const username = document.getElementById('regUsername')?.value.trim();
        const password = document.getElementById('regPassword')?.value;
        const role = document.getElementById('regRole')?.value;

        if (!username || !password) {
            authMessage.innerHTML = '错误：请填写完整信息';
            return;
        }

        if (password.length < 6) {
            authMessage.innerHTML = '错误：密码长度至少6位';
            return;
        }

        const registerBtn = document.getElementById('doRegisterBtn');
        const originalText = registerBtn.textContent;
        registerBtn.textContent = '注册中...';
        registerBtn.disabled = true;

        const result = await authManager.register(username, password, role);

        registerBtn.textContent = originalText;
        registerBtn.disabled = false;

        authMessage.innerHTML = result.success ? '注册成功，请登录' : `错误：${result.message}`;
        if (result.success) {
            authMessage.style.color = '#10b981';
            setTimeout(showLoginTab, 1500);
            const regUsername = document.getElementById('regUsername');
            const regPassword = document.getElementById('regPassword');
            if (regUsername) regUsername.value = '';
            if (regPassword) regPassword.value = '';
        } else {
            authMessage.style.color = '#f97316';
        }
    });

    document.getElementById('loginPassword')?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            document.getElementById('doLoginBtn')?.click();
        }
    });

    document.getElementById('regPassword')?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            document.getElementById('doRegisterBtn')?.click();
        }
    });

    showLoginTab();
});