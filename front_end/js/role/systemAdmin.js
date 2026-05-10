// 系统管理员UI
class SystemAdminUI extends BaseRoleUI {
    constructor(containerId, username) {
        super(containerId, username);
        this.users = [
            { username: 'analyst1', role: 'industry_analyst', status: 'active', lastLogin: '2024-01-15' },
            { username: 'modeler1', role: 'scene_modeler', status: 'active', lastLogin: '2024-01-14' },
            { username: 'admin', role: 'system_admin', status: 'active', lastLogin: '2024-01-15' }
        ];
        this.systemLogs = [
            '系统启动 - 2024-01-15 08:00:00',
            '用户 analyst1 登录 - 2024-01-15 09:23:45',
            '场景备份完成 - 2024-01-15 10:00:00',
            'API调用次数: 2,345次 - 2024-01-15 12:00:00'
        ];
    }

    render() {
        if (!this.container) return;

        this.container.innerHTML = `
            <div class="role-panel">
                <div class="glass-card" style="padding: 1.5rem; margin-bottom: 1rem;">
                    <div class="panel-title">
                        <i class="fas fa-shield-alt"></i> 系统管理控制台
                        <span style="font-size: 0.8rem; margin-left: auto; color: #f97316;">管理员: ${this.username}</span>
                    </div>
                    <p style="color: #94a3b8; margin-bottom: 1rem;">用户管理 | 系统监控 | 全局配置</p>
                    
                    <div class="stats-grid">
                        ${this.createStatCard('在线用户', 3, 'fas fa-users')}
                        ${this.createStatCard('系统运行', '24天', 'fas fa-clock')}
                        ${this.createStatCard('API调用', '12.4k', 'fas fa-chart-line')}
                        ${this.createStatCard('存储使用', '64%', 'fas fa-hdd')}
                    </div>
                </div>

                <div class="glass-card" style="padding: 1.5rem; margin-bottom: 1rem;">
                    <div class="panel-title">
                        <i class="fas fa-user-cog"></i> 用户管理
                        <button class="small-btn outline" id="addUserBtn" style="margin-left: auto;">+ 添加用户</button>
                    </div>
                    <div style="overflow-x: auto;">
                        <table style="width: 100%; border-collapse: collapse;">
                            <thead>
                                <tr style="border-bottom: 1px solid #334155;">
                                    <th style="text-align: left; padding: 0.5rem;">用户名</th>
                                    <th style="text-align: left; padding: 0.5rem;">角色</th>
                                    <th style="text-align: left; padding: 0.5rem;">状态</th>
                                    <th style="text-align: left; padding: 0.5rem;">最后登录</th>
                                    <th style="text-align: left; padding: 0.5rem;">操作</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${this.users.map(user => `
                                    <tr style="border-bottom: 1px solid #1e293b;">
                                        <td style="padding: 0.75rem 0.5rem;">${user.username}</td>
                                        <td style="padding: 0.75rem 0.5rem;">${user.role}</td>
                                        <td style="padding: 0.75rem 0.5rem;">
                                            <span style="background: ${user.status === 'active' ? '#10b981' : '#ef4444'}20; padding: 0.25rem 0.5rem; border-radius: 0.5rem; font-size: 0.7rem;">${user.status}</span>
                                        </td>
                                        <td style="padding: 0.75rem 0.5rem;">${user.lastLogin}</td>
                                        <td style="padding: 0.75rem 0.5rem;">
                                            <button class="small-btn outline user-edit" data-user="${user.username}" style="margin-right: 0.25rem;">编辑</button>
                                            <button class="small-btn outline user-delete" data-user="${user.username}" style="color: #ef4444;">删除</button>
                                        </td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>

                <div class="glass-card" style="padding: 1.5rem;">
                    <div class="panel-title">
                        <i class="fas fa-terminal"></i> 系统日志
                        <button class="small-btn outline" id="clearLogsBtn" style="margin-left: auto;">清空日志</button>
                    </div>
                    <div style="background: #0f172a; border-radius: 0.75rem; padding: 0.75rem; font-family: monospace; font-size: 0.75rem;">
                        ${this.systemLogs.map(log => `<div style="padding: 0.25rem 0; border-bottom: 1px solid #1e293b;">> ${log}</div>`).join('')}
                    </div>
                </div>

                <div class="glass-card" style="padding: 1.5rem; margin-top: 1rem;">
                    <div class="panel-title">
                        <i class="fas fa-sliders-h"></i> 系统配置
                    </div>
                    <div style="display: grid; gap: 0.75rem;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span>场景渲染质量</span>
                            <select id="renderQuality" style="background: #1e293b; border: 1px solid #334155; border-radius: 0.5rem; padding: 0.25rem 0.5rem; color: #e2e8f0;">
                                <option>高性能</option>
                                <option selected>均衡</option>
                                <option>高质量</option>
                            </select>
                        </div>
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span>自动备份间隔</span>
                            <select id="backupInterval" style="background: #1e293b; border: 1px solid #334155; border-radius: 0.5rem; padding: 0.25rem 0.5rem; color: #e2e8f0;">
                                <option>1小时</option>
                                <option selected>6小时</option>
                                <option>24小时</option>
                            </select>
                        </div>
                        <button class="small-btn" id="saveConfigBtn" style="margin-top: 0.5rem;">保存配置</button>
                    </div>
                </div>
            </div>
        `;

        this.bindEvents();
    }

    bindEvents() {
        const addUserBtn = document.getElementById('addUserBtn');
        if (addUserBtn) {
            addUserBtn.addEventListener('click', () => this.showMessage('添加用户功能', 'info'));
        }

        document.querySelectorAll('.user-edit').forEach(btn => {
            btn.addEventListener('click', () => this.showMessage('编辑用户信息', 'info'));
        });

        document.querySelectorAll('.user-delete').forEach(btn => {
            btn.addEventListener('click', () => this.showMessage('删除用户需要二次确认', 'error'));
        });

        const clearLogsBtn = document.getElementById('clearLogsBtn');
        if (clearLogsBtn) {
            clearLogsBtn.addEventListener('click', () => {
                const logContainer = document.querySelector('.glass-card:last-child .glass-card div');
                if (logContainer) logContainer.innerHTML = '<div>> 日志已清空</div>';
                this.showMessage('系统日志已清空', 'info');
            });
        }

        const saveConfigBtn = document.getElementById('saveConfigBtn');
        if (saveConfigBtn) {
            saveConfigBtn.addEventListener('click', () => this.showMessage('配置已保存', 'info'));
        }
    }
}