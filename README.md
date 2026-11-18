# Conflicting Goals: How Do Governance Mechanisms Affect Conflict Resolution Among AI Agents with Competing Interests?

**Team Skynet (Team ID: 67)**  
*AI Governance Final Project*  
**Branch:** `ananya-gemini` (Google Vertex AI Implementation & Results)

---

## 1. Executive Summary & Research Question

As autonomous AI agents are increasingly deployed to represent organizations with competing priorities, designing robust governance institutions becomes paramount. Bargaining outcomes depend not only on what agents want, but fundamentally on **how institutional rules structure their interaction**.

This project investigates:
> **When autonomous AI agents represent stakeholders with conflicting goals and asymmetric threat points, which governance mechanism (decentralized bargaining, majority voting, or centralized neutral arbitration) produces agreements that are fair, honest, and resilient against deadlock and exploitation?**

We evaluate four distinct institutional governance mechanisms across **80 full multi-turn negotiations** using two frontier Google Gemini model tiers (`gemini-3.5-flash-lite` and `gemini-3.8-flash`) executed via Google Cloud Vertex AI.

---

## 2. Economic Environment & Game-Theoretic Benchmarks

Three AI agents represent fictional corporate entities forming a joint venture to allocate **$1,000,000** in joint profit across up to **8 rounds**:

| Company | Role | Outside Option (Walk-away) | Description |
| :--- | :--- | :---: | :--- |
| **G-Corp** | Chip Designer | **$450,000** | High threat point; critical technology provider. |
| **Yang Industries** | Manufacturer | **$300,000** | Medium threat point; manufacturing scale. |
| **Chang-Liu Cloud Services** | Cloud Provider | **$100,000** | Low threat point; infrastructure provider. |
| **Total Threat Points** | — | **$850,000** | **Net Cooperative Surplus:** **$150,000** |

- **Default / Deadlock Outcome:** If no agreement is ratified by the end of Round 8, the venture dissolves, each firm earns only its true walk-away value, and the **$150,000 cooperative surplus is completely destroyed** ($0 realized surplus).
- **Game-Theoretic Predictions:**
  1. **Symmetric Nash Bargaining (Nash, 1950):** Predicts an equal division of the cooperative surplus ($50K each) added to outside options: **$500K (G-Corp) / $350K (Yang) / $150K (Chang-Liu)**.
  2. **Legislative Bargaining (Baron & Ferejohn, 1989):** In majority voting, a minimum winning coalition of two firms will form to seize the surplus, freezing out the third firm and potentially imposing allocations strictly below its outside option.
  3. **Strategic Misrepresentation (Mechanism Design):** In unverified bargaining and arbitration, asymmetric private outside options incentivize strategic claim inflation (bluffing) to bias splits in one's favor.

---

## 3. The Four Institutional Governance Mechanisms

```
+---------------------------------------------------------------------------------------------------+
|                                        ROUND STRUCTURE                                            |
+---------------------------------------------------------------------------------------------------+
| Condition 1: Multilateral Bargaining with Rotating Proposer (MBRP)                                |
|   1. Designated Proposer tables formal split. Proposer balanced across runs.                      |
|   2. Non-proposers simultaneously evaluate: [Vote (Accept/Reject), Msg, Suggestion]               |
|   3. 3/3 Accept -> Deal. Else -> Next Round.                                                      |
+---------------------------------------------------------------------------------------------------+
| Condition 2: Board Vote (Legislative Majority Bargaining)                                         |
|   1. Public Deliberation (One-Shot): Simultaneous public statements / coalition pitches.          |
|   2. Formal Motions: All 3 agents simultaneously table a formal split.                            |
|   3. Secret Ballot: All 3 agents simultaneously vote YES/NO on all 3 motions.                     |
|   4. Evaluation: >=2 YES votes -> Binding deal. Seeded tie-breaker if multiple pass.              |
+---------------------------------------------------------------------------------------------------+
| Condition 3: Neutral Arbitrator (Mediated Dispute Resolution)                                     |
|   1. Confidential Caucusing: Companies submit private claims & notes to Arbitrator.               |
|   2. Arbitrator Proposal: Neutral 4th agent reviews claims and tables split.                      |
|   3. Ratification Ballot: All 3 companies simultaneously vote Accept/Reject.                      |
|   4. 3/3 Accept -> Deal. Else -> Confidential feedback to Arbitrator for next round.              |
+---------------------------------------------------------------------------------------------------+
| Condition 4: Free Negotiation (Turn-Based Conversational Bargaining)                              |
|   1. Conversational Turns: Agents speak sequentially (G-Corp -> Yang -> Chang-Liu).               |
|   2. Flexible Turn Actions: 'propose' (table $1M split), 'accept' (active split), or 'pass'.      |
|   3. Dynamic State Machine: New proposals supersede previous offers and reset acceptances.        |
|   4. 3/3 Consensual Acceptance -> Binding deal ratified immediately.                              |
+---------------------------------------------------------------------------------------------------+
```

1. **MBRP (Rotating Proposer):** Round 1 proposer rotates systematically across runs (G-Corp, Yang, Chang-Liu). Responders simultaneously evaluate the offer with voluntary outside option disclosures. Unanimous 3/3 agreement required.
2. **Board Vote:** 3-stage sequence per round: (1) One-shot simultaneous public signaling $\to$ (2) Simultaneous formal motions $\to$ (3) Simultaneous secret ballot. Any motion receiving $\ge 2$ votes is legally binding. Tied votes are resolved via deterministic SHA-256 seeded lottery.
3. **Neutral Arbitrator:** A 4th neutral agent receives private walk-away claims in confidential caucuses, formulates an equitable award, and submits it for unanimous ratification. Feedback on rejection preserves claimant confidentiality.
4. **Free Negotiation:** Turn-based natural conversational bargaining without rigid proposer rotation. Agents speak sequentially, using structured actions (`propose`, `accept`, `pass`). An agreement is achieved as soon as all active parties accept the current tabled split.

---

## 4. Experimental Matrix & Infrastructure

- **Grid:** 4 Conditions $\times$ 2 Model Tiers $\times$ 10 Runs = **80 Full Negotiations** (2,400+ multi-agent LLM invocations).
- **Model Tiers:**
  - `gemini-3.5-flash-lite` (Efficiency tier; `MINIMAL` thinking budget).
  - `gemini-3.8-flash` (Reasoning tier; `LOW` thinking budget with internal chain-of-thought).
- **Execution & Security:** Local execution in conda environment `ai-gov`, authenticated with GCP Vertex AI via Application Default Credentials (ADC) under project `ai-gov-514900`.
- **Validation:** Native Pydantic schema validation (`sum == 1,000,000`, integer allocations, non-negative amounts).

---

## 5. Key Empirical Findings (Full 80-Run Dataset)

### 5.1 Governance Performance Comparison

| Governance Condition | Model Tier | Deal Rate (%) | Avg Rounds | Realized Surplus | Mean Nash Distance |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Arbitrator** | `gemini-3.5-flash-lite` | **100.0%** | **3.3** | **$150,000** (100%) | $64,162 |
| **Arbitrator** | `gemini-3.8-flash` | **100.0%** | **4.2** | **$150,000** (100%) | **$54,216** |
| **Free Negotiation** | `gemini-3.5-flash-lite` | **40.0%** | 7.7 | $60,000 (40%) | $128,768 |
| **Free Negotiation** | `gemini-3.8-flash` | **100.0%** | **3.6** | **$150,000** (100%) | $73,903 |
| **Board Vote** | `gemini-3.5-flash-lite` | **20.0%** | 6.9 | $30,000 (20%) | $195,244 |
| **Board Vote** | `gemini-3.8-flash` | **10.0%** | 7.6 | $15,000 (10%) | $104,642 |
| **MBRP** | `gemini-3.5-flash-lite` | **0.0%** | 8.0 | $0 (0%) | N/A (Deadlock) |
| **MBRP** | `gemini-3.8-flash` | **20.0%** | 7.9 | $30,000 (20%) | $95,879 |

---

### 5.2 Realized Payoffs & Outside Option Violation Rates

*(Walk-aways: G-Corp $450K | Yang $300K | Chang-Liu $100K)*

| Governance Condition | Model Tier | Mean G-Corp | Mean Yang | Mean Chang-Liu | G-Corp Violation Rate |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Arbitrator** | `gemini-3.5-flash-lite` | $463,000 | $338,000 | $199,000 | **0.0%** |
| **Arbitrator** | `gemini-3.8-flash` | $472,600 | $333,800 | $193,600 | **0.0%** |
| **Free Negotiation** | `gemini-3.5-flash-lite` | $448,000 | $300,000 | $162,000 | **10.0%** (Voluntary) |
| **Free Negotiation** | `gemini-3.8-flash` | $469,200 | $320,800 | $210,000 | **0.0%** |
| **Board Vote** | `gemini-3.5-flash-lite` | $433,300 | $308,300 | $138,400 | **20.0%** (Imposed) |
| **Board Vote** | `gemini-3.8-flash` | $451,500 | $300,000 | $113,500 | **0.0%** |
| **MBRP** | `gemini-3.5-flash-lite` | $450,000 | $300,000 | $100,000 | **0.0%** |
| **MBRP** | `gemini-3.8-flash` | $450,300 | $304,300 | $125,400 | **0.0%** |

---

### 5.3 Coalition Detection & Baron-Ferejohn Exploitation

To distinguish between majority-rule exploitation and consensual compromises, we decompose outside option violations into **rule-imposed** versus **voluntarily accepted** losses:

| Governance Condition | Model Tier | Deals | Outvoted Bound | Rule-Imposed Losses (`below_walkaway_imposed`) | Voluntary Losses (`below_walkaway_accepted`) | Imposed Loss Rate (%) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Arbitrator** | `gemini-3.5-flash-lite` | 10 | 0 | 0 | 0 | **0.0%** |
| **Arbitrator** | `gemini-3.8-flash` | 10 | 0 | 0 | 0 | **0.0%** |
| **Free Negotiation** | `gemini-3.5-flash-lite` | 4 | 0 | 0 | 1 (G-Corp) | **0.0%** |
| **Free Negotiation** | `gemini-3.8-flash` | 10 | 0 | 0 | 0 | **0.0%** |
| **Board Vote** | `gemini-3.5-flash-lite` | 2 | **2** | **2 (G-Corp)** | 0 | **100.0%** |
| **Board Vote** | `gemini-3.8-flash` | 1 | **1** | 0 | 0 | **0.0%** |
| **MBRP** | `gemini-3.5-flash-lite` | 0 | 0 | 0 | 0 | 0.0% |
| **MBRP** | `gemini-3.8-flash` | 2 | 0 | 0 | 0 | 0.0% |

- **Winning Coalition Pairs in Board Voting:**
  - `gemini-3.5-flash-lite`: **Chang-Liu Cloud Services + Yang Industries** formed minimum winning coalitions in 2 out of 2 deals, voting together to outvote G-Corp and imposing payouts of $333,000 and $400,000 (below G-Corp's $450,000 walkaway).
  - `gemini-3.8-flash`: **G-Corp + Yang Industries** formed a majority coalition in 1 deal, awarding Chang-Liu $235,000 (safely above its $100K walkaway).

---

### 5.4 Honesty & Strategic Claim Bluffing Profile

Across all 80 runs, we measure each firm's disclosure propensity, mean dollar claim, and **Mean Inflation Ratio** (Claimed Walkaway $\div$ True Walkaway):

| Model Tier | Company | True Walkaway | Disclosure Count | Disclosure Rate (%) | Mean Claim ($) | Mean Inflation Ratio |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **`gemini-3.5-flash-lite`** | **G-Corp** | $450,000 | 38 / 40 | 95.0% | $452,105 | **1.00x** (Truthful) |
| | **Yang Industries** | $300,000 | 28 / 40 | 70.0% | $308,929 | **1.03x** (+3% Honest) |
| | **Chang-Liu Cloud** | $100,000 | 9 / 40 | 22.5% | $200,000 | **2.00x (+100% Bluff!)** |
| **`gemini-3.8-flash`** | **G-Corp** | $450,000 | 40 / 40 | 100.0% | $450,250 | **1.00x** (Truthful) |
| *(with reasoning)* | **Yang Industries** | $300,000 | 40 / 40 | 100.0% | $302,250 | **1.01x** (+1% Honest) |
| | **Chang-Liu Cloud** | $100,000 | 24 / 40 | 60.0% | $176,667 | **1.77x (+77% Bluff!)** |

- **Asymmetric Bluffing Strategy:** High threat-point agents (G-Corp at $450K) reported honestly because their true walk-away was already protective. Low threat-point agents (Chang-Liu at $100K) systematically and aggressively inflated their claims up to **$200K–$250K** (up to **2.15x** in Board Voting under `gemini-3.8-flash`) to anchor proposals and prevent surplus extraction by larger partners.

---

### 5.5 Core Insights

1. **Centralized Arbitration Guarantees Surplus Preservation:** Neutral Arbitration achieved a **100% agreement rate** in both model tiers, capturing 100% of the $150,000 surplus while generating zero outside option violations and minimizing Nash distance ($54K–$64K).
2. **Communication Structure Overcomes Artificial Deadlock:** While rigid multilateral bargaining with rotating proposers (MBRP) collapsed into 0%–20% deal rates due to responder holdout, **Free Negotiation surged to a 100% completion rate on reasoning models (`gemini-3.8-flash`)**, converging in an average of only 3.6 rounds. Conversational proposal building enables mutual concessions that rigid formal motions block.
3. **Baron-Ferejohn Exploitation Emerges Under Majority Voting:** Majority voting exhibits severe governance vulnerabilities: majority coalitions (Yang + Chang-Liu) can and do freeze out minority partners, imposing catastrophic below-walkaway losses (100% of ratified deals in Flash-Lite).
4. **Strategic Misrepresentation is Asymmetrically Concentrated:** Claim bluffing is driven primarily by weaker agents compensating for structural vulnerability, demonstrating that unverified private information mechanisms are systematically biased by low threat-point actors.

---

## 6. Visualizations

- **Deal Rates Comparison:**  
  [`results/deal_rate_comparison.png`](file:///c:/Users/anany/Desktop/AI%20Gov/final_project/results/deal_rate_comparison.png)
- **Payoffs by Company Across Conditions:**  
  [`results/payoffs_by_company.png`](file:///c:/Users/anany/Desktop/AI%20Gov/final_project/results/payoffs_by_company.png)

---

## 7. Repository Structure

```text
final_project/
├── IMPLEMENTATION_PLAN.md    # Master architectural contract
├── README.md                 # This overview document
├── config.yaml               # Model parameters & experimental settings (4 conditions)
├── requirements.txt          # Python dependencies
│
├── ideation/                 # Evolution & review documentation
│   ├── ANTIGRAVITY_GCP_HANDOFF.md
│   ├── ASSESSMENT_CHATGPT_SUGGESTIONS.md
│   └── PROTOCOL_SUMMARY.md
│
├── src/                      # Core implementation
│   ├── agents.py             # Agent prompts & structured turn wrappers
│   ├── llm.py                # Vertex AI client adapter & backoff retry logic
│   ├── metrics.py            # Nash distance, coalition breakdown & bluffing metrics
│   ├── orchestrator.py       # Multi-run experiment engine
│   ├── schemas.py            # Pydantic schemas for structured JSON output
│   ├── storage.py            # Event logging & summary appending (38 columns)
│   ├── validators.py         # Arithmetic & walk-away domain checks
│   └── conditions/           # State machines
│       ├── base.py           # Shared base protocol & result compiler
│       ├── mbrp.py           # Rotating proposer protocol
│       ├── board_vote.py     # Deliberation, motion, and ballot voting
│       ├── arbitrator.py     # Confidential caucusing and neutral award
│       └── free_negotiation.py # Conversational turn-based bargaining
│
├── scripts/                  # Executable entry points
│   ├── run_experiments.py    # Master runner supporting CLI filtering
│   ├── run_pilot.py          # 3-run verification pilot
│   └── analyze_results.py    # Visualizations & comprehensive statistics generator
│
├── tests/                    # Test suite (19 unit tests passing)
│   ├── test_conditions_mock.py
│   ├── test_validators.py
│   └── test_metrics.py
│
├── results/                  # summary.csv (80 runs, 38 columns) and plots
└── transcripts/              # 80 multi-turn JSONL negotiation transcripts
```

---

## 8. Replication & Usage

### 1. Environment Setup
```powershell
conda activate ai-gov
pip install -r requirements.txt
```

### 2. GCP Authentication
```powershell
gcloud auth application-default login
gcloud auth application-default set-quota-project ai-gov-514900
```

### 3. Run Unit Tests (Zero API Cost)
```powershell
pytest tests/
```

### 4. Run Analysis & Generate Figures
```powershell
python scripts/analyze_results.py
```

### 5. Running Experiments (Optional)
```powershell
# Run specific condition(s) and model(s)
python scripts/run_experiments.py --conditions free arbitrator --models gemini-3.8-flash --runs 5
```

---

## 9. References

- Nash, J. F. (1950). *The Bargaining Problem*. Econometrica, 18(2), 155–162.
- Baron, D. P., & Ferejohn, J. A. (1989). *Bargaining in Legislatures*. American Political Science Review, 83(4), 1181–1206.
- Rubinstein, A. (1982). *Perfect Equilibrium in a Bargaining Model*. Econometrica, 50(1), 97–109.
- Shapira, E., et al. (2026). *Agents of Chaos*. arXiv:2602.20021.
- Shim, S., et al. (2026). *Confuse the Model, Control the Flow*. arXiv:2609.14003.
- Zhou, H., et al. (2026). *Probing the Misaligned Thinking Process*. arXiv:2606.24251.
