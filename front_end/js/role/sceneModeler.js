// 场景建模师UI
class SceneModelerUI extends BaseRoleUI {
    constructor(containerId, username) {
        super(containerId, username);
        this.scenes = [];
        this.selectedScene = null;
        this.blenderBridge = window.blenderBridge;
    }

    async render() {
        if (!this.container) return;
        
        this.showLoading(true);
        await this.loadScenes();
        
        this.container.innerHTML = `
            <div class="role-panel">
                <div class="glass-card" style="padding: 1.5rem; margin-bottom: 1rem;">
                    <div class="panel-title">
                        <i class="fas fa-cube"></i> 场景建模工作台
                        <span style="font-size: 0.8rem; margin-left: auto; color: #38bdf8;">${this.username}</span>
                    </div>
                    <p style="color: #94a3b8; margin-bottom: 1rem;">3D场景设计 | 资产库管理 | 实时渲染</p>
                    
                    <div class="stats-grid" id="statsGrid">
                        ${this.createStatCard('我的场景', this.scenes.length, 'fas fa-layer-group', '#38bdf8')}
                        ${this.createStatCard('资产总数', 156, 'fas fa-cubes', '#a78bfa')}
                        ${this.createStatCard('渲染任务', 3, 'fas fa-video', '#f59e0b')}
                        ${this.createStatCard('存储占用', '2.4GB', 'fas fa-hdd', '#10b981')}
                    </div>
                </div>

                <div class="glass-card" style="padding: 1.5rem; margin-bottom: 1rem;">
                    <div class="panel-title">
                        <i class="fas fa-project-diagram"></i> 我的场景项目
                        <button class="small-btn" id="createSceneBtn" style="margin-left: auto;"><i class="fas fa-plus"></i> 新建场景</button>
                    </div>
                    <div id="sceneList" class="scene-list">
                        ${this.renderSceneList()}
                    </div>
                </div>

                <div class="glass-card" style="padding: 1.5rem; margin-bottom: 1rem;">
                    <div class="panel-title">
                        <i class="fas fa-boxes"></i> 资产库
                        <div style="margin-left: auto; display: flex; gap: 0.5rem;">
                            <button class="small-btn outline" id="addAssetBtn"><i class="fas fa-upload"></i> 上传资产</button>
                            <button class="small-btn outline" id="refreshAssetsBtn"><i class="fas fa-sync-alt"></i> 刷新</button>
                        </div>
                    </div>
                    <div id="assetGrid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 1rem;">
                        ${this.renderAssetGrid()}
                    </div>
                </div>

                <div class="glass-card" style="padding: 1.5rem;">
                    <div class="panel-title">
                        <i class="fas fa-chalkboard"></i> Blender集成面板
                        <button class="small-btn outline" id="toggleBlenderPanel" style="margin-left: auto;">展开/收起</button>
                    </div>
                    <div id="blenderSimulatePanel" style="display: none;">
                        <div style="margin-bottom: 1rem;">
                            <div class="function-grid">
                                <button class="small-btn outline" id="simulateAddRoadTex"><i class="fas fa-road"></i> 道路纹理</button>
                                <button class="small-btn outline" id="simulateAdd3DLamp"><i class="fas fa-lightbulb"></i> 3D路灯</button>
                                <button class="small-btn outline" id="simulateTemplate0"><i class="fas fa-city"></i> 城市模板</button>
                                <button class="small-btn outline" id="simulateLLMCommand"><i class="fas fa-microphone-alt"></i> 自然语言指令</button>
                            </div>
                            <div style="margin-top: 1rem;">
                                <div style="background: #0f172a; border-radius: 0.75rem; padding: 0.75rem; font-family: monospace; font-size: 0.75rem; height: 150px; overflow-y: auto;" id="simulateOutput">
                                    <div style="color: #a78bfa;">[系统] Blender插件已就绪</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        this.bindEvents();
        this.showLoading(false);
    }

    async loadScenes() {
        // 模拟从后端获取场景列表
        this.scenes = [
            { id: 1, name: '智慧城市中心区', lastModified: '2024-01-15', status: 'published' },
            { id: 2, name: '滨江新区规划', lastModified: '2024-01-10', status: 'draft' },
            { id: 3, name: '科技园区', lastModified: '2024-01-05', status: 'published' }
        ];
    }

    renderSceneList() {
        if (this.scenes.length === 0) {
            return '<div style="text-align: center; padding: 2rem; color: #64748b;">暂无场景，点击上方按钮创建</div>';
        }
        
        return this.scenes.map(scene => `
            <div class="scene-item" data-id="${scene.id}">
                <div>
                    <div style="font-weight: 500;">${scene.name}</div>
                    <div style="font-size: 0.7rem; color: #64748b;">最后更新: ${scene.lastModified}</div>
                </div>
                <div style="display: flex; gap: 0.5rem;">
                    <span style="background: ${scene.status === 'published' ? '#10b98120' : '#f59e0b20'}; padding: 0.25rem 0.5rem; border-radius: 0.5rem; font-size: 0.7rem;">${scene.status === 'published' ? '已发布' : '草稿'}</span>
                    <button class="small-btn outline edit-scene" data-id="${scene.id}">编辑</button>
                    <button class="small-btn outline delete-scene" data-id="${scene.id}" style="color: #ef4444;">删除</button>
                </div>
            </div>
        `).join('');
    }

    renderAssetGrid() {
        const assets = [
            { name: '现代建筑', icon: 'fa-building', type: 'model' },
            { name: '柏油路面', icon: 'fa-road', type: 'texture' },
            { name: 'LED路灯', icon: 'fa-lightbulb', type: 'model' },
            { name: '绿化带', icon: 'fa-tree', type: 'model' },
            { name: '人行道', icon: 'fa-walking', type: 'texture' },
            { name: '交通标志', icon: 'fa-traffic-light', type: 'model' }
        ];
        
        return assets.map(asset => `
            <div style="background: #1e293b; border-radius: 0.75rem; padding: 0.75rem; text-align: center; cursor: pointer;" class="asset-item" data-asset="${asset.name}">
                <i class="fas ${asset.icon}" style="font-size: 2rem; color: #38bdf8;"></i>
                <div style="font-size: 0.7rem; margin-top: 0.5rem;">${asset.name}</div>
                <div style="font-size: 0.6rem; color: #64748b;">${asset.type}</div>
            </div>
        `).join('');
    }

    bindEvents() {
        // 创建场景
        const createSceneBtn = document.getElementById('createSceneBtn');
        if (createSceneBtn) {
            createSceneBtn.addEventListener('click', () => {
                const sceneName = prompt('请输入场景名称:');
                if (sceneName) {
                    this.scenes.unshift({
                        id: Date.now(),
                        name: sceneName,
                        lastModified: new Date().toISOString().split('T')[0],
                        status: 'draft'
                    });
                    const sceneList = document.getElementById('sceneList');
                    if (sceneList) sceneList.innerHTML = this.renderSceneList();
                    this.showMessage(`场景 "${sceneName}" 创建成功`, 'info');
                    this.bindSceneEvents();
                }
            });
        }
        
        // 添加资产
        const addAssetBtn = document.getElementById('addAssetBtn');
        if (addAssetBtn) {
            addAssetBtn.addEventListener('click', () => {
                this.showMessage('资产上传功能开发中', 'info');
            });
        }
        
        // 刷新资产
        const refreshAssetsBtn = document.getElementById('refreshAssetsBtn');
        if (refreshAssetsBtn) {
            refreshAssetsBtn.addEventListener('click', () => {
                this.showMessage('资产库已刷新', 'info');
            });
        }
        
        // Blender面板切换
        const toggleBtn = document.getElementById('toggleBlenderPanel');
        if (toggleBtn) {
            toggleBtn.addEventListener('click', () => {
                const panel = document.getElementById('blenderSimulatePanel');
                if (panel) panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
            });
        }
        
        // 资产点击事件
        document.querySelectorAll('.asset-item').forEach(item => {
            item.addEventListener('click', () => {
                const assetName = item.dataset.asset;
                if (this.blenderBridge) {
                    this.blenderBridge.addAsset('model', assetName);
                } else {
                    this.showMessage('Blender桥接未初始化', 'error');
                }
            });
        });
        
        this.bindSceneEvents();
        this.bindBlenderEvents();
    }

    bindSceneEvents() {
        document.querySelectorAll('.edit-scene').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const id = parseInt(btn.dataset.id);
                const scene = this.scenes.find(s => s.id === id);
                if (scene) {
                    this.showMessage(`编辑场景: ${scene.name}`, 'info');
                    if (this.blenderBridge) {
                        this.blenderBridge.applyTemplate(scene.name);
                    }
                }
            });
        });
        
        document.querySelectorAll('.delete-scene').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const id = parseInt(btn.dataset.id);
                if (confirm('确定要删除这个场景吗？')) {
                    this.scenes = this.scenes.filter(s => s.id !== id);
                    const sceneList = document.getElementById('sceneList');
                    if (sceneList) sceneList.innerHTML = this.renderSceneList();
                    this.showMessage('场景已删除', 'info');
                    this.bindSceneEvents();
                }
            });
        });
    }

    bindBlenderEvents() {
        const addRoadTex = document.getElementById('simulateAddRoadTex');
        const add3DLamp = document.getElementById('simulateAdd3DLamp');
        const applyTemplate = document.getElementById('simulateTemplate0');
        const llmCommand = document.getElementById('simulateLLMCommand');
        
        if (addRoadTex && this.blenderBridge) {
            addRoadTex.addEventListener('click', () => this.blenderBridge.addAsset('texture', '道路纹理'));
        }
        if (add3DLamp && this.blenderBridge) {
            add3DLamp.addEventListener('click', () => this.blenderBridge.addAsset('model', '3D路灯'));
        }
        if (applyTemplate && this.blenderBridge) {
            applyTemplate.addEventListener('click', () => this.blenderBridge.applyTemplate('城市基础模板_v0'));
        }
        if (llmCommand && this.blenderBridge) {
            llmCommand.addEventListener('click', () => {
                const command = prompt('请输入自然语言指令:', '在十字路口添加智能路灯');
                if (command) this.blenderBridge.processLLMCommand(command);
            });
        }
        
        // 初始化Blender桥接输出
        if (this.blenderBridge && !this.blenderBridge.outputElement) {
            this.blenderBridge.init('simulateOutput');
        }
    }
}