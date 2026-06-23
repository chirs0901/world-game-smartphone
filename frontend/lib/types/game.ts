/** Core game types matching backend schemas. */

export interface CompanyOption {
  id: string;
  name: string;
  tagline: string;
  logo_emoji: string;
  country: string;
  description: string;
  strengths: string[];
  weaknesses: string[];
  strategy_hint: string;
  difficulty: string;
  base_metrics: Record<string, number>;
}

export interface GameConfig {
  company_id: string;
  difficulty: "easy" | "normal" | "hard";
  initial_cash: number;
  max_turns: number;
}

export interface GameSession {
  id: string;
  status: string;
  config: GameConfig;
  current_turn: number;
  current_year: number;
  current_quarter: number;
  created_at: string;
}

export interface TurnSummary {
  turn: number;
  year: number;
  quarter: number;
  events_this_turn: string[];
  decisions_made: string[];
  metrics_delta: Record<string, number>;
  narrative: string;
}

export type TurnPhase = "observe" | "decide" | "execute" | "feedback";

export interface TurnPhaseState {
  turn: number;
  phase: TurnPhase;
  year: number;
  quarter: number;
}

export interface MarketActivity {
  timestamp: number;
  brand: string;
  action: "buy" | "browse" | "switch";
  product_segment: string;
  price: number;
  quantity: number;
  reason: string;
}

export interface MarketActivitySnapshot {
  company_name: string;
  activities: MarketActivity[];
  total_sales_this_quarter: number;
  total_revenue_this_quarter: number;
  market_trend: "rising" | "stable" | "declining";
  top_sellers: { brand: string; units: number; trend: string }[];
}
