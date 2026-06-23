"use client";

import { useGameStore } from "@/lib/store/gameStore";
import { simulationApi, techApi } from "@/lib/api/client";
import { useQuery } from "@tanstack/react-query";
import { useState, useEffect, useCallback } from "react";
import type { PlayerDecision, DecisionCategory, SimulationResult, ComponentCategory, TechSelection, TechPredictResponse, TechTier } from "@/lib/types/simulation";

const STORAGE_KEY = "world-game-sandbox-history";

interface SandboxHistory {
  id: string;
  timestamp: number;
  gameId: string;
  turn: number;
  decisions: { action: string; category: DecisionCategory; budget: number }[];
  results: SimulationResult[];
  totalCost: number;
}

const CATEGORY_LABELS: Record<DecisionCategory, string> = {
  product: "产品",
  rd: "研发",
  marketing: "营销",
  supply: "供应链",
  finance: "财务",
  hr: "人力",
};

const PRESET_DECISIONS: { category: DecisionCategory; action: string; budget: number }[] = [
  { category: "rd", action: "投入折叠屏技术研发", budget: 10 },
  { category: "rd", action: "升级AI芯片性能", budget: 8 },
  { category: "product", action: "推出中端新品线", budget: 6 },
  { category: "product", action: "旗舰机影像系统升级", budget: 5 },
  { category: "marketing", action: "全渠道品牌营销活动", budget: 8 },
  { category: "marketing", action: "KOL社交媒体推广", budget: 3 },
  { category: "supply", action: "与台积电签订长期协议", budget: 12 },
  { category: "supply", action: "多元化供应商策略", budget: 4 },
  { category: "finance", action: "扩大现金储备（保守策略）", budget: 0 },
  { category: "hr", action: "招聘顶级技术人才", budget: 5 },
];

const TECH_CATEGORY_LABELS: Record<string, string> = {
  soc: "芯片 SoC",
  display: "屏幕",
  camera: "影像",
  battery: "电池",
  storage: "存储",
  cooling: "散热",
  communication: "通信",
  ai_npu: "AI引擎",
};

const TIER_LABELS: Record<TechTier, string> = {
  short_term: "短期 (1年)",
  mid_term: "中期 (3年)",
  long_term: "长期 (5年)",
};

export default function SandboxPage() {
  const { session, setPhase } = useGameStore();
  const [tab, setTab] = useState<"simulate" | "roadmap">("simulate");

  // ── Decision Simulation State ──
  const [selected, setSelected] = useState<number[]>([]);
  const [simulating, setSimulating] = useState(false);
  const [results, setResults] = useState<SimulationResult[] | null>(null);
  const [history, setHistory] = useState<SandboxHistory[]>(() => {
    if (typeof window === "undefined") return [];
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]"); }
    catch { return []; }
  });

  // ── Tech Roadmap State ──
  const [techSelections, setTechSelections] = useState<Record<string, string>>({});
  const [targetTier, setTargetTier] = useState<TechTier>("short_term");
  const [techResult, setTechResult] = useState<TechPredictResponse | null>(null);
  const [techPredicting, setTechPredicting] = useState(false);

  // Fetch catalog on mount
  const { data: catalog } = useQuery({
    queryKey: ["tech-catalog"],
    queryFn: () => techApi.getCatalog(),
    staleTime: Infinity,
  });

  // Initialize defaults from catalog
  useEffect(() => {
    if (catalog?.categories) {
      const defaults: Record<string, string> = {};
      catalog.categories.forEach((cat) => {
        if (cat.default_option_id) {
          defaults[cat.id] = cat.default_option_id;
        }
      });
      setTechSelections((prev) => ({ ...defaults, ...prev }));
    }
  }, [catalog]);

  // Auto-predict when selections change
  useEffect(() => {
    if (!catalog || Object.keys(techSelections).length === 0) return;
    const selections: TechSelection[] = Object.entries(techSelections).map(
      ([category_id, option_id]) => ({ category_id, option_id })
    );
    if (selections.length < 7) return;
    const run = async () => {
      setTechPredicting(true);
      try {
        const res = await techApi.predict({ selections, target_tier: targetTier });
        setTechResult(res);
      } catch (e) {
        console.error("Tech predict failed:", e);
      } finally {
        setTechPredicting(false);
      }
    };
    run();
  }, [techSelections, targetTier, catalog]);

  const handleTechSelect = (categoryId: string, optionId: string) => {
    setTechSelections((prev) => ({ ...prev, [categoryId]: optionId }));
  };

  const toggleDecision = (index: number) => {
    setSelected((prev) =>
      prev.includes(index) ? prev.filter((i) => i !== index) : [...prev, index]
    );
  };

  const totalBudget = selected.reduce((sum, i) => sum + PRESET_DECISIONS[i].budget, 0);

  const handleSimulate = async () => {
    if (!session || selected.length === 0) return;
    setSimulating(true);
    try {
      const decisions: PlayerDecision[] = selected.map((i, idx) => ({
        ...PRESET_DECISIONS[i],
        priority: idx + 1,
      }));
      const res = await simulationApi.simulate(session.id, decisions);
      setResults(res.results);
      setPhase("execute");
      const entry: SandboxHistory = {
        id: Date.now().toString(),
        timestamp: Date.now(),
        gameId: session.id,
        turn: session.current_turn,
        decisions: selected.map((i) => ({
          action: PRESET_DECISIONS[i].action,
          category: PRESET_DECISIONS[i].category,
          budget: PRESET_DECISIONS[i].budget,
        })),
        results: res.results,
        totalCost: totalBudget,
      };
      const newHistory = [entry, ...history].slice(0, 20);
      setHistory(newHistory);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(newHistory));
    } catch (e) {
      console.error("Simulation failed:", e);
    } finally {
      setSimulating(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header + Tab Switch */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h1 className="text-2xl font-bold text-slate-900">推演沙盘</h1>
          <div className="flex rounded-lg bg-slate-100 p-0.5">
            <button
              onClick={() => setTab("simulate")}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                tab === "simulate" ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-700"
              }`}
            >
              策略推演
            </button>
            <button
              onClick={() => setTab("roadmap")}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                tab === "roadmap" ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-700"
              }`}
            >
              器件路线图
            </button>
          </div>
        </div>
        {tab === "simulate" && (
          <div className="text-sm">
            <span className="text-slate-700">预算: </span><strong className="text-slate-900">{totalBudget}</strong><span className="text-slate-400"> 亿元</span>
            <span className="text-slate-700"> | 已选: </span><strong className="text-slate-900">{selected.length}</strong><span className="text-slate-400"> 项</span>
          </div>
        )}
      </div>

      {/* ─── Strategy Simulation Tab ─── */}
      {tab === "simulate" && (
        <>
          {/* Decision options */}
          <div className="grid grid-cols-2 gap-3">
            {PRESET_DECISIONS.map((d, i) => (
              <div
                key={i}
                onClick={() => toggleDecision(i)}
                className={`p-4 rounded-xl border-2 cursor-pointer transition-all ${
                  selected.includes(i)
                    ? "bg-[var(--brand-light)]"
                    : "border-slate-200 bg-white hover:border-slate-300"
                }`}
                style={selected.includes(i) ? { borderColor: "var(--brand-primary)" } : undefined}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs px-2 py-0.5 rounded bg-slate-100 text-slate-600">
                    {CATEGORY_LABELS[d.category]}
                  </span>
                  <span className="text-sm font-semibold text-slate-700">
                    {d.budget > 0 ? `${d.budget}亿` : "免费"}
                  </span>
                </div>
                <h3 className="font-medium text-slate-900 mt-2">{d.action}</h3>
              </div>
            ))}
          </div>

          <button
            onClick={handleSimulate}
            disabled={simulating || selected.length === 0}
            className="w-full py-3 text-white rounded-lg font-semibold hover:opacity-90 disabled:opacity-50"
            style={{ backgroundColor: "var(--brand-primary)" }}
          >
            {simulating ? "推演计算中..." : `推演 ${selected.length} 项决策`}
          </button>

          {results && (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold text-slate-900">推演结果</h2>
              {results.map((result, ri) => (
                <div key={ri} className="bg-white rounded-xl p-4 shadow-sm border border-slate-200">
                  <h3 className="font-semibold text-slate-900">{result.decision.action}</h3>
                  {result.narrative && (
                    <p className="text-sm text-slate-700 mt-1">{result.narrative}</p>
                  )}
                  {result.direct_impacts.length > 0 && (
                    <div className="mt-3">
                      <div className="text-sm font-medium text-slate-700 mb-2">直接影响</div>
                      <div className="flex flex-wrap gap-2">
                        {result.direct_impacts.map((impact, ii) => (
                          <span key={ii} className={`text-xs px-3 py-1.5 rounded-lg ${
                            impact.delta > 0 ? "bg-green-100 text-green-700"
                            : impact.delta < 0 ? "bg-red-100 text-red-700"
                            : "bg-slate-100 text-slate-600"
                          }`}>
                            {impact.metric}: {impact.delta > 0 ? "+" : ""}{impact.delta.toFixed(2)} ({impact.delta_percent > 0 ? "+" : ""}{impact.delta_percent.toFixed(1)}%)
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {result.chain_effects.length > 0 && (
                    <div className="mt-3">
                      <div className="text-sm font-medium text-slate-700 mb-2">连锁效应</div>
                      {result.chain_effects.map((ce, ci) => (
                        <div key={ci} className="text-xs text-slate-600 ml-2">L{ce.order}: {ce.description}</div>
                      ))}
                    </div>
                  )}
                  {result.risk_warnings.length > 0 && (
                    <div className="mt-3 bg-amber-50 border border-amber-200 rounded-lg p-2">
                      <div className="text-xs font-medium text-amber-700">风险提示</div>
                      {result.risk_warnings.map((w, wi) => (
                        <div key={wi} className="text-xs text-amber-600 mt-1">{w}</div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* History */}
          {history.length > 0 && (
            <div className="mt-8">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-lg font-semibold text-slate-900">历史推演</h2>
                <button onClick={() => { setHistory([]); localStorage.removeItem(STORAGE_KEY); }}
                  className="text-xs text-red-500 hover:underline">清除历史</button>
              </div>
              <div className="space-y-2">
                {history.map((h) => (
                  <div key={h.id} className="bg-white rounded-xl p-3 shadow-sm border border-slate-200">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-slate-700 font-medium">
                        回合 {h.turn} · {h.decisions.length} 项决策 · 预算 {h.totalCost}亿
                      </span>
                      <span className="text-xs text-slate-400">
                        {new Date(h.timestamp).toLocaleString("zh-CN", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
                      </span>
                    </div>
                    <div className="text-xs text-slate-500 mt-1 truncate">{h.decisions.map(d => d.action).join("、")}</div>
                    <button onClick={() => setResults(h.results)} className="text-xs mt-1 hover:underline"
                      style={{ color: "var(--brand-primary)" }}>查看详情 →</button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* ─── Tech Roadmap Tab ─── */}
      {tab === "roadmap" && (
        <div className="space-y-6">
          {/* Market period selector */}
          <div className="flex items-center gap-3">
            <span className="text-sm font-medium text-slate-700">市场周期：</span>
            {(["short_term", "mid_term", "long_term"] as TechTier[]).map((tier) => (
              <button
                key={tier}
                onClick={() => setTargetTier(tier)}
                className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
                  targetTier === tier
                    ? "text-white"
                    : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-50"
                }`}
                style={targetTier === tier ? { backgroundColor: "var(--brand-primary)" } : undefined}
              >
                {TIER_LABELS[tier]}
              </button>
            ))}
            <span className="text-xs text-slate-400 ml-auto">
              选择短期市场周期时，中/远期技术将承受成熟度惩罚
            </span>
          </div>

          {/* Component Selection Grid */}
          <div className="grid grid-cols-2 gap-4">
            {catalog?.categories?.map((cat) => {
              const selectedId = techSelections[cat.id] || cat.default_option_id;
              const selectedOpt = cat.options.find(o => o.id === selectedId);
              return (
                <div key={cat.id} className="bg-white rounded-xl p-4 shadow-sm border border-slate-200">
                  <h3 className="font-semibold text-slate-900 mb-3">{TECH_CATEGORY_LABELS[cat.id] || cat.name}</h3>
                  <div className="space-y-2">
                    {cat.options.map((opt) => (
                      <button
                        key={opt.id}
                        onClick={() => handleTechSelect(cat.id, opt.id)}
                        className={`w-full text-left p-3 rounded-lg border-2 transition-all text-sm ${
                          selectedId === opt.id
                            ? "bg-[var(--brand-light)]"
                            : "border-slate-100 hover:border-slate-300"
                        }`}
                        style={selectedId === opt.id ? { borderColor: "var(--brand-primary)" } : undefined}
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-medium text-slate-900">{opt.name}</span>
                          <div className="flex items-center gap-1.5">
                            {opt.research_type !== "procurement" && (
                              <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                                opt.research_type === "self_developed"
                                  ? "bg-purple-100 text-purple-700"
                                  : "bg-indigo-100 text-indigo-700"
                              }`}>
                                {opt.research_type === "self_developed" ? "自研" : "联合研发"}
                              </span>
                            )}
                            {opt.supplier_lock_required && (
                              <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-100 text-amber-700">独家供应</span>
                            )}
                            <span className="text-xs text-slate-500">
                              {opt.tier === "short_term" ? "1年" : opt.tier === "mid_term" ? "3年" : "5年"}
                            </span>
                          </div>
                        </div>
                        <div className="flex items-center gap-3 mt-1.5 text-xs text-slate-500">
                          <span>成本 {opt.cost_share_pct}%</span>
                          <span>质量 {opt.quality_score}</span>
                          <span>成熟度 {Math.round(opt.tech_maturity * 100)}%</span>
                          {opt.space_cost > 0 && <span>空间 {opt.space_cost}</span>}
                        </div>
                        {opt.conflicts_with.length > 0 && (
                          <div className="text-[10px] text-rose-500 mt-1">⚠ 冲突器件: {opt.conflicts_with.join(", ")}</div>
                        )}
                        {opt.description && (
                          <p className="text-xs text-slate-400 mt-1 truncate">{opt.description}</p>
                        )}
                      </button>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Prediction Results Panel */}
          {techResult && (
            <div className="bg-white rounded-xl p-6 shadow-sm border border-slate-200">
              <div className="flex items-center gap-2 mb-4">
                <h2 className="text-lg font-semibold text-slate-900">器件影响预测</h2>
                {techPredicting && <span className="text-xs text-slate-500 animate-pulse">更新中...</span>}
              </div>

              {/* ── BOM 铁三角：成本、质量、空间 ── */}
              <div className="grid grid-cols-4 gap-4 mb-6">
                <div className="bg-slate-50 rounded-xl p-4 text-center">
                  <div className="text-xs text-slate-500 mb-1">BOM成本占比</div>
                  <div className="text-2xl font-bold text-slate-900">{techResult.total_bom_cost_pct}%</div>
                  <div className={`text-xs mt-1 ${techResult.bom_cost_vs_baseline_pct > 0 ? "text-red-600" : "text-green-600"}`}>
                    {techResult.bom_cost_vs_baseline_pct > 0 ? "+" : ""}{techResult.bom_cost_vs_baseline_pct}% vs 基准
                  </div>
                </div>
                <div className="bg-slate-50 rounded-xl p-4 text-center">
                  <div className="text-xs text-slate-500 mb-1">综合质量分</div>
                  <div className={`text-2xl font-bold ${techResult.quality_score >= 80 ? "text-green-600" : techResult.quality_score >= 70 ? "text-amber-600" : "text-red-600"}`}>{techResult.quality_score}</div>
                  <div className="text-xs text-slate-400 mt-1">满分100</div>
                </div>
                <div className="bg-slate-50 rounded-xl p-4 text-center">
                  <div className="text-xs text-slate-500 mb-1">预估不良率</div>
                  <div className={`text-2xl font-bold ${techResult.ffr_rate > 1.0 ? "text-red-600" : "text-green-600"}`}>{techResult.ffr_rate}%</div>
                  <div className="text-xs text-slate-400 mt-1">行业 ~0.5%</div>
                </div>
                <div className="bg-slate-50 rounded-xl p-4 text-center">
                  <div className="text-xs text-slate-500 mb-1">用户口碑</div>
                  <div className={`text-2xl font-bold ${techResult.reputation_score >= 70 ? "text-green-600" : techResult.reputation_score >= 50 ? "text-amber-600" : "text-red-600"}`}>{techResult.reputation_score}</div>
                  <div className="text-xs text-slate-400 mt-1">满分100</div>
                </div>
              </div>

              {/* ── 内部空间预算条 ── */}
              <div className="mb-4">
                <div className="flex items-center justify-between text-sm mb-1">
                  <span className="text-slate-700 font-medium">
                    内部空间消耗
                    {techResult.space_over_budget && <span className="text-rose-500 ml-2 text-xs">⚠ 超限</span>}
                  </span>
                  <span className={`text-sm font-semibold ${techResult.space_over_budget ? "text-rose-600" : "text-slate-700"}`}>
                    {techResult.total_space_cost} / {techResult.space_budget}
                  </span>
                </div>
                <div className="w-full h-2.5 bg-slate-200 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${
                      techResult.total_space_cost / techResult.space_budget > 0.9
                        ? "bg-red-500"
                        : techResult.total_space_cost / techResult.space_budget > 0.7
                          ? "bg-amber-500"
                          : "bg-emerald-500"
                    }`}
                    style={{ width: `${Math.min(100, (techResult.total_space_cost / techResult.space_budget) * 100)}%` }}
                  />
                </div>
                <div className="text-xs text-slate-400 mt-1">
                  空间超出预算将导致机身过厚、散热不良，并扣减质量和口碑
                </div>
              </div>

              {/* Reputation Prediction */}
              <div className={`p-4 rounded-lg mb-4 ${
                techResult.reputation_score >= 70 ? "bg-green-50 border border-green-200" :
                techResult.reputation_score >= 50 ? "bg-amber-50 border border-amber-200" :
                "bg-red-50 border border-red-200"
              }`}>
                <div className="text-sm font-medium text-slate-800">{techResult.reputation_prediction}</div>
                <div className="text-xs text-slate-600 mt-1">{techResult.competitive_advantage}</div>
              </div>

              {/* ── 跨周期技术成熟度惩罚 ── */}
              {techResult.maturity_penalties.length > 0 && (
                <div className="mb-4 p-4 rounded-lg border border-orange-200 bg-orange-50">
                  <div className="text-sm font-semibold text-orange-800 mb-2">⚡ 跨周期技术成熟度惩罚</div>
                  <div className="space-y-2">
                    {techResult.maturity_penalties.map((p, i) => (
                      <div key={i} className="text-xs bg-white/60 rounded-lg p-2">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-medium text-orange-800">{p.option_name}</span>
                          <span className="text-orange-500">({p.option_tier}技术 → {p.target_tier}市场)</span>
                        </div>
                        <div className="flex gap-3 text-orange-700">
                          <span>{p.cost_impact}</span>
                          <span>{p.ffr_impact}</span>
                          <span>{p.quality_impact}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* ── 内部空间冲突 ── */}
              {techResult.space_conflicts.length > 0 && (
                <div className="mb-4 p-4 rounded-lg border border-rose-200 bg-rose-50">
                  <div className="text-sm font-semibold text-rose-800 mb-2">🔧 内部空间冲突</div>
                  <div className="space-y-1">
                    {techResult.space_conflicts.map((c, i) => (
                      <div key={i} className="text-xs text-rose-700">
                        <span className="font-medium">{c.option_a}</span> ↔ <span className="font-medium">{c.option_b}</span>
                        <div className="text-rose-500 mt-0.5">{c.description}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* ── 自研风险 ── */}
              {techResult.research_risks.length > 0 && (
                <div className="mb-4 p-4 rounded-lg border border-purple-200 bg-purple-50">
                  <div className="text-sm font-semibold text-purple-800 mb-2">🧪 自研/联合研发展风险</div>
                  <div className="space-y-2">
                    {techResult.research_risks.map((r, i) => (
                      <div key={i} className="text-xs bg-white/60 rounded-lg p-2">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-medium text-purple-800">{r.option_name}</span>
                          <span className={`px-1.5 py-0.5 rounded text-[10px] ${
                            r.research_type === "完全自研" ? "bg-purple-200 text-purple-700" : "bg-indigo-200 text-indigo-700"
                          }`}>{r.research_type}</span>
                        </div>
                        <div className="text-purple-600">{r.impact}</div>
                        <div className="text-purple-400 mt-0.5">{r.description}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Selling Points */}
              {techResult.selling_points.length > 0 && (
                <div className="mb-4">
                  <div className="text-sm font-medium text-slate-700 mb-2">核心卖点 (按趋势加权)</div>
                  <div className="flex flex-wrap gap-2">
                    {techResult.selling_points.map((sp, i) => (
                      <span key={i} className="text-xs px-3 py-1.5 rounded-lg bg-blue-50 text-blue-700 font-medium">
                        {sp.tag} <span className="text-blue-400 ml-1">{sp.weight.toFixed(1)}</span>
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Risk Warnings */}
              {techResult.risk_warnings.length > 0 && (
                <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
                  <div className="text-xs font-medium text-amber-700 mb-1">全部风险提示</div>
                  {techResult.risk_warnings.map((w, wi) => (
                    <div key={wi} className="text-xs text-amber-600 mt-0.5">{w}</div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
