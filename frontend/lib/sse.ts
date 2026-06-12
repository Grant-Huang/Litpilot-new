/**
 * SSE client for Meso v1.0 event stream.
 *
 * Uses fetch + ReadableStream (not EventSource) to support
 * custom `since` parameter for reconnection.
 */

import type { MesoEvent, StreamState, Intent, WorkflowCard } from './types';
import { INITIAL_STATE } from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export type StreamCallback = (state: StreamState) => void;

/**
 * Connect to task SSE stream and process events.
 * Returns an abort controller for cancellation.
 */
export function connectStream(
  taskId: string,
  since: number,
  onEvent: (event: MesoEvent) => void,
  onDone: () => void,
  onError: (err: string) => void,
): AbortController {
  const controller = new AbortController();
  const url = `${API_BASE}/api/tasks/${taskId}/stream?since=${since}`;

  (async () => {
    let watchdogTimer: ReturnType<typeof setTimeout> | null = null;

    function resetWatchdog() {
      if (watchdogTimer) clearTimeout(watchdogTimer);
      watchdogTimer = setTimeout(() => {
        controller.abort();
        onError('Stream timeout (120s without data)');
      }, 120_000);
    }

    try {
      const res = await fetch(url, { signal: controller.signal });
      if (!res.ok) {
        onError(`Stream HTTP ${res.status}`);
        return;
      }

      const reader = res.body?.getReader();
      if (!reader) {
        onError('No response body');
        return;
      }

      const decoder = new TextDecoder();
      let buffer = '';
      resetWatchdog();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        resetWatchdog();
        buffer += decoder.decode(value, { stream: true });

        const frames = buffer.split('\n\n');
        buffer = frames.pop() || '';

        for (const frame of frames) {
          const event = parseSseFrame(frame);
          if (event) {
            onEvent(event);
            if (event.event === 'done' || event.event === 'error') {
              if (watchdogTimer) clearTimeout(watchdogTimer);
              onDone();
              return;
            }
          }
        }
      }
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        onError((err as Error).message);
      }
    } finally {
      if (watchdogTimer) clearTimeout(watchdogTimer);
    }
  })();

  return controller;
}

function parseSseFrame(frame: string): MesoEvent | null {
  let eventType = 'message';
  let dataStr = '';

  for (const line of frame.split('\n')) {
    if (line.startsWith('event: ')) {
      eventType = line.slice(7).trim();
    } else if (line.startsWith('data: ')) {
      dataStr = line.slice(6);
    }
  }

  if (!dataStr) return null;

  try {
    const data = JSON.parse(dataStr);
    return { event: eventType, data };
  } catch {
    return null;
  }
}

/**
 * Reducer: apply a Meso event to stream state, return new state.
 */
export function reduceEvent(
  state: StreamState,
  event: MesoEvent,
): StreamState {
  const d = event.data;

  switch (event.event) {
    case 'stage':
      return {
        ...state,
        status: state.status === 'idle' ? 'streaming' : state.status,
        executionTrace: updateTrace(state.executionTrace, d),
      };

    case 'text': {
      const delta = (d.delta as string) || '';
      return {
        ...state,
        status: 'streaming',
        text: state.text + delta,
      };
    }

    case 'think': {
      const delta = (d.delta as string) || '';
      return {
        ...state,
        status: 'streaming',
        think: state.think + delta,
      };
    }

    case 'artifact': {
      const id = d.id as string;
      const delta = (d.delta as string) || '';
      const key: 'matrix' | 'outline' | 'review' = id.includes('matrix')
        ? 'matrix'
        : id.includes('outline')
          ? 'outline'
          : 'review';
      return {
        ...state,
        status: 'streaming',
        artifacts: {
          ...state.artifacts,
          [key]: state.artifacts[key] + delta,
        },
      };
    }

    case 'extension':
      if (d.name === 'literature_intent') {
        const extData = (d.data ?? {}) as Record<string, unknown>;
        const nestedData = (extData.data ?? {}) as Record<string, unknown>;
        const intentVal = (extData.intent ?? nestedData.intent) as string | undefined;
        return { ...state, intent: intentVal as Intent | undefined };
      }
      return state;

    case 'done':
      return {
        ...state,
        status: 'done',
        reviewVersion: (d.extras as Record<string, unknown>)?.review_version as string | undefined,
      };

    case 'error':
      return { ...state, status: 'error', error: d.message as string };

    default:
      return state;
  }
}

function updateTrace(
  trace: WorkflowCard[],
  data: Record<string, unknown>,
): WorkflowCard[] {
  const name = data.name as string;
  const stageState = data.state as string;
  const log = data.log as string | undefined;

  const stageMap: Record<string, string> = {
    '理解研究问题': 'understand',
    '研究计划': 'brief',
    '文献检索': 'search',
    '抓取全文': 'fetch',
    '引用提取': 'cite',
    '引用抽取': 'cite',
    '文献结构化': 'attributes',
    '大纲规划': 'outline',
    '综述生成': 'generate',
    '文献矩阵': 'matrix',
    '矩阵生成': 'matrix',
    '语料问答': 'corpus_qa',
    '等待澄清': 'clarify',
    '文献库操作': 'manage',
  };

  const stage = stageMap[name] || name;
  const existing = trace.findIndex((c) => c.stage === stage);

  if (existing >= 0) {
    const updated = [...trace];
    const card = { ...updated[existing], state: stageState as WorkflowCard['state'] };
    if (log) {
      card.logs = [...(card.logs || []), log];
    }
    updated[existing] = card;
    return updated;
  }

  return [...trace, { stage, state: stageState as WorkflowCard['state'], logs: log ? [log] : [] }];
}

export { INITIAL_STATE };
