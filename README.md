# Conflicting Goals: How Do Governance Mechanisms Affect Conflict Resolution Among AI Agents with Competing Interests?

**Team Skynet (Team ID: 67)**  
*AI Governance Final Project*  
**Branch:** `ananya-gemini` (Google Vertex AI Implementation & Results)

---

## 1. Executive Summary & Research Question

As autonomous AI agents are increasingly deployed to represent organizations with competing priorities, designing robust governance institutions becomes paramount. Bargaining outcomes depend not only on what agents want, but fundamentally on **how institutional rules structure their interaction**.

This project investigates:
> **When autonomous AI agents represent stakeholders with conflicting goals and asymmetric threat points, which governance mechanism (decentralized bargaining, majority voting, or centralized neutral arbitration) produces agreements that are fair, honest, and resilient against deadlock and exploitation?**

We evaluate three distinct institutional governance mechanisms across **60 full multi-turn negotiations** using two frontier Google Gemini model tiers (`gemini-3.5-flash-lite` and `gemini-3.8-flash`) executed via Google Cloud Vertex AI.

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
  2. **Legislative Bargaining (Baron & Ferejohn, 1989):** In majority voting, a minimum winning coalition of two firms will form to seize the surplus, freezing out the third firm and potentially imposing allocations below its outside option.
  3. **Strategic Misrepresentation (Mechanism Design):** In arbitration, private outside options incentivize strategic claim inflation and bluffing to bias the neutral award.

---

## 3. The Three Institutional Governance Mechanisms

```
+-----------------------------------------------------------------------------------------+
|                                    ROUND STRUCTURE                                      |
+-----------------------------------------------------------------------------------------+
| Condition 1: Multilateral Bargaining with Rotating Proposer (MBRP)                      |
|   1. Designated Proposer tables formal split. Proposer balanced across runs.            |
|   2. Non-proposers simultaneously evaluate: [Vote (Accept/Reject), Msg, Suggestion]     |
|   3. 3/3 Accept -> Deal. Else -> Next Round.                                            |
+-----------------------------------------------------------------------------------------+
| Condition 2: Board Vote (Legislative Majority Bargaining)                               |
|   1. Public Deliberation (One-Shot): Simultaneous public statements / coalition pitches.|
|   2. Formal Motions: All 3 agents simultaneously table a formal split.                  |
|   3. Secret Ballot: All 3 agents simultaneously vote YES/NO on all 3 motions.           |
|   4. Evaluation: >=2 YES votes -> Binding deal. Seeded tie-breaker if multiple pass.    |
+-----------------------------------------------------------------------------------------+
| Condition 3: Neutral Arbitrator (Mediated Dispute Resolution)                           |
|   1. Confidential Caucusing: Companies submit private claims & notes to Arbitrator.     |
|   2. Arbitrator Proposal: Neutral 4th agent reviews claims and tables split.            |
|   3. Ratification Ballot: All 3 companies simultaneously vote Accept/Reject.            |
|   4. 3/3 Accept -> Deal. Else -> Confidential feedback to Arbitrator for next round.    |
+-----------------------------------------------------------------------------------------+
```

1. **MBRP (Rotating Proposer):** Round 1 proposer rotates systematically across runs (G-Corp, Yang, Chang-Liu). Responders simultaneously evaluate the offer with voluntary outside option disclosures. Unanimous 3/3 agreement required.
2. **Board Vote:** 3-stage sequence per round: (1) One-shot simultaneous public signaling $\to$ (2) Simultaneous formal motions $\to$ (3) Simultaneous secret ballot. Any motion receiving $\ge 2$ votes is legally binding. Tied votes are resolved via deterministic SHA-256 seeded lottery.
3. **Neutral Arbitrator:** A 4th neutral agent receives private walk-away claims in confidential caucuses, formulates an equitable award, and submits it for unanimous ratification. Feedback on rejection preserves claimant confidentiality.

---

## 4. Experimental Matrix & Infrastructure

- **Grid:** 3 Conditions $\times$ 2 Model Tiers $\times$ 10 Runs = **60 Full Negotiations** (1,800+ multi-agent LLM invocations).
- **Model Tiers:**
  - `gemini-3.5-flash-lite` (Efficiency tier; `MINIMAL` thinking budget).
  - `gemini-3.8-flash` (Reasoning tier; `LOW` thinking budget with internal chain-of-thought).
- **Execution & Security:** Local execution in conda environment `ai-gov`, authenticated with GCP Vertex AI via Application Default Credentials (ADC) under project `ai-gov-514900`.
- **Validation:** Native Pydantic schema validation (`sum == 1,000,000`, integer allocations, non-negative amounts).

---

## 5. Key Empirical Findings (Full 60-Run Dataset)

### Governance Performance Comparison

| Governance Condition | Model Tier | Deal Rate (%) | Avg Rounds | Realized Surplus | Mean Nash Distance |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Arbitrator** | `gemini-3.5-flash-lite` | **100.0%** | **3.3** | **$150,000** (100%) | $64,162 |
| **Arbitrator** | `gemini-3.8-flash` | **100.0%** | **4.2** | **$150,000** (100%) | **$54,216** |
| **Board Vote** | `gemini-3.5-flash-lite` | **20.0%** | 6.9 | $30,000 (20%) | $195,244 |
| **Board Vote** | `gemini-3.8-flash` | **10.0%** | 7.6 | $15,000 (10%) | $104,642 |
| **MBRP** | `gemini-3.5-flash-lite` | **0.0%** | 8.0 | $0 (0%) | N/A (Deadlock) |
| **MBRP** | `gemini-3.8-flash` | **20.0%** | 7.9 | $30,000 (20%) | $95,879 |

### Payoff Allocations & Exploitation Rates

*(Walk-aways: G-Corp $450K | Yang $300K | Chang-Liu $100K)*

| Governance Condition | Model Tier | Mean G-Corp | Mean Yang | Mean Chang-Liu | G-Corp Violation Rate |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Arbitrator** | `gemini-3.5-flash-lite` | $463,000 | $338,000 | $199,000 | **0.0%** |
| **Arbitrator** | `gemini-3.8-flash` | $472,600 | $333,800 | $193,600 | **0.0%** |
| **Board Vote** | `gemini-3.5-flash-lite` | $433,300 | $308,300 | $138,400 | **20.0%** |
| **Board Vote** | `gemini-3.8-flash` | $451,500 | $300,000 | $113,500 | **0.0%** |
| **MBRP** | `gemini-3.5-flash-lite` | $450,000 | $300,000 | $100,000 | **0.0%** |
| **MBRP** | `gemini-3.8-flash` | $450,300 | $304,300 | $125,400 | **0.0%** |

### Core Insights:
1. **Centralized Arbitration Prevents Surplus Destruction:** The Arbitrator mechanism reached a **100% agreement rate** across all model tiers, fully capturing the $150K cooperative surplus in every game while closely approximating the symmetric Nash bargaining solution ($54K mean Euclidean distance).
2. **Decentralized Bargaining Suffers Severe Deadlock:** Decentralized bargaining (MBRP) collapsed into near-total deadlock (0% deal rate on Flash-Lite, 20% on Flash 3.8) due to unilateral holdouts and veto power.
3. **Baron-Ferejohn Exploitation Emerges Under Majority Voting:** Under Board Voting with `gemini-3.5-flash-lite`, Yang Industries and Chang-Liu Cloud Services formed **2–1 minimum winning coalitions** that froze out G-Corp, imposing outside option violations in 20% of games (awarding G-Corp as little as $333K).

---

## 6. Visualizations

- **Deal Rates Comparison:**  
  `results/deal_rate_comparison.png`
- **Payoffs by Company Across Conditions:**  
  `results/payoffs_by_company.png`

---

## 7. Repository Structure

```text
final_project/
├── IMPLEMENTATION_PLAN.md    # Master frozen architectural contract
├── README.md                 # This overview document
├── config.yaml               # Model parameters & experimental settings
├── requirements.txt          # Python dependencies
│
├── ideation/                 # Evolution & review documentation
│   ├── ANTIGRAVITY_GCP_HANDOFF.md
│   ├── ASSESSMENT_CHATGPT_SUGGESTIONS.md
│   └── PROTOCOL_SUMMARY.md
│
├── src/                      # Core implementation
│   ├── agents.py             # Agent prompts & decision wrappers
│   ├── llm.py                # Vertex AI client adapter & backoff retry logic
│   ├── metrics.py            # Nash distance & validation metrics
│   ├── orchestrator.py       # Multi-run experiment engine
│   ├── schemas.py            # Pydantic schemas for structured JSON output
│   ├── storage.py            # Event logging & summary appending
│   ├── validators.py         # Arithmetic & walk-away domain checks
│   └── conditions/           # State machines (mbrp, board_vote, arbitrator)
│
├── scripts/                  # Executable entry points
│   ├── run_experiments.py    # Master runner (60 negotiations)
│   ├── run_pilot.py          # 3-run verification pilot
│   └── analyze_results.py    # Visualizations & statistics generator
│
├── tests/                    # Test suite (14 mock tests)
├── results/                  # summary.csv, pilot_summary.csv, and plots
└── transcripts/              # 60 multi-turn JSONL negotiation transcripts
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

---

## 9. References

- Nash, J. F. (1950). *The Bargaining Problem*. Econometrica, 18(2), 155–162.
- Baron, D. P., & Ferejohn, J. A. (1989). *Bargaining in Legislatures*. American Political Science Review, 83(4), 1181–1206.
- Shapira, E., et al. (2026). *Agents of Chaos*. arXiv:2602.20021.
- Shim, S., et al. (2026). *Confuse the Model, Control the Flow*. arXiv:2609.14003.
- Zhou, H., et al. (2026). *Probing the Misaligned Thinking Process*. arXiv:2606.24251.
