// js/roles/industry-analyst.js - 最小化版本
class IndustryAnalystUI extends BaseRoleUI {
    render() {
        if (!this.container) return;
        this.container.innerHTML = `
            <div class="glass-card" style="padding: 2rem; text-align: center;">
                <i class="fas fa-chart-line" style="font-size: 3rem; color: #38bdf8;"></i>
                <h3>行业分析师工作台</h3>
                <p>功能开发中...</p>
            </div>
        `;
    }
}