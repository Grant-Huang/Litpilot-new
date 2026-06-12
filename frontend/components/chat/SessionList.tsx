'use client';

import type { SessionMeta } from '@/lib/types';

interface Props {
  sessions: SessionMeta[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
}

export function SessionList({ sessions, activeId, onSelect, onNew }: Props) {
  return (
    <div className="w-[260px] shrink-0 border-r border-[var(--lp-line)] bg-white flex flex-col h-full">
      <div className="p-3 border-b border-[var(--lp-line)]">
        <button
          onClick={onNew}
          className="w-full px-3 py-2 rounded-[var(--lp-radius-md)] bg-[var(--lp-ink)] text-white text-sm font-medium hover:bg-[var(--lp-ink-soft)] transition-colors"
        >
          + 新建会话
        </button>
      </div>
      <div className="flex-1 overflow-y-auto">
        {sessions.length === 0 && (
          <div className="p-4 text-sm text-[var(--lp-muted)] text-center">
            暂无会话，点击上方新建
          </div>
        )}
        {sessions.map((s) => (
          <button
            key={s.id}
            onClick={() => onSelect(s.id)}
            className={`
              w-full text-left px-3 py-2.5 border-b border-[var(--lp-line)] text-sm
              transition-colors
              ${activeId === s.id
                ? 'bg-[var(--lp-accent-soft)] text-[var(--lp-ink)]'
                : 'hover:bg-gray-50 text-[var(--lp-ink-soft)]'
              }
            `}
          >
            <div className="font-medium truncate">{s.title || '新会话'}</div>
            <div className="text-xs text-[var(--lp-muted)] mt-0.5">
              {s.user_turns || 0} 轮对话
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
