# REPRODUCE

本資料夾是「先進封裝供應鏈16→15家公司跨市場領先-落後關係研究」的可重現複製程式碼：16支腳本、從零抓取股價開始，重建 `data/processed/` 與 `data/results/` 底下的全部產出。

## 環境

- Python 3.12（開發時用 3.12.4）
- `pip install -r requirements.txt`

## 執行順序

從repo根目錄執行，腳本只讀寫 `data/` 底下的檔案：

```
python scripts/01_fetch_data.py            # 連網；從Yahoo Finance重新抓取15檔股價
python scripts/02_clean_align.py
python scripts/03_flag_cn_limits.py
python scripts/04_compute_returns.py
python scripts/05_granger_full210.py
python scripts/06_placebo_test.py
python scripts/07_split_sample_granger.py
python scripts/08_network_centrality.py
python scripts/09_supply_chain_wls.py
python scripts/10_technical_analysis.py    # 連網；額外抓取^TWII(台股加權指數)
python scripts/11_rs_60d_basis.py
python scripts/12_leader_follower_timing.py
python scripts/13_cross_validation.py
python scripts/14_transfer_entropy.py      # 較慢：約24,000次surrogate TE運算
python scripts/15_event_reaction_all24.py
python scripts/16_basket_backtest.py
```

腳本01、10會連網（Yahoo Finance），其餘全部離線，只依賴 `data/raw/` 與彼此的輸出。

**注意**：腳本01重新抓取時會打到Yahoo Finance即時資料。已調整股價（adjusted close）對過去日期的數值，會隨時間因股息除權等事件被追溯修正，所以重新抓取不保證跟`data/raw/`裡目前這批資料逐位元相同——這是預期內現象，不是錯誤。原始樣本包含16家公司，因Shinko(6967.T)於2025年私有化下市、無法取得完整歷史資料，抓取後已從`raw_adjclose.csv`移除，全流程實際使用15檔標的。

## 資料衍生鏈

```
data/raw/ (01)
  → data/processed/panel_15co_usshift_intersection.csv (02)
    → data/processed/panel_15co_with_cn_flags.csv, cn_limit_days_all.csv (03)
    → data/processed/panel_15co_returns_raw.csv, panel_15co_returns_clean.csv (04)
      → data/results/granger/granger_full_210.csv 等 (05)
        → data/results/placebo/ (06)
        → data/results/granger/split_sample_granger.csv (07)
        → data/results/network/intra_asia_centrality.csv (08)
        → data/results/network/supply_chain_alignment.csv, event_analysis/wls_master_table.csv (09)
      → data/results/technical/ (10, 11)
      → data/results/network/leader_follower_timing_2sd.csv (12)
        → data/results/event_analysis/cross_validation_master.csv (13)
      → data/results/network/transfer_entropy_24edges.csv (14)
      → data/results/event_analysis/all24_pooled.csv, all24_split.csv, all24_master_table.csv (15)
        → data/results/event_analysis/basket_backtest_all19.csv (16)
```

## 已驗證的重跑結果

- **台積電(2330.TW) → 欣銓(3264.TWO)**，本研究引用最多次的核心關係：
  - Granger分段檢定（`granger/split_sample_granger.csv`）：F1=10.282, F2=10.662，前後兩段均通過FDR校正，分類為「全期間穩定」——與原版完全一致。
  - 事件反應分析（`event_analysis/all24_split.csv`）：前半段t=5.41、後半段t=3.25——與原版報告（03_core_findings.md）引用的數字一致。

## 已知差異（重新抓取 vs 原始版本）

- 台積電(2330.TW) 調整後股價全歷史系統性下修約0.29%（新除息日回溯調整所致），下游所有衍生指標因此有極小幅度變動，但均在小數點第5-6位以下，不影響任何分類結論或報告引用數字。
- 002156.SZ、002185.SZ 於抓取窗口最後一日(2026-09-10)的Open價有小幅修正，不影響Close/Adj Close，對分析結果無實質影響。
