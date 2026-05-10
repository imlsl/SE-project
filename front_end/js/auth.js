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

    login(username, password) {
        const users = this.getUsers();
        const user = users.find(u => u.username === username && u.password === password);
        
        if (user) {
            const sessionUser = { username: user.username, role: user.role };
            localStorage.setItem(this.currentUserKey, JSON.stringify(sessionUser));
            return { success: true, user: sessionUser };
        }
        return { success: false, message: '用户名或密码错误' };
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