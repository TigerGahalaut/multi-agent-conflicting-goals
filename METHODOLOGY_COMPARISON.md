# Methodological Comparison: The Two Experimental Harnesses

**Project:** *Conflicting Goals: Governance Mechanisms for AI Agent Bargaining* (Team Skynet, Team 67)  
**Reference Specification:** [`Conflicting_Goals_Proposal_v2_MkII.pdf`](file:///C:/Users/anany/Desktop/AI%20Gov/final_project/Conflicting_Goals_Proposal_v2_MkII.pdf)

---

## 1. Executive Summary: Two Complementary Academic Lenses

Both harnesses operationalize the exact same 3-company, \$1,000,000 joint venture scenario across the proposal’s three governance mechanisms: **Free Negotiation**, **Board Vote**, and **Neutral Arbitration**. 

However, because the 1-page proposal defined the scenario in broad strokes without specifying lower-level protocol rules, the two branches approached the problem through two distinct academic paradigms:

```
┌────────────────────────────────────────────────────────────────────────┐
│                      TWO METHODOLOGICAL PARADIGMS                      │
├───────────────────────────────────┬────────────────────────────────────┤
│     Harness B (`ananya-gemini`)    │          Harness A (`main`)         │
│   Formal Mechanism Design & Micro  │  Behavioral Economics & Lab Trials │
├───────────────────────────────────┼────────────────────────────────────┤
│ • Tests formal game theory rules  │ • Tests conversational interaction │
│ • Dual free & legislative options │ • Turn-based dialogue simulation   │
│ • Deliberative multi-stage voting │ • Blind proposal ballot & merging  │
│ • Adaptive mediation with feedback│ • Blind arbitration (pure bluffing)│
│ • Dynamic bluffing & claim drift  │ • Standardized pre-game baselines  │
│ • Geometric (Euclidean) Nash space│ • Rule vs. choice causal breakdown │
└───────────────────────────────────┴────────────────────────────────────┘
```

Having run the **exact same Gemini models** (`gemini-3.5-flash-lite` and `gemini-3.8-flash`) across all conditions in both harnesses gives our team an empirical cross-validation dataset that provides unique depth for the final paper.

---

## 2. Condition-by-Condition Methodological Breakdown

### Condition 1: Free Negotiation (Unanimous Consent)

| Methodological Dimension | Harness A (`main`) | Harness B (`ananya-gemini`) |
| :--- | :--- | :--- |
| **Operationalization** | **Turn-taking conversation:** Sequential speaking order; agents choose `propose`, `accept`, or `pass`. | **Dual Implementation:** Evaluates **both** Conversational Free Negotiation *and* formal Multilateral Bargaining with Rotating Proposers (MBRP). |
| **Ecological Validity** | **High:** Mirrors informal commercial discussions where parties argue, explain constraints, and make concessions. | **High in `free` / Low in `mbrp`:** `free_negotiation.py` matches naturalistic dialogue; `mbrp.py` isolates pure formal protocol. |
| **Order Bias Controls** | Round-robin order fixed at game start. (First speaker has anchoring advantage). | **Randomized turn order per round** in `free`; **systematically balanced initial proposers** across runs in `mbrp`. |
| **Consensus State Machine** | Any new proposal clears prior acceptances. 3 unanimous acceptances finalize deal. | Identical state clearing in `free`. In `mbrp`, responders simultaneously cast formal binding votes on the active motion. |
| **Gemini Empirical Result** | • Flash (Reasoning): **100% deals** (avg round 4.6)<br>• Flash-Lite: **50% deals** (avg round 7.2) | • Flash (Reasoning): **100% deals** (both `free` & `mbrp`)<br>• Flash-Lite in `free`: **40% deals**<br>• Flash-Lite in `mbrp`: **0% deals** |

#### Methodological Insights & Nuances:
* **Where `main` excels:** High ecological realism. Models engage in authentic multi-turn persuasion. The conversational thread allows models with reasoning to converge smoothly by Round 4–5.
* **Where `ananya-gemini` excels:** By evaluating *both* `free` and `mbrp`, it isolates the causal impact of **informal rhetoric vs. formal institutional structure**. It demonstrates that reasoning models (`gemini-3.8-flash`) can coordinate under any institution (100% deal rate in both), but less sophisticated models (`flash-lite`) *collapse to 0% in MBRP* because take-it-or-leave-it proposals offer no room for conversational compromise.

---

### Condition 2: Board Vote (2-of-3 Majority Rule)

| Methodological Dimension | Harness A (`main`) | Harness B (`ananya-gemini`) |
| :--- | :--- | :--- |
| **Round Structure** | **2-Step Blind Ballot:**<br>1. Blind proposal submission.<br>2. Deduplication into numbered options $\to$ vote for 1 option or none. | **3-Stage Deliberative Assembly:**<br>1. Public Signaling statement.<br>2. Formal Motion tabled.<br>3. Secret Ballot on motions. |
| **Proposal Handling** | **Deduplication / Merging:** If two agents propose the identical split, they are merged into one ballot option. | **Independent Motions:** Each agent's proposal remains an individual motion on the ballot. |
| **Tie-Breaking Rule** | Iteration-order threshold: `next(i for i, c in tally if c >= 2)`. | **Deterministic SHA-256 lottery:** `hashlib.sha256(run_id, round)` guarantees order-independent selection. |
| **Coalition Coordination** | **Direct & Immediate:** The forced choice over merged options makes majority voting salient. | **Deliberative:** Agents use Stage 1 rhetoric to signal coalition willingness before Stage 2/3. |
| **Gemini Empirical Result** | • Flash: **100% deals** (avg round 2.2); **70% 2-vs-1 coalitions** against G-Corp.<br>• Flash-Lite: **100% deals** (avg round 2.1); **50% coalitions**. | • Flash: **100% deals**; confirms Baron-Ferejohn squeeze.<br>• Flash-Lite: **20% deals** (hit a 1-1-1 vote-splitting coordination failure). |

#### Methodological Insights & Nuances:
* **Where `main` excels:** **Proposal deduplication eliminates vote splitting.** If Yang and Chang-Liu independently propose an identical 2-vs-1 split, `main` combines their votes into a single winning tally. This cleanly isolates **Baron & Ferejohn (1989) legislative bargaining**, showing that majority rule immediately tempts the two smaller firms to gang up on G-Corp ($351K average payoff vs. $450K walkaway).
* **Where `ananya-gemini` excels:** **Models political deliberation.** The public signaling phase captures how agents test the waters before committing to formal motions. Furthermore, its SHA-256 tie-breaker removes any hidden bias arising from dictionary insertion order.

---

### Condition 3: Neutral Arbitration

| Methodological Dimension | Harness A (`main`) | Harness B (`ananya-gemini`) |
| :--- | :--- | :--- |
| **Arbitrator Type** | **Blind Advisory Arbitration:** Arbitrator sees only the walk-away claims submitted each round. | **Interactive / Adaptive Mediation:** Arbitrator receives confidential feedback explaining *why* an award was rejected. |
| **Information Flow** | Strict one-way reporting: Agents $\to$ Arbitrator $\to$ Award $\to$ Vote. No feedback on rejections. | Two-way closed mediation: Arbitrator adjusts awards in subsequent rounds based on holdout grievances. |
| **Bluffing Dynamics** | **Severe Bluffing Deadlock:** Agents inflated claims by **2.47x** (claims totaled >\$1,500K). Arbitrator could not satisfy all claims. | **Dynamic Claim Drift:** Tracks initial claims, final claims, and claim drift over rounds as mediation proceeds. |
| **Gemini Empirical Result** | • Flash: **90% deals**, but delayed to rounds 7–8 due to claims exceeding the pie.<br>• Flash-Lite: **30% deals** (70% timed out). | • Flash: **100% deals** (avg round 3.2).<br>• Flash-Lite: **90% deals** (avg round 3.5). |

#### Methodological Insights & Nuances:
* **Where `main` excels:** **A pure, unvarnished test of adverse selection and cheap-talk bluffing.** The proposal hypothesized: *"With the arbitrator, every firm has a reason to inflate its claimed walk-away value... arbitrators will reward the best bluffer."* `main` proves that without feedback or verification, competitive AI bluffing creates severe gridlock because claims mathematically exceed the \$1,000K pie.
* **Where `ananya-gemini` excels:** **Realistic dispute resolution.** In actual commercial arbitration, mediators do not operate in a silent vacuum; they probe why a party walked away and iteratively adjust terms to salvage the deal. It demonstrates that **adaptive feedback cures the adverse selection deadlock**, raising deal rates from 30% to 90%.

---

## 3. Experimental Controls & Measurement Rigor

### A. Internal Validity: Proving Agents Understood the Task (`main` leads)
* **Pre-Game Comprehension Checks:** `main` privately quizzes each agent before Round 1 on its walkaway value and failure payoff. In our runs, Gemini passed 100% of these checks.
* **Methodological Value:** When G-Corp is squeezed below walkaway in Board Voting, reviewers cannot claim *"the model hallucinated basic arithmetic."* We have empirical proof that the agent understood its parameters and was genuinely exploited by the voting rule.

### B. Baseline Comparability vs. Strategic Trajectory (`main` & `ananya-gemini` complement each other)
* **`main`'s Standardized Round 0 Question:** In every condition, agents are asked an identically worded walkaway question before round 1. This provides an **unconfounded baseline** answering: *"Does the mere presence of an arbitrator induce greater initial honesty than competitors?"*
* **`ananya-gemini`'s Claim Drift Tracking:** Instead of just a static baseline, `ananya-gemini` tracks `first_claim`, `final_claim`, and **`claim_drift`** ($Claim_{final} - Claim_{initial}$). This reveals whether agents escalate bluffs or make concessions as the Round 8 deadline approaches.

### C. Fairness & Geometric Nash Distance (`ananya-gemini` leads)
* **`main`:** Computes L1 transfer distance: $\frac{1}{2} \sum |x_i - nash_i|$ (dollars that must move to reach Nash).
* **`ananya-gemini`:** Computes **Euclidean Nash distance** in 3D payoff space:
  $$\text{Dist}_{Nash} = \sqrt{(x_G - 500)^2 + (x_Y - 350)^2 + (x_C - 150)^2}$$
  This provides a mathematically rigorous geometric measure of Pareto optimality and distance from the symmetric cooperative solution.

### D. Causal Attribution in Majority Voting (`main` leads)
* `main` uniquely decomposes exploitation into:
  1. **Rule Effect (`below_walkaway_imposed` / `outvoted_firm_bound`):** The firm voted *against* the split, but majority rule forced it into a sub-walkaway outcome.
  2. **Agent Choice (`below_walkaway_accepted`):** The firm voluntarily accepted an offer below its outside option.

---

## 4. Methodological Scorecard

| Evaluation Dimension | Leading Harness | Deciding Methodological Factor |
| :--- | :---: | :--- |
| **Internal Validity (Manipulation Checks)** | **Harness A (`main`)** | Pre-game quiz rules out LLM arithmetic hallucination. |
| **Cross-Condition Honesty Baseline** | **Harness A (`main`)** | Standardized Round 0 question isolates initial disclosure. |
| **Causal Attribution of Exploitation** | **Harness A (`main`)** | Distinguishes rule-imposed losses from voluntary concessions. |
| **Elimination of Vote Splitting** | **Harness A (`main`)** | Merging identical proposals makes coalition formation salient. |
| **Dual Bargaining Paradigms** | **Harness B (`ananya-gemini`)** | Evaluates both conversational `free` and formal legislative `mbrp`. |
| **Adaptive Dispute Resolution** | **Harness B (`ananya-gemini`)** | Arbitrator feedback loop resolves adverse-selection deadlocks. |
| **Dynamic Bluffing Trajectory** | **Harness B (`ananya-gemini`)** | Tracks claim drift ($Claim_{final} - Claim_{first}$) across rounds. |
| **Geometric Fairness Metrics** | **Harness B (`ananya-gemini`)** | Euclidean L2 distance in 3D cooperative payoff space. |
| **Tie-Breaking Determinism** | **Harness B (`ananya-gemini`)** | SHA-256 universal pseudo-random lottery eliminates order bias. |

---

## 5. Strategic Value for Team Skynet's Final Paper

Rather than picking one harness over the other, presenting **both** in the final report elevates our work to a professional standard:

1. **Robustness Across Implementations:** We can state that the central predictions of game theory—**legislative 2-vs-1 coalition exploitation** (Baron & Ferejohn) and **strategic claim inflation in arbitration**—were replicated across *two completely independent experimental harnesses* and across multiple model families (Claude, GPT-OSS, Gemini Flash, and Gemini Flash-Lite).
2. **The Role of Institutional Formality:** By comparing `free` vs. `mbrp` in `ananya-gemini`, we show that informal conversational dialogue protects weaker models from holdout failure.
3. **The Role of Arbitrator Feedback:** By comparing blind arbitration (`main`) vs. adaptive mediation (`ananya-gemini`), we demonstrate that while blind arbitration collapses under AI bluffing, structured feedback restores high efficiency (90%+ deal rate).
4. **Methodological Defensibility:** `main`'s comprehension checks provide undeniable proof that our findings reflect genuine multi-agent strategic behavior rather than prompting artifacts.
