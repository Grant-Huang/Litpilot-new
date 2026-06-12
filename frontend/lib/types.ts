/**
 * LitPilot frontend types — aligned with 02-data-schema / 04-sse-events.
 */

export type Delivery = 'chat' | 'process' | 'artifact';
export type CardState = 'pending' | 'running' | 'done' | 'error';
export type Intent = 'new_topic' | 'append_urls' | 'query_corpus';

export interface LitPilotMessage {
  id: string;
  session_id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
  extras?: MessageExtras;
}

export interface MessageExtras {
  delivery?: Delivery;
  artifactKind?: 'review' | 'matrix' | 'outline' | 'none';
  intent?: Intent;
  executionTrace?: WorkflowCard[];
  review_version?: string;
  clarification?: string;
}

export interface WorkflowCard {
  stage: string;
  state: CardState;
  logs?: string[];
}

export interface LogStep {
  kind: 'tool' | 'inline' | 'think';
  state: CardState;
  text: string;
  result?: string;
  detail?: string;
}

// SSE event types
export interface MesoEvent {
  event: string;
  data: {
    seq: number;
    [key: string]: unknown;
  };
}

export const INITIAL_STATE: StreamState = {
  status: 'idle',
  executionTrace: [],
  artifacts: { review: '', matrix: '', outline: '' },
  text: '',
  think: '',
  intent: undefined,
  reviewVersion: undefined,
  error: undefined,
};

export interface StreamState {
  status: 'idle' | 'pending' | 'streaming' | 'settling' | 'done' | 'error';
  executionTrace: WorkflowCard[];
  artifacts: {
    review: string;
    matrix: string;
    outline: string;
  };
  text: string;
  think: string;
  intent?: Intent;
  reviewVersion?: string;
  error?: string;
}

export interface SessionMeta {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  user_turns: number;
  has_review: boolean;
  has_matrix: boolean;
  initial_query?: string;
  last_intent?: Intent;
  pinned?: boolean;
}

export interface LibraryItem {
  display_index: number;
  title: string;
  authors: string;
  year: string;
  doi: string;
  url: string;
  apa_citation: string;
  venue: string;
  abstract: string;
  tags: string[];
  has_full_text: boolean;
  has_pdf: boolean;
  fetch_status: string;
  canonical_key: string;
}

export interface LLMInstance {
  id: string;
  name: string;
  provider: string;
  model: string;
  base_url: string;
  api_key_set: boolean;
  max_tokens: number;
  temperature: number;
}

export interface CapabilityBinding {
  capability: string;
  instance_id: string;
  instance_name?: string;
}

export interface PromptConfig {
  name: string;
  system_prompt: string;
  temperature?: number;
  max_tokens?: number;
}
