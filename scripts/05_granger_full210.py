"""
Step 5: pairwise Granger causality tests, all 15x14 = 210 directed pairs.

Does:
  - ADF stationarity check per series.
  - Per unordered pair, selects VAR lag order via BIC and AIC (grid 1-10,
    floored to 1 if an information criterion prefers 0).
  - Runs the ssr F-test at the BIC-selected lag (headline) and at the AIC-
    selected lag (comparison), plus a Newey-West HAC-robust joint Wald F-test
    at the BIC lag.
  - Applies Benjamini-Hochberg FDR correction (and Bonferroni for comparison)
    across the family of 210 headline BIC p-values.
  - Flags the 54 directional tests that involve a US ticker (AMKR or INTC) as
    alignment-sensitive (see step 06), and builds the intra-Asia significant-
    link table from the remaining 156 tests.

Input:  data/processed/panel_15co_returns_clean.csv
        (uses only the first 1,250 rows, through 2026-09-10)
Output: data/results/granger/granger_full_210.csv
        data/results/granger/granger_pmatrix_bic.csv
        data/results/granger/granger_Fmatrix_bic.csv
        data/results/granger/granger_significant_links_intra_asia.csv
"""
import os
import itertools
import warnings
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller, grangercausalitytests
from statsmodels.tsa.api import VAR
from statsmodels.regression.linear_model import OLS
from statsmodels.stats.multitest import multipletests

warnings.simplefilter("ignore")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED = os.path.join(ROOT, "data", "processed")
GRANGER = os.path.join(ROOT, "data", "results", "granger")
os.makedirs(GRANGER, exist_ok=True)

MAXLAG = 10
ALPHA = 0.05
US = ["AMKR", "INTC"]
ANALYSIS_END = "2026-09-10"

df = pd.read_csv(os.path.join(PROCESSED, "panel_15co_returns_clean.csv"),
                  index_col=0, parse_dates=True).sort_index()
df = df.loc[:ANALYSIS_END]
TK = list(df.columns)
n_all = len(df)
assert df.isna().sum().sum() == 0

adf_p = {c: adfuller(df[c].values, regression="c", autolag="AIC")[1] for c in TK}

pair_lag = {}
for a, b in itertools.combinations(TK, 2):
    so = VAR(df[[a, b]].values).select_order(maxlags=MAXLAG)
    pair_lag[(a, b)] = (int(so.aic), int(so.bic))
    pair_lag[(b, a)] = (int(so.aic), int(so.bic))

nw_lags = int(np.floor(4 * ((n_all - MAXLAG) / 100) ** (2 / 9)))


def build_design(effect, cause, L):
    X = pd.DataFrame(index=df.index)
    X["const"] = 1.0
    for k in range(1, L + 1):
        X[f"{effect}_l{k}"] = df[effect].shift(k)
    cause_cols = []
    for k in range(1, L + 1):
        nm = f"{cause}_l{k}"
        X[nm] = df[cause].shift(k)
        cause_cols.append(nm)
    d = pd.concat([df[effect].rename("y"), X], axis=1).dropna()
    return d["y"].values, d.drop(columns="y"), cause_cols


def one_test(effect, cause, L):
    data = df[[effect, cause]].values
    gc = grangercausalitytests(data, maxlag=[L], verbose=False)[L][0]
    F, pF, dfd, dfn = gc["ssr_ftest"]
    chi2, pchi2, dfc = gc["ssr_chi2test"]
    yv, Xdf, cause_cols = build_design(effect, cause, L)
    res = OLS(yv, Xdf.values).fit(cov_type="HAC", cov_kwds={"maxlags": nw_lags, "use_correction": True})
    idx = [Xdf.columns.get_loc(c) for c in cause_cols]
    R = np.zeros((len(idx), Xdf.shape[1]))
    for i, j in enumerate(idx):
        R[i, j] = 1.0
    ft = res.f_test(R)
    return dict(F=F, pF=pF, df_num=int(dfn), df_denom=int(dfd), chi2=chi2, pchi2=pchi2,
                hacF=float(np.squeeze(ft.fvalue)), hacP=float(ft.pvalue))


rows = []
for effect in TK:
    for cause in TK:
        if effect == cause:
            continue
        l_aic, l_bic = pair_lag[(cause, effect)]
        lu_bic = max(l_bic, 1)
        lu_aic = max(l_aic, 1)
        rb = one_test(effect, cause, lu_bic)
        ra = one_test(effect, cause, lu_aic) if lu_aic != lu_bic else rb
        rows.append(dict(
            cause=cause, effect=effect, n_obs=n_all,
            adf_p_cause=adf_p[cause], adf_p_effect=adf_p[effect],
            maxlag_searched=MAXLAG, lag_aic=l_aic, lag_bic=l_bic,
            lag_used_bic=lu_bic, bic_lag_floored=(l_bic < 1),
            F_bic=rb["F"], df_num_bic=rb["df_num"], df_denom_bic=rb["df_denom"],
            p_bic=rb["pF"], chi2_bic=rb["chi2"], chi2_p_bic=rb["pchi2"],
            hac_F_bic=rb["hacF"], hac_p_bic=rb["hacP"], hac_maxlags=nw_lags,
            sig_raw_bic=rb["pF"] < ALPHA, sig_raw_hac_bic=rb["hacP"] < ALPHA,
            lag_used_aic=lu_aic, aic_lag_floored=(l_aic < 1), aic_at_boundary=(l_aic == MAXLAG),
            F_aic=ra["F"], p_aic=ra["pF"], sig_raw_aic=ra["pF"] < ALPHA,
        ))

res_df = pd.DataFrame(rows)
_, res_df["p_bic_fdr_bh"], _, _ = multipletests(res_df["p_bic"].values, alpha=ALPHA, method="fdr_bh")
_, res_df["p_bic_bonf"], _, _ = multipletests(res_df["p_bic"].values, alpha=ALPHA, method="bonferroni")
res_df["sig_fdr_bh"] = res_df["p_bic_fdr_bh"] < ALPHA
res_df["sig_bonf"] = res_df["p_bic_bonf"] < ALPHA
_, res_df["hac_p_bic_fdr_bh"], _, _ = multipletests(res_df["hac_p_bic"].values, alpha=ALPHA, method="fdr_bh")
res_df["sig_hac_fdr_bh"] = res_df["hac_p_bic_fdr_bh"] < ALPHA

touches_us = res_df.cause.isin(US) | res_df.effect.isin(US)
res_df["alignment_robust"] = np.where(
    touches_us,
    "alignment-sensitive, not interpreted as lead-lag",
    "robust (intra-Asia, no cross-timezone shift)",
)

res_df = res_df.sort_values(["cause", "effect"]).reset_index(drop=True)
res_df.to_csv(os.path.join(GRANGER, "granger_full_210.csv"), index=False)

pmat = res_df.pivot(index="cause", columns="effect", values="p_bic").reindex(index=TK, columns=TK)
Fmat = res_df.pivot(index="cause", columns="effect", values="F_bic").reindex(index=TK, columns=TK)
pmat.to_csv(os.path.join(GRANGER, "granger_pmatrix_bic.csv"))
Fmat.to_csv(os.path.join(GRANGER, "granger_Fmatrix_bic.csv"))

print(f"granger_full_210.csv: {len(res_df)} directional tests, n_obs={n_all}")
print(f"sig BH-FDR (all 210): {int(res_df.sig_fdr_bh.sum())}")

# ---- intra-Asia significant links (core findings) ----
core = res_df[res_df.sig_fdr_bh & ~touches_us].copy()
sigset = {(r.cause, r.effect) for r in core.itertuples()}
NON_US = [t for t in TK if t not in US]
link_rows = []
for a, b in itertools.combinations(NON_US, 2):
    ab, ba = (a, b) in sigset, (b, a) in sigset
    if not (ab or ba):
        continue
    def grab(c, e):
        return res_df[(res_df.cause == c) & (res_df.effect == e)].iloc[0]
    if ab and ba:
        r1, r2 = grab(a, b), grab(b, a)
        link_rows.append(dict(pair=f"{a} <-> {b}", type="bidirectional", lag=int(r1.lag_used_bic),
                               dir1=f"{a}->{b}", F1=r1.F_bic, p1=r1.p_bic, p1_fdr=r1.p_bic_fdr_bh, hac_p1=r1.hac_p_bic,
                               dir2=f"{b}->{a}", F2=r2.F_bic, p2=r2.p_bic, p2_fdr=r2.p_bic_fdr_bh, hac_p2=r2.hac_p_bic))
    else:
        c, e = (a, b) if ab else (b, a)
        r = grab(c, e)
        link_rows.append(dict(pair=f"{c} -> {e}", type="unidirectional", lag=int(r.lag_used_bic),
                               dir1=f"{c}->{e}", F1=r.F_bic, p1=r.p_bic, p1_fdr=r.p_bic_fdr_bh, hac_p1=r.hac_p_bic,
                               dir2="", F2=np.nan, p2=np.nan, p2_fdr=np.nan, hac_p2=np.nan))
core_links = pd.DataFrame(link_rows).sort_values(["type", "pair"]).reset_index(drop=True)
core_links.to_csv(os.path.join(GRANGER, "granger_significant_links_intra_asia.csv"), index=False)

print(f"granger_significant_links_intra_asia.csv: {len(core_links)} pair-relationships "
      f"({(core_links.type=='unidirectional').sum()} unidirectional, "
      f"{(core_links.type=='bidirectional').sum()} bidirectional)")
