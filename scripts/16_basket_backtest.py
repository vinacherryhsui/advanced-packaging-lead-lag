"""
Step 16: basket backtest vs. buy-and-hold, for the 19 edges classified as
"全期間穩定" or "僅後半段" in step 15.

Does:
  - For each such edge, defines a signal as the leader's weekly (5-day
    rolling sum) return exceeding 1.5x its own trailing 60-week-return
    standard deviation.
  - De-duplicates overlapping signals into independent, non-overlapping
    20-trading-day holding episodes (greedy: a new signal is accepted only
    after the previous episode's holding window has closed).
  - Compares the episode returns to 1,000 random 20-day holding periods
    (Mann-Whitney U test) and to full-sample buy-and-hold for the follower.

Input:  data/processed/panel_15co_returns_clean.csv (full panel)
        data/results/event_analysis/all24_split.csv
Output: data/results/event_analysis/basket_backtest_all19.csv
"""
import os
import sys
import numpy as np
import pandas as pd
from scipy import stats

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED = os.path.join(ROOT, "data", "processed")
EVENT = os.path.join(ROOT, "data", "results", "event_analysis")

HOLD = 20
N_RANDOM = 1000
TRADING_DAYS_YEAR = 252
RNG_SEED = 20260914

clean = pd.read_csv(os.path.join(PROCESSED, "panel_15co_returns_clean.csv"),
                     index_col=0, parse_dates=True).sort_index()
n = len(clean)

split = pd.read_csv(os.path.join(EVENT, "all24_split.csv"))
edges = split[split.classification.isin(["全期間穩定", "僅後半段"])][
    ["leader", "leader_name", "follower", "follower_name", "classification"]].reset_index(drop=True)

max_start = n - HOLD - 1


def holding_return(series, pos, horizon=HOLD):
    start, end = pos + 1, pos + horizon
    if end >= n:
        return np.nan
    return series.iloc[start:end + 1].sum()


def buyhold_stats(follower):
    s = clean[follower]
    mu, sd = s.mean(), s.std(ddof=1)
    ann_ret = mu * TRADING_DAYS_YEAR
    ann_vol = sd * np.sqrt(TRADING_DAYS_YEAR)
    return ann_ret, ann_vol, (ann_ret / ann_vol if ann_vol > 0 else np.nan)


bh_cache = {f: buyhold_stats(f) for f in edges.follower.unique()}

rows = []
for _, row in edges.iterrows():
    L, F = row["leader"], row["follower"]
    weekly_L = clean[L].rolling(5).sum()
    weekly_std_prior = weekly_L.shift(1).rolling(60).std()
    trig = weekly_L.abs() >= 1.5 * weekly_std_prior
    signal_positions = np.where(trig.fillna(False).values)[0]

    episodes = []
    blocked_until = -1
    for p in signal_positions:
        if p > blocked_until:
            episodes.append(p)
            blocked_until = p + HOLD

    fseries = clean[F]
    ep_returns = np.array([holding_return(fseries, p) for p in episodes])
    ep_returns_valid = ep_returns[~np.isnan(ep_returns)]
    n_ep = len(ep_returns_valid)

    rng = np.random.default_rng(RNG_SEED)
    random_positions = rng.integers(low=0, high=max_start, size=N_RANDOM)
    rand_returns = np.array([holding_return(fseries, p) for p in random_positions])
    rand_returns = rand_returns[~np.isnan(rand_returns)]

    if n_ep >= 2:
        u_stat, u_p = stats.mannwhitneyu(ep_returns_valid, rand_returns, alternative="two-sided")
        periods_per_year = TRADING_DAYS_YEAR / HOLD
        mu_p, sd_p = ep_returns_valid.mean(), ep_returns_valid.std(ddof=1)
        strat_ann_ret = mu_p * periods_per_year
        strat_ann_vol = sd_p * np.sqrt(periods_per_year)
        strat_sharpe = strat_ann_ret / strat_ann_vol if strat_ann_vol > 0 else np.nan
        winrate = (ep_returns_valid > 0).mean()
    else:
        u_stat = u_p = strat_ann_ret = strat_ann_vol = strat_sharpe = winrate = np.nan

    bh_ann_ret, bh_ann_vol, bh_sharpe = bh_cache[F]

    rows.append(dict(
        leader=L, leader_name=row["leader_name"], follower=F, follower_name=row["follower_name"],
        task1_classification=row["classification"],
        raw_signal_days=len(signal_positions), n_independent_episodes=n_ep,
        strategy_ann_ret=strat_ann_ret, strategy_ann_vol=strat_ann_vol, strategy_sharpe=strat_sharpe,
        strategy_winrate=winrate,
        buyhold_ann_ret=bh_ann_ret, buyhold_ann_vol=bh_ann_vol, buyhold_sharpe=bh_sharpe,
        mannwhitney_U=u_stat, mannwhitney_p=u_p,
        strategy_beats_random_at_5pct=(u_p < 0.05) if pd.notna(u_p) else np.nan,
    ))

out = pd.DataFrame(rows)
out.to_csv(os.path.join(EVENT, "basket_backtest_all19.csv"), index=False, encoding="utf-8")
print(f"saved basket_backtest_all19.csv  {len(out)} edges  "
      f"beats_random={int(out.strategy_beats_random_at_5pct.sum())}/{len(out)}")
