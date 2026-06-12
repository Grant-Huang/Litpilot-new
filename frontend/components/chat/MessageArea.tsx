'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import type { LitPilotMessage, StreamState, WorkflowCard as WFCard } from '@/lib/types';
import { WorkflowCard } from '@/components/chat/WorkflowCard';

interface Props {
  messages: LitPilotMessage[];
  stream: StreamState;
}

export function MessageArea({ messages, stream }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const pendingEventsRef = useRef<any[]>([]);
  const rafRef = useRef<number>(0);
  const [displayState, setDisplayState] = useState<StreamState>(stream);

  // rAF-based event batching for streaming updates
  useEffect(() => {
    cancelAnimationFrame(rafRef.current);
    rafRef.current = requestAnimationFrame(() => {
      setDisplayState(stream);
    });
    return () => cancelAnimationFrame(rafRef.current);
  }, [stream]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, displayState.text]);

  const streamingCards: WFCard[] = displayState.executionTrace.map((t) => ({
    stage: t.stage,
    state: t.state,
    logs: t.logs,
  }));

  return (
    <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
      {messages.map((msg) => (
        <div
          key={msg.id}
          className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
        >
          <div
            className={`
              max-w-[75%] px-4 py-3 rounded-[var(--lp-radius-lg)]
              ${msg.role === 'user'
                ? 'bg-[var(--lp-ink)] text-white'
                : 'bg-white border border-[var(--lp-line)]'}
            `}
          >
            <div className="text-sm whitespace-pre-wrap">{msg.content}</div>
            {msg.extras?.clarification && (
              <ClarificationPrompt text={msg.extras.clarification} />
            )}
          </div>
        </div>
      ))}

      {/* Streaming cards */}
      {streamingCards.length > 0 && (
        <div className="space-y-1">
          {streamingCards.map((card, i) => (
            <WorkflowCard key={`${card.stage}-${i}`} card={card} />
          ))}
        </div>
      )}

      {/* Streaming text */}
      {displayState.text && (
        <div className="flex justify-start">
          <div className="max-w-[75%] px-4 py-3 rounded-[var(--lp-radius-lg)] bg-white border border-[var(--lp-line)]">
            <div className="text-sm whitespace-pre-wrap">
              {displayState.text}
              <span className="animate-pulse">▍</span>
            </div>
          </div>
        </div>
      )}

      {/* Streaming think */}
      {displayState.think && (
        <div className="flex justify-start">
          <div className="max-w-[75%] px-4 py-3 rounded-[var(--lp-radius-lg)] bg-gray-50 border border-gray-200 text-gray-600 text-xs italic">
            💭 {displayState.think}
          </div>
        </div>
      )}

      {/* Error */}
      {displayState.error && (
        <div className="flex justify-start">
          <div className="max-w-[75%] px-4 py-3 rounded-[var(--lp-radius-lg)] bg-red-50 border border-red-200 text-red-700 text-sm">
            ⚠ {displayState.error}
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}

function ClarificationPrompt({ text }: { text: string }) {
  return (
    <div className="mt-2 p-2 rounded-[var(--lp-radius-sm)] bg-yellow-50 border border-yellow-200 text-yellow-800 text-xs">
      <span className="font-medium">需要澄清：</span> {text}
    </div>
  );
}
