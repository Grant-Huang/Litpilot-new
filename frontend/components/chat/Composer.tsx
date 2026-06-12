'use client';

import { useState, useRef, useCallback } from 'react';

interface Props {
  onSend: (message: string, fetchUrls: string[]) => void;
  onStop: () => void;
  streaming: boolean;
  userTurns: number;
}

export function Composer({ onSend, onStop, streaming, userTurns }: Props) {
  const [text, setText] = useState('');
  const [urls, setUrls] = useState<string[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const canSend = !streaming && (text.trim().length > 0 || (urls.length > 0 && userTurns > 0));

  const handleSend = useCallback(() => {
    if (!canSend) return;
    onSend(text.trim(), urls);
    setText('');
    setUrls([]);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }, [canSend, text, urls, onSend]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      const content = ev.target?.result as string;
      const urlRegex = /https?:\/\/\S+/g;
      const found = content.match(urlRegex) || [];
      setUrls((prev) => [...prev, ...found]);
    };
    reader.readAsText(file);
    e.target.value = '';
  };

  return (
    <div className="border-t border-[var(--lp-line)] bg-white px-4 py-3">
      {urls.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          {urls.map((url, i) => (
            <span key={i} className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded">
              {url.slice(0, 40)}...
              <button onClick={() => setUrls((prev) => prev.filter((_, j) => j !== i))} className="ml-1">
                ×
              </button>
            </span>
          ))}
        </div>
      )}
      <div className="flex items-end gap-2">
        {userTurns > 0 && (
          <label className="cursor-pointer p-2 text-[var(--lp-muted)] hover:text-[var(--lp-ink)]">
            +
            <input type="file" className="hidden" accept=".txt,.csv,.json" onChange={handleFileUpload} />
          </label>
        )}
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            e.target.style.height = 'auto';
            e.target.style.height = Math.min(e.target.scrollHeight, 150) + 'px';
          }}
          onKeyDown={handleKeyDown}
          placeholder={streaming ? '生成中…' : '描述你的研究主题或综述问题…'}
          disabled={streaming}
          rows={2}
          className="flex-1 resize-none rounded-[var(--lp-radius-md)] border border-[var(--lp-line)] px-3 py-2 text-sm
            focus:outline-none focus:border-[var(--lp-accent)] disabled:bg-gray-50 disabled:text-[var(--lp-muted)]"
        />
        {streaming ? (
          <button
            onClick={onStop}
            className="px-4 py-2 rounded-[var(--lp-radius-md)] bg-red-500 text-white text-sm font-medium hover:bg-red-600"
          >
            ■ 停止
          </button>
        ) : (
          <button
            onClick={handleSend}
            disabled={!canSend}
            className="px-4 py-2 rounded-[var(--lp-radius-md)] bg-[var(--lp-accent)] text-white text-sm font-medium
              hover:bg-orange-600 disabled:bg-gray-200 disabled:text-gray-400 transition-colors"
          >
            发送
          </button>
        )}
      </div>
    </div>
  );
}
