'use client';

import { useState } from 'react';
import type { WorkflowCard as WorkflowCardType } from '@/lib/types';

interface Props {
  card: WorkflowCardType;
}

const stageLabel: Record<string, string> = {
  understand: '理解',
  search: '搜索',
  fetch: '获取',
  cite: '引用',
  structure: '结构',
  outline: '大纲',
  generate: '生成',
  matrix: '矩阵',
};

const stateIcon: Record<string, string> = {
  pending: '⏳',
  running: '🔄',
  done: '✅',
  error: '❌',
};

export function WorkflowCard({ card }: Props) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="my-1 border border-[var(--lp-line)] rounded-[var(--lp-radius-md)] overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-3 py-2 flex items-center gap-2 text-sm hover:bg-gray-50 transition-colors"
      >
        <span>{stateIcon[card.state] || '⏳'}</span>
        <span className="font-medium">
          {stageLabel[card.stage] || card.stage}
        </span>
        <span className="text-[var(--lp-muted)] text-xs ml-auto">
          {card.logs?.length || 0} 条日志
        </span>
        <span className="text-xs text-[var(--lp-muted)]">
          {expanded ? '▲' : '▼'}
        </span>
      </button>
      {expanded && card.logs && card.logs.length > 0 && (
        <div className="border-t border-[var(--lp-line)] px-3 py-2 bg-gray-50">
          {card.logs.map((log, i) => (
            <div key={i} className="text-xs text-gray-600 py-0.5 font-mono">
              {log}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
