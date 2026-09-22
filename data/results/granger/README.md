# data/results/granger/

| 檔案 | 產生腳本 | 內容 | 列數 |
|---|---|---|---|
| granger_full_210.csv | 05 | 15×14=210組全配對Granger因果檢定：BIC/AIC選lag、ssr F檢定、Newey-West HAC穩健F檢定、BH-FDR校正 | 210 |
| granger_pmatrix_bic.csv | 05 | 210組p值(BIC lag)排成15×15矩陣 | 15 |
| granger_Fmatrix_bic.csv | 05 | 210組F值(BIC lag)排成15×15矩陣 | 15 |
| granger_significant_links_intra_asia.csv | 05 | 排除54組觸及美股(AMKR/INTC)的配對後，13家亞洲公司間通過FDR顯著性的23組關係(22單向+1雙向=24條邊) | 23 |
| split_sample_granger.csv | 07 | 上述24條邊，以2023-09-01切成前後兩個獨立3年子區間，各自重跑Granger+FDR，分類為全期間穩定/僅前半/僅後半/皆不顯著 | 24 |
