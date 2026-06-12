'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { NavSidebar } from '@/components/NavSidebar';
import { SessionList } from '@/components/chat/SessionList';
import { MessageArea } from '@/components/chat/MessageArea';
import { Composer } from '@/components/chat/Composer';
import { ArtifactPanel } from '@/components/artifact/ArtifactPanel';
import { TurnCompletionBar } from '@/components/chat/TurnCompletionBar';
import { api } from '@/lib/api';
import { connectStream, reduceEvent, INITIAL_STATE } from '@/lib/sse';
import { useToast } from '@/components/ToastProvider';
import type { SessionMeta, LitPilotMessage, StreamState } from '@/lib/types';

export function ChatShell({ initialSessionId }: { initialSessionId?: string }) {
  const [sessions, setSessions] = useState<SessionMeta[]>([]);
  const [activeId, setActiveId] = useState<string | null>(initialSessionId || null);
  const [messages, setMessages] = useState<LitPilotMessage[]>([]);
  const [stream, setStream] = useState<StreamState>(INITIAL_STATE);
  const abortRef = useRef<AbortController | null>(null);
  const { addToast } = useToast();

  useEffect(() => {
    api.listSessions().then((res) => {
      const list = res.data?.sessions || [];
      setSessions(list);
      if (activeId) return;
      const saved = localStorage.getItem('litpilot:active-session');
      if (saved && list.some((s) => s.id === saved)) {
        setActiveId(saved);
      } else if (list.length > 0) {
        setActiveId(list[0].id);
      }
    }).catch(() => {});
  }, [activeId]);

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

  const handleRename = useCallback(async (id: string, title: string) => {
    await api.updateSession(id, { title });
    setSessions((prev) => prev.map((s) => s.id === id ? { ...s, title } : s));
  }, []);

  const handleDelete = useCallback(async (id: string) => {
    await api.deleteSession(id);
    setSessions((prev) => prev.filter((s) => s.id !== id));
    if (activeId === id) {
      const remaining = sessions.filter((s) => s.id !== id);
      setActiveId(remaining.length > 0 ? remaining[0].id : null);
    }
  }, [activeId, sessions]);

  const handlePin = useCallback(async (id: string, pinned: boolean) => {
    await api.updateSession(id, { pinned });
    setSessions((prev) => prev.map((s) => s.id === id ? { ...s, pinned } : s));
  }, []);

  const handleSend = useCallback(async (message: string, fetchUrls: string[]) => {
    if (!activeId) return;

    const userMsg: LitPilotMessage = {
      id: `tmp-${Date.now()}`,
      session_id: activeId,
      role: 'user',
      content: message,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);

    try {
      const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const taskRes = await fetch(`${API_BASE}/api/tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: activeId, message, fetch_urls: fetchUrls }),
      });
      const { task_id } = await taskRes.json();

      setStream({ ...INITIAL_STATE, status: 'pending' });

      if (abortRef.current) abortRef.current.abort();
      const controller = connectStream(
        task_id, 0,
        (event) => { setStream((prev) => reduceEvent(prev, event)); },
        () => {
          if (activeId) {
            api.getMessages(activeId).then((res) => {
              setMessages(res.data?.messages || []);
            }).catch(() => {});
          }
        },
        (err) => {
          setStream((prev) => ({ ...prev, status: 'error', error: err }));
          addToast(err, 'error');
        },
      );
      abortRef.current = controller;
    } catch (err) {
      addToast(`发送失败: ${(err as Error).message}`, 'error');
    }
  }, [activeId, addToast]);

  const handleStop = useCallback(() => {
    if (abortRef.current) { abortRef.current.abort(); abortRef.current = null; }
    setStream((prev) => ({ ...prev, status: 'idle' }));
  }, []);

  const showArtifact = stream.artifacts.review || stream.artifacts.matrix || stream.artifacts.outline
    || messages.some((m) => m.extras?.artifactKind && m.extras.artifactKind !== 'none');

  const isStreaming = stream.status === 'streaming' || stream.status === 'pending';
  const userTurns = messages.filter((m) => m.role === 'user').length;

  return (
    <div className="flex h-screen overflow-hidden">
      <NavSidebar />
      <SessionList
        sessions={sessions}
        activeId={activeId}
        onSelect={setActiveId}
        onNew={handleNewSession}
        onRename={handleRename}
        onDelete={handleDelete}
        onPin={handlePin}
      />
      <div className="flex-1 flex flex-col min-w-0">
        <MessageArea messages={messages} stream={stream} />
        {stream.status === 'done' && (
          <TurnCompletionBar stream={stream} messages={messages} />
        )}
        <Composer
          onSend={handleSend}
          onStop={handleStop}
          streaming={isStreaming}
          userTurns={userTurns}
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
