export default function CredentialsPage() {
  return (
    <div className="max-w-2xl">
      <h1 className="text-lg font-semibold mb-4">API 凭据管理</h1>
      <div className="border border-[var(--lp-line)] rounded-[var(--lp-radius-md)] p-4 bg-white">
        <p className="text-sm text-[var(--lp-muted)]">在此管理 Tavily、Brave、Jina 等 API 密钥。通过 API 端点进行 CRUD 操作。</p>
      </div>
    </div>
  );
}
