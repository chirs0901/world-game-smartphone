"use client";

import { useRouter } from "next/navigation";
import { useGameStore } from "@/lib/store/gameStore";

const PHASE_LABELS: Record<string, string> = {
  observe: "👁️ 观察",
  decide: "🧠 决策",
  execute: "⚡ 执行",
  feedback: "📋 反馈",
};

export default function TopBar() {
  const router = useRouter();
  const { session, phase, worldState } = useGameStore();
  const reset = useGameStore((s) => s.reset);

  if (!session) return null;

  const metrics = worldState?.brand_metrics;

  const handleExitGame = () => {
    reset();
    router.replace("/");
  };

  const handleSwitchCompany = () => {
    reset();
    router.replace(`/?switch=true`);
  };

  return (
    <header className="h-14 bg-white border-b border-slate-200 flex items-center justify-between px-6 shrink-0">
      {/* Left: Phase badge */}
      <div className="flex items-center gap-4">
        <span
          className="text-xs font-semibold px-3 py-1.5 rounded-full"
          style={{ backgroundColor: "var(--brand-light)", color: "var(--brand-primary-dark)" }}
        >
          {PHASE_LABELS[phase] || phase}
        </span>
        <span className="text-sm text-slate-600">
          {session.current_year}年 Q{session.current_quarter}
        </span>
      </div>

      {/* Right: Quick KPIs + Actions */}
      <div className="flex items-center gap-5">
        {metrics && (
          <div className="flex items-center gap-5 text-sm">
            <span className="flex items-center gap-1">
              <span className="text-slate-500 text-xs">💰</span>
              <strong className="text-slate-900 font-semibold">{metrics.cash_reserve.toFixed(1)}</strong>
              <span className="text-slate-400 text-xs">亿</span>
            </span>
            <span className="flex items-center gap-1">
              <span className="text-slate-500 text-xs">📈</span>
              <strong className="text-slate-900 font-semibold">{metrics.market_share.toFixed(1)}</strong>
              <span className="text-slate-400 text-xs">%</span>
            </span>
            <span className="flex items-center gap-1">
              <span className="text-slate-500 text-xs">🔥</span>
              <strong className="text-slate-900 font-semibold">{metrics.brand_heat.toFixed(0)}</strong>
            </span>
            <span className="flex items-center gap-1">
              <span className="text-slate-500 text-xs">😊</span>
              <strong className="text-slate-900 font-semibold">{metrics.morale.toFixed(0)}</strong>
            </span>
          </div>
        )}
        <div className="flex items-center gap-2 border-l border-slate-200 pl-4">
          <button
            onClick={handleSwitchCompany}
            className="text-xs px-3 py-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 transition-colors"
          >
            切换公司
          </button>
          <button
            onClick={handleExitGame}
            className="text-xs px-3 py-1.5 rounded-lg bg-red-50 border border-red-100 text-red-500 hover:bg-red-100 transition-colors"
          >
            退出
          </button>
        </div>
      </div>
    </header>
  );
}
