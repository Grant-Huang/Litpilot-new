'use client';

import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api';
import { useToast } from '@/components/ToastProvider';

interface CredentialEntry {
  key: string;
  masked: string;
}

const KNOWN_KEYS = [
  { key: 'openai_api_key', label: 'OpenAI API Key' },
  { key: 'deepseek_api_key', label: 'DeepSeek API Key' },
  { key: 'minimax_api_key', label: 'MiniMax API Key' },
  { key: 'tavily_api_key', label: 'Tavily API Key' },
  { key: 'brave_api_key', label: 'Brave Search API Key' },
  { key: 'jina_api_key', label: 'Jina API Key' },
  { key: 'semantic_scholar_api_key', label: 'Semantic Scholar API Key' },
];

export default function CredentialsPage() {
  const [creds, setCreds] = useState<CredentialEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState<Record<string, string>>({});
  const [testing, setTesting] = useState<string | null>(null);
  const { addToast } = useToast();

  const load = useCallback(async () => {
    try {
      const res = await api.getCredentials();
      const data = res.data || {};
      const entries = KNOWN_KEYS.map((k) => ({
        key: k.key,
        masked: (data[k.key] as { masked: string })?.masked || '',
      }));
      setCreds(entries);
    } catch {
      addToast('加载凭据失败', 'error');
    } finally {
      setLoading(false);
    }
  }, [addToast]);

  useEffect(() => { load(); }, [load]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const updates: Record<string, string> = {};
      for (const [key, value] of Object.entries(editing)) {
        if (value.trim()) updates[key] = value.trim();
      }
      if (Object.keys(updates).length === 0) {
        addToast('没有需要保存的更改', 'info');
        setSaving(false);
        return;
      }
      await api.updateCredentials(updates);
      addToast('凭据已保存', 'success');
      setEditing({});
      load();
    } catch {
      addToast('保存失败', 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async (key: string) => {
    setTesting(key);
    try {
      const res = await api.testCredential(key);
      if (res.data?.ok) {
        addToast(`${key} 测试通过`, 'success');
      } else {
        addToast(`${key} 测试失败: ${res.data?.message || '未知错误'}`, 'error');
      }
    } catch {
      addToast('测试请求失败', 'error');
    } finally {
      setTesting(null);
    }
  };

  if (loading) return <div className="text-sm text-[var(--lp-muted)]">加载中…</div>;

  return (
    <div className="max-w-2xl">
      <h1 className="text-lg font-semibold mb-4">API 凭据管理</h1>
      <div className="border border-[var(--lp-line)] rounded-[var(--lp-radius-md)] bg-white divide-y divide-[var(--lp-line)]">
        {creds.map((cred) => {
          const label = KNOWN_KEYS.find((k) => k.key === cred.key)?.label || cred.key;
          return (
            <div key={cred.key} className="p-4">
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm font-medium">{label}</label>
                <div className="flex items-center gap-2">
                  <span className={`text-xs ${cred.masked ? 'text-green-600' : 'text-[var(--lp-muted)]'}`}>
                    {cred.masked || '未设置'}
                  </span>
                  {cred.masked && (
                    <button
                      onClick={() => handleTest(cred.key)}
                      disabled={testing === cred.key}
                      className="px-2 py-0.5 text-xs border border-[var(--lp-line)] rounded-[var(--lp-radius-sm)] hover:bg-gray-50 disabled:opacity-50"
                    >
                      {testing === cred.key ? '测试中…' : '测试'}
                    </button>
                  )}
                </div>
              </div>
              <input
                type="password"
                placeholder="输入新的密钥…（留空则不修改）"
                value={editing[cred.key] || ''}
                onChange={(e) => setEditing((prev) => ({ ...prev, [cred.key]: e.target.value }))}
                className="w-full px-3 py-1.5 border border-[var(--lp-line)] rounded-[var(--lp-radius-sm)] text-sm focus:outline-none focus:border-[var(--lp-accent)]"
              />
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
          {saving ? '保存中…' : '保存凭据'}
        </button>
      </div>
    </div>
  );
}
