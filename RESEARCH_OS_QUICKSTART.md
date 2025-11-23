# ResearchOS Quick Start

## What is ResearchOS?

**ResearchOS is an Operating System for Knowledge Acquisition** - a revolutionary architecture that treats research as:
- Distributed consensus (sources disagree, we track probability)
- Temporal knowledge (truth changes over time)
- Provenance-tracked (we know HOW we know)
- Multi-agent collaboration (debate yields better results)

## 5-Minute Tour

### 1. Run the Demo
```bash
python demo_research_os.py
```

This showcases all spectacular capabilities:
- Probabilistic beliefs (not just facts)
- Temporal queries (what did we believe in 2020?)
- Counterfactual reasoning (what if we excluded source X?)
- Contradiction detection (preserved, not hidden)
- Multi-agent research committees
- Provenance chains (full audit trail)
- Research debt tracking (what we don't know)

### 2. Basic Usage

```python
from src.research_os import ResearchOS, Claim, Source, ClaimType

# Initialize
ros = ResearchOS()

# Add a belief
claim = Claim(
    subject="climate_change",
    predicate="urgency_level",
    object="critical",
    claim_type=ClaimType.QUALITATIVE
)

source = Source(
    source_id="ipcc_2023",
    uri="https://ipcc.ch/report",
    source_type="scientific_report",
    credibility_score=0.95
)

ros.add_belief_from_source(claim, source, confidence=0.92)

# Query
result = ros.query("climate change urgency")
print(result.answer)  # Shows distribution, not single answer!
```

### 3. The Revolutionary Part

**Traditional System:**
```
Q: "When will population peak?"
A: "2064"  ← Single answer, no uncertainty
```

**ResearchOS:**
```python
Q: "When will population peak?"
A: BeliefDistribution(
    [75%] 2064 (UN, IHME),
    [25%] 2070 (Lancet),
    [10%] 2100+ (Wittgenstein),
    entropy=0.62  # Moderate disagreement
)

Contradictions: None
Research Debt: 2 paywalled papers
Provenance: Full chain available
```

**You get:**
- ✅ Uncertainty quantification
- ✅ Source attribution
- ✅ Contradiction awareness
- ✅ Research gap identification
- ✅ Complete audit trail

## Key Capabilities

### Temporal Queries
```python
# What did we believe before?
past = ros.query("COVID origins", as_of=datetime(2020, 4, 1))
# → "Natural origin" (80%)

now = ros.query("COVID origins", as_of=datetime.now())
# → "Under investigation" (60%)

# See belief evolution
evolution = ros.query_temporal("COVID origins", start=2020, end=2024)
```

### Counterfactual Reasoning
```python
# Normal query
normal = ros.query("Climate action urgency")
# → 85% "critical"

# What if we excluded industry sources?
no_industry = ros.query_counterfactual(
    "Climate action urgency",
    exclude_sources=["oil_gas_industry"]
)
# → 94% "critical"

# Industry impact: -9 percentage points!
```

### Provenance Tracking
```python
# How do we know this?
belief = result.consensus_belief
provenance = ros.get_provenance(belief.belief_id)

# Shows full chain:
#   Source → Snapshot → Extraction → Synthesis → Belief
# With confidence at each step!
```

### Contradiction Detection
```python
contradictions = ros.get_contradictions(min_importance=0.7)

# Contradictions auto-generate research questions:
#   - "Why do sources disagree?"
#   - "What methodological differences explain this?"
#   - "Has the truth changed over time?"
```

### Multi-Agent Research
```python
from src.research_os.agents import ResearchCommittee

committee = ResearchCommittee(
    question="Should we adopt renewable energy?",
    max_rounds=3
)

transcript = committee.deliberate()

# Agents debate:
#   Optimist: Finds supporting evidence
#   Skeptic: Finds contradicting evidence
#   Methodologist: Critiques methodology
#   Synthesizer: Reconciles views
```

## Architecture at a Glance

```
                    ┌─────────────────┐
                    │   ResearchOS    │
                    │     Kernel      │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
┌───────────────┐    ┌──────────────┐    ┌──────────────┐
│ Temporal      │    │ Multi-Agent  │    │ Consensus    │
│ Belief Graph  │◄──►│  Committee   │◄──►│   Engine     │
└───────────────┘    └──────────────┘    └──────────────┘
        ▼                    ▼                    ▼
┌───────────────┐    ┌──────────────┐    ┌──────────────┐
│ Provenance    │    │Contradiction │    │  Knowledge   │
│     DAG       │    │  Detection   │    │   Frontier   │
└───────────────┘    └──────────────┘    └──────────────┘
```

## Why This Matters

### 1. Research is Probabilistic
Real research deals with uncertainty. ResearchOS represents it explicitly:
- Confidence scores, not binary facts
- Distributions, not single answers
- Entropy as disagreement metric

### 2. Sources Contradict
Traditional systems hide contradictions. ResearchOS:
- Preserves all contradicting views
- Tracks importance of resolving them
- Auto-generates investigation questions

### 3. Knowledge Evolves
What was true yesterday may not be true today:
- Temporal versioning (valid time + transaction time)
- "What did we believe in 2020?"
- Belief evolution timelines

### 4. Provenance Matters
"How do you know?" is as important as "What do you know?":
- Complete audit trail
- Counterfactual queries
- Source impact analysis

### 5. Collaboration Improves Outcomes
Multiple perspectives beat single-shot answers:
- Adversarial agents find flaws
- Debate surfaces assumptions
- Synthesis reconciles views

## Integration with Existing System

ResearchOS is the ENGINE that powers:

| Existing Feature | ResearchOS Component |
|------------------|---------------------|
| Radar monitoring | → Continuous belief updates |
| Web scraping | → Source acquisition |
| LLM analysis | → Belief extraction |
| Change detection | → Temporal graph updates |
| Report generation | → Consensus aggregation |

**All existing features become more powerful** when built on ResearchOS.

## Next Steps

1. **Run the demo**: `python demo_research_os.py`
2. **Read the docs**: `RESEARCH_OS.md`
3. **Explore the code**: `src/research_os/`
4. **Try integration**: Connect your data sources to ResearchOS

## The Vision

ResearchOS is not just a tool - it's **infrastructure for knowledge**.

Just as:
- Linux provides primitives for computation (processes, files, sockets)
- Git provides primitives for version control (commits, branches, merges)

**ResearchOS provides primitives for epistemology:**
- Beliefs (not facts)
- Provenances (not just sources)
- Contradictions (not errors)
- Frontiers (not gaps)

**Build research applications on this foundation:**
- Civic monitors
- Literature reviewers
- Fact checkers
- Intelligence analysts
- Scientific meta-analyzers
- Consumer protection tools
- Legal research assistants

## Core Philosophy

1. **Embrace Uncertainty** - Represent it, don't hide it
2. **Preserve Disagreement** - Contradictions drive research
3. **Track Lineage** - Provenance enables explanation
4. **Version Everything** - Knowledge changes over time
5. **Collaborate** - Multiple perspectives yield truth
6. **Know Boundaries** - Track what you don't know

---

**This is an agentic system to be proud of.**

See `RESEARCH_OS.md` for complete documentation.
