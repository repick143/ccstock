# 本次自动化运行说明

- 运行时间：2026-06-29 17:06（Asia/Shanghai）
- 交付目录：`cg_task/output/202606291706`
- 输入文件：`cg_task/file/stock_list(2).csv`
- 样本数量：154
- 唯一股票代码：152
- 唯一股票名称：152
- 重复股票代码：`688362`, `688372`
- 空白字段检查：无
- 运行结果：成功，已更新评分/目标价并刷新 profile 短期预测
- 分析日期参数：`2026-06-29`
- Python/akshare：`/Users/chenchen/.pyenv/versions/3.10.15/bin/python, akshare 1.18.62`

## 数据口径

- 基本面：`akshare.stock_financial_abstract_new_ths`
- 实时快照：`akshare.stock_zh_a_spot_em`（一次性拉取全市场快照后按代码映射）
- 趋势日线：`akshare.stock_zh_a_daily`
- 结果有效性检查：现价 154/154，信号价 154/154，MA20 154/154，毛利率 154/154，ROE 154/154。

## 文件说明

- `stock_list_scored_20260629.csv`：本轮交付表备份。
- `stock_list_scored_20260629.xlsx`：Excel 版本交付表。
- `stock_list_scored_20260629.json`：保留全部抓取字段、评分细项与错误信息的结构化明细。
- `stock_list_scoring_report_20260629.md`：评分标准、Top 排名、异常样本和数据完整性说明。
- `cg_task/file/stock_list(2).csv`：已按本轮有效结果回填。

## Profile 更新

- 已更新 152 个 profile；新增 0 个 profile。
- 每个 profile 已追加 `2026-06-29 17:06 CST 预测更新`，并将顶部摘要、核心指标、资料来源和数据异常说明刷新到本轮口径。

## 综合排名 Top 10

- 301308 江波龙：综合 87.4，短线 80，目标价 1060.43 元
- 688525 佰维存储：综合 87，短线 74.5，目标价 744.96 元
- 603986 兆易创新：综合 85.5，短线 85.1，目标价 1109.35 元
- 688008 澜起科技：综合 82.9，短线 87.1，目标价 385.19 元
- 300604 长川科技：综合 81.4，短线 76.5，目标价 410.8 元
- 300054 鼎龙股份：综合 80，短线 74.1，目标价 134.28 元
- 688072 拓荆科技：综合 78.8，短线 71.5，目标价 1067.16 元
- 688146 中船特气：综合 77.8，短线 90.9，目标价 402.1 元
- 603203 快克智能：综合 77.4，短线 71.5，目标价 94.96 元
- 300666 江丰电子：综合 77.1，短线 76.7，目标价 435.24 元

## 异常说明

- 接口抓取失败：无。
- 口径差异：拓荆科技日线日期为 2026-06-26；其余 153 行日线日期为 2026-06-29，需下次复核补齐。

## 执行备注

```text
[INFO] 已加载实时快照 5867 条
[DONE] CSV: /Users/chenchen/codexwork/ccstock/cg_task/output/202606291706/stock_list_scored_20260629.csv
[DONE] XLSX: /Users/chenchen/codexwork/ccstock/cg_task/output/202606291706/stock_list_scored_20260629.xlsx
[DONE] JSON: /Users/chenchen/codexwork/ccstock/cg_task/output/202606291706/stock_list_scored_20260629.json
[DONE] MD: /Users/chenchen/codexwork/ccstock/cg_task/output/202606291706/stock_list_scoring_report_20260629.md
[DONE] profile 更新完成：152 个。
```
