'use client';

import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api';
import { useToast } from '@/components/ToastProvider';
import type { LibraryItem } from '@/lib/types';
import { NavSidebar } from '@/components/NavSidebar';

type DetailTab = 'info' | 'fulltext' | 'notes';

export default function LibraryPage() {
  const [items, setItems] = useState<LibraryItem[]>([]);
  const [search, setSearch] = useState('');
  const [tagFilter, setTagFilter] = useState('');
  const [allTags, setAllTags] = useState<string[]>([]);
  const [selected, setSelected] = useState<LibraryItem | null>(null);
  const [tab, setTab] = useState<DetailTab>('info');
  const [editMode, setEditMode] = useState(false);
  const [editData, setEditData] = useState<Partial<LibraryItem>>({});
  const { addToast } = useToast();

  const loadItems = useCallback(async () => {
    try {
      const tags = tagFilter ? tagFilter.split(',').map((t) => t.trim()).filter(Boolean) : undefined;
      const res = await api.getLibrary({ search: search || undefined, tags });
      const list = res.data?.items || [];
      setItems(list);
      const tagSet = new Set<string>();
      list.forEach((item) => item.tags?.forEach((t) => tagSet.add(t)));
      setAllTags(Array.from(tagSet).sort());
    } catch {
      addToast('加载文献库失败', 'error');
    }
  }, [search, tagFilter, addToast]);

  useEffect(() => { loadItems(); }, [loadItems]);

  const handleSelect = useCallback((item: LibraryItem) => {
    setSelected(item);
    setTab('info');
    setEditMode(false);
    setEditData({});
  }, []);

  const handleSave = useCallback(async () => {
    if (!selected) return;
    try {
      await api.updateLibraryItem(selected.canonical_key, editData);
      addToast('已保存修改', 'success');
      setEditMode(false);
      setEditData({});
      loadItems();
      const updated = await api.getLibraryItem(selected.canonical_key);
      setSelected(updated.data);
    } catch {
      addToast('保存失败', 'error');
    }
  }, [selected, editData, addToast, loadItems]);

  const handleRefresh = useCallback(async () => {
    if (!selected) return;
    try {
      addToast('正在刷新元数据…', 'info');
      const res = await api.refreshMetadata(selected.canonical_key);
      setSelected(res.data);
      addToast('元数据已刷新', 'success');
      loadItems();
    } catch {
      addToast('刷新失败', 'error');
    }
  }, [selected, addToast, loadItems]);

  const filtered = items;

  return (
    <div className="flex h-screen overflow-hidden">
      <NavSidebar />
      <div className="flex-1 flex min-w-0">
        {/* 左列：列表 */}
        <div className="w-[420px] shrink-0 border-r border-[var(--lp-line)] flex flex-col">
          <div className="p-3 border-b border-[var(--lp-line)] space-y-2">
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="搜索标题、作者、DOI…"
              className="w-full px-3 py-2 rounded-[var(--lp-radius-md)] border border-[var(--lp-line)] text-sm focus:outline-none focus:border-[var(--lp-accent)]"
            />
            {allTags.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {allTags.map((tag) => (
                  <button
                    key={tag}
                    onClick={() => setTagFilter(tagFilter === tag ? '' : tag)}
                    className={`px-2 py-0.5 rounded-full text-xs border transition-colors ${
                      tagFilter === tag
                        ? 'bg-[var(--lp-accent)] text-white border-[var(--lp-accent)]'
                        : 'bg-gray-50 text-[var(--lp-muted)] border-[var(--lp-line)] hover:bg-gray-100'
                    }`}
                  >
                    {tag}
                  </button>
                ))}
              </div>
            )}
          </div>
          <div className="flex-1 overflow-y-auto">
            {filtered.length === 0 && (
              <div className="p-4 text-sm text-[var(--lp-muted)] text-center">暂无文献</div>
            )}
            {filtered.map((item) => (
              <button
                key={item.canonical_key}
                onClick={() => handleSelect(item)}
                className={`w-full text-left px-4 py-3 border-b border-[var(--lp-line)] transition-colors ${
                  selected?.canonical_key === item.canonical_key ? 'bg-[var(--lp-accent-soft)]' : 'hover:bg-gray-50'
                }`}
              >
                <div className="font-medium text-sm truncate">{item.title || '无标题'}</div>
                <div className="text-xs text-[var(--lp-muted)] mt-0.5 truncate">
                  {item.authors || '未知作者'}{item.year ? ` (${item.year})` : ''}
                </div>
                <div className="flex gap-1 mt-1 flex-wrap">
                  {item.tags?.map((t) => (
                    <span key={t} className="px-1.5 py-0.5 bg-blue-50 text-blue-700 rounded text-[10px]">{t}</span>
                  ))}
                </div>
              </button>
            ))}
          </div>
          <div className="p-3 border-t border-[var(--lp-line)] text-xs text-[var(--lp-muted)] text-center">
            共 {filtered.length} 条文献
          </div>
        </div>

        {/* 右列：详情 */}
        <div className="flex-1 flex flex-col min-w-0">
          {!selected ? (
            <div className="flex-1 flex items-center justify-center text-[var(--lp-muted)]">
              选择一条文献查看详情
            </div>
          ) : (
            <>
              <div className="p-4 border-b border-[var(--lp-line)]">
                <h2 className="text-lg font-semibold">{selected.title}</h2>
                <div className="text-sm text-[var(--lp-muted)] mt-1">{selected.authors} ({selected.year})</div>
                <div className="flex gap-3 mt-2 text-xs text-[var(--lp-muted)]">
                  {selected.doi && <span>DOI: {selected.doi}</span>}
                  {selected.venue && <span>来源: {selected.venue}</span>}
                  <span>状态: {selected.fetch_status}</span>
                </div>
              </div>

              <div className="flex border-b border-[var(--lp-line)]">
                {(['info', 'fulltext', 'notes'] as DetailTab[]).map((t) => (
                  <button
                    key={t}
                    onClick={() => setTab(t)}
                    className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                      tab === t
                        ? 'border-[var(--lp-accent)] text-[var(--lp-accent)]'
                        : 'border-transparent text-[var(--lp-muted)] hover:text-[var(--lp-ink)]'
                    }`}
                  >
                    {t === 'info' ? '信息' : t === 'fulltext' ? '全文' : '笔记'}
                  </button>
                ))}
                <div className="ml-auto flex gap-2 pr-3 items-center">
                  {editMode ? (
                    <>
                      <button
                        onClick={handleSave}
                        className="px-3 py-1 text-xs bg-green-600 text-white rounded-[var(--lp-radius-sm)] hover:bg-green-700"
                      >
                        保存
                      </button>
                      <button
                        onClick={() => { setEditMode(false); setEditData({}); }}
                        className="px-3 py-1 text-xs border border-[var(--lp-line)] rounded-[var(--lp-radius-sm)]"
                      >
                        取消
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        onClick={handleRefresh}
                        className="px-3 py-1 text-xs border border-[var(--lp-line)] rounded-[var(--lp-radius-sm)] hover:bg-gray-50"
                      >
                        刷新元数据
                      </button>
                      <button
                        onClick={() => { setEditMode(true); setEditData({}); }}
                        className="px-3 py-1 text-xs border border-[var(--lp-line)] rounded-[var(--lp-radius-sm)] hover:bg-gray-50"
                      >
                        编辑
                      </button>
                    </>
                  )}
                </div>
              </div>

              <div className="flex-1 overflow-y-auto p-4">
                {tab === 'info' && (
                  <div className="space-y-3">
                    <Field label="APA 引用" value={selected.apa_citation} />
                    <Field label="DOI" value={selected.doi} editable={editMode} editKey="doi" editData={editData} setEditData={setEditData} />
                    <Field label="URL" value={selected.url} />
                    <Field label="标签" value={selected.tags?.join(', ')} editable={editMode} editKey="tags" editData={editData} setEditData={setEditData} editPlaceholder="逗号分隔标签" />
                    <Field label="摘要" value={selected.abstract} />
                  </div>
                )}
                {tab === 'fulltext' && (
                  <div className="text-sm text-[var(--lp-muted)]">
                    {selected.has_full_text
                      ? <div>全文已获取。{' '}
                          {selected.has_pdf && <a href={selected.url} target="_blank" rel="noopener noreferrer" className="text-[var(--lp-accent)] underline">查看 PDF</a>}
                        </div>
                      : '全文尚未获取。'}
                  </div>
                )}
                {tab === 'notes' && (
                  <textarea
                    placeholder="在此添加笔记…"
                    className="w-full h-64 px-3 py-2 border border-[var(--lp-line)] rounded-[var(--lp-radius-md)] text-sm focus:outline-none focus:border-[var(--lp-accent)] resize-none"
                  />
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function Field({ label, value, editable, editKey, editData, setEditData, editPlaceholder }: {
  label: string;
  value?: string;
  editable?: boolean;
  editKey?: string;
  editData?: Record<string, unknown>;
  setEditData?: (fn: (prev: Record<string, unknown>) => Record<string, unknown>) => void;
  editPlaceholder?: string;
}) {
  return (
    <div>
      <div className="text-xs font-medium text-[var(--lp-muted)] mb-1">{label}</div>
      {editable && editKey && editData && setEditData ? (
        <input
          value={(editData[editKey] as string) ?? value ?? ''}
          onChange={(e) => setEditData((prev) => ({ ...prev, [editKey]: e.target.value }))}
          placeholder={editPlaceholder}
          className="w-full px-2 py-1 text-sm border border-[var(--lp-accent)] rounded-[var(--lp-radius-sm)] focus:outline-none"
        />
      ) : (
        <div className="text-sm">{value || '—'}</div>
      )}
    </div>
  );
}
