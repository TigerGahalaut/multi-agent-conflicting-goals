# Conflicting Goals: Multi-Agent Governance Experiment

Study on how governance mechanisms affect conflict resolution, honesty, and coalition formation among AI agents with competing interests.

## Setup & Running

1. **Environment:**
   Activate conda environment `ai-gov`:
   ```powershell
   conda activate ai-gov
   ```

2. **Authenticate with GCP (ADC):**
   ```powershell
   gcloud auth application-default login
   gcloud auth application-default set-quota-project ai-gov-514900
   ```

3. **Run Unit Tests (Zero API cost):**
   ```powershell
   pytest tests/
   ```

4. **Run Pilots (Cost Verification):**
   ```powershell
   python scripts/run_pilot.py
   ```

5. **Run Master Experiment (60 runs):**
   ```powershell
   python scripts/run_experiments.py
   ```
