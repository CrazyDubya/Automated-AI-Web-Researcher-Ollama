"""
Consensus Engine - Computing truth from disagreement

When sources disagree, how do we determine what to believe?

ResearchOS treats research as a distributed consensus problem:
- Each source is a node with its own "worldview"
- Sources have different credibility scores
- We compute probabilistic consensus using belief aggregation

This is Byzantine Fault Tolerance applied to epistemology.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import math

from .belief import Belief, BeliefDistribution, Claim


class ConsensusStrategy:
    """Base class for consensus strategies"""

    def compute(self, beliefs: List[Belief]) -> BeliefDistribution:
        """Compute consensus from a list of beliefs"""
        raise NotImplementedError


@dataclass
class SourceCredibility:
    """Track credibility of a source"""
    source_id: str
    credibility: float = 0.5  # 0.0 = not credible, 1.0 = fully credible
    track_record: int = 0  # How many claims from this source
    correct_count: int = 0  # How many were later confirmed
    incorrect_count: int = 0  # How many were later contradicted

    @property
    def accuracy(self) -> float:
        """Historical accuracy rate"""
        if self.track_record == 0:
            return 0.5
        return self.correct_count / self.track_record

    def update_credibility(self):
        """Recompute credibility based on track record"""
        if self.track_record > 0:
            # Weighted average of prior and observed accuracy
            prior_weight = 0.3
            observed_weight = 0.7
            self.credibility = (
                prior_weight * self.credibility +
                observed_weight * self.accuracy
            )


class WeightedVoting(ConsensusStrategy):
    """
    Weighted voting consensus strategy.

    Each source votes with weight = credibility * confidence
    """

    def __init__(self, source_credibility: Dict[str, SourceCredibility] = None):
        self.source_credibility = source_credibility or {}

    def compute(self, beliefs: List[Belief]) -> Dict[str, float]:
        """
        Compute weighted votes for each unique claim.

        Returns: Dict[claim_id -> aggregated_confidence]
        """

        if not beliefs:
            return {}

        # Group beliefs by claim
        claims_votes: Dict[str, List[Tuple[Belief, float]]] = {}

        for belief in beliefs:
            claim_id = belief.claim.claim_id

            # Get source credibility
            source_weights = []
            for source_id in belief.source_ids:
                if source_id in self.source_credibility:
                    credibility = self.source_credibility[source_id].credibility
                else:
                    credibility = 0.5  # Default

                source_weights.append(credibility)

            # Average source credibility
            avg_credibility = sum(source_weights) / len(source_weights) if source_weights else 0.5

            # Vote weight = credibility * confidence
            vote_weight = avg_credibility * belief.confidence

            if claim_id not in claims_votes:
                claims_votes[claim_id] = []

            claims_votes[claim_id].append((belief, vote_weight))

        # Aggregate votes for each claim
        claim_confidences = {}
        for claim_id, votes in claims_votes.items():
            # Sum of all votes
            total_vote = sum(weight for _, weight in votes)

            # Normalize by number of voters (avoid runaway confidence)
            num_voters = len(votes)
            normalized_confidence = total_vote / num_voters if num_voters > 0 else 0

            # Cap at 1.0
            claim_confidences[claim_id] = min(normalized_confidence, 1.0)

        return claim_confidences


class BayesianAggregation(ConsensusStrategy):
    """
    Bayesian belief aggregation.

    Treats each source as providing evidence, updates posterior probability.
    """

    def __init__(self, prior: float = 0.5):
        self.prior = prior  # Prior probability

    def compute(self, beliefs: List[Belief]) -> Dict[str, float]:
        """
        Compute Bayesian aggregation.

        For each claim, treat each source as providing evidence.
        Update posterior using Bayes' theorem.
        """

        if not beliefs:
            return {}

        # Group by claim
        claims_evidence: Dict[str, List[float]] = {}

        for belief in beliefs:
            claim_id = belief.claim.claim_id

            if claim_id not in claims_evidence:
                claims_evidence[claim_id] = []

            # Treat confidence as likelihood ratio
            claims_evidence[claim_id].append(belief.confidence)

        # Compute posterior for each claim
        claim_confidences = {}

        for claim_id, evidence_list in claims_evidence.items():
            # Start with prior
            posterior = self.prior

            # Update with each piece of evidence
            for likelihood in evidence_list:
                # Bayesian update
                # P(H|E) = P(E|H) * P(H) / P(E)
                # Simplified: use likelihood as evidence weight

                # Odds form is easier to work with
                prior_odds = posterior / (1 - posterior) if posterior < 1 else 999
                likelihood_ratio = likelihood / (1 - likelihood) if likelihood < 1 and likelihood > 0 else 1

                posterior_odds = prior_odds * likelihood_ratio
                posterior = posterior_odds / (1 + posterior_odds)

            claim_confidences[claim_id] = min(posterior, 1.0)

        return claim_confidences


class ConsensusEngine:
    """
    Main consensus engine.

    Aggregates beliefs from multiple sources to compute consensus.
    """

    def __init__(self, strategy: Optional[ConsensusStrategy] = None):
        self.strategy = strategy or WeightedVoting()
        self.source_credibility: Dict[str, SourceCredibility] = {}

    def compute_consensus(self, beliefs: List[Belief]) -> BeliefDistribution:
        """
        Compute consensus from a list of beliefs.

        Returns a BeliefDistribution with aggregated confidences.
        """

        if not beliefs:
            return BeliefDistribution(
                question="",
                beliefs=[],
                sources_consulted=0
            )

        # Compute consensus scores
        claim_scores = self.strategy.compute(beliefs)

        # Create new beliefs with consensus confidences
        consensus_beliefs = []

        # Group beliefs by claim
        claims_to_beliefs: Dict[str, List[Belief]] = {}
        for belief in beliefs:
            cid = belief.claim.claim_id
            if cid not in claims_to_beliefs:
                claims_to_beliefs[cid] = []
            claims_to_beliefs[cid].append(belief)

        # For each unique claim, create a consensus belief
        for claim_id, claim_beliefs in claims_to_beliefs.items():
            if claim_id in claim_scores:
                # Take the first belief as template
                template = claim_beliefs[0]

                # Collect all sources
                all_sources = set()
                for b in claim_beliefs:
                    all_sources.update(b.source_ids)

                # Create consensus belief
                consensus_belief = Belief(
                    claim=template.claim,
                    confidence=claim_scores[claim_id],
                    valid_from=min(b.valid_from for b in claim_beliefs),
                    valid_to=None,  # Consensus is current
                    source_ids=list(all_sources),
                    extraction_method="consensus_aggregation"
                )

                consensus_beliefs.append(consensus_belief)

        # Count sources
        all_source_ids = set()
        for b in beliefs:
            all_source_ids.update(b.source_ids)

        return BeliefDistribution(
            question="",
            beliefs=consensus_beliefs,
            sources_consulted=len(all_source_ids)
        )

    def update_source_credibility(
        self,
        source_id: str,
        was_correct: bool
    ):
        """Update source credibility based on new evidence"""

        if source_id not in self.source_credibility:
            self.source_credibility[source_id] = SourceCredibility(source_id=source_id)

        cred = self.source_credibility[source_id]
        cred.track_record += 1

        if was_correct:
            cred.correct_count += 1
        else:
            cred.incorrect_count += 1

        cred.update_credibility()

    def get_source_credibility(self, source_id: str) -> float:
        """Get current credibility for a source"""
        if source_id in self.source_credibility:
            return self.source_credibility[source_id].credibility
        return 0.5  # Default

    def detect_outliers(self, beliefs: List[Belief]) -> List[Belief]:
        """
        Detect beliefs that are outliers (disagree with consensus).

        These might indicate:
        - Unreliable sources
        - Novel/minority perspectives worth investigating
        - Errors in extraction
        """

        if len(beliefs) < 3:
            return []  # Need at least 3 beliefs to detect outliers

        # Compute consensus
        consensus = self.compute_consensus(beliefs)

        if not consensus.beliefs:
            return []

        # Get consensus claim
        consensus_claim_id = consensus.consensus_belief.claim.claim_id if consensus.consensus_belief else None

        # Find beliefs that disagree with consensus
        outliers = []
        for belief in beliefs:
            if belief.claim.claim_id != consensus_claim_id:
                # This belief claims something different
                outliers.append(belief)

        return outliers

    def compute_agreement_score(self, beliefs: List[Belief]) -> float:
        """
        Compute how much agreement there is among beliefs.

        Returns 0.0 (total disagreement) to 1.0 (perfect agreement)
        """

        if len(beliefs) <= 1:
            return 1.0  # Trivial agreement

        # Group by claim
        claim_counts: Dict[str, int] = {}
        for belief in beliefs:
            cid = belief.claim.claim_id
            claim_counts[cid] = claim_counts.get(cid, 0) + 1

        # Compute Herfindahl index (concentration)
        total = len(beliefs)
        herfindahl = sum((count / total) ** 2 for count in claim_counts.values())

        return herfindahl

    def explain_consensus(self, beliefs: List[Belief]) -> str:
        """Generate human-readable explanation of consensus"""

        if not beliefs:
            return "No beliefs to aggregate."

        consensus = self.compute_consensus(beliefs)
        agreement = self.compute_agreement_score(beliefs)

        explanation = f"Consensus Analysis ({len(beliefs)} beliefs from {consensus.sources_consulted} sources):\n\n"

        if consensus.consensus_belief:
            explanation += f"Consensus: {consensus.consensus_belief.claim}\n"
            explanation += f"Confidence: {consensus.consensus_belief.confidence:.2%}\n"
            explanation += f"Agreement: {agreement:.2%}\n\n"

        if agreement < 0.5:
            explanation += "⚠️  LOW AGREEMENT - Sources significantly disagree\n\n"

        # Show breakdown
        explanation += "Belief Breakdown:\n"
        for i, belief in enumerate(sorted(consensus.beliefs, key=lambda b: b.confidence, reverse=True), 1):
            explanation += f"  {i}. [{belief.confidence:.2%}] {belief.claim}\n"
            explanation += f"     Sources: {len(belief.source_ids)}\n"

        return explanation

    def __repr__(self) -> str:
        return f"ConsensusEngine(strategy={self.strategy.__class__.__name__}, sources_tracked={len(self.source_credibility)})"
