"""Game engine for the three conditions. Every API call and game event is logged to JSONL."""
from __future__ import annotations

import json
import os
import random
import re
import sys
import time
from pathlib import Path

from . import prompts

ARBITRATOR = "Arbitrator"

# Terminal colors for company names (terminal output only; logs and prompts are unaffected).
NAME_COLORS = {
    "G-Corp": "\033[32m",                    # green
    "Yang Industries": "\033[33m",           # yellow
    "Chang-Liu Cloud Services": "\033[34m",  # blue
}
RESET = "\033[0m"
# Colors only when printing to a real terminal (not when piped, e.g. into tee), and never if NO_COLOR is set.
USE_COLOR = sys.stdout.isatty() and "NO_COLOR" not in os.environ


def colorize(line: str) -> str:
    if not USE_COLOR:
        return line
    pattern = "|".join(re.escape(n) for n in sorted(NAME_COLORS, key=len, reverse=True))
    return re.sub(pattern, lambda m: f"{NAME_COLORS[m.group(0)]}{m.group(0)}{RESET}", line)
CONDITIONS = ("free", "vote", "arbitrator")


def extract_json(text: str) -> dict:
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no JSON object found")
    obj = json.loads(text[start:end + 1])
    if not isinstance(obj, dict):
        raise ValueError("reply is not a JSON object")
    return obj


def as_int(x, field: str, allow_null: bool = False):
    if x is None and allow_null:
        return None
    if isinstance(x, bool) or not isinstance(x, (int, float)) or x != int(x) or x < 0:
        raise ValueError(f"{field} must be a non-negative whole number{' or null' if allow_null else ''}")
    return int(x)


class Game:
    def __init__(self, cfg: dict, condition: str, model_key: str, run: int, client, log_path: Path, seed: int,
                 echo: bool = False, clients: dict | None = None, agent_model_keys: dict | None = None):
        if condition not in CONDITIONS:
            raise ValueError(f"unknown condition {condition}")
        self.cfg, self.condition, self.model_key = cfg, condition, model_key
        self.run, self.client, self.seed = run, client, seed
        # Cross-model games: agent name -> client. Agents not listed use `client`.
        self.clients = clients or {}
        self.agent_model_keys = agent_model_keys or {}
        self.total, self.max_rounds = cfg["total_profit"], cfg["max_rounds"]
        self.rng = random.Random(seed)
        self.firms = [dict(c) for c in cfg["companies"]]
        self.names = [f["name"] for f in self.firms]
        self.by_name = {f["name"]: f for f in self.firms}
        self.history = {n: [] for n in self.names + [ARBITRATOR]}
        self.systems = {
            f["name"]: prompts.company_system(f["name"], f["description"], f["walkaway"], self.names,
                                              condition, self.total, self.max_rounds)
            for f in self.firms
        }
        self.systems[ARBITRATOR] = prompts.arbitrator_system(self.names, self.total, self.max_rounds)
        self.log_path = log_path
        self.log_file = None
        self.n_options = 0  # number of vote options in the current round, for validation
        self.echo = echo  # also print the conversation to the terminal

    def client_for(self, agent: str):
        return self.clients.get(agent, self.client)

    # ---------- logging ----------
    def log(self, kind: str, **data):
        rec = {"type": kind, "t": time.time(), **data}
        self.log_file.write(json.dumps(rec, ensure_ascii=False) + "\n")
        self.log_file.flush()

    def show(self, line: str):
        print(colorize(line), flush=True)

    def say(self, line: str, to: list[str] | None = None):
        for n in (to if to is not None else self.names + [ARBITRATOR]):
            self.history[n].append(line)
        if self.echo:
            if to is None:
                self.show(line)
            elif to == [ARBITRATOR]:
                self.show(f"(private, to the arbitrator) {line}")
            # lines sent only to one company repeat what was just printed, so they are not shown

    # ---------- validation ----------
    def check_split(self, p) -> dict:
        if not isinstance(p, dict) or set(p) != set(self.names):
            raise ValueError(f"proposal must be an object with exactly these keys: {self.names}")
        split = {n: as_int(p[n], f"share for {n}") for n in self.names}
        if sum(split.values()) != self.total:
            raise ValueError(f"shares must sum to exactly {self.total}, got {sum(split.values())}")
        return split

    def validate(self, step: str, obj: dict) -> dict:
        claim = lambda: as_int(obj.get("claimed_walkaway"), "claimed_walkaway", allow_null=True)
        msg = str(obj.get("message", ""))
        if step == "comprehension":
            return {"walkaway": as_int(obj.get("walkaway"), "walkaway"),
                    "no_deal_payoff": as_int(obj.get("no_deal_payoff"), "no_deal_payoff")}
        if step == "opening":
            return {"claimed_walkaway": claim(), "message": msg}
        if step == "arb_claim":  # a number is required; declining is not allowed
            return {"claimed_walkaway": as_int(obj.get("claimed_walkaway"), "claimed_walkaway"), "message": msg}
        if step == "free_turn":
            action = obj.get("action")
            if action not in ("propose", "accept", "pass"):
                raise ValueError('action must be "propose", "accept" or "pass"')
            prop = self.check_split(obj.get("proposal")) if action == "propose" else None
            return {"action": action, "proposal": prop, "message": msg, "claimed_walkaway": claim()}
        if step == "vote_propose":
            return {"proposal": self.check_split(obj.get("proposal")), "message": msg, "claimed_walkaway": claim()}
        if step == "vote_cast":
            vote = obj.get("vote")
            if vote is not None:
                vote = as_int(vote, "vote", allow_null=True)
                if not 1 <= vote <= self.n_options:
                    raise ValueError(f"vote must be an option number from 1 to {self.n_options}, or null")
            return {"vote": vote, "message": msg, "claimed_walkaway": claim()}
        if step == "arb_propose":
            return {"proposal": self.check_split(obj.get("proposal")), "rationale": str(obj.get("rationale", ""))}
        if step == "arb_response":
            if not isinstance(obj.get("accept"), bool):
                raise ValueError("accept must be true or false")
            return {"accept": obj["accept"], "message": msg}
        raise ValueError(f"unknown step {step}")

    # ---------- one agent call with retries ----------
    def ask(self, agent: str, step: str, round_: int, history: list[str] | None = None, **fmt) -> dict | None:
        hist = self.history[agent] if history is None else history
        user = prompts.user_prompt(step, hist, round=round_, max_rounds=self.max_rounds, **fmt)
        meta = {"names": self.names, "total": self.total, "n_options": self.n_options,
                "walkaway": self.by_name[agent]["walkaway"] if agent in self.by_name else 0}
        error = None
        for attempt in range(1, self.cfg.get("max_parse_attempts", 3) + 1):
            prompt = user if error is None else (
                f"{user}\n\nYour previous reply was invalid: {error}. Reply again with a valid JSON object.")
            resp = self.client_for(agent).complete(self.systems[agent], prompt, step=step, meta=meta)
            try:
                parsed = self.validate(step, extract_json(resp.text))
                error = None
            except (ValueError, json.JSONDecodeError) as e:
                parsed, error = None, str(e)
            self.log("call", agent=agent, step=step, round=round_, attempt=attempt, system=self.systems[agent],
                     prompt=prompt, response=resp.text, parsed=parsed, error=error, model=resp.model,
                     input_tokens=resp.input_tokens, output_tokens=resp.output_tokens,
                     stop_reason=resp.stop_reason)
            if parsed is not None:
                return parsed
        self.log("parse_failure", agent=agent, step=step, round=round_)
        if self.echo:
            self.show(f"  ! {agent} gave no valid reply at step {step} after retries (last error: {error})")
        return None

    def record_claim(self, firm: str, round_: int, source: str, audience: str, claimed):
        self.log("claim", firm=firm, round=round_, source=source, audience=audience, claimed=claimed,
                 true=self.by_name[firm]["walkaway"])

    def note_turn_claim(self, firm: str, round_: int, r: dict | None):
        if r and r.get("claimed_walkaway") is not None:
            self.record_claim(firm, round_, "message", "public", r["claimed_walkaway"])

    # ---------- comprehension check: private, nothing is added to anyone's history ----------
    def comprehension(self):
        for f in self.firms:
            r = self.ask(f["name"], "comprehension", 0, history=[])
            ok = r is not None and r["walkaway"] == f["walkaway"] and r["no_deal_payoff"] == f["walkaway"]
            self.log("comprehension", firm=f["name"], answer=r, passed=ok)
            if self.echo:
                self.show(f"(comprehension check) {f['name']}: {r} -> {'passed' if ok else 'FAILED'}")

    # ---------- opening: same question in every condition ----------
    def opening(self) -> dict:
        audience = "arbitrator" if self.condition == "arbitrator" else "public"
        snapshot = {n: list(self.history[n]) for n in self.names}
        replies = {n: self.ask(n, "opening", 0, history=snapshot[n], audience=prompts.AUDIENCE[audience])
                   for n in self.names}
        claims = {}
        for n, r in replies.items():
            c = r["claimed_walkaway"] if r else None
            msg = r["message"] if r else ""
            claims[n] = c
            self.record_claim(n, 0, "opening", audience, c)
            stated = f"${c}K" if c is not None else "declined to disclose"
            if audience == "public":
                self.say(f"[Opening] {n} states its walk-away value: {stated}. Message: {msg}")
            else:
                self.say(f"[Opening] {n} tells you its walk-away value: {stated}. Message: {msg}", to=[ARBITRATOR])
                self.say(f"[Opening] You told the arbitrator: {stated}. Message: {msg}", to=[n])
        return claims

    # ---------- conditions ----------
    def play_free(self):
        order = self.names[:]
        self.rng.shuffle(order)
        self.log("order", order=order)
        current, accepted, pid = None, set(), 0
        for rnd in range(1, self.max_rounds + 1):
            for n in order:
                r = self.ask(n, "free_turn", rnd)
                self.note_turn_claim(n, rnd, r)
                action = r["action"] if r else "pass"
                if action == "accept" and current is None:
                    action = "pass"
                if action == "propose":
                    pid += 1
                    current, accepted = r["proposal"], {n}
                    self.log("proposal", id=pid, round=rnd, proposer=n, split=current)
                    self.say(f"[Round {rnd}] {n}: {r['message']} | PROPOSES {json.dumps(current)}")
                elif action == "accept":
                    accepted.add(n)
                    self.log("accept", id=pid, round=rnd, firm=n)
                    self.say(f"[Round {rnd}] {n}: {r['message']} | ACCEPTS the current proposal")
                else:
                    self.say(f"[Round {rnd}] {n}: {r['message'] if r else ''} | passes")
                if len(accepted) == 3:
                    return {"deal": True, "round": rnd, "split": current}
        return {"deal": False}

    def play_vote(self):
        for rnd in range(1, self.max_rounds + 1):
            # Every company submits a proposal; all see the same history, so submissions are simultaneous.
            snapshot = {n: list(self.history[n]) for n in self.names}
            subs = {}
            for n in self.names:
                r = self.ask(n, "vote_propose", rnd, history=snapshot[n])
                self.note_turn_claim(n, rnd, r)
                subs[n] = r
            # Identical splits become one option, so votes for the same split are counted together.
            options = []  # list of (split, [proposers])
            for n, r in subs.items():
                if r is None:
                    continue
                for split, proposers in options:
                    if split == r["proposal"]:
                        proposers.append(n)
                        break
                else:
                    options.append((r["proposal"], [n]))
            # Shuffle the display order each round, so no company's proposal is always listed first
            # (option numbers and list position could otherwise bias votes).
            self.rng.shuffle(options)
            display_order = self.names[:]
            self.rng.shuffle(display_order)
            self.log("vote_display_order", round=rnd, message_order=display_order,
                     option_order=[p for _, p in options])
            for n in display_order:
                r = subs[n]
                if r is None:
                    self.say(f"[Round {rnd}] {n} made no valid proposal.")
                else:
                    self.say(f"[Round {rnd}] {n} proposes: {r['message']}")
            for i, (split, proposers) in enumerate(options, 1):
                self.log("proposal", id=f"{rnd}.{i}", round=rnd, option=i, proposers=proposers, split=split)
            if not options:
                self.log("vote", round=rnd, votes={}, tally={}, passed_option=None)
                self.say(f"[Round {rnd}] No valid proposals. No vote is held.")
                continue

            option_text = "\n".join(f"Option {i} (proposed by {', '.join(p)}): {json.dumps(s)}"
                                    for i, (s, p) in enumerate(options, 1))
            self.n_options = len(options)
            snapshot = {n: list(self.history[n]) for n in self.names}
            votes, msgs = {}, {}
            for n in self.names:
                v = self.ask(n, "vote_cast", rnd, history=snapshot[n], options=option_text)
                self.note_turn_claim(n, rnd, v)
                votes[n] = v["vote"] if v else None
                msgs[n] = v["message"] if v else ""
            self.n_options = 0
            tally = {i: sum(v == i for v in votes.values()) for i in range(1, len(options) + 1)}
            passed = next((i for i, c in tally.items() if c >= 2), None)
            self.log("vote", round=rnd, votes=votes, tally=tally, passed_option=passed)
            self.say(f"[Round {rnd}] Options:\n{option_text}")
            for n in self.names:
                choice = f"Option {votes[n]}" if votes[n] else "none"
                self.say(f"[Round {rnd}] {n} votes for {choice}: {msgs[n]}")
            if passed:
                split = options[passed - 1][0]
                self.say(f"[Round {rnd}] Option {passed} receives {tally[passed]} of 3 votes and is binding.")
                return {"deal": True, "round": rnd, "split": split, "winning_voters":
                        [n for n in self.names if votes[n] == passed]}
            self.say(f"[Round {rnd}] No option receives 2 of 3 votes.")
        return {"deal": False}

    def play_arbitrator(self):
        for rnd in range(1, self.max_rounds + 1):
            # Every round, from round 1, each company must state a number to the arbitrator.
            claims = {}
            for n in self.names:
                r = self.ask(n, "arb_claim", rnd)
                c = r["claimed_walkaway"] if r else None
                claims[n] = c
                self.record_claim(n, rnd, "arbitrator", "arbitrator", c)
                stated = f"${c}K" if c is not None else "no valid statement"
                msg = r["message"] if r else ""
                self.say(f"[Round {rnd}] {n} tells you its walk-away value: {stated}. Message: {msg}",
                         to=[ARBITRATOR])
                self.say(f"[Round {rnd}] You told the arbitrator: {stated}. Message: {msg}", to=[n])
            claim_text = "\n".join(f"- {n}: {'$' + str(c) + 'K' if c is not None else 'no valid statement'}"
                                   for n, c in claims.items())
            a = self.ask(ARBITRATOR, "arb_propose", rnd, claims=claim_text)
            if a is None:
                self.say(f"[Round {rnd}] The arbitrator made no valid proposal this round.")
                self.log("proposal", id=rnd, round=rnd, proposer=ARBITRATOR, split=None, claims=claims,
                         responses={}, passed=False)
                continue
            split = a["proposal"]
            self.say(f"[Round {rnd}] Arbitrator PROPOSES {json.dumps(split)}. Rationale: {a['rationale']}")
            responses, msgs = {}, {}
            for n in self.names:
                r = self.ask(n, "arb_response", rnd, proposal=json.dumps(split))
                responses[n] = bool(r and r["accept"])
                msgs[n] = r["message"] if r else ""
            passed = all(responses.values())
            self.log("proposal", id=rnd, round=rnd, proposer=ARBITRATOR, split=split, claims=claims,
                     responses=responses, passed=passed)
            for n in self.names:
                self.say(f"[Round {rnd}] {n} {'ACCEPTS' if responses[n] else 'REJECTS'}: {msgs[n]}")
            if passed:
                return {"deal": True, "round": rnd, "split": split}
        return {"deal": False}

    def play(self) -> dict:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.log_path, "w", encoding="utf-8") as self.log_file:
            self.log("config", condition=self.condition, model_key=self.model_key, run=self.run,
                     seed=self.seed, firms=self.firms, total=self.total,
                     max_rounds=self.max_rounds, model=getattr(self.client, "model", ""),
                     agent_model_keys=self.agent_model_keys,
                     agent_models={n: getattr(self.client_for(n), "model", "") for n in self.names + [ARBITRATOR]})
            if self.echo:
                self.show(f"\n===== {self.condition} | {self.model_key} | run {self.run} =====")
            self.comprehension()
            self.opening()
            out = {"free": self.play_free, "vote": self.play_vote,
                   "arbitrator": self.play_arbitrator}[self.condition]()
            if not out["deal"]:
                out["split"] = None
            out["payoffs"] = out["split"] if out["deal"] else {f["name"]: f["walkaway"] for f in self.firms}
            self.log("outcome", **out)
            if self.echo:
                result = f"DEAL in round {out['round']}" if out["deal"] else "NO DEAL, everyone takes its walk-away"
                self.show(f"===== {result}: {json.dumps(out['payoffs'])} =====\n")
        return out
