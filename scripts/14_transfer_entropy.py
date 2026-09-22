"""
Step 14: Transfer Entropy cross-validation of the 24 core Granger edges.

Does:
  - Quantile-bins each of the 13 series into 5 bins (full history).
  - For each directed edge, computes plug-in histogram Transfer Entropy in
    both directions, at the same history order (BIC lag) used by that
    edge's Granger test.
  - Tests significance of the forward TE against an empirical null built
    from 1,000 shuffles of the cause series.

Input:  data/processed/panel_15co_returns_clean.csv (full panel)
        data/results/granger/granger_full_210.csv
        data/results/granger/granger_significant_links_intra_asia.csv
Output: data/results/network/transfer_entropy_24edges.csv
"""
import os
import sys
import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

rng = np.random.default_rng(20260914)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED = os.path.join(ROOT, "data", "processed")
GRANGER = os.path.join(ROOT, "data", "results", "granger")
NETWORK = os.path.join(ROOT, "data", "results", "network")

NAMES = {
    "2330.TW": "TSMC 台積電", "3711.TW": "ASE 日月光", "6239.TW": "Powertech 力成",
    "2449.TW": "KYEC 京元電子", "3264.TWO": "Ardentec 欣銓", "3037.TW": "Unimicron 欣興",
    "8046.TW": "Nan Ya PCB 南電", "3189.TW": "Kinsus 景碩", "600584.SS": "JCET 長電",
    "002156.SZ": "Tongfu 通富", "002185.SZ": "Huatian 華天", "005930.KS": "Samsung 三星",
    "4062.T": "Ibiden",
}
N_BINS = 5
N_SURR = 1000
ALPHA = 0.05

clean = pd.read_csv(os.path.join(PROCESSED, "panel_15co_returns_clean.csv"),
                     index_col=0, parse_dates=True).sort_index()
full = pd.read_csv(os.path.join(GRANGER, "granger_full_210.csv"))
sig = pd.read_csv(os.path.join(GRANGER, "granger_significant_links_intra_asia.csv"))

edges = []
for r in sig.itertuples():
    a, b = r.dir1.split("->")
    edges.append((a, b))
    if r.type == "bidirectional":
        c, d = r.dir2.split("->")
        edges.append((c, d))

bins = {}
bin_counts_used = {}
for t in NAMES:
    s = clean[t].values
    b, edges_used = pd.qcut(s, N_BINS, labels=False, retbins=True, duplicates="drop")
    bins[t] = b.astype(int)
    bin_counts_used[t] = len(edges_used) - 1


def get_p_bic(cause, effect):
    row = full[(full.cause == cause) & (full.effect == effect)]
    return float(row.iloc[0]["p_bic"]), int(row.iloc[0]["lag_used_bic"])


def te_from_bins(xb, yb, k, nbinsX, nbinsY):
    N = len(yb)
    T = N - k
    y_future = yb[k:N]
    yhist_code = np.zeros(T, dtype=np.int64)
    xhist_code = np.zeros(T, dtype=np.int64)
    for i in range(k):
        yhist_code = yhist_code * nbinsY + yb[i:i + T]
        xhist_code = xhist_code * nbinsX + xb[i:i + T]
    Ky = nbinsY ** k
    Kx = nbinsX ** k
    joint_full = (y_future.astype(np.int64) * Ky + yhist_code) * Kx + xhist_code
    joint_y = y_future.astype(np.int64) * Ky + yhist_code
    cnt_full = np.bincount(joint_full, minlength=nbinsY * Ky * Kx)
    cnt_yx = np.bincount(yhist_code * Kx + xhist_code, minlength=Ky * Kx)
    cnt_y = np.bincount(joint_y, minlength=nbinsY * Ky)
    cnt_yhist = np.bincount(yhist_code, minlength=Ky)
    c_full = cnt_full[joint_full]
    c_yx = cnt_yx[yhist_code * Kx + xhist_code]
    c_y = cnt_y[joint_y]
    c_yhist = cnt_yhist[yhist_code]
    ratio = (c_full.astype(float) * c_yhist.astype(float)) / (c_yx.astype(float) * c_y.astype(float))
    return np.mean(np.log2(ratio))


rows = []
cache_te = {}
for cause, effect in edges:
    p_bic, k = get_p_bic(cause, effect)
    xb, yb = bins[cause], bins[effect]
    nx_, ny_ = bin_counts_used[cause], bin_counts_used[effect]

    key_fwd = (cause, effect, k)
    if key_fwd not in cache_te:
        cache_te[key_fwd] = te_from_bins(xb, yb, k, nx_, ny_)
    te_fwd = cache_te[key_fwd]

    key_bwd = (effect, cause, k)
    if key_bwd not in cache_te:
        cache_te[key_bwd] = te_from_bins(yb, xb, k, ny_, nx_)
    te_bwd = cache_te[key_bwd]

    surr = np.empty(N_SURR)
    xb_shuf = xb.copy()
    for i in range(N_SURR):
        rng.shuffle(xb_shuf)
        surr[i] = te_from_bins(xb_shuf, yb, k, nx_, ny_)
    p_emp = (1 + np.sum(surr >= te_fwd)) / (N_SURR + 1)

    consistent = "是" if te_fwd > te_bwd else "否"
    rows.append(dict(
        cause=cause, cause_name=NAMES[cause], effect=effect, effect_name=NAMES[effect],
        granger_p_bic=p_bic, granger_lag=k,
        TE_cause_to_effect=round(te_fwd, 5), TE_effect_to_cause=round(te_bwd, 5),
        TE_direction=("TE支持cause->effect" if te_fwd > te_bwd else "TE支持effect->cause(反向)"),
        TE_p_value=round(p_emp, 4), TE_sig_5pct=("是" if p_emp < ALPHA else "否"),
        consistent_with_granger=consistent,
    ))

out = pd.DataFrame(rows)
out.to_csv(os.path.join(NETWORK, "transfer_entropy_24edges.csv"), index=False, encoding="utf-8")
print(f"saved transfer_entropy_24edges.csv  {len(out)} rows  "
      f"consistent={int((out.consistent_with_granger=='是').sum())}/{len(out)}")
