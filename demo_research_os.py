#!/usr/bin/env python3
"""
ResearchOS Demo - Showcase of Spectacular Capabilities

This demo shows what makes ResearchOS revolutionary:
1. Probabilistic belief tracking (not just facts)
2. Temporal queries (how did beliefs evolve?)
3. Counterfactual queries (what if we excluded a source?)
4. Contradiction detection and tracking
5. Multi-agent research committees
6. Provenance chains (how do we know this?)
7. Research debt tracking (what don't we know?)
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.research_os import (
    ResearchOS,
    Claim,
    ClaimType,
    TemporalBeliefGraph,
    Source,
    ConsensusEngine,
)


def print_section(title: str):
    """Print a section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def demo_basic_beliefs():
    """Demo 1: Basic belief tracking with confidence"""

    print_section("DEMO 1: Probabilistic Belief Tracking")

    ros = ResearchOS()

    # Add beliefs from different sources about global population peak
    claims_data = [
        ("UN Population Division", "2064", 0.75, "un.org/population"),
        ("IHME Study", "2064", 0.80, "healthdata.org/population"),
        ("Lancet Study", "2070", 0.65, "thelancet.com/population"),
        ("Wittgenstein Centre", "2100", 0.50, "wittgenstein.ac.at"),
    ]

    for source_name, year, confidence, uri in claims_data:
        claim = Claim(
            subject="global_population_peak",
            predicate="will_occur_in_year",
            object=year,
            claim_type=ClaimType.TEMPORAL
        )

        source = Source(
            source_id=source_name.replace(" ", "_").lower(),
            uri=f"https://{uri}",
            source_type="url",
            domain=uri.split('/')[0],
            credibility_score=0.8 if "UN" in source_name else 0.7
        )

        ros.add_belief_from_source(
            claim=claim,
            source=source,
            confidence=confidence,
            extraction_method="manual_entry"
        )

    # Query for answer
    result = ros.query("global_population_peak")

    print("Question: When will global population peak?\n")
    print(result)

    print("\nNotice:")
    print("  • We get a DISTRIBUTION of beliefs, not a single answer")
    print("  • Each belief has confidence and provenance")
    print("  • Entropy shows us disagreement level")


def demo_temporal_queries():
    """Demo 2: Temporal queries - how did beliefs evolve?"""

    print_section("DEMO 2: Temporal Queries - Beliefs Evolving Over Time")

    graph = TemporalBeliefGraph()

    # Simulate beliefs about COVID origins evolving over time
    timeline_data = [
        (datetime(2020, 3, 1), "natural_origin", 0.8),
        (datetime(2020, 6, 1), "natural_origin", 0.7),
        (datetime(2021, 1, 1), "natural_origin", 0.6),
        (datetime(2021, 6, 1), "unknown", 0.5),
        (datetime(2023, 1, 1), "under_investigation", 0.6),
    ]

    source = Source(
        source_id="scientific_consensus",
        uri="https://scientific-consensus.org",
        source_type="meta-analysis"
    )

    graph.add_source(source)

    for timestamp, origin, confidence in timeline_data:
        claim = Claim(
            subject="COVID-19_origin",
            predicate="is_classified_as",
            object=origin,
            claim_type=ClaimType.FACTUAL
        )

        graph.add_belief(
            claim=claim,
            source=source,
            confidence=confidence,
            valid_from=timestamp
        )

    # Query at different points in time
    print("How did our belief about COVID origins evolve?\n")

    for query_date in [datetime(2020, 4, 1), datetime(2021, 7, 1), datetime(2023, 6, 1)]:
        result = graph.query("COVID-19_origin", as_of=query_date)

        if result.beliefs:
            belief = result.beliefs[0]
            print(f"{query_date.strftime('%B %Y'):20} → {belief.claim.object:25} (confidence: {belief.confidence:.2%})")

    print("\nNotice:")
    print("  • We can query 'what did we believe in the past?'")
    print("  • Temporal versioning tracks how knowledge changes")
    print("  • Confidence levels shift over time")


def demo_counterfactual_queries():
    """Demo 3: Counterfactual queries - what if we excluded a source?"""

    print_section("DEMO 3: Counterfactual Queries - Source Impact Analysis")

    ros = ResearchOS()

    # Add beliefs from different sources
    sources_data = [
        ("academic_study_1", "climate_action_urgent", 0.9, "Nature"),
        ("academic_study_2", "climate_action_urgent", 0.85, "Science"),
        ("industry_report", "climate_action_moderate", 0.7, "Oil & Gas Journal"),
        ("academic_study_3", "climate_action_urgent", 0.88, "PNAS"),
    ]

    for source_id, conclusion, confidence, journal in sources_data:
        claim = Claim(
            subject="climate_action_urgency",
            predicate="assessment_is",
            object=conclusion,
            claim_type=ClaimType.QUALITATIVE
        )

        source = Source(
            source_id=source_id,
            uri=f"https://{journal.replace(' ', '').lower()}.com",
            source_type="academic" if "study" in source_id else "industry",
            credibility_score=0.9 if "study" in source_id else 0.6
        )

        ros.add_belief_from_source(claim, source, confidence)

    # Normal query
    normal = ros.query("climate_action_urgency")
    print("With all sources:")
    if normal.consensus_belief:
        print(f"  Conclusion: {normal.consensus_belief.claim.object}")
        print(f"  Confidence: {normal.consensus_belief.confidence:.2%}\n")

    # Counterfactual: exclude industry source
    counterfactual = ros.query_counterfactual(
        "climate_action_urgency",
        exclude_sources=["industry_report"]
    )

    print("Excluding industry source:")
    if counterfactual.consensus_belief:
        print(f"  Conclusion: {counterfactual.consensus_belief.claim.object}")
        print(f"  Confidence: {counterfactual.consensus_belief.confidence:.2%}\n")

    print("Notice:")
    print("  • We can ask 'what if we excluded this source?'")
    print("  • Provenance tracking enables counterfactual reasoning")
    print("  • Useful for assessing source impact and bias")


def demo_contradiction_detection():
    """Demo 4: Contradiction detection"""

    print_section("DEMO 4: Contradiction Detection - Preserving Disagreement")

    ros = ResearchOS()

    # Add contradicting beliefs
    contradictory_data = [
        ("source_a", "remote_work_increases_productivity", 0.75),
        ("source_b", "remote_work_decreases_productivity", 0.70),
        ("source_c", "remote_work_increases_productivity", 0.80),
    ]

    for source_id, claim_text, confidence in contradictory_data:
        claim = Claim(
            subject="remote_work",
            predicate="productivity_effect",
            object=claim_text,
            claim_type=ClaimType.CAUSAL
        )

        source = Source(
            source_id=source_id,
            uri=f"https://{source_id}.com",
            source_type="study"
        )

        ros.add_belief_from_source(claim, source, confidence)

    # Get contradictions
    contradictions = ros.get_contradictions(min_importance=0.0)

    print(f"Detected {len(contradictions)} contradiction(s):\n")

    for contr in contradictions:
        print(contr)
        print(f"Suggested resolution: {contr.suggest_resolution_strategy()}\n")

        # Show generated research questions
        print("Generated research questions to resolve:")
        for q in contr.generate_research_questions()[:2]:
            print(f"  • {q}")
        print()

    print("Notice:")
    print("  • Contradictions are PRESERVED, not resolved")
    print("  • System suggests research to investigate disagreement")
    print("  • Contradictions drive new research questions")


def demo_research_committee():
    """Demo 5: Multi-agent research committee"""

    print_section("DEMO 5: Multi-Agent Research Committee - Collaborative Investigation")

    from src.research_os.agents.research_committee import ResearchCommittee
    from src.research_os.agents.base_agent import (
        OptimistAgent,
        SkepticAgent,
        MethodologistAgent,
        SynthesizerAgent,
        ResearchFinding,
    )

    # Create a committee
    committee = ResearchCommittee(
        question="Should we adopt renewable energy?",
        max_rounds=2
    )

    # Manually add some mock findings for demo purposes
    # (In real use, agents would actually research)

    optimist_findings = [
        ResearchFinding(
            claim="Renewable energy is cost-effective",
            evidence=["https://nrel.gov/renewable-cost-2023"],
            confidence=0.85,
            agent_role=committee.agents[0].role,
            reasoning="NREL study shows solar/wind are now cheapest"
        )
    ]

    skeptic_findings = [
        ResearchFinding(
            claim="Renewable energy has reliability concerns",
            evidence=["https://grid-reliability-study.org"],
            confidence=0.70,
            agent_role=committee.agents[1].role,
            reasoning="Grid stability issues during peak demand"
        )
    ]

    # Add findings to transcript (simulating research phase)
    committee.transcript.findings.extend(optimist_findings)
    committee.transcript.findings.extend(skeptic_findings)

    print("Committee Composition:")
    for agent in committee.agents:
        print(f"  • {agent.agent_id} ({agent.role.value})")

    print("\nMock Findings (in real use, agents would research):")
    print(f"  Optimist: {optimist_findings[0].claim}")
    print(f"  Skeptic: {skeptic_findings[0].claim}")

    print("\nNotice:")
    print("  • Multiple agents with different perspectives")
    print("  • Agents would independently research, then debate")
    print("  • Synthesizer would reconcile contradictory findings")
    print("  • Mirrors real research: peer review, replication, debate")


def demo_provenance_chain():
    """Demo 6: Provenance chains"""

    print_section("DEMO 6: Provenance Chains - How Do We Know This?")

    ros = ResearchOS()

    # Add a belief with provenance
    claim = Claim(
        subject="earth_temperature",
        predicate="increasing_at_rate",
        object="0.2C per decade",
        claim_type=ClaimType.STATISTICAL
    )

    source = Source(
        source_id="nasa_climate",
        uri="https://climate.nasa.gov/vital-signs/global-temperature",
        source_type="url",
        author="NASA",
        credibility_score=0.95
    )

    belief = ros.add_belief_from_source(
        claim=claim,
        source=source,
        confidence=0.92,
        extraction_method="web_scraping"
    )

    # Get provenance
    prov_chain = ros.get_provenance(belief.belief_id)

    if prov_chain:
        print("Provenance Chain:\n")
        print(prov_chain)

    print("\nNotice:")
    print("  • Every belief has complete lineage")
    print("  • We can trace back to original sources")
    print("  • Confidence propagates through transformation chain")
    print("  • Enables 'explain why you believe this'")


def demo_research_debt():
    """Demo 7: Research debt tracking"""

    print_section("DEMO 7: Research Debt - Tracking What We Don't Know")

    from src.research_os.core.frontier import FailureReason

    ros = ResearchOS()

    # Simulate failed research attempts
    ros.graph.record_research_debt(
        question="Full text of key paper on quantum computing",
        attempted_sources=["https://nature.com/article/12345"],
        failure_reason=FailureReason.PAYWALL,
        importance=0.8
    )

    ros.graph.record_research_debt(
        question="Historical climate data from 1800-1850",
        attempted_sources=["https://old-archive.gov"],
        failure_reason=FailureReason.NOT_FOUND,
        importance=0.6
    )

    # Get debt summary
    debt_summary = ros.get_research_debt()

    print("Research Debt Summary:")
    print(f"  Total debts: {debt_summary['total_debts']}")
    print(f"  Critical debts: {debt_summary['critical_debts']}\n")

    print("By failure reason:")
    for reason, count in debt_summary['by_reason'].items():
        print(f"  • {reason}: {count}")

    print("\nSuggested next research:")
    for suggestion in ros.suggest_next_research(3):
        print(f"  • {suggestion}")

    print("\nNotice:")
    print("  • System tracks what it TRIED to learn but couldn't")
    print("  • Suggests strategies to 'pay down' debt")
    print("  • Knows the boundaries of its knowledge")


def demo_system_stats():
    """Demo 8: System statistics"""

    print_section("DEMO 8: System Statistics & Summary")

    # Create a system with some activity
    ros = ResearchOS()

    # Add some data
    for i in range(5):
        claim = Claim(
            subject=f"topic_{i}",
            predicate="value_is",
            object=f"value_{i}",
            claim_type=ClaimType.FACTUAL
        )

        source = Source(
            source_id=f"source_{i}",
            uri=f"https://source{i}.com",
            source_type="url"
        )

        ros.add_belief_from_source(claim, source, confidence=0.7 + i * 0.05)

    # Run some queries
    ros.query("topic_1")
    ros.query("topic_2")

    # Get stats
    print(ros.to_summary())

    print("\nNotice:")
    print("  • Complete system observability")
    print("  • Track queries, beliefs, sources, contradictions")
    print("  • Monitor research debt accumulation")


def main():
    """Run all demos"""

    print("\n" + "█" * 80)
    print("█" + " " * 78 + "█")
    print("█" + "  ResearchOS - Operating System for Knowledge Acquisition".center(78) + "█")
    print("█" + " " * 78 + "█")
    print("█" * 80)

    demos = [
        ("Basic Probabilistic Belief Tracking", demo_basic_beliefs),
        ("Temporal Queries", demo_temporal_queries),
        ("Counterfactual Queries", demo_counterfactual_queries),
        ("Contradiction Detection", demo_contradiction_detection),
        ("Multi-Agent Research Committee", demo_research_committee),
        ("Provenance Chains", demo_provenance_chain),
        ("Research Debt Tracking", demo_research_debt),
        ("System Statistics", demo_system_stats),
    ]

    print("\nThis demo showcases ResearchOS's revolutionary capabilities:\n")
    for i, (name, _) in enumerate(demos, 1):
        print(f"  {i}. {name}")

    print("\n" + "─" * 80)

    for name, demo_func in demos:
        try:
            demo_func()
        except Exception as e:
            print(f"\n❌ Error in {name}: {e}")
            import traceback
            traceback.print_exc()

    print_section("Demo Complete!")

    print("ResearchOS enables:")
    print("  ✓ Probabilistic knowledge representation")
    print("  ✓ Temporal reasoning (how did we know in the past?)")
    print("  ✓ Counterfactual queries (what if we excluded X?)")
    print("  ✓ Contradiction preservation and investigation")
    print("  ✓ Multi-agent collaborative research")
    print("  ✓ Complete provenance tracking")
    print("  ✓ Research debt management")
    print("\nThis is an OPERATING SYSTEM for knowledge, not just a search tool.\n")


if __name__ == "__main__":
    main()
