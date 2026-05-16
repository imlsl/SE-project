// 系统管理员UI
class SystemAdminUI extends BaseRoleUI {
    constructor(containerId, username) {
        super(containerId, username);
        this.users = [];
        this.systemLogs = [];
        this.systemSettings = {
            renderQuality: '均衡',
            backupInterval: '6小时',
            enableAnalytics: true
        };
    }

    async render() {
        if (!this.container) return;
        
        this.showLoading(true);
        await this.loadData();
        
        this.container.innerHTML = `
            <div class="role-panel">
                <div class="glass-card" style="padding: 1.5rem; margin-bottom: 1rem;">
                    <div class="panel-title">
                        <i class="fas fa-shield-alt"></i> 系统管理控制台
                        <span style="font-size: 0.8rem; margin-left: auto; color: #f97316;">管理员: ${this.username}</span>
                    </div>
                    <p style="color: #94a3b8; margin-bottom: 1rem;">用户管理 | 系统监控 | 全局配置</p>
                    
                    <div class="stats-grid" id="statsGrid">
                        ${this.createStatCard('注册用户', this.users.length, 'fas fa-users', '#38bdf8')}
                        ${this.createStatCard('在线用户', this.getOnlineCount(), 'fas fa-user-check', '#10b981')}
                        ${this.createStatCard('系统运行', '24天', 'fas fa-clock', '#a78bfa')}
                        ${this.createStatCard('API调用', '12.4k', 'fas fa-chart-line', '#f59e0b')}
                    </div>
                </div>

                <div class="glass-card" style="padding: 1.5rem; margin-bottom: 1rem;">
                    <div class="panel-title">
                        <i class="fas fa-user-cog"></i> 用户管理
                        <button class="small-btn" id="addUserBtn" style="margin-left: auto;"><i class="fas fa-plus"></i> 添加用户</button>
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
                            <tbody id="userTableBody">
                                ${this.renderUserRows()}
                            </tbody>
                        </table>
                    </div>
                </div>

                <div class="glass-card" style="padding: 1.5rem; margin-bottom: 1rem;">
                    <div class="panel-title">
                        <i class="fas fa-terminal"></i> 系统日志
                        <button class="small-btn outline" id="clearLogsBtn" style="margin-left: auto;">清空日志</button>
                    </div>
                    <div id="logContainer" style="background: #0f172a; border-radius: 0.75rem; padding: 0.75rem; font-family: monospace; font-size: 0.75rem; height: 200px; overflow-y: auto;">
                        ${this.systemLogs.map(log => `<div style="padding: 0.25rem 0; border-bottom: 1px solid #1e293b;">> ${log}</div>`).join('')}
                    </div>
                </div>

                <div class="glass-card" style="padding: 1.5rem;">
                    <div class="panel-title">
                        <i class="fas fa-sliders-h"></i> 系统配置
                    </div>
                    <div style="display: grid; gap: 0.75rem;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span>场景渲染质量</span>
                            <select id="renderQuality" style="background: #1e293b; border: 1px solid #334155; border-radius: 0.5rem; padding: 0.25rem 0.5rem; color: #e2e8f0;">
                                <option ${this.systemSettings.renderQuality === '高性能' ? 'selected' : ''}>高性能</option>
                                <option ${this.systemSettings.renderQuality === '均衡' ? 'selected' : ''}>均衡</option>
                                <option ${this.systemSettings.renderQuality === '高质量' ? 'selected' : ''}>高质量</option>
                            </select>
                        </div>
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span>自动备份间隔</span>
                            <select id="backupInterval" style="background: #1e293b; border: 1px solid #334155; border-radius: 0.5rem; padding: 0.25rem 0.5rem; color: #e2e8f0;">
                                <option ${this.systemSettings.backupInterval === '1小时' ? 'selected' : ''}>1小时</option>
                                <option ${this.systemSettings.backupInterval === '6小时' ? 'selected' : ''}>6小时</option>
                                <option ${this.systemSettings.backupInterval === '24小时' ? 'selected' : ''}>24小时</option>
                            </select>
                        </div>
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span>数据统计分析</span>
                            <label style="display: flex; align-items: center; gap: 0.5rem;">
                                <input type="checkbox" id="enableAnalytics" ${this.systemSettings.enableAnalytics ? 'checked' : ''}>
                                <span style="font-size: 0.8rem;">启用</span>
                            </label>
                        </div>
                        <button class="small-btn" id="saveConfigBtn" style="margin-top: 0.5rem;">保存配置</button>
                    </div>
                </div>
            </div>
        `;
        
        this.bindEvents();
        this.showLoading(false);
    }

    async loadData() {
        // 模拟从后端获取用户数据
        this.users = [
            { username: 'analyst1', role: 'industry_analyst', roleName: '行业分析师', status: 'active', lastLogin: '2024-01-15 09:30' },
            { username: 'modeler1', role: 'scene_modeler', roleName: '场景建模师', status: 'active', lastLogin: '2024-01-14 14:20' },
            { username: 'admin', role: 'system_admin', roleName: '系统管理员', status: 'active', lastLogin: '2024-01-15 08:00' },
            { username: 'analyst2', role: 'industry_analyst', roleName: '行业分析师', status: 'inactive', lastLogin: '2024-01-10 11:15' }
        ];
        
        // 模拟系统日志
        this.systemLogs = [
            '系统启动 - 2024-01-15 08:00:00',
            '用户 analyst1 登录 - 2024-01-15 09:23:45',
            '场景备份完成 - 2024-01-15 10:00:00',
            'API调用次数: 2,345次 - 2024-01-15 12:00:00',
            '用户 modeler1 创建新场景 - 2024-01-15 13:20:00',
            '系统健康检查通过 - 2024-01-15 14:00:00'
        ];
    }

    getOnlineCount() {
        return this.users.filter(u => u.status === 'active').length;
    }

    renderUserRows() {
        const roleNames = {
            'industry_analyst': '行业分析师',
            'scene_modeler': '场景建模师',
            'system_admin': '系统管理员'
        };
        
        return this.users.map(user => `
            <tr style="border-bottom: 1px solid #1e293b;">
                <td style="padding: 0.75rem 0.5rem;">${user.username}</td>
                <td style="padding: 0.75rem 0.5rem;">${roleNames[user.role] || user.role}</td>
                <td style="padding: 0.75rem 0.5rem;">
                    <span style="background: ${user.status === 'active' ? '#10b98120' : '#ef444420'}; padding: 0.25rem 0.5rem; border-radius: 0.5rem; font-size: 0.7rem; color: ${user.status === 'active' ? '#10b981' : '#ef4444'}">
                        ${user.status === 'active' ? '活跃' : '禁用'}
                    </span>
                </td>
                <td style="padding: 0.75rem 0.5rem;">${user.lastLogin}</td>
                <td style="padding: 0.75rem 0.5rem;">
                    <button class="small-btn outline user-edit" data-user="${user.username}" style="margin-right: 0.25rem;">编辑</button>
                    <button class="small-btn outline user-delete" data-user="${user.username}" style="color: #ef4444;">删除</button>
                </td>
            </tr>
        `).join('');
    }

    bindEvents() {
        // 添加用户
        const addUserBtn = document.getElementById('addUserBtn');
        if (addUserBtn) {
            addUserBtn.addEventListener('click', () => this.showAddUserDialog());
        }
        
        // 用户编辑/删除事件
        document.querySelectorAll('.user-edit').forEach(btn => {
            btn.addEventListener('click', () => {
                const username = btn.dataset.user;
                this.showEditUserDialog(username);
            });
        });
        
        document.querySelectorAll('.user-delete').forEach(btn => {
            btn.addEventListener('click', () => {
                const username = btn.dataset.user;
                this.deleteUser(username);
            });
        });
        
        // 清空日志
        const clearLogsBtn = document.getElementById('clearLogsBtn');
        if (clearLogsBtn) {
            clearLogsBtn.addEventListener('click', () => {
                this.systemLogs = [];
                const logContainer = document.getElementById('logContainer');
                if (logContainer) {
                    logContainer.innerHTML = '<div>> 日志已清空</div>';
                }
                this.showMessage('系统日志已清空', 'info');
            });
        }
        
        // 保存配置
        const saveConfigBtn = document.getElementById('saveConfigBtn');
        if (saveConfigBtn) {
            saveConfigBtn.addEventListener('click', () => {
                const renderQuality = document.getElementById('renderQuality').value;
                const backupInterval = document.getElementById('backupInterval').value;
                const enableAnalytics = document.getElementById('enableAnalytics').checked;
                
                this.systemSettings = { renderQuality, backupInterval, enableAnalytics };
                this.showMessage('配置已保存', 'info');
                
                // 添加日志
                this.systemLogs.unshift(`系统配置已更新 - ${new Date().toLocaleString()}`);
                const logContainer = document.getElementById('logContainer');
                if (logContainer && this.systemLogs.length > 0) {
                    logContainer.innerHTML = this.systemLogs.map(log => `<div style="padding: 0.25rem 0; border-bottom: 1px solid #1e293b;">> ${log}</div>`).join('');
                }
            });
        }
    }

    showAddUserDialog() {
        const roleOptions = `
            <option value="industry_analyst">行业分析师</option>
            <option value="scene_modeler">场景建模师</option>
            <option value="system_admin">系统管理员</option>
        `;
        
        const dialogHtml = `
            <div id="userDialog" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); display: flex; justify-content: center; align-items: center; z-index: 10000;">
                <div style="background: #1e293b; border-radius: 1rem; padding: 1.5rem; width: 400px;">
                    <h3 style="margin-bottom: 1rem;">添加用户</h3>
                    <div class="input-group">
                        <label>用户名</label>
                        <input type="text" id="newUsername" style="width: 100%; padding: 0.5rem; border-radius: 0.5rem; background: #0f172a; border: 1px solid #334155; color: #e2e8f0;">
                    </div>
                    <div class="input-group">
                        <label>密码</label>
                        <input type="password" id="newPassword" style="width: 100%; padding: 0.5rem; border-radius: 0.5rem; background: #0f172a; border: 1px solid #334155; color: #e2e8f0;">
                    </div>
                    <div class="input-group">
                        <label>角色</label>
                        <select id="newRole" style="width: 100%; padding: 0.5rem; border-radius: 0.5rem; background: #0f172a; border: 1px solid #334155; color: #e2e8f0;">
                            ${roleOptions}
                        </select>
                    </div>
                    <div style="display: flex; gap: 1rem; margin-top: 1rem;">
                        <button class="btn" id="confirmAddUser">确认添加</button>
                        <button class="btn-outline" id="cancelAddUser">取消</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', dialogHtml);
        
        document.getElementById('confirmAddUser').addEventListener('click', () => {
            const username = document.getElementById('newUsername').value.trim();
            const password = document.getElementById('newPassword').value;
            const role = document.getElementById('newRole').value;
            
            if (!username || !password) {
                this.showMessage('请填写完整信息', 'error');
                return;
            }
            
            if (this.users.find(u => u.username === username)) {
                this.showMessage('用户名已存在', 'error');
                return;
            }
            
            const roleNames = {
                'industry_analyst': '行业分析师',
                'scene_modeler': '场景建模师',
                'system_admin': '系统管理员'
            };
            
            this.users.push({
                username,
                role,
                roleName: roleNames[role],
                status: 'active',
                lastLogin: '从未登录'
            });
            
            const userTableBody = document.getElementById('userTableBody');
            if (userTableBody) {
                userTableBody.innerHTML = this.renderUserRows();
            }
            
            this.showMessage(`用户 ${username} 添加成功`, 'info');
            document.getElementById('userDialog').remove();
            this.bindEvents();
        });
        
        document.getElementById('cancelAddUser').addEventListener('click', () => {
            document.getElementById('userDialog').remove();
        });
    }

    showEditUserDialog(username) {
        const user = this.users.find(u => u.username === username);
        if (!user) return;
        
        const roleOptions = `
            <option value="industry_analyst" ${user.role === 'industry_analyst' ? 'selected' : ''}>行业分析师</option>
            <option value="scene_modeler" ${user.role === 'scene_modeler' ? 'selected' : ''}>场景建模师</option>
            <option value="system_admin" ${user.role === 'system_admin' ? 'selected' : ''}>系统管理员</option>
        `;
        
        const dialogHtml = `
            <div id="userDialog" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); display: flex; justify-content: center; align-items: center; z-index: 10000;">
                <div style="background: #1e293b; border-radius: 1rem; padding: 1.5rem; width: 400px;">
                    <h3 style="margin-bottom: 1rem;">编辑用户: ${username}</h3>
                    <div class="input-group">
                        <label>新密码（留空表示不修改）</label>
                        <input type="password" id="editPassword" style="width: 100%; padding: 0.5rem; border-radius: 0.5rem; background: #0f172a; border: 1px solid #334155; color: #e2e8f0;">
                    </div>
                    <div class="input-group">
                        <label>角色</label>
                        <select id="editRole" style="width: 100%; padding: 0.5rem; border-radius: 0.5rem; background: #0f172a; border: 1px solid #334155; color: #e2e8f0;">
                            ${roleOptions}
                        </select>
                    </div>
                    <div class="input-group">
                        <label>状态</label>
                        <select id="editStatus" style="width: 100%; padding: 0.5rem; border-radius: 0.5rem; background: #0f172a; border: 1px solid #334155; color: #e2e8f0;">
                            <option value="active" ${user.status === 'active' ? 'selected' : ''}>活跃</option>
                            <option value="inactive" ${user.status === 'inactive' ? 'selected' : ''}>禁用</option>
                        </select>
                    </div>
                    <div style="display: flex; gap: 1rem; margin-top: 1rem;">
                        <button class="btn" id="confirmEditUser">保存修改</button>
                        <button class="btn-outline" id="cancelEditUser">取消</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', dialogHtml);
        
        document.getElementById('confirmEditUser').addEventListener('click', () => {
            const newPassword = document.getElementById('editPassword').value;
            const newRole = document.getElementById('editRole').value;
            const newStatus = document.getElementById('editStatus').value;
            
            user.role = newRole;
            user.status = newStatus;
            
            if (newPassword) {
                user.password = newPassword;
            }
            
            const userTableBody = document.getElementById('userTableBody');
            if (userTableBody) {
                userTableBody.innerHTML = this.renderUserRows();
            }
            
            this.showMessage(`用户 ${username} 信息已更新`, 'info');
            document.getElementById('userDialog').remove();
            this.bindEvents();
        });
        
        document.getElementById('cancelEditUser').addEventListener('click', () => {
            document.getElementById('userDialog').remove();
        });
    }

    deleteUser(username) {
        if (username === this.username) {
            this.showMessage('不能删除当前登录的管理员账号', 'error');
            return;
        }
        
        if (confirm(`确定要删除用户 "${username}" 吗？此操作不可恢复。`)) {
            this.users = this.users.filter(u => u.username !== username);
            const userTableBody = document.getElementById('userTableBody');
            if (userTableBody) {
                userTableBody.innerHTML = this.renderUserRows();
            }
            this.showMessage(`用户 ${username} 已删除`, 'info');
            this.bindEvents();
        }
    }
}