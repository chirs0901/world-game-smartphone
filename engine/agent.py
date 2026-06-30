"""
Brand Agent Decision Engine — Phase 3.

Each brand agent follows an Observe → Evaluate → Decide → Act loop,
driven by its DNA vector, goal_function, and world observation.

Key design:
  - No LLM dependency — decisions are purely rules-based, deterministic.
  - Each agent has its own decision_period (from company.schema.yaml).
  - Decision traces stored in brand_state["last_decision"] for audit.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.models import WorldStateData, SupplyChainLink, CompanyAgent, TechnologyNode, ConsumerSegment


class BrandAgent:
    """An autonomous brand agent that makes strategic decisions each decision_period."""

    def __init__(self, company_def: "CompanyAgent"):
        self.defn = company_def
        self.id: str = company_def.id
        self.name: str = company_def.name
        self.dna: dict = company_def.dna
        self.goals: list[str] = company_def.goal_function.get("maximize", [])
        self.constraints: list[str] = company_def.goal_function.get("constraints", [])
        self.decision_period: int = company_def.decision_period
        self.last_decision_tick: int = -999

    def should_decide(self, tick: int) -> bool:
        """Return True if the agent should make a decision on this tick."""
        return tick >= 0 and (tick - self.last_decision_tick) >= self.decision_period

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def decide(
        self,
        state: "WorldStateData",
        links: list["SupplyChainLink"],
        tech_nodes: list["TechnologyNode"],
        segments: list["ConsumerSegment"],
    ) -> dict:
        """Run the full Observe → Evaluate → Decide → Act loop. Returns trace."""
        obs = self._observe(state, links, tech_nodes, segments)
        options = self._evaluate(obs)
        choice = self._select(options)
        trace = self._act(choice, state)
        self.last_decision_tick = state.tick
        state.brand_states[self.id]["last_decision"] = trace
        return trace

    # ------------------------------------------------------------------
    # Step 1 — Observe
    # ------------------------------------------------------------------

    def _observe(
        self,
        state: "WorldStateData",
        links: list["SupplyChainLink"],
        tech_nodes: list["TechnologyNode"],
        segments: list["ConsumerSegment"],
    ) -> dict:
        """Gather world state from this agent's perspective."""

        # Own state
        own = state.brand_states.get(self.id, {})

        # Competitors (top 3 by market_share)
        competitors = []
        for bid, bs in state.brand_states.items():
            if bid != self.id and bs.get("market_share", 0) > 0:
                competitors.append({
                    "id": bid,
                    "market_share": bs.get("market_share", 0),
                    "tech_leadership": bs.get("tech_leadership", 0),
                    "profit_margin": bs.get("profit_margin", 0),
                    "brand_heat": bs.get("brand_heat", 0),
                })
        competitors.sort(key=lambda x: x["market_share"], reverse=True)

        # Active technology nodes
        active_techs = [
            t for t in tech_nodes
            if state.technology_status.get(t.id, {}).get("activated", False)
        ]

        # Consumer segment preferences (simplified: just pass the dicts)
        consumer_prefs = {}
        for seg in segments:
            seg_state = state.consumer_segments.get(seg.id, {})
            consumer_prefs[seg.id] = seg_state.get("preferences", {})

        return {
            "own": own,
            "competitors": competitors,
            "top_competitors": competitors[:3],
            "active_techs": active_techs,
            "consumer_prefs": consumer_prefs,
        }

    # ------------------------------------------------------------------
    # Step 2 — Evaluate
    # ------------------------------------------------------------------

    def _evaluate(self, obs: dict) -> dict:
        """Score all options for three decision dimensions."""
        own = obs["own"]
        competitors = obs["top_competitors"]

        return {
            "tech_investment": self._score_tech_categories(own, competitors),
            "pricing": self._score_pricing(own, competitors),
            "supply": self._score_supply(own),
        }

    # --- Tech Investment scoring ---

    TECH_CATEGORIES = ["soc", "display", "camera", "battery", "ai"]

    def _score_tech_categories(self, own: dict, competitors: list[dict]) -> dict[str, float]:
        scores = {}
        for cat in self.TECH_CATEGORIES:
            scores[cat] = self._score_one_tech_category(cat, own, competitors)
        return scores

    def _score_one_tech_category(self, cat: str, own: dict, competitors: list[dict]) -> float:
        dna = self.dna
        score = 50.0  # baseline

        # Category-specific DNA drivers
        if cat == "soc":
            # Soc is fundamental — all brands care, especially innovators
            score += dna.get("innovation_lead", 0.5) * 25
            # Brands behind in tech_leadership need better chips
            own_tech = own.get("tech_leadership", 50)
            if competitors:
                avg_comp_tech = sum(c["tech_leadership"] for c in competitors) / len(competitors)
                if own_tech < avg_comp_tech:
                    score += (avg_comp_tech - own_tech) * 0.5

        elif cat == "display":
            # Display matters for ecosystem experience and premium perception
            score += dna.get("ecosystem_lock", 0.5) * 20
            score += dna.get("innovation_lead", 0.5) * 10
            # Brands with high brand_heat want premium display
            score += (own.get("brand_heat", 50) / 100) * 10

        elif cat == "camera":
            # Camera matters for customer satisfaction and innovation
            score += dna.get("innovation_lead", 0.5) * 15
            # Low CSAT → invest in camera (visible improvement)
            csat = own.get("customer_satisfaction", 50)
            if csat < 70:
                score += (70 - csat) * 0.5
            # Goal-driven: brands that mention camera/imaging in goals
            if any("camera" in g or "imaging" in g or "photo" in g for g in self.goals):
                score += 15

        elif cat == "battery":
            # Battery gives perceived value — volume & price brands love it
            score += dna.get("volume_aggressive", 0.5) * 20
            score += dna.get("price_aggressive", 0.5) * 20

        elif cat == "ai":
            # AI: innovation + ecosystem synergy
            score += dna.get("innovation_lead", 0.5) * 20
            score += dna.get("ecosystem_lock", 0.5) * 20
            # Goal-driven: brands that mention ai in goals
            if any("ai" in g.lower() for g in self.goals):
                score += 10

        # Universal: competitor gap in tech_leadership (catch-up bonus for ALL categories)
        own_tech = own.get("tech_leadership", 50)
        if competitors:
            avg_comp_tech = sum(c["tech_leadership"] for c in competitors) / len(competitors)
            if own_tech < avg_comp_tech:
                score += (avg_comp_tech - own_tech) * 0.2

        return round(score, 1)

    # --- Pricing scoring ---

    def _score_pricing(self, own: dict, competitors: list[dict]) -> dict[str, float]:
        dna = self.dna
        scores = {}

        # Premium
        premium = 50.0
        premium += dna.get("profit_first", 0.5) * 40
        premium += dna.get("innovation_lead", 0.5) * 10
        if competitors:
            avg_margin = sum(c.get("profit_margin", 15) for c in competitors) / len(competitors)
            if avg_margin < 10:
                premium -= 20  # market is price-cutting, premium is risky
        scores["premium"] = round(premium, 1)

        # Aggressive
        aggressive = 50.0
        aggressive += dna.get("volume_aggressive", 0.5) * 40
        aggressive += dna.get("price_aggressive", 0.5) * 25
        aggressive -= dna.get("profit_first", 0.5) * 20
        scores["aggressive"] = round(aggressive, 1)

        # Balanced (moderate baseline, less DNA-driven)
        balanced = 50.0 + 15.0
        scores["balanced"] = round(balanced, 1)

        return scores

    # --- Supply scoring ---

    def _score_supply(self, own: dict) -> dict[str, float]:
        dna = self.dna
        stability = own.get("supply_stability", 50)
        scores = {}

        # Diversify
        diversify = 50.0
        diversify += dna.get("supply_diversify", 0.5) * 25
        diversify += dna.get("risk_appetite", 0.5) * 15
        if stability < 50:
            diversify += 20  # urgent need
        scores["diversify"] = round(diversify, 1)

        # Fortify: prefer when supply_diversify is LOW (already have good partners)
        fortify = 50.0
        fortify += (1 - dna.get("supply_diversify", 0.5)) * 20
        if stability >= 50:
            fortify += 15
        else:
            fortify += 5
        scores["fortify"] = round(fortify, 1)

        # Cost cut: profit-first brands squeeze suppliers
        cost_cut = 50.0
        cost_cut += dna.get("profit_first", 0.5) * 35
        cost_cut -= dna.get("supply_diversify", 0.5) * 15
        scores["cost_cut"] = round(cost_cut, 1)

        return scores

    # ------------------------------------------------------------------
    # Step 3 — Select
    # ------------------------------------------------------------------

    def _select(self, options: dict) -> dict:
        """Pick the highest-scoring option for each dimension."""
        tech_chosen = max(options["tech_investment"], key=options["tech_investment"].get)
        pricing_chosen = max(options["pricing"], key=options["pricing"].get)
        supply_chosen = max(options["supply"], key=options["supply"].get)

        return {
            "tech_investment": {
                "chosen": tech_chosen,
                "score": options["tech_investment"][tech_chosen],
                "all_scores": options["tech_investment"],
            },
            "pricing": {
                "chosen": pricing_chosen,
                "score": options["pricing"][pricing_chosen],
                "all_scores": options["pricing"],
            },
            "supply": {
                "chosen": supply_chosen,
                "score": options["supply"][supply_chosen],
                "all_scores": options["supply"],
            },
        }

    # ------------------------------------------------------------------
    # Step 4 — Act
    # ------------------------------------------------------------------

    def _act(self, choice: dict, state: "WorldStateData") -> dict:
        """Apply the chosen decisions to brand_state. Returns trace dict."""
        bs = state.brand_states[self.id]
        dna = self.dna
        effects: list[str] = []
        reasons: dict[str, str] = {}

        # --- A: Tech Investment ---
        tech_cat = choice["tech_investment"]["chosen"]
        tech_score = choice["tech_investment"]["score"]
        cash = bs.get("cash_reserve", 0)
        invest = cash * dna.get("risk_appetite", 0.5) * 0.3
        invest = max(0.1, min(invest, 5.0))  # cap at 5 billion
        if cash >= invest:
            bs["cash_reserve"] = round(cash - invest, 2)
            tech_gain = round(dna.get("innovation_lead", 0.5) * 3, 2)
            bs["tech_leadership"] = round(min(100, bs.get("tech_leadership", 50) + tech_gain), 2)
            effects.append(f"cash -{invest:.1f}B")
            effects.append(f"tech_leadership +{tech_gain}")
        reasons["tech_investment"] = (
            f"{self.name} innovation_lead={dna.get('innovation_lead',0):.2f}, "
            f"investing in {tech_cat} (score={tech_score})"
        )

        # --- B: Pricing ---
        pricing = choice["pricing"]["chosen"]
        pricing_score = choice["pricing"]["score"]
        margin = bs.get("profit_margin", 15)
        if pricing == "premium":
            bs["profit_margin"] = round(min(60, margin + 8), 2)
            reasons["pricing"] = (
                f"premium (profit_first={dna.get('profit_first',0):.2f}, "
                f"score={pricing_score})"
            )
        elif pricing == "aggressive":
            bs["profit_margin"] = round(max(1, margin - 6), 2)
            reasons["pricing"] = (
                f"aggressive (volume_aggressive={dna.get('volume_aggressive',0):.2f}, "
                f"score={pricing_score})"
            )
        else:
            bs["profit_margin"] = round(max(1, min(60, margin + 2)), 2)
            reasons["pricing"] = f"balanced (score={pricing_score})"
        effects.append(f"profit_margin → {bs['profit_margin']}%")

        # --- C: Supply ---
        supply = choice["supply"]["chosen"]
        supply_score = choice["supply"]["score"]
        stability = bs.get("supply_stability", 50)
        if supply == "diversify":
            bs["supply_stability"] = round(max(0, min(100, stability + 3)), 2)
            reasons["supply"] = (
                f"diversify (diversify={dna.get('supply_diversify',0):.2f}, "
                f"score={supply_score})"
            )
        elif supply == "fortify":
            bs["supply_stability"] = round(max(0, min(100, stability + 5)), 2)
            reasons["supply"] = f"fortify (score={supply_score})"
        else:
            bs["supply_stability"] = round(max(0, stability - 2), 2)
            bs["profit_margin"] = round(min(60, bs.get("profit_margin", 15) + 1), 2)
            reasons["supply"] = (
                f"cost_cut (profit_first={dna.get('profit_first',0):.2f}, "
                f"score={supply_score})"
            )
        effects.append(f"supply_stability → {bs['supply_stability']}")

        # --- Build trace ---
        trace = {
            "tick": state.tick,
            "tech_investment": {
                "chosen": tech_cat,
                "score": tech_score,
                "reason": reasons["tech_investment"],
            },
            "pricing": {
                "chosen": pricing,
                "score": pricing_score,
                "reason": reasons["pricing"],
            },
            "supply": {
                "chosen": supply,
                "score": supply_score,
                "reason": reasons["supply"],
            },
            "effects": effects,
        }

        bs["last_decision"] = trace
        return trace
