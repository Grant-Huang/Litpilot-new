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
  getReview: (sessionId: string) =>
    request<{ status: string; data: { version: string; content: string } }>(
      `/api/sessions/${sessionId}/review`,
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
  getLibrary: (params?: { search?: string; tags?: string[] }) => {
    const sp = new URLSearchParams();
    if (params?.search) sp.set('search', params.search);
    if (params?.tags?.length) sp.set('tags', params.tags.join(','));
    const qs = sp.toString();
    return request<{ status: string; data: { items: import('./types').LibraryItem[] } }>(
      `/api/library${qs ? `?${qs}` : ''}`,
    );
  },

  getLibraryItem: (key: string) =>
    request<{ status: string; data: import('./types').LibraryItem }>(
      `/api/library/${encodeURIComponent(key)}`,
    ),

  updateLibraryItem: (key: string, updates: Record<string, unknown>) =>
    request<{ status: string; data: import('./types').LibraryItem }>(
      `/api/library/${encodeURIComponent(key)}`,
      { method: 'PATCH', body: JSON.stringify(updates) },
    ),

  refreshMetadata: (key: string) =>
    request<{ status: string; data: import('./types').LibraryItem }>(
      `/api/library/${encodeURIComponent(key)}/refresh`,
      { method: 'POST' },
    ),

  // Settings — System config
  getSystemConfig: () =>
    request<{ status: string; data: Record<string, unknown> }>('/api/settings/system'),

  updateSystemConfig: (config: Record<string, unknown>) =>
    request<{ status: string }>('/api/settings/system', {
      method: 'PUT',
      body: JSON.stringify(config),
    }),

  // Settings — Credentials
  getCredentials: () =>
    request<{ status: string; data: Record<string, { masked: string }> }>('/api/settings/credentials'),

  updateCredentials: (creds: Record<string, string>) =>
    request<{ status: string }>('/api/settings/credentials', {
      method: 'PUT',
      body: JSON.stringify(creds),
    }),

  testCredential: (key: string) =>
    request<{ status: string; data: { ok: boolean; message: string } }>(
      `/api/settings/credentials/${encodeURIComponent(key)}/test`,
      { method: 'POST' },
    ),

  // Settings — LLM Instances
  getInstances: () =>
    request<{ status: string; data: { instances: import('./types').LLMInstance[] } }>('/api/settings/instances'),

  createInstance: (instance: Record<string, unknown>) =>
    request<{ status: string; data: import('./types').LLMInstance }>('/api/settings/instances', {
      method: 'POST',
      body: JSON.stringify(instance),
    }),

  updateInstance: (id: string, updates: Record<string, unknown>) =>
    request<{ status: string; data: import('./types').LLMInstance }>(
      `/api/settings/instances/${id}`,
      { method: 'PATCH', body: JSON.stringify(updates) },
    ),

  deleteInstance: (id: string) =>
    request<{ status: string }>(`/api/settings/instances/${id}`, { method: 'DELETE' }),

  testInstance: (id: string) =>
    request<{ status: string; data: { ok: boolean; message: string } }>(
      `/api/settings/instances/${id}/test`,
      { method: 'POST' },
    ),

  // Settings — Capabilities
  getCapabilities: () =>
    request<{ status: string; data: { bindings: import('./types').CapabilityBinding[] } }>('/api/settings/capabilities'),

  updateCapability: (capability: string, binding: Record<string, unknown>) =>
    request<{ status: string }>(
      `/api/settings/capabilities/${encodeURIComponent(capability)}`,
      { method: 'PUT', body: JSON.stringify(binding) },
    ),

  // Settings — Prompts
  getPrompts: () =>
    request<{ status: string; data: { prompts: import('./types').PromptConfig[] } }>('/api/settings/prompts'),

  updatePrompt: (name: string, config: Record<string, unknown>) =>
    request<{ status: string }>(
      `/api/settings/prompts/${encodeURIComponent(name)}`,
      { method: 'PUT', body: JSON.stringify(config) },
    ),
};
