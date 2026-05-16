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
        // 模拟从后端获取数据
        this.industryData = {
            totalProjects: 24,
            activeScenes: 8,
            totalReports: 156,
            accuracy: '94%',
            metrics: {
                transportation: { value: 85, trend: '+12%', status: 'up' },
                energy: { value: 72, trend: '+5%', status: 'up' },
                environment: { value: 91, trend: '+3%', status: 'up' }
            },
            activities: [
                { time: '10:30', action: '生成了第三季度城市交通分析报告', type: 'report' },
                { time: '09:15', action: '新增了5个智慧交通场景数据', type: 'data' },
                { time: '昨天', action: '完成了能源消耗趋势预测模型', type: 'model' },
                { time: '昨天', action: '导出了环境监测月度报告', type: 'report' }
            ]
        };
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
            generateReportBtn.addEventListener('click', () => {
                this.showMessage('报告生成中...', 'info');
                setTimeout(() => {
                    this.showMessage('报告已生成，请查看下载', 'info');
                }, 1500);
            });
        }

        const exportDataBtn = document.getElementById('exportDataBtn');
        if (exportDataBtn) {
            exportDataBtn.addEventListener('click', () => {
                this.showMessage('数据导出功能开发中', 'info');
            });
        }

        const viewTrendBtn = document.getElementById('viewTrendBtn');
        if (viewTrendBtn) {
            viewTrendBtn.addEventListener('click', () => {
                const preview = document.getElementById('reportPreview');
                if (preview) {
                    preview.style.display = preview.style.display === 'none' ? 'block' : 'none';
                    if (preview.style.display === 'block') {
                        preview.innerHTML = `
                            <div style="text-align: center;">
                                <i class="fas fa-chart-line" style="font-size: 2rem; color: #38bdf8;"></i>
                                <p style="margin-top: 0.5rem;">近30天行业趋势分析显示，智慧交通领域增长显著，环比提升12.5%</p>
                            </div>
                        `;
                    }
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