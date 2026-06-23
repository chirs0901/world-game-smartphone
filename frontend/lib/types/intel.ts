/** Intel types (news and events). */

export type NewsCategory =
  | "market"
  | "technology"
  | "supply_chain"
  | "policy"
  | "competitor"
  | "consumer";

export type EventSeverity = "low" | "medium" | "high" | "critical";
export type Sentiment = "positive" | "neutral" | "negative";

export interface EventImpact {
  metric: string;
  direction: "up" | "down";
  magnitude: "small" | "medium" | "large";
  estimated_value?: number;
  confidence: number;
}

export interface GameEvent {
  id: string;
  turn: number;
  category: NewsCategory;
  severity: EventSeverity;
  title: string;
  description: string;
  impacts: EventImpact[];
  response_options: string[];
  chain_effects: string[];
  duration_turns: number;
}

export interface NewsItem {
  id: string;
  turn: number;
  category: NewsCategory;
  headline: string;
  content: string;
  source: string;
  sentiment: Sentiment;
  affected_entities: string[];
  is_critical: boolean;
  tags: string[];
}
