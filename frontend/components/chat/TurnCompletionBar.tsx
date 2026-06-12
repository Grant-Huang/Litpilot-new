'use client';

import type { StreamState, LitPilotMessage } from '@/lib/types';

interface Props {
  stream: StreamState;
  messages: LitPilotMessage[];
}

export function TurnCompletionBar({ stream, messages }: Props) {
  const trace = stream.executionTrace;
  if (trace.length === 0) return null;

  const done = trace.filter((c) => c.state === 'done').length;
  const total = trace.length;
  const hasReview = !!stream.artifacts.review;
  const hasMatrix = !!stream.artifacts.matrix;

  return (
    <div className="border-t border-[var(--lp-line)] bg-gray-50 px-4 py-2 flex items-center gap-3 text-sm">
      <span className="text-[var(--lp-muted)]">
        流程完成 {done}/{total} 阶段
      </span>
      {hasReview && (
        <span className="text-green-700 font-medium">
          ✓ 综述已生成
        </span>
      )}
      {hasMatrix && (
        <span className="text-blue-700 font-medium">
          ✓ 矩阵已生成
        </span>
      )}
      {stream.reviewVersion && (
        <span className="text-xs text-[var(--lp-muted)]">
          版本 {stream.reviewVersion}
        </span>
      )}
    </div>
  );
}
