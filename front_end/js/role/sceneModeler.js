// 场景建模师UI
class SceneModelerUI extends BaseRoleUI {
    constructor(containerId, username) {
        super(containerId, username);
        this.scenes = [];
        this.selectedScene = null;
        this.editAssets = [];
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

                <div class="glass-card" id="sceneEditPanel" style="padding: 1.5rem; margin-bottom: 1rem; display: none;">
                    <div class="panel-title">
                        <i class="fas fa-pen"></i> 场景编辑面板
                        <span id="editSceneBadge" style="font-size: 0.8rem; margin-left: 0.5rem; color: #94a3b8;"></span>
                        <button class="small-btn outline" id="closeEditPanelBtn" style="margin-left: auto;">关闭</button>
                    </div>
                    <div style="display: grid; gap: 0.75rem; margin-top: 0.75rem;">
                        <div>
                            <label style="font-size: 0.85rem; color: #94a3b8;">场景名称</label>
                            <input id="editSceneName" placeholder="请输入场景名称" style="width: 100%; padding: 0.6rem; border-radius: 0.5rem; background: #0f172a; border: 1px solid #334155; color: #e2e8f0;">
                        </div>
                        <div>
                            <label style="font-size: 0.85rem; color: #94a3b8;">状态</label>
                            <select id="editSceneStatus" style="width: 100%; padding: 0.6rem; border-radius: 0.5rem; background: #0f172a; border: 1px solid #334155; color: #e2e8f0;">
                                <option value="draft">草稿</option>
                                <option value="published">已发布</option>
                            </select>
                        </div>
                        <div style="display: flex; gap: 0.5rem;">
                            <button class="small-btn" id="saveSceneBtn"><i class="fas fa-save"></i> 保存</button>
                            <button class="small-btn outline" id="resetSceneBtn"><i class="fas fa-undo"></i> 重置</button>
                            <button class="small-btn outline" id="applySceneTemplateBtn"><i class="fas fa-wand-magic-sparkles"></i> 使用模板生成</button>
                        </div>
                        <div style="font-size: 0.75rem; color: #64748b;">
                            在此面板修改场景名称与状态；模板生成将调用 Blender 生成流程。
                        </div>
                    </div>
                    <div style="margin-top: 1rem;">
                        <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
                            <button class="small-btn outline" data-edit-tab="assets">资产</button>
                            <button class="small-btn outline" data-edit-tab="layout">布局</button>
                            <button class="small-btn outline" data-edit-tab="sketch">草图</button>
                            <button class="small-btn outline" data-edit-tab="llm">LLM</button>
                            <button class="small-btn outline" data-edit-tab="render">渲染</button>
                        </div>
                        <div id="editTab_assets" style="margin-top: 0.75rem;">
                            <div style="display: flex; gap: 0.5rem; align-items: center;">
                                <input id="editAssetSearch" placeholder="搜索资产" style="flex: 1; padding: 0.5rem; border-radius: 0.5rem; background: #0f172a; border: 1px solid #334155; color: #e2e8f0;">
                                <button class="small-btn outline" id="editAssetAddBtn">添加</button>
                            </div>
                            <div id="editAssetList" style="margin-top: 0.5rem; font-size: 0.75rem; color: #94a3b8;">暂无已选资产</div>
                        </div>
                        <div id="editTab_layout" style="margin-top: 0.75rem; display: none;">
                            <textarea id="editLayoutInput" placeholder="布局点集: x1,y1;x2,y2;..." style="width: 100%; padding: 0.5rem; border-radius: 0.5rem; background: #0f172a; border: 1px solid #334155; color: #e2e8f0; height: 72px;"></textarea>
                            <div style="margin-top: 0.5rem;">
                                <button class="small-btn outline" id="editApplyLayoutBtn">应用布局</button>
                            </div>
                        </div>
                        <div id="editTab_sketch" style="margin-top: 0.75rem; display: none;">
                            <input type="file" id="editSketchUpload" accept="image/*" />
                            <button class="small-btn outline" id="editProcessSketchBtn" style="margin-left: 0.5rem;">处理草图</button>
                        </div>
                        <div id="editTab_llm" style="margin-top: 0.75rem; display: none;">
                            <div style="display: flex; gap: 0.5rem;">
                                <input id="editLlmInput" placeholder="输入自然语言指令" style="flex: 1; padding: 0.5rem; border-radius: 0.5rem; background: #0f172a; border: 1px solid #334155; color: #e2e8f0;">
                                <button class="small-btn outline" id="editSendLlmBtn">发送</button>
                            </div>
                        </div>
                        <div id="editTab_render" style="margin-top: 0.75rem; display: none;">
                            <div style="display: flex; gap: 0.5rem; align-items: center;">
                                <select id="renderQualitySelect" style="padding: 0.5rem; border-radius: 0.5rem; background: #0f172a; border: 1px solid #334155; color: #e2e8f0;">
                                    <option value="draft">草稿质量</option>
                                    <option value="balanced">均衡质量</option>
                                    <option value="high">高质量</option>
                                </select>
                                <button class="small-btn" id="renderSceneBtn">开始渲染</button>
                                <button class="small-btn outline" id="renderDownloadBtn" style="display: none;">下载结果</button>
                            </div>
                            <div id="renderResult" style="margin-top: 0.5rem; font-size: 0.75rem; color: #94a3b8;">渲染结果将显示在这里</div>
                            <div id="renderPreview" style="margin-top: 0.5rem; padding: 1rem; border: 1px dashed #334155; border-radius: 0.75rem; text-align: center; color: #94a3b8; display: none;">
                                <div style="height: 140px; border-radius: 0.5rem; background: linear-gradient(135deg, #1e293b, #0f172a); display: flex; align-items: center; justify-content: center;">渲染预览占位图</div>
                            </div>
                        </div>
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
                        <i class="fas fa-terminal"></i> 操作日志
                    </div>
                    <div style="margin-top: 0.75rem;">
                        <div style="background: #0f172a; border-radius: 0.75rem; padding: 0.75rem; font-family: monospace; font-size: 0.75rem; height: 180px; overflow-y: auto;" id="simulateOutput">
                            <div style="color: #a78bfa;">[系统] Blender插件已就绪</div>
                        </div>
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
        
        // 初始化日志输出
        if (this.blenderBridge && !this.blenderBridge.outputElement) {
            this.blenderBridge.init('simulateOutput');
        }

        this.bindSceneEvents();
        this.bindEditPanelEvents();
    }

    bindSceneEvents() {
        document.querySelectorAll('.edit-scene').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const id = parseInt(btn.dataset.id);
                const scene = this.scenes.find(s => s.id === id);
                if (scene) {
                    this.showEditPanel(scene);
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

    bindEditPanelEvents() {
        const closeBtn = document.getElementById('closeEditPanelBtn');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.hideEditPanel());
        }

        const resetBtn = document.getElementById('resetSceneBtn');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => {
                if (this.selectedScene) {
                    this.fillEditForm(this.selectedScene);
                }
            });
        }

        const saveBtn = document.getElementById('saveSceneBtn');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => {
                if (!this.selectedScene) return;
                const nameInput = document.getElementById('editSceneName');
                const statusSelect = document.getElementById('editSceneStatus');
                const newName = nameInput ? nameInput.value.trim() : '';
                const newStatus = statusSelect ? statusSelect.value : this.selectedScene.status;

                if (!newName) {
                    this.showMessage('请输入场景名称', 'error');
                    return;
                }

                this.selectedScene.name = newName;
                this.selectedScene.status = newStatus;
                const sceneList = document.getElementById('sceneList');
                if (sceneList) sceneList.innerHTML = this.renderSceneList();
                this.bindSceneEvents();
                this.showMessage('场景信息已更新（前端演示）', 'info');
                this.updateEditBadge();
            });
        }

        const applyTemplateBtn = document.getElementById('applySceneTemplateBtn');
        if (applyTemplateBtn) {
            applyTemplateBtn.addEventListener('click', () => {
                if (!this.selectedScene) return;
                if (this.blenderBridge) {
                    this.blenderBridge.applyTemplate(this.selectedScene.name);
                } else {
                    this.showMessage('Blender桥接未初始化', 'error');
                }
            });
        }

        document.querySelectorAll('[data-edit-tab]').forEach(btn => {
            btn.addEventListener('click', () => {
                const tab = btn.getAttribute('data-edit-tab');
                this.switchEditTab(tab);
            });
        });

        document.getElementById('editAssetAddBtn')?.addEventListener('click', () => {
            const name = document.getElementById('editAssetSearch')?.value.trim();
            if (!name) return this.showMessage('请输入资产名称', 'error');
            this.editAssets.push(name);
            this.renderEditAssets();
            this.showMessage('资产已添加（前端演示）', 'info');
            this.logEditAction(`编辑面板: 添加资产 ${name}`);
        });

        document.getElementById('editAssetList')?.addEventListener('click', (e) => {
            const target = e.target;
            if (!(target instanceof HTMLElement)) return;
            if (!target.matches('[data-remove-asset]')) return;
            const index = parseInt(target.getAttribute('data-remove-asset'), 10);
            if (isNaN(index)) return;
            const removed = this.editAssets.splice(index, 1);
            this.renderEditAssets();
            if (removed[0]) {
                this.logEditAction(`编辑面板: 移除资产 ${removed[0]}`);
            }
        });

        document.getElementById('editApplyLayoutBtn')?.addEventListener('click', () => {
            const raw = document.getElementById('editLayoutInput')?.value.trim();
            if (!raw) return this.showMessage('请填写布局点集', 'error');
            if (this.blenderBridge) {
                const points = raw.split(';').map(p => {
                    const [x,y] = p.split(',').map(s => parseFloat(s));
                    return { x: isNaN(x)?0:x, y: isNaN(y)?0:y };
                }).filter(pt => !isNaN(pt.x) && !isNaN(pt.y));
                this.blenderBridge.applyLayout({ points });
            }
            this.logEditAction('编辑面板: 应用布局');
        });

        document.getElementById('editProcessSketchBtn')?.addEventListener('click', () => {
            const file = document.getElementById('editSketchUpload')?.files?.[0];
            if (!file) return this.showMessage('请先选择草图文件', 'error');
            if (this.blenderBridge) {
                this.blenderBridge.processSketch(file.name);
            }
            this.logEditAction(`编辑面板: 处理草图 ${file.name}`);
        });

        document.getElementById('editSendLlmBtn')?.addEventListener('click', () => {
            const cmd = document.getElementById('editLlmInput')?.value.trim();
            if (!cmd) return this.showMessage('请输入指令文本', 'error');
            if (this.blenderBridge) {
                this.blenderBridge.processLLMCommand(cmd);
            }
            this.logEditAction(`编辑面板: LLM 指令 ${cmd}`);
        });

        document.getElementById('renderSceneBtn')?.addEventListener('click', () => {
            const quality = document.getElementById('renderQualitySelect')?.value || 'balanced';
            const result = document.getElementById('renderResult');
            if (result) result.textContent = `渲染任务已提交（质量: ${quality}）`;
            const preview = document.getElementById('renderPreview');
            if (preview) preview.style.display = 'block';
            const downloadBtn = document.getElementById('renderDownloadBtn');
            if (downloadBtn) downloadBtn.style.display = 'inline-flex';
            this.showMessage('渲染任务已提交（前端演示）', 'info');
            this.logEditAction(`编辑面板: 提交渲染 (${quality})`);
        });

        document.getElementById('renderDownloadBtn')?.addEventListener('click', () => {
            const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360"><rect width="100%" height="100%" fill="#0f172a"/><text x="50%" y="50%" fill="#94a3b8" font-size="24" font-family="Arial" dominant-baseline="middle" text-anchor="middle">Render Preview</text></svg>`;
            const url = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
            const link = document.createElement('a');
            link.href = url;
            link.download = 'render_preview.svg';
            link.click();
            this.showMessage('已下载渲染结果（占位）', 'info');
        });
    }

    showEditPanel(scene) {
        this.selectedScene = scene;
        this.editAssets = [];
        const panel = document.getElementById('sceneEditPanel');
        if (panel) panel.style.display = 'block';
        this.fillEditForm(scene);
        this.updateEditBadge();
        this.renderEditAssets();
        this.switchEditTab('assets');
        panel?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    hideEditPanel() {
        const panel = document.getElementById('sceneEditPanel');
        if (panel) panel.style.display = 'none';
        this.selectedScene = null;
        const badge = document.getElementById('editSceneBadge');
        if (badge) badge.textContent = '';
    }

    switchEditTab(tab) {
        const tabs = ['assets','layout','sketch','llm','render'];
        tabs.forEach(key => {
            const panel = document.getElementById(`editTab_${key}`);
            if (panel) panel.style.display = key === tab ? 'block' : 'none';
        });
    }

    fillEditForm(scene) {
        const nameInput = document.getElementById('editSceneName');
        const statusSelect = document.getElementById('editSceneStatus');
        if (nameInput) nameInput.value = scene.name || '';
        if (statusSelect) statusSelect.value = scene.status || 'draft';
    }

    renderEditAssets() {
        const list = document.getElementById('editAssetList');
        if (!list) return;
        if (this.editAssets.length === 0) {
            list.textContent = '暂无已选资产';
            return;
        }
        list.innerHTML = this.editAssets.map((name, idx) => (
            `<div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.25rem;">
                <span>${name}</span>
                <button class="small-btn outline" data-remove-asset="${idx}" style="padding: 0.1rem 0.4rem; font-size: 0.7rem;">移除</button>
            </div>`
        )).join('');
    }

    updateEditBadge() {
        const badge = document.getElementById('editSceneBadge');
        if (badge && this.selectedScene) {
            badge.textContent = `当前: ${this.selectedScene.name}`;
        }
    }

    logEditAction(message) {
        if (this.blenderBridge && this.blenderBridge.log) {
            this.blenderBridge.log(message);
        }
    }

}