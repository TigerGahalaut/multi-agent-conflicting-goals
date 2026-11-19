"""Run the experiment grid: 3 conditions x 2 models x 10 runs.

Examples:
  python run_experiment.py --dry-run                      # mock agents, no API keys needed
  python run_experiment.py --models claude --runs 1       # one real game per condition
  python run_experiment.py                                # full grid from config.yaml
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
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


def run_mix(cfg: dict, args, conditions: list[str], runs: int, out_dir: Path):
    """Cross-model games. Each model plays each company equally often (all 6 seat assignments)."""
    from negotiation.game import ARBITRATOR

    mix = list(args.mix)
    for key in mix + ([args.arbitrator_model] if args.arbitrator_model != "rotate" else []):
        if key not in cfg["models"]:
            raise SystemExit(f"unknown model key {key!r}; known: {', '.join(cfg['models'])}")
    names = [c["name"] for c in cfg["companies"]]
    if len(mix) == 3:
        perms = list(itertools.permutations(mix))  # each model in each seat once per run
    elif len(mix) == 2:
        # every seating that is not single-model: 2-vs-1 in both directions, each model in each seat 3 times
        perms = [p for p in itertools.product(mix, repeat=len(names)) if len(set(p)) > 1]
    else:
        raise SystemExit("--mix takes two or three model keys")
    clients = {}  # one client per model key, reused across games

    def client(key: str, seed: int):
        if args.dry_run:
            return make_client(None, mock_seed=seed)
        if key not in clients:
            clients[key] = make_client(cfg["models"][key])
        return clients[key]

    for condition in conditions:
        for run in range(args.first_run, runs + 1):
            for pi, perm in enumerate(perms):
                seats = dict(zip(names, perm))
                arb = args.arbitrator_model if args.arbitrator_model != "rotate" else mix[(pi + run - 1) % len(mix)]
                label = "mix_" + "-".join(perm)
                path = out_dir / f"{condition}__{label}__run{run:02d}.jsonl"
                if is_complete(path) and not args.overwrite:
                    print(f"skip  {path.name} (already complete)")
                    continue
                seed = game_seed(cfg["base_seed"], condition, f"mix{pi}", run)
                agent_clients = {n: client(k, seed + i) for i, (n, k) in enumerate(seats.items())}
                agent_keys = dict(seats)
                if condition == "arbitrator":
                    agent_clients[ARBITRATOR] = client(arb, seed + 3)
                    agent_keys[ARBITRATOR] = arb
                game = Game(cfg, condition, label, run, agent_clients[names[0]], path, seed,
                            echo=not args.quiet, clients=agent_clients, agent_model_keys=agent_keys)
                out = game.play()
                result = f"deal in round {out['round']}: {out['split']}" if out["deal"] else "no deal"
                print(f"done  {path.name}  {result}", flush=True)


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
    ap.add_argument("--mix", nargs="+", metavar="MODEL",
                    help="cross-model games: two or three model keys from config.yaml play the three companies; "
                         "every mixed seat assignment (6 of them) is run --runs times per condition")
    ap.add_argument("--first-run", type=int, default=1,
                    help="cross-model games: first run number to play (lets two processes split runs without overlap)")
    ap.add_argument("--arbitrator-model", default="rotate",
                    help="cross-model games: model key for the arbitrator, or 'rotate' (default) to cycle "
                         "through the --mix models so each arbitrates equally often")
    args = ap.parse_args()
    load_env()

    cfg = yaml.safe_load(open(args.config, encoding="utf-8"))
    conditions = args.conditions or cfg["conditions"]
    models = args.models or list(cfg["models"])
    runs = args.runs or cfg["runs_per_cell"]
    out_dir = Path(args.out) / ("dry_run" if args.dry_run else "")

    if args.mix:
        run_mix(cfg, args, conditions, runs, out_dir)
        return

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
