"""Simplified PROClaim debate engine — 3-phase board debate system."""

import uuid
from typing import Optional

from pydantic import BaseModel

from src.engines.agent import AgentSystem
from src.llm.client import LLMClient
from src.schemas.board import (
    AgentRole,
    BoardDecision,
    DebateRound,
    PositionStatement,
    Vote,
)
from src.utils.config import load_yaml
from src.utils.logging import logger


class DebateAnalysisOutput(BaseModel):
    """LLM output schema for debate conflict extraction."""
    conflicts: list[str] = []
    agreements: list[str] = []
    summary: str = ""


class ClaimDebateEngine:
    """Simplified PROClaim debate framework (3 phases).

    Phase 1 - PROpose: Each agent states their position sequentially
    Phase 2 - CLAsh: Identify conflicts and run 1-2 rounds of counter-arguments
    Phase 3 - RESolve: CEO makes final decision based on all input
    """

    # Order of speaking (CIO first, CEO last as moderator)
    SPEAKING_ORDER = [AgentRole.CIO, AgentRole.CPO, AgentRole.COO, AgentRole.SUPPLY_CHAIN, AgentRole.CFO, AgentRole.CEO]

    def __init__(self, agent_system: AgentSystem, llm: Optional[LLMClient] = None):
        self.agents = agent_system
        self.llm = llm
        self._prompts = load_yaml("prompts.yaml")

    async def run_debate(
        self,
        topic: str,
        context: str,
        options: list[str],
        max_clash_rounds: int = 1,
    ) -> tuple[list[DebateRound], BoardDecision]:
        """Execute the full 3-phase debate.

        Returns:
            Tuple of (debate_rounds, final_decision)
        """
        rounds: list[DebateRound] = []

        # Phase 1: PROpose — each agent states position
        propose_round = await self._phase_propose(topic, context)
        rounds.append(propose_round)

        # Phase 2: CLAsh — identify conflicts and debate
        has_conflicts = any(
            s.position in ("反对", "有条件支持") for s in propose_round.statements
        )
        if has_conflicts:
            for clash_num in range(max_clash_rounds):
                clash_round = await self._phase_clash(
                    topic, context, propose_round.statements, clash_num + 1
                )
                rounds.append(clash_round)
                if clash_round.consensus_reached:
                    break

        # Phase 3: RESolve — CEO makes final decision
        all_statements = []
        for r in rounds:
            all_statements.extend(r.statements)

        decision = await self._phase_resolve(topic, options, all_statements)

        return rounds, decision

    async def _phase_propose(self, topic: str, context: str) -> DebateRound:
        """Phase 1: Each agent states their position."""
        statements: list[PositionStatement] = []

        for role in self.SPEAKING_ORDER:
            stmt = await self.agents.generate_statement(
                role=role,
                topic=topic,
                context=context,
                other_statements=statements,  # Each sees previous statements
            )
            statements.append(stmt)

        return DebateRound(
            round_number=1,
            topic=topic,
            statements=statements,
            summary=f"各方对'{topic}'进行了初步表态",
        )

    async def _phase_clash(
        self,
        topic: str,
        context: str,
        existing_statements: list[PositionStatement],
        clash_num: int,
    ) -> DebateRound:
        """Phase 2: Identify conflicts and run counter-arguments."""
        # Extract conflicts (use LLM if available, otherwise heuristic)
        conflicts = await self._extract_conflicts(topic, existing_statements)

        if not conflicts:
            return DebateRound(
                round_number=clash_num + 1,
                topic=topic,
                consensus_reached=True,
                summary="各方无明显分歧，达成共识。",
            )

        # Have opposing agents respond to conflicts
        clash_context = context + f"\n\n主要分歧点：{'；'.join(conflicts)}"
        statements: list[PositionStatement] = []

        # Only agents with opposing views participate
        dissenters = [
            s.role for s in existing_statements
            if s.position in ("反对", "有条件支持")
        ]
        supporters = [
            s.role for s in existing_statements
            if s.position == "支持"
        ]

        # Let one supporter and one dissenter debate
        participants = []
        if supporters:
            participants.append(supporters[0])
        if dissenters:
            participants.append(dissenters[0])

        for role in participants:
            stmt = await self.agents.generate_statement(
                role=role,
                topic=f"针对分歧点回应：{conflicts[0]}",
                context=clash_context,
                other_statements=existing_statements + statements,
            )
            statements.append(stmt)

        # Check if consensus emerged
        all_positions = [s.position for s in existing_statements + statements]
        support_count = sum(1 for p in all_positions if p == "支持")
        consensus = support_count >= len(all_positions) * 0.6

        return DebateRound(
            round_number=clash_num + 1,
            topic=topic,
            statements=statements,
            consensus_reached=consensus,
            summary=f"针对分歧点进行了第{clash_num}轮交锋",
        )

    async def _phase_resolve(
        self,
        topic: str,
        options: list[str],
        all_statements: list[PositionStatement],
    ) -> BoardDecision:
        """Phase 3: CEO makes final decision."""
        # Collect votes from all roles
        votes: list[Vote] = []
        for stmt in all_statements:
            # Map position to option
            if stmt.position == "支持" and options:
                choice = options[0]
            elif stmt.position == "反对" and len(options) > 1:
                choice = options[-1]
            else:
                choice = options[0] if options else "维持现状"

            votes.append(Vote(role=stmt.role, choice=choice, reasoning=stmt.reasoning))

        # CEO makes final call
        ceo_stmts = [s for s in all_statements if s.role == AgentRole.CEO]
        ceo_rationale = ceo_stmts[-1].reasoning if ceo_stmts else "综合各方意见做出决策"

        # Determine final choice (CEO vote wins, or majority)
        ceo_votes = [v for v in votes if v.role == AgentRole.CEO]
        if ceo_votes:
            final_choice = ceo_votes[-1].choice
        else:
            # Simple majority
            choice_counts: dict[str, int] = {}
            for v in votes:
                choice_counts[v.choice] = choice_counts.get(v.choice, 0) + 1
            final_choice = max(choice_counts, key=choice_counts.get) if choice_counts else options[0] if options else "维持现状"

        # Record dissenting opinions
        dissenting = [
            s.reasoning for s in all_statements
            if s.position == "反对" and s.role != AgentRole.CEO
        ]

        return BoardDecision(
            topic=topic,
            options=options,
            votes=votes,
            final_choice=final_choice,
            ceo_rationale=ceo_rationale,
            dissenting_opinions=dissenting,
        )

    async def _extract_conflicts(
        self,
        topic: str,
        statements: list[PositionStatement],
    ) -> list[str]:
        """Extract main conflict points from statements."""
        if self.llm:
            try:
                prompts = self._prompts.get("debate_analysis", {})
                system = prompts.get("system", "你是辩论分析师。")
                user_template = prompts.get("user", "")

                stmt_text = "\n".join(
                    f"- {s.role.value}: {s.position} — {s.reasoning[:100]}"
                    for s in statements
                )
                user = user_template.format(topic=topic, statements=stmt_text)

                output = await self.llm.chat_json(
                    "debate_analysis", system, user, DebateAnalysisOutput
                )
                return output.conflicts
            except Exception as e:
                logger.error("Conflict extraction failed", error=str(e))

        # Fallback: simple heuristic
        positions = [s.position for s in statements]
        if "支持" in positions and "反对" in positions:
            return ["各方在是否推进该方案上存在根本分歧"]
        if "有条件支持" in positions:
            return ["部分成员对方案附加了前提条件"]
        return []
