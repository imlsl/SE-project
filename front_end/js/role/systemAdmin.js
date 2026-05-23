// 系统管理员UI
class SystemAdminUI extends BaseRoleUI {
    constructor(containerId, username) {
        super(containerId, username);
        this.users = [];
        this.systemLogs = [];
        this.systemUptime = {
            uptime_days: 0,
            server_start_time: '',
            current_time: ''
        };
        this.systemSettings = {
            renderQuality: '均衡',
            backupInterval: '6小时',
            enableAnalytics: true
        };
        this.autoRefreshInterval = null;
        this.uptimeRefreshInterval = null;
    }

    async render() {
        if (!this.container) return;
        
        this.showLoading(true);
        await this.loadData();
        await this.loadSystemUptime();
        
        const uptimeDisplay = this.formatUptime(this.systemUptime.uptime_days);
        
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
                        ${this.createStatCard('系统运行', uptimeDisplay, 'fas fa-clock', '#a78bfa')}
                        ${this.createStatCard('API调用', '12.4k', 'fas fa-chart-line', '#f59e0b')}
                    </div>
                    
                    <div style="margin-top: 1rem; padding: 0.75rem; background: rgba(15, 23, 42, 0.5); border-radius: 0.75rem; font-size: 0.75rem;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 0.25rem;">
                            <span style="color: #94a3b8;">服务器启动时间：</span>
                            <span style="color: #e2e8f0;">${this.systemUptime.server_start_time || '加载中...'}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between;">
                            <span style="color: #94a3b8;">当前系统时间：</span>
                            <span style="color: #e2e8f0;" id="currentTime">${this.systemUptime.current_time || '加载中...'}</span>
                        </div>
                    </div>
                </div>

                <div class="glass-card" style="padding: 1.5rem; margin-bottom: 1rem;">
                    <div class="panel-title">
                        <i class="fas fa-user-cog"></i> 用户管理
                        <button class="small-btn" id="addUserBtn" style="margin-left: auto;"><i class="fas fa-plus"></i> 添加用户</button>
                    </div>
                    
                    <!-- 表格信息栏 -->
                    <div class="table-info">
                        <span>
                            <i class="fas fa-users"></i> 共 <strong id="userCount">${this.users.length}</strong> 位用户
                        </span>
                        <span style="font-size: 0.75rem;">
                            <i class="fas fa-arrow-up"></i> 上下滑动查看更多
                        </span>
                    </div>
                    
                    <!-- 固定高度的表格容器 -->
                    <div class="user-table-container">
                        <table class="user-table">
                            <thead>
                                <tr>
                                    <th style="min-width: 120px;">用户名</th>
                                    <th style="min-width: 120px;">角色</th>
                                    <th style="min-width: 80px;">状态</th>
                                    <th style="min-width: 160px;">最后登录</th>
                                    <th style="min-width: 120px;">操作</th>
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
                        ${this.renderLogs()}
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
        this.startUptimeRefresh();
        this.showLoading(false);
    }

    async loadData() {
        await this.loadUsers();
        await this.loadSystemLogs();
    }

    async loadUsers() {
        try {
            const response = await this.apiRequest('/admin/users', {
                method: 'GET',
                headers: {
                    'X-Username': this.username
                }
            });
            
            if (response) {
                this.users = response;
                this.updateStatsCard();
                this.updateUserCount();
            }
        } catch (error) {
            console.error('加载用户列表失败:', error);
            this.showMessage('加载用户列表失败: ' + error.message, 'error');
        }
    }

    async loadSystemUptime() {
        try {
            const response = await this.apiRequest('/admin/users/system/uptime', {
                method: 'GET',
                headers: {
                    'X-Username': this.username
                }
            });
            
            if (response) {
                this.systemUptime = response;
                this.updateStatsCard();
                
                // 更新时间详情
                const startTimeSpan = document.querySelector('.glass-card:first-child div:last-child span:first-child + span');
                if (startTimeSpan) {
                    startTimeSpan.textContent = response.server_start_time;
                }
                
                const currentTimeSpan = document.getElementById('currentTime');
                if (currentTimeSpan) {
                    currentTimeSpan.textContent = response.current_time;
                }
            }
        } catch (error) {
            console.error('加载系统运行时间失败:', error);
        }
    }

    async loadSystemLogs() {
        // 模拟系统日志，可以后续对接真实API
        this.systemLogs = [
            `系统启动 - ${new Date().toLocaleString()}`,
            `管理员 ${this.username} 登录 - ${new Date().toLocaleString()}`,
            '用户管理模块初始化完成',
            '等待操作...'
        ];
    }

    renderLogs() {
        if (this.systemLogs.length === 0) {
            return '<div style="text-align: center; padding: 2rem; color: #64748b;">暂无日志记录</div>';
        }
        
        return this.systemLogs.map(log => `
            <div style="padding: 0.25rem 0; border-bottom: 1px solid #1e293b;">
                > ${log}
            </div>
        `).join('');
    }

    formatUptime(days) {
        if (days === 0) {
            return '不足1天';
        } else if (days === 1) {
            return '1天';
        } else {
            return `${days}天`;
        }
    }

    getOnlineCount() {
        return this.users.filter(u => u.status === 'active').length;
    }

    updateStatsCard() {
        const statsGrid = document.getElementById('statsGrid');
        if (statsGrid) {
            const uptimeDisplay = this.formatUptime(this.systemUptime.uptime_days);
            statsGrid.innerHTML = `
                ${this.createStatCard('注册用户', this.users.length, 'fas fa-users', '#38bdf8')}
                ${this.createStatCard('在线用户', this.getOnlineCount(), 'fas fa-user-check', '#10b981')}
                ${this.createStatCard('系统运行', uptimeDisplay, 'fas fa-clock', '#a78bfa')}
                ${this.createStatCard('API调用', '12.4k', 'fas fa-chart-line', '#f59e0b')}
            `;
        }
    }

    updateUserCount() {
        const userCountSpan = document.getElementById('userCount');
        if (userCountSpan) {
            userCountSpan.textContent = this.users.length;
        }
    }

    renderUserRows() {
        const roleNames = {
            'industry_analyst': '行业分析师',
            'scene_modeler': '场景建模师',
            'system_admin': '系统管理员'
        };
        
        if (this.users.length === 0) {
            return `
                <tr>
                    <td colspan="5" style="text-align: center; padding: 2rem; color: #94a3b8;">
                        暂无用户数据
                    </td>
                </tr>
            `;
        }
        
        return this.users.map(user => `
            <tr>
                <td style="padding: 0.75rem 0.5rem;">${user.username}</td>
                <td style="padding: 0.75rem 0.5rem;">${roleNames[user.role] || user.role}</td>
                <td style="padding: 0.75rem 0.5rem;">
                    <span class="status-badge ${user.status === 'active' ? 'status-active' : 'status-inactive'}">
                        ${user.status === 'active' ? '活跃' : '禁用'}
                    </span>
                </td>
                <td style="padding: 0.75rem 0.5rem;">${user.last_login || '从未登录'}</td>
                <td style="padding: 0.75rem 0.5rem;">
                    <button class="small-btn outline user-edit" data-user="${user.username}" style="margin-right: 0.25rem;">编辑</button>
                    <button class="small-btn outline user-delete" data-user="${user.username}" style="color: #ef4444;">删除</button>
                </td>
            </tr>
        `).join('');
    }

    startUptimeRefresh() {
        if (this.uptimeRefreshInterval) {
            clearInterval(this.uptimeRefreshInterval);
        }
        
        this.uptimeRefreshInterval = setInterval(() => {
            const currentTimeSpan = document.getElementById('currentTime');
            if (currentTimeSpan) {
                const now = new Date();
                const formattedTime = now.toISOString().replace('T', ' ').substring(0, 19);
                currentTimeSpan.textContent = formattedTime;
            }
        }, 1000);
    }

    bindEvents() {
        const addUserBtn = document.getElementById('addUserBtn');
        if (addUserBtn) {
            addUserBtn.addEventListener('click', () => this.showAddUserDialog());
        }
        
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
        
        const clearLogsBtn = document.getElementById('clearLogsBtn');
        if (clearLogsBtn) {
            clearLogsBtn.addEventListener('click', () => {
                this.systemLogs = [];
                const logContainer = document.getElementById('logContainer');
                if (logContainer) {
                    logContainer.innerHTML = '<div style="text-align: center; padding: 2rem; color: #64748b;">日志已清空</div>';
                }
                this.showMessage('系统日志已清空', 'info');
            });
        }
        
        const saveConfigBtn = document.getElementById('saveConfigBtn');
        if (saveConfigBtn) {
            saveConfigBtn.addEventListener('click', () => {
                const renderQuality = document.getElementById('renderQuality').value;
                const backupInterval = document.getElementById('backupInterval').value;
                const enableAnalytics = document.getElementById('enableAnalytics').checked;
                
                this.systemSettings = { renderQuality, backupInterval, enableAnalytics };
                this.showMessage('配置已保存', 'info');
                
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
            <div id="userDialog" class="modal">
                <div class="modal-content">
                    <h3>添加用户</h3>
                    <div class="input-group">
                        <label>用户名</label>
                        <input type="text" id="newUsername" placeholder="请输入用户名">
                    </div>
                    <div class="input-group">
                        <label>密码</label>
                        <input type="password" id="newPassword" placeholder="请输入密码（至少6位）">
                    </div>
                    <div class="input-group">
                        <label>角色</label>
                        <select id="newRole">
                            ${roleOptions}
                        </select>
                    </div>
                    <div class="modal-buttons">
                        <button class="btn" id="confirmAddUser">确认添加</button>
                        <button class="btn-outline" id="cancelAddUser">取消</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', dialogHtml);
        
        document.getElementById('confirmAddUser').addEventListener('click', async () => {
            const username = document.getElementById('newUsername').value.trim();
            const password = document.getElementById('newPassword').value;
            const role = document.getElementById('newRole').value;
            
            if (!username || !password) {
                this.showMessage('请填写完整信息', 'error');
                return;
            }
            
            if (password.length < 6) {
                this.showMessage('密码长度至少6位', 'error');
                return;
            }
            
            await this.createUser(username, password, role);
            document.getElementById('userDialog').remove();
        });
        
        document.getElementById('cancelAddUser').addEventListener('click', () => {
            document.getElementById('userDialog').remove();
        });
    }

    async createUser(username, password, role) {
        this.showLoading(true);
        try {
            const response = await this.apiRequest('/admin/users', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Username': this.username
                },
                body: JSON.stringify({
                    username: username,
                    password: password,
                    role: role
                })
            });
            
            if (response && !response.detail) {
                this.users.push(response);
                this.refreshUserTable();
                this.showMessage(`用户 ${username} 添加成功`, 'success');
            } else if (response && response.detail) {
                this.showMessage(response.detail, 'error');
            }
        } catch (error) {
            console.error('创建用户失败:', error);
            this.showMessage('创建用户失败: ' + error.message, 'error');
        } finally {
            this.showLoading(false);
        }
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
            <div id="userDialog" class="modal">
                <div class="modal-content">
                    <h3>编辑用户: ${username}</h3>
                    <div class="input-group">
                        <label>新用户名</label>
                        <input type="text" id="editUsername" value="${user.username}">
                    </div>
                    <div class="input-group">
                        <label>新密码（留空表示不修改）</label>
                        <input type="password" id="editPassword" placeholder="留空则不修改密码">
                    </div>
                    <div class="input-group">
                        <label>角色</label>
                        <select id="editRole">
                            ${roleOptions}
                        </select>
                    </div>
                    <div class="modal-buttons">
                        <button class="btn" id="confirmEditUser">保存修改</button>
                        <button class="btn-outline" id="cancelEditUser">取消</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', dialogHtml);
        
        document.getElementById('confirmEditUser').addEventListener('click', async () => {
            const newUsername = document.getElementById('editUsername').value.trim();
            const newPassword = document.getElementById('editPassword').value;
            const newRole = document.getElementById('editRole').value;
            
            if (!newUsername) {
                this.showMessage('用户名不能为空', 'error');
                return;
            }
            
            await this.updateUser(username, newUsername, newPassword, newRole);
            document.getElementById('userDialog').remove();
        });
        
        document.getElementById('cancelEditUser').addEventListener('click', () => {
            document.getElementById('userDialog').remove();
        });
    }

    async updateUser(oldUsername, newUsername, password, role) {
        this.showLoading(true);
        try {
            const updateData = {};
            if (newUsername !== oldUsername) updateData.username = newUsername;
            if (password) updateData.password = password;
            if (role) updateData.role = role;
            
            if (Object.keys(updateData).length === 0) {
                this.showMessage('没有要更新的内容', 'info');
                return;
            }
            
            const response = await this.apiRequest(`/admin/users/${oldUsername}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Username': this.username
                },
                body: JSON.stringify(updateData)
            });
            
            if (response && !response.detail) {
                const index = this.users.findIndex(u => u.username === oldUsername);
                if (index !== -1) {
                    this.users[index] = response;
                }
                this.refreshUserTable();
                this.showMessage(`用户 ${oldUsername} 信息已更新`, 'success');
            } else if (response && response.detail) {
                this.showMessage(response.detail, 'error');
            }
        } catch (error) {
            console.error('更新用户失败:', error);
            this.showMessage('更新用户失败: ' + error.message, 'error');
        } finally {
            this.showLoading(false);
        }
    }

    async deleteUser(username) {
        if (username === this.username) {
            this.showMessage('不能删除当前登录的管理员账号', 'error');
            return;
        }
        
        if (confirm(`确定要删除用户 "${username}" 吗？此操作不可恢复。`)) {
            this.showLoading(true);
            try {
                const response = await this.apiRequest(`/admin/users/${username}`, {
                    method: 'DELETE',
                    headers: {
                        'X-Username': this.username
                    }
                });
                
                if (response && !response.detail) {
                    this.users = this.users.filter(u => u.username !== username);
                    this.refreshUserTable();
                    this.showMessage(`用户 ${username} 已删除`, 'success');
                } else if (response && response.detail) {
                    this.showMessage(response.detail, 'error');
                }
            } catch (error) {
                console.error('删除用户失败:', error);
                this.showMessage('删除用户失败: ' + error.message, 'error');
            } finally {
                this.showLoading(false);
            }
        }
    }

    refreshUserTable() {
        const userTableBody = document.getElementById('userTableBody');
        if (userTableBody) {
            userTableBody.innerHTML = this.renderUserRows();
        }
        this.updateStatsCard();
        this.updateUserCount();
        this.bindEvents();
    }

    destroy() {
        if (this.uptimeRefreshInterval) {
            clearInterval(this.uptimeRefreshInterval);
        }
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
        }
        super.destroy();
    }
}