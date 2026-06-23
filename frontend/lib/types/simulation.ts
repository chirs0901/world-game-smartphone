/** Simulation types. */

export type DecisionCategory =
  | "product"
  | "rd"
  | "marketing"
  | "supply"
  | "finance"
  | "hr";

export interface PlayerDecision {
  category: DecisionCategory;
  action: string;
  budget?: number;
  priority: number;
}

export interface SimImpact {
  metric: string;
  delta: number;
  delta_percent: number;
  confidence: number;
  reasoning: string;
}

export interface QualitativeFeedback {
  source: string;
  reaction: string;
  sentiment: "positive" | "negative" | "mixed";
}

export interface ChainEffect {
  order: number;
  description: string;
  impacts: SimImpact[];
  probability: number;
}

export interface SimulationResult {
  turn: number;
  decision: PlayerDecision;
  direct_impacts: SimImpact[];
  qualitative_feedbacks: QualitativeFeedback[];
  chain_effects: ChainEffect[];
  narrative: string;
  risk_warnings: string[];
}

export interface SimulateRequest {
  decisions: PlayerDecision[];
}

export interface SimulateResponse {
  results: SimulationResult[];
  total_cost: number;
}

// ── Technology Roadmap Types ──

export type TechTier = "short_term" | "mid_term" | "long_term";

export interface ComponentOption {
  id: string;
  name: string;
  tier: TechTier;
  cost_share_pct: number;
  quality_score: number;
  tech_maturity: number;
  selling_point_tags: string[];
  ffr_base: number;
  supplier_lock_required: boolean;
  description: string;
  space_cost: number;
  research_type: "procurement" | "joint_rd" | "self_developed";
  conflicts_with: string[];
}

export interface ComponentCategory {
  id: string;
  name: string;
  default_option_id: string;
  options: ComponentOption[];
}

export interface TechCatalog {
  categories: ComponentCategory[];
}

export interface TechSelection {
  category_id: string;
  option_id: string;
}

export interface TechPredictRequest {
  selections: TechSelection[];
  target_tier: TechTier;
}

export interface SellingPoint {
  tag: string;
  weight: number;
}

export interface MaturityPenaltyDetail {
  option_name: string;
  option_tier: string;
  target_tier: string;
  tier_diff: number;
  cost_impact: string;
  ffr_impact: string;
  quality_impact: string;
}

export interface SpaceConflictDetail {
  option_a: string;
  option_b: string;
  description: string;
}

export interface ResearchRiskDetail {
  option_name: string;
  research_type: string;
  description: string;
  impact: string;
}

export interface TechPredictResponse {
  selections: TechSelection[];
  total_bom_cost_pct: number;
  bom_cost_vs_baseline_pct: number;
  ffr_rate: number;
  quality_score: number;
  selling_points: SellingPoint[];
  reputation_prediction: string;
  reputation_score: number;
  risk_warnings: string[];
  competitive_advantage: string;
  total_space_cost: number;
  space_budget: number;
  space_over_budget: boolean;
  maturity_penalties: MaturityPenaltyDetail[];
  space_conflicts: SpaceConflictDetail[];
  research_risks: ResearchRiskDetail[];
}

export interface TechTrends {
  period: string;
  trends: Record<string, number>;
}
