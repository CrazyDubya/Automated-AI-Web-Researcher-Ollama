"""
Research Committee - Multi-agent debate and consensus

Instead of one LLM answering, we spawn a committee of agents that:
1. Independently research the question
2. Present their findings
3. Debate and challenge each other
4. Reach consensus (or document disagreement)

This mirrors how real research works: peer review, replication, debate.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime

from .base_agent import (
    ResearchAgent,
    OptimistAgent,
    SkepticAgent,
    MethodologistAgent,
    SynthesizerAgent,
    ResearchFinding,
    AgentArgument,
    AgentRole
)


@dataclass
class DebateTranscript:
    """Record of a research committee's deliberation"""

    question: str
    agents: List[str]  # Agent IDs
    started_at: datetime
    ended_at: Optional[datetime] = None

    # Research phases
    findings: List[ResearchFinding] = field(default_factory=list)
    arguments: List[AgentArgument] = field(default_factory=list)

    # Consensus
    consensus_reached: bool = False
    consensus_finding: Optional[ResearchFinding] = None
    confidence: float = 0.0

    # Metadata
    rounds: int = 0
    contradictions_identified: int = 0

    def get_summary(self) -> str:
        """Human-readable summary of the debate"""

        summary = f"=== Research Committee Debate ===\n\n"
        summary += f"Question: {self.question}\n"
        summary += f"Agents: {', '.join(self.agents)}\n"
        summary += f"Duration: {self.started_at.strftime('%Y-%m-%d %H:%M')} - "

        if self.ended_at:
            duration = (self.ended_at - self.started_at).total_seconds() / 60
            summary += f"{self.ended_at.strftime('%H:%M')} ({duration:.1f} min)\n"
        else:
            summary += "In progress\n"

        summary += f"Rounds: {self.rounds}\n"
        summary += f"Findings: {len(self.findings)}\n"
        summary += f"Arguments: {len(self.arguments)}\n\n"

        if self.consensus_reached:
            summary += f"✓ CONSENSUS REACHED (confidence: {self.confidence:.2%})\n\n"
            if self.consensus_finding:
                summary += f"Conclusion: {self.consensus_finding.claim}\n"
                summary += f"Evidence: {len(self.consensus_finding.evidence)} source(s)\n"
        else:
            summary += f"✗ NO CONSENSUS (confidence: {self.confidence:.2%})\n\n"
            summary += f"The committee remains divided. Further research needed.\n"

        if self.contradictions_identified > 0:
            summary += f"\n⚠️  {self.contradictions_identified} contradictions identified\n"

        return summary

    def __str__(self) -> str:
        return self.get_summary()


class ResearchCommittee:
    """
    A committee of research agents that deliberate on a question.

    The committee follows this protocol:
    1. Each agent independently researches
    2. Agents present findings
    3. Agents challenge each other's findings
    4. Synthesizer attempts to reconcile
    5. Repeat until consensus or timeout
    """

    def __init__(
        self,
        question: str,
        agents: Optional[List[ResearchAgent]] = None,
        max_rounds: int = 3,
        consensus_threshold: float = 0.7
    ):
        self.question = question
        self.max_rounds = max_rounds
        self.consensus_threshold = consensus_threshold

        # Default committee composition
        if agents is None:
            self.agents = [
                OptimistAgent(),
                SkepticAgent(),
                MethodologistAgent(),
                SynthesizerAgent()
            ]
        else:
            self.agents = agents

        # Transcript
        self.transcript = DebateTranscript(
            question=question,
            agents=[a.agent_id for a in self.agents],
            started_at=datetime.now()
        )

    def deliberate(self, context: Optional[Dict[str, Any]] = None) -> DebateTranscript:
        """
        Run the full deliberation process.

        Returns a transcript of the debate.
        """

        for round_num in range(1, self.max_rounds + 1):
            self.transcript.rounds = round_num

            print(f"\n--- Round {round_num} ---")

            # Phase 1: Independent research
            round_findings = self._research_phase(context)
            self.transcript.findings.extend(round_findings)

            if not round_findings:
                print("No findings in this round. Ending deliberation.")
                break

            # Phase 2: Debate
            arguments = self._debate_phase(round_findings)
            self.transcript.arguments.extend(arguments)

            # Phase 3: Check for consensus
            consensus = self._check_consensus(round_findings)

            if consensus:
                self.transcript.consensus_reached = True
                self.transcript.consensus_finding = consensus
                self.transcript.confidence = consensus.confidence
                print(f"\n✓ Consensus reached: {consensus.claim}")
                break

            # If no consensus, identify what we need to research next
            if round_num < self.max_rounds:
                context = self._prepare_next_round(round_findings, arguments)

        self.transcript.ended_at = datetime.now()

        return self.transcript

    def _research_phase(self, context: Optional[Dict[str, Any]] = None) -> List[ResearchFinding]:
        """Phase 1: Each agent independently researches"""

        print("\nPhase 1: Independent Research")

        findings = []

        for agent in self.agents:
            print(f"  {agent.agent_id} researching...")

            # Agent conducts research
            agent_findings = agent.research(self.question, context)

            findings.extend(agent_findings)
            print(f"    → {len(agent_findings)} finding(s)")

        return findings

    def _debate_phase(self, findings: List[ResearchFinding]) -> List[AgentArgument]:
        """Phase 2: Agents challenge each other's findings"""

        print("\nPhase 2: Debate")

        arguments = []

        # Each agent critiques other agents' findings
        for agent in self.agents:
            for finding in findings:
                # Don't critique own findings
                if finding.agent_role == agent.role:
                    continue

                argument = agent.critique(finding)

                if argument:
                    arguments.append(argument)
                    print(f"  {agent.agent_id} → {argument.position[:80]}...")

        return arguments

    def _check_consensus(self, findings: List[ResearchFinding]) -> Optional[ResearchFinding]:
        """Phase 3: Check if consensus has been reached"""

        if not findings:
            return None

        # Get synthesizer agent
        synthesizer = next(
            (a for a in self.agents if isinstance(a, SynthesizerAgent)),
            None
        )

        if not synthesizer:
            # No synthesizer, just take highest confidence finding
            best_finding = max(findings, key=lambda f: f.confidence)
            if best_finding.confidence >= self.consensus_threshold:
                return best_finding
            return None

        # Let synthesizer create consensus
        synthesis = synthesizer.synthesize(findings)

        if synthesis.confidence >= self.consensus_threshold:
            return synthesis

        return None

    def _prepare_next_round(
        self,
        findings: List[ResearchFinding],
        arguments: List[AgentArgument]
    ) -> Dict[str, Any]:
        """Prepare context for next round based on current findings"""

        # Identify contradictions
        contradictions = []
        for i, f1 in enumerate(findings):
            for f2 in findings[i+1:]:
                # Simple contradiction detection: opposite claims
                if self._are_contradictory(f1, f2):
                    contradictions.append((f1, f2))

        self.transcript.contradictions_identified = len(contradictions)

        # Build context for next round
        context = {
            "previous_findings": findings,
            "arguments": arguments,
            "contradictions": contradictions,
            "round": self.transcript.rounds
        }

        if contradictions:
            print(f"\n⚠️  {len(contradictions)} contradictions detected. Agents will investigate...")

        return context

    def _are_contradictory(self, f1: ResearchFinding, f2: ResearchFinding) -> bool:
        """Simple contradiction detection"""
        # Placeholder - in real implementation, use NLP or LLM to detect contradictions
        claim1 = f1.claim.lower()
        claim2 = f2.claim.lower()

        # Check for negation words
        negations = ["not", "no", "never", "contrary", "opposite", "disagree"]

        # If one has negation and they share key words, might be contradictory
        has_negation = any(neg in claim1 or neg in claim2 for neg in negations)

        # Share significant words (simple heuristic)
        words1 = set(w for w in claim1.split() if len(w) > 4)
        words2 = set(w for w in claim2.split() if len(w) > 4)
        overlap = words1.intersection(words2)

        return has_negation and len(overlap) > 2

    def get_agent_by_role(self, role: AgentRole) -> Optional[ResearchAgent]:
        """Get agent by role"""
        return next((a for a in self.agents if a.role == role), None)

    def add_agent(self, agent: ResearchAgent):
        """Add an agent to the committee"""
        self.agents.append(agent)
        self.transcript.agents.append(agent.agent_id)

    def __repr__(self) -> str:
        return f"ResearchCommittee(question='{self.question[:50]}...', agents={len(self.agents)})"
