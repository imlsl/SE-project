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