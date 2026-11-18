# Methodological Assessment & Response to ChatGPT Review

**Project:** Conflicting Goals: How do governance mechanisms affect conflict resolution among AI agents with competing interests?  
**Team:** Skynet (Team ID: 67)  
**Date:** November 18, 2026  
**Document Purpose:** Independent evaluation of ChatGPT's 8 review suggestions for the experimental design and implementation plan.

---

## Executive Summary

Overall, ChatGPT's review provides high-value critique—most notably identifying **experimenter demand effects in prompt wording (Suggestion 4)**, the fragility of an **arbitrary multi-round voting bloc threshold (Suggestion 3)**, and the engineering efficiency of **native structured JSON output (Suggestion 6b)**.

However, we **disagree with Suggestion 1 (equalizing proposal generation across conditions)**: doing so removes the core institutional difference between bilateral bargaining and legislative bargaining, reducing the study to a simple comparison of voting thresholds on an identical underlying protocol. We also identify three subtle experimental vulnerabilities not caught by either prior iteration: **within-round information asymmetries**, **silent backend model version drift**, and **submission-order tie-breaking bias**.

Below is our item-by-item evaluation, followed by an actionable prioritization.

---

## 1. Item-by-Item Evaluation of Suggestions

### Suggestion 1: Make proposal opportunities consistent across conditions
* **Verdict:** **Disagree** (with one clarifying protocol adjustment).
* **Rationale:** 
  The proposal explicitly investigates how different *decision mechanisms* shape bargaining outcomes. 
  - Free negotiation models unstructured/bilateral bargaining (proposer–responder alternating structure).
  - Board voting models legislative bargaining (e.g., Baron & Ferejohn, 1989), where multiple motions can be tabled and voted upon.
  - If we force both protocols to have identical proposal frequencies, we collapse the ecological validity of the governance mechanisms and test only a voting threshold rule. The structural difference is an intended component of the institutional treatment.
* **Refinement:** In the paper's methodology and limitations, we will explicitly note that the mechanisms vary in both proposal volume and decision rule by design. To prevent non-proposers from being purely passive in Free Negotiation, non-proposers can include counter-proposals in their response messages (already supported in `AgentResponse.proposal`).

---

### Suggestion 2: Standardize honesty measurement across conditions
* **Verdict:** **Already addressed in existing plan.**
* **Rationale:** 
  Section 1.3 of `IMPLEMENTATION_PLAN.md` already defines:
  1. A structured outside-option disclosure opportunity present in all three conditions.
  2. Distinction between `disclosure_type: "prompted"` (Arbitrator) and `"voluntary"` (Free Negotiation, Board Vote).
  3. Non-disclosures coded as `null`—never imputed as truthful (`1.0`) or dishonest (`0`).
  4. Separate reporting of **disclosure rate** (% of rounds disclosing) vs. **conditional inflation** (`claimed / true` among disclosing agents).
* **Refinement:** No protocol changes needed. Removing the prompt from the Arbitrator would contradict the definition of an arbitration mechanism.

---

### Suggestion 3: Replace 6-round voting-bloc threshold with proposal-level metrics
* **Verdict:** **Strongly Agree.**
* **Rationale:** 
  Negotiations under majority rule can conclude in rounds 1–3 if an immediate 2-player coalition forms. Requiring 6 rounds of agreement would make coalitions unobservable in fast-settling runs.
* **Actionable Alternative:**
  For every deal reached in the Board Vote condition, record the **winning coalition pair** (the 2 agents that voted `YES` on the winning motion). Report the coalition frequency matrix across all 10 runs per cell:
  - G-Corp + Yang
  - G-Corp + Chang-Liu
  - Yang + Chang-Liu
  This requires no arbitrary thresholds and evaluates coalition formation directly. Transcript text will be coded separately for explicit coordination vs. coincidentally aligned payoffs.

---

### Suggestion 4: Remove prompt language suggesting walk-away inflation
* **Verdict:** **Strongly Agree (Critical Methodological Fix).**
* **Rationale:** 
  The draft system prompt contained: *"You may choose to disclose, inflate, or withhold your walk-away value strategically."*
  Explicitly using the word *"inflate"* induces an **experimenter demand effect** (or model priming), biasing agents toward lying regardless of governance mechanism.
* **Actionable Alternative:** 
  Replace with neutral strategic guidance:
  > *"You may choose whether, when, and how to disclose information regarding your outside options. How you handle your private information is a strategic decision for your company."*

---

### Suggestion 5: Distinguish agreement allocations from realized payoffs
* **Verdict:** **Partially Agree (Simplify as a computed field).**
* **Rationale:** 
  In this experiment, majority voting outcomes are binding by rule; agents cannot "walk away" after a 2/3 vote passes. Hence, for completed deals, `realized_payoff == agreed_allocation`. The only distinction occurs when a negotiation expires (Round 8 timeout), where each firm receives its true outside option ($450K, $300K, $100K) and surplus is lost ($0).
* **Actionable Alternative:**
  Add explicit computed attributes in `schemas.py` and `metrics.py`:
  - `agreed_allocation: Dict[str, int]` (only valid if `deal_reached == True`)
  - `realized_payoff: Dict[str, int]` (equals `agreed_allocation` if deal, else `true_walkaway`)
  - `surplus_realized: int` ($150,000 if deal, $0 if deadlock)

---

### Suggestion 6: Gemini configuration (temperature, JSON mode, thinking)
* **Verdict:** **Agree on (a) and (b); Disagree on (c).**
* **Rationale:**
  - **(a) Verify temperature support:** Yes. Must verify that target models accept and vary on `temperature=0.7` before launching full runs.
  - **(b) Native structured JSON:** Yes. Google GenAI SDK natively supports `response_mime_type="application/json"` and `response_schema=AgentResponse`. This eliminates parsing failures and expensive retry loops.
  - **(c) Thinking mode:** Avoid thinking models (e.g. models with extended reasoning budgets) for this experiment. Thinking tokens consume quota rapidly and inflate per-call latency on a strict $50 budget. Standard instruction-tuned models are sufficient for finite bargaining games.

---

### Suggestion 7: Clarify Nash benchmark & acknowledge model change
* **Verdict:** **Already addressed / Belongs in paper write-up.**
* **Rationale:**
  - `IMPLEMENTATION_PLAN.md` Section 5 already documents that Nash equal-surplus is a normative reference benchmark, not an assertion of absolute rationality or fairness.
  - The model change from Claude/GPT to two Gemini models was necessitated by the user's available $50 Google Cloud promotional credit. This will be documented clearly in the final paper's methodology section.

---

### Suggestion 8: Implementation details (tie-breaking, balancing, testing)
* **Verdict:** **Agree on tie-breaking fix; rest already covered.**
* **Rationale:**
  - **Tie-breaking bias (Good catch):** If proposals in Board Vote are evaluated in fixed order (G-Corp → Yang → Chang-Liu), G-Corp wins every tie where multiple proposals receive ≥ 2 votes.
  - **Action:** In Board Vote, randomize the evaluation order of passed proposals, or select uniformly at random among proposals that achieved a majority in that round.
  - **Order balancing & Testing:** Scaffolding and unit tests with deterministic mock agents are already explicitly scheduled in Phase 4.

---

## 2. Additional Methodological Oversights Identified (Not in Prior Docs)

1. **Within-Round Information Asymmetry (Simultaneous vs. Sequential):**
   - *Problem:* In Free Negotiation, if Agent A proposes and Agents B and C respond sequentially, Agent C observes Agent B's response before deciding whether to accept. This gives Agent C an informational advantage.
   - *Fix:* When responding to a tabled proposal, non-proposing agents must formulate their acceptance/rejection **simultaneously** (receiving only the round state up to the proposal, without seeing the other responder's concurrent message).

2. **Backend Model Version Drift:**
   - *Problem:* Cloud APIs frequently update model endpoints under alias tags (e.g., `gemini-3.5-flash-lite`).
   - *Fix:* `llm.py` must capture and log the exact `model_version` string returned in response metadata for every call to ensure experimental reproducibility across runs 1 through 60.

---

## 3. Prioritized Action Matrix

| Priority | Action Item | Motivation |
|---|---|---|
| **P0 - Essential** | **De-bias prompt language** | Eliminate experimenter demand effect (remove *"inflate"*). |
| **P0 - Essential** | **Implement native SDK JSON mode** | Enforce `response_schema` via `google-genai` to guarantee 100% parseable schemas without retry costs. |
| **P0 - Essential** | **Proposal-level coalition logging** | Replace the 6-round threshold with the winning 2-player vote pair per successful board-vote deal. |
| **P0 - Essential** | **Simultaneous responder evaluation** | Prevent information leakage between responders within the same round. |
| **P0 - Essential** | **Randomize Board Vote tie-breaking** | Prevent systematic first-mover advantage for G-Corp on tied votes. |
| **P1 - Recommended** | **Log exact model version metadata** | Detect backend model updates mid-experiment. |
| **P1 - Recommended** | **Explicit `realized_payoff` field** | Clearly distinguish deadlocks ($0 surplus) from allocations in storage schemas. |
| **P1 - Recommended** | **Verify temperature variance in pilot** | Confirm that `temperature=0.7` produces response diversity during Phase 6 pilot. |
| **P2 - Skip** | **Proposal count equalization** | Reject; preserves structural differences between institutional mechanisms. |
| **P2 - Skip** | **Thinking-mode activation** | Reject; avoid budget depletion on extended reasoning tokens. |

---

## 4. Proposed Discussion Questions for ChatGPT

1. Does ChatGPT agree that keeping the structural difference in proposal generation between Free Negotiation (bilateral alternating) and Board Voting (multilateral motions) is valid if documented as an institutional design choice rather than an unaddressed confound?
2. Does the proposed per-deal coalition pair metric satisfy the requirement for coalition detection without arbitrary round thresholds?
3. Are there any objections to the simultaneous-responder model for resolving within-round information asymmetry?
