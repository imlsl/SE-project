// 场景建模师UI
class SceneModelerUI extends BaseRoleUI {
    constructor(containerId, username) {
        super(containerId, username);
        this.scenes = [];
        this.selectedScene = null;
        this.assets = [];
    }

    get blenderBridge() {
        return window.blenderBridge;
    }

    async render() {
        if (!this.container) return;
        
        this.showLoading(true);
        await this.loadScenes();
        await this.loadAssets();
        
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
                        ${this.createStatCard('资产总数', this.assets.length, 'fas fa-cubes', '#a78bfa')}
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

            </div>
        `;
        
        this.bindEvents();
        this.showLoading(false);
    }

    async loadScenes() {
        try {
            const response = await this.apiRequest('/modeler/scenes', {
                method: 'GET',
                headers: {
                    'X-Username': this.username
                }
            });

            if (response) {
                this.scenes = response;
            }
        } catch (error) {
            console.error('加载场景列表失败:', error);
            this.showMessage('加载场景列表失败', 'error');
        }
    }

    async loadAssets() {
        try {
            const response = await this.apiRequest('/modeler/assets', {
                method: 'GET',
                headers: {
                    'X-Username': this.username
                }
            });

            if (response) {
                this.assets = response;
            }
        } catch (error) {
            console.error('加载资产列表失败:', error);
            this.showMessage('加载资产列表失败', 'error');
        }
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
        if (this.assets.length === 0) {
            return '<div style="color: #94a3b8;">暂无资产，请点击“上传资产”</div>';
        }
        
        return this.assets.map(asset => `
            <div style="background: #1e293b; border-radius: 0.75rem; padding: 0.75rem; text-align: center; cursor: pointer;" class="asset-item" data-asset="${asset.name}">
                <i class="fas ${asset.icon || 'fa-cube'}" style="font-size: 2rem; color: #38bdf8;"></i>
                <div style="font-size: 0.7rem; margin-top: 0.5rem;">${asset.name}</div>
                <div style="font-size: 0.6rem; color: #64748b;">${asset.type}</div>
            </div>
        `).join('');
    }

    async handleCreateAsset() {
        const assetName = prompt('请输入资产名称');
        if (!assetName) return;
        const assetType = prompt('请输入资产类型', '设施') || '设施';
        const assetIcon = prompt('请输入 Font Awesome 图标 (例如 fa-cube)', 'fa-cube') || 'fa-cube';

        try {
            const response = await this.apiRequest('/modeler/assets', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Username': this.username
                },
                body: JSON.stringify({
                    name: assetName,
                    type: assetType,
                    icon: assetIcon
                })
            });

            if (response && response.asset) {
                this.assets.unshift(response.asset);
            }
            const grid = document.getElementById('assetGrid');
            if (grid) grid.innerHTML = this.renderAssetGrid();
            this.bindAssetEvents();
            this.refreshStats();
            this.showMessage('资产已创建', 'success');
        } catch (error) {
            console.error('Asset create failed', error);
            this.showMessage('资产创建失败', 'error');
        }
    }

    bindEvents() {
        // 创建场景
        const createSceneBtn = document.getElementById('createSceneBtn');
        if (createSceneBtn) {
            createSceneBtn.addEventListener('click', async () => {
                const sceneName = prompt('请输入场景名称:');
                if (!sceneName) return;

                try {
                    const response = await this.apiRequest('/modeler/scenes', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-Username': this.username
                        },
                        body: JSON.stringify({ name: sceneName })
                    });

                    if (response && !response.detail) {
                        this.scenes.unshift(response);
                        const sceneList = document.getElementById('sceneList');
                        if (sceneList) sceneList.innerHTML = this.renderSceneList();
                        this.showMessage(`场景 "${sceneName}" 创建成功`, 'info');
                        this.bindSceneEvents();
                    } else if (response && response.detail) {
                        this.showMessage(response.detail, 'error');
                    }
                } catch (error) {
                    console.error('创建场景失败:', error);
                    this.showMessage('创建场景失败', 'error');
                }
            });
        }
        
        // 添加资产
        const addAssetBtn = document.getElementById('addAssetBtn');
        if (addAssetBtn) {
            addAssetBtn.addEventListener('click', () => this.handleCreateAsset());
        }
        
        // 刷新资产
        const refreshAssetsBtn = document.getElementById('refreshAssetsBtn');
        if (refreshAssetsBtn) {
            refreshAssetsBtn.addEventListener('click', async () => {
                await this.loadAssets();
                const grid = document.getElementById('assetGrid');
                if (grid) grid.innerHTML = this.renderAssetGrid();
                this.bindAssetEvents();
                this.refreshStats();
                this.showMessage('资产库已刷新', 'info');
            });
        }
        
        
        this.bindAssetEvents();
        
        this.bindSceneEvents();
    }

    refreshStats() {
        const statsGrid = document.getElementById('statsGrid');
        if (!statsGrid) return;
        statsGrid.innerHTML = `
            ${this.createStatCard('我的场景', this.scenes.length, 'fas fa-layer-group', '#38bdf8')}
            ${this.createStatCard('资产总数', this.assets.length, 'fas fa-cubes', '#a78bfa')}
            ${this.createStatCard('渲染任务', 3, 'fas fa-video', '#f59e0b')}
            ${this.createStatCard('存储占用', '2.4GB', 'fas fa-hdd', '#10b981')}
        `;
    }

    bindAssetEvents() {
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
    }

    bindSceneEvents() {
        document.querySelectorAll('.edit-scene').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const id = parseInt(btn.dataset.id);
                const scene = this.scenes.find(s => s.id === id);
                if (scene) {
                    const payload = {
                        id: scene.id,
                        name: scene.name,
                        status: scene.status,
                        lastModified: scene.lastModified
                    };
                    localStorage.setItem('smartcity_edit_scene', JSON.stringify(payload));
                    window.location.href = 'scene_edit.html';
                }
            });
        });
        
        document.querySelectorAll('.delete-scene').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const id = parseInt(btn.dataset.id);
                if (!confirm('确定要删除这个场景吗？')) return;

                try {
                    const response = await this.apiRequest(`/modeler/scenes/${id}`, {
                        method: 'DELETE',
                        headers: {
                            'X-Username': this.username
                        }
                    });

                    if (response && !response.detail) {
                        this.scenes = this.scenes.filter(s => s.id !== id);
                        const sceneList = document.getElementById('sceneList');
                        if (sceneList) sceneList.innerHTML = this.renderSceneList();
                        this.showMessage('场景已删除', 'info');
                        this.bindSceneEvents();
                    } else if (response && response.detail) {
                        this.showMessage(response.detail, 'error');
                    }
                } catch (error) {
                    console.error('删除场景失败:', error);
                    this.showMessage('删除场景失败', 'error');
                }
            });
        });
    }

}