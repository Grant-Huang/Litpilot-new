'use client';

import { useState, useEffect } from 'react';
import { NavSidebar } from '@/components/NavSidebar';
import { api } from '@/lib/api';
import type { LibraryItem } from '@/lib/types';

export default function LibraryPage() {
  const [items, setItems] = useState<LibraryItem[]>([]);
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState<LibraryItem | null>(null);

  useEffect(() => {
    api.getLibrary().then((res) => {
      setItems(res.data?.items || []);
    }).catch(() => {});
  }, []);

  const filtered = items.filter((item) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      item.title.toLowerCase().includes(q) ||
      item.authors.toLowerCase().includes(q) ||
      item.apa_citation.toLowerCase().includes(q) ||
      item.doi.toLowerCase().includes(q)
    );
  });

  return (
    <div className="flex h-screen overflow-hidden">
      <NavSidebar />
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="border-b border-[var(--lp-line)] px-6 py-4 bg-white">
          <h1 className="text-lg font-semibold">文献库</h1>
          <p className="text-sm text-[var(--lp-muted)]">共 {filtered.length} 条文献</p>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="搜索标题、作者、DOI…"
            className="mt-2 w-full max-w-md px-3 py-1.5 rounded-[var(--lp-radius-md)] border border-[var(--lp-line)] text-sm
              focus:outline-none focus:border-[var(--lp-accent)]"
          />
        </div>

        {/* Two-column layout */}
        <div className="flex-1 flex overflow-hidden">
          {/* Left: list */}
          <div className="w-[400px] shrink-0 border-r border-[var(--lp-line)] overflow-y-auto">
            {filtered.length === 0 ? (
              <div className="p-6 text-center text-sm text-[var(--lp-muted)]">
                {search ? '无匹配结果' : '文献库为空'}
              </div>
            ) : (
              filtered.map((item) => (
                <button
                  key={item.canonical_key}
                  onClick={() => setSelected(item)}
                  className={`w-full text-left px-4 py-3 border-b border-[var(--lp-line)] transition-colors
                    ${selected?.canonical_key === item.canonical_key
                      ? 'bg-[var(--lp-accent-soft)]'
                      : 'hover:bg-gray-50'
                    }`}
                >
                  <div className="text-sm font-medium truncate">
                    [{item.display_index}] {item.title || '无标题'}
                  </div>
                  <div className="text-xs text-[var(--lp-muted)] mt-0.5 truncate">
                    {item.authors} {item.year && `(${item.year})`}
                  </div>
                  <div className="flex gap-1 mt-1">
                    {item.has_full_text && (
                      <span className="text-[10px] bg-green-50 text-green-700 px-1.5 py-0.5 rounded">全文</span>
                    )}
                    {item.has_pdf && (
                      <span className="text-[10px] bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded">PDF</span>
                    )}
                    {item.fetch_status === 'fetch_failed' && (
                      <span className="text-[10px] bg-red-50 text-red-700 px-1.5 py-0.5 rounded">抓取失败</span>
                    )}
                  </div>
                </button>
              ))
            )}
          </div>

          {/* Right: detail */}
          <div className="flex-1 overflow-y-auto p-6">
            {selected ? (
              <div className="space-y-4">
                <h2 className="text-lg font-semibold">{selected.title}</h2>
                <p className="text-sm text-[var(--lp-muted)]">{selected.authors}</p>
                {selected.venue && (
                  <p className="text-sm">{selected.venue} {selected.year}</p>
                )}
                {selected.doi && (
                  <p className="text-sm">
                    DOI: <a href={`https://doi.org/${selected.doi}`} target="_blank" className="text-blue-600 underline">{selected.doi}</a>
                  </p>
                )}
                {selected.abstract && (
                  <div>
                    <h3 className="text-sm font-medium mb-1">摘要</h3>
                    <p className="text-sm text-[var(--lp-ink-soft)] leading-relaxed">{selected.abstract}</p>
                  </div>
                )}
                {selected.apa_citation && (
                  <div>
                    <h3 className="text-sm font-medium mb-1">APA 引用</h3>
                    <pre className="text-sm bg-gray-50 p-3 rounded-[var(--lp-radius-md)] whitespace-pre-wrap">
                      {selected.apa_citation}
                    </pre>
                    <button
                      onClick={() => navigator.clipboard.writeText(selected.apa_citation)}
                      className="mt-1 text-xs text-[var(--lp-muted)] hover:text-[var(--lp-ink)]"
                    >
                      复制引用
                    </button>
                  </div>
                )}
                {selected.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {selected.tags.map((tag) => (
                      <span key={tag} className="text-xs bg-gray-100 px-2 py-0.5 rounded">{tag}</span>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div className="flex items-center justify-center h-full text-sm text-[var(--lp-muted)]">
                选择左侧文献查看详情
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
