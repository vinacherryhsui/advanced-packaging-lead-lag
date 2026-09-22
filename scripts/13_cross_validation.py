"""
Step 13: cross-validation master table (13 intra-Asia nodes).

Does:
  - Merges, per node: WLS and its rank, supply-chain alignment role summary
    (as leader and as follower), and RS-timing role summary (as leader and
    as follower) from the 2sd threshold table.

Input:  data/results/event_analysis/wls_master_table.csv
        data/results/network/supply_chain_alignment.csv
        data/results/network/leader_follower_timing_2sd.csv
Output: data/results/event_analysis/cross_validation_master.csv
"""
import os
import sys
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NETWORK = os.path.join(ROOT, "data", "results", "network")
EVENT = os.path.join(ROOT, "data", "results", "event_analysis")

NAMES = {
    "2330.TW": "TSMC 台積電", "3711.TW": "ASE 日月光", "6239.TW": "Powertech 力成",
    "2449.TW": "KYEC 京元電子", "3264.TWO": "Ardentec 欣銓", "3037.TW": "Unimicron 欣興",
    "8046.TW": "Nan Ya PCB 南電", "3189.TW": "Kinsus 景碩", "600584.SS": "JCET 長電",
    "002156.SZ": "Tongfu 通富", "002185.SZ": "Huatian 華天", "005930.KS": "Samsung 三星",
    "4062.T": "Ibiden",
}
L = {
    "2330.TW": 1, "3037.TW": 2, "8046.TW": 2, "3189.TW": 2, "4062.T": 2,
    "3711.TW": 3, "6239.TW": 3, "2449.TW": 3, "3264.TWO": 3,
    "600584.SS": 3, "002156.SZ": 3, "002185.SZ": 3, "005930.KS": None,
}
ALL13 = list(NAMES.keys())

wls = pd.read_csv(os.path.join(EVENT, "wls_master_table.csv"))
align = pd.read_csv(os.path.join(NETWORK, "supply_chain_alignment.csv"))
timing = pd.read_csv(os.path.join(NETWORK, "leader_follower_timing_2sd.csv"))

wls = wls.sort_values("WLS", ascending=False).reset_index(drop=True)
wls["WLS_rank"] = wls["WLS"].rank(ascending=False, method="min").astype(int)


def align_summary(ticker, role_col):
    sub = align[align[role_col] == ticker]
    if ticker not in L or L[ticker] is None:
        return "N/A(排除:垂直整合廠)"
    if len(sub) == 0:
        return "無資料(未進入11家子集分析或無邊)"
    n1 = int((sub.S_ij == 1).sum())
    n0 = int((sub.S_ij == 0).sum())
    nm1 = int((sub.S_ij == -1).sum())
    parts = []
    if role_col == "cause":
        if n1: parts.append(f"{n1}次領先下游(符合)")
        if n0: parts.append(f"{n0}次同層級")
        if nm1: parts.append(f"{nm1}次領先上游(反直覺)")
    else:
        if n1: parts.append(f"{n1}次被上游領先(符合)")
        if n0: parts.append(f"{n0}次同層級")
        if nm1: parts.append(f"{nm1}次被下游領先(反直覺)")
    return "; ".join(parts)


def timing_summary(ticker, role_col):
    sub = timing[timing[role_col] == ticker]
    if len(sub) == 0:
        return "無資料"
    counts = sub["order"].value_counts()
    n = len(sub)
    consistent = sum(v for k, v in counts.items() if k == "領先者先")
    anomaly = sum(v for k, v in counts.items() if "異常" in k)
    concur = sum(v for k, v in counts.items() if k == "同步")
    other = n - consistent - anomaly - concur
    s = f"{consistent}/{n}領先者先"
    if anomaly: s += f", {anomaly}/{n}異常"
    if concur: s += f", {concur}/{n}同步"
    if other: s += f", {other}/{n}無跳空可比"
    return s


rows = []
for t in ALL13:
    w = wls[wls.ticker == t].iloc[0]
    rows.append(dict(
        ticker=t, name=NAMES[t], L_i=(L[t] if L[t] is not None else "N/A"),
        out_degree=int(w.out_degree), in_degree=int(w.in_degree),
        WLS=round(float(w.WLS), 2), WLS_rank=int(w.WLS_rank),
        WLS_zero_reason=w.WLS_zero_reason if pd.notna(w.WLS_zero_reason) and w.WLS_zero_reason != "" else "",
        Alignment_as_leader=align_summary(t, "cause"),
        Alignment_as_follower=align_summary(t, "effect"),
        RS_timing_as_leader=timing_summary(t, "leader"),
        RS_timing_as_follower=timing_summary(t, "follower"),
    ))

out = pd.DataFrame(rows).sort_values("WLS", ascending=False).reset_index(drop=True)
out.to_csv(os.path.join(EVENT, "cross_validation_master.csv"), index=False, encoding="utf-8")
print(out.to_string(index=False))
