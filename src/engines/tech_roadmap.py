"""Technology Roadmap Engine — component-level parameter prediction.

Based on the 手机全产业模拟经营游戏配套专业研究报告 white paper.
Models the cascading effects of component choices on:
- Whole-device BOM cost (整机成本)
- Technology selling points (产品技术卖点)
- Field Failure Rate / FFR (产品质量/不良率)
- User reputation / word-of-mouth (用户口碑)
- Technology maturity penalty (技术成熟度惩罚)
- Internal space conflicts (内部空间冲突)
- Self-research vs procurement risk (自研vs采购博弈)
"""

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from src.engines.rss_intel import RSSIntelEngine
    from src.services.rss_service import RSSService


# ──────────────────────────────────────────────────────────
# Component Technology Definitions (from White Paper §2.1)
# ──────────────────────────────────────────────────────────

@dataclass
class ComponentOption:
    """A specific technology option for a component category."""
    id: str
    name: str
    tier: str  # "short_term" / "mid_term" / "long_term"
    cost_share_pct: float  # % of total BOM cost this component accounts for
    quality_score: float  # 0-100, inversely affects FFR
    tech_maturity: float  # 0-1, affects yield & risk (low = risky)
    selling_point_tags: list[str] = field(default_factory=list)
    ffr_base: float = 0.0  # base field failure rate %
    supplier_lock_required: bool = False  # needs exclusive supplier deal
    description: str = ""
    space_cost: float = 0.0  # internal space consumption (relative units, 0-15)
    research_type: str = "procurement"  # "procurement" | "joint_rd" | "self_developed"
    conflicts_with: list[str] = field(default_factory=list)  # conflicting option IDs


@dataclass
class ComponentCategory:
    """A category of components (e.g. SoC, Display, Camera)."""
    id: str
    name: str
    options: list[ComponentOption] = field(default_factory=list)
    default_option_id: str = ""


# ──────────────────────────────────────────────────────────
# Catalog Loader — reads from config/tech_catalog.yaml
# ──────────────────────────────────────────────────────────

def _load_catalog_from_yaml() -> list[ComponentCategory]:
    """Load component technology catalog from YAML config file.

    Falls back to inline defaults if the config file is missing or malformed.
    """
    from src.utils.config import load_yaml

    try:
        raw = load_yaml("tech_catalog.yaml")
        categories = []
        for cat_data in raw.get("categories", []):
            options = []
            for opt_data in cat_data.get("options", []):
                options.append(ComponentOption(
                    id=opt_data["id"],
                    name=opt_data["name"],
                    tier=opt_data.get("tier", "short_term"),
                    cost_share_pct=float(opt_data.get("cost_share_pct", 0)),
                    quality_score=float(opt_data.get("quality_score", 80)),
                    tech_maturity=float(opt_data.get("tech_maturity", 0.8)),
                    selling_point_tags=opt_data.get("selling_point_tags", []),
                    ffr_base=float(opt_data.get("ffr_base", 0.5)),
                    supplier_lock_required=bool(opt_data.get("supplier_lock_required", False)),
                    description=opt_data.get("description", ""),
                    space_cost=float(opt_data.get("space_cost", 0)),
                    research_type=opt_data.get("research_type", "procurement"),
                    conflicts_with=opt_data.get("conflicts_with", []),
                ))
            categories.append(ComponentCategory(
                id=cat_data["id"],
                name=cat_data["name"],
                default_option_id=cat_data.get("default_option_id", ""),
                options=options,
            ))
        return categories
    except Exception:
        import logging
        logging.getLogger(__name__).warning(
            "Failed to load tech_catalog.yaml, using empty catalog"
        )
        return []

# ──────────────────────────────────────────────────────────
# Market Meme / Trend Weights (from White Paper §9)
# ──────────────────────────────────────────────────────────

MARKET_TRENDS = {
    "short_term": {
        "折叠屏": 1.5,
        "端侧AI": 1.4,
        "影像旗舰": 1.3,
        "长续航": 1.2,
        "快充": 1.0,
        "高性价比": 0.9,
        "IP68防护": 1.1,
    },
    "mid_term": {
        "折叠屏": 1.6,
        "端侧AI": 1.5,
        "自研芯片": 1.4,
        "卫星通信": 1.2,
        "固态电池": 1.3,
        "影像革命": 1.3,
    },
    "long_term": {
        "自研2nm": 1.8,
        "固态电池": 1.7,
        "连续光变": 1.6,
        "6G通信": 1.5,
        "智能体AI": 1.6,
        "折叠屏": 1.2,
    },
}

# ──────────────────────────────────────────────────────────
# Game Balance Constants
# ──────────────────────────────────────────────────────────

# Technology tier ordering for maturity penalty calculation
TIER_ORDER = {"short_term": 0, "mid_term": 1, "long_term": 2}

# Internal space budget (relative units) — represents physical constraints
# Average flagship phone has ~8000mm³ usable volume
SPACE_BUDGET = 30.0

# Maturity penalty: multiplier applied when option tier exceeds target market tier
# (tier_diff, cost_multiplier, ffr_multiplier, quality_penalty)
MATURITY_PENALTY = {
    1: (1.30, 1.50, 5),   # one tier ahead: 30% cost increase, 50% FFR increase, -5 quality
    2: (2.00, 3.00, 12),  # two tiers ahead: 100% cost, 300% FFR, -12 quality
}

# Research type risk modifiers
RESEARCH_RISK = {
    "procurement":     (0.0, 0,  "采购",     "通用方案，供应链稳定，无额外风险"),
    "joint_rd":       (0.3, -3, "联合研发",  "需提前2周期投入研发资金，有延期风险"),
    "self_developed":  (0.5, -5, "完全自研",  "需提前2-3周期大量研发投入，良率爬坡缓慢"),
}


# ──────────────────────────────────────────────────────────
# Prediction Engine
# ──────────────────────────────────────────────────────────

@dataclass
class TechSelection:
    """Player's selection for one component category."""
    category_id: str
    option_id: str


@dataclass
class MaturityPenaltyDetail:
    """Detail of a technology maturity penalty."""
    option_name: str
    option_tier: str
    target_tier: str
    tier_diff: int
    cost_impact: str  # human-readable description
    ffr_impact: str
    quality_impact: str


@dataclass
class SpaceConflictDetail:
    """Detail of an internal space conflict."""
    option_a: str
    option_b: str
    description: str


@dataclass
class ResearchRiskDetail:
    """Detail of a self-research / joint-RD risk."""
    option_name: str
    research_type: str
    description: str
    impact: str


@dataclass
class PredictionResult:
    """Cascading prediction results for a given configuration."""
    selections: list[TechSelection]
    total_bom_cost_pct: float  # total BOM cost as % of selling price
    bom_cost_vs_baseline_pct: float  # cost change vs baseline
    ffr_rate: float  # predicted field failure rate %
    quality_score: float  # overall quality score (0-100)
    selling_points: list[tuple[str, float]]  # (tag, weighted impact)
    reputation_prediction: str  # qualitative prediction
    reputation_score: float  # 0-100
    risk_warnings: list[str]
    competitive_advantage: str
    # New enhanced fields
    total_space_cost: float = 0.0
    space_budget: float = SPACE_BUDGET
    space_over_budget: bool = False
    maturity_penalties: list[MaturityPenaltyDetail] = field(default_factory=list)
    space_conflicts: list[SpaceConflictDetail] = field(default_factory=list)
    research_risks: list[ResearchRiskDetail] = field(default_factory=list)


class TechRoadmapEngine:
    """Calculates cascading effects of component choices.

    Supports RSS-driven dynamic trend adjustment: when RSS intelligence is available,
    market trend weights are dynamically adjusted based on real industry signals.
    """

    # Cache TTL for effective trends (5 minutes)
    _TRENDS_CACHE_TTL = 300

    def __init__(
        self,
        rss_service: Optional["RSSService"] = None,
        rss_intel_engine: Optional["RSSIntelEngine"] = None,
    ):
        self._catalog = _load_catalog_from_yaml()
        self._trends = MARKET_TRENDS
        self.rss_service = rss_service
        self.rss_intel_engine = rss_intel_engine
        # Cache: period -> (timestamp, effective_trends)
        self._trends_cache: dict[str, tuple[float, dict[str, float]]] = {}

    def get_catalog(self) -> list[ComponentCategory]:
        return self._catalog

    async def _get_effective_trends(self, period: str = "short_term") -> dict[str, float]:
        """Get market trends merged with RSS-driven dynamic adjustments.

        Static trends are adjusted based on RSS signal sentiment and frequency.
        Results are cached for 5 minutes to avoid excessive RSS polling.
        """
        # Check cache
        cached = self._trends_cache.get(period)
        if cached and (time.time() - cached[0]) < self._TRENDS_CACHE_TTL:
            return cached[1]

        static_trends = dict(self._trends.get(period, self._trends["short_term"]))

        if not self.rss_service or not self.rss_intel_engine:
            self._trends_cache[period] = (time.time(), static_trends)
            return static_trends

        # Get RSS items
        items = self.rss_service.get_cached()
        if not items:
            try:
                items = await self.rss_service.fetch_all()
            except Exception:
                self._trends_cache[period] = (time.time(), static_trends)
                return static_trends

        if not items:
            self._trends_cache[period] = (time.time(), static_trends)
            return static_trends

        # Analyze and calculate adjustments
        signals = self.rss_intel_engine.analyze_items(items)
        adjustments = self.rss_intel_engine.calculate_trend_adjustments(signals, static_trends)

        # Apply adjustments
        effective = dict(static_trends)
        for adj in adjustments:
            effective[adj.tag] = adj.adjusted_weight

        self._trends_cache[period] = (time.time(), effective)
        return effective

    async def get_trends_comparison(self, period: str = "short_term") -> dict:
        """Return static vs dynamic trends comparison for transparency.

        Returns:
            {
                "period": period,
                "static_trends": {...},
                "dynamic_trends": {...},
                "adjustments": [...]
            }
        """
        static_trends = self._trends.get(period, self._trends["short_term"])
        dynamic_trends = await self._get_effective_trends(period)

        adjustments = []
        if self.rss_service and self.rss_intel_engine:
            items = self.rss_service.get_cached()
            if not items:
                try:
                    items = await self.rss_service.fetch_all()
                except Exception:
                    items = []
            if items:
                signals = self.rss_intel_engine.analyze_items(items)
                adjustments = [
                    {
                        "tag": adj.tag,
                        "current_weight": adj.current_weight,
                        "adjusted_weight": adj.adjusted_weight,
                        "reason": adj.reason,
                        "signal_count": adj.signal_count,
                    }
                    for adj in self.rss_intel_engine.calculate_trend_adjustments(signals, static_trends)
                ]

        return {
            "period": period,
            "static_trends": static_trends,
            "dynamic_trends": dynamic_trends,
            "adjustments": adjustments,
        }

    def get_market_trends(self, period: str = "short_term") -> dict[str, float]:
        """Get static market trends (synchronous, for backward compatibility)."""
        return self._trends.get(period, self._trends["short_term"])

    def get_category(self, category_id: str) -> Optional[ComponentCategory]:
        for cat in self._catalog:
            if cat.id == category_id:
                return cat
        return None

    def get_option(self, category_id: str, option_id: str) -> Optional[ComponentOption]:
        cat = self.get_category(category_id)
        if cat is None:
            return None
        for opt in cat.options:
            if opt.id == option_id:
                return opt
        return None

    async def predict(self, selections: list[TechSelection], target_tier: str = "short_term") -> PredictionResult:
        """Calculate cascading prediction for a full component configuration.

        Now includes:
        - Technology maturity penalty (跨周期技术惩罚)
        - Internal space conflict detection (内部空间冲突)
        - Self-research / joint-RD risk quantification (自研博弈风险)
        - RSS-driven dynamic trend weighting (RSS动态趋势权重)

        Args:
            selections: List of component selections (category_id, option_id)
            target_tier: Market period for trend weighting ("short_term" / "mid_term" / "long_term")

        Returns:
            PredictionResult with all cascading effects
        """
        trends = await self._get_effective_trends(target_tier)
        target_tier_ord = TIER_ORDER.get(target_tier, 0)

        risk_warnings: list[str] = []
        maturity_penalties: list[MaturityPenaltyDetail] = []
        space_conflicts: list[SpaceConflictDetail] = []
        research_risks: list[ResearchRiskDetail] = []

        all_tags: dict[str, float] = {}
        total_cost = 0.0
        total_baseline_cost = 0.0
        weighted_ffr = 0.0
        weighted_quality = 0.0
        total_weight = 0.0
        total_space = 0.0
        low_maturity_count = 0
        supplier_locks: list[str] = []

        # Build a map of selected option IDs for conflict detection
        selected_ids_map: dict[str, str] = {}  # category_id -> option_id
        selected_names_map: dict[str, str] = {}  # option_id -> option_name

        # First pass: gather options
        resolved_options: list[tuple[str, ComponentOption]] = []
        for sel in selections:
            cat = self.get_category(sel.category_id)
            if cat is None:
                continue
            opt = self.get_option(sel.category_id, sel.option_id)
            if opt is None:
                continue
            selected_ids_map[sel.category_id] = sel.option_id
            selected_names_map[sel.option_id] = opt.name
            resolved_options.append((sel.category_id, opt))

        # Second pass: calculate metrics with all contextual info
        for category_id, opt in resolved_options:
            cat = self.get_category(category_id)

            # Baseline cost (default option)
            default_opt = next((o for o in cat.options if o.id == cat.default_option_id), None) if cat else None
            baseline_cost = default_opt.cost_share_pct if default_opt else opt.cost_share_pct

            # ── Technology Maturity Penalty ──
            opt_tier_ord = TIER_ORDER.get(opt.tier, 0)
            tier_diff = opt_tier_ord - target_tier_ord

            effective_cost = opt.cost_share_pct
            effective_ffr = opt.ffr_base
            effective_quality = opt.quality_score

            if tier_diff > 0:
                cost_mult, ffr_mult, qual_penalty = MATURITY_PENALTY.get(
                    tier_diff, (1.0, 1.0, 0)
                )
                effective_cost *= cost_mult
                effective_ffr *= ffr_mult
                effective_quality = max(40, effective_quality - qual_penalty)

                tier_labels = {"short_term": "短期", "mid_term": "中期", "long_term": "远期"}
                detail = MaturityPenaltyDetail(
                    option_name=opt.name,
                    option_tier=tier_labels.get(opt.tier, opt.tier),
                    target_tier=tier_labels.get(target_tier, target_tier),
                    tier_diff=tier_diff,
                    cost_impact=f"成本 ×{cost_mult:.1f}（+{(cost_mult-1)*100:.0f}%）",
                    ffr_impact=f"不良率 ×{ffr_mult:.1f}（+{(ffr_mult-1)*100:.0f}%）",
                    quality_impact=f"质量 -{qual_penalty}",
                )
                maturity_penalties.append(detail)
                risk_warnings.append(
                    f"【跨周期惩罚】{opt.name} 为 {detail.option_tier} 技术，"
                    f"在当前 {detail.target_tier} 市场周期上马："
                    f"{detail.cost_impact}、{detail.ffr_impact}、{detail.quality_impact}"
                )

            total_cost += effective_cost
            total_baseline_cost += baseline_cost
            weighted_ffr += effective_ffr * effective_cost
            weighted_quality += effective_quality * effective_cost
            total_weight += effective_cost
            total_space += opt.space_cost

            # ── Research Type Risk ──
            if opt.research_type != "procurement":
                extra_ffr, rep_penalty, type_label, type_desc = RESEARCH_RISK.get(
                    opt.research_type, (0.0, 0, "未知", "")
                )
                weighted_ffr += extra_ffr * effective_cost  # add extra FFR contribution
                detail = ResearchRiskDetail(
                    option_name=opt.name,
                    research_type=type_label,
                    description=type_desc,
                    impact=f"FFR +{extra_ffr}%，口碑 -{abs(rep_penalty)}",
                )
                research_risks.append(detail)
                risk_warnings.append(
                    f"【自研风险】{opt.name} 采用 {type_label} 路线：{type_desc}"
                )

            # ── Selling points ──
            for tag in opt.selling_point_tags:
                trend_weight = trends.get(tag, 1.0)
                all_tags[tag] = all_tags.get(tag, 0) + effective_cost * trend_weight * opt.tech_maturity

            # ── Low maturity risk ──
            if opt.tech_maturity < 0.5:
                low_maturity_count += 1
                risk_warnings.append(f"【良率风险】{opt.name} 技术成熟度仅 {opt.tech_maturity:.0%}，量产良率可能不足")

            # ── Supplier lock risk ──
            if opt.supplier_lock_required:
                supplier_locks.append(opt.name)
                risk_warnings.append(f"【供应风险】{opt.name} 需要独家供应协议，产能受限")

            # ── Quality risk ──
            if opt.quality_score < 75:
                risk_warnings.append(f"【质量风险】{opt.name} 质量评分 {opt.quality_score}，可能导致售后成本上升")

        # ── Internal Space Conflict Detection ──
        for category_id, opt in resolved_options:
            for conflict_id in opt.conflicts_with:
                # Check if any selected option conflicts
                for other_cat_id, other_opt in resolved_options:
                    if other_opt.id == conflict_id and other_cat_id != category_id:
                        conflict_detail = SpaceConflictDetail(
                            option_a=opt.name,
                            option_b=other_opt.name,
                            description=f"{opt.name} 与 {other_opt.name} 在内部空间上冲突，同时选用将导致散热恶化、装配困难",
                        )
                        space_conflicts.append(conflict_detail)
                        risk_warnings.append(
                            f"【空间冲突】{conflict_detail.description}"
                        )

        # ── Space Budget Check ──
        space_over_budget = total_space > SPACE_BUDGET
        if space_over_budget:
            excess = total_space - SPACE_BUDGET
            risk_warnings.append(
                f"【空间超限】内部空间消耗 {total_space:.1f} / {SPACE_BUDGET:.0f}，超出 {excess:.1f} 单位，"
                f"可能导致机身过厚、散热不良"
            )

        # ── Aggregate metrics ──
        bom_cost_vs_baseline = ((total_cost - total_baseline_cost) / total_baseline_cost * 100) if total_baseline_cost > 0 else 0
        ffr_rate = weighted_ffr / total_weight if total_weight > 0 else 0
        quality_score = weighted_quality / total_weight if total_weight > 0 else 80

        # Space penalty on quality
        if space_over_budget:
            excess = total_space - SPACE_BUDGET
            space_quality_penalty = excess * 2
            quality_score = max(30, quality_score - space_quality_penalty)
        # Space conflict penalty on quality
        quality_score = max(30, quality_score - len(space_conflicts) * 3)

        # Sort selling points by weighted impact
        sorted_tags = sorted(all_tags.items(), key=lambda x: x[1], reverse=True)

        # ── Reputation score (0-100) ──
        tag_score = min(25, sum(v for _, v in sorted_tags[:5]) / 10)
        quality_contribution = quality_score * 0.5
        cost_efficiency = max(0, 25 - abs(bom_cost_vs_baseline))

        reputation_score = min(100, quality_contribution + tag_score + cost_efficiency)

        # Research type reputation penalties
        for risk in research_risks:
            _, rep_penalty, _, _ = RESEARCH_RISK.get(
                next((o.research_type for _, o in resolved_options if o.name == risk.option_name), "procurement"),
                (0.0, 0, "", "")
            )
            reputation_score += rep_penalty

        if low_maturity_count > 2:
            reputation_score -= 10
        if len(supplier_locks) > 2:
            reputation_score -= 5
        if len(space_conflicts) > 0:
            reputation_score -= len(space_conflicts) * 5
        if space_over_budget:
            reputation_score -= 8

        reputation_score = max(0, min(100, reputation_score))

        # ── Reputation prediction text ──
        if reputation_score >= 80:
            reputation_prediction = "【遥遥领先】产品配置顶级，市场口碑预计极佳，有望成为年度真香机"
        elif reputation_score >= 65:
            reputation_prediction = "【水桶机】配置均衡全面，无明显短板，市场口碑良好"
        elif reputation_score >= 50:
            reputation_prediction = "【中规中矩】配置尚可但缺乏亮点，难以在激烈竞争中脱颖而出"
        elif reputation_score >= 35:
            reputation_prediction = "【刀法失误】配置存在明显短板，可能遭受数码圈口诛笔伐"
        else:
            reputation_prediction = "【产品翻车】配置严重不合理，良率风险极高，建议重新评估方案"

        # ── Competitive advantage ──
        top_tags = [t[0] for t in sorted_tags[:3]]
        if top_tags:
            competitive_advantage = f"核心卖点: {'、'.join(top_tags)}"
        else:
            competitive_advantage = "缺乏差异化卖点，仅靠价格竞争"

        return PredictionResult(
            selections=selections,
            total_bom_cost_pct=round(total_cost, 1),
            bom_cost_vs_baseline_pct=round(bom_cost_vs_baseline, 1),
            ffr_rate=round(ffr_rate, 2),
            quality_score=round(quality_score, 1),
            selling_points=sorted_tags[:8],
            reputation_prediction=reputation_prediction,
            reputation_score=round(reputation_score, 1),
            risk_warnings=risk_warnings,
            competitive_advantage=competitive_advantage,
            total_space_cost=round(total_space, 1),
            space_budget=SPACE_BUDGET,
            space_over_budget=space_over_budget,
            maturity_penalties=maturity_penalties,
            space_conflicts=space_conflicts,
            research_risks=research_risks,
        )
