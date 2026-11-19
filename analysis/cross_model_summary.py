"""Headline numbers for the cross-model games. Usage: python analysis/cross_model_summary.py <out_dir of cross_model_analyze.py>"""
import sys, json, random
import pandas as pd
x = sys.argv[1]
S = pd.read_csv(f"{x}/x_seats.csv"); G = pd.read_csv(f"{x}/x_games.csv"); C = pd.read_csv(f"{x}/x_claims.csv")
X = S[S.kind == "cross"]; XG = G[G.kind == "cross"]; XC = C[C.kind == "cross"]
res = {}
for c in ["free", "vote", "arbitrator", "ALL"]:
    s = X if c == "ALL" else X[X.condition == c]; g = XG if c == "ALL" else XG[XG.condition == c]
    d = s[s.deal]
    row = dict(games=len(g), deals=int(g.deal.sum()), any_below=int(g.any_below.sum()),
               claude_gain=round(d[d.model == "Claude"].gain.mean(), 1), gemini_gain=round(d[d.model == "Gemini"].gain.mean(), 1),
               claude_below=f"{int(s[s.model=='Claude'].below.sum())}/{int((s.model=='Claude').sum())}",
               gemini_below=f"{int(s[s.model=='Gemini'].below.sum())}/{int((s.model=='Gemini').sum())}",
               mean_round=round(g[g.deal].rnd.mean(), 1))
    # per-game advantage with bootstrap CI
    adv = []
    for gname, gs in d.groupby("game"):
        a = gs[gs.model == "Claude"].gain.mean(); b = gs[gs.model == "Gemini"].gain.mean()
        adv.append(a - b)
    random.seed(3)
    if adv:
        bs = sorted(sum(random.choice(adv) for _ in adv) / len(adv) for _ in range(4000))
        row["claude_minus_gemini"] = [round(sum(adv) / len(adv), 1), round(bs[100], 1), round(bs[3899], 1), len(adv)]
    res[c] = row
V = XG[(XG.condition == "vote") & XG.deal]
res["vote_detail"] = dict(loser_model=V.loser_model.value_counts().to_dict(), imposed=int(V.imposed_below.fillna(False).astype(bool).sum()),
                          winners_with_gemini=int(V.winner_models.str.contains("Gemini").sum()), n=len(V),
                          same_model_pairs=int((V.winner_models.isin(["Claude+Claude", "Gemini+Gemini"])).sum()),
                          two_member=int((V.winner_models.str.count("\\+") == 1).sum()),
                          outvoted=int(V.loser_model.notna().sum()),
                          claude_majority_games=int((V.n_claude == 2).sum()),
                          claude_majority_claude_lost=int(((V.n_claude == 2) & (V.loser_model == "Claude")).sum()))
O = XC[XC.source == "opening"]
res["opening"] = O.groupby("model").agg(disclosed=("disclosed", "mean"), ratio=("ratio", "mean")).round(2).to_dict()
A = XC[XC.source == "arbitrator"]
res["arb_claims"] = A.groupby("model").ratio.mean().round(2).to_dict()
AR = XG[XG.condition == "arbitrator"]
res["arb_by_arbitrator"] = AR.groupby("arb_model").agg(n=("deal", "size"), deals=("deal", "sum")).to_dict()
json.dump(res, open(f"{x}/xsummary.json", "w"), default=str); print(json.dumps(res, indent=1, default=str))
