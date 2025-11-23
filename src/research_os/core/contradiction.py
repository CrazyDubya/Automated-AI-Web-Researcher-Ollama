"""
Contradiction Detection and Tracking

In ResearchOS, contradictions are FIRST-CLASS CITIZENS, not errors to be resolved.
When sources disagree, that disagreement itself is valuable information.

Contradictions drive new research:
- Why do sources disagree?
- Which source is more reliable?
- Is this a temporal difference (both were true at different times)?
- Is this a definitional difference (they're measuring different things)?
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from .belief import Belief, Claim


class ContradictionType(Enum):
    """Types of contradictions we can detect"""
    DIRECT_NEGATION = "direct_negation"  # "X is Y" vs "X is not Y"
    INCOMPATIBLE_VALUES = "incompatible_values"  # "X is 5" vs "X is 10"
    TEMPORAL_CONFLICT = "temporal_conflict"  # Timeline doesn't make sense
    CAUSAL_CONFLICT = "causal_conflict"  # "X caused Y" vs "Z caused Y"
    METHODOLOGICAL = "methodological"  # Same study, different conclusions


class ContradictionSeverity(Enum):
    """How serious is the contradiction?"""
    TRIVIAL = "trivial"  # Rounding errors, minor differences
    MODERATE = "moderate"  # Significant difference but both plausible
    SEVERE = "severe"  # Fundamentally incompatible claims
    CRITICAL = "critical"  # One must be completely wrong


@dataclass
class Contradiction:
    """
    A contradiction represents incompatible beliefs in our knowledge graph.

    Unlike errors, contradictions are preserved and tracked. They represent:
    - Uncertainty in our knowledge
    - Disagreement between sources
    - Opportunities for deeper investigation
    """

    belief_a: Belief
    belief_b: Belief
    contradiction_type: ContradictionType

    # When was this contradiction discovered?
    detected_at: datetime = field(default_factory=datetime.now)

    # How important is it to resolve this?
    importance_score: float = 0.5  # 0.0 = trivial, 1.0 = critical
    severity: ContradictionSeverity = ContradictionSeverity.MODERATE

    # Resolution status
    is_resolved: bool = False
    resolution_explanation: Optional[str] = None
    resolved_at: Optional[datetime] = None

    # Generated research to investigate this
    spawned_research_ids: list[str] = field(default_factory=list)

    @property
    def contradiction_id(self) -> str:
        """Unique identifier for this contradiction"""
        import hashlib
        contr_str = f"{self.belief_a.belief_id}::{self.belief_b.belief_id}"
        return hashlib.sha256(contr_str.encode()).hexdigest()[:16]

    def get_disagreement_summary(self) -> str:
        """Human-readable explanation of the disagreement"""
        a_claim = self.belief_a.claim.to_natural_language()
        b_claim = self.belief_b.claim.to_natural_language()

        summary = f"Contradiction ({self.contradiction_type.value}):\n"
        summary += f"  Belief A [{self.belief_a.confidence:.2f}]: {a_claim}\n"
        summary += f"    Sources: {len(self.belief_a.source_ids)}\n"
        summary += f"  Belief B [{self.belief_b.confidence:.2f}]: {b_claim}\n"
        summary += f"    Sources: {len(self.belief_b.source_ids)}\n"

        if self.is_resolved:
            summary += f"\n  ✓ Resolved: {self.resolution_explanation}\n"
        else:
            summary += f"\n  ⚠️  Unresolved (importance: {self.importance_score:.2f})\n"

        return summary

    def compute_importance(self) -> float:
        """
        Calculate how important it is to resolve this contradiction.

        Factors:
        - Confidence of both beliefs (high confidence = important to resolve)
        - Number of sources (more sources = more important)
        - Severity of contradiction
        """
        # Average confidence of both beliefs
        avg_confidence = (self.belief_a.confidence + self.belief_b.confidence) / 2

        # Source multiplier (more sources = more important)
        source_count = len(self.belief_a.source_ids) + len(self.belief_b.source_ids)
        source_factor = min(source_count / 10, 1.0)  # Cap at 1.0

        # Severity multiplier
        severity_weights = {
            ContradictionSeverity.TRIVIAL: 0.2,
            ContradictionSeverity.MODERATE: 0.5,
            ContradictionSeverity.SEVERE: 0.8,
            ContradictionSeverity.CRITICAL: 1.0,
        }
        severity_factor = severity_weights[self.severity]

        # Combine factors
        importance = avg_confidence * 0.4 + source_factor * 0.3 + severity_factor * 0.3

        return min(importance, 1.0)

    def suggest_resolution_strategy(self) -> str:
        """Suggest how to investigate this contradiction"""
        if self.contradiction_type == ContradictionType.TEMPORAL_CONFLICT:
            return "Check if both were true at different times. Query historical sources."

        elif self.contradiction_type == ContradictionType.METHODOLOGICAL:
            return "Compare methodologies. Look for meta-analyses or systematic reviews."

        elif self.contradiction_type == ContradictionType.INCOMPATIBLE_VALUES:
            return "Check if measurements/definitions differ. Look for authoritative sources."

        elif self.contradiction_type == ContradictionType.CAUSAL_CONFLICT:
            return "Look for causal chain analysis. Multiple causes may be valid."

        else:
            return "Investigate source credibility. Look for consensus in authoritative sources."

    def generate_research_questions(self) -> list[str]:
        """Generate research questions to resolve this contradiction"""
        questions = []

        # Why do sources disagree?
        questions.append(
            f"Why do sources disagree about {self.belief_a.claim.subject}?"
        )

        # Which is more credible?
        questions.append(
            f"Which sources are more authoritative on {self.belief_a.claim.subject}?"
        )

        # Is this a temporal issue?
        questions.append(
            f"Has {self.belief_a.claim.subject} changed over time?"
        )

        # Are there meta-analyses?
        questions.append(
            f"What do systematic reviews say about {self.belief_a.claim.subject}?"
        )

        return questions

    def resolve(self, explanation: str, winning_belief: Optional[Belief] = None):
        """Mark this contradiction as resolved"""
        self.is_resolved = True
        self.resolution_explanation = explanation
        self.resolved_at = datetime.now()

        # If one belief wins, lower confidence of the other
        if winning_belief:
            if winning_belief == self.belief_a:
                self.belief_b.confidence *= 0.5  # Reduce losing belief
            else:
                self.belief_a.confidence *= 0.5

    def __str__(self) -> str:
        return self.get_disagreement_summary()

    def __repr__(self) -> str:
        return (
            f"Contradiction({self.contradiction_id[:8]}..."
            f":{self.contradiction_type.value}"
            f":importance={self.importance_score:.2f})"
        )


class ContradictionDetector:
    """Detects contradictions between beliefs"""

    @staticmethod
    def detect(belief_a: Belief, belief_b: Belief) -> Optional[Contradiction]:
        """Detect if two beliefs contradict each other"""

        # Check if claims contradict
        if not belief_a.claim.contradicts(belief_b.claim):
            return None

        # Determine type and severity
        contradiction_type = ContradictionDetector._classify_type(belief_a, belief_b)
        severity = ContradictionDetector._assess_severity(belief_a, belief_b)

        contradiction = Contradiction(
            belief_a=belief_a,
            belief_b=belief_b,
            contradiction_type=contradiction_type,
            severity=severity
        )

        # Compute importance
        contradiction.importance_score = contradiction.compute_importance()

        return contradiction

    @staticmethod
    def _classify_type(belief_a: Belief, belief_b: Belief) -> ContradictionType:
        """Classify the type of contradiction"""
        claim_a = belief_a.claim
        claim_b = belief_b.claim

        # Check if same predicate but different objects
        if claim_a.predicate == claim_b.predicate:
            if claim_a.claim_type == claim_b.claim_type:
                return ContradictionType.INCOMPATIBLE_VALUES
            else:
                return ContradictionType.METHODOLOGICAL

        # Check temporal conflict
        if (belief_a.valid_to and belief_b.valid_from and
            belief_a.valid_to > belief_b.valid_from):
            return ContradictionType.TEMPORAL_CONFLICT

        # Default
        return ContradictionType.DIRECT_NEGATION

    @staticmethod
    def _assess_severity(belief_a: Belief, belief_b: Belief) -> ContradictionSeverity:
        """Assess how severe the contradiction is"""

        # If both have high confidence, it's severe
        avg_confidence = (belief_a.confidence + belief_b.confidence) / 2
        if avg_confidence > 0.8:
            return ContradictionSeverity.SEVERE

        # If both have many sources, it's critical
        source_count = len(belief_a.source_ids) + len(belief_b.source_ids)
        if source_count > 10:
            return ContradictionSeverity.CRITICAL

        # If confidences are low, might be trivial
        if avg_confidence < 0.3:
            return ContradictionSeverity.TRIVIAL

        # Default
        return ContradictionSeverity.MODERATE
