"use client";

import { useGameStore } from "@/lib/store/gameStore";
import { useQuery } from "@tanstack/react-query";
import { boardApi } from "@/lib/api/client";
import { useState } from "react";
import type { DebateResponse } from "@/lib/types/board";

const ROLE_LABELS: Record<string, string> = {
  ceo: "CEO Alexander Chen",
  coo: "COO Victoria Hayes",
  cpo: "CPO Marcus Liu",
  cio: "CIO Robert Kim",
  cfo: "CFO Sarah Johnson",
  supply_chain: "供应链 Michael Wang",
};

const POSITION_COLORS: Record<string, string> = {
  "支持": "bg-green-100 text-green-700 border-green-300",
  "反对": "bg-red-100 text-red-700 border-red-300",
  "有条件支持": "bg-yellow-100 text-yellow-700 border-yellow-300",
};

export default function BoardPage() {
  const { session } = useGameStore();
  const [topic, setTopic] = useState("");
  const [debating, setDebating] = useState(false);
  const [result, setResult] = useState<DebateResponse | null>(null);

  const { data: agents } = useQuery({
    queryKey: ["agents", session?.id],
    queryFn: () => boardApi.getAgents(session!.id),
    enabled: !!session,
  });

  const handleDebate = async () => {
    if (!session || !topic.trim()) return;
    setDebating(true);
    try {
      const res = await boardApi.runDebate(session.id, {
        topic,
        context: `当前${session.current_year}年Q${session.current_quarter}`,
      });
      setResult(res);
    } catch (e) {
      console.error("Debate failed:", e);
    } finally {
      setDebating(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-slate-900">AI 决策委员会</h1>

      {/* Agent profiles */}
      <div className="grid grid-cols-6 gap-3">
        {agents?.map((agent) => (
          <div
            key={agent.role}
            className="bg-white rounded-xl p-3 shadow-sm border border-slate-200 text-center"
          >
            <div className="text-2xl mb-1">
              {agent.role === "cio" && "🔧"}
              {agent.role === "cpo" && "📱"}
              {agent.role === "coo" && "⚙️"}
              {agent.role === "supply_chain" && "🏭"}
              {agent.role === "cfo" && "💰"}
              {agent.role === "ceo" && "👔"}
            </div>
            <div className="text-sm font-semibold text-slate-900">{ROLE_LABELS[agent.role]}</div>
            <div className="text-xs text-slate-600 mt-1 line-clamp-2">
              {agent.goal}
            </div>
          </div>
        ))}
      </div>

      {/* Debate input */}
      <div className="bg-white rounded-xl p-4 shadow-sm border border-slate-200 space-y-3">
        <h2 className="font-semibold text-slate-900">发起议题</h2>
        <input
          type="text"
          placeholder="输入讨论主题，例如：是否投入折叠屏研发？"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          className="w-full px-4 py-2 border border-slate-300 rounded-lg text-sm text-slate-900 placeholder:text-slate-900"
        />
        <button
          onClick={handleDebate}
          disabled={debating || !topic.trim()}
          className="px-6 py-2 text-white rounded-lg text-sm hover:opacity-90 disabled:opacity-50"
          style={{ backgroundColor: "var(--brand-primary)" }}
        >
          {debating ? "辩论中..." : "开始辩论"}
        </button>
      </div>

      {/* Debate result */}
      {result && (
        <div className="space-y-4">
          {/* Rounds */}
          {result.rounds.map((round, ri) => (
            <div
              key={ri}
              className="bg-white rounded-xl p-4 shadow-sm border border-slate-200"
            >
              <h3 className="font-semibold text-slate-900 mb-3">
                第 {round.round_number} 轮{round.consensus_reached ? " ✅ 达成共识" : ""}
              </h3>
              <div className="space-y-3">
                {round.statements.map((stmt, si) => (
                  <div key={si} className="flex gap-3">
                    <div className="w-28 flex-shrink-0 text-sm font-medium text-slate-900">
                      {ROLE_LABELS[stmt.role]}
                    </div>
                    <div className="flex-1">
                      <span
                        className={`text-xs px-2 py-0.5 rounded border ${
                          POSITION_COLORS[stmt.position] || "bg-slate-100 text-slate-600"
                        }`}
                      >
                        {stmt.position}
                      </span>
                      <p className="text-sm text-slate-700 mt-1">{stmt.reasoning}</p>
                      {stmt.concerns.length > 0 && (
                        <div className="mt-1 text-xs text-orange-600">
                          顾虑: {stmt.concerns.join("、")}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
              {round.summary && (
                <div className="mt-3 text-sm text-slate-600 border-t pt-2">
                  {round.summary}
                </div>
              )}
            </div>
          ))}

          {/* Decision */}
          {result.decision && (
            <div className="rounded-xl p-4 border border-blue-200" style={{ backgroundColor: "var(--brand-primary-light)", opacity: 0.15 }}>
              <h3 className="font-semibold text-slate-900">CEO 裁决</h3>
              <p className="text-sm text-slate-900 mt-1">
                最终决策: <strong>{result.decision.final_choice}</strong>
              </p>
              <p className="text-sm mt-1" style={{ color: "var(--brand-primaryDark)" }}>
                {result.decision.ceo_rationale}
              </p>
              {result.decision.dissenting_opinions.length > 0 && (
                <div className="mt-2 text-xs" style={{ color: "var(--brand-primary)" }}>
                  异议: {result.decision.dissenting_opinions.join(" | ")}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
