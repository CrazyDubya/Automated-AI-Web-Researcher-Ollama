"""
ResearchOS - The Operating System for Knowledge Acquisition

This is the main kernel that orchestrates:
- Temporal Belief Graph (knowledge storage)
- Provenance DAG (lineage tracking)
- Consensus Engine (belief aggregation)
- Multi-Agent Research (collaborative investigation)
- Knowledge Frontier (gap tracking)

ResearchOS treats research as:
- A distributed consensus problem (sources may disagree)
- A temporal problem (truth changes over time)
- A provenance problem (we need to know HOW we know)
- A collaborative problem (multiple perspectives yield better results)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any

from ..core.temporal_graph import TemporalBeliefGraph
from ..core.belief import Belief, Claim, BeliefDistribution, ClaimType
from ..core.provenance import Source, ProvenanceType
from ..core.consensus import ConsensusEngine
from ..core.contradiction import Contradiction
from ..core.frontier import KnowledgeFrontier, FailureReason
from ..agents.research_committee import ResearchCommittee, DebateTranscript
from ..agents.base_agent import ResearchFinding


@dataclass
class ResearchResult:
    """
    The result of a research operation.

    This is what users get back - not just an answer, but:
    - The answer with confidence
    - All evidence found
    - Contradictions detected
    - Research debt accumulated
    - Suggested follow-up questions
    - Full provenance chain
    """

    question: str
    answer: Optional[BeliefDistribution] = None

    # Evidence
    evidence: List[ResearchFinding] = field(default_factory=list)
    sources_consulted: int = 0

    # Quality metrics
    confidence: float = 0.0
    consensus: bool = False

    # Issues
    contradictions: List[Contradiction] = field(default_factory=list)
    research_debt: List[Any] = field(default_factory=list)  # ResearchDebt objects

    # Provenance
    provenance_chain: Optional[Any] = None  # ProvenanceChain

    # Suggestions
    suggested_follow_ups: List[str] = field(default_factory=list)

    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    debate_transcript: Optional[DebateTranscript] = None

    def to_summary(self) -> str:
        """Human-readable summary"""

        summary = f"=== Research Result ===\n\n"
        summary += f"Question: {self.question}\n"
        summary += f"Timestamp: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        if self.answer and self.answer.consensus_belief:
            summary += f"Answer: {self.answer.consensus_belief.claim}\n"
            summary += f"Confidence: {self.confidence:.2%}\n"
            summary += f"Consensus: {'Yes' if self.consensus else 'No'}\n\n"
        else:
            summary += f"Answer: Unable to reach conclusion\n\n"

        summary += f"Sources Consulted: {self.sources_consulted}\n"
        summary += f"Evidence Pieces: {len(self.evidence)}\n\n"

        if self.contradictions:
            summary += f"⚠️  Contradictions: {len(self.contradictions)}\n"
            for i, contr in enumerate(self.contradictions[:3], 1):
                summary += f"  {i}. {contr.contradiction_type.value}\n"
            if len(self.contradictions) > 3:
                summary += f"  ... and {len(self.contradictions) - 3} more\n"
            summary += "\n"

        if self.research_debt:
            summary += f"📊 Research Debt: {len(self.research_debt)} item(s)\n"
            for debt in self.research_debt[:2]:
                summary += f"  • {debt.failure_reason.value}: {debt.question[:60]}...\n"
            summary += "\n"

        if self.suggested_follow_ups:
            summary += f"💡 Suggested Follow-ups:\n"
            for i, followup in enumerate(self.suggested_follow_ups[:3], 1):
                summary += f"  {i}. {followup}\n"
            summary += "\n"

        if self.debate_transcript:
            summary += f"\n--- Committee Debate Summary ---\n"
            summary += f"Rounds: {self.debate_transcript.rounds}\n"
            summary += f"Findings: {len(self.debate_transcript.findings)}\n"
            summary += f"Arguments: {len(self.debate_transcript.arguments)}\n"

        return summary

    def __str__(self) -> str:
        return self.to_summary()


class ResearchOS:
    """
    The main ResearchOS kernel.

    This is the interface that users interact with.
    It orchestrates all the underlying systems.
    """

    def __init__(self):
        # Core systems
        self.graph = TemporalBeliefGraph()
        self.consensus_engine = ConsensusEngine()

        # Statistics
        self.stats = {
            "queries": 0,
            "beliefs_added": 0,
            "contradictions_found": 0,
            "committees_convened": 0
        }

    def research(
        self,
        question: str,
        use_committee: bool = True,
        context: Optional[Dict[str, Any]] = None
    ) -> ResearchResult:
        """
        The main research operation.

        This is the spectacular part - it orchestrates:
        1. Multi-agent committee deliberation
        2. Belief graph updates
        3. Contradiction detection
        4. Provenance tracking
        5. Frontier updates
        """

        self.stats["queries"] += 1

        result = ResearchResult(question=question)

        if use_committee:
            # Convene a research committee
            committee = ResearchCommittee(question=question)
            transcript = committee.deliberate(context)

            self.stats["committees_convened"] += 1

            result.debate_transcript = transcript
            result.evidence = transcript.findings

            # Add findings to belief graph
            for finding in transcript.findings:
                # Convert finding to belief
                claim = Claim(
                    subject=question,
                    predicate="answer_is",
                    object=finding.claim,
                    claim_type=ClaimType.FACTUAL
                )

                # Create a dummy source for the finding
                # In real implementation, findings would have actual sources
                source = Source(
                    source_id=f"agent_{finding.agent_role.value}",
                    uri=f"internal://agent/{finding.agent_role.value}",
                    source_type="agent"
                )

                self.graph.add_source(source)

                belief = self.graph.add_belief(
                    claim=claim,
                    source=source,
                    confidence=finding.confidence,
                    extraction_method=f"committee_research_{finding.agent_role.value}"
                )

                self.stats["beliefs_added"] += 1

            # Get consensus from committee
            if transcript.consensus_finding:
                result.confidence = transcript.confidence
                result.consensus = transcript.consensus_reached

        # Query the belief graph
        answer = self.graph.query(question)
        result.answer = answer

        # Count sources
        all_sources = set()
        if answer.beliefs:
            for belief in answer.beliefs:
                all_sources.update(belief.source_ids)
        result.sources_consulted = len(all_sources)

        # Get contradictions
        result.contradictions = self.graph.get_contradictions(
            unresolved_only=True,
            min_importance=0.3
        )
        self.stats["contradictions_found"] += len(result.contradictions)

        # Get research debt
        result.research_debt = self.graph.frontier.get_critical_debts(top_n=5)

        # Generate follow-up questions
        result.suggested_follow_ups = self._generate_follow_ups(question, answer)

        # Get provenance for top belief
        if answer.consensus_belief:
            result.provenance_chain = self.graph.get_provenance_chain(
                answer.consensus_belief.belief_id
            )

        return result

    def add_belief_from_source(
        self,
        claim: Claim,
        source: Source,
        confidence: float,
        extraction_method: Optional[str] = None
    ) -> Belief:
        """
        Add a belief to the graph from an external source.

        This is how we integrate external research (web scraping, etc.)
        """

        self.graph.add_source(source)

        belief = self.graph.add_belief(
            claim=claim,
            source=source,
            confidence=confidence,
            extraction_method=extraction_method
        )

        self.stats["beliefs_added"] += 1

        return belief

    def query(
        self,
        question: str,
        as_of: Optional[datetime] = None,
        min_confidence: float = 0.0
    ) -> BeliefDistribution:
        """
        Query the belief graph directly (without committee).

        This is fast but doesn't do new research.
        """

        return self.graph.query(
            question=question,
            as_of=as_of,
            min_confidence=min_confidence
        )

    def query_temporal(
        self,
        subject: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[Belief]:
        """Query beliefs over a time range - see how knowledge evolved"""

        return self.graph.query_temporal(subject, start_time, end_time)

    def query_counterfactual(
        self,
        question: str,
        exclude_sources: List[str]
    ) -> BeliefDistribution:
        """
        Counterfactual query: "What if we excluded these sources?"

        This lets you understand source impact.
        """

        return self.graph.counterfactual_query(question, exclude_sources)

    def get_contradictions(
        self,
        unresolved_only: bool = True,
        min_importance: float = 0.5
    ) -> List[Contradiction]:
        """Get contradictions in the knowledge graph"""

        return self.graph.get_contradictions(unresolved_only, min_importance)

    def get_research_debt(self) -> Dict[str, Any]:
        """Get summary of research debt"""

        return self.graph.frontier.get_total_debt()

    def suggest_next_research(self, n: int = 5) -> List[str]:
        """Suggest most valuable research to do next"""

        return self.graph.frontier.suggest_next_research(n)

    def get_provenance(self, belief_id: str):
        """Get full provenance chain for a belief"""

        return self.graph.get_provenance_chain(belief_id)

    def get_source_impact(self, source_id: str) -> Dict[str, Any]:
        """Analyze the impact of a source"""

        return self.graph.provenance.get_source_impact(source_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get system statistics"""

        graph_stats = self.graph.get_stats()

        return {
            **self.stats,
            **graph_stats
        }

    def to_summary(self) -> str:
        """System summary"""

        stats = self.get_stats()

        summary = "=== ResearchOS Status ===\n\n"
        summary += f"Queries: {stats['queries']}\n"
        summary += f"Beliefs: {stats['total_beliefs']}\n"
        summary += f"Sources: {stats['total_sources']}\n"
        summary += f"Contradictions: {stats['total_contradictions']} ({stats['unresolved_contradictions']} unresolved)\n"
        summary += f"Research Debt: {stats['research_debts']}\n"
        summary += f"Committees Convened: {stats['committees_convened']}\n"

        return summary

    def _generate_follow_ups(
        self,
        question: str,
        answer: BeliefDistribution
    ) -> List[str]:
        """Generate follow-up questions based on answer"""

        followups = []

        # If low consensus, ask about contradictions
        if not answer.has_consensus():
            followups.append(f"Why do sources disagree about: {question}?")

        # If there are contradictions, explore them
        contradictions = answer.get_contradictions()
        if contradictions:
            c = contradictions[0]
            followups.append(
                f"What explains the difference between "
                f"'{c[0].claim.object}' and '{c[1].claim.object}'?"
            )

        # Ask about causal factors
        if "what" in question.lower() or "who" in question.lower():
            followups.append(f"What factors influence: {question}?")

        # Ask temporal question
        if "when" not in question.lower():
            followups.append(f"When did this change: {question}?")

        return followups[:5]

    def __repr__(self) -> str:
        stats = self.get_stats()
        return f"ResearchOS(beliefs={stats['total_beliefs']}, sources={stats['total_sources']}, queries={stats['queries']})"
