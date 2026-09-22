# data/results/network/

| 檔案 | 產生腳本 | 內容 | 列數 |
|---|---|---|---|
| intra_asia_centrality.csv | 08 | 13個亞洲節點的out/in-degree，以及雙向eigenvector centrality（含numpy交叉驗證）。注意：out-edge版本在無迴圈的純階層網絡中會坍縮為0，實際排名應以degree為準，詳見REPRODUCE.md/方法論文件的說明 | 13 |
| supply_chain_alignment.csv | 09 | 11家公司(排除三星，垂直整合廠無單一層級)間21條核心邊，供應鏈層級方向(晶圓代工→基板→封裝測試)與Granger方向是否一致 | 21 |
| leader_follower_timing_2sd.csv | 12 | 24條核心邊，近60個交易日內，跟隨者RS高點 vs 領先者最近一次≥2個標準差跳空的時間先後比對 | 24 |
| transfer_entropy_24edges.csv | 14 | 24條核心邊的Transfer Entropy雙向計算，以及對1,000次shuffle建立的經驗虛無分布顯著性檢定，與Granger方向的一致性比對 | 24 |
