export default function CapabilitiesPage() {
  return (
    <div className="max-w-2xl">
      <h1 className="text-lg font-semibold mb-4">检索与抓取能力</h1>
      <div className="border border-[var(--lp-line)] rounded-[var(--lp-radius-md)] p-4 bg-white space-y-3">
        <p className="text-sm text-[var(--lp-muted)]">配置 web_search / web_fetch 提供商及参数。</p>
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <label className="font-medium">搜索提供商</label>
            <p className="text-[var(--lp-muted)]">multi_academic (默认)</p>
          </div>
          <div>
            <label className="font-medium">抓取提供商</label>
            <p className="text-[var(--lp-muted)]">native (默认)</p>
          </div>
          <div>
            <label className="font-medium">并行度</label>
            <p className="text-[var(--lp-muted)]">3</p>
          </div>
          <div>
            <label className="font-medium">PDF 提取</label>
            <p className="text-[var(--lp-muted)]">pymupdf4llm</p>
          </div>
        </div>
      </div>
    </div>
  );
}
