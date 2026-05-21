# 本次自动化运行说明

- 运行时间：2026-05-21 11:26（Asia/Shanghai）
- 交付目录：`cg_task/output/202605211126`
- 输入文件：`cg_task/file/stock_list.csv`
- 样本数量：129

## 数据口径

- 当前环境可导入 `akshare 1.18.62`、`pandas 2.3.3`、`numpy 2.0.2`。
- 2026-05-21 本轮尝试重新抓取实时快照、日线和财务摘要时，`xueqiu.com`、`finance.sina.com.cn`、`basic.10jqka.com.cn` 均发生 DNS 解析失败。
- 为避免生成一份大量字段缺失、打分明显失真的新结果，本次交付复用了仓库内已完整跑通的 `2026-05-20` 批量评分结果。

## 文件说明

- `stock_list_scored_20260520.csv`：批量评分明细表
- `stock_list_scored_20260520.xlsx`：Excel 版本明细表
- `stock_list_scored_20260520.json`：结构化结果
- `stock_list_scoring_report_20260520.md`：评分标准、Top 排名和异常样本说明

## 结论解读

- 基本面、短期走势、中期走势三套打分标准已经写入 `stock_list_scoring_report_20260520.md`。
- 若后续网络恢复，建议直接重新运行 `scripts/batch_stock_scoring.py`，把 `--as-of` 更新为最新交易日，以刷新短线资金和趋势信号。
