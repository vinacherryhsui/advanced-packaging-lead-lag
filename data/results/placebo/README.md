# data/results/placebo/

腳本06：針對54組觸及美股(AMKR/INTC)的Granger方向性檢定，測試「美股與亞股對齊方式」本身是否製造出虛假因果關係。三種對齊方式：A=headline(美股日期+1營業日，主要採用版本)、B=反向安慰劑(-1營業日)、C=naive曆法(不位移)。

| 檔案 | 內容 | 列數 |
|---|---|---|
| placebo_alignment_results_long.csv | 54組測試 × 3種對齊方式的完整長表 | 162 |
| placebo_pvalue_by_alignment.csv | 依對齊方式分組的p值彙總 | 54 |
| placebo_Fstat_by_alignment.csv | 依對齊方式分組的F值彙總 | 54 |
| placebo_hacp_by_alignment.csv | 依對齊方式分組的HAC穩健p值彙總 | 54 |
| placebo_summary_counts.csv | 每種對齊方式、每個方向組別的顯著次數統計 | 9 |
