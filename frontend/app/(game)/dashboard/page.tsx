"use client";

import { useGameStore } from "@/lib/store/gameStore";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { intelApi, gameApi, socialApi } from "@/lib/api/client";
import { useRouter } from "next/navigation";
import PhoneStore from "@/components/PhoneStore";
import { useEffect, useState, useRef } from "react";

const METRIC_LABELS: Record<string, { label: string; icon: string; unit: string }> = {
  cash_reserve: { label: "现金储备", icon: "💰", unit: "亿" },
  market_share: { label: "市场份额", icon: "📈", unit: "%" },
  brand_heat: { label: "品牌热度", icon: "🔥", unit: "" },
  morale: { label: "团队士气", icon: "😊", unit: "" },
  tech_leadership: { label: "技术领先", icon: "🔬", unit: "" },
  supply_stability: { label: "供应链稳定", icon: "🏭", unit: "" },
  customer_satisfaction: { label: "客户满意度", icon: "⭐", unit: "" },
  sales_volume: { label: "销量", icon: "📱", unit: "万台" },
  revenue: { label: "营收", icon: "💵", unit: "亿" },
  profit: { label: "利润", icon: "💎", unit: "亿" },
};

export default function DashboardPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { session, worldState, phase, setPhase, lastSummary, advanceTurn, loading, fetchWorldState, autoMode, autoSpeed, setAutoMode, setAutoSpeed } =
    useGameStore();

  const autoTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const SPEED_MAP: Record<2 | 3 | 4, number> = { 2: 2000, 3: 1300, 4: 750 };

  // Auto-play timer management
  useEffect(() => {
    if (autoMode && session) {
      const interval = SPEED_MAP[autoSpeed] || 2000;
      autoTimerRef.current = setInterval(async () => {
        const { session: s } = useGameStore.getState();
        if (!s || s.current_turn >= s.config.max_turns) {
          setAutoMode(false);
          return;
        }
        await advanceTurn();
      }, interval);
    }
    return () => {
      if (autoTimerRef.current) {
        clearInterval(autoTimerRef.current);
        autoTimerRef.current = null;
      }
    };
  }, [autoMode, autoSpeed, session?.id]);

  // Auto-fetch worldState when session exists but worldState is null (e.g. after page refresh)
  useEffect(() => {
    if (session && !worldState) {
      fetchWorldState();
    }
  }, [session, worldState, fetchWorldState]);

  // Redirect to home if there's truly no session (after hydration is complete)
  useEffect(() => {
    if (!session) {
      router.replace("/");
    }
  }, [session]);

  // Xiaohongshu social feed (2h auto-refresh)
  const brandId = session?.config.company_id ?? "apple";
  const {
    data: xhsData,
    isLoading: loadingXhs,
    isFetching: fetchingXhs,
  } = useQuery({
    queryKey: ["xhs-posts", brandId],
    queryFn: () => socialApi.getXhsPosts(brandId),
    enabled: !!session,
    refetchInterval: 7200000, // 2 hours
    retry: 1,
    retryDelay: 2000,
  });

  const [xhsManualRefreshing, setXhsManualRefreshing] = useState(false);
  const handleRefreshXhs = async () => {
    setXhsManualRefreshing(true);
    try {
      // Force refresh: bypass cache and trigger live XHS search
      const freshData = await socialApi.getXhsPosts(brandId, true);
      queryClient.setQueryData(["xhs-posts", brandId], freshData);
    } finally {
      setXhsManualRefreshing(false);
    }
  };

  const xhsPosts = xhsData?.posts ?? [];
  const xhsLastUpdated = xhsData?.cached_at
    ? new Date(xhsData.cached_at * 1000).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" })
    : null;
  const xhsError = xhsData?.error;

  const { data: events, isLoading: loadingEvents } = useQuery({
    queryKey: ["events", session?.id, session?.current_turn],
    queryFn: () => intelApi.listEvents(session!.id, session!.current_turn),
    enabled: !!session,
    retry: 2,
    retryDelay: 1000,
  });

  // Get company name from companies API
  const { data: companies, isLoading: loadingCompanies } = useQuery({
    queryKey: ["companies"],
    queryFn: () => gameApi.getCompanies(),
    retry: 2,
    retryDelay: 1000,
  });

  const companyName = companies?.find(
    (c) => c.id === session?.config.company_id
  )?.name ?? "我的品牌";

  // Show loading state during initial hydration or redirect
  if (!session) {
    return (
      <div className="min-h-screen bg-[#FAFBFC] flex items-center justify-center">
        <p className="text-slate-500">正在跳转...</p>
      </div>
    );
  }

  // Show loading state while worldState is being fetched
  if (!worldState) {
    return (
      <div className="max-w-6xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-slate-900">{session.current_year}年 第{session.current_quarter}季度</h1>
        </div>
        <div className="card p-8 text-center">
          <div className="animate-spin w-8 h-8 border-3 border-slate-200 border-t-slate-600 rounded-full mx-auto mb-3" />
          <p className="text-slate-500 text-sm">加载世界状态中...</p>
        </div>
      </div>
    );
  }

  // Show loading state while fetching initial data
  if (loadingCompanies || loadingEvents) {
    return (
      <div className="max-w-6xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-slate-900">{session.current_year}年 第{session.current_quarter}季度</h1>
        </div>
        <div className="card p-8 text-center">
          <div className="animate-spin w-8 h-8 border-3 border-slate-200 border-t-slate-600 rounded-full mx-auto mb-3" />
          <p className="text-slate-500 text-sm">加载中...</p>
        </div>
      </div>
    );
  }

  const metrics = worldState.brand_metrics;
  const coreKPIs = ["cash_reserve", "market_share", "brand_heat", "morale"];
  const secondaryKPIs = [
    "tech_leadership",
    "supply_stability",
    "customer_satisfaction",
    "sales_volume",
    "revenue",
    "profit",
  ];

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            {session.current_year}年 第{session.current_quarter}季度
            <span className="text-sm font-normal px-2 py-0.5 rounded-full text-white" style={{ backgroundColor: "var(--brand-primary)" }}>
              {companyName}
            </span>
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">回合 {session.current_turn} / {session.config.max_turns}</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => setAutoMode(!autoMode)}
            disabled={!session || session.current_turn >= session.config.max_turns}
            className={`px-3 py-2 rounded-lg text-sm font-medium transition-all disabled:opacity-40 ${
              autoMode
                ? "bg-amber-100 text-amber-700 border border-amber-200 hover:bg-amber-200"
                : "bg-purple-50 text-purple-700 border border-purple-200 hover:bg-purple-100"
            }`}
          >
            {autoMode ? "⏸ 暂停" : "▶ 自动"}
          </button>
          {autoMode && (
            <select
              value={autoSpeed}
              onChange={(e) => setAutoSpeed(Number(e.target.value) as 2 | 3 | 4)}
              className="text-xs border border-slate-200 rounded-lg px-2 py-1.5 bg-white text-slate-700"
            >
              <option value={2}>2x</option>
              <option value={3}>3x</option>
              <option value={4}>4x</option>
            </select>
          )}
          {phase === "observe" && (
            <button
              onClick={() => router.replace("/sandbox")}
              className="px-4 py-2 text-white rounded-lg hover:opacity-90 transition-opacity font-medium text-sm" style={{ backgroundColor: "var(--brand-primary)" }}
            >
              进入决策 →
            </button>
          )}
          {phase === "feedback" && (
            <button
              onClick={advanceTurn}
              disabled={loading}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors font-medium text-sm"
            >
              {loading ? "推进中..." : "进入下一回合 →"}
            </button>
          )}
        </div>
      </div>

      {/* Phone Store Animation */}
      <PhoneStore gameId={session.id} companyName={companyName} />

      {/* Core KPIs */}
      <div className="grid grid-cols-4 gap-4">
        {coreKPIs.map((key) => {
          const meta = METRIC_LABELS[key];
          const value = metrics[key as keyof typeof metrics] as number;
          return (
            <div
              key={key}
              className="card p-4 hover:shadow-md transition-shadow group"
            >
              <div className="gradient-highlight-blue absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity" />
              <div className="relative">
                <div className="text-xs text-slate-500 font-medium uppercase tracking-wide">
                  {meta.label}
                </div>
                <div className="text-2xl font-bold text-slate-900 mt-1.5">
                  {value.toFixed(key === "market_share" ? 1 : 0)}
                  <span className="text-sm font-normal text-slate-400 ml-1">
                    {meta.unit}
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Secondary metrics */}
      <div className="card p-5">
        <h2 className="text-sm font-semibold text-slate-700 mb-4 uppercase tracking-wide">详细指标</h2>
        <div className="grid grid-cols-3 gap-x-8 gap-y-3">
          {secondaryKPIs.map((key) => {
            const meta = METRIC_LABELS[key];
            const value = metrics[key as keyof typeof metrics] as number;
            return (
              <div key={key} className="flex items-center justify-between py-1.5 border-b border-slate-100 last:border-0">
                <span className="text-sm text-slate-600">
                  {meta.label}
                </span>
                <span className="text-sm font-semibold text-slate-900">
                  {value.toFixed(1)} <span className="text-xs font-normal text-slate-400">{meta.unit}</span>
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Events */}
      <div className="card p-5">
        <h2 className="text-sm font-semibold text-slate-700 mb-3 uppercase tracking-wide">本回合事件</h2>
        {events && events.length > 0 ? (
          <div className="space-y-2">
            {events.map((event) => (
              <div
                key={event.id}
                className={`p-3 rounded-lg border-l-4 ${
                  event.severity === "critical"
                    ? "bg-red-50/70 border-red-500"
                    : event.severity === "high"
                      ? "bg-orange-50/70 border-orange-500"
                      : event.severity === "medium"
                        ? "bg-yellow-50/70 border-yellow-500"
                        : "bg-slate-50/70 border-slate-300"
                }`}
              >
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-slate-800">{event.title}</span>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-slate-200/70 text-slate-600">
                    {event.category}
                  </span>
                </div>
                <p className="text-sm text-slate-600 mt-1">{event.description}</p>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-400">暂无事件，在新回合中推进游戏以触发事件</p>
        )}
      </div>

      {/* Xiaohongshu Social Feed */}
      <div className="card p-5">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">
              📱 社交动态 · 小红书
            </h2>
            {xhsLastUpdated && (
              <span className="text-xs text-slate-400">
                更新于 {xhsLastUpdated}
              </span>
            )}
            {fetchingXhs && (
              <span className="text-xs text-slate-400 animate-pulse">刷新中...</span>
            )}
          </div>
          <button
            onClick={handleRefreshXhs}
            disabled={xhsManualRefreshing || fetchingXhs}
            className="text-xs px-3 py-1.5 rounded-lg border border-slate-200 text-slate-500 hover:bg-slate-50 disabled:opacity-50 transition-all"
          >
            {xhsManualRefreshing ? "🔄 刷新中..." : "🔄 手动刷新"}
          </button>
        </div>

        {xhsError && !xhsPosts.length && (
          <div className="text-center py-8">
            <p className="text-2xl mb-2">🔌</p>
            <p className="text-sm text-slate-500">{xhsError}</p>
            <p className="text-xs text-slate-400 mt-1">
              请确保 Chrome 浏览器已打开并安装 opencli Browser Bridge 扩展
            </p>
          </div>
        )}

        {loadingXhs && (
          <div className="text-center py-8">
            <div className="animate-spin w-6 h-6 border-2 border-slate-200 border-t-slate-500 rounded-full mx-auto mb-2" />
            <p className="text-sm text-slate-400">加载社交动态中...</p>
          </div>
        )}

        {!loadingXhs && xhsPosts.length > 0 && (
          <div className="grid grid-cols-4 gap-3">
            {xhsPosts.map((post) => (
              <a
                key={post.id}
                href={post.url}
                target="_blank"
                rel="noopener noreferrer"
                className="group block rounded-xl overflow-hidden bg-white border border-slate-100 hover:shadow-md transition-all hover:-translate-y-0.5"
              >
                {/* Cover Image */}
                <div className="aspect-square bg-slate-100 overflow-hidden">
                  {post.cover_proxy || post.cover ? (
                    <img
                      src={post.cover_proxy || post.cover}
                      alt={post.title}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                      loading="lazy"
                      onError={(e) => {
                        (e.target as HTMLImageElement).style.display = "none";
                      }}
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-slate-300 text-4xl">
                      📱
                    </div>
                  )}
                </div>
                {/* Content */}
                <div className="p-2.5">
                  <h3 className="text-xs font-medium text-slate-800 line-clamp-2 leading-snug group-hover:text-rose-600 transition-colors">
                    {post.title}
                  </h3>
                  {post.text && (
                    <p className="text-[11px] text-slate-400 mt-1 line-clamp-2 leading-relaxed">
                      {post.text}
                    </p>
                  )}
                  <div className="flex items-center gap-3 mt-2 pt-2 border-t border-slate-50">
                    <span className="flex items-center gap-1 text-xs text-rose-500">
                      ❤️ {(post.likes ?? 0) >= 1000
                        ? `${((post.likes ?? 0) / 1000).toFixed(1)}k`
                        : post.likes}
                    </span>
                    {post.type && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-500">
                        {post.type}
                      </span>
                    )}
                  </div>
                </div>
              </a>
            ))}
          </div>
        )}

        {!loadingXhs && !xhsError && xhsPosts.length === 0 && (
          <div className="text-center py-6">
            <p className="text-sm text-slate-400">暂无相关笔记</p>
            <p className="text-xs text-slate-300 mt-1">点击"手动刷新"获取最新动态</p>
          </div>
        )}

        {xhsError && xhsPosts.length > 0 && (
          <p className="text-[11px] text-amber-500 mt-2">
            ⚠️ 实时搜索失败：{xhsError}，当前显示缓存数据
          </p>
        )}
      </div>

      {/* Last turn summary */}
      {lastSummary && (
        <div className="card p-5" style={{ borderColor: "var(--brand-primary-light)" }}>
          <h2 className="text-sm font-semibold text-slate-700 mb-2 uppercase tracking-wide">上回合总结</h2>
          <p className="text-sm text-slate-700 leading-relaxed">{lastSummary.narrative}</p>
          {Object.keys(lastSummary.metrics_delta).length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {Object.entries(lastSummary.metrics_delta).map(([k, v]) => (
                <span
                  key={k}
                  className={`text-xs px-2.5 py-1 rounded-full font-medium ${
                    v > 0
                      ? "bg-green-100 text-green-700"
                      : v < 0
                        ? "bg-red-100 text-red-700"
                        : "bg-slate-100 text-slate-600"
                  }`}
                >
                  {k}: {v > 0 ? "+" : ""}
                  {v.toFixed(2)}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

    </div>
  );
}
