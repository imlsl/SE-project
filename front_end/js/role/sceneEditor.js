// 场景编辑页：通过后端调用 Blender 中已安装的 SCGS 插件。
class SceneEditorUI extends BaseRoleUI {
    constructor(containerId, username) {
        super(containerId, username);
        this.scene = null;
        this.editAssets = [];
        this.activeTab = 'generate';
        this.sketchPreviewUrl = '';
        this.blenderBridge = window.blenderBridge;
        this.lastDownloadUrl = '';
        this.templatePresets = [
            { id: '0', name: '现代模板', detail: '由 SCGS 插件解释模板 ID 0' },
            { id: '1', name: '古典模板', detail: '由 SCGS 插件解释模板 ID 1' },
            { id: '2', name: '生态模板', detail: '由 SCGS 插件解释模板 ID 2' },
            { id: '3', name: '工业模板', detail: '由 SCGS 插件解释模板 ID 3' },
            { id: '4', name: '地域模板', detail: '由 SCGS 插件解释模板 ID 4' }
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
                <div class="glass-card" style="padding: 1.5rem;">
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
        this.blenderBridge?.init('simulateOutput');
    }

    render() {
        const sceneName = this.escapeHTML(this.scene.name || '');
        this.container.innerHTML = `
            <div class="role-panel">
                <div class="glass-card" style="padding: 1.5rem; margin-bottom: 1rem;">
                    <div class="panel-title">
                        <i class="fas fa-pen"></i> 场景编辑
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
                            <button class="small-btn" id="saveSceneBtn"><i class="fas fa-save"></i> 保存场景信息</button>
                            <button class="small-btn outline" id="runDiagnosticsBtn"><i class="fas fa-stethoscope"></i> 插件诊断</button>
                        </div>
                        <div id="sceneSaveStatus" style="display: none; font-size: 0.75rem;"></div>
                    </div>
                </div>

                <div class="glass-card" style="padding: 1.5rem; margin-bottom: 1rem;">
                    <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
                        <button class="small-btn outline scene-edit-tab" data-edit-tab="generate">生成</button>
                        <button class="small-btn outline scene-edit-tab" data-edit-tab="diagnostics">诊断</button>
                        <button class="small-btn outline scene-edit-tab" data-edit-tab="assets">资产</button>
                        <button class="small-btn outline scene-edit-tab" data-edit-tab="layout">布局</button>
                        <button class="small-btn outline scene-edit-tab" data-edit-tab="sketch">草图</button>
                        <button class="small-btn outline scene-edit-tab" data-edit-tab="render">渲染</button>
                    </div>

                    <div id="editTab_generate" style="margin-top: 0.9rem;">
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 0.75rem;">
                            <label style="display: grid; gap: 0.35rem; color: #94a3b8; font-size: 0.82rem;">
                                自然语言描述
                                <textarea id="generateDescription" placeholder="例如：生成一座雨天的现代城市" style="min-height: 84px; padding: 0.6rem; border-radius: 0.5rem; background: #0f172a; border: 1px solid #334155; color: #e2e8f0;">${sceneName}</textarea>
                            </label>
                            <label style="display: grid; gap: 0.35rem; color: #94a3b8; font-size: 0.82rem;">
                                模板 ID
                                <input id="editTemplateId" placeholder="例如 0" style="padding: 0.6rem; border-radius: 0.5rem; background: #0f172a; border: 1px solid #334155; color: #e2e8f0;">
                            </label>
                            <label style="display: grid; gap: 0.35rem; color: #94a3b8; font-size: 0.82rem;">
                                道路类型
                                <select id="generateRoadType" style="padding: 0.6rem; border-radius: 0.5rem; background: #0f172a; border: 1px solid #334155; color: #e2e8f0;">
                                    <option value="">插件默认</option>
                                    <option value="1">1 - 默认/基础</option>
                                    <option value="2">2 - 网格/扩展</option>
                                    <option value="3">3 - 图像/草图提取</option>
                                    <option value="4">4 - 手动顶点边</option>
                                </select>
                            </label>
                            <label style="display: grid; gap: 0.35rem; color: #94a3b8; font-size: 0.82rem;">
                                天气
                                <select id="generateWeather" style="padding: 0.6rem; border-radius: 0.5rem; background: #0f172a; border: 1px solid #334155; color: #e2e8f0;">
                                    <option value="">插件默认</option>
                                    <option value="sunny">sunny</option>
                                    <option value="rainy">rainy</option>
                                    <option value="snowy">snowy</option>
                                </select>
                            </label>
                            <label style="display: grid; gap: 0.35rem; color: #94a3b8; font-size: 0.82rem;">
                                风格
                                <input id="generateStyle" value="default" style="padding: 0.6rem; border-radius: 0.5rem; background: #0f172a; border: 1px solid #334155; color: #e2e8f0;">
                            </label>
                            <label style="display: grid; gap: 0.35rem; color: #94a3b8; font-size: 0.82rem;">
                                缩放
                                <input id="generateScale" type="number" step="0.1" value="1.0" style="padding: 0.6rem; border-radius: 0.5rem; background: #0f172a; border: 1px solid #334155; color: #e2e8f0;">
                            </label>
                        </div>
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 0.75rem; margin-top: 0.75rem;">
                            <label style="display: grid; gap: 0.35rem; color: #94a3b8; font-size: 0.82rem;">
                                手动顶点
                                <textarea id="manualVertices" placeholder="(0,0,0),(50,0,0),(50,50,0)" style="height: 72px; padding: 0.6rem; border-radius: 0.5rem; background: #0f172a; border: 1px solid #334155; color: #e2e8f0;"></textarea>
                            </label>
                            <label style="display: grid; gap: 0.35rem; color: #94a3b8; font-size: 0.82rem;">
                                手动边
                                <textarea id="manualEdges" placeholder="(0,1),(1,2)" style="height: 72px; padding: 0.6rem; border-radius: 0.5rem; background: #0f172a; border: 1px solid #334155; color: #e2e8f0;"></textarea>
                            </label>
                        </div>
                        <div style="display: flex; gap: 0.5rem; flex-wrap: wrap; margin-top: 0.75rem;">
                            ${this.renderTemplatePresetButtons()}
                        </div>
                        <div style="display: flex; gap: 0.5rem; flex-wrap: wrap; align-items: center; margin-top: 0.75rem;">
                            <button class="small-btn" id="generateSceneBtn"><i class="fas fa-wand-magic-sparkles"></i> 调用 SCGS 生成</button>
                            <a id="blendDownloadLink" class="small-btn outline" href="#" target="_blank" style="display: none; text-decoration: none;"><i class="fas fa-download"></i> 下载 .blend</a>
                        </div>
                        <div id="generationStatus" style="margin-top: 0.6rem; font-size: 0.78rem; color: #64748b;">生成任务会调用 Blender 中已安装的 SCGS 插件，仓库样例仅作为参考。</div>
                    </div>

                    <div id="editTab_diagnostics" style="margin-top: 0.9rem; display: none;">
                        <div id="diagnosticsSummary" style="font-size: 0.78rem; color: #94a3b8;">点击“插件诊断”检查 Blender 路径、SCGS 启用状态和 sna 候选算子。</div>
                        <pre id="diagnosticsOutput" style="margin-top: 0.75rem; max-height: 260px; overflow: auto; white-space: pre-wrap; background: #0f172a; border: 1px solid #334155; border-radius: 0.5rem; padding: 0.75rem; color: #cbd5e1;"></pre>
                    </div>

                    <div id="editTab_assets" style="margin-top: 0.9rem; display: none;">
                        <div style="display: flex; gap: 0.5rem; align-items: center;">
                            <input id="editAssetSearch" placeholder="输入资产名称" style="flex: 1; padding: 0.5rem; border-radius: 0.5rem; background: #0f172a; border: 1px solid #334155; color: #e2e8f0;">
                            <button class="small-btn outline" id="editAssetAddBtn">添加</button>
                        </div>
                        <div style="margin-top: 0.45rem; font-size: 0.75rem; color: #64748b;">资产库暂保留演示能力，真实同步需要 SCGS 插件暴露资产 API。</div>
                        <div id="editAssetList" style="margin-top: 0.6rem; font-size: 0.75rem; color: #94a3b8;"></div>
                    </div>

                    <div id="editTab_layout" style="margin-top: 0.9rem; display: none;">
                        <textarea id="editLayoutInput" placeholder="布局点集: x1,y1;x2,y2;..." style="width: 100%; padding: 0.5rem; border-radius: 0.5rem; background: #0f172a; border: 1px solid #334155; color: #e2e8f0; height: 72px;"></textarea>
                        <div id="layoutFeedback" style="margin-top: 0.45rem; font-size: 0.75rem; color: #64748b;">示例：0,20;50,80;120,60</div>
                        <div style="margin-top: 0.5rem;"><button class="small-btn outline" id="editApplyLayoutBtn">应用布局演示</button></div>
                    </div>

                    <div id="editTab_sketch" style="margin-top: 0.9rem; display: none;">
                        <input type="file" id="editSketchUpload" accept="image/*" />
                        <button class="small-btn outline" id="editProcessSketchBtn" style="margin-left: 0.5rem;">处理草图演示</button>
                        <div id="sketchMeta" style="margin-top: 0.5rem; font-size: 0.75rem; color: #64748b;">请选择草图图片后处理。</div>
                        <div id="sketchPreview" style="display: none; margin-top: 0.6rem;"></div>
                        <div id="sketchResult" style="margin-top: 0.5rem; font-size: 0.75rem; color: #94a3b8;"></div>
                    </div>

                    <div id="editTab_render" style="margin-top: 0.9rem; display: none;">
                        <div style="display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap;">
                            <select id="renderQualitySelect" style="padding: 0.5rem; border-radius: 0.5rem; background: #0f172a; border: 1px solid #334155; color: #e2e8f0;">
                                <option value="draft">草稿质量</option>
                                <option value="balanced">均衡质量</option>
                                <option value="high">高质量</option>
                            </select>
                            <button class="small-btn" id="renderSceneBtn">开始渲染演示</button>
                            <button class="small-btn outline" id="renderDownloadBtn" disabled style="display: none;">下载结果</button>
                        </div>
                        <div id="renderResult" style="margin-top: 0.5rem; font-size: 0.75rem; color: #94a3b8;">渲染结果将显示在这里。</div>
                        <div id="renderPreview" style="margin-top: 0.5rem; padding: 1rem; border: 1px dashed #334155; border-radius: 0.75rem; text-align: center; color: #94a3b8; display: none;">
                            <div style="height: 140px; border-radius: 0.5rem; background: linear-gradient(135deg, #1e293b, #0f172a); display: flex; align-items: center; justify-content: center;">Render Preview</div>
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
                            <div style="color: #a78bfa;">[system] Blender bridge ready.</div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    bindEvents() {
        document.querySelectorAll('[data-edit-tab]').forEach(btn => {
            btn.addEventListener('click', () => this.switchEditTab(btn.getAttribute('data-edit-tab')));
        });

        document.getElementById('saveSceneBtn')?.addEventListener('click', () => this.saveScene());
        document.getElementById('runDiagnosticsBtn')?.addEventListener('click', () => this.runDiagnostics());
        document.getElementById('generateSceneBtn')?.addEventListener('click', () => this.generateScene());
        document.querySelectorAll('[data-template-preset]').forEach(btn => {
            btn.addEventListener('click', () => this.selectTemplatePreset(btn.getAttribute('data-template-preset')));
        });

        document.getElementById('editAssetAddBtn')?.addEventListener('click', () => this.addEditAsset());
        document.getElementById('editAssetSearch')?.addEventListener('keydown', e => {
            if (e.key === 'Enter') this.addEditAsset();
        });
        document.getElementById('editAssetList')?.addEventListener('click', e => this.removeAssetFromClick(e));

        document.getElementById('editLayoutInput')?.addEventListener('input', () => this.updateLayoutFeedback());
        document.getElementById('editApplyLayoutBtn')?.addEventListener('click', () => this.applyLayout());
        document.getElementById('editSketchUpload')?.addEventListener('change', event => this.updateSketchPreview(event));
        document.getElementById('editProcessSketchBtn')?.addEventListener('click', () => this.processSketch());
        document.getElementById('renderSceneBtn')?.addEventListener('click', () => this.startRender());
        document.getElementById('renderDownloadBtn')?.addEventListener('click', () => this.downloadRenderPreview());

        document.getElementById('copyLogBtn')?.addEventListener('click', () => this.copyLog());
        document.getElementById('clearLogBtn')?.addEventListener('click', () => {
            this.blenderBridge?.clearLog();
            this.logEditAction('Log cleared.', 'system');
        });
        document.getElementById('backToListBtn')?.addEventListener('click', () => { window.location.href = 'modeler.html'; });
        document.getElementById('logoutBtn')?.addEventListener('click', () => {
            new AuthManager().logout();
            window.location.href = 'index.html';
        });
    }

    collectGenerationParams() {
        return {
            scene_id: this.scene.id || null,
            city_name: document.getElementById('editSceneName')?.value.trim() || this.scene.name || '',
            description: document.getElementById('generateDescription')?.value.trim() || '',
            template_id: document.getElementById('editTemplateId')?.value.trim() || '',
            road_type: document.getElementById('generateRoadType')?.value || '',
            weather: document.getElementById('generateWeather')?.value || '',
            manual_vertices: document.getElementById('manualVertices')?.value.trim() || '',
            manual_edges: document.getElementById('manualEdges')?.value.trim() || '',
            style: document.getElementById('generateStyle')?.value.trim() || 'default',
            scale: Number(document.getElementById('generateScale')?.value || 1)
        };
    }

    async generateScene() {
        const button = document.getElementById('generateSceneBtn');
        const status = document.getElementById('generationStatus');
        const download = document.getElementById('blendDownloadLink');
        const params = this.collectGenerationParams();
        if (!params.description && !params.template_id) {
            this.showMessage('请填写描述或模板 ID', 'error');
            return;
        }

        this.setButtonBusy(button, true, '<i class="fas fa-spinner fa-pulse"></i> 生成中');
        if (download) download.style.display = 'none';
        this.setGenerationStatus('任务已提交，等待 Blender 返回状态...', 'task');

        try {
            await this.blenderBridge.generateScene(params, {
                onStatus: task => this.setGenerationStatus(this.formatTaskStatus(task), task.status === 'failed' ? 'error' : 'task'),
                onComplete: task => {
                    this.lastDownloadUrl = task.absolute_download_url;
                    this.setGenerationStatus(`生成完成。Task ID: ${task.task_id}`, 'success');
                    if (download && this.lastDownloadUrl) {
                        download.href = this.lastDownloadUrl;
                        download.style.display = 'inline-flex';
                    }
                },
                onFailed: task => this.setGenerationStatus(task.error || '生成失败', 'error')
            });
            this.showMessage('SCGS 生成完成', 'info');
        } catch (error) {
            this.setGenerationStatus(error.message || '生成失败', 'error');
            this.showMessage('SCGS 生成失败', 'error');
        } finally {
            this.setButtonBusy(button, false);
            if (status) status.style.display = 'block';
        }
    }

    async runDiagnostics() {
        this.switchEditTab('diagnostics');
        const button = document.getElementById('runDiagnosticsBtn');
        const summary = document.getElementById('diagnosticsSummary');
        const output = document.getElementById('diagnosticsOutput');
        this.setButtonBusy(button, true, '<i class="fas fa-spinner fa-pulse"></i> 诊断中');
        if (summary) summary.textContent = '正在启动 Blender 进行诊断...';
        if (output) output.textContent = '';

        try {
            const data = await this.blenderBridge.diagnostics();
            const ok = data.blender_started && !data.error;
            if (summary) {
                summary.style.color = ok ? '#10b981' : '#f87171';
                summary.textContent = [
                    `Blender: ${data.blender_found ? 'found' : 'missing'}`,
                    `Started: ${data.blender_started ? 'yes' : 'no'}`,
                    `Plugin enabled: ${data.plugin_enabled ? 'yes' : 'no'}`,
                    `Operators: ${(data.operators || []).length}`
                ].join(' | ');
            }
            if (output) output.textContent = JSON.stringify(data, null, 2);
        } catch (error) {
            if (summary) {
                summary.style.color = '#f87171';
                summary.textContent = error.message || '诊断失败';
            }
        } finally {
            this.setButtonBusy(button, false);
        }
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
        try {
            const updated = this.scene.id ? await this.apiRequest(`/modeler/scenes/${this.scene.id}`, {
                method: 'PUT',
                body: JSON.stringify({ name: newName, status: newStatus })
            }) : null;

            if (updated && !updated.detail) {
                this.scene = { ...this.scene, ...updated };
                localStorage.setItem('smartcity_edit_scene', JSON.stringify(this.scene));
                this.updateSceneHeader();
                this.setSceneSaveStatus(`已保存到后端 ${new Date().toLocaleTimeString()}`, 'success');
                this.showMessage('场景信息已保存', 'info');
                return;
            }

            this.scene.name = newName;
            this.scene.status = newStatus;
            localStorage.setItem('smartcity_edit_scene', JSON.stringify(this.scene));
            this.updateSceneHeader();
            this.setSceneSaveStatus('后端未确认，已先保存到本地', 'warning');
        } finally {
            this.setButtonBusy(saveBtn, false);
        }
    }

    renderTemplatePresetButtons() {
        return this.templatePresets.map(template => (
            `<button class="small-btn outline template-preset-btn" data-template-preset="${template.id}" title="${this.escapeHTML(template.detail)}" style="padding: 0.3rem 0.6rem; font-size: 0.75rem;">
                ${template.id} - ${this.escapeHTML(template.name)}
            </button>`
        )).join('');
    }

    selectTemplatePreset(templateId) {
        const template = this.templatePresets.find(item => item.id === templateId);
        const input = document.getElementById('editTemplateId');
        const status = document.getElementById('generationStatus');
        if (input) input.value = templateId || '';
        document.querySelectorAll('[data-template-preset]').forEach(btn => {
            btn.classList.toggle('active', btn.getAttribute('data-template-preset') === templateId);
        });
        if (template && status) {
            status.textContent = `已选择模板 ${template.id}: ${template.name}`;
            status.style.color = '#38bdf8';
        }
    }

    addEditAsset() {
        const input = document.getElementById('editAssetSearch');
        const name = input?.value.trim();
        if (!name) {
            this.showMessage('请输入资产名称', 'error');
            return;
        }
        if (this.editAssets.some(asset => asset.toLowerCase() === name.toLowerCase())) {
            this.showMessage('该资产已添加', 'error');
            return;
        }
        this.editAssets.push(name);
        input.value = '';
        this.renderEditAssets();
        this.blenderBridge?.addAsset('model', name);
    }

    removeAssetFromClick(event) {
        const target = event.target;
        if (!(target instanceof HTMLElement)) return;
        const button = target.closest('[data-remove-asset]');
        if (!button) return;
        const index = parseInt(button.getAttribute('data-remove-asset'), 10);
        if (Number.isNaN(index)) return;
        this.editAssets.splice(index, 1);
        this.renderEditAssets();
    }

    async applyLayout() {
        const raw = document.getElementById('editLayoutInput')?.value.trim();
        const parsed = this.parseLayoutPoints(raw);
        if (!parsed.valid) {
            this.setLayoutFeedback(parsed.message, 'error');
            this.showMessage(parsed.message, 'error');
            return;
        }
        const response = await this.apiRequest('/modeler/layout/apply', {
            method: 'POST',
            body: JSON.stringify({ points: parsed.points })
        });
        if (response && !response.detail) {
            await this.blenderBridge?.applyLayout({ points: parsed.points });
            this.setLayoutFeedback(`应用成功：${parsed.points.length} 个点，${response.road_count ?? parsed.points.length - 1} 条道路。`, 'success');
        }
    }

    updateLayoutFeedback() {
        const raw = document.getElementById('editLayoutInput')?.value.trim();
        if (!raw) {
            this.setLayoutFeedback('示例：0,20;50,80;120,60', 'muted');
            return;
        }
        const parsed = this.parseLayoutPoints(raw);
        this.setLayoutFeedback(parsed.valid ? `已识别 ${parsed.points.length} 个点。` : parsed.message, parsed.valid ? 'task' : 'error');
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
        if (meta) meta.textContent = `${file.name} - ${this.formatFileSize(file.size)}`;
        if (preview) {
            preview.style.display = 'block';
            preview.innerHTML = `<img src="${this.sketchPreviewUrl}" alt="草图预览" style="max-width: 220px; max-height: 140px; border-radius: 0.5rem; border: 1px solid #334155; object-fit: cover;">`;
        }
        if (result) result.textContent = '草图已选择，可以开始处理。';
    }

    async processSketch() {
        const file = document.getElementById('editSketchUpload')?.files?.[0];
        const result = document.getElementById('sketchResult');
        if (!file) {
            this.showMessage('请先选择草图文件', 'error');
            return;
        }
        const response = await this.apiRequest('/modeler/sketch/process', {
            method: 'POST',
            body: JSON.stringify({ file_name: file.name })
        });
        if (response && !response.detail) {
            await this.blenderBridge?.processSketch(file.name);
            if (result) {
                result.textContent = `处理完成：提取 ${response.points?.length || 0} 个点，${response.road_count || 0} 条道路。`;
                result.style.color = '#10b981';
            }
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
            result.textContent = `渲染演示任务已提交（质量: ${this.renderQualityLabel(quality)}）。`;
            result.style.color = '#38bdf8';
        }
        setTimeout(() => {
            if (result) {
                result.textContent = `渲染演示完成（质量: ${this.renderQualityLabel(quality)}）。`;
                result.style.color = '#10b981';
            }
            if (downloadBtn) {
                downloadBtn.style.display = 'inline-flex';
                downloadBtn.disabled = false;
            }
            this.setButtonBusy(button, false);
        }, 900);
    }

    downloadRenderPreview() {
        const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360"><rect width="100%" height="100%" fill="#0f172a"/><text x="50%" y="50%" fill="#94a3b8" font-size="24" font-family="Arial" dominant-baseline="middle" text-anchor="middle">Render Preview</text></svg>`;
        const url = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
        const link = document.createElement('a');
        link.href = url;
        link.download = 'render_preview.svg';
        link.click();
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
        ['generate', 'diagnostics', 'assets', 'layout', 'sketch', 'render'].forEach(key => {
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

    formatTaskStatus(task) {
        const warningText = task.warnings?.length ? ` Warnings: ${task.warnings.join('; ')}` : '';
        return `Task ${task.task_id}: ${task.status}.${warningText}`;
    }

    setGenerationStatus(message, type = 'muted') {
        const status = document.getElementById('generationStatus');
        if (!status) return;
        status.textContent = message;
        status.style.color = this.feedbackColor(type);
    }

    setLayoutFeedback(message, type = 'muted') {
        const feedback = document.getElementById('layoutFeedback');
        if (!feedback) return;
        feedback.textContent = message;
        feedback.style.color = this.feedbackColor(type);
    }

    setSceneSaveStatus(message, type = 'success') {
        const status = document.getElementById('sceneSaveStatus');
        if (!status) return;
        status.textContent = message;
        status.style.color = this.feedbackColor(type);
        status.style.display = 'block';
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
        this.blenderBridge?.log?.(message, type);
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
