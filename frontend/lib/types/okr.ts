/** OKR types. */

export type KRStatus = "not_started" | "in_progress" | "achieved" | "missed";

export interface KeyResult {
  id: string;
  title: string;
  metric: string;
  target_value: number;
  current_value: number;
  unit: string;
  status: KRStatus;
  progress: number;
}

export interface Objective {
  id: string;
  game_id: string;
  turn_created: number;
  title: string;
  description: string;
  key_results: KeyResult[];
  priority: number;
  is_active: boolean;
}

export interface ObjectiveCreate {
  title: string;
  description?: string;
  key_results?: Omit<KeyResult, "id" | "status" | "progress">[];
  priority?: number;
}

export interface OKRSummary {
  total: number;
  completed: number;
  on_track: number;
  at_risk: number;
}

export interface OKRUpdate {
  key_result_id: string;
  new_value: number;
}
