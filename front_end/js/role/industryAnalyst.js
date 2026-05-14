// js/roles/industry-analyst.js - 最小化版本
class IndustryAnalystUI extends BaseRoleUI {
    render() {
        if (!this.container) return;

        this.container.innerHTML = `
            <div class="role-panel">
                <div style="display:flex; gap:1rem; margin-bottom:1rem; align-items:center;">
                    <div style="flex:1; display:flex; gap:0.75rem;">
                        ${this.createStatCard('活跃用户', 124, 'fas fa-users')}
                        ${this.createStatCard('本周新增插件', 3, 'fas fa-puzzle-piece')}
                        ${this.createStatCard('待验收项', 5, 'fas fa-clipboard-list')}
                    </div>
                    <div style="min-width:320px; display:flex; gap:0.5rem; align-items:center;">
                        <select id="ia_filter_industry" style="padding:0.4rem; background:#0f172a; border:1px solid #334155; color:#e2e8f0; border-radius:6px;">
                            <option value="all">所有行业</option>
                            <option value="transport">交通</option>
                            <option value="energy">能源</option>
                            <option value="urban">城市规划</option>
                        </select>
                        <input id="ia_filter_time" type="date" style="padding:0.4rem; background:#0f172a; border:1px solid #334155; color:#e2e8f0; border-radius:6px;">
                        <button class="small-btn" id="ia_apply_filter">应用筛选</button>
                        <button class="small-btn outline" id="ia_export">导出 CSV</button>
                    </div>
                </div>

                <div class="glass-card" style="padding:1rem; margin-bottom:1rem;">
                    <div style="display:flex; gap:1rem; align-items:center;">
                        <div style="flex:1;">
                            <div style="font-size:0.9rem; color:#94a3b8; margin-bottom:0.5rem;">报表概览</div>
                            <svg id="ia_chart" width="100%" height="120" viewBox="0 0 400 120" style="background:#07102a; border-radius:6px; padding:8px;">
                                <!-- 简单静态条形图占位 -->
                                <rect x="30" y="40" width="40" height="60" fill="#38bdf8" />
                                <rect x="90" y="20" width="40" height="80" fill="#a78bfa" />
                                <rect x="150" y="60" width="40" height="40" fill="#f97316" />
                                <text x="30" y="110" fill="#94a3b8" font-size="10">A</text>
                                <text x="90" y="110" fill="#94a3b8" font-size="10">B</text>
                                <text x="150" y="110" fill="#94a3b8" font-size="10">C</text>
                            </svg>
                        </div>
                        <div style="width:320px;">
                            <div style="font-size:0.9rem; color:#94a3b8; margin-bottom:0.5rem;">近期审核任务</div>
                            <ul id="ia_task_list" style="list-style:none; padding-left:0;">
                                <li style="padding:0.5rem 0; border-bottom:1px solid #1e293b;">插件 A - 待验收</li>
                                <li style="padding:0.5rem 0; border-bottom:1px solid #1e293b;">插件 B - 待修复</li>
                                <li style="padding:0.5rem 0; border-bottom:1px solid #1e293b;">插件 C - 待验收</li>
                            </ul>
                        </div>
                    </div>
                </div>

                <div class="glass-card" style="padding:1rem;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
                        <div class="panel-title"><i class="fas fa-table"></i> 数据表</div>
                        <div style="color:#94a3b8; font-size:0.85rem;">示例静态数据</div>
                    </div>
                    <div style="overflow-x:auto;">
                        <table style="width:100%; border-collapse:collapse;">
                            <thead>
                                <tr style="border-bottom:1px solid #334155;">
                                    <th style="text-align:left; padding:0.5rem;">插件名</th>
                                    <th style="text-align:left; padding:0.5rem;">行业</th>
                                    <th style="text-align:left; padding:0.5rem;">状态</th>
                                    <th style="text-align:left; padding:0.5rem;">提交时间</th>
                                </tr>
                            </thead>
                            <tbody id="ia_table_body">
                                <tr style="border-bottom:1px solid #1e293b;"><td style="padding:0.5rem;">插件 A</td><td style="padding:0.5rem;">交通</td><td style="padding:0.5rem;">待验收</td><td style="padding:0.5rem;">2026-04-10</td></tr>
                                <tr style="border-bottom:1px solid #1e293b;"><td style="padding:0.5rem;">插件 B</td><td style="padding:0.5rem;">能源</td><td style="padding:0.5rem;">已发布</td><td style="padding:0.5rem;">2026-03-22</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;

        this.bindEvents();
    }

    bindEvents() {
        const exportBtn = document.getElementById('ia_export');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => {
                const rows = [
                    ['插件名','行业','状态','提交时间'],
                    ['插件 A','交通','待验收','2026-04-10'],
                    ['插件 B','能源','已发布','2026-03-22']
                ];
                const csv = rows.map(r => r.map(c => '"'+String(c).replace(/"/g,'""')+'"').join(',')).join('\n');
                const blob = new Blob([csv], {type:'text/csv;charset=utf-8;'});
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'industry_report.csv';
                document.body.appendChild(a);
                a.click();
                a.remove();
                URL.revokeObjectURL(url);
            });
        }

        const applyFilter = document.getElementById('ia_apply_filter');
        if (applyFilter) {
            applyFilter.addEventListener('click', () => {
                this.showMessage('筛选已应用（示例）', 'info');
                // 演示：不做真实数据过滤，仅用于交互感受
            });
        }
    }
}