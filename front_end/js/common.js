// 通用工具函数

// 根据角色跳转到对应页面
function redirectByRole(role) {
    const rolePageMap = {
        'system_admin': 'admin.html',
        'industry_analyst': 'analyst.html',
        'scene_modeler': 'modeler.html'
    };
    
    const page = rolePageMap[role];
    if (page) {
        window.location.href = page;
    } else {
        console.error('未知角色:', role);
        window.location.href = 'index.html';
    }
}

// 获取当前登录用户
function getCurrentUser() {
    const authManager = new AuthManager();
    return authManager.getCurrentUser();
}

// 检查登录状态并可选校验角色
function requireLogin(options = {}) {
    const authManager = new AuthManager();
    const redirectTo = options.redirectTo || 'index.html';
    const deniedMessage = options.deniedMessage || '权限不足';
    const expectedRole = options.expectedRole;

    if (!authManager.isLoggedIn()) {
        window.location.href = redirectTo;
        return null;
    }

    const currentUser = authManager.getCurrentUser();
    if (expectedRole && currentUser.role !== expectedRole) {
        alert(deniedMessage);
        window.location.href = redirectTo;
        return null;
    }

    return { authManager, currentUser };
}

// 绑定通用页面按钮
function bindShellActions(options = {}) {
    const authManager = options.authManager || new AuthManager();
    const profileBtnId = options.profileBtnId || 'profileBtn';
    const logoutBtnId = options.logoutBtnId || 'logoutBtn';
    const redirectTo = options.redirectTo || 'index.html';

    const profileBtn = document.getElementById(profileBtnId);
    if (profileBtn) {
        profileBtn.addEventListener('click', () => {
            window.location.href = options.profilePage || 'profile.html';
        });
    }

    const logoutBtn = document.getElementById(logoutBtnId);
    if (logoutBtn) {
        logoutBtn.addEventListener('click', () => {
            authManager.logout();
            window.location.href = redirectTo;
        });
    }
}

// 显示提示消息
function showMessage(message, type = 'info') {
    const msgDiv = document.createElement('div');
    msgDiv.className = `toast-message ${type}`;
    msgDiv.textContent = message;
    msgDiv.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: ${type === 'error' ? '#ef4444' : '#10b981'};
        color: white;
        padding: 8px 16px;
        border-radius: 8px;
        font-size: 14px;
        z-index: 1000;
        animation: fadeOut 3s forwards;
    `;
    document.body.appendChild(msgDiv);
    setTimeout(() => msgDiv.remove(), 3000);
}

// 添加动画样式
const style = document.createElement('style');
style.textContent = `
    @keyframes fadeOut {
        0% { opacity: 1; transform: translateX(0); }
        70% { opacity: 1; }
        100% { opacity: 0; transform: translateX(20px); }
    }
`;
document.head.appendChild(style);