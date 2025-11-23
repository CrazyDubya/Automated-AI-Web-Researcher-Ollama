"""
Knowledge Frontier - Tracking the boundaries of what we know

Traditional systems don't know what they don't know.
ResearchOS explicitly tracks:
- Research debt (things we tried to learn but couldn't)
- Knowledge gaps (missing connections in our knowledge graph)
- Uncertainty frontiers (where our confidence drops off)

This enables:
- "What would be most valuable to research next?"
- "What are the biggest gaps in our knowledge?"
- "What sources have we failed to access?"
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Set
from enum import Enum


class FailureReason(Enum):
    """Why we couldn't acquire information"""
    PAYWALL = "paywall"
    AUTH_REQUIRED = "auth_required"
    NOT_FOUND = "not_found"
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"
    PARSE_ERROR = "parse_error"
    NO_RESULTS = "no_results"
    INSUFFICIENT_QUALITY = "insufficient_quality"


@dataclass
class ResearchDebt:
    """
    Research debt represents things we TRIED to learn but couldn't.

    Like technical debt, research debt accumulates and should be "paid down"
    when possible.
    """

    question: str
    attempted_sources: List[str]
    failure_reason: FailureReason
    attempted_at: datetime = field(default_factory=datetime.now)

    # How critical is it to resolve this?
    importance: float = 0.5  # 0.0 = nice to have, 1.0 = critical

    # What would help resolve this?
    resolution_strategies: List[str] = field(default_factory=list)

    # Dependencies
    blocks_questions: List[str] = field(default_factory=list)  # Questions that need this

    @property
    def debt_id(self) -> str:
        """Unique identifier for this debt"""
        import hashlib
        debt_str = f"{self.question}::{self.failure_reason.value}::{self.attempted_at.isoformat()}"
        return hashlib.sha256(debt_str.encode()).hexdigest()[:16]

    def suggest_solutions(self) -> List[str]:
        """Suggest ways to pay down this debt"""
        solutions = []

        if self.failure_reason == FailureReason.PAYWALL:
            solutions.extend([
                "Try institutional access (university library)",
                "Look for preprint on arXiv/bioRxiv",
                "Contact authors for copy",
                "Check if cited by open-access papers",
                "Use interlibrary loan"
            ])

        elif self.failure_reason == FailureReason.NOT_FOUND:
            solutions.extend([
                "Try alternative search terms",
                "Search in different databases",
                "Look for related/similar sources",
                "Check if resource moved (search for author/title)"
            ])

        elif self.failure_reason == FailureReason.NO_RESULTS:
            solutions.extend([
                "Broaden search terms",
                "Try different search engines/databases",
                "Question may be too specific or novel",
                "Look for related topics that might inform this"
            ])

        elif self.failure_reason == FailureReason.PARSE_ERROR:
            solutions.extend([
                "Try different parsing method",
                "Manual extraction may be needed",
                "Source may have anti-scraping measures",
                "Look for alternative format (PDF vs HTML)"
            ])

        return solutions

    def __str__(self) -> str:
        debt_str = f"Research Debt ({self.failure_reason.value}):\n"
        debt_str += f"  Question: {self.question}\n"
        debt_str += f"  Attempted: {len(self.attempted_sources)} source(s)\n"
        debt_str += f"  Importance: {self.importance:.2f}\n"

        if self.blocks_questions:
            debt_str += f"  Blocks: {len(self.blocks_questions)} other question(s)\n"

        if self.resolution_strategies:
            debt_str += f"  Strategies: {', '.join(self.resolution_strategies[:3])}\n"

        return debt_str


@dataclass
class KnowledgeGap:
    """A missing connection in our knowledge graph"""

    gap_id: str
    description: str

    # What's on either side of the gap?
    known_before: Optional[str] = None  # Belief/entity we know
    known_after: Optional[str] = None  # Belief/entity we know

    # The missing link
    missing_predicate: Optional[str] = None  # What relationship are we missing?

    # How important is it to fill this gap?
    importance: float = 0.5

    # Potential research to fill the gap
    suggested_queries: List[str] = field(default_factory=list)

    def __str__(self) -> str:
        gap_str = f"Knowledge Gap: {self.description}\n"
        if self.known_before and self.known_after:
            gap_str += f"  We know: {self.known_before}\n"
            gap_str += f"  We know: {self.known_after}\n"
            gap_str += f"  Missing: How are they connected?\n"

        if self.suggested_queries:
            gap_str += f"  Suggested: {self.suggested_queries[0]}\n"

        return gap_str


class KnowledgeFrontier:
    """
    Tracks the boundaries of our knowledge.

    The frontier has three components:
    1. Research debt (failed acquisition attempts)
    2. Knowledge gaps (missing connections)
    3. Low-confidence regions (uncertain beliefs)
    """

    def __init__(self):
        self.research_debts: List[ResearchDebt] = []
        self.knowledge_gaps: List[KnowledgeGap] = []

        # Track attempted sources to avoid retrying too soon
        self._attempted_sources: dict[str, datetime] = {}

    def add_debt(
        self,
        question: str,
        attempted_sources: List[str],
        failure_reason: FailureReason,
        importance: float = 0.5
    ) -> ResearchDebt:
        """Record a failed research attempt"""

        debt = ResearchDebt(
            question=question,
            attempted_sources=attempted_sources,
            failure_reason=failure_reason,
            importance=importance
        )

        # Suggest resolution strategies
        debt.resolution_strategies = debt.suggest_solutions()

        self.research_debts.append(debt)

        # Track attempted sources
        for source in attempted_sources:
            self._attempted_sources[source] = datetime.now()

        return debt

    def add_gap(
        self,
        description: str,
        known_before: Optional[str] = None,
        known_after: Optional[str] = None,
        importance: float = 0.5
    ) -> KnowledgeGap:
        """Record a knowledge gap"""

        import hashlib
        gap_id = hashlib.sha256(description.encode()).hexdigest()[:16]

        gap = KnowledgeGap(
            gap_id=gap_id,
            description=description,
            known_before=known_before,
            known_after=known_after,
            importance=importance
        )

        self.knowledge_gaps.append(gap)
        return gap

    def get_critical_debts(self, top_n: int = 10) -> List[ResearchDebt]:
        """Get the most important research debts"""
        return sorted(
            self.research_debts,
            key=lambda d: d.importance,
            reverse=True
        )[:top_n]

    def get_critical_gaps(self, top_n: int = 10) -> List[KnowledgeGap]:
        """Get the most important knowledge gaps"""
        return sorted(
            self.knowledge_gaps,
            key=lambda g: g.importance,
            reverse=True
        )[:top_n]

    def get_debts_for_question(self, question: str) -> List[ResearchDebt]:
        """Get all debts related to a question"""
        return [d for d in self.research_debts if question.lower() in d.question.lower()]

    def get_total_debt(self) -> dict:
        """Summary of total research debt"""
        debt_by_reason = {}
        for debt in self.research_debts:
            reason = debt.failure_reason.value
            debt_by_reason[reason] = debt_by_reason.get(reason, 0) + 1

        return {
            "total_debts": len(self.research_debts),
            "total_gaps": len(self.knowledge_gaps),
            "by_reason": debt_by_reason,
            "critical_debts": len([d for d in self.research_debts if d.importance > 0.7])
        }

    def suggest_next_research(self, n: int = 5) -> List[str]:
        """Suggest the most valuable research to do next"""

        suggestions = []

        # High-importance debts that block other questions
        blocking_debts = [
            d for d in self.research_debts
            if d.importance > 0.6 and d.blocks_questions
        ]
        for debt in sorted(blocking_debts, key=lambda d: len(d.blocks_questions), reverse=True)[:n]:
            suggestions.append(debt.question)

        # High-importance gaps
        for gap in self.get_critical_gaps(n):
            if gap.suggested_queries:
                suggestions.append(gap.suggested_queries[0])

        return suggestions[:n]

    def has_recently_attempted(self, source: str, hours: int = 24) -> bool:
        """Check if we recently tried a source"""
        if source not in self._attempted_sources:
            return False

        last_attempt = self._attempted_sources[source]
        hours_since = (datetime.now() - last_attempt).total_seconds() / 3600

        return hours_since < hours

    def mark_debt_resolved(self, debt: ResearchDebt):
        """Remove a debt that's been paid down"""
        if debt in self.research_debts:
            self.research_debts.remove(debt)

    def mark_gap_filled(self, gap: KnowledgeGap):
        """Remove a gap that's been filled"""
        if gap in self.knowledge_gaps:
            self.knowledge_gaps.remove(gap)

    def to_report(self) -> str:
        """Generate a frontier report"""
        report = "=== Knowledge Frontier Report ===\n\n"

        summary = self.get_total_debt()
        report += f"Total Research Debts: {summary['total_debts']}\n"
        report += f"Total Knowledge Gaps: {summary['total_gaps']}\n"
        report += f"Critical Debts: {summary['critical_debts']}\n\n"

        if summary['by_reason']:
            report += "Debt by Reason:\n"
            for reason, count in summary['by_reason'].items():
                report += f"  • {reason}: {count}\n"
            report += "\n"

        report += "=== Top Priority Debts ===\n\n"
        for debt in self.get_critical_debts(5):
            report += str(debt) + "\n"

        report += "=== Top Priority Gaps ===\n\n"
        for gap in self.get_critical_gaps(5):
            report += str(gap) + "\n"

        report += "=== Suggested Next Research ===\n\n"
        for suggestion in self.suggest_next_research(5):
            report += f"  • {suggestion}\n"

        return report

    def __len__(self) -> int:
        return len(self.research_debts) + len(self.knowledge_gaps)

    def __repr__(self) -> str:
        return f"KnowledgeFrontier(debts={len(self.research_debts)}, gaps={len(self.knowledge_gaps)})"
