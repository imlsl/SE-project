// 认证模块 - 用户登录/注册逻辑
class AuthManager {
    constructor() {
        this.currentUserKey = 'smartcity_current_user';
        this.baseUrl = 'http://127.0.0.1:8000';
    }

    async login(username, password) {
        try {
            const response = await fetch(`${this.baseUrl}/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });

            if (response.ok) {
                const data = await response.json();
                const sessionUser = { 
                    username: username, 
                    role: data.role, 
                    token: data.token
                };
                localStorage.setItem(this.currentUserKey, JSON.stringify(sessionUser));
                return { success: true, user: sessionUser };
            } else {
                const errorData = await response.json();
                return { success: false, message: errorData.detail || '用户名或密码错误' };
            }
        } catch (error) {
            console.error('Login error:', error);
            return { success: false, message: '无法连接到服务器，请检查后端服务是否启动' };
        }
    }

    async register(username, password, role) {
        try {
            const response = await fetch(`${this.baseUrl}/auth/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password, role })
            });

            if (response.ok) {
                const data = await response.json();
                return { success: true, message: data.message || '注册成功，请登录' };
            } else {
                const errorData = await response.json();
                return { success: false, message: errorData.detail || '注册失败' };
            }
        } catch (error) {
            console.error('Register error:', error);
            return { success: false, message: '无法连接到服务器，请检查后端服务是否启动' };
        }
    }

    getCurrentUser() {
        const userStr = localStorage.getItem(this.currentUserKey);
        return userStr ? JSON.parse(userStr) : null;
    }

    logout() {
        localStorage.removeItem(this.currentUserKey);
    }

    isLoggedIn() {
        return this.getCurrentUser() !== null;
    }

    // 移除 validateToken 方法，不再使用
}