// 连接后端与 Blender 中已安装的 SCGS 插件。
class BlenderBridge {
    constructor() {
        this.baseUrl = 'http://127.0.0.1:8000';
        this.outputElement = null;
        this.lastCompletedTask = null;
    }

    init(outputElementId) {
        this.outputElement = document.getElementById(outputElementId);
        this.log('SCGS 插件桥接已就绪。');
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
            this.outputElement.innerHTML += `<div style="color: ${color};">[${timestamp}] ${this.escapeHTML(message)}</div>`;
            this.outputElement.scrollTop = this.outputElement.scrollHeight;
        }
        console.log('[Blender]', message);
    }

    clearLog() {
        if (this.outputElement) this.outputElement.innerHTML = '';
    }

    async diagnostics() {
        this.log('正在诊断 Blender/SCGS 插件...', 'task');
        const response = await fetch(`${this.baseUrl}/blender/diagnostics`);
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || '诊断请求失败');
        }
        if (data.error) {
            this.log(`诊断错误: ${data.error}`, 'error');
        } else {
            this.log(`诊断完成。发现算子数: ${(data.operators || []).length}`, 'success');
        }
        return data;
    }

    async generateScene(parameters, callbacks = {}) {
        this.log('正在提交 SCGS 生成任务...', 'task');
        const response = await fetch(`${this.baseUrl}/blender/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(parameters)
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || '生成请求失败');
        }

        const statusUrl = data.status_url ? this.normalizeUrl(data.status_url) : `${this.baseUrl}/blender/status/${data.task_id}`;
        this.log(`后端已接受任务: ${data.task_id}`, 'task');
        callbacks.onStart?.(data);
        return this.pollTask(data.task_id, statusUrl, callbacks);
    }

    async pollTask(taskId, statusUrl, callbacks = {}) {
        const poll = async () => {
            const response = await fetch(statusUrl || `${this.baseUrl}/blender/status/${taskId}`);
            const status = await response.json();
            if (!response.ok) {
                throw new Error(status.detail || 'Status request failed');
            }

            callbacks.onStatus?.(status);
            if (status.status === 'not_found') {
                const error = status.error || '任务未找到';
                this.log(error, 'error');
                callbacks.onFailed?.(status);
                throw new Error(error);
            }
            if (status.status === 'completed') {
                this.lastCompletedTask = status;
                const downloadUrl = status.download_url ? this.normalizeUrl(status.download_url) : '';
                this.log(`SCGS 任务完成。下载地址: ${downloadUrl || '暂无'}`, 'success');
                callbacks.onComplete?.({ ...status, absolute_download_url: downloadUrl });
                return status;
            }

            if (status.status === 'failed') {
                const error = status.error || 'SCGS 任务失败';
                this.log(error, 'error');
                callbacks.onFailed?.(status);
                throw new Error(error);
            }

            this.log(`任务状态: ${status.status}`, 'task');
            await new Promise(resolve => setTimeout(resolve, 1500));
            return poll();
        };
        return poll();
    }

    async applyTemplate(templateId, extra = {}, callbacks = {}) {
        return this.generateScene({ ...extra, template_id: templateId }, callbacks);
    }

    async processLLMCommand(command, extra = {}, callbacks = {}) {
        return this.generateScene({ ...extra, description: command, instruction: command }, callbacks);
    }

    addAsset(assetType, assetName) {
        this.log(`资产 "${assetName || assetType}" 已暂存为前端演示项。若要真实同步，需要 SCGS 插件提供资产接口。`, 'warning');
        return true;
    }

    async applyLayout(layoutData) {
        this.log(`布局已作为前后端演示数据暂存: ${JSON.stringify(layoutData)}`, 'warning');
        return true;
    }

    async processSketch(fileName) {
        this.log(`草图 "${fileName}" 已通过演示接口处理。真实提取需要 SCGS 插件提供接口。`, 'warning');
        return true;
    }

    normalizeUrl(pathOrUrl) {
        if (!pathOrUrl) return '';
        if (pathOrUrl.startsWith('http://') || pathOrUrl.startsWith('https://')) {
            return pathOrUrl;
        }
        return `${this.baseUrl}${pathOrUrl}`;
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

window.blenderBridge = new BlenderBridge();
