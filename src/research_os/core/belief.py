"""
Belief System - Core data structures for probabilistic knowledge representation

The fundamental insight: We don't store FACTS, we store BELIEFS.
Every piece of knowledge has:
- A claim (what is asserted)
- A confidence (how certain we are)
- A provenance (where it came from)
- A temporal validity (when it was/is true)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any
from enum import Enum
import hashlib
import json


class ClaimType(Enum):
    """Types of claims that can be made"""
    FACTUAL = "factual"  # "X is Y"
    RELATIONAL = "relational"  # "X relates to Y"
    TEMPORAL = "temporal"  # "X happened at time T"
    CAUSAL = "causal"  # "X caused Y"
    STATISTICAL = "statistical"  # "X% of Y"
    QUALITATIVE = "qualitative"  # "X is good/bad/important"


@dataclass(frozen=True)
class Claim:
    """
    A claim is an assertion about the world.
    It's immutable - claims don't change, but our beliefs about them do.
    """

    subject: str  # What the claim is about
    predicate: str  # What we're asserting
    object: Any  # The value/target
    claim_type: ClaimType = ClaimType.FACTUAL

    # Optional structured data
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        # Make metadata frozen
        object.__setattr__(self, 'metadata', dict(self.metadata))

    @property
    def claim_id(self) -> str:
        """Unique identifier for this claim"""
        claim_str = f"{self.subject}::{self.predicate}::{self.object}::{self.claim_type.value}"
        return hashlib.sha256(claim_str.encode()).hexdigest()[:16]

    def contradicts(self, other: 'Claim') -> bool:
        """Check if this claim contradicts another"""
        # Same subject and predicate but different object
        if self.subject == other.subject and self.predicate == other.predicate:
            if self.claim_type == ClaimType.FACTUAL:
                return self.object != other.object
            # More sophisticated contradiction detection can be added
        return False

    def to_natural_language(self) -> str:
        """Convert claim to human-readable form"""
        if self.claim_type == ClaimType.FACTUAL:
            return f"{self.subject} {self.predicate} {self.object}"
        elif self.claim_type == ClaimType.RELATIONAL:
            return f"{self.subject} {self.predicate} {self.object}"
        elif self.claim_type == ClaimType.TEMPORAL:
            return f"{self.subject} {self.predicate} at {self.object}"
        elif self.claim_type == ClaimType.CAUSAL:
            return f"{self.subject} caused {self.object}"
        elif self.claim_type == ClaimType.STATISTICAL:
            return f"{self.object}% of {self.subject} {self.predicate}"
        else:
            return f"{self.subject} {self.predicate} {self.object}"

    def __str__(self) -> str:
        return self.to_natural_language()

    def __repr__(self) -> str:
        return f"Claim({self.claim_id[:8]}...:{self.to_natural_language()})"


@dataclass
class Belief:
    """
    A belief is our confidence in a claim at a point in time from a source.

    This is the fundamental unit of knowledge in ResearchOS.
    Unlike traditional databases that store facts, we store beliefs with:
    - Temporal validity (when is this true?)
    - Confidence scores (how certain are we?)
    - Provenance (where did we learn this?)
    """

    claim: Claim
    confidence: float  # 0.0 to 1.0

    # Temporal validity
    valid_from: datetime
    valid_to: Optional[datetime] = None  # None means "still valid"

    # Provenance
    source_ids: list[str] = field(default_factory=list)
    derived_from: list[str] = field(default_factory=list)  # Other belief IDs

    # Transaction time (when we learned this, different from valid_from)
    learned_at: datetime = field(default_factory=datetime.now)

    # Metadata
    extraction_method: Optional[str] = None
    tags: list[str] = field(default_factory=list)

    @property
    def belief_id(self) -> str:
        """Unique identifier for this specific belief"""
        belief_str = (
            f"{self.claim.claim_id}::"
            f"{self.valid_from.isoformat()}::"
            f"{self.learned_at.isoformat()}"
        )
        return hashlib.sha256(belief_str.encode()).hexdigest()[:16]

    def is_valid_at(self, timestamp: datetime) -> bool:
        """Check if this belief was valid at a given time"""
        if timestamp < self.valid_from:
            return False
        if self.valid_to and timestamp > self.valid_to:
            return False
        return True

    def is_current(self, as_of: Optional[datetime] = None) -> bool:
        """Check if this belief is currently valid"""
        if as_of is None:
            as_of = datetime.now()
        return self.is_valid_at(as_of)

    def supersede(self, new_belief: 'Belief') -> 'Belief':
        """Create a new belief that supersedes this one"""
        # Close the validity window of current belief
        self.valid_to = new_belief.valid_from
        return new_belief

    def __str__(self) -> str:
        valid_str = f"from {self.valid_from.date()}"
        if self.valid_to:
            valid_str += f" to {self.valid_to.date()}"
        else:
            valid_str += " to present"

        return (
            f"[{self.confidence:.2f}] {self.claim} "
            f"({valid_str})"
        )

    def __repr__(self) -> str:
        return f"Belief({self.belief_id[:8]}...:{self.confidence:.2f}:{self.claim})"


@dataclass
class BeliefDistribution:
    """
    A probability distribution over multiple beliefs about the same subject.

    This is what queries return - not a single answer, but a distribution
    showing what we believe and with what confidence.
    """

    question: str
    beliefs: list[Belief]

    # Consensus metrics
    total_confidence: float = 0.0
    entropy: float = 0.0  # Higher = more disagreement

    # Metadata
    queried_at: datetime = field(default_factory=datetime.now)
    sources_consulted: int = 0

    def __post_init__(self):
        """Compute distribution metrics"""
        self.total_confidence = sum(b.confidence for b in self.beliefs)

        # Normalize confidences to probabilities
        if self.total_confidence > 0:
            probs = [b.confidence / self.total_confidence for b in self.beliefs]
            # Compute Shannon entropy
            import math
            self.entropy = -sum(p * math.log2(p) if p > 0 else 0 for p in probs)

    @property
    def consensus_belief(self) -> Optional[Belief]:
        """Return the highest confidence belief"""
        if not self.beliefs:
            return None
        return max(self.beliefs, key=lambda b: b.confidence)

    def has_consensus(self, threshold: float = 0.7) -> bool:
        """Check if there's strong consensus (one belief > threshold)"""
        if not self.beliefs:
            return False
        max_conf = max(b.confidence for b in self.beliefs)
        return max_conf >= threshold

    def get_contradictions(self) -> list[tuple[Belief, Belief]]:
        """Find contradicting beliefs in the distribution"""
        contradictions = []
        for i, b1 in enumerate(self.beliefs):
            for b2 in self.beliefs[i+1:]:
                if b1.claim.contradicts(b2.claim):
                    contradictions.append((b1, b2))
        return contradictions

    def to_summary(self) -> str:
        """Human-readable summary of the distribution"""
        if not self.beliefs:
            return f"No beliefs found for: {self.question}"

        summary = f"Question: {self.question}\n"
        summary += f"Sources consulted: {self.sources_consulted}\n"
        summary += f"Consensus: {'Yes' if self.has_consensus() else 'No'} (entropy: {self.entropy:.2f})\n\n"

        summary += "Beliefs:\n"
        for b in sorted(self.beliefs, key=lambda x: x.confidence, reverse=True):
            summary += f"  • [{b.confidence:.2%}] {b.claim}\n"
            summary += f"    Sources: {len(b.source_ids)} | Valid: "
            if b.valid_to:
                summary += f"{b.valid_from.date()} to {b.valid_to.date()}\n"
            else:
                summary += f"{b.valid_from.date()} to present\n"

        contradictions = self.get_contradictions()
        if contradictions:
            summary += f"\n⚠️  {len(contradictions)} contradiction(s) detected\n"

        return summary

    def __str__(self) -> str:
        return self.to_summary()

    def __repr__(self) -> str:
        return f"BeliefDistribution(n={len(self.beliefs)}, entropy={self.entropy:.2f})"
