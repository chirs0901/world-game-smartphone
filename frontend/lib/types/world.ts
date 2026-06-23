/** World state and knowledge graph types. */

export interface BrandMetrics {
  sales_volume: number;
  revenue: number;
  profit: number;
  inventory: number;
  cash_reserve: number;
  brand_heat: number;
  tech_leadership: number;
  market_share: number;
  supply_stability: number;
  customer_satisfaction: number;
  morale: number;
}

export interface MarketMetrics {
  total_market_size: number;
  growth_rate: number;
  avg_selling_price: number;
  top_brands: { name: string; share: number }[];
}

export interface WorldState {
  turn: number;
  year: number;
  quarter: number;
  brand_metrics: BrandMetrics;
  market_metrics: MarketMetrics;
  active_events: string[];
}

export type EntityType = "brand" | "supplier" | "product" | "technology" | "person";

export interface EntityRelation {
  target_id: string;
  relation_type: string;
  weight: number;
  attributes: Record<string, unknown>;
}

export interface Entity {
  id: string;
  type: EntityType;
  name: string;
  attributes: Record<string, unknown>;
  relations: EntityRelation[];
}

export interface KnowledgeGraphData {
  nodes: Record<string, unknown>[];
  edges: Record<string, unknown>[];
}
