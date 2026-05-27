// 场景编辑页面逻辑
class SceneEditorUI extends BaseRoleUI {
    constructor(containerId, username) {
        super(containerId, username);
        this.scene = null;
        this.editAssets = [];
        this.blenderBridge = window.blenderBridge;
    }

    init() {
        const stored = localStorage.getItem('smartcity_edit_scene');
        if (stored) {
            try {
                this.scene = JSON.parse(stored);
            } catch (_) {
                this.scene = null;
            }
        }

        if (!this.scene) {
            this.container.innerHTML = `
                <div class="glass-card" style="padding: 1.5rem; margin-bottom: 1rem;">
                    <div class="panel-title"><i class="fas fa-triangle-exclamation"></i> 未选择场景</div>
                    <p style="color: #94a3b8;">请返回场景列表并点击“编辑”。</p>
                </div>
            `;
            return;
        }

        this.render();
        this.bindEvents();
        if (this.blenderBridge && !this.blenderBridge.outputElement) {
            this.blenderBridge.init('simulateOutput');
        }
    }

    render() {
        this.container.innerHTML = `
            <div class="role-panel">
                <div class="glass-card" style="padding: 1.5rem; margin-bottom: 1rem;">
                    <div class="panel-title">
                        <i class="fas fa-pen"></i> 场景编辑面板
                        <span style="font-size: 0.8rem; margin-left: 0.5rem; color: #94a3b8;">当前: ${this.scene.name}</span>
                    </div>
                    <div style="display: grid; gap: 0.75rem; margin-top: 0.75rem;">
                        <div>
                            <label style="font-size: 0.85rem; color: #94a3b8;">场景名称</label>
                            <input id="editSceneName" value="${this.scene.name}" style="width: 100%; padding: 0.6rem; border-radius: 0.5rem; background: #0f172a; border: 1px solid #334155; color: #e2e8f0;">
                        </div>
                        <div>
                            <label style="font-size: 0.85rem; color: #94a3b8;">状态</label>
                            <select id="editSceneStatus" style="width: 100%; padding: 0.6rem; border-radius: 0.5rem; background: #0f172a; border: 1px solid #334155; color: #e2e8f0;">
                                <option value="draft" ${this.scene.status === 'draft' ? 'selected' : ''}>草稿</option>
                                <option value="published" ${this.scene.status === 'published' ? 'selected' : ''}>已发布</option>
                            </select>
                        </div>
                        <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
                            <button class="small-btn" id="saveSceneBtn"><i class="fas fa-save"></i> 保存</button>
                            <input id="editTemplateId" placeholder="模板ID（如 0）" style="flex: 1; min-width: 160px; padding: 0.5rem; border-radius: 0.5rem; background: #0f172a; border: 1px solid #334155; color: #e2e8f0;">
                            <button class="small-btn outline" id="applySceneTemplateBtn"><i class="fas fa-wand-magic-sparkles"></i> 使用模板生成</button>
                        </div>
                        <div style="font-size: 0.75rem; color: #64748b;">
                            修改场景名称与状态；模板生成会触发 Blender 生成流程。
                        </div>
                    </div>
                </div>

                <div class="glass-card" style="padding: 1.5rem; margin-bottom: 1rem;">
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
    }

    bindEvents() {
        document.querySelectorAll('[data-edit-tab]').forEach(btn => {
            btn.addEventListener('click', () => {
                const tab = btn.getAttribute('data-edit-tab');
                this.switchEditTab(tab);
            });
        });

        document.getElementById('saveSceneBtn')?.addEventListener('click', () => {
            const nameInput = document.getElementById('editSceneName');
            const statusSelect = document.getElementById('editSceneStatus');
            const newName = nameInput ? nameInput.value.trim() : '';
            const newStatus = statusSelect ? statusSelect.value : this.scene.status;

            if (!newName) {
                this.showMessage('请输入场景名称', 'error');
                return;
            }

            this.scene.name = newName;
            this.scene.status = newStatus;
            localStorage.setItem('smartcity_edit_scene', JSON.stringify(this.scene));
            this.showMessage('场景信息已更新（前端演示）', 'info');
            this.logEditAction(`编辑面板: 保存场景 ${newName}`);
        });

        document.getElementById('applySceneTemplateBtn')?.addEventListener('click', () => {
            const templateId = document.getElementById('editTemplateId')?.value.trim();
            const templateValue = templateId || this.scene.name;
            if (!templateValue) {
                this.showMessage('请输入模板ID', 'error');
                return;
            }

            if (this.blenderBridge) {
                this.blenderBridge.applyTemplate(templateValue);
            } else {
                this.showMessage('Blender桥接未初始化', 'error');
            }
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

        document.getElementById('backToListBtn')?.addEventListener('click', () => {
            window.location.href = 'modeler.html';
        });

        document.getElementById('logoutBtn')?.addEventListener('click', () => {
            const authManager = new AuthManager();
            authManager.logout();
            window.location.href = 'index.html';
        });
    }

    switchEditTab(tab) {
        const tabs = ['assets', 'layout', 'sketch', 'llm', 'render'];
        tabs.forEach(key => {
            const panel = document.getElementById(`editTab_${key}`);
            if (panel) panel.style.display = key === tab ? 'block' : 'none';
        });
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

    logEditAction(message) {
        if (this.blenderBridge && this.blenderBridge.log) {
            this.blenderBridge.log(message);
        }
    }
}

const session = requireLogin({ expectedRole: 'scene_modeler', deniedMessage: '权限不足' });
if (session) {
    const ui = new SceneEditorUI('sceneEditorRoot', session.currentUser.username);
    ui.init();
}
