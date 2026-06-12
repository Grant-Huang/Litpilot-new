'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LitPilotLogo } from './LitPilotMark';

const NAV_ITEMS = [
  { href: '/chat', label: '对话', icon: '💬' },
  { href: '/library', label: '文献库', icon: '📚' },
  { href: '/settings', label: '设置', icon: '⚙️' },
];

export function NavSidebar() {
  const pathname = usePathname();

  return (
    <nav className="w-[145px] shrink-0 bg-[var(--lp-ink)] text-white flex flex-col h-full">
      <div className="p-4 flex items-center justify-center">
        <LitPilotLogo markSize={28} wordmarkSize={16} ink="#fff" accent="var(--lp-accent)" />
      </div>
      <div className="flex-1 flex flex-col gap-1 px-2 mt-4">
        {NAV_ITEMS.map((item) => {
          const active = pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`
                flex items-center gap-2 px-3 py-2 rounded-[var(--lp-radius-md)]
                text-sm transition-colors
                ${active
                  ? 'bg-white/15 text-white font-medium'
                  : 'text-white/80 hover:bg-white/10 hover:text-white'
                }
              `}
            >
              <span className="text-base">{item.icon}</span>
              <span>{item.label}</span>
            </Link>
          );
        })}
      </div>
      <div className="p-3 text-xs text-white/60 text-center">
        LitPilot v0.1
      </div>
    </nav>
  );
}
