// js/roles/scene-modeler.js - 最小化版本
class SceneModelerUI extends BaseRoleUI {
    render() {
        if (!this.container) return;
        this.container.innerHTML = `
            <div class="glass-card" style="padding: 2rem; text-align: center;">
                <i class="fas fa-cube" style="font-size: 3rem; color: #38bdf8;"></i>
                <h3>场景建模师工作台</h3>
                <p>功能开发中...</p>
            </div>
        `;
    }
}