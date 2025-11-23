"""
Research Operating System (ResearchOS)

A revolutionary architecture for knowledge acquisition that treats research
as a distributed consensus problem with temporal versioning and provenance tracking.

Core Concepts:
- Research is probabilistic belief aggregation, not fact retrieval
- Every claim has provenance, temporal validity, and confidence
- Contradictions are first-class citizens
- Multi-agent debate leads to consensus
- The system knows what it doesn't know (research debt)
"""

from .core.belief import Belief, Claim, BeliefDistribution, ClaimType
from .core.temporal_graph import TemporalBeliefGraph
from .core.provenance import ProvenanceDAG, ProvenanceChain, Source, ProvenanceType
from .core.consensus import ConsensusEngine
from .core.contradiction import Contradiction, ContradictionType
from .core.frontier import KnowledgeFrontier, ResearchDebt, FailureReason
from .agents.research_committee import ResearchCommittee
from .kernel.research_os import ResearchOS

__version__ = "0.1.0"
__all__ = [
    "Belief",
    "Claim",
    "ClaimType",
    "BeliefDistribution",
    "TemporalBeliefGraph",
    "ProvenanceDAG",
    "ProvenanceChain",
    "Source",
    "ProvenanceType",
    "ConsensusEngine",
    "Contradiction",
    "ContradictionType",
    "KnowledgeFrontier",
    "ResearchDebt",
    "FailureReason",
    "ResearchCommittee",
    "ResearchOS",
]
