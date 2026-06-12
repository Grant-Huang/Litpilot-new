'use client';

import { NavSidebar } from '@/components/NavSidebar';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

const ADMIN_LINKS = [
  { href: '/settings/admin', label: '概览' },
  { href: '/settings/admin/storage', label: '存储' },
  { href: '/settings/admin/credentials', label: '凭据' },
  { href: '/settings/admin/instances', label: '实例库' },
  { href: '/settings/admin/capabilities', label: '检索与抓取' },
  { href: '/settings/admin/prompts', label: '编排与综述' },
];

export default function SettingsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  return (
    <div className="flex h-screen overflow-hidden">
      <NavSidebar />
      <div className="flex-1 flex">
        {/* Sidebar */}
        <div className="w-[200px] shrink-0 border-r border-[var(--lp-line)] bg-white p-4">
          <h2 className="text-sm font-semibold mb-3">个人</h2>
          <Link
            href="/settings/personal"
            className={`block px-3 py-1.5 rounded-[var(--lp-radius-sm)] text-sm mb-1
              ${pathname === '/settings/personal'
                ? 'bg-[var(--lp-accent-soft)] text-[var(--lp-ink)]'
                : 'text-[var(--lp-muted)] hover:text-[var(--lp-ink)]'
              }`}
          >
            偏好设置
          </Link>

          <h2 className="text-sm font-semibold mb-3 mt-6">管理员</h2>
          {ADMIN_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={`block px-3 py-1.5 rounded-[var(--lp-radius-sm)] text-sm mb-1
                ${pathname === link.href
                  ? 'bg-[var(--lp-accent-soft)] text-[var(--lp-ink)]'
                  : 'text-[var(--lp-muted)] hover:text-[var(--lp-ink)]'
                }`}
            >
              {link.label}
            </Link>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {children}
        </div>
      </div>
    </div>
  );
}
