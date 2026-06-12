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
}

export interface WorkflowCard {
  type: string;
  title: string;
  state: CardState;
  summary?: string;
  steps: LogStep[];
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

export interface StreamState {
  status: 'idle' | 'pending' | 'streaming' | 'settling' | 'done' | 'error';
  executionTrace: WorkflowCard[];
  artifacts: {
    review: string;
    matrix: string;
    outline: string;
  };
  chatText: string;
  processText: string;
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
