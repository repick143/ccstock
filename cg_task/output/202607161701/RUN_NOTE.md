# 本次自动化运行说明

- 运行时间：2026-07-16 17:01（Asia/Shanghai）
- 交付目录：`cg_task/output/202607161701`
- 输入文件：`cg_task/file/stock_list(2).csv`
- 样本数量：154
- 唯一股票代码：152
- 唯一股票名称：152
- 重复股票代码：`688362`、`688372`
- 重复股票名称：`伟测科技`、`甬矽电子`
- 空白字段检查：无
- 运行结果：成功，已更新评分/目标价并刷新 profile 短期预测；实时快照接口异常已在报告和 profile 中标注
- 分析日期参数：`2026-07-16`
- Python/akshare：`/Users/chenchen/.pyenv/versions/3.10.15/bin/python, akshare 1.18.62`

## 数据口径

- 基本面：`akshare.stock_financial_abstract_new_ths`
- 实时快照：`akshare.stock_zh_a_spot_em`（本轮接口返回 `RemoteDisconnected`，未取得全市场快照）
- 趋势日线：`akshare.stock_zh_a_daily`
- 结果有效性检查：日线现价 154/154，信号价 154/154，MA20 154/154，毛利率 152/154，ROE 152/154。

## 文件说明

- `stock_list_scored_20260716.csv`：本轮交付表备份。
- `stock_list_scored_20260716.xlsx`：Excel 版本交付表。
- `stock_list_scored_20260716.json`：保留全部抓取字段、评分细项与错误信息的结构化明细。
- `stock_list_scoring_report_20260716.md`：评分标准、Top 排名、异常样本和数据完整性说明。
- `cg_task/file/stock_list(2).csv`：已按本轮有效结果回填。

## Profile 更新

- 已更新 152 个 profile；新增 0 个 profile。
- 每个 profile 已追加 `2026-07-16 17:01 CST 预测更新`，并将顶部摘要、核心指标、资料来源和数据异常说明刷新到本轮口径。

## 综合排名 Top 10

- 688498 源杰科技：综合 76.2，短线 63.9，目标价 2308.5 元
- 002384 东山精密：综合 73.3，短线 74.5，目标价 330.07 元
- 002156 通富微电：综合 71.2，短线 81.2，目标价 91.51 元
- 688072 拓荆科技：综合 70.5，短线 59.3，目标价 885.35 元
- 603893 瑞芯微：综合 69.5，短线 69.8，目标价 268.98 元
- 688347 华虹公司：综合 66.8，短线 65.7，目标价 388.81 元
- 300567 精测电子：综合 66.6，短线 61.1，目标价 292 元
- 688802 沐曦股份：综合 66，短线 53.7，目标价 1067.33 元
- 300604 长川科技：综合 65.5，短线 51.2，目标价 351.37 元
- 300502 新易盛：综合 64.5，短线 50.9，目标价 646.91 元

## 异常说明

- 全市场实时快照 `akshare.stock_zh_a_spot_em` 返回 `RemoteDisconnected`；本轮总市值、PE、PB 对 154/154 样本缺失。
- 已使用 `akshare.stock_zh_a_daily` 最新日线收盘价作为现价/信号价，并使用日线成交额、换手率参与短线评分。
- 日线日期分布：{'2026-07-16': 154}。
- 财务摘要异常 2/154：300331 苏大维格：JSONDecodeError('Expecting value: line 1 column 1 (char 0)')；301511 德福科技：JSONDecodeError('Expecting value: line 1 column 1 (char 0)')。
- 财报期分布：{'2026-03-31': 152}。

## 执行备注

```text
[WARN] 全市场实时快照抓取失败: ConnectionError(ProtocolError('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')))
[DONE] profile 更新完成：152 个，新增 0 个。
```
