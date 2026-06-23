"""Technology Roadmap API routes — component selection and prediction."""

from fastapi import APIRouter, Depends

from src.dependencies import get_tech_roadmap_engine
from src.engines.tech_roadmap import TechRoadmapEngine, TechSelection

router = APIRouter()


@router.get("/tech/catalog")
async def get_catalog(engine: TechRoadmapEngine = Depends(get_tech_roadmap_engine)):
    """Get the full component technology catalog."""
    categories = engine.get_catalog()
    return {
        "categories": [
            {
                "id": cat.id,
                "name": cat.name,
                "default_option_id": cat.default_option_id,
                "options": [
                    {
                        "id": opt.id,
                        "name": opt.name,
                        "tier": opt.tier,
                        "cost_share_pct": opt.cost_share_pct,
                        "quality_score": opt.quality_score,
                        "tech_maturity": opt.tech_maturity,
                        "selling_point_tags": opt.selling_point_tags,
                        "ffr_base": opt.ffr_base,
                        "supplier_lock_required": opt.supplier_lock_required,
                        "description": opt.description,
                        "space_cost": opt.space_cost,
                        "research_type": opt.research_type,
                        "conflicts_with": opt.conflicts_with,
                    }
                    for opt in cat.options
                ],
            }
            for cat in categories
        ]
    }


@router.post("/tech/predict")
async def predict_tech(
    data: dict,
    engine: TechRoadmapEngine = Depends(get_tech_roadmap_engine),
):
    """Predict cascading effects of component selections.

    Body: {
        "selections": [{"category_id": "soc", "option_id": "soc_snapdragon_3nm"}, ...],
        "target_tier": "short_term"  // "short_term" / "mid_term" / "long_term"
    }
    """
    selections = [
        TechSelection(category_id=s["category_id"], option_id=s["option_id"])
        for s in data.get("selections", [])
    ]
    target_tier = data.get("target_tier", "short_term")
    result = await engine.predict(selections, target_tier=target_tier)
    return {
        "selections": [{"category_id": s.category_id, "option_id": s.option_id} for s in result.selections],
        "total_bom_cost_pct": result.total_bom_cost_pct,
        "bom_cost_vs_baseline_pct": result.bom_cost_vs_baseline_pct,
        "ffr_rate": result.ffr_rate,
        "quality_score": result.quality_score,
        "selling_points": [{"tag": tag, "weight": round(weight, 2)} for tag, weight in result.selling_points],
        "reputation_prediction": result.reputation_prediction,
        "reputation_score": result.reputation_score,
        "risk_warnings": result.risk_warnings,
        "competitive_advantage": result.competitive_advantage,
        "total_space_cost": result.total_space_cost,
        "space_budget": result.space_budget,
        "space_over_budget": result.space_over_budget,
        "maturity_penalties": [
            {
                "option_name": p.option_name,
                "option_tier": p.option_tier,
                "target_tier": p.target_tier,
                "tier_diff": p.tier_diff,
                "cost_impact": p.cost_impact,
                "ffr_impact": p.ffr_impact,
                "quality_impact": p.quality_impact,
            }
            for p in result.maturity_penalties
        ],
        "space_conflicts": [
            {
                "option_a": c.option_a,
                "option_b": c.option_b,
                "description": c.description,
            }
            for c in result.space_conflicts
        ],
        "research_risks": [
            {
                "option_name": r.option_name,
                "research_type": r.research_type,
                "description": r.description,
                "impact": r.impact,
            }
            for r in result.research_risks
        ],
    }


@router.get("/tech/trends")
async def get_trends(
    period: str = "short_term",
    engine: TechRoadmapEngine = Depends(get_tech_roadmap_engine),
):
    """Get market trend weights for a given period (dynamic, RSS-adjusted)."""
    trends = await engine._get_effective_trends(period)
    return {"period": period, "trends": trends}


@router.get("/tech/trends/comparison")
async def get_trends_comparison(
    period: str = "short_term",
    engine: TechRoadmapEngine = Depends(get_tech_roadmap_engine),
):
    """Compare static vs RSS-dynamic trends for transparency."""
    return await engine.get_trends_comparison(period)
