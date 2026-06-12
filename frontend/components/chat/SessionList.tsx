'use client';

import { useState } from 'react';
import type { SessionMeta } from '@/lib/types';
import { useToast } from '@/components/ToastProvider';

interface Props {
  sessions: SessionMeta[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onRename: (id: string, title: string) => void;
  onDelete: (id: string) => void;
  onPin: (id: string, pinned: boolean) => void;
}

export function SessionList({ sessions, activeId, onSelect, onNew, onRename, onDelete, onPin }: Props) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [menuId, setMenuId] = useState<string | null>(null);
  const { addToast } = useToast();

  const sorted = [...sessions].sort((a, b) => {
    if (a.pinned && !b.pinned) return -1;
    if (!a.pinned && b.pinned) return 1;
    return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
  });

  const startRename = (s: SessionMeta) => {
    setEditingId(s.id);
    setEditTitle(s.title || '');
    setMenuId(null);
  };

  const confirmRename = () => {
    if (editingId && editTitle.trim()) {
      onRename(editingId, editTitle.trim());
      addToast('会话已重命名', 'success');
    }
    setEditingId(null);
  };

  const handleDelete = (id: string) => {
    onDelete(id);
    setMenuId(null);
    addToast('会话已删除', 'success');
  };

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
        {sorted.map((s) => (
          <div
            key={s.id}
            className={`
              group relative border-b border-[var(--lp-line)] transition-colors
              ${activeId === s.id ? 'bg-[var(--lp-accent-soft)]' : 'hover:bg-gray-50'}
            `}
          >
            {editingId === s.id ? (
              <div className="px-3 py-2">
                <input
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') confirmRename(); if (e.key === 'Escape') setEditingId(null); }}
                  onBlur={confirmRename}
                  autoFocus
                  className="w-full px-2 py-1 text-sm border border-[var(--lp-accent)] rounded-[var(--lp-radius-sm)] focus:outline-none"
                />
              </div>
            ) : (
              <button
                onClick={() => onSelect(s.id)}
                className="w-full text-left px-3 py-2.5"
              >
                <div className="flex items-center gap-1">
                  {s.pinned && <span className="text-xs text-[var(--lp-accent)]">📌</span>}
                  <span className="font-medium text-sm truncate flex-1">{s.title || '新会话'}</span>
                  <button
                    onClick={(e) => { e.stopPropagation(); setMenuId(menuId === s.id ? null : s.id); }}
                    className="opacity-0 group-hover:opacity-100 text-[var(--lp-muted)] hover:text-[var(--lp-ink)] text-xs px-1"
                  >
                    ⋯
                  </button>
                </div>
                <div className="text-xs text-[var(--lp-muted)] mt-0.5">
                  {s.user_turns || 0} 轮对话
                </div>
              </button>
            )}
            {menuId === s.id && (
              <div className="absolute right-2 top-8 z-10 bg-white border border-[var(--lp-line)] rounded-[var(--lp-radius-md)] shadow-lg py-1 w-32">
                <button
                  onClick={() => onPin(s.id, !s.pinned)}
                  className="w-full text-left px-3 py-1.5 text-sm hover:bg-gray-50"
                >
                  {s.pinned ? '取消置顶' : '置顶'}
                </button>
                <button
                  onClick={() => startRename(s)}
                  className="w-full text-left px-3 py-1.5 text-sm hover:bg-gray-50"
                >
                  重命名
                </button>
                <button
                  onClick={() => handleDelete(s.id)}
                  className="w-full text-left px-3 py-1.5 text-sm text-red-600 hover:bg-red-50"
                >
                  删除
                </button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
