# 本次自动化运行说明

- 运行时间：2026-07-18 17:02（Asia/Shanghai）
- 交付目录：`cg_task/output/202607181702`
- 输入文件：`cg_task/file/stock_list(2).csv`
- 样本数量：154
- 唯一股票代码：152
- 唯一股票名称：152
- 重复股票代码：`688362`、`688372`
- 重复股票名称：`伟测科技`、`甬矽电子`
- 空白字段检查：无
- 运行结果：成功，已更新评分/目标价并刷新 profile 短期预测；实时快照接口异常已在报告和 profile 中标注
- 分析日期参数：`2026-07-18`
- Python/akshare：`/Users/chenchen/.pyenv/versions/3.10.15/bin/python, akshare 1.18.62`

## 数据口径

- 基本面：`akshare.stock_financial_abstract_new_ths`
- 实时快照：`akshare.stock_zh_a_spot_em`（本轮接口返回 `RemoteDisconnected`，未取得全市场快照）
- 趋势日线：`akshare.stock_zh_a_daily`
- 结果有效性检查：日线现价 154/154，信号价 154/154，MA20 154/154，毛利率 154/154，ROE 154/154。

## 文件说明

- `stock_list_scored_20260718.csv`：本轮交付表备份。
- `stock_list_scored_20260718.xlsx`：Excel 版本交付表。
- `stock_list_scored_20260718.json`：保留全部抓取字段、评分细项与错误信息的结构化明细。
- `stock_list_scoring_report_20260718.md`：评分标准、Top 排名、异常样本和数据完整性说明。
- `cg_task/file/stock_list(2).csv`：已按本轮有效结果回填。

## Profile 更新

- 已更新 152 个 profile；新增 0 个 profile。
- 每个 profile 已追加 `2026-07-18 17:02 CST 预测更新`，并将顶部摘要、核心指标、资料来源和数据异常说明刷新到本轮口径。

## 综合排名 Top 10

- 688498 源杰科技：综合 64.8，短线 40，目标价 1987.86 元
- 688072 拓荆科技：综合 63，短线 43.8，目标价 827.71 元
- 300604 长川科技：综合 62.6，短线 43.6，目标价 329.69 元
- 603893 瑞芯微：综合 61.3，短线 50.7，目标价 235.34 元
- 688146 中船特气：综合 61.3，短线 62.5，目标价 268.98 元
- 603986 兆易创新：综合 60.8，短线 55.3，目标价 540.1 元
- 002384 东山精密：综合 59.3，短线 42.3，目标价 278.37 元
- 688347 华虹公司：综合 58.8，短线 50，目标价 352.45 元
- 300567 精测电子：综合 58.6，短线 47.9，目标价 252.06 元
- 688627 精智达：综合 57.7，短线 46.7，目标价 582.2 元

## 异常说明

- 全市场实时快照 `akshare.stock_zh_a_spot_em` 返回 `RemoteDisconnected`；本轮总市值、PE、PB 对 154/154 样本缺失。
- 已使用 `akshare.stock_zh_a_daily` 最新日线收盘价作为现价/信号价，并使用日线成交额、换手率参与短线评分。
- 日线日期分布：{'2026-07-17': 154}。
- 日线异常 0/154：无。
- 财务摘要异常 0/154：无。
- 财报期分布：{'2026-03-31': 154}。

## 执行备注

```text
[WARN] 全市场实时快照抓取失败: ConnectionError(ProtocolError('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')))
[DONE] profile 更新完成：152 个，新增 0 个。
```
