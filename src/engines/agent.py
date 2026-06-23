"""AI agent system — board members with personality, memory, and LLM-driven behavior."""

from typing import Optional

from pydantic import BaseModel

from src.llm.client import LLMClient
from src.schemas.board import (
    AgentMemory,
    AgentProfile,
    AgentRole,
    PositionStatement,
    RiskAppetite,
)
from src.utils.config import load_yaml
from src.utils.logging import logger


# Default agent profiles for P0 MVP
DEFAULT_PROFILES = [
    AgentProfile(
        role=AgentRole.CEO,
        name="Alexander Chen",
        goal="公司整体最优，平衡各方利益",
        risk_appetite=RiskAppetite.MODERATE,
        personality="全局思维，善于在技术创新和财务稳健之间找平衡。最终裁决时会综合考虑但有自己判断。",
        expertise=["战略规划", "组织管理", "行业趋势"],
    ),
    AgentProfile(
        role=AgentRole.COO,
        name="Victoria Hayes",
        goal="优化运营效率，确保战略落地执行",
        risk_appetite=RiskAppetite.MODERATE,
        personality="执行力强，关注流程和落地细节。对资源浪费和不切实际的方案天然敏感。",
        expertise=["运营管理", "流程优化", "跨部门协调"],
    ),
    AgentProfile(
        role=AgentRole.CPO,
        name="Marcus Liu",
        goal="打造行业标杆产品，引领用户体验创新",
        risk_appetite=RiskAppetite.AGGRESSIVE,
        personality="产品理想主义者，相信极致体验能改变行业格局，反对'me-too'式的跟随策略。对用户需求有敏锐直觉。",
        expertise=["产品设计", "用户体验", "市场定位", "硬件创新"],
    ),
    AgentProfile(
        role=AgentRole.CIO,
        name="Robert Kim",
        goal="技术驱动业务增长，构建长期技术护城河",
        risk_appetite=RiskAppetite.AGGRESSIVE,
        personality="技术信仰者，相信技术变革能开辟新赛道。对技术债务和架构落后有强烈危机感。",
        expertise=["芯片设计", "操作系统", "AI技术", "架构规划"],
    ),
    AgentProfile(
        role=AgentRole.CFO,
        name="Sarah Johnson",
        goal="确保财务健康，控制成本风险",
        risk_appetite=RiskAppetite.CONSERVATIVE,
        personality="数字驱动的实用主义者，口头禅是'现金流是企业的血液'。对烧钱行为天然警惕。",
        expertise=["财务管理", "成本控制", "投资分析"],
    ),
    AgentProfile(
        role=AgentRole.SUPPLY_CHAIN,
        name="Michael Wang",
        goal="优化供应链成本和稳定性",
        risk_appetite=RiskAppetite.CONSERVATIVE,
        personality="务实低调，最担心断供风险。对'All in 单一供应商'有本能的抵触，信奉'不把鸡蛋放一个篮子'。",
        expertise=["供应链管理", "采购谈判", "物流优化"],
    ),
]


class LLMAgentStatement(BaseModel):
    """LLM output schema for agent statements."""
    position: str
    reasoning: str
    concerns: list[str] = []
    conditions: list[str] = []
    confidence: float = 0.5


class AgentSystem:
    """Manages multiple AI board members and their behavior."""

    def __init__(self, llm: Optional[LLMClient] = None, profiles: Optional[list[AgentProfile]] = None):
        self.llm = llm
        self.profiles: dict[AgentRole, AgentProfile] = {
            p.role: p for p in (profiles or DEFAULT_PROFILES)
        }
        self.memories: dict[AgentRole, AgentMemory] = {}
        self._prompts = load_yaml("prompts.yaml")
        self._init_memories()

    def _init_memories(self) -> None:
        """Initialize empty memories for all agents."""
        for role in self.profiles:
            self.memories[role] = AgentMemory(role=role)

    def get_profiles(self) -> list[AgentProfile]:
        """Return all agent profiles."""
        return list(self.profiles.values())

    async def generate_statement(
        self,
        role: AgentRole,
        topic: str,
        context: str,
        other_statements: list[PositionStatement] = None,
    ) -> PositionStatement:
        """Generate a position statement from an agent.

        Uses LLM if available, otherwise generates a basic statement
        based on the agent's profile and risk appetite.
        """
        profile = self.profiles.get(role)
        if not profile:
            raise ValueError(f"Unknown agent role: {role}")

        if self.llm:
            try:
                return await self._generate_with_llm(
                    profile, topic, context, other_statements
                )
            except Exception as e:
                logger.error("LLM statement generation failed", role=role.value, error=str(e))

        return self._generate_fallback(profile, topic)

    async def _generate_with_llm(
        self,
        profile: AgentProfile,
        topic: str,
        context: str,
        other_statements: list[PositionStatement] = None,
    ) -> PositionStatement:
        """Use LLM to generate a personality-driven statement."""
        prompts = self._prompts.get("agent_statement", {})
        system_template = prompts.get("system", "")
        user_template = prompts.get("user", "")

        memory = self.memories.get(profile.role, AgentMemory(role=profile.role))
        memory_summary = "\n".join(memory.recent_events[-3:]) if memory.recent_events else "（无特殊记忆）"

        other_text = ""
        if other_statements:
            lines = []
            for stmt in other_statements:
                p = self.profiles.get(stmt.role)
                name = p.name if p else stmt.role.value
                lines.append(f"- {name}({stmt.role.value}): {stmt.position} — {stmt.reasoning[:80]}")
            other_text = "\n".join(lines)

        system_prompt = system_template.format(
            agent_name=profile.name,
            agent_role=profile.role.value.upper(),
            agent_goal=profile.goal,
            agent_risk_appetite=profile.risk_appetite.value,
            agent_personality=profile.personality,
            agent_expertise=", ".join(profile.expertise),
            agent_memory_summary=memory_summary,
            satisfaction=memory.satisfaction,
            other_statements=other_text or "（尚无其他人表态）",
        )

        user_prompt = user_template.format(topic=topic, context=context)

        output = await self.llm.chat_json(
            "agent_statement", system_prompt, user_prompt, LLMAgentStatement
        )

        return PositionStatement(
            role=profile.role,
            position=output.position,
            reasoning=output.reasoning,
            concerns=output.concerns,
            conditions=output.conditions,
            confidence=output.confidence,
        )

    def _generate_fallback(self, profile: AgentProfile, topic: str) -> PositionStatement:
        """Generate a basic statement based on profile when LLM unavailable."""
        appetite_map = {
            RiskAppetite.AGGRESSIVE: "支持",
            RiskAppetite.MODERATE: "有条件支持",
            RiskAppetite.CONSERVATIVE: "反对",
        }
        position = appetite_map.get(profile.risk_appetite, "有条件支持")

        return PositionStatement(
            role=profile.role,
            position=position,
            reasoning=f"基于{profile.name}的立场（{profile.risk_appetite.value}风险偏好），对此议题持{position}态度。",
            concerns=["需要更多数据支持决策"] if profile.risk_appetite == RiskAppetite.CONSERVATIVE else [],
            confidence=0.5,
        )

    def update_memory(
        self,
        role: AgentRole,
        event_summaries: list[str],
        decision_summary: str,
    ) -> None:
        """Update an agent's memory after a turn ends."""
        memory = self.memories.get(role)
        if not memory:
            return

        # Add recent events (keep last 8, FIFO)
        memory.recent_events.extend(event_summaries)
        memory.recent_events = memory.recent_events[-8:]

        # Add past decision
        memory.past_decisions.append(decision_summary)
        memory.past_decisions = memory.past_decisions[-5:]
