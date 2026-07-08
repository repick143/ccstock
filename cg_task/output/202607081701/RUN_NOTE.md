# 本次自动化运行说明

- 运行时间：2026-07-08 17:01（Asia/Shanghai）
- 交付目录：`cg_task/output/202607081701`
- 输入文件：`cg_task/file/stock_list(2).csv`
- 样本数量：154
- 唯一股票代码：152
- 唯一股票名称：152
- 重复股票代码：`688362`、`688372`
- 重复股票名称：`伟测科技`、`甬矽电子`
- 空白字段检查：无
- 运行结果：成功，已更新评分/目标价并刷新 profile 短期预测；实时快照接口异常已在报告和 profile 中标注
- 分析日期参数：`2026-07-08`
- Python/akshare：`/Library/Developer/CommandLineTools/usr/bin/python3, akshare 1.18.62`

## 数据口径

- 基本面：`akshare.stock_financial_abstract_new_ths`
- 实时快照：`akshare.stock_zh_a_spot_em`（本轮接口返回 `RemoteDisconnected`，未取得全市场快照）
- 趋势日线：`akshare.stock_zh_a_daily`
- 结果有效性检查：日线现价 154/154，信号价 154/154，MA20 154/154，毛利率 154/154，ROE 154/154。

## 文件说明

- `stock_list_scored_20260708.csv`：本轮交付表备份。
- `stock_list_scored_20260708.xlsx`：Excel 版本交付表。
- `stock_list_scored_20260708.json`：保留全部抓取字段、评分细项与错误信息的结构化明细。
- `stock_list_scoring_report_20260708.md`：评分标准、Top 排名、异常样本和数据完整性说明。
- `cg_task/file/stock_list(2).csv`：已按本轮有效结果回填。

## Profile 更新

- 已更新 152 个 profile；新增 0 个 profile。
- 每个 profile 已追加 `2026-07-08 17:01 CST 预测更新`，并将顶部摘要、核心指标、资料来源和数据异常说明刷新到本轮口径。

## 综合排名 Top 10

- 688072 拓荆科技：综合 77.6，短线 75.3，目标价 1053.02 元
- 300604 长川科技：综合 77.5，短线 70.8，目标价 402.46 元
- 688347 华虹公司：综合 74，短线 79.2，目标价 439.83 元
- 688120 华海清科：综合 71.8，短线 67.2，目标价 337.98 元
- 300567 精测电子：综合 71.5，短线 68.7，目标价 338.47 元
- 688432 有研硅：综合 71.3，短线 73.6，目标价 47.02 元
- 688362 甬矽电子：综合 70.8，短线 83.1，目标价 109.51 元
- 688361 中科飞测：综合 70.4，短线 63.6，目标价 430.32 元
- 002185 华天科技：综合 70.3，短线 79.7，目标价 25.9 元
- 688146 中船特气：综合 70.2，短线 73.6，目标价 372.41 元

## 异常说明

- 全市场实时快照 `akshare.stock_zh_a_spot_em` 返回 `RemoteDisconnected`；本轮总市值、PE、PB 对 154/154 样本缺失。
- 已使用 `akshare.stock_zh_a_daily` 最新日线收盘价作为现价/信号价，并使用日线成交额、换手率参与短线评分。
- 日线日期分布：{'2026-06-26': 1, '2026-07-08': 153}。
- 财务摘要全部可用：{'2026-03-31': 154}。

## 执行备注

```text
[WARN] 全市场实时快照抓取失败: ConnectionError(ProtocolError('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')))
[DONE] profile 更新完成：152 个，新增 0 个。
```
