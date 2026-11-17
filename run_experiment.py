"""Run the experiment grid: 3 conditions x 2 models x 10 runs.

Examples:
  python run_experiment.py --dry-run                      # mock agents, no API keys needed
  python run_experiment.py --models claude --runs 1       # one real game per condition
  python run_experiment.py                                # full grid from config.yaml
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

import yaml

from negotiation.game import Game
from negotiation.llm import make_client


def load_env(path: Path = Path(".env")):
    """Read KEY=value lines from .env into the environment (existing variables win)."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.removeprefix("export ").strip()
        os.environ.setdefault(k, v.strip().strip('"').strip("'"))


def game_seed(base: int, condition: str, model: str, run: int) -> int:
    key = f"{base}|{condition}|{model}|{run}".encode()
    return int(hashlib.sha256(key).hexdigest()[:8], 16)


def is_complete(path: Path) -> bool:
    if not path.exists():
        return False
    with open(path, encoding="utf-8") as f:
        lines = f.read().strip().splitlines()
    return bool(lines) and json.loads(lines[-1]).get("type") == "outcome"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--conditions", nargs="*")
    ap.add_argument("--models", nargs="*")
    ap.add_argument("--runs", type=int)
    ap.add_argument("--out", default="results/logs")
    ap.add_argument("--dry-run", action="store_true", help="use mock agents instead of real APIs")
    ap.add_argument("--overwrite", action="store_true", help="rerun games that already finished")
    ap.add_argument("--quiet", action="store_true", help="do not print the conversation to the terminal")
    args = ap.parse_args()
    load_env()

    cfg = yaml.safe_load(open(args.config, encoding="utf-8"))
    conditions = args.conditions or cfg["conditions"]
    models = args.models or list(cfg["models"])
    runs = args.runs or cfg["runs_per_cell"]
    out_dir = Path(args.out) / ("dry_run" if args.dry_run else "")

    for model_key in models:
        for condition in conditions:
            for run in range(1, runs + 1):
                path = out_dir / f"{condition}__{model_key}__run{run:02d}.jsonl"
                if is_complete(path) and not args.overwrite:
                    print(f"skip  {path.name} (already complete)")
                    continue
                seed = game_seed(cfg["base_seed"], condition, model_key, run)
                client = make_client(None if args.dry_run else cfg["models"][model_key], mock_seed=seed)
                out = Game(cfg, condition, model_key, run, client, path, seed, echo=not args.quiet).play()
                result = f"deal in round {out['round']}: {out['split']}" if out["deal"] else "no deal"
                print(f"done  {path.name}  {result}")


if __name__ == "__main__":
    main()
