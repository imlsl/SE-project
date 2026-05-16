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

    log(message) {
        if (this.outputElement) {
            const timestamp = new Date().toLocaleTimeString();
            this.outputElement.innerHTML += `<div style="color: #a78bfa;">[${timestamp}] ${message}</div>`;
            this.outputElement.scrollTop = this.outputElement.scrollHeight;
        }
        console.log('[Blender]', message);
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
                        this.log(`任务状态: ${statusData.status}`);
                        if (statusData.status === 'completed') {
                            this.log(`模板 ${templateId} 应用完成，场景已更新 (下载链接: ${statusData.download_url})`);
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

    processLLMCommand(command) {
        this.log(`LLM指令: "${command}"`);
        this.log(`解析自然语言...`);
        
        // 简单的命令解析示例
        setTimeout(() => {
            if (command.includes('道路') || command.includes('路')) {
                this.log(`识别到道路生成需求，自动添加道路纹理资产`);
            } else if (command.includes('路灯') || command.includes('灯')) {
                this.log(`识别到路灯需求，添加3D路灯模型`);
            } else if (command.includes('建筑') || command.includes('楼')) {
                this.log(`识别到建筑需求，生成建筑群`);
            } else {
                this.log(`未能识别具体指令，请尝试更详细的描述`);
            }
            this.log(`LLM处理完成`);
        }, 1000);
        
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
window.blenderBridge = null;