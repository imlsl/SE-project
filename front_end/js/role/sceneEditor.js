// 场景编辑页面逻辑
class SceneEditorUI extends BaseRoleUI {
    constructor(containerId, username) {
        super(containerId, username);
        this.scene = null;
        this.editAssets = [];
        this.activeTab = 'assets';
        this.sketchPreviewUrl = '';
        this.blenderBridge = window.blenderBridge;
        this.templatePresets = [
            { id: '0', name: '现代风格', detail: '树木1 · 道路2 · 座椅1' },
            { id: '1', name: '古典风格', detail: '树木2 · 道路1 · 座椅2' },
            { id: '2', name: '绿色生态', detail: '树木3 · 道路3 · 座椅3' },
            { id: '3', name: '工业风格', detail: '树木1 · 道路4 · 座椅1' },
            { id: '4', name: '天津风格', detail: '树木4 · 道路2 · 座椅4' }
        ];
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
        this.switchEditTab(this.activeTab);
        this.renderEditAssets();
        if (this.blenderBridge && !this.blenderBridge.outputElement) {
            this.blenderBridge.init('simulateOutput');
        }
    }

    render() {
        const sceneName = this.escapeHTML(this.scene.name || '');
        this.container.innerHTML = `
            <div class="role-panel">
                <div class="glass-card" style="padding: 1.5rem; margin-bottom: 1rem;">
                    <div class="panel-title">
                        <i class="fas fa-pen"></i> 场景编辑面板
                        <span id="currentSceneLabel" style="font-size: 0.8rem; margin-left: 0.5rem; color: #94a3b8;">当前: ${sceneName}</span>
                    </div>
                    <div style="display: grid; gap: 0.75rem; margin-top: 0.75rem;">
                        <div>
                            <label style="font-size: 0.85rem; color: #94a3b8;">场景名称</label>
                            <input id="editSceneName" value="${sceneName}" style="width: 100%; padding: 0.6rem; border-radius: 0.5rem; background: #0f172a; border: 1px solid #334155; color: #e2e8f0;">
                            <div id="sceneNameError" style="display: none; margin-top: 0.35rem; font-size: 0.75rem; color: #f87171;"></div>
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
                        <div id="sceneSaveStatus" style="display: none; font-size: 0.75rem;"></div>
                        <div style="display: flex; gap: 0.4rem; flex-wrap: wrap;">
                            ${this.renderTemplatePresetButtons()}
                        </div>
                        <div id="templateStatus" style="font-size: 0.75rem; color: #64748b;">
                            可用模板：0 现代、1 古典、2 绿色生态、3 工业、4 天津；模板生成会触发 Blender 生成流程。
                        </div>
                    </div>
                </div>

                <div class="glass-card" style="padding: 1.5rem; margin-bottom: 1rem;">
                    <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
                        <button class="small-btn outline scene-edit-tab" data-edit-tab="assets">资产</button>
                        <button class="small-btn outline scene-edit-tab" data-edit-tab="layout">布局</button>
                        <button class="small-btn outline scene-edit-tab" data-edit-tab="sketch">草图</button>
                        <button class="small-btn outline scene-edit-tab" data-edit-tab="llm">LLM</button>
                        <button class="small-btn outline scene-edit-tab" data-edit-tab="render">渲染</button>
                    </div>

                    <div id="editTab_assets" style="margin-top: 0.75rem;">
                        <div style="display: flex; gap: 0.5rem; align-items: center;">
                            <input id="editAssetSearch" placeholder="搜索资产" style="flex: 1; padding: 0.5rem; border-radius: 0.5rem; background: #0f172a; border: 1px solid #334155; color: #e2e8f0;">
                            <button class="small-btn outline" id="editAssetAddBtn">添加</button>
                        </div>
                        <div id="editAssetHint" style="margin-top: 0.45rem; font-size: 0.75rem; color: #64748b;">输入资产名称后添加到当前场景。</div>
                        <div id="editAssetList" style="margin-top: 0.6rem; font-size: 0.75rem; color: #94a3b8;"></div>
                    </div>

                    <div id="editTab_layout" style="margin-top: 0.75rem; display: none;">
                        <textarea id="editLayoutInput" placeholder="布局点集: x1,y1;x2,y2;..." style="width: 100%; padding: 0.5rem; border-radius: 0.5rem; background: #0f172a; border: 1px solid #334155; color: #e2e8f0; height: 72px;"></textarea>
                        <div id="layoutFeedback" style="margin-top: 0.45rem; font-size: 0.75rem; color: #64748b;">示例：10,20;50,80;120,60</div>
                        <div style="margin-top: 0.5rem;">
                            <button class="small-btn outline" id="editApplyLayoutBtn">应用布局</button>
                        </div>
                    </div>

                    <div id="editTab_sketch" style="margin-top: 0.75rem; display: none;">
                        <input type="file" id="editSketchUpload" accept="image/*" />
                        <button class="small-btn outline" id="editProcessSketchBtn" style="margin-left: 0.5rem;">处理草图</button>
                        <div id="sketchMeta" style="margin-top: 0.5rem; font-size: 0.75rem; color: #64748b;">请选择草图图片后处理。</div>
                        <div id="sketchPreview" style="display: none; margin-top: 0.6rem;"></div>
                        <div id="sketchResult" style="margin-top: 0.5rem; font-size: 0.75rem; color: #94a3b8;"></div>
                    </div>

                    <div id="editTab_llm" style="margin-top: 0.75rem; display: none;">
                        <div style="display: flex; gap: 0.5rem;">
                            <input id="editLlmInput" placeholder="输入自然语言指令" style="flex: 1; padding: 0.5rem; border-radius: 0.5rem; background: #0f172a; border: 1px solid #334155; color: #e2e8f0;">
                            <button class="small-btn outline" id="editSendLlmBtn">发送</button>
                        </div>
                        <div style="display: flex; gap: 0.4rem; flex-wrap: wrap; margin-top: 0.55rem;">
                            <button class="small-btn outline llm-suggestion" style="padding: 0.25rem 0.55rem; font-size: 0.75rem;" data-command="树木1，道路2，座椅1">现代配置</button>
                            <button class="small-btn outline llm-suggestion" style="padding: 0.25rem 0.55rem; font-size: 0.75rem;" data-command="树木3，道路3，座椅3">绿色生态</button>
                            <button class="small-btn outline llm-suggestion" style="padding: 0.25rem 0.55rem; font-size: 0.75rem;" data-command="树木1，道路4，座椅1">工业道路</button>
                        </div>
                        <div id="llmResult" style="margin-top: 0.5rem; font-size: 0.75rem; color: #64748b;">AI 指令结果会显示在这里。</div>
                    </div>

                    <div id="editTab_render" style="margin-top: 0.75rem; display: none;">
                        <div style="display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap;">
                            <select id="renderQualitySelect" style="padding: 0.5rem; border-radius: 0.5rem; background: #0f172a; border: 1px solid #334155; color: #e2e8f0;">
                                <option value="draft">草稿质量</option>
                                <option value="balanced">均衡质量</option>
                                <option value="high">高质量</option>
                            </select>
                            <button class="small-btn" id="renderSceneBtn">开始渲染</button>
                            <button class="small-btn outline" id="renderDownloadBtn" disabled style="display: none;">下载结果</button>
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
                        <div style="margin-left: auto; display: flex; gap: 0.5rem;">
                            <button class="small-btn outline" id="copyLogBtn" style="padding: 0.3rem 0.65rem; font-size: 0.75rem;">复制日志</button>
                            <button class="small-btn outline" id="clearLogBtn" style="padding: 0.3rem 0.65rem; font-size: 0.75rem;">清空日志</button>
                        </div>
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

        document.getElementById('saveSceneBtn')?.addEventListener('click', () => this.saveScene());
        document.getElementById('applySceneTemplateBtn')?.addEventListener('click', () => this.applyTemplate());
        document.querySelectorAll('[data-template-preset]').forEach(btn => {
            btn.addEventListener('click', () => this.selectTemplatePreset(btn.getAttribute('data-template-preset')));
        });
        document.getElementById('editAssetAddBtn')?.addEventListener('click', () => this.addEditAsset());
        document.getElementById('editAssetSearch')?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') this.addEditAsset();
        });

        document.getElementById('editAssetList')?.addEventListener('click', (e) => {
            const target = e.target;
            if (!(target instanceof HTMLElement)) return;
            const button = target.closest('[data-remove-asset]');
            if (!button) return;
            const index = parseInt(button.getAttribute('data-remove-asset'), 10);
            if (Number.isNaN(index)) return;
            const removed = this.editAssets.splice(index, 1);
            this.renderEditAssets();
            if (removed[0]) {
                this.logEditAction(`编辑面板: 移除资产 ${removed[0]}`, 'warning');
            }
        });

        document.getElementById('editLayoutInput')?.addEventListener('input', () => this.updateLayoutFeedback());
        document.getElementById('editApplyLayoutBtn')?.addEventListener('click', () => this.applyLayout());

        document.getElementById('editSketchUpload')?.addEventListener('change', (event) => this.updateSketchPreview(event));
        document.getElementById('editProcessSketchBtn')?.addEventListener('click', () => this.processSketch());

        document.querySelectorAll('.llm-suggestion').forEach(btn => {
            btn.addEventListener('click', () => {
                const input = document.getElementById('editLlmInput');
                if (input) input.value = btn.getAttribute('data-command') || '';
            });
        });
        document.getElementById('editSendLlmBtn')?.addEventListener('click', () => this.sendLlmCommand());

        document.getElementById('renderSceneBtn')?.addEventListener('click', () => this.startRender());
        document.getElementById('renderDownloadBtn')?.addEventListener('click', () => this.downloadRenderPreview());

        document.getElementById('copyLogBtn')?.addEventListener('click', () => this.copyLog());
        document.getElementById('clearLogBtn')?.addEventListener('click', () => {
            if (this.blenderBridge?.clearLog) this.blenderBridge.clearLog();
            this.logEditAction('日志已清空', 'system');
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

    async saveScene() {
        const saveBtn = document.getElementById('saveSceneBtn');
        const nameInput = document.getElementById('editSceneName');
        const statusSelect = document.getElementById('editSceneStatus');
        const error = document.getElementById('sceneNameError');
        const newName = nameInput ? nameInput.value.trim() : '';
        const newStatus = statusSelect ? statusSelect.value : this.scene.status;

        if (!newName) {
            if (error) {
                error.textContent = '请输入场景名称';
                error.style.display = 'block';
            }
            this.showMessage('请输入场景名称', 'error');
            return;
        }
        if (error) error.style.display = 'none';

        this.setButtonBusy(saveBtn, true, '<i class="fas fa-spinner fa-pulse"></i> 保存中');
        this.logEditAction(`编辑面板: 正在保存场景 ${newName}`, 'task');

        try {
            let updated = null;
            if (this.scene.id) {
                updated = await this.apiRequest(`/modeler/scenes/${this.scene.id}`, {
                    method: 'PUT',
                    body: JSON.stringify({ name: newName, status: newStatus })
                });
            }

            if (updated && !updated.detail) {
                this.scene = { ...this.scene, ...updated };
                localStorage.setItem('smartcity_edit_scene', JSON.stringify(this.scene));
                this.updateSceneHeader();
                this.setSceneSaveStatus(`已保存到后端 · ${new Date().toLocaleTimeString()}`, 'success');
                this.showMessage('场景信息已保存', 'info');
                this.logEditAction(`编辑面板: 场景已保存 ${newName}`, 'success');
                return;
            }

            if (!this.scene.id || !updated) {
                this.scene.name = newName;
                this.scene.status = newStatus;
                localStorage.setItem('smartcity_edit_scene', JSON.stringify(this.scene));
                this.updateSceneHeader();
                this.setSceneSaveStatus(`后端未连接，已先保存到本地 · ${new Date().toLocaleTimeString()}`, 'warning');
                this.showMessage('已保存到本地，后端未确认', 'info');
                this.logEditAction(`编辑面板: 本地保存场景 ${newName}`, 'warning');
                return;
            }

            this.setSceneSaveStatus(updated?.detail || '保存失败，请稍后重试', 'error');
            this.showMessage(updated?.detail || '保存失败，请稍后重试', 'error');
            this.logEditAction(`编辑面板: 保存失败 ${updated?.detail || ''}`, 'error');
        } catch (error) {
            console.error('Save scene failed:', error);
            this.scene.name = newName;
            this.scene.status = newStatus;
            localStorage.setItem('smartcity_edit_scene', JSON.stringify(this.scene));
            this.updateSceneHeader();
            this.setSceneSaveStatus(`后端请求失败，已先保存到本地 · ${new Date().toLocaleTimeString()}`, 'warning');
            this.showMessage('已保存到本地，后端请求失败', 'info');
            this.logEditAction(`编辑面板: 后端保存失败，已本地保存 ${error.message}`, 'warning');
        } finally {
            this.setButtonBusy(saveBtn, false);
        }
    }

    async applyTemplate() {
        const templateInput = document.getElementById('editTemplateId');
        const status = document.getElementById('templateStatus');
        const button = document.getElementById('applySceneTemplateBtn');
        const templateValue = templateInput?.value.trim() || this.scene.name;
        if (!templateValue) {
            this.showMessage('请输入模板ID', 'error');
            return;
        }

        this.setButtonBusy(button, true, '<i class="fas fa-spinner fa-pulse"></i> 生成中');
        if (status) {
            status.textContent = `模板 ${templateValue} 已提交，正在等待 Blender 任务状态...`;
            status.style.color = '#38bdf8';
        }

        try {
            if (this.blenderBridge) {
                await this.blenderBridge.applyTemplate(templateValue);
                this.logEditAction(`编辑面板: 使用模板生成 ${templateValue}`, 'task');
                this.showMessage('模板生成任务已提交', 'info');
            } else {
                this.showMessage('Blender桥接未初始化', 'error');
            }
        } finally {
            this.setButtonBusy(button, false);
        }
    }

    renderTemplatePresetButtons() {
        return this.templatePresets.map(template => (
            `<button class="small-btn outline template-preset-btn" data-template-preset="${template.id}" title="${this.escapeHTML(template.detail)}" style="padding: 0.3rem 0.6rem; font-size: 0.75rem;">
                ${template.id} · ${this.escapeHTML(template.name)}
            </button>`
        )).join('');
    }

    selectTemplatePreset(templateId) {
        const template = this.templatePresets.find(item => item.id === templateId);
        const input = document.getElementById('editTemplateId');
        const status = document.getElementById('templateStatus');
        if (input) input.value = templateId || '';
        document.querySelectorAll('[data-template-preset]').forEach(btn => {
            btn.classList.toggle('active', btn.getAttribute('data-template-preset') === templateId);
        });
        if (template && status) {
            status.textContent = `已选择模板 ${template.id}：${template.name}（${template.detail}）。点击“使用模板生成”后会提交到 Blender。`;
            status.style.color = '#38bdf8';
        }
    }

    setSceneSaveStatus(message, type = 'success') {
        const status = document.getElementById('sceneSaveStatus');
        if (!status) return;
        status.textContent = message;
        status.style.color = this.feedbackColor(type);
        status.style.display = 'block';
    }

    addEditAsset() {
        const input = document.getElementById('editAssetSearch');
        const name = input?.value.trim();
        if (!name) {
            this.showMessage('请输入资产名称', 'error');
            return;
        }

        const exists = this.editAssets.some(asset => asset.toLowerCase() === name.toLowerCase());
        if (exists) {
            this.showMessage('该资产已添加', 'error');
            this.logEditAction(`编辑面板: 重复资产 ${name}`, 'warning');
            return;
        }

        this.editAssets.push(name);
        input.value = '';
        this.renderEditAssets();
        this.showMessage('资产已添加', 'info');
        this.logEditAction(`编辑面板: 添加资产 ${name}`, 'success');
        if (this.blenderBridge?.addAsset) {
            this.blenderBridge.addAsset('model', name);
        }
    }

    async applyLayout() {
        const button = document.getElementById('editApplyLayoutBtn');
        const raw = document.getElementById('editLayoutInput')?.value.trim();
        const parsed = this.parseLayoutPoints(raw);
        if (!parsed.valid) {
            this.setLayoutFeedback(parsed.message, 'error');
            this.showMessage(parsed.message, 'error');
            return;
        }

        this.setButtonBusy(button, true, '<i class="fas fa-spinner fa-pulse"></i> 应用中');
        this.setLayoutFeedback(`已识别 ${parsed.points.length} 个点，正在应用布局...`, 'task');

        try {
            const response = await this.apiRequest('/modeler/layout/apply', {
                method: 'POST',
                body: JSON.stringify({ points: parsed.points })
            });

            if (response && !response.detail) {
                if (this.blenderBridge?.applyLayout) {
                    await this.blenderBridge.applyLayout({ points: parsed.points });
                }
                const roadCount = response.road_count ?? Math.max(parsed.points.length - 1, 0);
                this.setLayoutFeedback(`应用成功：${parsed.points.length} 个点，${roadCount} 条道路。`, 'success');
                this.showMessage('布局已应用', 'info');
                this.logEditAction(`编辑面板: 应用布局 ${parsed.points.length} 个点`, 'success');
            } else {
                this.setLayoutFeedback(response?.detail || '布局应用失败', 'error');
                this.showMessage(response?.detail || '布局应用失败', 'error');
                this.logEditAction(`编辑面板: 布局应用失败 ${response?.detail || ''}`, 'error');
            }
        } finally {
            this.setButtonBusy(button, false);
        }
    }

    updateLayoutFeedback() {
        const raw = document.getElementById('editLayoutInput')?.value.trim();
        if (!raw) {
            this.setLayoutFeedback('示例：10,20;50,80;120,60', 'muted');
            return;
        }
        const parsed = this.parseLayoutPoints(raw);
        if (parsed.valid) {
            this.setLayoutFeedback(`已识别 ${parsed.points.length} 个点，预计 ${Math.max(parsed.points.length - 1, 0)} 条道路。`, 'task');
        } else {
            this.setLayoutFeedback(parsed.message, 'error');
        }
    }

    updateSketchPreview(event) {
        const file = event.target.files?.[0];
        const meta = document.getElementById('sketchMeta');
        const preview = document.getElementById('sketchPreview');
        const result = document.getElementById('sketchResult');
        if (this.sketchPreviewUrl) URL.revokeObjectURL(this.sketchPreviewUrl);

        if (!file) {
            if (meta) meta.textContent = '请选择草图图片后处理。';
            if (preview) {
                preview.style.display = 'none';
                preview.innerHTML = '';
            }
            if (result) result.textContent = '';
            return;
        }

        this.sketchPreviewUrl = URL.createObjectURL(file);
        if (meta) meta.textContent = `${file.name} · ${this.formatFileSize(file.size)}`;
        if (preview) {
            preview.style.display = 'block';
            preview.innerHTML = `<img src="${this.sketchPreviewUrl}" alt="草图预览" style="max-width: 220px; max-height: 140px; border-radius: 0.5rem; border: 1px solid #334155; object-fit: cover;">`;
        }
        if (result) result.textContent = '草图已选择，可以开始处理。';
    }

    async processSketch() {
        const button = document.getElementById('editProcessSketchBtn');
        const file = document.getElementById('editSketchUpload')?.files?.[0];
        const result = document.getElementById('sketchResult');
        if (!file) {
            this.showMessage('请先选择草图文件', 'error');
            return;
        }

        this.setButtonBusy(button, true, '<i class="fas fa-spinner fa-pulse"></i> 处理中');
        if (result) {
            result.textContent = '正在提取点集与道路线...';
            result.style.color = '#38bdf8';
        }

        try {
            const response = await this.apiRequest('/modeler/sketch/process', {
                method: 'POST',
                body: JSON.stringify({ file_name: file.name })
            });

            if (response && !response.detail) {
                if (this.blenderBridge?.processSketch) {
                    await this.blenderBridge.processSketch(file.name);
                }
                const count = response.points?.length || 0;
                if (result) {
                    result.textContent = `处理完成：提取 ${count} 个点，${response.road_count || 0} 条道路。`;
                    result.style.color = '#10b981';
                }
                this.showMessage('草图处理完成', 'info');
                this.logEditAction(`编辑面板: 处理草图 ${file.name}`, 'success');
            } else {
                if (result) {
                    result.textContent = response?.detail || '草图处理失败';
                    result.style.color = '#f87171';
                }
                this.showMessage(response?.detail || '草图处理失败', 'error');
                this.logEditAction(`编辑面板: 草图处理失败 ${response?.detail || ''}`, 'error');
            }
        } finally {
            this.setButtonBusy(button, false);
        }
    }

    async sendLlmCommand() {
        const button = document.getElementById('editSendLlmBtn');
        const input = document.getElementById('editLlmInput');
        const result = document.getElementById('llmResult');
        const cmd = input?.value.trim();
        if (!cmd) {
            this.showMessage('请输入指令文本', 'error');
            return;
        }

        this.setButtonBusy(button, true, '<i class="fas fa-spinner fa-pulse"></i> 发送中');
        if (result) {
            result.textContent = 'AI 指令已发送，正在等待执行结果...';
            result.style.color = '#38bdf8';
        }

        try {
            if (this.blenderBridge?.processLLMCommand) {
                await this.blenderBridge.processLLMCommand(cmd);
            }
            if (result) {
                result.textContent = `已提交指令：“${cmd}”。请在操作日志查看任务状态。`;
                result.style.color = '#10b981';
            }
            this.showMessage('AI 指令已提交', 'info');
            this.logEditAction(`编辑面板: LLM 指令 ${cmd}`, 'task');
        } finally {
            this.setButtonBusy(button, false);
        }
    }

    startRender() {
        const button = document.getElementById('renderSceneBtn');
        const quality = document.getElementById('renderQualitySelect')?.value || 'balanced';
        const result = document.getElementById('renderResult');
        const preview = document.getElementById('renderPreview');
        const downloadBtn = document.getElementById('renderDownloadBtn');

        this.setButtonBusy(button, true, '<i class="fas fa-spinner fa-pulse"></i> 渲染中');
        if (downloadBtn) {
            downloadBtn.style.display = 'none';
            downloadBtn.disabled = true;
        }
        if (preview) preview.style.display = 'block';
        if (result) {
            result.textContent = `渲染任务已提交（质量: ${this.renderQualityLabel(quality)}），正在生成预览...`;
            result.style.color = '#38bdf8';
        }
        this.logEditAction(`编辑面板: 提交渲染 (${this.renderQualityLabel(quality)})`, 'task');

        setTimeout(() => {
            if (result) {
                result.textContent = `渲染完成（质量: ${this.renderQualityLabel(quality)}），可以下载预览结果。`;
                result.style.color = '#10b981';
            }
            if (downloadBtn) {
                downloadBtn.style.display = 'inline-flex';
                downloadBtn.disabled = false;
            }
            this.setButtonBusy(button, false);
            this.showMessage('渲染任务完成（前端演示）', 'info');
            this.logEditAction('编辑面板: 渲染完成，预览已生成', 'success');
        }, 900);
    }

    downloadRenderPreview() {
        const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360"><rect width="100%" height="100%" fill="#0f172a"/><text x="50%" y="50%" fill="#94a3b8" font-size="24" font-family="Arial" dominant-baseline="middle" text-anchor="middle">Render Preview</text></svg>`;
        const url = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
        const link = document.createElement('a');
        link.href = url;
        link.download = 'render_preview.svg';
        link.click();
        this.showMessage('已下载渲染结果（占位）', 'info');
        this.logEditAction('编辑面板: 下载渲染预览', 'success');
    }

    async copyLog() {
        const output = document.getElementById('simulateOutput');
        const text = output?.innerText || '';
        if (!text.trim()) {
            this.showMessage('暂无日志可复制', 'error');
            return;
        }
        try {
            await navigator.clipboard.writeText(text);
            this.showMessage('日志已复制', 'info');
        } catch (_) {
            const textarea = document.createElement('textarea');
            textarea.value = text;
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand('copy');
            textarea.remove();
            this.showMessage('日志已复制', 'info');
        }
    }

    switchEditTab(tab) {
        this.activeTab = tab;
        const tabs = ['assets', 'layout', 'sketch', 'llm', 'render'];
        tabs.forEach(key => {
            const panel = document.getElementById(`editTab_${key}`);
            if (panel) panel.style.display = key === tab ? 'block' : 'none';
        });
        document.querySelectorAll('[data-edit-tab]').forEach(btn => {
            btn.classList.toggle('active', btn.getAttribute('data-edit-tab') === tab);
        });
    }

    renderEditAssets() {
        const list = document.getElementById('editAssetList');
        if (!list) return;
        if (this.editAssets.length === 0) {
            list.innerHTML = '<div style="color: #64748b;">暂无已选资产</div>';
            return;
        }
        list.innerHTML = this.editAssets.map((name, idx) => (
            `<span class="scene-asset-tag">
                <i class="fas fa-cube"></i>
                ${this.escapeHTML(name)}
                <button type="button" data-remove-asset="${idx}" aria-label="移除资产 ${this.escapeHTML(name)}"><i class="fas fa-times"></i></button>
            </span>`
        )).join('');
    }

    parseLayoutPoints(raw) {
        if (!raw) return { valid: false, points: [], message: '请填写布局点集' };
        const chunks = raw.split(';').map(part => part.trim()).filter(Boolean);
        if (chunks.length < 2) {
            return { valid: false, points: [], message: '至少需要 2 个点，例如：10,20;50,80' };
        }
        const points = [];
        for (const chunk of chunks) {
            const parts = chunk.split(',').map(part => part.trim());
            if (parts.length !== 2) {
                return { valid: false, points: [], message: `格式错误：${chunk} 应为 x,y` };
            }
            const x = Number(parts[0]);
            const y = Number(parts[1]);
            if (!Number.isFinite(x) || !Number.isFinite(y)) {
                return { valid: false, points: [], message: `坐标必须是数字：${chunk}` };
            }
            points.push({ x, y });
        }
        return { valid: true, points, message: '' };
    }

    setLayoutFeedback(message, type = 'muted') {
        const feedback = document.getElementById('layoutFeedback');
        if (!feedback) return;
        feedback.textContent = message;
        feedback.style.color = this.feedbackColor(type);
    }

    updateSceneHeader() {
        const label = document.getElementById('currentSceneLabel');
        if (label) label.textContent = `当前: ${this.scene.name}`;
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

    logEditAction(message, type = 'task') {
        if (this.blenderBridge?.log) {
            this.blenderBridge.log(message, type);
        }
    }

    feedbackColor(type) {
        return {
            error: '#f87171',
            success: '#10b981',
            task: '#38bdf8',
            warning: '#f59e0b',
            muted: '#64748b'
        }[type] || '#64748b';
    }

    renderQualityLabel(value) {
        return {
            draft: '草稿质量',
            balanced: '均衡质量',
            high: '高质量'
        }[value] || value;
    }

    formatFileSize(bytes) {
        if (!bytes) return '0 KB';
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
    }

    escapeHTML(value) {
        return String(value)
            .replaceAll('&', '&amp;')
            .replaceAll('<', '&lt;')
            .replaceAll('>', '&gt;')
            .replaceAll('"', '&quot;')
            .replaceAll("'", '&#39;');
    }
}

const session = requireLogin({ expectedRole: 'scene_modeler', deniedMessage: '权限不足' });
if (session) {
    const ui = new SceneEditorUI('sceneEditorRoot', session.currentUser.username);
    ui.init();
}
