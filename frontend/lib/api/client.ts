/** API client for World Game backend.
 *
 * In development: connects to localhost:8000
 * In production (Vercel): uses NEXT_PUBLIC_API_URL env var or /api proxy
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL
  || (process.env.NODE_ENV === "production" ? "/api" : "http://localhost:8000/api");

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `API error ${res.status}`);
  }

  return res.json();
}

// Game API
export const gameApi = {
  getCompanies: () =>
    request<import("@/lib/types/game").CompanyOption[]>("/game/companies"),

  create: (config?: Record<string, unknown>) =>
    request<import("@/lib/types/game").GameSession>("/game", {
      method: "POST",
      body: JSON.stringify(config ? { config } : {}),
    }),

  get: (gameId: string) =>
    request<import("@/lib/types/game").GameSession>(`/game/${gameId}`),

  getWorldState: (gameId: string) =>
    request<import("@/lib/types/world").WorldState>(
      `/game/${gameId}/world-state`
    ),

  getMarketActivity: (gameId: string) =>
    request<import("@/lib/types/game").MarketActivitySnapshot>(
      `/game/${gameId}/market-activity`
    ),

  nextTurn: (gameId: string, decisions?: import("@/lib/types/simulation").PlayerDecision[]) =>
    request<import("@/lib/types/game").TurnSummary>(
      `/game/${gameId}/next-turn`,
      {
        method: "POST",
        body: JSON.stringify(decisions),
      }
    ),
};

// OKR API
export const okrApi = {
  list: (gameId: string) =>
    request<import("@/lib/types/okr").Objective[]>(`/game/${gameId}/okr`),

  create: (gameId: string, data: import("@/lib/types/okr").ObjectiveCreate) =>
    request<import("@/lib/types/okr").Objective>(`/game/${gameId}/okr`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getSummary: (gameId: string) =>
    request<import("@/lib/types/okr").OKRSummary>(
      `/game/${gameId}/okr/summary`
    ),

  updateProgress: (gameId: string, data: import("@/lib/types/okr").OKRUpdate) =>
    request<import("@/lib/types/okr").KeyResult>(
      `/game/${gameId}/okr/progress`,
      {
        method: "PUT",
        body: JSON.stringify(data),
      }
    ),
};

// Intel API
export const intelApi = {
  listEvents: (gameId: string, turn?: number) =>
    request<import("@/lib/types/intel").GameEvent[]>(
      `/game/${gameId}/intel/events${turn !== undefined ? `?turn=${turn}` : ""}`
    ),

  getEvent: (gameId: string, eventId: string) =>
    request<import("@/lib/types/intel").GameEvent>(
      `/game/${gameId}/intel/events/${eventId}`
    ),

  listNews: (gameId: string, turn?: number) =>
    request<import("@/lib/types/intel").NewsItem[]>(
      `/game/${gameId}/intel/news${turn !== undefined ? `?turn=${turn}` : ""}`
    ),
};

// Board API
export const boardApi = {
  getAgents: (gameId: string) =>
    request<import("@/lib/types/board").AgentProfile[]>(
      `/game/${gameId}/board/agents`
    ),

  runDebate: (gameId: string, data: import("@/lib/types/board").DebateRequest) =>
    request<import("@/lib/types/board").DebateResponse>(
      `/game/${gameId}/board/debate`,
      {
        method: "POST",
        body: JSON.stringify(data),
      }
    ),
};

// Simulation API
export const simulationApi = {
  simulate: (gameId: string, decisions: import("@/lib/types/simulation").PlayerDecision[]) =>
    request<import("@/lib/types/simulation").SimulateResponse>(
      `/game/${gameId}/simulate`,
      {
        method: "POST",
        body: JSON.stringify({ decisions }),
      }
    ),
};

// World API
export const worldApi = {
  getEntities: (entityType?: string) =>
    request<import("@/lib/types/world").Entity[]>(
      `/world/entities${entityType ? `?entity_type=${entityType}` : ""}`
    ),

  getKnowledgeGraph: (rootIds?: string[], depth = 2) =>
    request<import("@/lib/types/world").KnowledgeGraphData>(
      `/world/knowledge-graph${rootIds ? `?root_ids=${rootIds.join(",")}&depth=${depth}` : ""}`
    ),
};

// Tech Roadmap API
export const techApi = {
  getCatalog: () =>
    request<import("@/lib/types/simulation").TechCatalog>("/tech/catalog"),

  predict: (data: import("@/lib/types/simulation").TechPredictRequest) =>
    request<import("@/lib/types/simulation").TechPredictResponse>("/tech/predict", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getTrends: (period?: string) =>
    request<import("@/lib/types/simulation").TechTrends>(
      `/tech/trends${period ? `?period=${period}` : ""}`
    ),
};

// RSS Feed API
export const rssApi = {
  getFeeds: () =>
    request<{ feeds: { name: string; category: string; xml_url: string; html_url: string }[]; categories: string[] }>("/rss/feeds"),

  getItems: (refresh = false, category = "") =>
    request<{ items: { id: string; title: string; description: string; link: string; source_name: string; source_category: string; published: string }[] }>(
      `/rss/items?refresh=${refresh}&category=${encodeURIComponent(category)}`
    ),

  refresh: () =>
    request<{ count: number; items: { id: string; title: string; source_name: string; source_category: string }[] }>("/rss/refresh"),
};

// Phones API
export const phonesApi = {
  /** Get all brands with model summaries */
  listAll: () =>
    request<Record<string, {
      name: string;
      model_count: number;
      models: { id: string; model: string; release_year: number; tier: string; price_range: string }[];
    }>>("/phones"),

  /** Get detailed models for a specific brand */
  getBrand: (brandId: string) =>
    request<{
      name: string;
      models: {
        id: string; model: string; release_year: number; tier: string;
        price_range: string;
        key_specs: Record<string, string>;
        selling_points: string[];
        strengths: string[];
        weaknesses: string[];
      }[];
    }>(`/phones/${brandId}`),
};

// RSS Intelligence API
export const rssIntelApi = {
  getEvents: (refresh = false) =>
    request<{
      count: number;
      events: {
        title: string;
        description: string;
        category: string;
        severity: string;
        source_rss: string;
        source_link: string;
        component_id: string | null;
        tech_tags: string[];
        sentiment: string;
        impacts: { metric: string; direction: string; magnitude_hint: string }[];
        response_options: string[];
        rss_driven: boolean;
      }[];
    }>(`/rss/intel/events?refresh=${refresh}`),

  getDebates: (refresh = false) =>
    request<{
      count: number;
      topics: {
        topic: string;
        context: string;
        source_link: string;
        category: string;
        component_id: string | null;
        tech_tags: string[];
        sentiment: string;
        suggested_positions: string[];
      }[];
    }>(`/rss/intel/debates?refresh=${refresh}`),

  getTrends: (period = "short_term", refresh = false) =>
    request<{
      period: string;
      original_trends: Record<string, number>;
      merged_trends: Record<string, number>;
      adjustments: {
        tag: string;
        current_weight: number;
        adjusted_weight: number;
        reason: string;
        signal_count: number;
      }[];
    }>(`/rss/intel/trends?period=${period}&refresh=${refresh}`),

  getSummary: (period = "short_term", refresh = false) =>
    request<{
      total_signals: number;
      positive_count: number;
      negative_count: number;
      neutral_count: number;
      top_tags: { tag: string; count: number }[];
      category_breakdown: Record<string, number>;
      key_events: string[];
      trend_adjustments: {
        tag: string;
        current_weight: number;
        adjusted_weight: number;
        reason: string;
        signal_count: number;
      }[];
      generated_at: string;
    }>(`/rss/intel/summary?period=${period}&refresh=${refresh}`),
};

// Social Media API
export const socialApi = {
  getXhsPosts: (brand: string, forceRefresh = false) =>
    request<{
      brand_id: string;
      search_keyword: string;
      posts: {
        id: string;
        title: string;
        text: string;
        cover: string;
        cover_proxy: string;
        likes: number;
        url: string;
        type?: string;
      }[];
      total_found: number;
      cached_at: number;
      from_cache: boolean;
      error: string | null;
    }>(`/social/xhs-posts?brand=${brand}&force_refresh=${forceRefresh}`),
};
