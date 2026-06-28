"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useGameStore } from "@/lib/store/gameStore";
import { useQuery } from "@tanstack/react-query";
import { gameApi } from "@/lib/api/client";

const NAV_ITEMS = [
  { href: "/dashboard", label: "仪表盘", icon: "📊" },
  { href: "/okr", label: "OKR 工作台", icon: "🎯" },
  { href: "/intel", label: "情报中心", icon: "📡" },
  { href: "/board", label: "AI 决策委", icon: "🏛️" },
  { href: "/sandbox", label: "推演沙盘", icon: "🗺️" },
];

export default function Sidebar() {
  const pathname = usePathname();
  const session = useGameStore((s) => s.session);

  const { data: companies } = useQuery({
    queryKey: ["companies"],
    queryFn: () => gameApi.getCompanies(),
  });

  const companyId = session?.config.company_id ?? "";
  const company = companies?.find((c) => c.id === companyId);
  const companyName = company?.name ?? companyId;
  const companyEmoji = company?.logo_emoji ?? "📱";

  return (
    <aside className="w-64 text-white flex flex-col min-h-screen" style={{ backgroundColor: "var(--brand-sidebar-bg)" }}>
      {/* Logo area */}
      <div className="p-5 border-b border-white/10">
        <h1 className="text-lg font-bold tracking-tight">📱 Phone Sim</h1>
        {session && (
          <p className="text-sm text-slate-300 mt-1.5">
            {companyEmoji} <span className="font-medium">{companyName}</span>
          </p>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3 space-y-0.5">
        {NAV_ITEMS.map((item) => {
          const active = pathname?.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-200 ${
                active
                  ? "text-white font-medium shadow-sm"
                  : "text-slate-400 hover:text-white hover:bg-white/5"
              }`}
              style={active ? { backgroundColor: "var(--brand-primary)" } : undefined}
            >
              <span className="text-base">{item.icon}</span>
              <span className="text-sm font-medium">{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Turn progress */}
      {session && (
        <div className="p-4 border-t border-white/10 space-y-3">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>{session.current_year} Q{session.current_quarter}</span>
            <span>→</span>
            <span>{Math.floor(session.config.max_turns / 4) + 2025} Q4</span>
          </div>

          <div className="bg-white/10 rounded-full h-1.5 overflow-hidden">
            <div
              className="h-1.5 rounded-full transition-all duration-700"
              style={{
                width: `${Math.min(100, (session.current_turn / session.config.max_turns) * 100)}%`,
                backgroundColor: "var(--brand-primary)",
              }}
            />
          </div>

          <div className="flex justify-between text-xs text-slate-400">
            <span>回合 {session.current_turn}/{session.config.max_turns}</span>
            <span>{((session.current_turn / session.config.max_turns) * 100).toFixed(0)}%</span>
          </div>
        </div>
      )}
    </aside>
  );
}
