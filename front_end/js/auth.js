// 认证模块 - 用户登录/注册逻辑
class AuthManager {
    constructor() {
        this.storageKey = 'smartcity_users';
        this.currentUserKey = 'smartcity_current_user';
        this.initUsers();
    }

    initUsers() {
        if (!localStorage.getItem(this.storageKey)) {
            const defaultUsers = [
                { username: 'admin', password: 'admin123', role: 'system_admin' },
                { username: 'analyst', password: '123456', role: 'industry_analyst' },
                { username: 'modeler', password: '123456', role: 'scene_modeler' }
            ];
            localStorage.setItem(this.storageKey, JSON.stringify(defaultUsers));
        }
    }

    getUsers() {
        return JSON.parse(localStorage.getItem(this.storageKey) || '[]');
    }

    saveUsers(users) {
        localStorage.setItem(this.storageKey, JSON.stringify(users));
    }

    async login(username, password) {
        try {
            const response = await fetch('http://127.0.0.1:8000/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });

            if (response.ok) {
                const data = await response.json();
                const sessionUser = { 
                    username: username, 
                    role: data.role, 
                    token: data.token,
                    redirect_url: data.redirect_url
                };
                localStorage.setItem(this.currentUserKey, JSON.stringify(sessionUser));
                return { success: true, user: sessionUser };
            } else {
                const errorData = await response.json();
                return { success: false, message: errorData.detail || '用户名或密码错误' };
            }
        } catch (error) {
            console.error('Login error:', error);
            // 降级使用本地验证（方便没有后端环境时测试）
            const users = this.getUsers();
            const user = users.find(u => u.username === username && u.password === password);
            if (user) {
                const sessionUser = { username: user.username, role: user.role };
                localStorage.setItem(this.currentUserKey, JSON.stringify(sessionUser));
                return { success: true, user: sessionUser };
            }
            return { success: false, message: '无法连接到服务器或用户名密码错误' };
        }
    }

    register(username, password, role) {
        const users = this.getUsers();
        
        if (users.find(u => u.username === username)) {
            return { success: false, message: '用户名已存在' };
        }
        
        if (username.length < 3 || username.length > 20) {
            return { success: false, message: '用户名长度需为3-20个字符' };
        }
        
        if (password.length < 6) {
            return { success: false, message: '密码长度至少6位' };
        }
        
        users.push({ username, password, role });
        this.saveUsers(users);
        return { success: true, message: '注册成功，请登录' };
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
}