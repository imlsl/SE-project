// 角色基类 - 所有角色UI的抽象基类
class BaseRoleUI {
    constructor(containerId, username) {
        this.container = document.getElementById(containerId);
        this.username = username;
        if (!this.container) {
            console.error(`Container ${containerId} not found`);
        }
    }

    // 渲染角色面板 - 子类必须实现
    render() {
        throw new Error('子类必须实现 render 方法');
    }

    // 清理事件监听 - 可选
    destroy() {
        // 子类可覆盖
    }

    // 显示提示消息
    showMessage(message, type = 'info') {
        const msgDiv = document.createElement('div');
        msgDiv.className = `role-message ${type}`;
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

    // 创建统计卡片
    createStatCard(title, value, icon) {
        return `
            <div class="stat-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="font-size: 0.75rem; color: #94a3b8;">${title}</div>
                        <div style="font-size: 1.5rem; font-weight: 700; margin-top: 0.25rem;">${value}</div>
                    </div>
                    <i class="${icon}" style="font-size: 2rem; color: #38bdf8; opacity: 0.7;"></i>
                </div>
            </div>
        `;
    }
}