// app.js
// 登录页入口控制器 - 统一登录、注册和角色跳转逻辑

// 登录页面控制器（原有逻辑）
function initLoginPage() {
    const loginTabBtn = document.getElementById('loginTabBtn');
    const registerTabBtn = document.getElementById('registerTabBtn');
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');
    const toRegisterBtn = document.getElementById('toRegisterBtn');
    const toLoginBtn = document.getElementById('toLoginBtn');
    const authMessage = document.getElementById('authMessage');

    if (!loginTabBtn || !registerTabBtn || !loginForm || !registerForm || !authMessage) {
        return false;
    }

    const authManager = new AuthManager();

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
    return true;
}

// 首页模态框控制器
function initHomePageModal() {
    const modal = document.getElementById('loginModal');
    const headerLoginBtn = document.getElementById('headerLoginBtn');
    const closeModalBtn = document.getElementById('closeModalBtn');
    const loginTabBtn = document.getElementById('modalLoginTabBtn');
    const registerTabBtn = document.getElementById('modalRegisterTabBtn');
    const doLoginBtn = document.getElementById('modalDoLoginBtn');
    const doRegisterBtn = document.getElementById('modalDoRegisterBtn');
    const loginPassword = document.getElementById('modalLoginPassword');
    const registerPassword = document.getElementById('modalRegPassword');
    
    // 如果页面没有模态框元素，说明不是首页，直接返回
    if (!modal) return false;
    
    const authManager = new AuthManager();

    function openModal() { 
        if (modal) modal.style.display = 'flex'; 
        // 清空表单和消息
        const loginUsername = document.getElementById('modalLoginUsername');
        const loginPwd = document.getElementById('modalLoginPassword');
        const regUsername = document.getElementById('modalRegUsername');
        const regPwd = document.getElementById('modalRegPassword');
        const authMessage = document.getElementById('modalAuthMessage');
        if (loginUsername) loginUsername.value = '';
        if (loginPwd) loginPwd.value = '';
        if (regUsername) regUsername.value = '';
        if (regPwd) regPwd.value = '';
        if (authMessage) authMessage.innerHTML = '';
        // 默认显示登录标签
        showLoginTab();
    }
    
    function closeModal() { 
        if (modal) modal.style.display = 'none'; 
    }

    function showLoginTab() {
        const loginForm = document.getElementById('modalLoginForm');
        const registerForm = document.getElementById('modalRegisterForm');
        const loginTab = document.getElementById('modalLoginTabBtn');
        const registerTab = document.getElementById('modalRegisterTabBtn');
        if (loginForm) loginForm.style.display = 'block';
        if (registerForm) registerForm.style.display = 'none';
        if (loginTab) loginTab.classList.add('active');
        if (registerTab) registerTab.classList.remove('active');
        const authMessage = document.getElementById('modalAuthMessage');
        if (authMessage) authMessage.innerHTML = '';
    }

    function showRegisterTab() {
        const loginForm = document.getElementById('modalLoginForm');
        const registerForm = document.getElementById('modalRegisterForm');
        const loginTab = document.getElementById('modalLoginTabBtn');
        const registerTab = document.getElementById('modalRegisterTabBtn');
        if (loginForm) loginForm.style.display = 'none';
        if (registerForm) registerForm.style.display = 'block';
        if (registerTab) registerTab.classList.add('active');
        if (loginTab) loginTab.classList.remove('active');
        const authMessage = document.getElementById('modalAuthMessage');
        if (authMessage) authMessage.innerHTML = '';
    }

    async function handleLogin() {
        const username = document.getElementById('modalLoginUsername')?.value.trim();
        const password = document.getElementById('modalLoginPassword')?.value;
        const authMessage = document.getElementById('modalAuthMessage');
        const loginBtn = document.getElementById('modalDoLoginBtn');
        
        if (!authMessage) return;
        
        if (!username || !password) { 
            authMessage.innerHTML = '请输入用户名和密码'; 
            authMessage.style.color = '#f97316';
            return; 
        }
        
        // 显示加载状态
        const originalText = loginBtn?.innerHTML || '登录系统';
        if (loginBtn) {
            loginBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 登录中...';
            loginBtn.disabled = true;
        }
        
        try {
            const result = await authManager.login(username, password);
            console.log('登录结果:', result); // 调试日志
            if (result.success) {
                authMessage.innerHTML = '登录成功，跳转中...';
                authMessage.style.color = '#10b981';
                setTimeout(() => { 
                    closeModal(); 
                    redirectByRole(result.user.role); 
                }, 500);
            } else { 
                authMessage.innerHTML = result.message || '用户名或密码错误'; 
                authMessage.style.color = '#f97316'; 
            }
        } catch (error) {
            console.error('登录错误:', error);
            authMessage.innerHTML = '登录失败，请稍后重试'; 
            authMessage.style.color = '#f97316';
        } finally {
            if (loginBtn) {
                loginBtn.innerHTML = originalText;
                loginBtn.disabled = false;
            }
        }
    }

    async function handleRegister() {
        const username = document.getElementById('modalRegUsername')?.value.trim();
        const password = document.getElementById('modalRegPassword')?.value;
        const role = document.getElementById('modalRegRole')?.value;
        const authMessage = document.getElementById('modalAuthMessage');
        const registerBtn = document.getElementById('modalDoRegisterBtn');
        
        if (!authMessage) return;
        
        if (!username || !password) { 
            authMessage.innerHTML = '请填写完整信息'; 
            authMessage.style.color = '#f97316';
            return; 
        }
        
        if (username.length < 3) {
            authMessage.innerHTML = '用户名至少3个字符'; 
            authMessage.style.color = '#f97316';
            return;
        }
        
        if (password.length < 6) {
            authMessage.innerHTML = '密码至少6位'; 
            authMessage.style.color = '#f97316';
            return;
        }
        
        // 显示加载状态
        const originalText = registerBtn?.innerHTML || '注册新账号';
        if (registerBtn) {
            registerBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 注册中...';
            registerBtn.disabled = true;
        }
        
        try {
            const result = await authManager.register(username, password, role);
            console.log('注册结果:', result); // 调试日志
            authMessage.innerHTML = result.message;
            if (result.success) {
                authMessage.style.color = '#10b981';
                setTimeout(() => {
                    showLoginTab();
                    // 清空注册表单
                    const regUsername = document.getElementById('modalRegUsername');
                    const regPassword = document.getElementById('modalRegPassword');
                    if (regUsername) regUsername.value = '';
                    if (regPassword) regPassword.value = '';
                }, 1500);
            } else { 
                authMessage.style.color = '#f97316'; 
            }
        } catch (error) {
            console.error('注册错误:', error);
            authMessage.innerHTML = '注册失败，请稍后重试'; 
            authMessage.style.color = '#f97316';
        } finally {
            if (registerBtn) {
                registerBtn.innerHTML = originalText;
                registerBtn.disabled = false;
            }
        }
    }

    // 添加事件监听
    if (headerLoginBtn) headerLoginBtn.addEventListener('click', openModal);
    if (closeModalBtn) closeModalBtn.addEventListener('click', closeModal);
    if (modal) modal.addEventListener('click', (e) => { if (e.target === modal) closeModal(); });
    if (loginTabBtn) loginTabBtn.addEventListener('click', showLoginTab);
    if (registerTabBtn) registerTabBtn.addEventListener('click', showRegisterTab);
    if (doLoginBtn) doLoginBtn.addEventListener('click', handleLogin);
    if (doRegisterBtn) doRegisterBtn.addEventListener('click', handleRegister);
    if (loginPassword) loginPassword.addEventListener('keypress', (e) => { if (e.key === 'Enter') handleLogin(); });
    if (registerPassword) registerPassword.addEventListener('keypress', (e) => { if (e.key === 'Enter') handleRegister(); });
    
    return true;
}

// DOM 加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    // 先尝试初始化登录页面（如果有 loginForm）
    const isLoginPage = initLoginPage();
    
    // 如果不是登录页面，尝试初始化首页模态框
    if (!isLoginPage) {
        initHomePageModal();
    }
});