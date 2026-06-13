// 场景编辑页：通过后端调用 Blender 中已安装的 SCGS 插件。
class SceneEditorUI extends BaseRoleUI {
    constructor(containerId, username) {
        super(containerId, username);
        this.scene = null;
        this.editAssets = [];
        this.activeTab = 'generate';
        this.blenderBridge = window.blenderBridge;
        this.lastDownloadUrl = '';
        this.lastBlendTaskId = '';
        this.availableAssets = [];
        this.layoutPoints = [];
        this.templatePresets = [
            { id: '0', name: '现代风格', detail: '树木1 · 道路纹理2 · 座椅1' },
            { id: '1', name: '古典风格', detail: '树木2 · 道路纹理1 · 座椅2' },
            { id: '2', name: '绿色生态', detail: '树木3 · 道路纹理3 · 座椅3' },
            { id: '3', name: '工业风格', detail: '树木1 · 道路纹理4 · 座椅1' },
            { id: '4', name: '台湾风格', detail: '树木4 · 道路纹理2 · 座椅4' }
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
        this.lastBlendTaskId = this.loadSceneBlendTaskId();
        this.bindEvents();
        this.switchEditTab(this.activeTab);
        this.renderEditAssets();
        this.blenderBridge?.init('simulateOutput');
        this.loadAvailableAssets();
        this._loadPendingAssets();

        // 页面刷新后恢复未完成的生成任务轮询
        const pendingTask = sessionStorage.getItem('scgs_pending_task');
        if (pendingTask) {
            try {
                const { taskId } = JSON.parse(pendingTask);
                const progressWrap = document.getElementById('generationProgressWrap');
                const idleEl = document.getElementById('generationIdle');
                const download = document.getElementById('blendDownloadLink');
                if (progressWrap) progressWrap.style.display = 'block';
                if (idleEl) idleEl.style.display = 'none';
                if (download) download.style.display = 'none';
                this.setGenerationStatus(`页面刷新，恢复任务 ${taskId} 轮询...`, 'task');
                this._pollTaskStatus(taskId, download);
            } catch { sessionStorage.removeItem('scgs_pending_task'); }
        }
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
                            <button class="small-btn" id="generateSceneBtn"><i class="fas fa-wand-magic-sparkles"></i> 调用 SCGS 生成</button>
                        </div>
                        <div id="sceneSaveStatus" style="display: none; font-size: 0.75rem;"></div>
                    </div>
                </div>

                <div class="glass-card" style="padding: 1.5rem; margin-bottom: 1rem;">
                    <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
                        <button class="small-btn outline scene-edit-tab" data-edit-tab="generate">城市生成</button>
                        <button class="small-btn outline scene-edit-tab" data-edit-tab="edit">快捷编辑</button>
                        <button class="small-btn outline scene-edit-tab" data-edit-tab="template">模板</button>
                        <button class="small-btn outline scene-edit-tab" data-edit-tab="assets">资产</button>
                        <button class="small-btn outline scene-edit-tab" data-edit-tab="diagnostics">诊断</button>
                    </div>

                    <div id="editTab_generate" style="margin-top: 0.9rem;">
                        <!-- 第一行：自然语言描述 -->
                        <label style="display: grid; gap: 0.35rem; color: #94a3b8; font-size: 0.82rem; margin-bottom: 0.75rem;">
                            自然语言描述
                            <textarea id="generateDescription" placeholder="例如：请生成一座雨天的现代城市" style="min-height: 72px; padding: 0.6rem; border-radius: 0.5rem; background: #0f172a; border: 1px solid #334155; color: #e2e8f0; resize: vertical;"></textarea>
                            <input type="hidden" id="editTemplateId" value="">
                        </label>
                        <!-- 第二行：道路类型 + 天气 -->
                        <div style="display: flex; gap: 0.75rem; margin-bottom: 0.75rem;">
                            <label style="display: grid; gap: 0.35rem; color: #94a3b8; font-size: 0.82rem; flex: 1;">
                                道路类型
                                <select id="generateRoadType" style="padding: 0.6rem; border-radius: 0.5rem; background: #0f172a; border: 1px solid #334155; color: #e2e8f0;">
                                    <option value="1">1 - 经典网格布局</option>
                                    <option value="2" selected>2 - 扩展网格布局（默认）</option>
                                    <option value="3">3 - 图像识别提取</option>
                                    <option value="4">4 - 手动布局</option>
                                </select>
                            </label>
                        </div>
                        <!-- 手动布局（道路类型选 3/4 时显示） -->
                        <div id="generateManualSection" style="display: none; margin-bottom: 0.75rem; padding: 0.75rem; border: 1px solid #334155; border-radius: 0.5rem; background: #0f172a;">
                            <div style="font-size: 0.78rem; color: #94a3b8; margin-bottom: 0.5rem;"><i class="fas fa-pencil"></i> 手动布局</div>
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem;">
                                <label style="display: grid; gap: 0.3rem; color: #94a3b8; font-size: 0.78rem;">
                                    顶点 (Vertices)
                                    <textarea id="generateManualVertices" placeholder="(0,0,0),(50,0,0),(50,50,0),(0,50,0)" style="height: 64px; padding: 0.5rem; border-radius: 0.4rem; background: #1e293b; border: 1px solid #334155; color: #e2e8f0; font-size: 0.75rem;"></textarea>
                                </label>
                                <label style="display: grid; gap: 0.3rem; color: #94a3b8; font-size: 0.78rem;">
                                    边 (Edges)
                                    <textarea id="generateManualEdges" placeholder="(0,1),(1,2),(2,3),(3,0)" style="height: 64px; padding: 0.5rem; border-radius: 0.4rem; background: #1e293b; border: 1px solid #334155; color: #e2e8f0; font-size: 0.75rem;"></textarea>
                                </label>
                            </div>
                            <div id="generateImageTools" style="display: none; margin-top: 0.5rem; display: flex; gap: 0.5rem; align-items: center;">
                                <input type="file" id="generateImageInput" accept="image/*" style="font-size: 0.75rem; color: #94a3b8;" />
                                <button class="small-btn outline" id="generateExtractBtn" style="font-size: 0.75rem;">提取布局</button>
                                <span id="generateImageMeta" style="font-size: 0.7rem; color: #64748b;"></span>
                            </div>
                        </div>
                        <!-- 进度 + 状态 + 下载 -->
                        <div id="generationProgressWrap" style="display: none; margin-top: 0.75rem;">
                            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.4rem;">
                                <div style="flex: 1; background: #1e293b; border-radius: 0.35rem; height: 6px; overflow: hidden;">
                                    <div id="generationProgressBar" style="width: 0%; height: 100%; background: linear-gradient(90deg, #38bdf8, #a78bfa); transition: width 0.3s;"></div>
                                </div>
                                <span id="generationProgressPct" style="font-size: 0.75rem; color: #38bdf8; min-width: 38px; text-align: right;">0%</span>
                            </div>
                            <div style="display: flex; align-items: center; gap: 0.5rem;">
                                <span id="generationStatus" style="font-size: 0.75rem; color: #64748b;"></span>
                                <a id="blendDownloadLink" class="small-btn outline" style="display: none; text-decoration: none; cursor: pointer;"><i class="fas fa-download"></i> 下载 .blend</a>
                            </div>
                        </div>
                        <div id="generationIdle" style="margin-top: 0.6rem; font-size: 0.78rem; color: #64748b;">选择模板或输入描述后，点击顶部的「调用 SCGS 生成」即可。</div>
                    </div>

                    <div id="editTab_template" style="margin-top: 0.9rem; display: none;">
                        <!-- AI 指令 -->
                        <label style="display: grid; gap: 0.35rem; color: #94a3b8; font-size: 0.82rem; margin-bottom: 0.75rem;">
                            AI 自然语言指令
                            <input id="aiInstruction" placeholder="例如：树木1, 道路2, 座椅1  或  模板4  或  古典风格" style="padding: 0.6rem; border-radius: 0.5rem; background: #0f172a; border: 1px solid #334155; color: #e2e8f0;">
                        </label>
                        <!-- 模板按钮 -->
                        <div style="font-size: 0.82rem; color: #94a3b8; margin-bottom: 0.5rem;">模板预设（点击选中）</div>
                        <div style="display: flex; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 0.75rem;">
                            ${this.renderTemplatePresetButtons()}
                        </div>
                        <div style="font-size: 0.78rem; color: #64748b;">模板详情：现代（树木1·道路2·座椅1）、古典（树木2·道路1·座椅2）、生态（树木3·道路3·座椅3）、工业（树木1·道路4·座椅1）、地域（树木4·道路2·座椅4）</div>
                    </div>

                    <div id="editTab_edit" style="margin-top: 0.9rem; display: none;">
                        <label style="display: grid; gap: 0.35rem; color: #94a3b8; font-size: 0.82rem;">
                            编辑指令
                            <textarea id="editInstruction" placeholder="例如：Please change the weather to sunny." style="min-height: 64px; padding: 0.6rem; border-radius: 0.5rem; background: #0f172a; border: 1px solid #334155; color: #e2e8f0;"></textarea>
                        </label>
                        <div style="display: flex; gap: 0.5rem; flex-wrap: wrap; margin-top: 0.75rem;">
                            <button class="small-btn" id="editCityBtn"><i class="fas fa-edit"></i> 调整场景</button>
                        </div>
                        <div style="font-size: 0.78rem; color: #94a3b8; margin-top: 0.75rem;">快捷操作</div>
                        <div style="display: flex; gap: 0.4rem; flex-wrap: wrap; margin-top: 0.4rem;">
                            <button class="small-btn outline quick-edit-btn" data-edit-cmd="Please change the weather to sunny.">☀️ 晴天</button>
                            <button class="small-btn outline quick-edit-btn" data-edit-cmd="Please change the weather to rainy days.">🌧️ 雨天</button>
                            <button class="small-btn outline quick-edit-btn" data-edit-cmd="Please change the weather to snowy days.">❄️ 雪天</button>
                            <button class="small-btn outline quick-edit-btn" data-edit-cmd="adjust the scene to daytime">🌅 白天</button>
                            <button class="small-btn outline quick-edit-btn" data-edit-cmd="adjust the scene to night">🌙 夜晚</button>
                            <button class="small-btn outline quick-edit-btn" data-edit-cmd="remove weeds and small garbage from the road surface.">🧹 清洁道路</button>
                            <button class="small-btn outline quick-edit-btn" data-edit-cmd="add weeds and small garbage on the road surface.">🍂 脏污道路</button>
                        </div>
                        <div id="editStatus" style="margin-top: 0.6rem; font-size: 0.78rem; color: #64748b;">编辑指令支持天气切换、白天/夜晚、道路清洁/脏污等操作。请先完成一次 SCGS 生成，再调整生成结果。</div>
                        <div id="editProgressWrap" style="display: none; margin-top: 0.75rem;">
                            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.4rem;">
                                <div style="flex: 1; background: #1e293b; border-radius: 0.35rem; height: 6px; overflow: hidden;">
                                    <div id="editProgressBar" style="width: 0%; height: 100%; background: linear-gradient(90deg, #38bdf8, #a78bfa); transition: width 0.3s;"></div>
                                </div>
                                <span id="editProgressPct" style="font-size: 0.75rem; color: #38bdf8; min-width: 38px; text-align: right;">0%</span>
                            </div>
                            <div style="display: flex; align-items: center; gap: 0.5rem;">
                                <span id="editProgressStatus" style="font-size: 0.75rem; color: #64748b;"></span>
                                <a id="editDownloadLink" class="small-btn outline" style="display: none; text-decoration: none; cursor: pointer;"><i class="fas fa-download"></i> 下载 .blend</a>
                            </div>
                        </div>
                    </div>

                    <div id="editTab_diagnostics" style="margin-top: 0.9rem; display: none;">
                        <div id="diagnosticsSummary" style="font-size: 0.78rem; color: #94a3b8;">点击“插件诊断”检查 Blender 路径、SCGS 启用状态和 sna 候选算子。</div>
                        <pre id="diagnosticsOutput" style="margin-top: 0.75rem; max-height: 260px; overflow: auto; white-space: pre-wrap; background: #0f172a; border: 1px solid #334155; border-radius: 0.5rem; padding: 0.75rem; color: #cbd5e1;"></pre>
                    </div>

                    <div id="editTab_assets" style="margin-top: 0.9rem; display: none;">
                        <div style="display: flex; gap: 0.5rem; align-items: center; margin-bottom: 0.75rem;">
                            <button class="small-btn" id="uploadAssetBtn"><i class="fas fa-upload"></i> 上传资产</button>
                            <button class="small-btn outline" id="refreshAssetsBtn" title="刷新资产库"><i class="fas fa-sync-alt"></i></button>
                            <input id="editAssetSearch" placeholder="筛选资产..." style="flex: 1; padding: 0.5rem; border-radius: 0.5rem; background: #0f172a; border: 1px solid #334155; color: #e2e8f0;">
                        </div>
                        <div id="uploadAssetForm" style="display: none; border: 1px solid #334155; border-radius: 0.5rem; padding: 0.75rem; background: #0f172a; margin-bottom: 0.75rem;">
                            <div style="display: grid; gap: 0.55rem;">
                                <input id="uploadAssetName" placeholder="资产名称" style="padding: 0.5rem; border-radius: 0.45rem; background: #1e293b; border: 1px solid #334155; color: #e2e8f0; font-size: 0.82rem;">
                                <input id="uploadAssetType" placeholder="类型（设施、建筑、植被、道路...）" value="设施" style="padding: 0.5rem; border-radius: 0.45rem; background: #1e293b; border: 1px solid #334155; color: #e2e8f0; font-size: 0.82rem;">
                                <input id="uploadAssetIcon" placeholder="Font Awesome 图标名" value="fa-cube" style="padding: 0.5rem; border-radius: 0.45rem; background: #1e293b; border: 1px solid #334155; color: #e2e8f0; font-size: 0.82rem;">
                                <div style="display: flex; gap: 0.5rem;">
                                    <button class="small-btn" id="confirmUploadBtn"><i class="fas fa-check"></i> 确认上传</button>
                                    <button class="small-btn outline" id="cancelUploadBtn">取消</button>
                                </div>
                            </div>
                        </div>
                        <div style="font-size: 0.75rem; color: #64748b; margin-bottom: 0.35rem;">可用资产（点击添加）</div>
                        <div id="editAssetCatalog" style="max-height: 240px; overflow-y: auto; margin-bottom: 0.75rem; font-size: 0.78rem; color: #64748b;">资产库加载中...</div>
                        <div style="font-size: 0.75rem; color: #94a3b8; margin-bottom: 0.35rem;">已选资产（点击 × 移除）</div>
                        <div id="editAssetList" style="font-size: 0.75rem; color: #94a3b8;"></div>
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

        // edit tab
        document.getElementById('editCityBtn')?.addEventListener('click', () => this.editCity());
        document.querySelectorAll('[data-edit-cmd]').forEach(btn => {
            btn.addEventListener('click', () => this.quickEdit(btn.getAttribute('data-edit-cmd')));
        });

        // road type change → show/hide manual layout + image tools
        document.getElementById('generateRoadType')?.addEventListener('change', e => this.handleRoadTypeChange(e));
        document.getElementById('generateImageInput')?.addEventListener('change', e => this.handleGenerateImageChange(e));
        document.getElementById('generateExtractBtn')?.addEventListener('click', () => this.extractLayoutFromImage());

        document.getElementById('uploadAssetBtn')?.addEventListener('click', () => this.toggleUploadForm());
        document.getElementById('confirmUploadBtn')?.addEventListener('click', () => this.confirmUploadAsset());
        document.getElementById('cancelUploadBtn')?.addEventListener('click', () => this.toggleUploadForm(false));
        document.getElementById('refreshAssetsBtn')?.addEventListener('click', () => this.refreshAssets());
        document.getElementById('editAssetSearch')?.addEventListener('input', () => this.filterAssetCatalog());
        document.getElementById('editAssetCatalog')?.addEventListener('click', e => this.addAssetFromCatalog(e));
        document.getElementById('editAssetList')?.addEventListener('click', e => this.removeAssetFromClick(e));

        document.getElementById('copyLogBtn')?.addEventListener('click', () => this.copyLog());
        document.getElementById('clearLogBtn')?.addEventListener('click', () => {
            this.blenderBridge?.clearLog();
            this.logEditAction('日志已清空。', 'system');
        });
        document.getElementById('backToListBtn')?.addEventListener('click', () => { window.location.href = 'modeler.html'; });
        document.getElementById('logoutBtn')?.addEventListener('click', () => {
            new AuthManager().logout();
            window.location.href = 'index.html';
        });
        // init road type state
        const roadTypeSel = document.getElementById('generateRoadType');
        if (roadTypeSel) this.handleRoadTypeChange({ target: roadTypeSel });
    }

    handleRoadTypeChange(event) {
        const target = event.target;
        if (!(target instanceof HTMLSelectElement)) return;
        const manualSection = document.getElementById('generateManualSection');
        const imageTools = document.getElementById('generateImageTools');
        if (!manualSection) return;
        const showManual = target.value === '3' || target.value === '4';
        manualSection.style.display = showManual ? 'block' : 'none';
        if (imageTools) {
            imageTools.style.display = target.value === '3' ? 'flex' : 'none';
        }
    }

    handleGenerateImageChange(event) {
        const target = event.target;
        if (!(target instanceof HTMLInputElement)) return;
        const meta = document.getElementById('generateImageMeta');
        const file = target.files?.[0];
        if (!meta) return;
        if (!file) {
            meta.textContent = '';
            return;
        }
        meta.textContent = `${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
    }

    extractLayoutFromImage() {
        const file = document.getElementById('generateImageInput')?.files?.[0];
        if (!file) {
            this.showMessage('请先选择图片', 'error');
            return;
        }
        const verticesInput = document.getElementById('generateManualVertices');
        const edgesInput = document.getElementById('generateManualEdges');
        if (!verticesInput || !edgesInput) return;

        verticesInput.value = '(0,0,0),(50,0,0),(50,50,0),(0,50,0)';
        edgesInput.value = '(0,1),(1,2),(2,3),(3,0)';
        this.showMessage('已根据图片提取道路布局（演示）', 'info');
    }

    async editCity() {
        const instruction = document.getElementById('editInstruction')?.value.trim();
        const button = document.getElementById('editCityBtn');
        const download = document.getElementById('editDownloadLink');
        const progressWrap = document.getElementById('editProgressWrap');
        if (!instruction) {
            this.showMessage('请输入编辑指令', 'error');
            return;
        }

        const sourceTaskId = this.getEditableBlendTaskId();
        if (!sourceTaskId) {
            this.setEditStatus('请先完成一次 SCGS 生成任务，再调整生成结果。', 'error');
            this.showMessage('请先生成场景，再调整场景', 'error');
            return;
        }

        this.setButtonBusy(button, true, '<i class="fas fa-spinner fa-pulse"></i> 调整中');
        this.logEditAction(`[system] 调整任务提交中，源任务: ${sourceTaskId}`, 'task');
        this._setEditProgress(0);
        if (progressWrap) progressWrap.style.display = 'block';
        if (download) download.style.display = 'none';

        try {
            const result = await this.apiRequest('/blender/edit', {
                method: 'POST',
                body: JSON.stringify({
                    source_task_id: sourceTaskId,
                    instruction,
                    description: instruction,
                    scene_id: this.scene.id || null
                })
            });

            if (!result || result.detail) {
                throw new Error(result?.detail || '场景调整接口调用失败');
            }

            const taskId = result.task_id;
            this.logEditAction(`[system] 调整任务 ${taskId} 已启动`, 'task');
            await this._pollEditTaskStatus(taskId, result.download_url, download);
            this.showMessage('场景调整完成', 'info');
        } catch (error) {
            this._setEditProgress(0);
            const errorMessage = error.message || '场景调整失败';
            if (errorMessage.startsWith('TASK_NOT_FOUND:')) {
                this.setEditProgressStatus(errorMessage.replace('TASK_NOT_FOUND:', ''), 'error');
            } else {
                this.setEditProgressStatus(errorMessage, 'error');
                this.setEditStatus(errorMessage, 'error');
            }
            this.showMessage('场景调整失败', 'error');
        } finally {
            this.setButtonBusy(button, false);
        }
    }

    quickEdit(cmd) {
        const input = document.getElementById('editInstruction');
        if (input) input.value = cmd;
        this.editCity();
    }

    collectGenerationParams() {
        const manualVertices = document.getElementById('generateManualVertices')?.value.trim() || '';
        const manualEdges = document.getElementById('generateManualEdges')?.value.trim() || '';

        return {
            scene_id: this.scene.id || null,
            city_name: document.getElementById('editSceneName')?.value.trim() || this.scene.name || '',
            description: document.getElementById('generateDescription')?.value.trim() || '',
            template_id: document.getElementById('editTemplateId')?.value.trim() || '',
            road_type: document.getElementById('generateRoadType')?.value || '2',
            weather: document.getElementById('generateWeather')?.value || '',
            manual_vertices: manualVertices,
            manual_edges: manualEdges,
            style: document.getElementById('generateStyle')?.value.trim() || 'default',
            scale: Number(document.getElementById('generateScale')?.value || 1),
            selected_assets: this.editAssets.map(a => this.assetPayload(a))
        };
    }

    async generateScene() {
        const button = document.getElementById('generateSceneBtn');
        const statusEl = document.getElementById('generationStatus');
        const progressWrap = document.getElementById('generationProgressWrap');
        const idleEl = document.getElementById('generationIdle');
        const download = document.getElementById('blendDownloadLink');
        const params = this.collectGenerationParams();
        if (!params.description) {
            this.showMessage('请填写自然语言描述', 'error');
            return;
        }

        console.log('[generateScene] 开始生成，参数:', params);
        this.setButtonBusy(button, true, '<i class="fas fa-spinner fa-pulse"></i> 生成中');
        if (download) download.style.display = 'none';
        if (idleEl) idleEl.style.display = 'none';
        if (progressWrap) progressWrap.style.display = 'block';
        this._setProgress(0);
        this.logEditAction('[system] 生成任务已提交至后端，等待 Blender 返回状态...', 'task');

        try {
            // 优先调用后端 API
            const result = await this.apiRequest('/blender/generate', {
                method: 'POST',
                body: JSON.stringify(params)
            });

            if (!result || result.detail) {
                throw new Error(result?.detail || '后端不可用');
            }

            const taskId = result.task_id;
            this.logEditAction(`[system] 生成任务 ${taskId} 已启动`, 'task');

            // 轮询状态（2s 间隔，最多 120s）
            await this._pollTaskStatus(taskId, download);
            this.showMessage('SCGS 生成完成', 'info');
        } catch (error) {
            this.setGenerationStatus(error.message || '生成失败', 'error');
            this.showMessage('SCGS 生成失败', 'error');
        } finally {
            this.setButtonBusy(button, false);
        }
    }

    async _pollTaskStatus(taskId, downloadEl, intervalMs = 2000, maxRetries = 60) {
        for (let i = 0; i < maxRetries; i++) {
            await new Promise(resolve => setTimeout(resolve, intervalMs));

            const statusData = await this.apiRequest(`/blender/status/${taskId}`);
            console.log(`[poll] 第${i+1}次:`, statusData);
            if (!statusData) {
                this.setGenerationStatus(`轮询 ${taskId} 失败（第 ${i + 1} 次）`, 'error');
                continue;
            }

            const taskStatus = statusData.status;
            if (taskStatus === 'completed') {
                this.rememberBlendTaskId(taskId);
                sessionStorage.removeItem('scgs_pending_task');
                this._setProgress(100);
                // 后端返回相对路径，用 taskId 拼
                const dl = statusData.download_url || `/blender/download/${taskId}`;
                this.lastDownloadUrl = this.resolveBackendUrl(dl);
                this.setGenerationStatus(`生成完成！`, 'success');
                if (downloadEl) {
                    downloadEl.href = this.lastDownloadUrl;
                    downloadEl.style.display = 'inline-flex';
                    downloadEl.innerHTML = '<i class="fas fa-download"></i> 下载 .blend';
                    // 点击时在新标签打开下载
                    downloadEl.onclick = (e) => {
                        e.preventDefault();
                        window.open(this.lastDownloadUrl, '_blank');
                    };
                }
                return;
            }

            if (taskStatus === 'failed') {
                sessionStorage.removeItem('scgs_pending_task');
                this._setProgress(0);
                throw new Error(statusData.error || 'Blender 任务执行失败');
            }

            // 仍在 processing — 进度基于轮询次数估算（最多到 90%）
            const pct = Math.min(Math.floor(((i + 1) / maxRetries) * 90), 90);
            this._setProgress(pct);
            const warnings = statusData.warnings?.length ? ` ⚠${statusData.warnings.length}` : '';
            this.setGenerationStatus(`Blender 生成中…（${pct}%）${warnings}`, 'task');
        }
        throw new Error(`生成超时：${maxRetries * intervalMs / 1000} 秒未完成`);
    }

    _setProgress(pct) {
        const bar = document.getElementById('generationProgressBar');
        const label = document.getElementById('generationProgressPct');
        if (bar) bar.style.width = `${pct}%`;
        if (label) label.textContent = `${pct}%`;
    }

    _setEditProgress(pct) {
        const bar = document.getElementById('editProgressBar');
        const label = document.getElementById('editProgressPct');
        if (bar) bar.style.width = `${pct}%`;
        if (label) label.textContent = `${pct}%`;
    }

    setEditProgressStatus(message, type = 'muted') {
        const status = document.getElementById('editProgressStatus');
        if (!status) return;
        status.textContent = message;
        status.style.color = this.feedbackColor(type);
    }

    async _pollEditTaskStatus(taskId, downloadUrl, downloadEl, intervalMs = 2000, maxRetries = 60) {
        for (let i = 0; i < maxRetries; i++) {
            await new Promise(resolve => setTimeout(resolve, intervalMs));

            const statusData = await this.apiRequest(`/blender/status/${taskId}`);
            if (!statusData) {
                this.setEditProgressStatus(`轮询 ${taskId} 失败（第 ${i + 1} 次）`, 'error');
                continue;
            }

            if (statusData.status === 'not_found') {
                this._setEditProgress(0);
                const notFoundMessage = statusData.error || '场景调整任务不存在';
                const progressWrap = document.getElementById('editProgressWrap');
                if (progressWrap) progressWrap.style.display = 'none';
                this.setEditProgressStatus(notFoundMessage, 'error');
                throw new Error(`TASK_NOT_FOUND:${notFoundMessage}`);
            }

            const taskStatus = statusData.status;
            if (taskStatus === 'completed') {
                this.rememberBlendTaskId(taskId);
                this.lastDownloadUrl = this.resolveBackendUrl(statusData.download_url || downloadUrl || `/blender/download/${taskId}`);
                this._setEditProgress(100);
                this.setEditProgressStatus('场景调整完成', 'success');
                if (downloadEl && this.lastDownloadUrl) {
                    downloadEl.href = this.lastDownloadUrl;
                    downloadEl.style.display = 'inline-flex';
                    downloadEl.innerHTML = '<i class="fas fa-download"></i> 下载 .blend';
                    downloadEl.onclick = (e) => {
                        e.preventDefault();
                        window.open(this.lastDownloadUrl, '_blank');
                    };
                }
                return;
            }

            if (taskStatus === 'failed') {
                this._setEditProgress(0);
                this.setEditProgressStatus(statusData.error || '场景调整任务执行失败', 'error');
                throw new Error(statusData.error || '场景调整任务执行失败');
            }

            const warnings = statusData.warnings?.length ? ` ⚠ ${statusData.warnings.length}` : '';
            const pct = Math.min(Math.floor(((i + 1) / maxRetries) * 90), 90);
            this._setEditProgress(pct);
            this.setEditProgressStatus(`场景调整中…（${pct}%）${warnings}`, 'task');
        }
        throw new Error(`调整任务 ${taskId} 超时：轮询 ${maxRetries} 次后仍未完成`);
    }

    async runDiagnostics() {
        this.switchEditTab('diagnostics');
        const button = document.getElementById('runDiagnosticsBtn');
        const summary = document.getElementById('diagnosticsSummary');
        const output = document.getElementById('diagnosticsOutput');
        this.setButtonBusy(button, true, '<i class="fas fa-spinner fa-pulse"></i> 诊断中');
        if (summary) summary.textContent = '正在启动 Blender 进行诊断...';
        if (output) output.textContent = '';

        const renderDiagnostics = (data, source = '') => {
            const ok = data.blender_started && !data.error;
            const sourceLabel = source ? ` [${source}]` : '';
            if (summary) {
                summary.style.color = ok ? '#10b981' : '#f87171';
                summary.textContent = [
                    `Blender: ${data.blender_found ? 'found' : 'missing'}`,
                    `Started: ${data.blender_started ? 'yes' : 'no'}`,
                    `Plugin enabled: ${data.plugin_enabled ? 'yes' : 'no'}`,
                    `Operators: ${(data.operators || []).length}`
                ].join(' | ') + sourceLabel;
            }
            if (output) output.textContent = JSON.stringify(data, null, 2);
        };

        try {
            // 优先调用后端诊断 API
            const backendData = await this.apiRequest('/blender/diagnostics');
            if (backendData && !backendData.detail) {
                renderDiagnostics(backendData, 'backend');
                this.logEditAction('[system] Blender bridge ready.', 'system');
                return;
            }
            throw new Error('后端返回异常');
        } catch (error) {
            if (summary) {
                summary.style.color = '#f87171';
                summary.textContent = error.message || '诊断失败';
            }
            this.logEditAction('[system] Blender bridge 诊断失败。', 'error');
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
        const hidden = document.getElementById('editTemplateId');
        const isCurrentlySelected = hidden && hidden.value === templateId;

        if (isCurrentlySelected) {
            // 取消选中
            if (hidden) hidden.value = '';
            document.querySelectorAll('[data-template-preset]').forEach(btn => {
                btn.classList.remove('active');
            });
            this.setGenerationStatus('已取消模板选择', 'muted');
            return;
        }

        // 选中
        if (hidden) hidden.value = templateId || '';
        document.querySelectorAll('[data-template-preset]').forEach(btn => {
            btn.classList.toggle('active', btn.getAttribute('data-template-preset') === templateId);
        });

        const template = this.templatePresets.find(item => item.id === templateId);
        if (template) {
            this.setGenerationStatus(`已选择模板 ${template.id}: ${template.name}（${template.detail}）`, 'success');
        }
    }

    addEditAsset() {
        const input = document.getElementById('editAssetSearch');
        const name = input?.value.trim();
        if (!name) {
            this.showMessage('请输入资产名称', 'error');
            return;
        }
        const asset = this.findAssetByName(name);
        if (!asset) {
            this.showMessage('资产库中未找到该资产', 'error');
            return;
        }
        this.addAssetToSelection(asset);
        input.value = '';
    }

    addAssetFromCatalog(event) {
        const target = event.target;
        if (!(target instanceof HTMLElement)) return;
        const item = target.closest('[data-asset-id]');
        if (!item) return;
        const asset = this.availableAssets.find(candidate => String(candidate.id) === item.getAttribute('data-asset-id'));
        if (asset) this.addAssetToSelection(asset);
    }

    addAssetToSelection(asset) {
        if (this.editAssets.some(item => String(item.id) === String(asset.id) || item.name.toLowerCase() === asset.name.toLowerCase())) {
            this.showMessage('该资产已添加', 'error');
            return;
        }
        this.editAssets.push(asset);
        this.renderEditAssets();
        this.renderAssetCatalog(document.getElementById('editAssetSearch')?.value || '');
        this.blenderBridge?.addAsset(asset.plugin_type || asset.type || 'model', asset.plugin_name || asset.name);
        this.showMessage('资产已选择并加入生成参数', 'info');
    }

    _loadPendingAssets() {
        try {
            const raw = localStorage.getItem('smartcity_pending_assets');
            if (!raw) return;
            const pending = JSON.parse(raw);
            if (!Array.isArray(pending) || pending.length === 0) return;
            pending.forEach(asset => this.addAssetToSelection(asset));
            localStorage.removeItem('smartcity_pending_assets');
            this.showMessage(`已从建模师导入 ${pending.length} 个待选资产`, 'info');
        } catch { /* ignore */ }
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
        this.renderAssetCatalog(document.getElementById('editAssetSearch')?.value || '');
    }

    toggleUploadForm(show = true) {
        const form = document.getElementById('uploadAssetForm');
        if (form) form.style.display = show ? 'block' : 'none';
    }

    async confirmUploadAsset() {
        const nameInput = document.getElementById('uploadAssetName');
        const typeInput = document.getElementById('uploadAssetType');
        const iconInput = document.getElementById('uploadAssetIcon');
        const assetName = nameInput?.value.trim();
        if (!assetName) {
            this.showMessage('请输入资产名称', 'error');
            return;
        }
        const assetType = typeInput?.value.trim() || '设施';
        const assetIcon = iconInput?.value.trim() || 'fa-cube';

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
                this.availableAssets.unshift(response.asset);
                this.renderAssetCatalog(document.getElementById('editAssetSearch')?.value || '');
                if (nameInput) nameInput.value = '';
                if (typeInput) typeInput.value = '设施';
                if (iconInput) iconInput.value = 'fa-cube';
                this.toggleUploadForm(false);
                this.showMessage(`资产「${assetName}」已创建`, 'success');
            } else {
                this.showMessage(response?.detail || '资产创建失败', 'error');
            }
        } catch (error) {
            console.error('Asset upload failed', error);
            this.showMessage('资产创建失败', 'error');
        }
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
        ['generate', 'edit', 'template', 'diagnostics', 'assets'].forEach(key => {
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
        list.innerHTML = this.editAssets.map((asset, idx) => (
            `<span class="scene-asset-tag">
                <i class="fas ${asset.icon || 'fa-cube'}"></i>
                ${this.escapeHTML(asset.name)}
                <button type="button" data-remove-asset="${idx}" aria-label="移除资产 ${this.escapeHTML(asset.name)}"><i class="fas fa-times"></i></button>
            </span>`
        )).join('');
    }

    async loadAvailableAssets() {
        const catalog = document.getElementById('editAssetCatalog');
        if (catalog) catalog.textContent = '资产库加载中...';
        try {
            const response = await this.apiRequest('/modeler/assets', { method: 'GET' });
            if (response && !response.detail) {
                this.availableAssets = Array.isArray(response) ? response : [];
                this.renderAssetCatalog();
            } else if (catalog) {
                catalog.textContent = response?.detail || '资产库加载失败';
            }
        } catch (error) {
            console.error('加载资产库失败', error);
            if (catalog) catalog.textContent = '资产库加载失败';
        }
    }

    renderAssetCatalog(filterText = '') {
        const catalog = document.getElementById('editAssetCatalog');
        if (!catalog) return;
        if (this.availableAssets.length === 0) {
            catalog.innerHTML = '<div style="color: #64748b; padding: 0.5rem;">资产库为空，可点击「上传资产」新增。</div>';
            return;
        }
        const lowerFilter = filterText.toLowerCase();
        const filtered = lowerFilter
            ? this.availableAssets.filter(a =>
                (a.name || '').toLowerCase().includes(lowerFilter) ||
                (a.plugin_name || '').toLowerCase().includes(lowerFilter) ||
                (a.type || '').toLowerCase().includes(lowerFilter))
            : this.availableAssets;
        if (filtered.length === 0) {
            catalog.innerHTML = '<div style="color: #64748b; padding: 0.5rem;">无匹配资产</div>';
            return;
        }
        const addedIds = new Set(this.editAssets.map(a => String(a.id)));
        catalog.innerHTML = filtered.map(asset => {
            const alreadyAdded = addedIds.has(String(asset.id));
            return `<div class="asset-catalog-row" data-asset-id="${this.escapeHTML(asset.id)}" style="display: flex; align-items: center; justify-content: space-between; padding: 0.45rem 0.6rem; border-radius: 0.35rem; cursor: ${alreadyAdded ? 'default' : 'pointer'}; transition: background 0.15s; ${alreadyAdded ? 'opacity: 0.5;' : ''} border-bottom: 1px solid #1e293b;">
                <span style="flex: 1; min-width: 0;">
                    <i class="fas ${asset.icon || 'fa-cube'}" style="color: #38bdf8; width: 1.2rem; text-align: center;"></i>
                    <span style="color: #e2e8f0;">${this.escapeHTML(asset.name)}</span>
                    <span style="color: #64748b; font-size: 0.68rem; margin-left: 0.35rem;">${this.escapeHTML(asset.type || asset.plugin_type || '')}</span>
                </span>
                ${alreadyAdded
                    ? '<span style="color: #22c55e; font-size: 0.7rem;">已添加</span>'
                    : '<i class="fas fa-plus-circle" style="color: #38bdf8; flex-shrink: 0;"></i>'}
            </div>`;
        }).join('');
    }

    filterAssetCatalog() {
        const input = document.getElementById('editAssetSearch');
        this.renderAssetCatalog(input?.value || '');
    }

    async refreshAssets() {
        await this.loadAvailableAssets();
        this.showMessage('资产库已刷新', 'info');
    }

    findAssetByName(name) {
        const lowerName = name.toLowerCase();
        return this.availableAssets.find(asset =>
            asset.name?.toLowerCase() === lowerName ||
            asset.plugin_name?.toLowerCase() === lowerName
        );
    }

    assetPayload(asset) {
        return {
            id: asset.id,
            name: asset.name,
            plugin_name: asset.plugin_name || asset.name,
            plugin_type: asset.plugin_type || asset.type || 'model',
            material_target: asset.material_target || null
        };
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

    setEditStatus(message, type = 'muted') {
        const status = document.getElementById('editStatus');
        if (!status) return;
        status.textContent = message;
        status.style.color = this.feedbackColor(type);
    }

    setSceneSaveStatus(message, type = 'success') {
        const status = document.getElementById('sceneSaveStatus');
        if (!status) return;
        status.textContent = message;
        status.style.color = this.feedbackColor(type);
        status.style.display = 'block';
    }

    sceneBlendTaskStorageKey() {
        const sceneKey = this.scene?.id || this.scene?.name || 'current';
        return `smartcity_scene_${sceneKey}_blend_task`;
    }

    loadSceneBlendTaskId() {
        return localStorage.getItem(this.sceneBlendTaskStorageKey()) || this.scene?.blenderTaskId || '';
    }

    rememberBlendTaskId(taskId) {
        if (!taskId) return;
        this.lastBlendTaskId = taskId;
        this.scene.blenderTaskId = taskId;
        localStorage.setItem(this.sceneBlendTaskStorageKey(), taskId);
        localStorage.setItem('smartcity_edit_scene', JSON.stringify(this.scene));
    }

    getEditableBlendTaskId() {
        return this.lastBlendTaskId || this.loadSceneBlendTaskId();
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

    resolveBackendUrl(url) {
        if (!url) return '';
        if (/^https?:\/\//i.test(url)) return url;
        return `http://127.0.0.1:8000${url.startsWith('/') ? url : `/${url}`}`;
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
