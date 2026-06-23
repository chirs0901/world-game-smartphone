"use client";

import { useEffect, useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import { gameApi } from "@/lib/api/client";
import type { MarketActivity } from "@/lib/types/game";

// Store visual constants
const STORE_WIDTH = 100; // percentage
const CUSTOMER_AVATARS = ["🧑", "👩", "👨", "🧓", "👱", "👩‍💼", "👨‍💻", "🧑‍🎓", "👩‍🔬", "🧑‍💼"];
const PHONE_EMOJIS: Record<string, string> = {
  "旗舰": "📱✨",
  "中端": "📱",
  "入门": "📲",
};

const ACTION_LABELS: Record<string, string> = {
  buy: "🛒 购买",
  browse: "👀 浏览",
  switch: "↔️ 换到",
};

const SEGMENT_COLORS: Record<string, string> = {
  "旗舰": "text-purple-400",
  "中端": "text-blue-400",
  "入门": "text-green-400",
};

interface PhoneStoreProps {
  gameId: string;
  companyName: string;
}

interface FloatingCustomer {
  id: string;
  avatar: string;
  activity: MarketActivity;
  x: number;
  y: number;
  enteredAt: number;
}

export default function PhoneStore({ gameId, companyName }: PhoneStoreProps) {
  const [customers, setCustomers] = useState<FloatingCustomer[]>([]);
  const [salesCounter, setSalesCounter] = useState(0);
  const [revenueCounter, setRevenueCounter] = useState(0);
  const nextId = useRef(0);

  // Fetch market activity periodically
  const { data: activity, isLoading } = useQuery({
    queryKey: ["market-activity", gameId],
    queryFn: () => gameApi.getMarketActivity(gameId),
    refetchInterval: 5000, // Every 5 seconds
    enabled: !!gameId,
    retry: 2,
    retryDelay: 1000,
  });

  // Process new activities into animated customers
  useEffect(() => {
    if (!activity?.activities.length) return;

    // Add new customers from the latest activity batch
    const newCustomers: FloatingCustomer[] = activity.activities
      .filter((a) => a.action === "buy" || a.action === "browse")
      .slice(0, 4)
      .map((act) => ({
        id: `cust-${nextId.current++}`,
        avatar: CUSTOMER_AVATARS[Math.floor(Math.random() * CUSTOMER_AVATARS.length)],
        activity: act,
        x: 10 + Math.random() * 80,
        y: 20 + Math.random() * 60,
        enteredAt: Date.now(),
      }));

    setCustomers((prev) => {
      const combined = [...newCustomers, ...prev];
      // Keep max 8 customers on screen
      return combined.slice(0, 8);
    });

    // Update counters
    const newSales = activity.activities
      .filter((a) => a.action === "buy" && a.brand === companyName)
      .reduce((sum, a) => sum + a.quantity, 0);

    const newRevenue = activity.activities
      .filter((a) => a.action === "buy" && a.brand === companyName)
      .reduce((sum, a) => sum + a.price * a.quantity / 10000, 0);

    setSalesCounter((prev) => prev + newSales);
    setRevenueCounter((prev) => prev + newRevenue);

    // Auto-remove old customers after 8 seconds
    const timer = setTimeout(() => {
      setCustomers((prev) =>
        prev.filter((c) => Date.now() - c.enteredAt < 8000)
      );
    }, 4000);

    return () => clearTimeout(timer);
  }, [activity]);

  const trendEmoji =
    activity?.market_trend === "rising"
      ? "📈"
      : activity?.market_trend === "declining"
        ? "📉"
        : "📊";
  const trendLabel =
    activity?.market_trend === "rising"
      ? "市场上升"
      : activity?.market_trend === "declining"
        ? "市场下滑"
        : "市场平稳";

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-gradient-to-r from-indigo-50 to-blue-50 border-b border-slate-200">
        <div className="flex items-center gap-2">
          <span className="text-lg">🏪</span>
          <h2 className="text-sm font-semibold text-slate-800">
            手机专卖店 · 实时市场
          </h2>
          <span className="text-xs text-slate-700">{trendEmoji} {trendLabel}</span>
        </div>
        <div className="flex gap-3 text-xs">
          <span className="text-slate-600">
            本季销量:{" "}
            <span className="font-bold text-blue-600">
              {activity?.total_sales_this_quarter?.toFixed(0) ?? "—"}
            </span>{" "}
            万台
          </span>
          <span className="text-slate-600">
            营收:{" "}
            <span className="font-bold text-green-600">
              {activity?.total_revenue_this_quarter?.toFixed(1) ?? "—"}
            </span>{" "}
            亿
          </span>
        </div>
      </div>

      {/* Store Scene */}
      <div className="relative h-48 overflow-hidden" style={{
        backgroundImage: 'url(/images/store-background.png)',
        backgroundSize: 'cover',
        backgroundPosition: 'center',
        backgroundRepeat: 'no-repeat'
      }}>
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/50">
            <span className="text-sm text-slate-500">加载中...</span>
          </div>
        )}
        {/* Shelves */}
        <div className="absolute top-2 left-0 right-0 flex justify-around px-4">
          {["旗舰", "中端", "入门"].map((seg) => (
            <div
              key={seg}
              className="text-center bg-white/80 rounded-lg px-3 py-1 shadow-sm border border-slate-100"
            >
              <div className="text-xs text-slate-400">{seg}专区</div>
              <div className="text-lg">{PHONE_EMOJIS[seg]}</div>
            </div>
          ))}
        </div>

        {/* Store counter */}
        <div className="absolute bottom-0 left-0 right-0 h-8 bg-gradient-to-t from-amber-100/50 to-transparent" />

        {/* Salesperson - left side */}
        <div className="absolute bottom-2 left-8 flex items-end gap-2">
          <div className="flex flex-col items-center">
            <div className="w-6 h-6 bg-amber-200 rounded-full border border-amber-300" />
            <div className="w-8 h-9 -mt-0.5 bg-indigo-500 rounded-b-lg relative">
              <div className="absolute -left-2 top-1.5 w-2 h-3 bg-indigo-500 rounded opacity-80" />
              <div className="absolute -right-2 top-1.5 w-2 h-3 bg-indigo-500 rounded opacity-80" />
            </div>
            <div className="flex gap-0.5 -mt-0.5">
              <div className="w-2.5 h-3.5 bg-slate-600 rounded-b" />
              <div className="w-2.5 h-3.5 bg-slate-600 rounded-b" />
            </div>
          </div>
        </div>

        {/* Salesperson - right side with speech bubble */}
        <div className="absolute bottom-2 right-8 flex items-end gap-2">
          <motion.div
            animate={{ y: [0, -3, 0] }}
            transition={{ duration: 2, repeat: Infinity }}
            className="flex flex-col items-center"
          >
            <div className="w-6 h-6 bg-amber-100 rounded-full border border-amber-300" />
            <div className="w-8 h-9 -mt-0.5 bg-emerald-500 rounded-b-lg relative">
              <div className="absolute -left-2 top-1.5 w-2 h-3 bg-emerald-500 rounded opacity-80" />
              <div className="absolute -right-2 top-1.5 w-2 h-3 bg-emerald-500 rounded opacity-80" />
            </div>
            <div className="flex gap-0.5 -mt-0.5">
              <div className="w-2.5 h-3.5 bg-slate-600 rounded-b" />
              <div className="w-2.5 h-3.5 bg-slate-600 rounded-b" />
            </div>
          </motion.div>
          {/* Speech bubble */}
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: [1, 1, 0.7, 1] }}
            transition={{ duration: 4, repeat: Infinity }}
            className="absolute -top-12 right-0 bg-white text-[10px] px-2 py-1 rounded-lg shadow border border-slate-200 whitespace-nowrap"
          >
            <div className="absolute -bottom-1 right-6 w-2 h-2 bg-white border-r border-b border-slate-200 rotate-45" />
            💬 欢迎光临！请问想看什么机型？
          </motion.div>
        </div>

        {/* Animated customers */}
        <AnimatePresence>
          {customers.map((cust) => (
            <CustomerSprite key={cust.id} customer={cust} />
          ))}
        </AnimatePresence>

        {/* Empty state */}
        {customers.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center">
            <p className="text-slate-300 text-sm">等待顾客进店...</p>
          </div>
        )}
      </div>

      {/* Activity Feed */}
      <div className="border-t border-slate-100 px-4 py-2 max-h-32 overflow-hidden">
        <div className="space-y-1">
          {activity?.activities.slice(0, 5).map((act, i) => (
            <motion.div
              key={`${act.timestamp}-${i}`}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              className="flex items-center gap-2 text-xs"
            >
              <span className="text-slate-400">
                {new Date(act.timestamp * 1000).toLocaleTimeString("zh-CN", {
                  hour: "2-digit",
                  minute: "2-digit",
                  second: "2-digit",
                })}
              </span>
              <span className={act.brand === companyName ? "font-bold text-blue-600" : "text-slate-700"}>
                {CUSTOMER_AVATARS[i % CUSTOMER_AVATARS.length]}{" "}
                <span className="text-slate-700">{act.brand}</span>
              </span>
              <span className={SEGMENT_COLORS[act.product_segment] ?? "text-slate-500"}>
                {act.product_segment}
              </span>
              <span className="text-slate-700">
                {ACTION_LABELS[act.action]} {act.action === "buy" ? `¥${act.price}` : ""}
              </span>
              <span className="text-slate-400 truncate flex-1">
                {act.reason}
              </span>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Top sellers bar */}
      {activity?.top_sellers && activity.top_sellers.length > 0 && (
        <div className="border-t border-slate-100 px-4 py-2 bg-slate-50">
          <div className="flex items-center gap-3 text-xs">
            <span className="text-slate-700 font-medium">品牌排行:</span>
            {activity.top_sellers.map((seller) => (
              <span
                key={seller.brand}
                className={`flex items-center gap-1 ${
                  seller.brand === companyName
                    ? "text-blue-600 font-bold"
                    : "text-slate-700"
                }`}
              >
                {seller.brand}
                <span className="text-slate-600">{seller.units}%</span>
                <span>
                  {seller.trend === "up"
                    ? "🔺"
                    : seller.trend === "down"
                      ? "🔻"
                      : "➖"}
                </span>
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function CustomerSprite({ customer }: { customer: FloatingCustomer }) {
  const { activity, x, y } = customer;
  const isBuy = activity.action === "buy";

  const bodyColor = isBuy ? "bg-blue-500" : "bg-slate-400";

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.5, x: -50 }}
      animate={{
        opacity: 1,
        scale: 1,
        x: 0,
        y: [0, -5, 0],
      }}
      exit={{ opacity: 0, scale: 0.5, y: 30 }}
      transition={{
        opacity: { duration: 0.3 },
        scale: { duration: 0.3 },
        x: { duration: 0.8, ease: "easeOut" },
        y: { duration: 1.5, repeat: Infinity, ease: "easeInOut" },
      }}
      className="absolute flex flex-col items-center"
      style={{ left: `${x}%`, top: `${y}%` }}
    >
      {/* CSS Character */}
      <div className="flex flex-col items-center">
        {/* Head */}
        <div className="w-5 h-5 bg-amber-300 rounded-full border border-amber-400" />
        {/* Body */}
        <div className={`w-6 h-7 -mt-0.5 rounded-b-lg ${bodyColor} relative`}>
          {/* Arms */}
          <div className={`absolute -left-1.5 top-1 w-1.5 h-3 rounded ${bodyColor} opacity-80`} />
          <div className={`absolute -right-1.5 top-1 w-1.5 h-3 rounded ${bodyColor} opacity-80`} />
        </div>
        {/* Legs */}
        <div className="flex gap-0.5 -mt-0.5">
          <div className="w-2 h-3 bg-slate-500 rounded-b" />
          <div className="w-2 h-3 bg-slate-500 rounded-b" />
        </div>
      </div>
      {isBuy && (
        <motion.div
          initial={{ opacity: 0, y: 0 }}
          animate={{ opacity: 1, y: -40 }}
          transition={{ delay: 0.5, duration: 0.5 }}
          className="absolute -top-8 text-[10px] bg-green-500 text-white px-1.5 py-0.5 rounded-full whitespace-nowrap shadow-sm"
        >
          +{activity.quantity}台 💰
        </motion.div>
      )}
      {activity.action === "browse" && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: [1, 1, 0] }}
          transition={{ duration: 3, repeat: Infinity }}
          className="absolute -top-7 text-[10px] bg-white px-1.5 py-0.5 rounded-full shadow border border-slate-200 whitespace-nowrap"
        >
          👀 看看
        </motion.div>
      )}
      <span
        className={`text-[10px] mt-0.5 ${
          isBuy ? "text-blue-600 font-bold" : "text-slate-500"
        }`}
      >
        {activity.brand}
      </span>
    </motion.div>
  );
}
