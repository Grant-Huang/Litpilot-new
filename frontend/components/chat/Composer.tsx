'use client';

import { useState, useRef } from 'react';

interface Props {
  onSend: (message: string, fetchUrls: string[]) => void;
  onStop: () => void;
  streaming: boolean;
  userTurns: number;
}

export function Composer({ onSend, onStop, streaming, userTurns }: Props) {
  const [text, setText] = useState('');
  const [urlInput, setUrlInput] = useState('');
  const fileRef = useRef<HTMLInputElement>(null);

  const handleSend = () => {
    const msg = text.trim();
    if (!msg) return;
    const urls = urlInput
      .split(/[\n,]+/)
      .map((u) => u.trim())
      .filter(Boolean);
    onSend(msg, urls);
    setText('');
    setUrlInput('');
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;
    const fileUrls: string[] = [];
    for (const f of Array.from(files)) {
      fileUrls.push(f.name);
    }
    if (fileUrls.length > 0) {
      setUrlInput((prev) => (prev ? prev + '\n' : '') + fileUrls.join('\n'));
    }
    e.target.value = '';
  };

  const placeholder = userTurns === 0
    ? '描述你想综述的主题…'
    : '继续对话，或粘贴 URL 添加文献…';

  return (
    <div className="border-t border-[var(--lp-line)] bg-white px-4 py-3">
      {urlInput && (
        <div className="mb-2 px-3 py-1.5 bg-gray-50 rounded-[var(--lp-radius-sm)] text-xs text-[var(--lp-muted)] flex items-center gap-1">
          <span>📎 URL ({urlInput.split(/[\n,]+/).filter(Boolean).length})</span>
          <button onClick={() => setUrlInput('')} className="ml-auto hover:text-red-500">✕</button>
        </div>
      )}
      <div className="flex items-end gap-2">
        <textarea
          value={urlInput ? `${text}${text ? '\n' : ''}[URLs]\n${urlInput}` : text}
          onChange={(e) => {
            const val = e.target.value;
            if (val.includes('[URLs]')) {
              const parts = val.split('[URLs]\n');
              setText(parts[0]);
              setUrlInput(parts.slice(1).join('[URLs]\n'));
            } else {
              setText(val);
            }
          }}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
          placeholder={placeholder}
          rows={2}
          className="flex-1 resize-none rounded-[var(--lp-radius-md)] border border-[var(--lp-line)] px-3 py-2 text-sm focus:outline-none focus:border-[var(--lp-accent)]"
        />
        <input
          ref={fileRef}
          type="file"
          multiple
          accept=".pdf,.txt,.bib"
          className="hidden"
          onChange={handleFileChange}
        />
        <button
          onClick={() => fileRef.current?.click()}
          className="p-2 rounded-[var(--lp-radius-md)] border border-[var(--lp-line)] hover:bg-gray-50 text-sm"
          title="上传文献文件"
        >
          📎
        </button>
        {streaming ? (
          <button
            onClick={onStop}
            className="px-4 py-2 rounded-[var(--lp-radius-md)] bg-red-600 text-white text-sm font-medium hover:bg-red-700"
          >
            停止
          </button>
        ) : (
          <button
            onClick={handleSend}
            disabled={!text.trim()}
            className="px-4 py-2 rounded-[var(--lp-radius-md)] bg-[var(--lp-ink)] text-white text-sm font-medium hover:bg-[var(--lp-ink-soft)] disabled:opacity-40"
          >
            发送
          </button>
        )}
      </div>
    </div>
  );
}
