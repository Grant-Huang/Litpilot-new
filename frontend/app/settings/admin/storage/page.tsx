'use client';

import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api';
import { useToast } from '@/components/ToastProvider';

export default function StoragePage() {
  const [config, setConfig] = useState<Record<string, unknown>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const { addToast } = useToast();

  const load = useCallback(async () => {
    try {
      const res = await api.getSystemConfig();
      setConfig(res.data || {});
    } catch {
      addToast('加载配置失败', 'error');
    } finally {
      setLoading(false);
    }
  }, [addToast]);

  useEffect(() => { load(); }, [load]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.updateSystemConfig(config);
      addToast('存储配置已保存', 'success');
    } catch {
      addToast('保存失败', 'error');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="text-sm text-[var(--lp-muted)]">加载中…</div>;

  return (
    <div className="max-w-2xl">
      <h1 className="text-lg font-semibold mb-4">存储配置</h1>
      <div className="border border-[var(--lp-line)] rounded-[var(--lp-radius-md)] p-4 bg-white space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1">存储模式</label>
          <select
            value={(config.storage_mode as string) || 'local'}
            onChange={(e) => setConfig((prev) => ({ ...prev, storage_mode: e.target.value }))}
            className="w-full px-3 py-2 border border-[var(--lp-line)] rounded-[var(--lp-radius-sm)] text-sm"
          >
            <option value="local">本地文件存储</option>
          </select>
          <p className="text-xs text-[var(--lp-muted)] mt-1">当前仅支持本地文件存储模式</p>
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">数据目录</label>
          <input
            type="text"
            value={(config.data_dir as string) || 'data'}
            onChange={(e) => setConfig((prev) => ({ ...prev, data_dir: e.target.value }))}
            className="w-full px-3 py-2 border border-[var(--lp-line)] rounded-[var(--lp-radius-sm)] text-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">最大存储空间 (MB)</label>
          <input
            type="number"
            value={(config.max_storage_mb as number) || 1024}
            onChange={(e) => setConfig((prev) => ({ ...prev, max_storage_mb: parseInt(e.target.value) || 1024 }))}
            className="w-full px-3 py-2 border border-[var(--lp-line)] rounded-[var(--lp-radius-sm)] text-sm"
          />
        </div>
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-4 py-2 bg-[var(--lp-ink)] text-white text-sm font-medium rounded-[var(--lp-radius-md)] hover:bg-[var(--lp-ink-soft)] disabled:opacity-50"
        >
          {saving ? '保存中…' : '保存配置'}
        </button>
      </div>
    </div>
  );
}
