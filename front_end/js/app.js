// 主应用程序入口 - 整合所有模块
document.addEventListener('DOMContentLoaded', () => {
    // 初始化认证管理器
    const authManager = new AuthManager();
    
    // 初始化仪表盘控制器
    const dashboardController = new DashboardController(authManager);
    
    // 初始化Blender桥接
    window.blenderBridge = new BlenderBridge();
    window.blenderBridge.init('simulateOutput');
    
    // DOM 元素
    const authView = document.getElementById('authView');
    const dashboardView = document.getElementById('dashboardView');
    
    // 初始显示状态
    if (authManager.isLoggedIn()) {
        authView.style.display = 'none';
        dashboardView.style.display = 'block';
        dashboardController.showDashboard();
    } else {
        authView.style.display = 'flex';
        dashboardView.style.display = 'none';
    }
    
    // 登录/注册标签切换
    const loginTabBtn = document.getElementById('loginTabBtn');
    const registerTabBtn = document.getElementById('registerTabBtn');
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');
    const toRegisterBtn = document.getElementById('toRegisterBtn');
    const toLoginBtn = document.getElementById('toLoginBtn');
    const authMessage = document.getElementById('authMessage');
    
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
    toRegisterBtn.addEventListener('click', showRegisterTab);
    toLoginBtn.addEventListener('click', showLoginTab);
    
    // 登录逻辑
    document.getElementById('doLoginBtn').addEventListener('click', () => {
        const username = document.getElementById('loginUsername').value.trim();
        const password = document.getElementById('loginPassword').value;
        
        if (!username || !password) {
            authMessage.innerHTML = '请输入用户名和密码';
            return;
        }
        
        const result = authManager.login(username, password);
        if (result.success) {
            authMessage.innerHTML = '登录成功，跳转中...';
            setTimeout(() => {
                dashboardController.showDashboard();
            }, 500);
        } else {
            authMessage.innerHTML = `错误：${result.message}`;
        }
    });
    
    // 注册逻辑
    document.getElementById('doRegisterBtn').addEventListener('click', () => {
        const username = document.getElementById('regUsername').value.trim();
        const password = document.getElementById('regPassword').value;
        const role = document.getElementById('regRole').value;
        
        if (!username || !password) {
            authMessage.innerHTML = '错误：请填写完整信息';
            return;
        }
        
        const result = authManager.register(username, password, role);
        authMessage.innerHTML = result.success ? '注册成功，请登录' : `错误：${result.message}`;
        if (result.success) {
            setTimeout(showLoginTab, 1500);
            document.getElementById('regUsername').value = '';
            document.getElementById('regPassword').value = '';
        }
    });
    
    // 退出登录
    document.getElementById('logoutBtn').addEventListener('click', () => {
        authManager.logout();
        dashboardController.hideDashboard();
        authView.style.display = 'flex';
        dashboardView.style.display = 'none';
        // 清空登录表单
        document.getElementById('loginUsername').value = '';
        document.getElementById('loginPassword').value = '';
        authMessage.innerHTML = '';
        showLoginTab();
    });
    

    // Blender 按钮事件
    const enterBlenderBtn = document.getElementById('enterBlenderBtn');
    if (enterBlenderBtn) {
        enterBlenderBtn.addEventListener('click', () => {
            window.blenderBridge.showPanel();
        });
    }
    
    // 模拟按钮
    const simulateAddRoadTex = document.getElementById('simulateAddRoadTex');
    const simulateAdd3DLamp = document.getElementById('simulateAdd3DLamp');
    const simulateTemplate0 = document.getElementById('simulateTemplate0');
    const simulateLLMCommand = document.getElementById('simulateLLMCommand');
    
    if (simulateAddRoadTex) {
        simulateAddRoadTex.addEventListener('click', () => window.blenderBridge.addAsset('texture', '道路纹理'));
    }
    if (simulateAdd3DLamp) {
        simulateAdd3DLamp.addEventListener('click', () => window.blenderBridge.addAsset('model', '3D路灯'));
    }
    if (simulateTemplate0) {
        simulateTemplate0.addEventListener('click', () => window.blenderBridge.applyTemplate('城市基础模板_v0'));
    }
    if (simulateLLMCommand) {
        simulateLLMCommand.addEventListener('click', () => {
            const command = prompt('请输入自然语言指令:', '在十字路口添加智能路灯');
            if (command) window.blenderBridge.processLLMCommand(command);
        });
    }
    
    // 键盘支持 - 回车登录
    const loginPassword = document.getElementById('loginPassword');
    if (loginPassword) {
        loginPassword.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') document.getElementById('doLoginBtn').click();
        });
    }
});