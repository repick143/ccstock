# 本次自动化运行说明

- 运行时间：2026-07-03 17:06（Asia/Shanghai）
- 交付目录：`cg_task/output/202607031706`
- 输入文件：`cg_task/file/stock_list(2).csv`
- 样本数量：154
- 唯一股票代码：152
- 唯一股票名称：152
- 重复股票代码：`688362`、`688372`
- 重复股票名称：`伟测科技`、`甬矽电子`
- 空白字段检查：无
- 运行结果：成功，已更新评分/目标价并刷新 profile 短期预测；实时快照接口异常已在报告和 profile 中标注
- 分析日期参数：`2026-07-03`
- Python/akshare：`/usr/bin/python3, akshare 1.18.62`

## 数据口径

- 基本面：`akshare.stock_financial_abstract_new_ths`
- 实时快照：`akshare.stock_zh_a_spot_em`（本轮接口返回 `RemoteDisconnected`，未取得全市场快照）
- 趋势日线：`akshare.stock_zh_a_daily`
- 结果有效性检查：日线现价 154/154，信号价 154/154，MA20 154/154，毛利率 154/154，ROE 154/154。

## 文件说明

- `stock_list_scored_20260703.csv`：本轮交付表备份。
- `stock_list_scored_20260703.xlsx`：Excel 版本交付表。
- `stock_list_scored_20260703.json`：保留全部抓取字段、评分细项与错误信息的结构化明细。
- `stock_list_scoring_report_20260703.md`：评分标准、Top 排名、异常样本和数据完整性说明。
- `cg_task/file/stock_list(2).csv`：已按本轮有效结果回填。

## Profile 更新

- 已更新 152 个 profile；新增 0 个 profile。
- 每个 profile 已追加 `2026-07-03 17:06 CST 预测更新`，并将顶部摘要、核心指标、资料来源和数据异常说明刷新到本轮口径。

## 综合排名 Top 10

- 688072 拓荆科技：综合 76.8，短线 74.4，目标价 1048.57 元
- 603986 兆易创新：综合 75.8，短线 73.7，目标价 851.92 元
- 301308 江波龙：综合 75.4，短线 66.3，目标价 779.48 元
- 300604 长川科技：综合 74.2，短线 64，目标价 378.48 元
- 688525 佰维存储：综合 72.5，短线 61.5，目标价 532.51 元
- 688008 澜起科技：综合 71.9，短线 70.1，目标价 328.36 元
- 603078 江化微：综合 71.3，短线 81.4，目标价 63.15 元
- 002916 深南电路：综合 70.8，短线 69.4，目标价 552.33 元
- 002409 雅克科技：综合 69.7，短线 78.4，目标价 223.24 元
- 600641 万业企业：综合 69.1，短线 69.5，目标价 53.05 元

## 异常说明

- 全市场实时快照 `akshare.stock_zh_a_spot_em` 返回 `RemoteDisconnected`；本轮总市值、PE、PB 对 154/154 样本缺失。
- 已使用 `akshare.stock_zh_a_daily` 最新日线收盘价作为现价/信号价，并使用日线成交额、换手率参与短线评分。
- 日线日期分布：{'2026-07-03': 153, '2026-06-26': 1}。
- 财务摘要全部可用：{'2026-03-31': 154}。

## 执行备注

```text
[WARN] 全市场实时快照抓取失败: ConnectionError(ProtocolError('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')))
[DONE] profile 更新完成：152 个，新增 0 个。
```
