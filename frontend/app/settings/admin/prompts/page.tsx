'use client';

import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api';
import { useToast } from '@/components/ToastProvider';
import type { PromptConfig } from '@/lib/types';

const DEFAULT_PROMPTS = [
  { name: 'understanding_system_template', label: '理解与规划', group: 'orchestrator' },
  { name: 'review_system_prompt_template', label: '综述写作', group: 'generation' },
  { name: 'matrix_system_template', label: '矩阵生成', group: 'generation' },
  { name: 'query_corpus_system_template', label: '语料问答', group: 'generation' },
];

export default function PromptsPage() {
  const [prompts, setPrompts] = useState<PromptConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<string | null>(null);
  const [editing, setEditing] = useState<Record<string, string>>({});
  const { addToast } = useToast();

  const load = useCallback(async () => {
    try {
      const res = await api.getPrompts();
      setPrompts(res.data?.prompts || []);
    } catch {
      addToast('加载提示词失败', 'error');
    } finally {
      setLoading(false);
    }
  }, [addToast]);

  useEffect(() => { load(); }, [load]);

  const getPromptText = (name: string) => {
    if (editing[name] !== undefined) return editing[name];
    const prompt = prompts.find((p) => p.name === name);
    return prompt?.system_prompt || '';
  };

  const handleEdit = (name: string, value: string) => {
    setEditing((prev) => ({ ...prev, [name]: value }));
  };

  const handleSave = async (name: string) => {
    const text = editing[name];
    if (text === undefined) return;
    setSaving(name);
    try {
      await api.updatePrompt(name, { system_prompt: text });
      addToast('提示词已保存', 'success');
      setEditing((prev) => {
        const next = { ...prev };
        delete next[name];
        return next;
      });
      load();
    } catch {
      addToast('保存失败', 'error');
    } finally {
      setSaving(null);
    }
  };

  const handleReset = async (name: string) => {
    setEditing((prev) => {
      const next = { ...prev };
      delete next[name];
      return next;
    });
  };

  if (loading) return <div className="text-sm text-[var(--lp-muted)]">加载中…</div>;

  return (
    <div className="max-w-3xl">
      <h1 className="text-lg font-semibold mb-4">编排与综述提示词</h1>
      <div className="space-y-4">
        {DEFAULT_PROMPTS.map((p) => {
          const text = getPromptText(p.name);
          const isEditing = editing[p.name] !== undefined;
          return (
            <div key={p.name} className="border border-[var(--lp-line)] rounded-[var(--lp-radius-md)] p-4 bg-white">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">{p.label}</span>
                <span className="text-xs text-[var(--lp-muted)]">{p.group}</span>
              </div>
              <textarea
                rows={6}
                value={text}
                onChange={(e) => handleEdit(p.name, e.target.value)}
                className={`w-full text-sm rounded-[var(--lp-radius-sm)] p-2 border font-mono resize-y ${
                  isEditing ? 'border-[var(--lp-accent)] bg-white' : 'border-[var(--lp-line)] bg-gray-50'
                } focus:outline-none`}
                placeholder="输入提示词模板…"
              />
              {isEditing && (
                <div className="flex gap-2 mt-2">
                  <button
                    onClick={() => handleSave(p.name)}
                    disabled={saving === p.name}
                    className="px-3 py-1 text-xs bg-[var(--lp-ink)] text-white rounded-[var(--lp-radius-sm)] hover:bg-[var(--lp-ink-soft)] disabled:opacity-50"
                  >
                    {saving === p.name ? '保存中…' : '保存'}
                  </button>
                  <button
                    onClick={() => handleReset(p.name)}
                    className="px-3 py-1 text-xs border border-[var(--lp-line)] rounded-[var(--lp-radius-sm)]"
                  >
                    重置
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
