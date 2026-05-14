// js/roles/scene-modeler.js - 最小化版本
class SceneModelerUI extends BaseRoleUI {
    render() {
        if (!this.container) return;

        this.container.innerHTML = `
            <div class="role-panel" style="display:flex; gap:1rem;">
                <div style="width:280px;">
                    <div class="glass-card" style="padding:1rem; margin-bottom:1rem;">
                        <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.5rem;">
                            <input id="sm_asset_search" placeholder="搜索资产" style="flex:1; padding:0.4rem; background:#0f172a; border:1px solid #334155; color:#e2e8f0; border-radius:6px;">
                            <button class="small-btn outline" id="sm_add_texture">+2D</button>
                        </div>
                        <div style="max-height:320px; overflow:auto;">
                            <ul id="sm_asset_list" style="list-style:none; padding-left:0; margin:0;">
                                <li style="padding:0.5rem; border-bottom:1px solid #1e293b;">道路纹理 (texture_roads)</li>
                                <li style="padding:0.5rem; border-bottom:1px solid #1e293b;">3D 路灯 (lamp_model)</li>
                                <li style="padding:0.5rem; border-bottom:1px solid #1e293b;">长椅 (bench_model)</li>
                            </ul>
                        </div>
                    </div>

                    <div class="glass-card" style="padding:1rem;">
                        <div style="display:flex; gap:0.5rem; align-items:center; margin-bottom:0.5rem;">
                            <input id="sm_template_input" placeholder="模板 ID (例如 0)" style="flex:1; padding:0.4rem; background:#0f172a; border:1px solid #334155; color:#e2e8f0; border-radius:6px;">
                            <button class="small-btn" id="sm_apply_template">应用</button>
                        </div>
                        <div style="margin-top:0.5rem; display:flex; gap:0.5rem;">
                            <button class="small-btn outline" id="sm_add_3d">添加 3D 资产</button>
                            <button class="small-btn outline" id="sm_send_blender">发送到 Blender</button>
                        </div>
                        <div style="margin-top:0.75rem;">
                            <input id="sm_llm_cmd" placeholder="自然语言指令，例如：添加路灯" style="width:100%; padding:0.4rem; background:#0f172a; border:1px solid #334155; color:#e2e8f0; border-radius:6px; margin-top:0.5rem;">
                            <button class="small-btn" id="sm_run_llm" style="margin-top:0.5rem; width:100%;">解析并执行</button>
                        </div>
                    </div>
                </div>

                <div style="flex:1;">
                    <div class="glass-card" style="padding:1rem; min-height:420px; display:flex; flex-direction:column;">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
                            <div class="panel-title"><i class="fas fa-cube"></i> 场景预览</div>
                            <div style="color:#94a3b8; font-size:0.85rem;">预览区（占位）</div>
                        </div>
                        <div id="sm_3d_preview" style="flex:1; background:#07102a; border-radius:8px; display:flex; align-items:center; justify-content:center; color:#94a3b8;">
                            <div style="text-align:center;">
                                <div style="font-size:1.25rem;">3D 预览占位</div>
                                <div style="font-size:0.85rem; color:#94a3b8; margin-top:0.5rem;">（实际集成 Blender 时在此嵌入或对接）</div>
                            </div>
                        </div>
                        <div style="margin-top:0.75rem; display:flex; gap:0.5rem;">
                            <button class="small-btn" id="sm_sim_add_roadtex">添加道路纹理</button>
                            <button class="small-btn" id="sm_sim_add_lamp">添加 3D 路灯</button>
                            <button class="small-btn outline" id="sm_sim_template0">应用模板 0</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        this.bindEvents();
    }

    bindEvents() {
        const search = document.getElementById('sm_asset_search');
        if (search) {
            search.addEventListener('input', (e) => {
                const q = e.target.value.toLowerCase();
                document.querySelectorAll('#sm_asset_list li').forEach(li => {
                    li.style.display = li.textContent.toLowerCase().includes(q) ? '' : 'none';
                });
            });
        }

        const add3dBtn = document.getElementById('sm_add_3d');
        if (add3dBtn) add3dBtn.addEventListener('click', () => this.showMessage('请使用“添加 3D 资产”功能上传或选择模型（示例）', 'info'));

        const sendBlenderBtn = document.getElementById('sm_send_blender');
        if (sendBlenderBtn) sendBlenderBtn.addEventListener('click', () => {
            if (window.blenderBridge) {
                window.blenderBridge.showPanel();
                this.showMessage('已尝试打开 Blender 插件面板（模拟）', 'info');
            } else {
                this.showMessage('Blender 桥接未初始化', 'error');
            }
        });

        const simRoad = document.getElementById('sm_sim_add_roadtex');
        if (simRoad) simRoad.addEventListener('click', () => window.blenderBridge && window.blenderBridge.addAsset('texture', '道路纹理'));

        const simLamp = document.getElementById('sm_sim_add_lamp');
        if (simLamp) simLamp.addEventListener('click', () => window.blenderBridge && window.blenderBridge.addAsset('model', '3D路灯'));

        const simTemplate0 = document.getElementById('sm_sim_template0');
        if (simTemplate0) simTemplate0.addEventListener('click', () => window.blenderBridge && window.blenderBridge.applyTemplate('城市基础模板_v0'));

        const applyTemplate = document.getElementById('sm_apply_template');
        if (applyTemplate) applyTemplate.addEventListener('click', () => {
            const id = document.getElementById('sm_template_input').value.trim();
            if (!id) return this.showMessage('请输入模板 ID', 'error');
            if (window.blenderBridge) {
                window.blenderBridge.applyTemplate('模板_' + id);
                this.showMessage('模板已应用（模拟）', 'info');
            }
        });

        const runLLM = document.getElementById('sm_run_llm');
        if (runLLM) runLLM.addEventListener('click', () => {
            const cmd = document.getElementById('sm_llm_cmd').value.trim();
            if (!cmd) return this.showMessage('请输入自然语言指令', 'error');
            if (window.blenderBridge) {
                window.blenderBridge.processLLMCommand(cmd);
                this.showMessage('LLM 指令已发送（模拟）', 'info');
            }
        });
    }
}