"""
Provenance Tracking - Complete audit trail of knowledge lineage

Every piece of knowledge in ResearchOS has a PROVENANCE CHAIN:
- Where did we get this information?
- What transformations were applied?
- What other beliefs does this depend on?

This enables:
- Counterfactual queries: "What if source X was wrong?"
- Trust assessment: "How reliable is this claim?"
- Explanation: "Why do you believe this?"
- Debugging: "Where did this belief come from?"
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Set, List
from enum import Enum
import hashlib


class ProvenanceType(Enum):
    """Types of provenance operations"""
    ACQUIRED = "acquired"  # Fetched from a source
    EXTRACTED = "extracted"  # Extracted from unstructured content
    INFERRED = "inferred"  # Derived through reasoning
    SYNTHESIZED = "synthesized"  # Combined from multiple sources
    TRANSFORMED = "transformed"  # Modified/normalized
    VALIDATED = "validated"  # Cross-checked against other sources


@dataclass
class Source:
    """A source of information"""
    source_id: str
    uri: str  # URL, file path, API endpoint, etc.
    source_type: str  # "url", "api", "pdf", "feed", etc.

    # Source metadata
    domain: Optional[str] = None
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    accessed_at: datetime = field(default_factory=datetime.now)

    # Trust metrics
    credibility_score: float = 0.5  # 0.0 = untrusted, 1.0 = fully trusted
    bias_score: float = 0.5  # 0.0 = heavily biased, 1.0 = neutral

    # Content hash for change detection
    content_hash: Optional[str] = None

    def __hash__(self):
        return hash(self.source_id)

    def __eq__(self, other):
        if not isinstance(other, Source):
            return False
        return self.source_id == other.source_id


@dataclass
class ProvenanceNode:
    """A node in the provenance DAG"""
    node_id: str
    operation: ProvenanceType
    artifact_id: str  # Belief ID, entity ID, etc.
    artifact_type: str  # "belief", "entity", "report", etc.

    # Timestamp
    timestamp: datetime = field(default_factory=datetime.now)

    # Dependencies (edges in the DAG)
    derived_from: List[str] = field(default_factory=list)  # Other node IDs

    # Sources consulted
    source_ids: Set[str] = field(default_factory=set)

    # Operation details
    method: Optional[str] = None  # e.g., "llm_extraction", "keyword_match"
    parameters: dict = field(default_factory=dict)

    # Quality metrics
    confidence: float = 1.0

    def __hash__(self):
        return hash(self.node_id)

    def __eq__(self, other):
        if not isinstance(other, ProvenanceNode):
            return False
        return self.node_id == other.node_id


@dataclass
class ProvenanceChain:
    """A complete lineage trace from sources to final artifact"""
    artifact_id: str
    nodes: List[ProvenanceNode]
    sources: Set[Source]

    @property
    def depth(self) -> int:
        """How many transformation steps from source to artifact"""
        return len(self.nodes)

    @property
    def source_count(self) -> int:
        """How many unique sources contributed"""
        return len(self.sources)

    @property
    def combined_confidence(self) -> float:
        """Product of all confidence scores in the chain"""
        if not self.nodes:
            return 0.0
        confidence = 1.0
        for node in self.nodes:
            confidence *= node.confidence
        return confidence

    def to_trace(self) -> str:
        """Human-readable provenance trace"""
        trace = f"Provenance chain for {self.artifact_id}:\n"
        trace += f"  Sources: {self.source_count}\n"
        trace += f"  Steps: {self.depth}\n"
        trace += f"  Confidence: {self.combined_confidence:.2%}\n\n"

        for i, node in enumerate(self.nodes, 1):
            trace += f"  {i}. [{node.operation.value}] {node.method or 'unknown'}\n"
            if node.derived_from:
                trace += f"     Depends on: {len(node.derived_from)} artifacts\n"
            if node.source_ids:
                trace += f"     Sources: {len(node.source_ids)}\n"

        trace += "\n  Original sources:\n"
        for source in self.sources:
            trace += f"    • {source.uri} (credibility: {source.credibility_score:.2f})\n"

        return trace

    def __str__(self) -> str:
        return self.to_trace()


class ProvenanceDAG:
    """
    Directed Acyclic Graph of provenance relationships.

    This is the complete audit trail of all knowledge in the system.
    """

    def __init__(self):
        self.nodes: dict[str, ProvenanceNode] = {}
        self.sources: dict[str, Source] = {}

        # Indexes for fast querying
        self._artifact_to_node: dict[str, str] = {}  # artifact_id -> node_id
        self._source_to_artifacts: dict[str, Set[str]] = {}  # source_id -> {artifact_ids}

    def add_source(self, source: Source):
        """Register a source"""
        self.sources[source.source_id] = source
        if source.source_id not in self._source_to_artifacts:
            self._source_to_artifacts[source.source_id] = set()

    def add_node(
        self,
        artifact_id: str,
        artifact_type: str,
        operation: ProvenanceType,
        derived_from: List[str] = None,
        source_ids: Set[str] = None,
        method: str = None,
        parameters: dict = None,
        confidence: float = 1.0
    ) -> ProvenanceNode:
        """Add a provenance node"""

        node_id = self._generate_node_id(artifact_id, operation)

        node = ProvenanceNode(
            node_id=node_id,
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            operation=operation,
            derived_from=derived_from or [],
            source_ids=source_ids or set(),
            method=method,
            parameters=parameters or {},
            confidence=confidence
        )

        self.nodes[node_id] = node
        self._artifact_to_node[artifact_id] = node_id

        # Update source index
        for source_id in node.source_ids:
            if source_id in self._source_to_artifacts:
                self._source_to_artifacts[source_id].add(artifact_id)

        return node

    def get_chain(self, artifact_id: str) -> Optional[ProvenanceChain]:
        """Get the complete provenance chain for an artifact"""
        if artifact_id not in self._artifact_to_node:
            return None

        # Traverse DAG backwards to find all nodes and sources
        nodes = []
        sources = set()
        visited = set()

        def traverse(aid: str):
            if aid in visited:
                return
            visited.add(aid)

            if aid not in self._artifact_to_node:
                return

            node_id = self._artifact_to_node[aid]
            node = self.nodes[node_id]
            nodes.append(node)

            # Collect sources
            for source_id in node.source_ids:
                if source_id in self.sources:
                    sources.add(self.sources[source_id])

            # Recurse on dependencies
            for dep_id in node.derived_from:
                traverse(dep_id)

        traverse(artifact_id)

        return ProvenanceChain(
            artifact_id=artifact_id,
            nodes=nodes,
            sources=sources
        )

    def get_artifacts_from_source(self, source_id: str) -> Set[str]:
        """Get all artifacts that depend on a source"""
        return self._source_to_artifacts.get(source_id, set())

    def prune_source(self, source_id: str) -> 'ProvenanceDAG':
        """
        Create a new DAG excluding a source.

        This enables counterfactual queries:
        "What would we know if we didn't have source X?"
        """
        pruned = ProvenanceDAG()

        # Copy sources except the pruned one
        for sid, source in self.sources.items():
            if sid != source_id:
                pruned.add_source(source)

        # Copy nodes that don't depend on pruned source
        artifacts_to_prune = self.get_artifacts_from_source(source_id)

        for node_id, node in self.nodes.items():
            if node.artifact_id not in artifacts_to_prune:
                # Check if any dependencies were pruned
                valid_deps = [
                    dep for dep in node.derived_from
                    if dep not in artifacts_to_prune
                ]

                # Only include if all dependencies are valid
                if len(valid_deps) == len(node.derived_from):
                    pruned.nodes[node_id] = node
                    pruned._artifact_to_node[node.artifact_id] = node_id

        return pruned

    def get_source_impact(self, source_id: str) -> dict:
        """Analyze the impact of a source"""
        artifacts = self.get_artifacts_from_source(source_id)

        return {
            "source_id": source_id,
            "artifact_count": len(artifacts),
            "artifact_types": self._count_artifact_types(artifacts),
            "credibility": self.sources[source_id].credibility_score if source_id in self.sources else 0.0
        }

    def _count_artifact_types(self, artifact_ids: Set[str]) -> dict:
        """Count artifacts by type"""
        counts = {}
        for aid in artifact_ids:
            if aid in self._artifact_to_node:
                node = self.nodes[self._artifact_to_node[aid]]
                atype = node.artifact_type
                counts[atype] = counts.get(atype, 0) + 1
        return counts

    def _generate_node_id(self, artifact_id: str, operation: ProvenanceType) -> str:
        """Generate unique node ID"""
        node_str = f"{artifact_id}::{operation.value}::{datetime.now().isoformat()}"
        return hashlib.sha256(node_str.encode()).hexdigest()[:16]

    def visualize_chain(self, artifact_id: str) -> str:
        """ASCII visualization of provenance chain"""
        chain = self.get_chain(artifact_id)
        if not chain:
            return f"No provenance found for {artifact_id}"

        # Build tree structure
        lines = ["Provenance Tree:", ""]

        def build_tree(aid: str, indent: int = 0):
            if aid not in self._artifact_to_node:
                return
            node = self.nodes[self._artifact_to_node[aid]]

            prefix = "  " * indent + "└─ "
            lines.append(f"{prefix}[{node.operation.value}] {aid[:12]}...")

            if node.source_ids:
                source_line = "  " * (indent + 1) + f"📄 {len(node.source_ids)} source(s)"
                lines.append(source_line)

            for dep in node.derived_from:
                build_tree(dep, indent + 1)

        build_tree(artifact_id)
        return "\n".join(lines)

    def __len__(self) -> int:
        return len(self.nodes)

    def __repr__(self) -> str:
        return f"ProvenanceDAG(nodes={len(self.nodes)}, sources={len(self.sources)})"
