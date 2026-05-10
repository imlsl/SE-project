// 仪表盘控制器 - 管理角色切换和面板渲染
class DashboardController {
    constructor(authManager) {
        this.authManager = authManager;
        this.currentRoleUI = null;
        this.roleUIMap = {
            'industry_analyst': IndustryAnalystUI,
            'scene_modeler': SceneModelerUI,
            'system_admin': SystemAdminUI
        };
    }

    showDashboard() {
        const currentUser = this.authManager.getCurrentUser();
        if (!currentUser) return false;

        document.getElementById('authView').style.display = 'none';
        document.getElementById('dashboardView').style.display = 'block';
        
        // 更新顶部信息
        document.getElementById('currentUsernameSpan').textContent = currentUser.username;
        const roleLabel = document.getElementById('currentRoleLabel');
        
        const roleNames = {
            'industry_analyst': '行业分析师',
            'scene_modeler': '场景建模师',
            'system_admin': '系统管理员'
        };
        roleLabel.textContent = roleNames[currentUser.role] || currentUser.role;
        
        // 渲染角色面板
        this.renderRolePanel(currentUser.role, currentUser.username);
        
        return true;
    }

    renderRolePanel(role, username) {
        const containerId = 'roleSpecificPanel';
        const RoleClass = this.roleUIMap[role];
        
        if (!RoleClass) {
            console.error(`未找到角色 ${role} 的UI类`);
            return;
        }
        
        // 销毁旧实例
        if (this.currentRoleUI && this.currentRoleUI.destroy) {
            this.currentRoleUI.destroy();
        }
        
        // 创建新实例并渲染
        this.currentRoleUI = new RoleClass(containerId, username);
        this.currentRoleUI.render();
    }

    hideDashboard() {
        document.getElementById('authView').style.display = 'flex';
        document.getElementById('dashboardView').style.display = 'none';
        
        if (this.currentRoleUI && this.currentRoleUI.destroy) {
            this.currentRoleUI.destroy();
        }
        this.currentRoleUI = null;
    }
}