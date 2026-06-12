export default function InstancesPage() {
  return (
    <div className="max-w-2xl">
      <h1 className="text-lg font-semibold mb-4">LLM 实例库</h1>
      <div className="border border-[var(--lp-line)] rounded-[var(--lp-radius-md)] p-4 bg-white">
        <p className="text-sm text-[var(--lp-muted)]">管理 OpenAI、DeepSeek、MiniMax、Ollama 等 LLM 实例配置。</p>
      </div>
    </div>
  );
}
