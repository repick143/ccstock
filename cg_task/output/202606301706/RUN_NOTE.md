# 本次自动化运行说明

- 运行时间：2026-06-30 17:06（Asia/Shanghai）
- 交付目录：`cg_task/output/202606301706`
- 输入文件：`cg_task/file/stock_list(2).csv`
- 样本数量：154
- 唯一股票代码：152
- 唯一股票名称：152
- 重复股票代码：`688362`, `688372`
- 空白字段检查：无
- 运行结果：成功，已更新评分/目标价并刷新 profile 短期预测；实时快照接口异常已在报告和 profile 中标注
- 分析日期参数：`2026-06-30`
- Python/akshare：`/Users/chenchen/.pyenv/versions/3.10.15/bin/python, akshare 1.18.62`

## 数据口径

- 基本面：`akshare.stock_financial_abstract_new_ths`
- 实时快照：`akshare.stock_zh_a_spot_em`（本轮接口返回 `RemoteDisconnected`，未取得全市场快照）
- 趋势日线：`akshare.stock_zh_a_daily`
- 结果有效性检查：日线现价 154/154，信号价 154/154，MA20 154/154，毛利率 154/154，ROE 154/154。

## 文件说明

- `stock_list_scored_20260630.csv`：本轮交付表备份。
- `stock_list_scored_20260630.xlsx`：Excel 版本交付表。
- `stock_list_scored_20260630.json`：保留全部抓取字段、评分细项与错误信息的结构化明细。
- `stock_list_scoring_report_20260630.md`：评分标准、Top 排名、异常样本和数据完整性说明。
- `cg_task/file/stock_list(2).csv`：已按本轮有效结果回填。

## Profile 更新

- 已更新 152 个 profile；新增 0 个 profile。
- 每个 profile 已追加 `2026-06-30 17:06 CST 预测更新`，并将顶部摘要、核心指标、资料来源和数据异常说明刷新到本轮口径。

## 综合排名 Top 10

- 603986 兆易创新：综合 82.7，短线 84.5，目标价 1057.5 元
- 688008 澜起科技：综合 80.4，短线 87.0，目标价 396.52 元
- 301308 江波龙：综合 79.7，短线 77.2，目标价 904.1 元
- 688525 佰维存储：综合 79.1，短线 72.7，目标价 634.57 元
- 300604 长川科技：综合 78.5，短线 74.8，目标价 434.87 元
- 688498 源杰科技：综合 77.9，短线 71.1，目标价 2399.09 元
- 688256 寒武纪：综合 76.4，短线 74.2，目标价 2011.51 元
- 300054 鼎龙股份：综合 75.2，短线 74.5，目标价 132.35 元
- 688072 拓荆科技：综合 75.1，短线 73.5，目标价 1039.79 元
- 300666 江丰电子：综合 74.8，短线 77.7，目标价 441.56 元

## 异常说明

- 全市场实时快照 `akshare.stock_zh_a_spot_em` 两次均返回 `RemoteDisconnected`；本轮总市值、PE、PB 对 154/154 样本缺失。
- 已使用 `akshare.stock_zh_a_daily` 最新日线收盘价作为现价/信号价，并使用日线成交额、换手率参与短线评分。
- 拓荆科技日线日期为 2026-06-26；其余 153 行日线日期为 2026-06-30。
- 财务摘要全部可用：154/154 财报期为 2026-03-31。

## 执行备注

```text
[WARN] 全市场实时快照抓取失败: ConnectionError(ProtocolError('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')))
[DONE] CSV: /Users/chenchen/codexwork/ccstock/cg_task/output/202606301706/stock_list_scored_20260630.csv
[DONE] XLSX: /Users/chenchen/codexwork/ccstock/cg_task/output/202606301706/stock_list_scored_20260630.xlsx
[DONE] JSON: /Users/chenchen/codexwork/ccstock/cg_task/output/202606301706/stock_list_scored_20260630.json
[DONE] MD: /Users/chenchen/codexwork/ccstock/cg_task/output/202606301706/stock_list_scoring_report_20260630.md
[DONE] profile 更新完成：152 个。
```
