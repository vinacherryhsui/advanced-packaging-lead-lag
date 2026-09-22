# data/results/

腳本05-16的最終分析產出，分5個子資料夾。共同輸入是`data/processed/panel_15co_returns_clean.csv`（15檔標的、1,251日、對齊後的日log報酬率）。

| 子資料夾 | 對應腳本 | 內容摘要 |
|---|---|---|
| granger/ | 05, 06(部分), 07 | 210組全配對Granger因果檢定、分段穩健性複驗 |
| placebo/ | 06 | 美股對齊方式的時區安慰劑檢定 |
| network/ | 08, 09(部分), 12, 14 | 網絡中心性、供應鏈方向對齊、領先-跟隨時機、Transfer Entropy |
| technical/ | 10, 11 | RS/動能/RRG/市場廣度技術指標交叉驗證 |
| event_analysis/ | 09(部分), 13, 15, 16 | WLS領先分數、交叉驗證總表、事件觸發反應分析、一籃子回測 |

各子資料夾詳細欄位說明見各自的README.md。
