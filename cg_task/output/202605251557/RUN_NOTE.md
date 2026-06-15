# 本次自动化运行说明

- 运行时间：2026-05-25 15:57（Asia/Shanghai）
- 交付目录：`cg_task/output/202605251557`
- 输入文件：`cg_task/file/stock_list.csv`
- 样本数量：129
- 运行结果：失败
- 分析日期参数：`2026-05-25`

## 数据口径

- 基本面：`akshare.stock_financial_abstract_new_ths`
- 实时快照：`akshare.stock_individual_spot_xq`
- 趋势日线：`akshare.stock_zh_a_daily`
- 结果有效性检查：首只样本探测未拿到实时快照、日线或财务摘要

## 文件说明

- `stock_list_scored_*.csv`：批量评分明细表
- `stock_list_scored_*.xlsx`：Excel 版本明细表
- `stock_list_scored_*.json`：结构化结果
- `stock_list_scoring_report_*.md`：评分标准、Top 排名和异常样本说明

## 执行备注

```text
(no stdout)
```

```text
首只样本探测未拿到实时快照、日线或财务摘要
```
