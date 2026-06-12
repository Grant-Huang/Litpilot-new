/**
 * REST API client for LitPilot backend.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function request<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body.slice(0, 200)}`);
  }
  return res.json();
}

// Sessions
export const api = {
  listSessions: () =>
    request<{ status: string; data: { sessions: import('./types').SessionMeta[] } }>('/api/sessions'),

  createSession: (title?: string) =>
    request<{ status: string; data: import('./types').SessionMeta }>('/api/sessions', {
      method: 'POST',
      body: JSON.stringify({ title }),
    }),

  getSession: (id: string) =>
    request<{ status: string; data: import('./types').SessionMeta }>(`/api/sessions/${id}`),

  deleteSession: (id: string) =>
    request<{ status: string }>(`/api/sessions/${id}`, { method: 'DELETE' }),

  updateSession: (id: string, updates: Record<string, unknown>) =>
    request<{ status: string; data: import('./types').SessionMeta }>(`/api/sessions/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(updates),
    }),

  // Messages
  getMessages: (sessionId: string) =>
    request<{ status: string; data: { messages: import('./types').LitPilotMessage[] } }>(
      `/api/sessions/${sessionId}/messages`,
    ),

  appendMessage: (sessionId: string, msg: Partial<import('./types').LitPilotMessage>) =>
    request<{ status: string; data: import('./types').LitPilotMessage }>(
      `/api/sessions/${sessionId}/messages`,
      { method: 'POST', body: JSON.stringify(msg) },
    ),

  // Reviews
  getReview: (sessionId: string, version?: string) => {
    const q = version ? `?version=${version}` : '';
    return request<{ status: string; data: { version: string; content: string } }>(
      `/api/sessions/${sessionId}/review${q}`,
    );
  },

  getReviewVersions: (sessionId: string) =>
    request<{ status: string; data: { versions: string[] } }>(
      `/api/sessions/${sessionId}/review/versions`,
    ),

  // Matrix
  getMatrix: (sessionId: string) =>
    request<{ status: string; data: { content: string } }>(
      `/api/sessions/${sessionId}/matrix`,
    ),

  // Outline
  getOutline: (sessionId: string) =>
    request<{ status: string; data: Record<string, unknown> }>(
      `/api/sessions/${sessionId}/outline`,
    ),

  // Library
  getLibrary: () =>
    request<{ status: string; data: { items: import('./types').LibraryItem[] } }>(
      '/api/library',
    ),
};
