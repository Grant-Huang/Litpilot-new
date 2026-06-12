'use client';

import { useRef, useEffect } from 'react';
import type { LitPilotMessage, StreamState } from '@/lib/types';
import { WorkflowCard } from './WorkflowCard';

interface Props {
  messages: LitPilotMessage[];
  stream: StreamState;
}

export function MessageArea({ messages, stream }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, stream.chatText, stream.processText, stream.executionTrace]);

  if (messages.length === 0 && stream.status === 'idle') {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="text-5xl font-bold text-[var(--lp-ink)]">
            Lit<span className="text-[var(--lp-accent)]">Pilot</span>
          </div>
          <p className="text-[var(--lp-muted)] text-sm max-w-md">
            描述你的研究主题或综述问题，LitPilot 将帮你检索、整理并撰写文献综述。
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6">
      <div className="max-w-3xl mx-auto space-y-4">
        {messages.map((msg) => (
          <div key={msg.id}>
            {msg.role === 'user' ? (
              <div className="flex justify-end">
                <div className="bg-[var(--lp-ink)] text-white px-4 py-2 rounded-[var(--lp-radius-lg)] max-w-[80%] text-sm">
                  {msg.content}
                </div>
              </div>
            ) : (
              <div className="space-y-2">
                {msg.extras?.executionTrace && msg.extras.executionTrace.length > 0 && (
                  <div className="space-y-2">
                    {msg.extras.executionTrace.map((card, i) => (
                      <WorkflowCard key={i} card={card} />
                    ))}
                  </div>
                )}
                {msg.content && (!msg.extras?.delivery || msg.extras.delivery === 'chat') && (
                  <div className="px-2 py-1 text-sm text-[var(--lp-ink-soft)]">
                    {msg.content}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}

        {/* Streaming content */}
        {(stream.status === 'streaming' || stream.status === 'pending') && (
          <div className="space-y-2">
            {stream.executionTrace.map((card, i) => (
              <WorkflowCard key={`stream-${i}`} card={card} />
            ))}
            {stream.chatText && (
              <div className="px-2 py-1 text-sm">{stream.chatText}</div>
            )}
          </div>
        )}

        {stream.status === 'error' && (
          <div className="px-3 py-2 rounded-[var(--lp-radius-md)] bg-red-50 text-red-700 text-sm">
            错误: {stream.error || '未知错误'}
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}
