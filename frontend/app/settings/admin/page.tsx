'use client';

import { useState, useEffect } from 'react';

export default function AdminOverviewPage() {
  const [config, setConfig] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    fetch(`${API_BASE}/api/config`)
      .then((r) => r.json())
      .then((d) => setConfig(d.data || {}))
      .catch(() => {});
  }, []);

  return (
    <div className="max-w-2xl">
      <h1 className="text-lg font-semibold mb-4">系统概览</h1>

      <div className="border border-[var(--lp-line)] rounded-[var(--lp-radius-md)] p-4 bg-white space-y-3">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-green-500" />
          <span className="text-sm">API 服务运行中</span>
        </div>

        {config && (
          <div className="text-sm text-[var(--lp-muted)]">
            <p>凭据数: {Array.isArray(config.credentials) ? config.credentials.length : 0}</p>
            <p>实例数: {Array.isArray(config.instances) ? config.instances.length : 0}</p>
            <p>能力数: {Array.isArray(config.capabilities) ? config.capabilities.length : 0}</p>
          </div>
        )}

        {!config && (
          <p className="text-sm text-[var(--lp-muted)]">正在加载配置…</p>
        )}
      </div>
    </div>
  );
}
