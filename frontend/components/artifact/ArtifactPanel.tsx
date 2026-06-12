'use client';

import { useState } from 'react';
import type { LitPilotMessage } from '@/lib/types';
import { api } from '@/lib/api';

interface Props {
  review: string;
  matrix: string;
  outline: string;
  messages: LitPilotMessage[];
  sessionId: string | null;
}

const TABS = ['综述', '大纲', '矩阵', '文献'] as const;
type Tab = (typeof TABS)[number];

export function ArtifactPanel({ review, matrix, outline, messages, sessionId }: Props) {
  const [tab, setTab] = useState<Tab>('综述');
  const [savedReview, setSavedReview] = useState<string>('');
  const [savedMatrix, setSavedMatrix] = useState<string>('');

  // Load saved review on tab change
  const loadReview = async () => {
    if (!sessionId || savedReview) return;
    try {
      const res = await api.getReview(sessionId);
      setSavedReview(res.data?.content || '');
    } catch {}
  };

  const content = tab === '综述'
    ? review || savedReview || '综述正在生成中…'
    : tab === '矩阵'
      ? matrix || savedMatrix || '矩阵尚未生成'
      : tab === '大纲'
        ? outline || '大纲尚未生成'
        : '文献列表';

  return (
    <div className="w-[clamp(280px,30vw,420px)] shrink-0 border-l border-[var(--lp-line)] bg-white flex flex-col h-full">
      <div className="flex border-b border-[var(--lp-line)]">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => {
              setTab(t);
              if (t === '综述') loadReview();
            }}
            className={`flex-1 px-2 py-2 text-xs font-medium transition-colors
              ${tab === t
                ? 'text-[var(--lp-accent)] border-b-2 border-[var(--lp-accent)]'
                : 'text-gray-500 hover:text-[var(--lp-ink)]'
              }`}
          >
            {t}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-y-auto p-4">
        {tab === '综述' || tab === '矩阵' ? (
          <div className="prose prose-sm max-w-none">
            <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed">
              {content}
            </pre>
          </div>
        ) : tab === '大纲' ? (
          <pre className="text-sm whitespace-pre-wrap">{content}</pre>
        ) : (
          <div className="text-sm text-gray-500">
            文献列表将在综述生成后可用
          </div>
        )}
      </div>
      {(review || matrix) && (
        <div className="border-t border-[var(--lp-line)] px-3 py-2 flex gap-2">
          <button
            onClick={() => navigator.clipboard.writeText(content)}
            className="text-xs text-gray-500 hover:text-[var(--lp-ink)]"
          >
            复制
          </button>
          {(review || savedReview) && (
            <button
              onClick={() => {
                const blob = new Blob([content], { type: 'text/markdown' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'review.md';
                a.click();
                URL.revokeObjectURL(url);
              }}
              className="text-xs text-gray-500 hover:text-[var(--lp-ink)]"
            >
              导出 .md
            </button>
          )}
        </div>
      )}
    </div>
  );
}
