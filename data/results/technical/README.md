# data/results/technical/

腳本10-11：以台股加權指數(^TWII)為基準的技術指標交叉驗證，獨立於Granger/因果分析之外。

| 檔案 | 產生腳本 | 內容 | 列數 |
|---|---|---|---|
| rs_full_period.csv | 10 | 每檔標的相對TAIEX的累積log報酬差(相對強度RS)，全歷史 | 1,251 |
| momentum_full_period.csv | 10 | RS的20日變化量(動能) | 1,251 |
| rrg_12month_trajectory.csv | 10 | 最近12個月底時點，RS與動能的60日滾動z分數座標，分類4象限(RRG) | 180 |
| breadth_full_period.csv | 10 | 全體及4個供應鏈分層各自站上自身60日均線的比例(市場廣度) | 1,251 |
| snapshot_RS_momentum_RRG.csv | 10 | 最新一期RS/動能/RRG象限快照，15檔標的 | 15 |
| rs_60d_15way_basis.csv | 11 | in-degree最高的3個跟隨者(欣銓/南電/景碩)，近60日對台積電與Ibiden兩個基準的累積RS | 366 |
