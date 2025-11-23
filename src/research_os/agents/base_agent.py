"""
Base Research Agent

Agents are autonomous researchers with different perspectives and biases.
They independently investigate questions, then debate their findings.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class AgentRole(Enum):
    """Different agent roles in research"""
    OPTIMIST = "optimist"  # Finds supporting evidence
    SKEPTIC = "skeptic"  # Finds contradicting evidence
    METHODOLOGIST = "methodologist"  # Critiques methodology
    SYNTHESIZER = "synthesizer"  # Reconciles views
    EXPLORER = "explorer"  # Discovers new angles
    VALIDATOR = "validator"  # Cross-checks facts


@dataclass
class ResearchFinding:
    """A finding from an agent's research"""
    claim: str
    evidence: List[str]  # Source URLs or references
    confidence: float
    agent_role: AgentRole
    timestamp: datetime = field(default_factory=datetime.now)
    reasoning: Optional[str] = None  # Why the agent believes this


@dataclass
class AgentArgument:
    """An argument made by an agent in debate"""
    agent_id: str
    position: str
    supporting_evidence: List[ResearchFinding]
    counter_arguments: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


class ResearchAgent:
    """
    Base class for research agents.

    Each agent has a role and bias that affects how it researches.
    """

    def __init__(
        self,
        agent_id: str,
        role: AgentRole,
        bias: Optional[str] = None
    ):
        self.agent_id = agent_id
        self.role = role
        self.bias = bias
        self.findings: List[ResearchFinding] = []

    def research(self, question: str, context: Dict[str, Any] = None) -> List[ResearchFinding]:
        """
        Conduct research on a question.

        Each agent type researches differently based on its role.
        """
        raise NotImplementedError("Subclasses must implement research()")

    def critique(self, finding: ResearchFinding) -> Optional[AgentArgument]:
        """
        Critique another agent's finding.

        Returns an argument if the agent disagrees.
        """
        raise NotImplementedError("Subclasses must implement critique()")

    def adjust_confidence(self, finding: ResearchFinding, feedback: List[AgentArgument]) -> float:
        """
        Adjust confidence in a finding based on peer feedback.

        This is how agents learn from debate.
        """
        # Base implementation: reduce confidence if there are counter-arguments
        if not feedback:
            return finding.confidence

        num_counters = sum(1 for arg in feedback if self._is_counter_argument(arg, finding))

        # Reduce confidence based on counter-arguments
        reduction = min(num_counters * 0.1, 0.5)  # Max 50% reduction
        return max(finding.confidence - reduction, 0.1)

    def _is_counter_argument(self, argument: AgentArgument, finding: ResearchFinding) -> bool:
        """Check if an argument counters a finding"""
        # Simple heuristic: check if argument mentions the finding's claim
        return finding.claim.lower() in argument.position.lower()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(role={self.role.value}, findings={len(self.findings)})"


class OptimistAgent(ResearchAgent):
    """
    Agent that looks for supporting evidence.

    Bias: Confirmation - seeks evidence that supports the hypothesis.
    """

    def __init__(self, agent_id: str = "optimist"):
        super().__init__(agent_id, AgentRole.OPTIMIST, bias="confirmation")

    def research(self, question: str, context: Dict[str, Any] = None) -> List[ResearchFinding]:
        """
        Research with optimistic bias.

        In full implementation, this would:
        - Search for confirming evidence
        - Weight positive findings more heavily
        - Look for success stories and positive outcomes
        """
        # Placeholder - actual implementation would query sources
        return []

    def critique(self, finding: ResearchFinding) -> Optional[AgentArgument]:
        """Optimist rarely critiques - tends to accept findings"""
        # Only critique if confidence is very low
        if finding.confidence < 0.3:
            return AgentArgument(
                agent_id=self.agent_id,
                position=f"While the evidence for '{finding.claim}' is weak, there may be unreported supporting evidence.",
                supporting_evidence=[]
            )
        return None


class SkepticAgent(ResearchAgent):
    """
    Agent that looks for contradicting evidence and flaws.

    Bias: Skepticism - seeks evidence that contradicts the hypothesis.
    """

    def __init__(self, agent_id: str = "skeptic"):
        super().__init__(agent_id, AgentRole.SKEPTIC, bias="skepticism")

    def research(self, question: str, context: Dict[str, Any] = None) -> List[ResearchFinding]:
        """
        Research with skeptical bias.

        In full implementation, this would:
        - Search for contradicting evidence
        - Look for alternative explanations
        - Identify potential flaws and biases
        """
        return []

    def critique(self, finding: ResearchFinding) -> Optional[AgentArgument]:
        """Skeptic critiques aggressively"""
        # Always question high-confidence claims
        if finding.confidence > 0.7:
            return AgentArgument(
                agent_id=self.agent_id,
                position=f"The claim '{finding.claim}' may be overconfident. We should seek contradicting evidence.",
                supporting_evidence=[],
                counter_arguments=[finding.claim]
            )
        return None


class MethodologistAgent(ResearchAgent):
    """
    Agent that critiques research methodology.

    Bias: Methodological rigor - focuses on quality of evidence.
    """

    def __init__(self, agent_id: str = "methodologist"):
        super().__init__(agent_id, AgentRole.METHODOLOGIST, bias="methodological_rigor")

    def research(self, question: str, context: Dict[str, Any] = None) -> List[ResearchFinding]:
        """
        Research focused on methodology.

        In full implementation, this would:
        - Assess quality of sources
        - Check for methodological issues
        - Look for meta-analyses and systematic reviews
        """
        return []

    def critique(self, finding: ResearchFinding) -> Optional[AgentArgument]:
        """Critique methodology"""
        # Check evidence quality
        if len(finding.evidence) < 2:
            return AgentArgument(
                agent_id=self.agent_id,
                position=f"The claim '{finding.claim}' is supported by insufficient evidence ({len(finding.evidence)} source(s)). Need more sources for confidence.",
                supporting_evidence=[]
            )
        return None


class SynthesizerAgent(ResearchAgent):
    """
    Agent that reconciles different perspectives.

    Bias: Synthesis - seeks middle ground and integration.
    """

    def __init__(self, agent_id: str = "synthesizer"):
        super().__init__(agent_id, AgentRole.SYNTHESIZER, bias="synthesis")

    def research(self, question: str, context: Dict[str, Any] = None) -> List[ResearchFinding]:
        """
        Research focused on synthesis.

        In full implementation, this would:
        - Look for ways to reconcile contradictions
        - Find common ground
        - Identify complementary perspectives
        """
        return []

    def critique(self, finding: ResearchFinding) -> Optional[AgentArgument]:
        """Synthesizer tries to integrate, not critique"""
        return None

    def synthesize(self, findings: List[ResearchFinding]) -> ResearchFinding:
        """Synthesize multiple findings into one"""
        if not findings:
            return ResearchFinding(
                claim="No findings to synthesize",
                evidence=[],
                confidence=0.0,
                agent_role=self.role
            )

        # Collect all evidence
        all_evidence = []
        for finding in findings:
            all_evidence.extend(finding.evidence)

        # Average confidence (weighted by number of sources)
        total_weight = sum(len(f.evidence) for f in findings)
        if total_weight == 0:
            avg_confidence = sum(f.confidence for f in findings) / len(findings)
        else:
            avg_confidence = sum(
                f.confidence * len(f.evidence) / total_weight
                for f in findings
            )

        # Create synthesis claim
        synthesis_claim = f"Based on {len(findings)} perspectives: "
        synthesis_claim += " | ".join(f.claim for f in findings[:3])  # Top 3
        if len(findings) > 3:
            synthesis_claim += f" | and {len(findings) - 3} more"

        return ResearchFinding(
            claim=synthesis_claim,
            evidence=all_evidence,
            confidence=avg_confidence,
            agent_role=self.role,
            reasoning="Synthesized from multiple agent findings"
        )

    def __repr__(self) -> str:
        return f"SynthesizerAgent(findings={len(self.findings)})"
