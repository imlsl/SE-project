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
                        <div style="margin-left: auto; display: flex; align-items: center; gap: 0.75rem;">
                            <button class="small-btn outline" id="launchBlenderBtn"> 进入 Blender</button>
                        </div>
                    </div>
                    <p style="color: #94a3b8; margin-bottom: 1rem;"><i class="fas fa-map-pin"></i> 场景项目管理 · 资产库维护 · 3D 城市建模</p>

                    <div class="stats-grid" id="statsGrid">
                        ${this.createStatCard('场景总数', this.scenes.length, 'fas fa-layer-group', '#38bdf8')}
                        ${this.createStatCard('已发布', this.scenes.filter(s => s.status === 'published').length, 'fas fa-check-circle', '#10b981')}
                        ${this.createStatCard('草稿中', this.scenes.filter(s => s.status === 'draft').length, 'fas fa-pen', '#f59e0b')}
                        ${this.createStatCard('资产总数', this.assets.length, 'fas fa-cubes', '#a78bfa')}
                    </div>
                </div>

                <div class="glass-card" style="padding: 1.5rem; margin-bottom: 1rem;">
                    <div class="panel-title">
                        <i class="fas fa-project-diagram"></i> 我的场景项目
                        <button class="small-btn" id="createSceneBtn" style="margin-left: auto;"><i class="fas fa-plus"></i> 新建场景</button>
                    </div>
                    <div id="createSceneForm" style="display: none; border: 1px solid #334155; border-radius: 0.5rem; padding: 0.75rem; background: #0f172a; margin-bottom: 0.75rem;">
                        <div style="display: flex; gap: 0.5rem; align-items: center;">
                            <input id="newSceneName" placeholder="输入场景名称（必填）" style="flex: 1; padding: 0.5rem; border-radius: 0.45rem; background: #1e293b; border: 1px solid #334155; color: #e2e8f0; font-size: 0.82rem;">
                            <button class="small-btn" id="confirmCreateBtn"><i class="fas fa-check"></i> 创建</button>
                            <button class="small-btn outline" id="cancelCreateBtn">取消</button>
                        </div>
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
                    <div id="uploadAssetForm" style="display: none; border: 1px solid #334155; border-radius: 0.5rem; padding: 0.75rem; background: #0f172a; margin-bottom: 0.75rem;">
                        <div style="display: grid; gap: 0.55rem;">
                            <input id="uploadAssetName" placeholder="资产名称（必填）" style="padding: 0.5rem; border-radius: 0.45rem; background: #1e293b; border: 1px solid #334155; color: #e2e8f0; font-size: 0.82rem;">
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem;">
                                <input id="uploadAssetType" placeholder="类型（设施、建筑...）" value="设施" style="padding: 0.5rem; border-radius: 0.45rem; background: #1e293b; border: 1px solid #334155; color: #e2e8f0; font-size: 0.82rem;">
                                <input id="uploadAssetIcon" placeholder="图标名" value="fa-cube" style="padding: 0.5rem; border-radius: 0.45rem; background: #1e293b; border: 1px solid #334155; color: #e2e8f0; font-size: 0.82rem;">
                            </div>
                            <div style="font-size: 0.7rem; color: #64748b;"><i class="fas fa-info-circle"></i> 图标名参考：fa-tree / fa-chair / fa-lightbulb / fa-road / fa-cube</div>
                            <div style="display: flex; gap: 0.5rem;">
                                <button class="small-btn" id="confirmUploadBtn"><i class="fas fa-check"></i> 确认上传</button>
                                <button class="small-btn outline" id="cancelUploadBtn">取消</button>
                            </div>
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
            return `<div class="empty-state">
                <i class="fas fa-folder-open"></i>
                <div>暂无场景项目</div>
                <div style="font-size: 0.75rem; margin-top: 0.25rem;">点击「新建场景」开始创建</div>
            </div>`;
        }

        return this.scenes.map(scene => `
            <div class="scene-item" data-id="${scene.id}">
                <div style="display: flex; align-items: center; gap: 0.75rem;">
                    <i class="fas fa-city" style="font-size: 1.5rem; color: ${scene.status === 'published' ? '#34d399' : '#fbbf24'}; opacity: 0.7;"></i>
                    <div>
                        <div style="font-weight: 500;">${scene.name}</div>
                        <div style="font-size: 0.7rem; color: #64748b;">最后更新: ${scene.lastModified}</div>
                    </div>
                </div>
                <div style="display: flex; gap: 0.5rem; align-items: center;">
                    <span class="status-badge ${scene.status === 'published' ? 'published' : 'draft'}">${scene.status === 'published' ? '已发布' : '草稿'}</span>
                    <button class="small-btn outline edit-scene" data-id="${scene.id}"><i class="fas fa-pen"></i> 编辑</button>
                    <button class="small-btn outline delete-scene" data-id="${scene.id}" style="color: #ef4444; border-color: rgba(239,68,68,0.3);"><i class="fas fa-trash"></i> 删除</button>
                </div>
            </div>
        `).join('');
    }

    renderAssetGrid() {
        if (this.assets.length === 0) {
            return '<div style="color: #94a3b8;">暂无资产，请点击"上传资产"</div>';
        }

        return this.assets.map(asset => `
            <div style="background: #1e293b; border-radius: 0.75rem; padding: 0.75rem; text-align: center; cursor: pointer;" class="asset-item" data-asset="${asset.name}">
                <i class="fas ${asset.icon || 'fa-cube'}" style="font-size: 2rem; color: #38bdf8;"></i>
                <div style="font-size: 0.7rem; margin-top: 0.5rem;">${asset.name}</div>
                <div style="font-size: 0.6rem; color: #64748b;">${asset.type}</div>
            </div>
        `).join('');
    }

    toggleAssetForm(show = true) {
        const form = document.getElementById('uploadAssetForm');
        if (form) {
            form.style.display = show ? 'block' : 'none';
            if (!show) {
                document.getElementById('uploadAssetName').value = '';
                document.getElementById('uploadAssetType').value = '设施';
                document.getElementById('uploadAssetIcon').value = 'fa-cube';
            }
        }
    }

    async confirmCreateAsset() {
        const nameInput = document.getElementById('uploadAssetName');
        const typeInput = document.getElementById('uploadAssetType');
        const iconInput = document.getElementById('uploadAssetIcon');
        const assetName = nameInput?.value.trim();
        if (!assetName) {
            this.showMessage('请输入资产名称', 'error');
            nameInput?.focus();
            return;
        }
        const assetType = typeInput?.value.trim() || '设施';
        const assetIcon = iconInput?.value.trim() || 'fa-cube';

        const btn = document.getElementById('confirmUploadBtn');
        this.setButtonBusy(btn, true, '<i class="fas fa-spinner fa-pulse"></i> 上传中');

        try {
            const response = await this.apiRequest('/modeler/assets', {
                method: 'POST',
                headers: { 'X-Username': this.username },
                body: JSON.stringify({ name: assetName, type: assetType, icon: assetIcon })
            });

            // 后端返回 AssetItem 直接对象，非 { asset: ... } 包裹
            if (response && !response.detail) {
                this.assets.unshift(response);
                const grid = document.getElementById('assetGrid');
                if (grid) grid.innerHTML = this.renderAssetGrid();
                this.refreshStats();
                this.toggleAssetForm(false);
                this.showMessage(`资产「${assetName}」已创建`, 'success');
            } else if (response?.detail) {
                this.showMessage(response.detail, 'error');
            }
        } catch (error) {
            console.error('Asset create failed', error);
            this.showMessage('资产创建失败', 'error');
        } finally {
            this.setButtonBusy(btn, false);
        }
    }

    toggleSceneForm(show = true) {
        const form = document.getElementById('createSceneForm');
        const input = document.getElementById('newSceneName');
        if (form) {
            form.style.display = show ? 'block' : 'none';
            if (show) setTimeout(() => input?.focus(), 100);
            if (!show && input) input.value = '';
        }
    }

    async confirmCreateScene() {
        const input = document.getElementById('newSceneName');
        const sceneName = input?.value.trim();
        if (!sceneName) {
            this.showMessage('请输入场景名称', 'error');
            input?.focus();
            return;
        }

        const btn = document.getElementById('confirmCreateBtn');
        this.setButtonBusy(btn, true, '<i class="fas fa-spinner fa-pulse"></i> 创建中');

        try {
            const response = await this.apiRequest('/modeler/scenes', {
                method: 'POST',
                headers: { 'X-Username': this.username },
                body: JSON.stringify({ name: sceneName })
            });

            if (response && !response.detail) {
                this.scenes.unshift(response);
                const sceneList = document.getElementById('sceneList');
                if (sceneList) sceneList.innerHTML = this.renderSceneList();
                this.bindSceneEvents();
                this.refreshStats();
                this.toggleSceneForm(false);
                this.showMessage(`场景「${sceneName}」创建成功`, 'info');
            } else if (response?.detail) {
                this.showMessage(response.detail, 'error');
            }
        } catch (error) {
            console.error('创建场景失败:', error);
            this.showMessage('创建场景失败', 'error');
        } finally {
            this.setButtonBusy(btn, false);
        }
    }

    // 弹出简洁的跳转提示
    showBlenderModal() {
        const overlay = document.createElement('div');
        overlay.className = 'blender-modal-overlay';
        
        overlay.innerHTML = `
            <div class="blender-modal">
                
                <p>正在跳转到 Blender...</p>
            </div>
        `;
        
        document.body.appendChild(overlay);
        
        // 尝试跳转
        window.location.href = 'blender://open?project=smartcity';
        
        // 2秒后自动关闭弹窗
        setTimeout(() => {
            overlay.remove();
        }, 2000);
    }

    bindEvents() {
        // 创建场景 — 内联表单
        document.getElementById('createSceneBtn')?.addEventListener('click', () => this.toggleSceneForm(true));
        document.getElementById('confirmCreateBtn')?.addEventListener('click', () => this.confirmCreateScene());
        document.getElementById('cancelCreateBtn')?.addEventListener('click', () => this.toggleSceneForm(false));
        document.getElementById('newSceneName')?.addEventListener('keydown', e => {
            if (e.key === 'Enter') this.confirmCreateScene();
        });
        
        // 上传资产
        document.getElementById('addAssetBtn')?.addEventListener('click', () => this.toggleAssetForm(true));
        document.getElementById('confirmUploadBtn')?.addEventListener('click', () => this.confirmCreateAsset());
        document.getElementById('cancelUploadBtn')?.addEventListener('click', () => this.toggleAssetForm(false));
        // Enter 键快捷提交
        document.getElementById('uploadAssetName')?.addEventListener('keydown', e => {
            if (e.key === 'Enter') this.confirmCreateAsset();
        });
        
        // 刷新资产
        const refreshAssetsBtn = document.getElementById('refreshAssetsBtn');
        if (refreshAssetsBtn) {
            refreshAssetsBtn.addEventListener('click', async () => {
                await this.loadAssets();
                const grid = document.getElementById('assetGrid');
                if (grid) grid.innerHTML = this.renderAssetGrid();
                this.refreshStats();
                this.showMessage('资产库已刷新', 'info');
            });
        }

        // 进入 Blender 按钮
        const launchBlenderBtn = document.getElementById('launchBlenderBtn');
        if (launchBlenderBtn) {
            launchBlenderBtn.addEventListener('click', () => this.showBlenderModal());
        }

        this.bindSceneEvents();
    }

    refreshStats() {
        const statsGrid = document.getElementById('statsGrid');
        if (!statsGrid) return;
        statsGrid.innerHTML = `
            ${this.createStatCard('场景总数', this.scenes.length, 'fas fa-layer-group', '#38bdf8')}
            ${this.createStatCard('已发布', this.scenes.filter(s => s.status === 'published').length, 'fas fa-check-circle', '#10b981')}
            ${this.createStatCard('草稿中', this.scenes.filter(s => s.status === 'draft').length, 'fas fa-pen', '#f59e0b')}
            ${this.createStatCard('资产总数', this.assets.length, 'fas fa-cubes', '#a78bfa')}
        `;
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

    setButtonBusy(button, busy, busyHtml = '') {
        if (!button) return;
        if (busy) {
            button.dataset.originalHtml = button.innerHTML;
            button.innerHTML = busyHtml || button.innerHTML;
            button.disabled = true;
            return;
        }
        if (button.dataset.originalHtml) {
            button.innerHTML = button.dataset.originalHtml;
            delete button.dataset.originalHtml;
        }
        button.disabled = false;
    }

}