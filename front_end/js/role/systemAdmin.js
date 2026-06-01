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
        this.apiStats = null;
        this.autoRefreshInterval = null;
        this.uptimeRefreshInterval = null;
        this.logRefreshInterval = null;
    }

    async render() {
        if (!this.container) return;
        
        this.showLoading(true);
        await this.loadData();
        await this.loadSystemUptime();
        await this.loadSystemLogs();
        
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
                </div>

                <div class="glass-card" style="padding: 1.5rem; margin-bottom: 1rem;">
                    <div class="panel-title">
                        <i class="fas fa-user-cog"></i> 用户管理
                        <button class="small-btn" id="addUserBtn" style="margin-left: auto;"><i class="fas fa-plus"></i> 添加用户</button>
                    </div>
                    
                    <div class="table-info">
                        <span>
                            <i class="fas fa-users"></i> 共 <strong id="userCount">${this.users.length}</strong> 位用户
                        </span>
                        <span style="font-size: 0.75rem;">
                            <i class="fas fa-arrow-up"></i> 上下滑动查看更多
                        </span>
                    </div>
                    
                    <div class="user-table-container">
                        <table class="user-table">
                            <thead>
                                <tr>
                                    <th style="min-width: 120px;">用户名</th>
                                    <th style="min-width: 120px;">角色</th>
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
                        <div style="margin-left: auto; display: flex; gap: 0.5rem;">
                            <button class="small-btn outline" id="refreshLogsBtn"><i class="fas fa-sync-alt"></i> 刷新</button>
                            <button class="small-btn outline" id="clearLogsBtn" style="color: #ef4444;">清空日志</button>
                        </div>
                    </div>
                    <div id="logContainer" style="background: #0f172a; border-radius: 0.75rem; padding: 0.75rem; font-family: monospace; font-size: 0.75rem; height: 300px; overflow-y: auto;">
                        ${this.renderLogs()}
                    </div>
                    <div id="logStats" style="margin-top: 0.5rem; font-size: 0.7rem; color: #64748b; text-align: right;">
                        共 ${this.systemLogs.length} 条日志
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
        this.startLogAutoRefresh();
        this.showLoading(false);
    }

    async loadData() {
        await this.loadUsers();
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
            }
        } catch (error) {
            console.error('加载系统运行时间失败:', error);
        }
    }

    async loadSystemSettings() {
        try {
            const response = await this.apiRequest('/admin/users/system/settings', {
                method: 'GET',
                headers: {
                    'X-Username': this.username
                }
            });

            if (response && !response.detail) {
                this.systemSettings = response;
            }
        } catch (error) {
            console.error('加载系统配置失败:', error);
        }
    }

    async loadApiStats() {
        try {
            const response = await this.apiRequest('/admin/users/system/api-stats', {
                method: 'GET',
                headers: {
                    'X-Username': this.username
                }
            });

            if (response && !response.detail) {
                this.apiStats = response;
                this.updateStatsCard();
            }
        } catch (error) {
            console.error('加载 API 统计失败:', error);
        }
    }

    async loadSystemLogs() {
        try {
            const response = await this.apiRequest('/admin/users/system/logs?limit=100', {
                method: 'GET',
                headers: {
                    'X-Username': this.username
                }
            });
            
            // 后端返回的是字符串数组，需要解析成日志对象
            if (response && Array.isArray(response)) {
                this.systemLogs = response.map(logLine => this.parseLogLine(logLine));
            } else {
                this.systemLogs = [];
            }
        } catch (error) {
            console.error('加载系统日志失败:', error);
            this.systemLogs = [];
        }
    }

    /**
     * 解析日志行
     * 日志格式示例: "2024-01-15 10:30:45 - admin - INFO - 用户登录成功"
     */
    parseLogLine(logLine) {
        try {
            // 尝试匹配标准日志格式: 时间 - 用户名 - 级别 - 消息
            const patterns = [
                /^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+-\s+([^\s-]+)\s+-\s+(\w+)\s+-\s+(.+)$/,
                /^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}),\d+\s+-\s+([^\s-]+)\s+-\s+(\w+)\s+-\s+(.+)$/,
                /^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+-\s+(\w+)\s+-\s+(.+)$/
            ];
            
            for (const pattern of patterns) {
                const match = logLine.match(pattern);
                if (match) {
                    let timestamp = match[1];
                    let username = match[2] || 'system';
                    let level = match[3] ? match[3].toLowerCase() : 'info';
                    let message = match[4] || match[3] || '';
                    
                    // 映射日志级别
                    let type = 'info';
                    if (level.includes('error')) type = 'error';
                    else if (level.includes('warning')) type = 'warning';
                    else if (level.includes('success')) type = 'success';
                    
                    return {
                        timestamp: timestamp,
                        username: username,
                        type: type,
                        message: message,
                        raw: logLine
                    };
                }
            }
            
            // 如果无法解析，返回默认格式
            return {
                timestamp: new Date().toISOString().slice(0, 19).replace('T', ' '),
                username: 'system',
                type: 'info',
                message: logLine,
                raw: logLine
            };
        } catch (error) {
            // 解析失败时的兜底处理
            return {
                timestamp: new Date().toISOString().slice(0, 19).replace('T', ' '),
                username: 'system',
                type: 'info',
                message: logLine,
                raw: logLine
            };
        }
    }

    renderLogs() {
        if (this.systemLogs.length === 0) {
            return '<div style="text-align: center; padding: 2rem; color: #64748b;">暂无日志记录</div>';
        }
        
        const getLogStyle = (type) => {
            switch(type) {
                case 'error':
                    return { icon: 'fa-times-circle', color: '#ef4444' };
                case 'warning':
                    return { icon: 'fa-exclamation-triangle', color: '#f59e0b' };
                case 'success':
                    return { icon: 'fa-check-circle', color: '#10b981' };
                default:
                    return { icon: 'fa-info-circle', color: '#38bdf8' };
            }
        };
        
        return this.systemLogs.map(log => {
            const style = getLogStyle(log.type);
            return `
                <div style="padding: 0.5rem 0; border-bottom: 1px solid #1e293b; display: flex; gap: 0.75rem; font-family: monospace;">
                    <span style="color: #64748b; min-width: 150px;">${this.escapeHtml(log.timestamp)}</span>
                    <span style="color: ${style.color}; min-width: 70px;">
                        <i class="fas ${style.icon}"></i> ${this.escapeHtml(log.type.toUpperCase())}
                    </span>
                    <span style="color: #94a3b8; min-width: 100px;">[${this.escapeHtml(log.username)}]</span>
                    <span style="color: #e2e8f0; flex: 1;">${this.escapeHtml(log.message)}</span>
                </div>
            `;
        }).join('');
    }
    
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    async refreshLogs() {
        await this.loadSystemLogs();
        const logContainer = document.getElementById('logContainer');
        if (logContainer) {
            logContainer.innerHTML = this.renderLogs();
            // 自动滚动到底部显示最新日志
            logContainer.scrollTop = logContainer.scrollHeight;
        }
        
        const logStats = document.getElementById('logStats');
        if (logStats) {
            logStats.innerHTML = `共 ${this.systemLogs.length} 条日志`;
        }
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
            const apiTotal = this.apiStats?.total_calls ? `${this.apiStats.total_calls}` : '0';
            statsGrid.innerHTML = `
                ${this.createStatCard('注册用户', this.users.length, 'fas fa-users', '#38bdf8')}
                ${this.createStatCard('在线用户', this.getOnlineCount(), 'fas fa-user-check', '#10b981')}
                ${this.createStatCard('系统运行', uptimeDisplay, 'fas fa-clock', '#a78bfa')}
                ${this.createStatCard('API调用', apiTotal, 'fas fa-chart-line', '#f59e0b')}
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
                    <td colspan="4" style="text-align: center; padding: 2rem; color: #94a3b8;">
                        暂无用户数据
                    </td>
                </tr>
            `;
        }
        
        return this.users.map(user => `
            <tr>
                <td style="padding: 0.75rem 0.5rem;">${this.escapeHtml(user.username)}</td>
                <td style="padding: 0.75rem 0.5rem;">${roleNames[user.role] || user.role}</td>
                <td style="padding: 0.75rem 0.5rem;">${user.last_login || '从未登录'}</td>
                <td style="padding: 0.75rem 0.5rem;">
                    <button class="small-btn outline user-edit" data-user="${this.escapeHtml(user.username)}" style="margin-right: 0.25rem;">编辑</button>
                    <button class="small-btn outline user-delete" data-user="${this.escapeHtml(user.username)}" style="color: #ef4444;">删除</button>
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
    
    startLogAutoRefresh() {
        if (this.logRefreshInterval) {
            clearInterval(this.logRefreshInterval);
        }
        
        this.logRefreshInterval = setInterval(() => {
            this.refreshLogs();
        }, 30000);
    }

    bindEvents() {
        const addUserBtn = document.getElementById('addUserBtn');
        if (addUserBtn) {
            addUserBtn.addEventListener('click', () => this.showAddUserDialog());
        }
        
        const userTableBody = document.getElementById('userTableBody');
        if (userTableBody) {
            userTableBody.addEventListener('click', (e) => {
                const editBtn = e.target.closest('.user-edit');
                if (editBtn) {
                    const username = editBtn.dataset.user;
                    this.showEditUserDialog(username);
                }
                
                const deleteBtn = e.target.closest('.user-delete');
                if (deleteBtn) {
                    const username = deleteBtn.dataset.user;
                    this.deleteUser(username);
                }
            });
        }
        
        const refreshLogsBtn = document.getElementById('refreshLogsBtn');
        if (refreshLogsBtn) {
            refreshLogsBtn.addEventListener('click', () => this.refreshLogs());
        }
        
        const clearLogsBtn = document.getElementById('clearLogsBtn');
        if (clearLogsBtn) {
            clearLogsBtn.addEventListener('click', async () => {
                if (confirm('确定要清空所有系统日志吗？此操作不可恢复。')) {
                    await this.clearAllLogs();
                }
            });
        }
        
        const saveConfigBtn = document.getElementById('saveConfigBtn');
        if (saveConfigBtn) {
            saveConfigBtn.addEventListener('click', async () => {
                const renderQuality = document.getElementById('renderQuality').value;
                const backupInterval = document.getElementById('backupInterval').value;
                const enableAnalytics = document.getElementById('enableAnalytics').checked;

                await this.saveSystemSettings({ renderQuality, backupInterval, enableAnalytics });
            });
        }
    }

    async saveSystemSettings(payload) {
        try {
            const response = await this.apiRequest('/admin/users/system/settings', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Username': this.username
                },
                body: JSON.stringify(payload)
            });

            if (response && !response.detail) {
                this.systemSettings = response;
                this.showMessage('配置已保存', 'info');
                
                this.refreshLogs();
            });
        }
    }

    async clearAllLogs() {
        this.showLoading(true);
        try {
            const response = await this.apiRequest('/admin/users/system/logs', {
                method: 'DELETE',
                headers: {
                    'X-Username': this.username
                }
            });
            
            if (response) {
                this.showMessage('系统日志已清空', 'success');
                await this.refreshLogs();
            }
        } catch (error) {
            console.error('清空日志失败:', error);
            this.showMessage('清空日志失败: ' + error.message, 'error');
        } finally {
            this.showLoading(false);
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
                await this.refreshLogs();
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
                    <h3>编辑用户: ${this.escapeHtml(username)}</h3>
                    <div class="input-group">
                        <label>新用户名</label>
                        <input type="text" id="editUsername" value="${this.escapeHtml(user.username)}">
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
            
            const response = await this.apiRequest(`/admin/users/${encodeURIComponent(oldUsername)}`, {
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
                await this.refreshLogs();
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
                const response = await this.apiRequest(`/admin/users/${encodeURIComponent(username)}`, {
                    method: 'DELETE',
                    headers: {
                        'X-Username': this.username
                    }
                });
                
                if (response && !response.detail) {
                    this.users = this.users.filter(u => u.username !== username);
                    this.refreshUserTable();
                    this.showMessage(`用户 ${username} 已删除`, 'success');
                    await this.refreshLogs();
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
    }

    destroy() {
        if (this.uptimeRefreshInterval) {
            clearInterval(this.uptimeRefreshInterval);
        }
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
        }
        if (this.logRefreshInterval) {
            clearInterval(this.logRefreshInterval);
        }
        super.destroy();
    }
}
