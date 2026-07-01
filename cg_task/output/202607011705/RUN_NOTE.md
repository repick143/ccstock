# 本次自动化运行说明

- 运行时间：2026-07-01 17:05（Asia/Shanghai）
- 交付目录：`cg_task/output/202607011705`
- 输入文件：`cg_task/file/stock_list(2).csv`
- 样本数量：154
- 唯一股票代码：152
- 唯一股票名称：152
- 重复股票代码：`688362`、`688372`
- 重复股票名称：`伟测科技`、`甬矽电子`
- 空白字段检查：无
- 运行结果：成功，已更新评分/目标价并刷新 profile 短期预测；实时快照接口异常已在报告和 profile 中标注
- 分析日期参数：`2026-07-01`
- Python/akshare：`/usr/bin/python3, akshare 1.18.62`

## 数据口径

- 基本面：`akshare.stock_financial_abstract_new_ths`
- 实时快照：`akshare.stock_zh_a_spot_em`（本轮接口返回 `RemoteDisconnected`，未取得全市场快照）
- 趋势日线：`akshare.stock_zh_a_daily`
- 结果有效性检查：日线现价 154/154，信号价 154/154，MA20 154/154，毛利率 154/154，ROE 154/154。

## 文件说明

- `stock_list_scored_20260701.csv`：本轮交付表备份。
- `stock_list_scored_20260701.xlsx`：Excel 版本交付表。
- `stock_list_scored_20260701.json`：保留全部抓取字段、评分细项与错误信息的结构化明细。
- `stock_list_scoring_report_20260701.md`：评分标准、Top 排名、异常样本和数据完整性说明。
- `cg_task/file/stock_list(2).csv`：已按本轮有效结果回填。

## Profile 更新

- 已更新 152 个 profile；新增 0 个 profile。
- 每个 profile 已追加 `2026-07-01 17:05 CST 预测更新`，并将顶部摘要、核心指标、资料来源和数据异常说明刷新到本轮口径。

## 综合排名 Top 10

- 688008 澜起科技：综合 80.7，短线 86，目标价 404.91 元
- 603986 兆易创新：综合 79.8，短线 79.9，目标价 988.37 元
- 300604 长川科技：综合 78.8，短线 76.1，目标价 425.25 元
- 301308 江波龙：综合 78.5，短线 74.6，目标价 853.43 元
- 688146 中船特气：综合 77.7，短线 88.7，目标价 442.05 元
- 688525 佰维存储：综合 76.7，短线 69.8，目标价 587.22 元
- 300666 江丰电子：综合 75.6，短线 77.1，目标价 474.56 元
- 688072 拓荆科技：综合 75.4，短线 72.8，目标价 1041.58 元
- 300054 鼎龙股份：综合 74.8，短线 74，目标价 125.05 元
- 300408 三环集团：综合 74.7，短线 82.8，目标价 202.66 元

## 异常说明

- 全市场实时快照 `akshare.stock_zh_a_spot_em` 返回 `RemoteDisconnected`；本轮总市值、PE、PB 对 154/154 样本缺失。
- 已使用 `akshare.stock_zh_a_daily` 最新日线收盘价作为现价/信号价，并使用日线成交额、换手率参与短线评分。
- 日线日期分布：{'2026-07-01': 153, '2026-06-26': 1}。
- 财务摘要全部可用：{'2026-03-31': 154}。

## 执行备注

```text
[WARN] 全市场实时快照抓取失败: ConnectionError(ProtocolError('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')))
[DONE] profile 更新完成：152 个。
```
