"""
Step 7: split-sample robustness test for the 24 core Granger edges.

Does:
  - Splits the full CLEAN return panel into two independent sub-periods at
    2023-09-01 (pre/post "AI demand boom").
  - Re-runs Granger causality (BIC lag over 1-10, ssr F-test + HAC) for each
    of the 24 directed edges in the intra-Asia significant-link set,
    independently in each half.
  - Applies Benjamini-Hochberg FDR correction within each half's family of
    24 tests, and classifies each edge as fully stable / front-half-only /
    back-half-only / not stable.

Input:  data/processed/panel_15co_returns_clean.csv (full panel)
        data/results/granger/granger_significant_links_intra_asia.csv
Output: data/results/granger/split_sample_granger.csv
"""
import os
import sys
import warnings
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import grangercausalitytests
from statsmodels.tsa.api import VAR
from statsmodels.regression.linear_model import OLS
from statsmodels.stats.multitest import multipletests

warnings.simplefilter("ignore")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED = os.path.join(ROOT, "data", "processed")
GRANGER = os.path.join(ROOT, "data", "results", "granger")

MAXLAG = 10
ALPHA = 0.05
SPLIT = pd.Timestamp("2023-09-01")

clean = pd.read_csv(os.path.join(PROCESSED, "panel_15co_returns_clean.csv"),
                     index_col=0, parse_dates=True).sort_index()
sig = pd.read_csv(os.path.join(GRANGER, "granger_significant_links_intra_asia.csv"))

edges = []
for r in sig.itertuples():
    a, b = r.dir1.split("->")
    edges.append((a, b))
    if r.type == "bidirectional":
        c, d = r.dir2.split("->")
        edges.append((c, d))

first = clean[clean.index < SPLIT]
second = clean[clean.index >= SPLIT]
print(f"first half : {first.index.min().date()} -> {first.index.max().date()}  n={len(first)}")
print(f"second half: {second.index.min().date()} -> {second.index.max().date()}  n={len(second)}")


def granger_one(df, effect, cause):
    sub = df[[cause, effect]].dropna()
    so = VAR(sub.values).select_order(maxlags=MAXLAG)
    bic_arr = np.asarray(so.ics["bic"])
    lag = int(np.argmin(bic_arr[1:]) + 1)
    data = df[[effect, cause]].values
    gc = grangercausalitytests(data, maxlag=[lag], verbose=False)[lag][0]
    F, pF, dfd, dfn = gc["ssr_ftest"]
    X = pd.DataFrame(index=df.index)
    X["const"] = 1.0
    cause_cols = []
    for k in range(1, lag + 1):
        X[f"e_l{k}"] = df[effect].shift(k)
    for k in range(1, lag + 1):
        nm = f"c_l{k}"
        X[nm] = df[cause].shift(k)
        cause_cols.append(nm)
    d = pd.concat([df[effect].rename("y"), X], axis=1).dropna()
    nwlags = int(np.floor(4 * (len(d) / 100) ** (2 / 9)))
    res = OLS(d["y"].values, d.drop(columns="y").values).fit(
        cov_type="HAC", cov_kwds={"maxlags": max(nwlags, 1), "use_correction": True})
    cols = list(d.drop(columns="y").columns)
    idxs = [cols.index(c) for c in cause_cols]
    R = np.zeros((len(idxs), len(cols)))
    for i, j in enumerate(idxs):
        R[i, j] = 1.0
    ft = res.f_test(R)
    return dict(lag=lag, F=F, p=pF, hac_p=float(ft.pvalue), n=len(sub))


rows = []
for cause, effect in edges:
    r1 = granger_one(first, effect, cause)
    r2 = granger_one(second, effect, cause)
    rows.append(dict(cause=cause, effect=effect,
                      n1=r1["n"], lag1=r1["lag"], F1=round(r1["F"], 3), p1=r1["p"], hac_p1=round(r1["hac_p"], 4),
                      n2=r2["n"], lag2=r2["lag"], F2=round(r2["F"], 3), p2=r2["p"], hac_p2=round(r2["hac_p"], 4)))

out = pd.DataFrame(rows)
_, out["p1_fdr"], _, _ = multipletests(out["p1"], alpha=ALPHA, method="fdr_bh")
_, out["p2_fdr"], _, _ = multipletests(out["p2"], alpha=ALPHA, method="fdr_bh")
out["sig1_raw"] = out.p1 < ALPHA
out["sig2_raw"] = out.p2 < ALPHA
out["sig1_fdr"] = out.p1_fdr < ALPHA
out["sig2_fdr"] = out.p2_fdr < ALPHA


def classify(r):
    if r.sig1_fdr and r.sig2_fdr:
        return "全期間穩定(兩段FDR顯著)"
    if r.sig1_fdr and not r.sig2_fdr:
        return "僅前半段顯著(消退中)"
    if r.sig2_fdr and not r.sig1_fdr:
        return "僅後半段顯著(AI週期新現象)"
    if r.sig1_raw and r.sig2_raw:
        return "兩段raw顯著但FDR未過(邊際)"
    return "兩段均不顯著"


out["classification"] = out.apply(classify, axis=1)
out.to_csv(os.path.join(GRANGER, "split_sample_granger.csv"), index=False, encoding="utf-8")
print(out["classification"].value_counts().to_string())
