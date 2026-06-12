'use client';

import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api';
import { useToast } from '@/components/ToastProvider';

interface SystemInfo {
  python_version: string;
  data_dir: string;
  storage_mode: string;
  credential_count: number;
  instance_count: number;
  capability_count: number;
  library_count: number;
  session_count: number;
}

export default function AdminOverviewPage() {
  const [info, setInfo] = useState<SystemInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const { addToast } = useToast();

  const load = useCallback(async () => {
    try {
      const res = await api.getSystemConfig();
      setInfo(res.data as unknown as SystemInfo || null);
    } catch {
      addToast('加载系统信息失败', 'error');
    } finally {
      setLoading(false);
    }
  }, [addToast]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="max-w-2xl">
      <h1 className="text-lg font-semibold mb-4">系统概览</h1>

      {loading && <div className="text-sm text-[var(--lp-muted)]">加载中…</div>}

      {!loading && (
        <div className="space-y-4">
          <div className="border border-[var(--lp-line)] rounded-[var(--lp-radius-md)] p-4 bg-white">
            <div className="flex items-center gap-2 mb-3">
              <span className="w-2 h-2 rounded-full bg-green-500" />
              <span className="text-sm font-medium">API 服务运行中</span>
            </div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <div className="text-xs text-[var(--lp-muted)]">Python</div>
                <div>{info?.python_version || '—'}</div>
              </div>
              <div>
                <div className="text-xs text-[var(--lp-muted)]">存储模式</div>
                <div>{info?.storage_mode || 'local'}</div>
              </div>
              <div>
                <div className="text-xs text-[var(--lp-muted)]">数据目录</div>
                <div>{info?.data_dir || 'data'}</div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <StatCard label="凭据" value={info?.credential_count ?? 0} href="/settings/admin/credentials" />
            <StatCard label="LLM 实例" value={info?.instance_count ?? 0} href="/settings/admin/instances" />
            <StatCard label="能力绑定" value={info?.capability_count ?? 0} href="/settings/admin/capabilities" />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <StatCard label="文献库条目" value={info?.library_count ?? 0} href="/library" />
            <StatCard label="会话总数" value={info?.session_count ?? 0} href="/chat" />
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value, href }: { label: string; value: number; href: string }) {
  return (
    <a
      href={href}
      className="block border border-[var(--lp-line)] rounded-[var(--lp-radius-md)] p-3 bg-white hover:bg-gray-50 transition-colors"
    >
      <div className="text-2xl font-bold">{value}</div>
      <div className="text-xs text-[var(--lp-muted)]">{label}</div>
    </a>
  );
}
