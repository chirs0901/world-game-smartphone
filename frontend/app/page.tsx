"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useGameStore } from "@/lib/store/gameStore";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useQuery } from "@tanstack/react-query";
import { gameApi } from "@/lib/api/client";
import { useState, useEffect, Suspense } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { BRAND_COLORS } from "@/lib/config/brandColors";
import type { CompanyOption } from "@/lib/types/game";

// Create a single QueryClient instance outside the component to avoid recreation on every render
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60 * 1000, // 1 minute
      gcTime: 5 * 60 * 1000, // 5 minutes
      retry: 3,
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    },
  },
});

const DIFFICULTY_INFO = {
  easy: { label: "简单", desc: "事件少，资金充裕", color: "green" },
  normal: { label: "普通", desc: "标准挑战", color: "blue" },
  hard: { label: "困难", desc: "事件多，资源紧张", color: "red" },
} as const;

export default function HomePage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-950 to-indigo-950 flex items-center justify-center">
        <p className="text-white">加载中...</p>
      </div>
    }>
      <QueryClientProvider client={queryClient}>
        <HomePageInner />
      </QueryClientProvider>
    </Suspense>
  );
}

function HomePageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const isSwitchMode = searchParams.get("switch") === "true";
  const { session, createGame, loading } = useGameStore();
  const [selectedCompany, setSelectedCompany] = useState<string | null>(null);
  const [difficulty, setDifficulty] = useState<"easy" | "normal" | "hard">("normal");

  // Redirect to dashboard if session exists (after Zustand hydration)
  useEffect(() => {
    if (session) {
      router.replace("/dashboard");
    }
  }, [session]);

  const { data: companies, isLoading: loadingCompanies } = useQuery({
    queryKey: ["companies"],
    queryFn: () => gameApi.getCompanies(),
    enabled: !session,
  });

  // Early return for redirecting state
  if (session) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-950 to-indigo-950 flex items-center justify-center">
        <p className="text-white">正在跳转...</p>
      </div>
    );
  }

  const handleStart = async () => {
    if (!selectedCompany) return;
    await createGame({
      company_id: selectedCompany,
      difficulty,
      initial_cash: 50.0,
      max_turns: 40,
    });
    // Use replace instead of push to avoid adding to history stack
    router.replace("/dashboard");
  };

  const selected = companies?.find((c) => c.id === selectedCompany);
  const brandColor = selectedCompany ? BRAND_COLORS[selectedCompany] : null;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-950 to-indigo-950">
      <div className="max-w-5xl mx-auto px-4 py-12">
        {/* Header */}
        <div className="text-center mb-10">
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            {isSwitchMode ? (
              <>
                <h1 className="text-4xl font-bold text-white mb-2">
                  🔄 切换公司
                </h1>
                <p className="text-blue-300 text-lg">
                  选择新的公司开始经营
                </p>
              </>
            ) : (
              <>
                <h1 className="text-4xl font-bold text-white mb-2">
                  🌍 World Game
                </h1>
                <p className="text-blue-300 text-lg">
                  AI 产业世界模拟器 · 硬件产品经理
                </p>
                <p className="text-slate-400 text-sm mt-1">
                  选择你的公司，在手机行业大展拳脚
                </p>
              </>
            )}
          </motion.div>
        </div>

        {/* Step 1: Company Selection */}
        <div className="mb-8">
          <h2 className="text-white text-lg font-semibold mb-4 flex items-center gap-2">
            <span className="text-white w-7 h-7 rounded-full flex items-center justify-center text-sm" style={{ backgroundColor: brandColor?.primary ?? "#2563EB" }}>
              1
            </span>
            选择你的公司
          </h2>

          {loadingCompanies ? (
            <div className="text-center text-slate-400 py-12">
              加载公司列表中...
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <AnimatePresence>
                {companies?.map((company, index) => (
                  <CompanyCard
                    key={company.id}
                    company={company}
                    selected={selectedCompany === company.id}
                    onClick={() => setSelectedCompany(company.id)}
                    index={index}
                  />
                ))}
              </AnimatePresence>
            </div>
          )}
        </div>

        {/* Step 2: Selected company details */}
        <AnimatePresence>
          {selected && (
            <motion.div
              initial={{ opacity: 0, y: 20, height: 0 }}
              animate={{ opacity: 1, y: 0, height: "auto" }}
              exit={{ opacity: 0, y: 20, height: 0 }}
              className="mb-8 bg-white/10 backdrop-blur-sm rounded-2xl p-6 border border-white/20"
            >
              <div className="flex items-start gap-4">
                <div className="text-5xl">{selected.logo_emoji}</div>
                <div className="flex-1">
                  <h3 className="text-xl font-bold text-white">
                    {selected.name}
                  </h3>
                  <p className="text-blue-300 text-sm italic">
                    {selected.tagline}
                  </p>
                  <p className="text-slate-300 text-sm mt-2">
                    {selected.description}
                  </p>

                  <div className="grid grid-cols-2 gap-4 mt-4">
                    <div>
                      <span className="text-green-400 text-xs font-semibold uppercase">
                        优势
                      </span>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {selected.strengths.map((s) => (
                          <span
                            key={s}
                            className="text-xs px-2 py-0.5 bg-green-500/20 text-green-300 rounded"
                          >
                            {s}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div>
                      <span className="text-red-400 text-xs font-semibold uppercase">
                        劣势
                      </span>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {selected.weaknesses.map((w) => (
                          <span
                            key={w}
                            className="text-xs px-2 py-0.5 bg-red-500/20 text-red-300 rounded"
                          >
                            {w}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>

                  <p className="text-yellow-300 text-xs mt-3 italic">
                    💡 策略提示: {selected.strategy_hint}
                  </p>

                  {/* Base metrics preview */}
                  <div className="mt-4 grid grid-cols-4 gap-2">
                    {[
                      { key: "market_share", label: "市占率", suffix: "%" },
                      { key: "brand_heat", label: "品牌热度", suffix: "" },
                      { key: "tech_leadership", label: "技术力", suffix: "" },
                      { key: "cash_reserve", label: "资金", suffix: "亿" },
                    ].map(({ key, label, suffix }) => (
                      <div
                        key={key}
                        className="text-center bg-white/5 rounded-lg py-2"
                      >
                        <div className="text-white font-bold">
                          {(selected.base_metrics[key] ?? 0).toFixed(0)}
                          <span className="text-xs font-normal text-slate-400">
                            {suffix}
                          </span>
                        </div>
                        <div className="text-xs text-slate-400">{label}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Step 3: Difficulty */}
        {selectedCompany && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mb-8"
          >
            <h2 className="text-white text-lg font-semibold mb-4 flex items-center gap-2">
              <span className="text-white w-7 h-7 rounded-full flex items-center justify-center text-sm" style={{ backgroundColor: brandColor?.primary ?? "#2563EB" }}>
                2
              </span>
              选择难度
            </h2>
            <div className="flex gap-3">
              {(["easy", "normal", "hard"] as const).map((d) => {
                const info = DIFFICULTY_INFO[d];
                const isRecommended = selected?.difficulty === d;
                return (
                  <button
                    key={d}
                    onClick={() => setDifficulty(d)}
                    className={`flex-1 py-3 px-4 rounded-xl text-sm font-medium transition-all border-2 ${
                      difficulty === d
                        ? d === "easy"
                          ? "bg-green-600/20 border-green-500 text-green-300"
                          : d === "normal"
                            ? "bg-blue-600/20 border-blue-500 text-blue-300"
                            : "bg-red-600/20 border-red-500 text-red-300"
                        : "bg-white/5 border-white/10 text-slate-400 hover:border-white/30"
                    }`}
                  >
                    <div>{info.label}</div>
                    <div className="text-xs opacity-70 mt-0.5">
                      {info.desc}
                    </div>
                    {isRecommended && (
                      <div className="text-xs mt-1 text-yellow-400">
                        ⭐ 推荐
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
          </motion.div>
        )}

        {/* Start Button */}
        {selectedCompany && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <button
              onClick={handleStart}
              disabled={loading}
              className="w-full py-4 text-white rounded-xl font-bold text-lg disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                            style={brandColor ? {
                              background: `linear-gradient(to right, ${brandColor.primary}, ${brandColor.primaryDark})`,
                              boxShadow: `0 10px 15px -3px ${brandColor.primary}40`
                            } : {}}
            >
              {loading
                ? "创建世界中..."
                : isSwitchMode
                  ? `切换为 ${selected?.name} 并开始`
                  : `以 ${selected?.name} 身份开始游戏`}
            </button>
          </motion.div>
        )}

        <p className="text-xs text-slate-500 text-center mt-8">
          每回合模拟一个季度，共40回合。通过观察、决策、执行、反馈循环，打造你的手机帝国。
        </p>
      </div>
    </div>
  );
}

function CompanyCard({
  company,
  selected,
  onClick,
  index,
}: {
  company: CompanyOption;
  selected: boolean;
  onClick: () => void;
  index: number;
}) {
  const colors = BRAND_COLORS[company.id];
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      onClick={onClick}
      className={`cursor-pointer rounded-xl p-4 border-2 transition-all ${
        selected
          ? "shadow-lg"
          : "bg-white/5 border-white/10 hover:border-white/30 hover:bg-white/10"
      }`}
      style={selected && colors ? {
        borderColor: colors.primary,
        backgroundColor: `${colors.primary}33`,
        boxShadow: `0 4px 6px -1px ${colors.primary}33`,
      } : undefined}
    >
      <div className="flex items-center gap-3">
        <div className="text-3xl">{company.logo_emoji}</div>
        <div>
          <h3
            className={`font-bold ${selected ? "text-white" : "text-white"}`}
            style={selected && colors ? { color: colors.primaryLight } : undefined}
          >
            {company.name}
          </h3>
          <p className="text-xs text-slate-400">
            {company.country} · {company.tagline}
          </p>
        </div>
      </div>

      <div className="mt-3 flex flex-wrap gap-1">
        {company.strengths.slice(0, 3).map((s) => (
          <span
            key={s}
            className="text-xs px-1.5 py-0.5 bg-green-500/15 text-green-400 rounded"
          >
            {s}
          </span>
        ))}
      </div>

      <div className="mt-2 flex items-center gap-3 text-xs text-slate-500">
        <span>
          市占率{" "}
          <span className="text-white font-semibold">
            {(company.base_metrics.market_share ?? 0).toFixed(0)}%
          </span>
        </span>
        <span>
          热度{" "}
          <span className="text-white font-semibold">
            {(company.base_metrics.brand_heat ?? 0).toFixed(0)}
          </span>
        </span>
        <span
          className={`ml-auto px-1.5 py-0.5 rounded text-xs ${
            company.difficulty === "easy"
              ? "bg-green-500/20 text-green-400"
              : company.difficulty === "hard"
                ? "bg-red-500/20 text-red-400"
                : "bg-blue-500/20 text-blue-400"
          }`}
        >
          {company.difficulty === "easy"
            ? "简单"
            : company.difficulty === "hard"
              ? "困难"
              : "普通"}
        </span>
      </div>
    </motion.div>
  );
}
