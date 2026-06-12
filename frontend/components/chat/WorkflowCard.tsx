'use client';

import type { WorkflowCard as WFCard } from '@/lib/types';

interface Props {
  card: WFCard;
}

const STATE_ICONS: Record<string, string> = {
  pending: '○',
  running: '⟳',
  done: '✓',
  error: '⚠',
};

export function WorkflowCard({ card }: Props) {
  return (
    <div className="border border-[var(--lp-line)] rounded-[var(--lp-radius-md)] bg-white overflow-hidden">
      <div className="flex items-center gap-2 px-3 py-2 bg-gray-50">
        <span className={
          card.state === 'running' ? 'animate-spin text-[var(--lp-accent)]' :
          card.state === 'done' ? 'text-green-600' :
          card.state === 'error' ? 'text-red-500' : 'text-[var(--lp-muted)]'
        }>
          {STATE_ICONS[card.state] || '○'}
        </span>
        <span className="text-sm font-medium">{card.title}</span>
        {card.summary && (
          <span className="text-xs text-[var(--lp-muted)] ml-auto">{card.summary}</span>
        )}
      </div>
      {card.steps.length > 0 && (
        <div className="px-3 py-2 space-y-1">
          {card.steps.map((step, i) => (
            <div key={i} className="flex items-start gap-2 text-xs">
              <span className="text-[var(--lp-muted)]">{STATE_ICONS[step.state]}</span>
              <span>{step.text}</span>
              {step.result && (
                <span className="text-[var(--lp-muted)]">— {step.result}</span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
