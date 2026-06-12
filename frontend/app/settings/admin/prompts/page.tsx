export default function PromptsPage() {
  return (
    <div className="max-w-3xl">
      <h1 className="text-lg font-semibold mb-4">编排与综述提示词</h1>
      <div className="space-y-4">
        {[
          { key: 'understanding_system_template', label: '理解与规划', group: 'orchestrator' },
          { key: 'review_system_prompt_template', label: '综述写作', group: 'generation' },
          { key: 'matrix_system_template', label: '矩阵生成', group: 'generation' },
          { key: 'query_corpus_system_template', label: '语料问答', group: 'generation' },
        ].map((p) => (
          <div key={p.key} className="border border-[var(--lp-line)] rounded-[var(--lp-radius-md)] p-4 bg-white">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium">{p.label}</span>
              <span className="text-xs text-[var(--lp-muted)]">{p.group}</span>
            </div>
            <textarea
              readOnly
              rows={3}
              className="w-full text-sm bg-gray-50 rounded-[var(--lp-radius-sm)] p-2 border border-[var(--lp-line)]"
              value="（使用默认提示词 — 可通过 API 覆盖）"
            />
          </div>
        ))}
      </div>
    </div>
  );
}
