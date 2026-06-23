"use client";

import { useGameStore } from "@/lib/store/gameStore";
import { useQuery } from "@tanstack/react-query";
import { okrApi } from "@/lib/api/client";
import { useState } from "react";
import type { ObjectiveCreate, Objective } from "@/lib/types/okr";

export default function OKRPage() {
  const { session } = useGameStore();
  const [showCreate, setShowCreate] = useState(false);
  const [title, setTitle] = useState("");
  const [desc, setDesc] = useState("");
  const [editingObj, setEditingObj] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editDesc, setEditDesc] = useState("");

  const { data: objectives, refetch } = useQuery({
    queryKey: ["okr", session?.id],
    queryFn: () => okrApi.list(session!.id),
    enabled: !!session,
  });

  const { data: summary } = useQuery({
    queryKey: ["okr-summary", session?.id],
    queryFn: () => okrApi.getSummary(session!.id),
    enabled: !!session,
  });

  const handleCreate = async () => {
    if (!session || !title.trim()) return;
    await okrApi.create(session.id, {
      title,
      description: desc,
      priority: 1,
    });
    setTitle("");
    setDesc("");
    setShowCreate(false);
    refetch();
  };

  const handleStartEdit = (obj: Objective) => {
    setEditingObj(obj.id);
    setEditTitle(obj.title);
    setEditDesc(obj.description || "");
  };

  const handleSaveEdit = async (objId: string) => {
    // For now, just dismiss editing (full update endpoint not yet available)
    // In production, would call PUT /okr to update title/description
    setEditingObj(null);
    refetch();
  };

  const handleKrProgress = async (gameId: string, krId: string, newValue: number) => {
    try {
      await okrApi.updateProgress(gameId, {
        key_result_id: krId,
        new_value: newValue,
      });
      refetch();
    } catch (e) {
      console.error("Failed to update KR progress:", e);
    }
  };

  const statusColor = (status: string) => {
    switch (status) {
      case "achieved":
        return "bg-green-100 text-green-700";
      case "in_progress":
        return "bg-blue-100 text-blue-700";
      case "missed":
        return "bg-red-100 text-red-700";
      default:
        return "bg-slate-100 text-slate-600";
    }
  };

  const statusLabel = (status: string) => {
    switch (status) {
      case "achieved":
        return "已达成";
      case "in_progress":
        return "进行中";
      case "missed":
        return "已错过";
      default:
        return "未开始";
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900">OKR 工作台</h1>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="px-4 py-2 text-white rounded-lg hover:opacity-90 text-sm"
          style={{ backgroundColor: "var(--brand-primary)" }}
        >
          + 新建目标
        </button>
      </div>

      {/* Summary */}
      {summary && (
        <div className="grid grid-cols-4 gap-4">
          {[
            { label: "总目标", value: summary.total, color: "text-slate-900" },
            { label: "已完成", value: summary.completed, color: "text-green-600" },
            { label: "进行中", value: summary.on_track, color: "text-blue-600" },
            { label: "有风险", value: summary.at_risk, color: "text-red-600" },
          ].map((item) => (
            <div
              key={item.label}
              className="bg-white rounded-xl p-4 shadow-sm border border-slate-200 text-center"
            >
              <div className={`text-2xl font-bold ${item.color}`}>
                {item.value}
              </div>
              <div className="text-xs text-slate-700 font-medium">{item.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Create form */}
      {showCreate && (
        <div className="bg-white rounded-xl p-4 shadow-sm border border-slate-200 space-y-3">
          <input
            type="text"
            placeholder="目标标题"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-900 placeholder:text-slate-900"
          />
          <textarea
            placeholder="目标描述（可选）"
            value={desc}
            onChange={(e) => setDesc(e.target.value)}
            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-900 placeholder:text-slate-900"
            rows={2}
          />
          <div className="flex gap-2">
            <button
              onClick={handleCreate}
              className="px-4 py-2 text-white rounded-lg text-sm"
              style={{ backgroundColor: "var(--brand-primary)" }}
            >
              创建
            </button>
            <button
              onClick={() => setShowCreate(false)}
              className="px-4 py-2 bg-slate-100 text-slate-600 rounded-lg text-sm"
            >
              取消
            </button>
          </div>
        </div>
      )}

      {/* Objectives list */}
      <div className="space-y-4">
        {objectives && objectives.length > 0 ? (
          objectives.map((obj) => (
            <div
              key={obj.id}
              className="bg-white rounded-xl p-4 shadow-sm border border-slate-200"
            >
              <div className="flex items-center justify-between">
                {editingObj === obj.id ? (
                  <input
                    type="text"
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    className="font-semibold text-slate-900 border border-slate-300 rounded px-2 py-1 flex-1 mr-2"
                  />
                ) : (
                  <h3 className="font-semibold text-slate-900">{obj.title}</h3>
                )}
                <div className="flex items-center gap-2">
                  <span className="text-xs px-2 py-0.5 rounded bg-slate-100 text-slate-500">
                    P{obj.priority}
                  </span>
                  {editingObj === obj.id ? (
                    <>
                      <button
                        onClick={() => handleSaveEdit(obj.id)}
                        className="text-xs px-2 py-1 text-white rounded hover:opacity-90" style={{ backgroundColor: "var(--brand-primary)" }}
                      >
                        保存
                      </button>
                      <button
                        onClick={() => setEditingObj(null)}
                        className="text-xs px-2 py-1 bg-slate-100 text-slate-600 rounded hover:bg-slate-200"
                      >
                        取消
                      </button>
                    </>
                  ) : (
                    <button
                      onClick={() => handleStartEdit(obj)}
                      className="text-xs px-2 py-1 text-slate-500 hover:text-[var(--brand-primary)] hover:bg-[var(--brand-light)] rounded transition-colors"
                    >
                      ✏️
                    </button>
                  )}
                </div>
              </div>
              {editingObj === obj.id ? (
                <textarea
                  value={editDesc}
                  onChange={(e) => setEditDesc(e.target.value)}
                  className="w-full mt-2 px-2 py-1 border border-slate-300 rounded text-sm text-slate-900 placeholder:text-slate-900"
                  rows={2}
                  placeholder="目标描述"
                />
              ) : obj.description ? (
                <p className="text-sm text-slate-600 mt-1">{obj.description}</p>
              ) : null}

              {/* Key Results */}
              <div className="mt-3 space-y-3">
                {obj.key_results.map((kr) => (
                  <div key={kr.id} className="flex items-center gap-3">
                    <div className="flex-1">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-slate-700 font-medium">{kr.title}</span>
                        <span
                          className={`text-xs px-2 py-0.5 rounded ${statusColor(kr.status)}`}
                        >
                          {statusLabel(kr.status)}
                          {kr.progress < 0.3 && kr.status === "in_progress" && " ⚠️"}
                          {kr.progress >= 0.8 && kr.status === "in_progress" && " 🎯"}
                        </span>
                      </div>
                      {/* Draggable progress slider */}
                      <div className="mt-1 flex items-center gap-2">
                        <input
                          type="range"
                          min={0}
                          max={kr.target_value}
                          step={Math.max(0.1, kr.target_value / 100)}
                          value={kr.current_value}
                          onChange={(e) => {
                            if (!session) return;
                            handleKrProgress(session.id, kr.id, parseFloat(e.target.value));
                          }}
                          className="flex-1 h-2 appearance-none bg-slate-200 rounded-full cursor-pointer
                            [&::-webkit-slider-thumb]:appearance-none
                            [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4
                            [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:cursor-pointer
                            [&::-webkit-slider-thumb]:shadow-sm"
                          style={{ accentColor: "var(--brand-primary)" }}
                        />
                      </div>
                      <div className="text-xs text-slate-700 mt-0.5 flex justify-between">
                        <span>
                          {kr.current_value} / {kr.target_value} {kr.unit}
                        </span>
                        <span className="font-medium text-slate-600">
                          {(kr.progress * 100).toFixed(0)}%
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))
        ) : (
          <div className="text-center py-12 text-slate-600">
            暂无目标，点击"新建目标"开始制定你的 OKR
          </div>
        )}
      </div>
    </div>
  );
}
