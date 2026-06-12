'use client';

import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api';
import { useToast } from '@/components/ToastProvider';
import type { LLMInstance } from '@/lib/types';

const EMPTY_INSTANCE: Record<string, unknown> = {
  name: '',
  provider: 'openai',
  model: '',
  base_url: '',
  api_key: '',
  max_tokens: 4096,
  temperature: 0.7,
};

export default function InstancesPage() {
  const [instances, setInstances] = useState<LLMInstance[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<Record<string, unknown>>({ ...EMPTY_INSTANCE });
  const [editingId, setEditingId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState<string | null>(null);
  const { addToast } = useToast();

  const load = useCallback(async () => {
    try {
      const res = await api.getInstances();
      setInstances(res.data?.instances || []);
    } catch {
      addToast('加载实例列表失败', 'error');
    } finally {
      setLoading(false);
    }
  }, [addToast]);

  useEffect(() => { load(); }, [load]);

  const handleSave = async () => {
    if (!(form.name as string)?.trim() || !(form.model as string)?.trim()) {
      addToast('名称和模型不能为空', 'error');
      return;
    }
    setSaving(true);
    try {
      if (editingId) {
        await api.updateInstance(editingId, form);
        addToast('实例已更新', 'success');
      } else {
        await api.createInstance(form);
        addToast('实例已创建', 'success');
      }
      setShowForm(false);
      setEditingId(null);
      setForm({ ...EMPTY_INSTANCE });
      load();
    } catch {
      addToast('保存失败', 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = (inst: LLMInstance) => {
    setEditingId(inst.id);
    setForm({
      name: inst.name,
      provider: inst.provider,
      model: inst.model,
      base_url: inst.base_url,
      api_key: '',
      max_tokens: inst.max_tokens,
      temperature: inst.temperature,
    });
    setShowForm(true);
  };

  const handleDelete = async (id: string) => {
    try {
      await api.deleteInstance(id);
      addToast('实例已删除', 'success');
      load();
    } catch {
      addToast('删除失败', 'error');
    }
  };

  const handleTest = async (id: string) => {
    setTesting(id);
    try {
      const res = await api.testInstance(id);
      if (res.data?.ok) {
        addToast('连接测试通过', 'success');
      } else {
        addToast(`测试失败: ${res.data?.message || '未知错误'}`, 'error');
      }
    } catch {
      addToast('测试请求失败', 'error');
    } finally {
      setTesting(null);
    }
  };

  if (loading) return <div className="text-sm text-[var(--lp-muted)]">加载中…</div>;

  return (
    <div className="max-w-3xl">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-lg font-semibold">LLM 实例库</h1>
        <button
          onClick={() => { setShowForm(true); setEditingId(null); setForm({ ...EMPTY_INSTANCE }); }}
          className="px-3 py-1.5 bg-[var(--lp-ink)] text-white text-sm rounded-[var(--lp-radius-md)] hover:bg-[var(--lp-ink-soft)]"
        >
          + 新增实例
        </button>
      </div>

      {showForm && (
        <div className="border border-[var(--lp-line)] rounded-[var(--lp-radius-md)] p-4 bg-white mb-4 space-y-3">
          <h3 className="text-sm font-semibold">{editingId ? '编辑实例' : '新增实例'}</h3>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium mb-1">名称</label>
              <input
                value={form.name as string}
                onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
                className="w-full px-2 py-1.5 border border-[var(--lp-line)] rounded-[var(--lp-radius-sm)] text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1">提供商</label>
              <select
                value={form.provider as string}
                onChange={(e) => setForm((p) => ({ ...p, provider: e.target.value }))}
                className="w-full px-2 py-1.5 border border-[var(--lp-line)] rounded-[var(--lp-radius-sm)] text-sm"
              >
                <option value="openai">OpenAI</option>
                <option value="deepseek">DeepSeek</option>
                <option value="minimax">MiniMax</option>
                <option value="ollama">Ollama</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium mb-1">模型</label>
              <input
                value={form.model as string}
                onChange={(e) => setForm((p) => ({ ...p, model: e.target.value }))}
                placeholder="gpt-4o / deepseek-chat"
                className="w-full px-2 py-1.5 border border-[var(--lp-line)] rounded-[var(--lp-radius-sm)] text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1">Base URL</label>
              <input
                value={form.base_url as string}
                onChange={(e) => setForm((p) => ({ ...p, base_url: e.target.value }))}
                placeholder="https://api.openai.com/v1"
                className="w-full px-2 py-1.5 border border-[var(--lp-line)] rounded-[var(--lp-radius-sm)] text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1">API Key</label>
              <input
                type="password"
                value={form.api_key as string}
                onChange={(e) => setForm((p) => ({ ...p, api_key: e.target.value }))}
                placeholder={editingId ? '留空不修改' : '输入 API Key'}
                className="w-full px-2 py-1.5 border border-[var(--lp-line)] rounded-[var(--lp-radius-sm)] text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1">Max Tokens</label>
              <input
                type="number"
                value={form.max_tokens as number}
                onChange={(e) => setForm((p) => ({ ...p, max_tokens: parseInt(e.target.value) || 4096 }))}
                className="w-full px-2 py-1.5 border border-[var(--lp-line)] rounded-[var(--lp-radius-sm)] text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1">Temperature</label>
              <input
                type="number"
                step="0.1"
                min="0"
                max="2"
                value={form.temperature as number}
                onChange={(e) => setForm((p) => ({ ...p, temperature: parseFloat(e.target.value) || 0.7 }))}
                className="w-full px-2 py-1.5 border border-[var(--lp-line)] rounded-[var(--lp-radius-sm)] text-sm"
              />
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-3 py-1.5 bg-[var(--lp-ink)] text-white text-sm rounded-[var(--lp-radius-md)] hover:bg-[var(--lp-ink-soft)] disabled:opacity-50"
            >
              {saving ? '保存中…' : '保存'}
            </button>
            <button
              onClick={() => { setShowForm(false); setEditingId(null); }}
              className="px-3 py-1.5 border border-[var(--lp-line)] text-sm rounded-[var(--lp-radius-md)]"
            >
              取消
            </button>
          </div>
        </div>
      )}

      <div className="space-y-2">
        {instances.map((inst) => (
          <div
            key={inst.id}
            className="border border-[var(--lp-line)] rounded-[var(--lp-radius-md)] p-3 bg-white flex items-center justify-between"
          >
            <div>
              <div className="text-sm font-medium">{inst.name}</div>
              <div className="text-xs text-[var(--lp-muted)]">
                {inst.provider} / {inst.model}
                {inst.base_url && <span className="ml-2">→ {inst.base_url}</span>}
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className={`text-xs ${inst.api_key_set ? 'text-green-600' : 'text-orange-500'}`}>
                {inst.api_key_set ? '✓ Key' : '⚠ 无 Key'}
              </span>
              <button
                onClick={() => handleTest(inst.id)}
                disabled={testing === inst.id}
                className="px-2 py-0.5 text-xs border border-[var(--lp-line)] rounded-[var(--lp-radius-sm)] hover:bg-gray-50 disabled:opacity-50"
              >
                {testing === inst.id ? '…' : '测试'}
              </button>
              <button
                onClick={() => handleEdit(inst)}
                className="px-2 py-0.5 text-xs border border-[var(--lp-line)] rounded-[var(--lp-radius-sm)] hover:bg-gray-50"
              >
                编辑
              </button>
              <button
                onClick={() => handleDelete(inst.id)}
                className="px-2 py-0.5 text-xs border border-red-200 text-red-600 rounded-[var(--lp-radius-sm)] hover:bg-red-50"
              >
                删除
              </button>
            </div>
          </div>
        ))}
        {instances.length === 0 && (
          <div className="text-sm text-[var(--lp-muted)] text-center py-8">
            暂无 LLM 实例，点击上方新增
          </div>
        )}
      </div>
    </div>
  );
}
