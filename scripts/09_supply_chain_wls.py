"""
Step 9: supply-chain direction alignment and Weighted Lead Score (WLS).

Does:
  - Assigns each of 11 companies (excludes Samsung, a vertically-integrated
    IDM with no single layer) a supply-chain layer: 1 = wafer foundry,
    2 = substrate, 3 = OSAT packaging/test.
  - For each core edge among those 11, computes S_ij = sign(layer_effect -
    layer_cause) and Alignment_ij = -log10(p_bic) * S_ij.
  - For all 13 intra-Asia nodes, computes the Weighted Lead Score:
    WLS = sum(-log10(p_bic) over out-edges) - sum(-log10(p_bic) over in-edges).

Input:  data/results/granger/granger_full_210.csv
        data/results/granger/granger_significant_links_intra_asia.csv
Output: data/results/network/supply_chain_alignment.csv
        data/results/event_analysis/wls_master_table.csv
"""
import os
import sys
import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRANGER = os.path.join(ROOT, "data", "results", "granger")
NETWORK = os.path.join(ROOT, "data", "results", "network")
EVENT = os.path.join(ROOT, "data", "results", "event_analysis")
os.makedirs(NETWORK, exist_ok=True)
os.makedirs(EVENT, exist_ok=True)

NAMES = {
    "2330.TW": "TSMC 台積電", "3711.TW": "ASE 日月光", "6239.TW": "Powertech 力成",
    "2449.TW": "KYEC 京元電子", "3264.TWO": "Ardentec 欣銓", "3037.TW": "Unimicron 欣興",
    "8046.TW": "Nan Ya PCB 南電", "3189.TW": "Kinsus 景碩", "600584.SS": "JCET 長電",
    "002156.SZ": "Tongfu 通富", "002185.SZ": "Huatian 華天", "005930.KS": "Samsung 三星",
    "4062.T": "Ibiden",
}
L = {
    "2330.TW": 1,
    "3037.TW": 2, "8046.TW": 2, "3189.TW": 2, "4062.T": 2,
    "3711.TW": 3, "6239.TW": 3, "2449.TW": 3, "3264.TWO": 3,
    "600584.SS": 3, "002156.SZ": 3, "002185.SZ": 3,
}
EXCLUDED = ["005930.KS", "INTC", "AMKR"]

full = pd.read_csv(os.path.join(GRANGER, "granger_full_210.csv"))
sig = pd.read_csv(os.path.join(GRANGER, "granger_significant_links_intra_asia.csv"))

edges = []
for r in sig.itertuples():
    a, b = r.dir1.split("->")
    edges.append((a, b))
    if r.type == "bidirectional":
        c, d = r.dir2.split("->")
        edges.append((c, d))


def get_p_bic(cause, effect):
    row = full[(full.cause == cause) & (full.effect == effect)]
    return float(row.iloc[0]["p_bic"])


# ---- supply-chain alignment (11-company subset) ----
sc_edges = [(a, b) for a, b in edges if a not in EXCLUDED and b not in EXCLUDED]
rows = []
for cause, effect in sc_edges:
    Lc, Le = L[cause], L[effect]
    S = 1 if Lc < Le else (0 if Lc == Le else -1)
    p = get_p_bic(cause, effect)
    g = -np.log10(p)
    rows.append(dict(cause=cause, cause_name=NAMES[cause], effect=effect, effect_name=NAMES[effect],
                      L_cause=Lc, L_effect=Le, S_ij=S, p_bic=p, g_ij=round(g, 4),
                      Alignment_ij=round(g * S, 4)))
align_df = pd.DataFrame(rows).sort_values(["S_ij", "cause", "effect"], ascending=[False, True, True]).reset_index(drop=True)
align_df.to_csv(os.path.join(NETWORK, "supply_chain_alignment.csv"), index=False, encoding="utf-8")
print(f"supply_chain_alignment.csv: {len(align_df)} edges, "
      f"S=+1:{(align_df.S_ij==1).sum()}  S=0:{(align_df.S_ij==0).sum()}  S=-1:{(align_df.S_ij==-1).sum()}")

# ---- WLS: all 13 intra-Asia nodes ----
ALL13 = list(NAMES.keys())
g_out = {n: 0.0 for n in ALL13}
g_in = {n: 0.0 for n in ALL13}
out_deg = {n: 0 for n in ALL13}
in_deg = {n: 0 for n in ALL13}
for cause, effect in edges:
    p = get_p_bic(cause, effect)
    g = -np.log10(p)
    g_out[cause] += g
    g_in[effect] += g
    out_deg[cause] += 1
    in_deg[effect] += 1

wls_rows = []
for n in ALL13:
    wls = g_out[n] - g_in[n]
    if out_deg[n] == 0 and in_deg[n] == 0:
        reason = "無任何顯著關係"
    elif abs(wls) < 1e-9:
        reason = "領先與被領先權重抵銷"
    else:
        reason = ""
    wls_rows.append(dict(ticker=n, name=NAMES[n], out_degree=out_deg[n], in_degree=in_deg[n],
                          sum_g_leading=round(g_out[n], 4), sum_g_led=round(g_in[n], 4),
                          WLS=round(wls, 4), WLS_zero_reason=reason))
wls_df = pd.DataFrame(wls_rows).sort_values("WLS", ascending=False).reset_index(drop=True)
wls_df.to_csv(os.path.join(EVENT, "wls_master_table.csv"), index=False, encoding="utf-8")
print(wls_df.to_string(index=False))
