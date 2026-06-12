export default function StoragePage() {
  return (
    <div className="max-w-2xl">
      <h1 className="text-lg font-semibold mb-4">存储配置</h1>
      <div className="border border-[var(--lp-line)] rounded-[var(--lp-radius-md)] p-4 bg-white">
        <p className="text-sm text-[var(--lp-muted)]">本地文件存储模式。数据保存在后端 data/ 目录。</p>
      </div>
    </div>
  );
}
