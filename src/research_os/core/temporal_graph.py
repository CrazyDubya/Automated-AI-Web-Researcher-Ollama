"""
Temporal Belief Graph - The heart of ResearchOS

This is simultaneously:
- A knowledge graph (entities and relationships)
- A temporal database (facts with validity periods)
- A belief network (probabilistic, not factual)
- A version control system (full history)

Every fact has:
- Valid time (when was it true in the world?)
- Transaction time (when did we learn it?)
- Confidence (how certain are we?)
- Provenance (where did we learn it?)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Set, Dict
from collections import defaultdict

from .belief import Belief, Claim, BeliefDistribution, ClaimType
from .provenance import ProvenanceDAG, Source, ProvenanceType
from .contradiction import Contradiction, ContradictionDetector
from .frontier import KnowledgeFrontier, ResearchDebt, FailureReason


class TemporalBeliefGraph:
    """
    The core data structure of ResearchOS.

    This graph stores ALL knowledge with:
    - Temporal versioning (when was it true?)
    - Provenance tracking (how do we know?)
    - Contradiction detection (what conflicts?)
    - Frontier tracking (what don't we know?)
    """

    def __init__(self):
        # Core storage
        self.beliefs: Dict[str, Belief] = {}  # belief_id -> Belief

        # Temporal index: subject -> [beliefs about that subject]
        self._subject_index: Dict[str, List[str]] = defaultdict(list)

        # Supporting structures
        self.provenance: ProvenanceDAG = ProvenanceDAG()
        self.contradictions: List[Contradiction] = []
        self.frontier: KnowledgeFrontier = KnowledgeFrontier()

        # Statistics
        self._stats = {
            "beliefs_added": 0,
            "contradictions_detected": 0,
            "debts_accumulated": 0
        }

    def add_source(self, source: Source):
        """Register a source in the provenance graph"""
        self.provenance.add_source(source)

    def add_belief(
        self,
        claim: Claim,
        source: Source,
        confidence: float,
        valid_from: Optional[datetime] = None,
        extraction_method: Optional[str] = None
    ) -> Belief:
        """
        Add a belief to the graph.

        This is the PRIMARY OPERATION of ResearchOS.
        Every time we learn something, we add a belief.
        """

        if valid_from is None:
            valid_from = datetime.now()

        # Create the belief
        belief = Belief(
            claim=claim,
            confidence=confidence,
            valid_from=valid_from,
            source_ids=[source.source_id],
            extraction_method=extraction_method
        )

        # Store it
        self.beliefs[belief.belief_id] = belief
        self._subject_index[claim.subject].append(belief.belief_id)

        # Add provenance
        self.provenance.add_node(
            artifact_id=belief.belief_id,
            artifact_type="belief",
            operation=ProvenanceType.ACQUIRED,
            source_ids={source.source_id},
            method=extraction_method,
            confidence=confidence
        )

        # Check for contradictions
        self._detect_contradictions(belief)

        # Update stats
        self._stats["beliefs_added"] += 1

        return belief

    def add_derived_belief(
        self,
        claim: Claim,
        confidence: float,
        derived_from: List[str],  # belief_ids this is derived from
        method: str,
        valid_from: Optional[datetime] = None
    ) -> Belief:
        """
        Add a belief derived from other beliefs (inference, synthesis, etc.)
        """

        if valid_from is None:
            valid_from = datetime.now()

        # Collect sources from parent beliefs
        source_ids = set()
        for belief_id in derived_from:
            if belief_id in self.beliefs:
                source_ids.update(self.beliefs[belief_id].source_ids)

        belief = Belief(
            claim=claim,
            confidence=confidence,
            valid_from=valid_from,
            source_ids=list(source_ids),
            derived_from=derived_from,
            extraction_method=method
        )

        self.beliefs[belief.belief_id] = belief
        self._subject_index[claim.subject].append(belief.belief_id)

        # Add provenance
        self.provenance.add_node(
            artifact_id=belief.belief_id,
            artifact_type="belief",
            operation=ProvenanceType.INFERRED,
            derived_from=derived_from,
            source_ids=source_ids,
            method=method,
            confidence=confidence
        )

        # Check for contradictions
        self._detect_contradictions(belief)

        self._stats["beliefs_added"] += 1

        return belief

    def query(
        self,
        question: str,
        subject: Optional[str] = None,
        as_of: Optional[datetime] = None,
        min_confidence: float = 0.0
    ) -> BeliefDistribution:
        """
        Query the belief graph.

        Returns a DISTRIBUTION of beliefs, not a single answer.
        This captures uncertainty and disagreement.
        """

        if as_of is None:
            as_of = datetime.now()

        # Find relevant beliefs
        relevant_beliefs = []

        if subject:
            # Direct subject lookup
            belief_ids = self._subject_index.get(subject, [])
            for bid in belief_ids:
                belief = self.beliefs[bid]
                if belief.is_valid_at(as_of) and belief.confidence >= min_confidence:
                    relevant_beliefs.append(belief)
        else:
            # Full scan (can be optimized with better indexing)
            for belief in self.beliefs.values():
                if belief.is_valid_at(as_of) and belief.confidence >= min_confidence:
                    # Simple relevance check (can be made more sophisticated)
                    if self._is_relevant(belief, question):
                        relevant_beliefs.append(belief)

        # Count unique sources
        all_sources = set()
        for b in relevant_beliefs:
            all_sources.update(b.source_ids)

        return BeliefDistribution(
            question=question,
            beliefs=relevant_beliefs,
            sources_consulted=len(all_sources)
        )

    def query_temporal(
        self,
        subject: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[Belief]:
        """Query beliefs within a time range"""

        belief_ids = self._subject_index.get(subject, [])
        temporal_beliefs = []

        for bid in belief_ids:
            belief = self.beliefs[bid]
            # Check if belief's validity overlaps with query range
            if belief.valid_from <= end_time and (belief.valid_to is None or belief.valid_to >= start_time):
                temporal_beliefs.append(belief)

        return sorted(temporal_beliefs, key=lambda b: b.valid_from)

    def counterfactual_query(
        self,
        question: str,
        exclude_sources: List[str]
    ) -> BeliefDistribution:
        """
        Answer: "What would we believe if we excluded these sources?"

        This uses provenance pruning to recompute beliefs.
        """

        # Get normal query result
        normal_result = self.query(question)

        # Filter out beliefs that depend on excluded sources
        filtered_beliefs = []
        for belief in normal_result.beliefs:
            # Check if belief depends on excluded sources
            depends_on_excluded = False
            for source_id in belief.source_ids:
                if source_id in exclude_sources:
                    depends_on_excluded = True
                    break

            if not depends_on_excluded:
                filtered_beliefs.append(belief)

        # Recompute confidence (might need normalization)
        return BeliefDistribution(
            question=f"{question} (excluding {len(exclude_sources)} sources)",
            beliefs=filtered_beliefs,
            sources_consulted=len(set(sid for b in filtered_beliefs for sid in b.source_ids))
        )

    def get_contradictions(
        self,
        unresolved_only: bool = True,
        min_importance: float = 0.0
    ) -> List[Contradiction]:
        """Get contradictions in the graph"""

        filtered = []
        for c in self.contradictions:
            if unresolved_only and c.is_resolved:
                continue
            if c.importance_score < min_importance:
                continue
            filtered.append(c)

        return sorted(filtered, key=lambda c: c.importance_score, reverse=True)

    def get_provenance_chain(self, belief_id: str):
        """Get the full provenance chain for a belief"""
        return self.provenance.get_chain(belief_id)

    def record_research_debt(
        self,
        question: str,
        attempted_sources: List[str],
        failure_reason: FailureReason,
        importance: float = 0.5
    ):
        """Record a failed research attempt"""
        debt = self.frontier.add_debt(
            question=question,
            attempted_sources=attempted_sources,
            failure_reason=failure_reason,
            importance=importance
        )
        self._stats["debts_accumulated"] += 1
        return debt

    def get_evolution(self, subject: str) -> List[Belief]:
        """Get the evolution of beliefs about a subject over time"""
        return self.query_temporal(
            subject=subject,
            start_time=datetime(1900, 1, 1),
            end_time=datetime.now()
        )

    def _detect_contradictions(self, new_belief: Belief):
        """Check if a new belief contradicts existing beliefs"""

        # Get other beliefs about the same subject
        subject_belief_ids = self._subject_index[new_belief.claim.subject]

        for bid in subject_belief_ids:
            if bid == new_belief.belief_id:
                continue

            existing_belief = self.beliefs[bid]

            # Check temporal overlap
            if not self._temporal_overlap(new_belief, existing_belief):
                continue  # No conflict if they're valid at different times

            # Check for contradiction
            contradiction = ContradictionDetector.detect(new_belief, existing_belief)

            if contradiction:
                self.contradictions.append(contradiction)
                self._stats["contradictions_detected"] += 1

    def _temporal_overlap(self, belief_a: Belief, belief_b: Belief) -> bool:
        """Check if two beliefs have overlapping validity periods"""
        # If either has no end, they overlap if start times overlap
        if belief_a.valid_to is None or belief_b.valid_to is None:
            return True

        # Check if ranges overlap
        return (belief_a.valid_from <= belief_b.valid_to and
                belief_b.valid_from <= belief_a.valid_to)

    def _is_relevant(self, belief: Belief, question: str) -> bool:
        """Simple relevance check (can be made much more sophisticated)"""
        question_lower = question.lower()
        claim_text = belief.claim.to_natural_language().lower()

        # Simple keyword matching for now
        return any(word in claim_text for word in question_lower.split() if len(word) > 3)

    def get_stats(self) -> dict:
        """Get graph statistics"""
        return {
            **self._stats,
            "total_beliefs": len(self.beliefs),
            "total_sources": len(self.provenance.sources),
            "total_contradictions": len(self.contradictions),
            "unresolved_contradictions": len([c for c in self.contradictions if not c.is_resolved]),
            "research_debts": len(self.frontier.research_debts),
            "knowledge_gaps": len(self.frontier.knowledge_gaps)
        }

    def to_summary(self) -> str:
        """Human-readable summary of the graph"""
        stats = self.get_stats()

        summary = "=== Temporal Belief Graph Summary ===\n\n"
        summary += f"Beliefs: {stats['total_beliefs']}\n"
        summary += f"Sources: {stats['total_sources']}\n"
        summary += f"Contradictions: {stats['total_contradictions']} ({stats['unresolved_contradictions']} unresolved)\n"
        summary += f"Research Debts: {stats['research_debts']}\n"
        summary += f"Knowledge Gaps: {stats['knowledge_gaps']}\n"

        return summary

    def __len__(self) -> int:
        return len(self.beliefs)

    def __repr__(self) -> str:
        stats = self.get_stats()
        return f"TemporalBeliefGraph(beliefs={stats['total_beliefs']}, sources={stats['total_sources']})"
