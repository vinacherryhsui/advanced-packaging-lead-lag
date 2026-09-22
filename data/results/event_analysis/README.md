# data/results/event_analysis/

| 檔案 | 產生腳本 | 內容 | 列數 |
|---|---|---|---|
| wls_master_table.csv | 09 | 13個亞洲節點的加權領先分數(WLS = 出邊-log10(p)總和 - 入邊-log10(p)總和) | 13 |
| cross_validation_master.csv | 13 | 13個節點的WLS排名、供應鏈方向對齊角色、RS時機角色，三項指標彙總 | 13 |
| all24_pooled.csv | 15 | 24條核心邊，領先者觸發日(單日報酬≥1.5倍自身60日標準差)後，跟隨者1/3/5/10日累積報酬(全樣本pooled) | 24 |
| all24_split.csv | 15 | 同上，以2023-09-01切前後兩段各自重跑10日窗口，分類全期間穩定/僅前半/僅後半/皆不顯著 | 24 |
| all24_master_table.csv | 15 | pooled與split結果彙總 | 24 |
| basket_backtest_all19.csv | 16 | 15的分類為「全期間穩定」或「僅後半段」的19條邊，領先者週訊號觸發的跟隨者20日持有報酬，vs 1,000次隨機持有窗口(Mann-Whitney U檢定)、vs 全樣本buy-and-hold | 19 |

