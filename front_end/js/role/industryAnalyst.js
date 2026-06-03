// 行业分析师UI
class IndustryAnalystUI extends BaseRoleUI {
    constructor(containerId, username) {
        super(containerId, username);
        this.industryData = null;
        this.selectedIndustry = 'all';
    }

    async render() {
        if (!this.container) return;
        
        this.showLoading(true);
        
        // 获取行业数据
        await this.loadIndustryData();
        
        this.container.innerHTML = `
            <div class="role-panel">
                <div class="glass-card" style="padding: 1.5rem; margin-bottom: 1rem;">
                    <div class="panel-title">
                        <i class="fas fa-chart-line"></i> 行业分析工作台
                        <span style="font-size: 0.8rem; margin-left: auto; color: #38bdf8;">${this.username}</span>
                    </div>
                    <p style="color: #94a3b8; margin-bottom: 1rem;">实时数据监控 | 行业趋势分析 | 智能预测</p>
                    
                    <div class="stats-grid" id="statsGrid">
                        ${this.createStatCard('城市项目数', this.industryData?.totalProjects || 0, 'fas fa-city', '#38bdf8')}
                        ${this.createStatCard('活跃场景', this.industryData?.activeScenes || 0, 'fas fa-cube', '#a78bfa')}
                        ${this.createStatCard('数据报告', this.industryData?.totalReports || 0, 'fas fa-file-alt', '#10b981')}
                        ${this.createStatCard('预测准确率', this.industryData?.accuracy || '92%', 'fas fa-chart-line', '#f59e0b')}
                    </div>
                </div>

                <div class="glass-card" style="padding: 1.5rem; margin-bottom: 1rem;">
                    <div class="panel-title">
                        <i class="fas fa-chart-bar"></i> 行业指标
                        <select id="industrySelect" style="margin-left: auto; background: #1e293b; border: 1px solid #334155; border-radius: 0.5rem; padding: 0.25rem 0.5rem; color: #e2e8f0;">
                            <option value="all">全部行业</option>
                            <option value="transportation">交通运输</option>
                            <option value="energy">能源管理</option>
                            <option value="environment">环境保护</option>
                        </select>
                    </div>
                    <div id="metricsContainer" style="display: grid; gap: 1rem;">
                        ${this.renderMetrics()}
                    </div>
                </div>

                <div class="glass-card" style="padding: 1.5rem; margin-bottom: 1rem;">
                    <div class="panel-title">
                        <i class="fas fa-calendar-alt"></i> 最近活动
                        <button class="small-btn outline" id="refreshBtn" style="margin-left: auto;"><i class="fas fa-sync-alt"></i> 刷新</button>
                    </div>
                    <div id="activityList" style="max-height: 300px; overflow-y: auto;">
                        ${this.renderActivities()}
                    </div>
                </div>

                <div class="glass-card" style="padding: 1.5rem;">
                    <div class="panel-title">
                        <i class="fas fa-chart-pie"></i> 数据分析报告
                    </div>
                    <div style="display: flex; gap: 1rem; flex-wrap: wrap;">
                        <button class="small-btn" id="generateReportBtn"><i class="fas fa-download"></i> 生成周报</button>
                        <button class="small-btn outline" id="exportDataBtn"><i class="fas fa-file-excel"></i> 导出数据</button>
                        <button class="small-btn outline" id="viewTrendBtn"><i class="fas fa-chart-line"></i> 查看趋势</button>
                    </div>
                    <div id="reportPreview" style="margin-top: 1rem; padding: 1rem; background: rgba(0,0,0,0.2); border-radius: 0.75rem; display: none;">
                        <!-- 报告预览区域 -->
                    </div>
                </div>
            </div>
        `;
        
        this.bindEvents();
        this.showLoading(false);
    }

    async loadIndustryData() {
        try {
            const response = await this.apiRequest('/analyst/dashboard', {
                method: 'GET',
                headers: {
                    'X-Username': this.username
                }
            });

            if (response) {
                this.industryData = response;
            }
        } catch (error) {
            console.error('加载行业数据失败:', error);
            this.showMessage('加载行业数据失败', 'error');
        }
    }

    renderMetrics() {
        const metrics = this.industryData?.metrics || {};
        const selected = this.selectedIndustry;
        
        let filteredMetrics = [];
        if (selected === 'all') {
            filteredMetrics = Object.entries(metrics);
        } else {
            filteredMetrics = [[selected, metrics[selected]]];
        }
        
        return filteredMetrics.map(([key, data]) => `
            <div style="background: rgba(30,41,59,0.3); border-radius: 0.75rem; padding: 1rem;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-weight: 500;">${this.getIndustryName(key)}</span>
                    <span style="color: ${data.status === 'up' ? '#10b981' : '#ef4444'};">${data.trend}</span>
                </div>
                <div style="margin-top: 0.5rem;">
                    <div style="background: #1e293b; border-radius: 0.5rem; overflow: hidden;">
                        <div style="width: ${data.value}%; background: linear-gradient(90deg, #38bdf8, #a78bfa); height: 8px;"></div>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-top: 0.5rem;">
                        <span style="font-size: 0.75rem; color: #94a3b8;">健康度评分</span>
                        <span style="font-size: 0.875rem; font-weight: 500;">${data.value}%</span>
                    </div>
                </div>
            </div>
        `).join('');
    }

    renderActivities() {
        const activities = this.industryData?.activities || [];
        return activities.map(activity => `
            <div style="padding: 0.75rem; border-bottom: 1px solid #1e293b; display: flex; gap: 0.75rem; align-items: center;">
                <i class="fas ${activity.type === 'report' ? 'fa-file-alt' : activity.type === 'data' ? 'fa-database' : 'fa-brain'}" style="color: #38bdf8; width: 24px;"></i>
                <div style="flex: 1;">
                    <div style="font-size: 0.875rem;">${activity.action}</div>
                    <div style="font-size: 0.7rem; color: #64748b;">${activity.time}</div>
                </div>
            </div>
        `).join('');
    }

    getIndustryName(key) {
        const names = {
            transportation: '交通运输业',
            energy: '能源管理业',
            environment: '环境保护业'
        };
        return names[key] || key;
    }

    bindEvents() {
        const industrySelect = document.getElementById('industrySelect');
        if (industrySelect) {
            industrySelect.addEventListener('change', (e) => {
                this.selectedIndustry = e.target.value;
                const metricsContainer = document.getElementById('metricsContainer');
                if (metricsContainer) {
                    metricsContainer.innerHTML = this.renderMetrics();
                }
            });
        }

        const refreshBtn = document.getElementById('refreshBtn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', async () => {
                this.showLoading(true);
                await this.loadIndustryData();
                this.refreshUI();
                this.showLoading(false);
                this.showMessage('数据已刷新', 'info');
            });
        }

        const generateReportBtn = document.getElementById('generateReportBtn');
        if (generateReportBtn) {
            generateReportBtn.addEventListener('click', async () => {
                this.showMessage('报告生成中...', 'info');
                const preview = document.getElementById('reportPreview');
                try {
                    const response = await this.apiRequest('/analyst/reports/generate', {
                        method: 'POST',
                        headers: {
                            'X-Username': this.username
                        }
                    });

                    if (response && !response.detail) {
                        if (preview) {
                            preview.style.display = 'block';
                            preview.innerHTML = `
                                <div style="font-size: 0.9rem; color: #38bdf8; font-weight: 500;">${response.title}</div>
                                <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 0.25rem;">
                                    报告 ID: ${response.report_id} | 生成时间：${response.generated_at}
                                </div>
                                <div style="font-size: 0.82rem; color: #e2e8f0; margin-top: 0.5rem;">${response.summary}</div>
                                <a class="small-btn outline" style="margin-top: 0.5rem; display: inline-flex; text-decoration: none;" href="http://127.0.0.1:8000${response.download_url}" target="_blank">
                                    <i class="fas fa-download"></i> 下载报告
                                </a>
                            `;
                        }
                        this.showMessage('报告已生成', 'info');
                    } else if (response && response.detail) {
                        this.showMessage(response.detail, 'error');
                    }
                } catch (error) {
                    console.error('报告生成失败:', error);
                    this.showMessage('报告生成失败', 'error');
                }
            });
        }

        const exportDataBtn = document.getElementById('exportDataBtn');
        if (exportDataBtn) {
            exportDataBtn.addEventListener('click', async () => {
                this.showMessage('数据导出中...', 'info');
                try {
                    const response = await this.apiRequest('/analyst/data/export', {
                        method: 'GET',
                        headers: {
                            'X-Username': this.username
                        }
                    });

                    if (response && !response.detail) {
                        const preview = document.getElementById('reportPreview');
                        if (preview) {
                            const exportData = response.data || {};
                            preview.style.display = 'block';
                            preview.innerHTML = `
                                <div style="font-size: 0.85rem; color: #e2e8f0;">导出文件：${response.filename}</div>
                                <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 0.25rem;">
                                    导出 ID: ${response.export_id} | 生成时间：${response.generated_at}
                                </div>
                                <div style="font-size: 0.78rem; color: #cbd5e1; margin-top: 0.4rem;">
                                    项目数: ${exportData.totalProjects || '-'} | 活跃场景: ${exportData.activeScenes || '-'} | 准确率: ${exportData.accuracy || '-'}
                                </div>
                                <a class="small-btn outline" style="margin-top: 0.5rem; display: inline-flex; text-decoration: none;" href="http://127.0.0.1:8000${response.download_url}" target="_blank">
                                    <i class="fas fa-download"></i> 下载数据
                                </a>
                            `;
                        }
                        this.showMessage('数据导出已准备', 'info');
                    } else if (response && response.detail) {
                        this.showMessage(response.detail, 'error');
                    }
                } catch (error) {
                    console.error('数据导出失败:', error);
                    this.showMessage('数据导出失败', 'error');
                }
            });
        }

        const viewTrendBtn = document.getElementById('viewTrendBtn');
        if (viewTrendBtn) {
            viewTrendBtn.addEventListener('click', async () => {
                const preview = document.getElementById('reportPreview');
                if (!preview) return;
                try {
                    const response = await this.apiRequest('/analyst/trends?days=30', {
                        method: 'GET',
                        headers: {
                            'X-Username': this.username
                        }
                    });

                    if (response && !response.detail) {
                        preview.style.display = 'block';
                        preview.innerHTML = `
                            <div style="font-size: 0.85rem; color: #38bdf8; font-weight: 500;">近 ${response.window_days} 天趋势</div>
                            <div style="font-size: 0.82rem; color: #e2e8f0; margin-top: 0.35rem;">${response.summary}</div>
                            <div style="margin-top: 0.6rem; display: grid; gap: 0.4rem;">
                                ${(response.series || []).map(item => `
                                    <div style="display: flex; align-items: center; gap: 0.5rem; font-size: 0.78rem;">
                                        <span style="color: #94a3b8; width: 80px;">${this.getIndustryName(item.label)}</span>
                                        <span style="flex: 1; background: #1e293b; border-radius: 0.35rem; height: 6px; overflow: hidden;">
                                            <span style="display: block; width: ${item.value}%; height: 100%; background: linear-gradient(90deg, #38bdf8, #a78bfa);"></span>
                                        </span>
                                        <span style="color: #e2e8f0; width: 40px; text-align: right;">${item.value}</span>
                                        <span style="color: ${item.change >= 0 ? '#10b981' : '#ef4444'}; width: 55px; text-align: right;">${item.change > 0 ? '+' : ''}${item.change}%</span>
                                    </div>
                                `).join('')}
                            </div>
                        `;
                    } else if (response && response.detail) {
                        this.showMessage(response.detail, 'error');
                    }
                } catch (error) {
                    console.error('趋势数据加载失败:', error);
                    this.showMessage('趋势数据加载失败', 'error');
                }
            });
        }
    }

    refreshUI() {
        const statsGrid = document.getElementById('statsGrid');
        if (statsGrid) {
            statsGrid.innerHTML = `
                ${this.createStatCard('城市项目数', this.industryData?.totalProjects || 0, 'fas fa-city', '#38bdf8')}
                ${this.createStatCard('活跃场景', this.industryData?.activeScenes || 0, 'fas fa-cube', '#a78bfa')}
                ${this.createStatCard('数据报告', this.industryData?.totalReports || 0, 'fas fa-file-alt', '#10b981')}
                ${this.createStatCard('预测准确率', this.industryData?.accuracy || '92%', 'fas fa-chart-line', '#f59e0b')}
            `;
        }
        
        const activityList = document.getElementById('activityList');
        if (activityList) {
            activityList.innerHTML = this.renderActivities();
        }
    }
}