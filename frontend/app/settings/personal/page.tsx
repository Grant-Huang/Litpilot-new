export default function PersonalPage() {
  return (
    <div className="max-w-2xl">
      <h1 className="text-lg font-semibold mb-4">偏好设置</h1>

      <div className="border border-[var(--lp-line)] rounded-[var(--lp-radius-md)] p-4 bg-white">
        <div className="space-y-4">
          <div>
            <label className="text-sm font-medium">引用格式</label>
            <p className="text-sm text-[var(--lp-muted)] mt-1">
              当前版本固定为 APA 格式，不可切换。
            </p>
            <div className="mt-2 px-3 py-2 bg-gray-50 rounded-[var(--lp-radius-sm)] text-sm text-[var(--lp-muted)]">
              APA (American Psychological Association)
            </div>
          </div>

          <div>
            <label className="text-sm font-medium">综述版本规则</label>
            <p className="text-sm text-[var(--lp-muted)] mt-1">
              v(n+1) 递增，无字母后缀。每次追加文献时版本号自动递增。
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
