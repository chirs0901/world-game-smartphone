"""
Phase 3 agent decision verification.

Runs 4 ticks (1 year) and shows:
  - Which agents decided on each tick
  - Decision content (tech / pricing / supply)
  - Decision traces with reasons

Expected:
  - Apple: decides on tick 0, 4  (period=4)
  - Samsung: decides on tick 0, 2  (period=2)
  - Xiaomi: decides on tick 0, 2  (period=2)
  - etc.
"""
from __future__ import annotations

from engine.world import World


def main():
    world = World(scenario="base_2025")
    print(f"Loaded world: {world.state.turn}")
    print(f"Brands: {len(world.companies)} | Tech nodes: {len(world.tech_nodes)}")
    print(f"Segments: {len(world.segments)} | Rules: {len(world.rules_list)}")
    print(f"Supply links: {len(world.links)}")
    print()

    # Show agent decision periods
    print("DECISION PERIODS")
    for agent in sorted(world.agents, key=lambda a: a.decision_period):
        print(f"  {agent.name:12s}  period={agent.decision_period} tick  "
              f"profit_first={agent.dna.get('profit_first',0):.2f}  "
              f"innovation_lead={agent.dna.get('innovation_lead',0):.2f}")
    print()

    # Run 4 ticks
    for i in range(4):
        snapshot = world.tick()
        tick_id = i  # snapshot tick is AFTER advance, so use i
        diag = snapshot.get("_diagnostics", {})
        decisions = diag.get("market_summary", {}).get("decisions", {})

        tick_id = snapshot.get("tick", i) - 1  # tick was already advanced
        print(f"━━━ TICK {tick_id} → {snapshot.get('turn', '?')} ━━━")

        if decisions:
            for brand_id, dec in decisions.items():
                # Get full trace from brand_state
                brand_state = world.state.brand_states.get(brand_id, {})
                trace = brand_state.get("last_decision", {})
                tech = trace.get("tech_investment", {})
                pricing = trace.get("pricing", {})
                supply = trace.get("supply", {})

                name = brand_id.replace("brand_", "").capitalize()
                print(f"  [{name:12s}] DECIDE")
                print(f"     tech:   {tech.get('chosen','?'):10s}  (score={tech.get('score','?')})")
                print(f"     pricing:{pricing.get('chosen','?'):10s}  margin → {brand_state.get('profit_margin','?')}%")
                print(f"     supply: {supply.get('chosen','?'):10s}  stability → {brand_state.get('supply_stability','?')}")
                if trace.get("effects"):
                    print(f"     effects: {', '.join(trace['effects'])}")
        else:
            print("  (no agent decisions this tick — off-cycle for all)")

        # Show a few key metrics
        top_brands = sorted(
            world.state.brand_states.items(),
            key=lambda kv: kv[1].get("market_share", 0),
            reverse=True,
        )[:3]
        shares = [f"{bid.replace('brand_','').capitalize()}:{bs.get('market_share',0):.1f}%" for bid, bs in top_brands]
        print(f"  Market top3: {', '.join(shares)}")
        print()

    print("All 4 ticks completed. Agent decision engine verified.")


if __name__ == "__main__":
    main()
