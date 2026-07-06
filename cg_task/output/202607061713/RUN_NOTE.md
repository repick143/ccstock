# 本次自动化运行说明

- 运行时间：2026-07-06 17:13（Asia/Shanghai）
- 交付目录：`cg_task/output/202607061713`
- 输入文件：`cg_task/file/stock_list(2).csv`
- 样本数量：154
- 唯一股票代码：152
- 唯一股票名称：152
- 重复股票代码：`688362`、`688372`
- 重复股票名称：`伟测科技`、`甬矽电子`
- 空白字段检查：无
- 运行结果：成功，已更新评分/目标价并刷新 profile 短期预测；实时快照接口异常已在报告和 profile 中标注
- 分析日期参数：`2026-07-06`
- Python/akshare：`/Library/Developer/CommandLineTools/usr/bin/python3, akshare 1.18.62`

## 数据口径

- 基本面：`akshare.stock_financial_abstract_new_ths`
- 实时快照：`akshare.stock_zh_a_spot_em`（本轮接口返回 `RemoteDisconnected`，未取得全市场快照）
- 趋势日线：`akshare.stock_zh_a_daily`
- 结果有效性检查：日线现价 154/154，信号价 154/154，MA20 154/154，毛利率 154/154，ROE 154/154。

## 文件说明

- `stock_list_scored_20260706.csv`：本轮交付表备份。
- `stock_list_scored_20260706.xlsx`：Excel 版本交付表。
- `stock_list_scored_20260706.json`：保留全部抓取字段、评分细项与错误信息的结构化明细。
- `stock_list_scoring_report_20260706.md`：评分标准、Top 排名、异常样本和数据完整性说明。
- `cg_task/file/stock_list(2).csv`：已按本轮有效结果回填。

## Profile 更新

- 已更新 152 个 profile；新增 0 个 profile。
- 每个 profile 已追加 `2026-07-06 17:13 CST 预测更新`，并将顶部摘要、核心指标、资料来源和数据异常说明刷新到本轮口径。

## 综合排名 Top 10

- 301308 江波龙：综合 81.1，短线 78.2，目标价 881.64 元
- 688072 拓荆科技：综合 76.8，短线 74.4，目标价 1048.9 元
- 688525 佰维存储：综合 75.1，短线 62.7，目标价 573.31 元
- 300604 长川科技：综合 73.5，短线 61，目标价 379.03 元
- 603986 兆易创新：综合 73，短线 65，目标价 813.09 元
- 688008 澜起科技：综合 72.2，短线 65，目标价 332.01 元
- 603078 江化微：综合 71.5，短线 80.8，目标价 64.83 元
- 688362 甬矽电子：综合 71，短线 82.6，目标价 107.32 元
- 688012 中微公司：综合 70，短线 64.1，目标价 510.7 元
- 688362 甬矽电子：综合 69.8，短线 82.6，目标价 106.31 元

## 异常说明

- 全市场实时快照 `akshare.stock_zh_a_spot_em` 返回 `RemoteDisconnected`；本轮总市值、PE、PB 对 154/154 样本缺失。
- 已使用 `akshare.stock_zh_a_daily` 最新日线收盘价作为现价/信号价，并使用日线成交额、换手率参与短线评分。
- 日线日期分布：{'2026-06-26': 1, '2026-07-06': 153}。
- 财务摘要全部可用：{'2026-03-31': 154}。

## 执行备注

```text
[WARN] 全市场实时快照抓取失败: ConnectionError(ProtocolError('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')))
[DONE] profile 更新完成：152 个，新增 0 个。
```
