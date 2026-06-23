"use client";

import { useGameStore } from "@/lib/store/gameStore";
import { useQuery } from "@tanstack/react-query";
import { intelApi, rssApi } from "@/lib/api/client";
import { useState } from "react";
import type { EventSeverity } from "@/lib/types/intel";

const SEVERITY_COLORS: Record<EventSeverity, string> = {
  critical: "border-red-500 bg-red-50",
  high: "border-orange-500 bg-orange-50",
  medium: "border-yellow-500 bg-yellow-50",
  low: "border-slate-300 bg-slate-50",
};

const SEVERITY_LABELS: Record<EventSeverity, string> = {
  critical: "紧急",
  high: "重要",
  medium: "一般",
  low: "低",
};

export default function IntelPage() {
  const { session } = useGameStore();
  const [filter, setFilter] = useState<string>("all");
  const [selectedEvent, setSelectedEvent] = useState<string | null>(null);
  const [tab, setTab] = useState<"events" | "rss">("events");

  const { data: events } = useQuery({
    queryKey: ["events", session?.id, session?.current_turn],
    queryFn: () => intelApi.listEvents(session!.id, session!.current_turn),
    enabled: !!session && tab === "events",
  });

  const { data: news } = useQuery({
    queryKey: ["news", session?.id, session?.current_turn],
    queryFn: () => intelApi.listNews(session!.id, session!.current_turn),
    enabled: !!session && tab === "events",
  });

  // RSS feed state
  const [rssCategory, setRssCategory] = useState<string>("");
  const [rssRefreshing, setRssRefreshing] = useState(false);

  const { data: rssFeeds } = useQuery({
    queryKey: ["rss-feeds"],
    queryFn: () => rssApi.getFeeds(),
    enabled: tab === "rss",
    staleTime: 300000,
  });

  const { data: rssData, refetch: refetchRss } = useQuery({
    queryKey: ["rss-items", rssCategory],
    queryFn: () => rssApi.getItems(false, rssCategory),
    enabled: tab === "rss",
    staleTime: 120000,
  });

  const handleRssRefresh = async () => {
    setRssRefreshing(true);
    try {
      await rssApi.refresh();
      await refetchRss();
    } catch (e) {
      console.error("RSS refresh failed:", e);
    } finally {
      setRssRefreshing(false);
    }
  };

  const categories = ["all", "market", "technology", "supply_chain", "policy", "competitor", "consumer"];
  const categoryLabels: Record<string, string> = {
    all: "全部",
    market: "市场",
    technology: "技术",
    supply_chain: "供应链",
    policy: "政策",
    competitor: "竞品",
    consumer: "消费者",
  };

  const filteredEvents = events?.filter(
    (e) => filter === "all" || e.category === filter
  );

  const selected = events?.find((e) => e.id === selectedEvent);

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header + Tabs */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h1 className="text-2xl font-bold text-slate-900">情报中心</h1>
          <div className="flex rounded-lg bg-slate-100 p-0.5">
            <button
              onClick={() => setTab("events")}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                tab === "events" ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-700"
              }`}
            >
              游戏事件
            </button>
            <button
              onClick={() => setTab("rss")}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                tab === "rss" ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-700"
              }`}
            >
              行业资讯
            </button>
          </div>
        </div>
        {tab === "rss" && (
          <button
            onClick={handleRssRefresh}
            disabled={rssRefreshing}
            className="px-3 py-1.5 text-sm text-white rounded-lg hover:opacity-90 disabled:opacity-50"
            style={{ backgroundColor: "var(--brand-primary)" }}
          >
            {rssRefreshing ? "刷新中..." : "刷新资讯"}
          </button>
        )}
      </div>

      {/* ─── Game Events Tab ─── */}
      {tab === "events" && (
        <>
          {/* Category filter */}
          <div className="flex gap-2">
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setFilter(cat)}
                className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
                  filter === cat
                    ? "text-white"
                    : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-50"
                }`}
                style={filter === cat ? { backgroundColor: "var(--brand-primary)" } : undefined}
              >
                {categoryLabels[cat]}
              </button>
            ))}
          </div>

          <div className="grid grid-cols-3 gap-6">
            {/* Events list */}
            <div className="col-span-2 space-y-3">
              <h2 className="text-lg font-semibold text-slate-900">事件列表</h2>
              {filteredEvents && filteredEvents.length > 0 ? (
                filteredEvents.map((event) => (
                  <div
                    key={event.id}
                    onClick={() => setSelectedEvent(event.id)}
                    className={`p-4 rounded-xl border-l-4 cursor-pointer transition-all hover:shadow-md ${
                      SEVERITY_COLORS[event.severity]
                    }`}
                    style={selectedEvent === event.id ? { boxShadow: "0 0 0 2px var(--brand-primary)" } : undefined}
                  >
                    <div className="flex items-center justify-between">
                      <h3 className="font-semibold text-slate-900">{event.title}</h3>
                      <div className="flex items-center gap-2">
                        <span className="text-xs px-2 py-0.5 rounded bg-slate-200 text-slate-600">
                          {categoryLabels[event.category] || event.category}
                        </span>
                        <span className={`text-xs px-2 py-0.5 rounded ${
                          event.severity === "critical" ? "bg-red-200 text-red-700"
                          : event.severity === "high" ? "bg-orange-200 text-orange-700"
                          : "bg-slate-100 text-slate-500"
                        }`}>
                          {SEVERITY_LABELS[event.severity]}
                        </span>
                      </div>
                    </div>
                    <p className="text-sm text-slate-700 mt-1">{event.description}</p>
                  </div>
                ))
              ) : (
                <p className="text-slate-600 text-sm py-8 text-center">暂无事件</p>
              )}

              {/* News */}
              {news && news.length > 0 && (
                <>
                  <h2 className="text-lg font-semibold text-slate-900 mt-6">行业新闻</h2>
                  {news.map((item) => (
                    <div key={item.id} className="bg-white p-4 rounded-xl shadow-sm border border-slate-200">
                      <h3 className="font-medium text-slate-900">{item.headline}</h3>
                      <p className="text-sm text-slate-700 mt-1">{item.content}</p>
                      <div className="text-xs text-slate-400 mt-2">{item.source} · {item.turn}回合</div>
                    </div>
                  ))}
                </>
              )}
            </div>

            {/* Event detail */}
            <div className="col-span-1">
              {selected ? (
                <div className="bg-white rounded-xl p-4 shadow-sm border border-slate-200 sticky top-6">
                  <h2 className="text-lg font-semibold text-slate-900">{selected.title}</h2>
                  <p className="text-sm text-slate-600 mt-2">{selected.description}</p>
                  {selected.impacts.length > 0 && (
                    <div className="mt-4">
                      <h3 className="text-sm font-semibold text-slate-700">影响评估</h3>
                      <div className="mt-2 space-y-2">
                        {selected.impacts.map((impact, i) => (
                          <div key={i} className={`text-sm px-3 py-2 rounded-lg ${
                            impact.direction === "up" ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"
                          }`}>
                            {impact.metric}: {impact.direction === "up" ? "↑" : "↓"} {impact.magnitude}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {selected.response_options.length > 0 && (
                    <div className="mt-4">
                      <h3 className="text-sm font-semibold text-slate-700">应对方案</h3>
                      <ul className="mt-2 space-y-1">
                        {selected.response_options.map((opt, i) => (
                          <li key={i} className="text-sm text-slate-600 flex items-center gap-2">
                            <span className="w-5 h-5 rounded-full flex items-center justify-center text-xs"
                              style={{ backgroundColor: "var(--brand-light)", color: "var(--brand-primary)" }}>{i + 1}</span>
                            {opt}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ) : (
                <div className="bg-white rounded-xl p-4 shadow-sm border border-slate-200 text-center text-slate-500 text-sm">
                  点击事件查看详情
                </div>
              )}
            </div>
          </div>
        </>
      )}

      {/* ─── RSS Industry Intelligence Tab ─── */}
      {tab === "rss" && (
        <div className="grid grid-cols-4 gap-6">
          {/* Left: Category sidebar */}
          <div className="col-span-1">
            <div className="bg-white rounded-xl p-4 shadow-sm border border-slate-200 sticky top-6">
              <h3 className="font-semibold text-slate-900 text-sm mb-3">资讯分类</h3>
              <div className="space-y-1">
                <button
                  onClick={() => setRssCategory("")}
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                    rssCategory === "" ? "bg-slate-100 text-slate-900 font-medium" : "text-slate-600 hover:bg-slate-50"
                  }`}
                >
                  全部来源
                </button>
                {rssFeeds?.categories?.map((cat) => (
                  <button
                    key={cat}
                    onClick={() => setRssCategory(cat)}
                    className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                      rssCategory === cat ? "bg-slate-100 text-slate-900 font-medium" : "text-slate-600 hover:bg-slate-50"
                    }`}
                  >
                    {cat}
                  </button>
                ))}
              </div>

              {/* Feed source list */}
              {rssFeeds?.feeds && (
                <div className="mt-4 pt-4 border-t border-slate-100">
                  <h4 className="text-xs font-medium text-slate-500 mb-2">订阅源 ({rssFeeds.feeds.length})</h4>
                  <div className="space-y-1 max-h-60 overflow-y-auto">
                    {rssFeeds.feeds.map((f) => (
                      <div key={f.name} className="text-xs text-slate-500 truncate" title={f.name}>
                        {f.name}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Right: RSS items */}
          <div className="col-span-3 space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-900">
                实时行业资讯
                {rssData?.items && <span className="text-sm font-normal text-slate-500 ml-2">({rssData.items.length}条)</span>}
              </h2>
            </div>

            {rssData?.items && rssData.items.length > 0 ? (
              rssData.items.map((item) => (
                <a
                  key={item.id}
                  href={item.link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block bg-white rounded-xl p-4 shadow-sm border border-slate-200 hover:border-slate-300 hover:shadow-md transition-all"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <h3 className="font-medium text-slate-900 leading-snug">{item.title}</h3>
                      {item.description && (
                        <p className="text-sm text-slate-600 mt-1 line-clamp-2">{item.description}</p>
                      )}
                      <div className="flex items-center gap-3 mt-2">
                        <span className="text-xs text-slate-400">{item.source_name}</span>
                        <span className="text-xs px-2 py-0.5 rounded bg-slate-100 text-slate-500">{item.source_category}</span>
                        {item.published && (
                          <span className="text-xs text-slate-400">{item.published}</span>
                        )}
                      </div>
                    </div>
                    <span className="text-slate-300 text-lg shrink-0 mt-1">→</span>
                  </div>
                </a>
              ))
            ) : (
              <div className="bg-white rounded-xl p-8 shadow-sm border border-slate-200 text-center">
                <p className="text-slate-600 mb-2">点击右上角"刷新资讯"获取最新行业情报</p>
                <p className="text-xs text-slate-500">
                  覆盖 Counterpoint、IDC、TrendForce 等 {rssFeeds?.feeds?.length || 20}+ 权威信息源
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
