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

    // 显示加载状态
    showLoading(show = true) {
        if (show) {
            this.loadingDiv = document.createElement('div');
            this.loadingDiv.className = 'loading-overlay';
            this.loadingDiv.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.5);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 9999;
            `;
            this.loadingDiv.innerHTML = `
                <div style="background: #1e293b; padding: 20px; border-radius: 12px; text-align: center;">
                    <i class="fas fa-spinner fa-pulse" style="font-size: 32px; color: #38bdf8;"></i>
                    <p style="margin-top: 12px; color: #e2e8f0;">加载中...</p>
                </div>
            `;
            document.body.appendChild(this.loadingDiv);
        } else {
            if (this.loadingDiv) {
                this.loadingDiv.remove();
                this.loadingDiv = null;
            }
        }
    }

    // 创建统计卡片
    createStatCard(title, value, icon, color = '#38bdf8') {
        return `
            <div class="stat-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="font-size: 0.75rem; color: #94a3b8;">${title}</div>
                        <div style="font-size: 1.5rem; font-weight: 700; margin-top: 0.25rem;">${value}</div>
                    </div>
                    <i class="${icon}" style="font-size: 2rem; color: ${color}; opacity: 0.7;"></i>
                </div>
            </div>
        `;
    }

    // 发起API请求
    async apiRequest(endpoint, options = {}) {
        const token = localStorage.getItem('smartcity_current_user') ? 
            JSON.parse(localStorage.getItem('smartcity_current_user')).token : null;
        
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };
        
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        
        try {
            const response = await fetch(`http://127.0.0.1:8000${endpoint}`, {
                ...options,
                headers
            });
            
            if (response.status === 401) {
                // Token过期，跳转登录
                window.location.href = 'index.html';
                return null;
            }
            
            return await response.json();
        } catch (error) {
            console.error('API request error:', error);
            this.showMessage('网络错误，请稍后重试', 'error');
            return null;
        }
    }
}