/** AI Board types (agents and debate). */

export type AgentRole = "ceo" | "coo" | "cpo" | "cio" | "cfo" | "supply_chain";
export type RiskAppetite = "conservative" | "moderate" | "aggressive";

export interface AgentProfile {
  role: AgentRole;
  name: string;
  goal: string;
  risk_appetite: RiskAppetite;
  personality: string;
  expertise: string[];
  relationships: Record<string, string>;
}

export interface PositionStatement {
  role: AgentRole;
  position: string;
  reasoning: string;
  concerns: string[];
  conditions: string[];
  confidence: number;
}

export interface DebateRound {
  round_number: number;
  topic: string;
  statements: PositionStatement[];
  counter_arguments: Record<string, unknown>[];
  consensus_reached: boolean;
  summary: string;
}

export interface Vote {
  role: AgentRole;
  choice: string;
  reasoning: string;
}

export interface BoardDecision {
  topic: string;
  options: string[];
  votes: Vote[];
  final_choice: string;
  ceo_rationale: string;
  dissenting_opinions: string[];
}

export interface DebateRequest {
  topic: string;
  context?: string;
  options?: string[];
}

export interface DebateResponse {
  debate_id: string;
  rounds: DebateRound[];
  decision: BoardDecision | null;
  status: "preparing" | "debating" | "voting" | "concluded";
}
