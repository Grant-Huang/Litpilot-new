'use client';

import { ChatShell } from '@/components/chat/ChatShell';
import { use } from 'react';

export default function ChatSessionPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = use(params);
  return <ChatShell initialSessionId={sessionId} />;
}
