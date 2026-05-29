// Blender插件桥接模块 - 模拟与Blender插件的通信
class BlenderBridge {
    constructor() {
        this.isConnected = false;
        this.outputElement = null;
    }

    init(outputElementId) {
        this.outputElement = document.getElementById(outputElementId);
        this.log('Blender 插件桥接已初始化');
    }

    log(message, type = 'system') {
        if (this.outputElement) {
            const timestamp = new Date().toLocaleTimeString();
            const colorMap = {
                system: '#a78bfa',
                task: '#38bdf8',
                success: '#10b981',
                warning: '#f59e0b',
                error: '#f87171'
            };
            const color = colorMap[type] || colorMap.system;
            const safeMessage = this.escapeHTML(message);
            this.outputElement.innerHTML += `<div style="color: ${color};">[${timestamp}] ${safeMessage}</div>`;
            this.outputElement.scrollTop = this.outputElement.scrollHeight;
        }
        console.log('[Blender]', message);
    }

    escapeHTML(value) {
        return String(value)
            .replaceAll('&', '&amp;')
            .replaceAll('<', '&lt;')
            .replaceAll('>', '&gt;')
            .replaceAll('"', '&quot;')
            .replaceAll("'", '&#39;');
    }

    clearLog() {
        if (this.outputElement) {
            this.outputElement.innerHTML = '';
        }
    }

    addAsset(assetType, assetName) {
        this.log(`添加资产: ${assetName || assetType}`);
        this.log(`同步到Blender场景...`);
        // 模拟异步操作
        setTimeout(() => {
            this.log(`资产 "${assetName || assetType}" 已成功添加到3D场景`);
        }, 500);
        return true;
    }

    async applyTemplate(templateId) {
        this.log(`应用模板: ${templateId}`);
        this.log(`联系后端生成城市布局...`);
        try {
            const response = await fetch('http://127.0.0.1:8000/blender/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    city_name: templateId, 
                    scale: 1.0, 
                    style: 'default'
                })
            });
            if (response.ok) {
                const data = await response.json();
                this.log(`后端已接受任务，Task ID: ${data.task_id}`);
                
                // 轮询检查任务状态
                const checkStatus = async () => {
                    const statusRes = await fetch(`http://127.0.0.1:8000/blender/status/${data.task_id}`);
                    if (statusRes.ok) {
                        const statusData = await statusRes.json();
                        this.log(`任务状态: ${statusData.status}`, statusData.status === 'failed' ? 'error' : 'task');
                        if (statusData.status === 'completed') {
                            this.log(`模板 ${templateId} 应用完成，场景已更新 (下载链接: ${statusData.download_url})`, 'success');
                        } else if (statusData.status === 'failed') {
                            this.log(`模板 ${templateId} 应用失败: ${statusData.error || 'Blender 任务失败'}`, 'error');
                        } else {
                            setTimeout(checkStatus, 1500);
                        }
                    }
                };
                setTimeout(checkStatus, 1000);
            } else {
                this.log(`发生错误: 请求后端失败`);
            }
        } catch (e) {
            this.log(`后端网络错误, 使用降级逻辑...`);
            setTimeout(() => {
                this.log(`模板 ${templateId} 降级应用完成，场景已更新`);
            }, 800);
        }
        return true;
    }

    async applyLayout(layoutData) {
        this.log(`应用布局: ${JSON.stringify(layoutData)}`);
        this.log('生成道路/节点并同步到场景...');
        // 模拟后端处理
        setTimeout(() => {
            this.log('布局应用完成，场景道路与节点已更新');
        }, 800);
        return true;
    }

    async processSketch(fileName) {
        this.log(`处理草图文件: ${fileName}`);
        this.log('尝试从草图中提取点集与道路线...');
        // 模拟提取结果
        setTimeout(() => {
            const points = [{x:10,y:20},{x:50,y:80},{x:120,y:60}];
            this.log(`草图提取完成: 点集(${points.length})，已应用到布局`);
        }, 1000);
        return true;
    }

    async processLLMCommand(command) {
        this.log(`LLM指令: "${command}"`);
        this.log(`联系后端发送AI生成指令...`);
        try {
            const response = await fetch('http://127.0.0.1:8000/blender/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    instruction: command
                })
            });
            if (response.ok) {
                const data = await response.json();
                this.log(`后端已接受AI生成任务，Task ID: ${data.task_id}`);
                
                const checkStatus = async () => {
                    const statusRes = await fetch(`http://127.0.0.1:8000/blender/status/${data.task_id}`);
                    if (statusRes.ok) {
                        const statusData = await statusRes.json();
                        this.log(`任务状态: ${statusData.status}`, statusData.status === 'failed' ? 'error' : 'task');
                        if (statusData.status === 'completed') {
                            this.log(`AI指令执行完成，模型已生成 (下载链接: ${statusData.download_url})`, 'success');
                        } else if (statusData.status === 'failed') {
                            this.log(`AI指令执行失败: ${statusData.error || 'Blender 任务失败'}`, 'error');
                        } else {
                            setTimeout(checkStatus, 1500);
                        }
                    }
                };
                setTimeout(checkStatus, 1000);
            } else {
                this.log(`发生错误: 请求后端失败`);
            }
        } catch (e) {
            this.log(`后端网络错误, 无法执行指令: ${e}`);
        }
        return true;
    }

    showPanel() {
        const panel = document.getElementById('blenderSimulatePanel');
        if (panel) {
            panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
            this.log('插件面板已' + (panel.style.display === 'block' ? '打开' : '关闭'));
        }
    }
}

// 全局单例
window.blenderBridge = new BlenderBridge();
