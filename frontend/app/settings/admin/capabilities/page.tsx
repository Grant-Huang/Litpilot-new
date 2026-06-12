'use client';

import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api';
import { useToast } from '@/components/ToastProvider';
import type { CapabilityBinding } from '@/lib/types';

const CAPABILITIES = [
  { key: 'web_search', label: '网络搜索', desc: '学术论文检索提供商' },
  { key: 'web_fetch', label: '网页抓取', desc: '全文获取提供商' },
  { key: 'review_generation', label: '综述生成', desc: '综述写作 LLM 实例' },
  { key: 'matrix_generation', label: '矩阵生成', desc: '文献矩阵 LLM 实例' },
  { key: 'qa_generation', label: '语料问答', desc: 'QA 生成 LLM 实例' },
];

export default function CapabilitiesPage() {
  const [bindings, setBindings] = useState<CapabilityBinding[]>([]);
  const [instances, setInstances] = useState<{ id: string; name: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const { addToast } = useToast();

  const load = useCallback(async () => {
    try {
      const [capRes, instRes] = await Promise.all([
        api.getCapabilities(),
        api.getInstances(),
      ]);
      setBindings(capRes.data?.bindings || []);
      setInstances((instRes.data?.instances || []).map((i) => ({ id: i.id, name: i.name })));
    } catch {
      addToast('加载配置失败', 'error');
    } finally {
      setLoading(false);
    }
  }, [addToast]);

  useEffect(() => { load(); }, [load]);

  const getInstanceName = (id: string) => instances.find((i) => i.id === id)?.name || id;

  const handleChange = (capability: string, instanceId: string) => {
    setBindings((prev) => {
      const existing = prev.findIndex((b) => b.capability === capability);
      if (existing >= 0) {
        const updated = [...prev];
        updated[existing] = { ...updated[existing], instance_id: instanceId, instance_name: getInstanceName(instanceId) };
        return updated;
      }
      return [...prev, { capability, instance_id: instanceId, instance_name: getInstanceName(instanceId) }];
    });
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      for (const binding of bindings) {
        await api.updateCapability(binding.capability, {
          instance_id: binding.instance_id,
        });
      }
      addToast('能力绑定已保存', 'success');
    } catch {
      addToast('保存失败', 'error');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="text-sm text-[var(--lp-muted)]">加载中…</div>;

  return (
    <div className="max-w-2xl">
      <h1 className="text-lg font-semibold mb-4">检索与抓取能力</h1>
      <div className="border border-[var(--lp-line)] rounded-[var(--lp-radius-md)] bg-white divide-y divide-[var(--lp-line)]">
        {CAPABILITIES.map((cap) => {
          const binding = bindings.find((b) => b.capability === cap.key);
          return (
            <div key={cap.key} className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm font-medium">{cap.label}</div>
                  <div className="text-xs text-[var(--lp-muted)]">{cap.desc}</div>
                </div>
                <select
                  value={binding?.instance_id || ''}
                  onChange={(e) => handleChange(cap.key, e.target.value)}
                  className="px-2 py-1.5 border border-[var(--lp-line)] rounded-[var(--lp-radius-sm)] text-sm w-48"
                >
                  <option value="">未绑定</option>
                  {instances.map((inst) => (
                    <option key={inst.id} value={inst.id}>{inst.name}</option>
                  ))}
                </select>
              </div>
            </div>
          );
        })}
      </div>
      <div className="mt-4">
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-4 py-2 bg-[var(--lp-ink)] text-white text-sm font-medium rounded-[var(--lp-radius-md)] hover:bg-[var(--lp-ink-soft)] disabled:opacity-50"
        >
          {saving ? '保存中…' : '保存绑定'}
        </button>
      </div>
    </div>
  );
}
