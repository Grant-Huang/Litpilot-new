'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { NavSidebar } from '@/components/NavSidebar';
import { SessionList } from '@/components/chat/SessionList';
import { MessageArea } from '@/components/chat/MessageArea';
import { Composer } from '@/components/chat/Composer';
import { ArtifactPanel } from '@/components/artifact/ArtifactPanel';
import { api } from '@/lib/api';
import { connectStream, reduceEvent, INITIAL_STATE } from '@/lib/sse';
import type { SessionMeta, LitPilotMessage, StreamState } from '@/lib/types';

export default function ChatPage() {
  const [sessions, setSessions] = useState<SessionMeta[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<LitPilotMessage[]>([]);
  const [stream, setStream] = useState<StreamState>(INITIAL_STATE);
  const abortRef = useRef<AbortController | null>(null);

  // Load sessions on mount
  useEffect(() => {
    api.listSessions().then((res) => {
      const list = res.data?.sessions || [];
      setSessions(list);
      const saved = localStorage.getItem('litpilot:active-session');
      if (saved && list.some((s) => s.id === saved)) {
        setActiveId(saved);
      } else if (list.length > 0) {
        setActiveId(list[0].id);
      }
    }).catch(() => {});
  }, []);

  // Load messages when active session changes
  useEffect(() => {
    if (!activeId) return;
    localStorage.setItem('litpilot:active-session', activeId);
    api.getMessages(activeId).then((res) => {
      setMessages(res.data?.messages || []);
    }).catch(() => {});
    setStream(INITIAL_STATE);
  }, [activeId]);

  const handleNewSession = useCallback(async () => {
    const res = await api.createSession();
    const session = res.data;
    setSessions((prev) => [session, ...prev]);
    setActiveId(session.id);
  }, []);

  const handleSend = useCallback(async (message: string, fetchUrls: string[]) => {
    if (!activeId) return;

    // Add user message optimistically
    const userMsg: LitPilotMessage = {
      id: `tmp-${Date.now()}`,
      session_id: activeId,
      role: 'user',
      content: message,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);

    // Create task
    const taskRes = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/tasks`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: activeId,
          message,
          fetch_urls: fetchUrls,
        }),
      },
    );
    const { task_id } = await taskRes.json();

    // Reset stream state and connect
    setStream({ ...INITIAL_STATE, status: 'pending' });

    if (abortRef.current) abortRef.current.abort();
    const controller = connectStream(
      task_id,
      0,
      (event) => {
        setStream((prev) => reduceEvent(prev, event));
      },
      () => {
        // Done: reload messages from server
        if (activeId) {
          api.getMessages(activeId).then((res) => {
            setMessages(res.data?.messages || []);
          }).catch(() => {});
        }
      },
      (err) => {
        setStream((prev) => ({ ...prev, status: 'error', error: err }));
      },
    );
    abortRef.current = controller;
  }, [activeId]);

  const handleStop = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    setStream((prev) => ({ ...prev, status: 'idle' }));
  }, []);

  const showArtifact = stream.artifacts.review || stream.artifacts.matrix || stream.artifacts.outline
    || messages.some((m) => m.extras?.artifactKind && m.extras.artifactKind !== 'none');

  return (
    <div className="flex h-screen overflow-hidden">
      <NavSidebar />
      <SessionList
        sessions={sessions}
        activeId={activeId}
        onSelect={setActiveId}
        onNew={handleNewSession}
      />
      <div className="flex-1 flex flex-col min-w-0">
        <MessageArea
          messages={messages}
          stream={stream}
        />
        <Composer
          onSend={handleSend}
          onStop={handleStop}
          streaming={stream.status === 'streaming' || stream.status === 'pending'}
          userTurns={messages.filter((m) => m.role === 'user').length}
        />
      </div>
      {showArtifact && (
        <ArtifactPanel
          review={stream.artifacts.review}
          matrix={stream.artifacts.matrix}
          outline={stream.artifacts.outline}
          messages={messages}
          sessionId={activeId}
        />
      )}
    </div>
  );
}
