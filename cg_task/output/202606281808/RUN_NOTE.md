# 本次自动化运行说明

- 运行时间：2026-06-28 18:08（Asia/Shanghai）
- 交付目录：`cg_task/output/202606281808`
- 输入文件：`cg_task/file/stock_list(2).csv`
- 样本数量：154
- 唯一股票代码：152
- 唯一股票名称：152
- 重复股票代码：`688362`, `688372`
- 空白字段检查：无
- 运行结果：成功，已更新评分/目标价并刷新 profile 短期预测
- 分析日期参数：`2026-06-28`
- Python/akshare：`/Library/Developer/CommandLineTools/usr/bin/python3, akshare 1.18.62`

## 数据口径

- 基本面：`akshare.stock_financial_abstract_new_ths`
- 实时快照：`akshare.stock_zh_a_spot_em`（一次性拉取全市场快照后按代码映射）
- 趋势日线：`akshare.stock_zh_a_daily`
- 结果有效性检查：现价 154/154，信号价 152/154，MA20 152/154，毛利率 153/154，ROE 153/154。

## 文件说明

- `stock_list_scored_20260628.csv`：本轮交付表备份。
- `stock_list_scored_20260628.xlsx`：Excel 版本交付表。
- `stock_list_scored_20260628.json`：保留全部抓取字段、评分细项与错误信息的结构化明细。
- `stock_list_scoring_report_20260628.md`：评分标准、Top 排名和异常样本说明。
- `cg_task/file/stock_list(2).csv`：已按本轮有效结果回填；光华科技、兴福电子因日线超时保留上一有效目标价并在备注标注。

## Profile 更新

- 已更新 152 个 profile；新增 0 个 profile。
- 每个 profile 已追加 `2026-06-28 18:08 CST 预测更新/复核`，并将顶部摘要、核心指标、资料来源和数据异常说明刷新到本轮口径。

## 综合排名 Top 10

- 301308 江波龙：综合 88.4，短线 84.3，目标价 999.79 元
- 688525 佰维存储：综合 87.9，短线 77.4，目标价 738.6 元
- 603986 兆易创新：综合 85.3，短线 85.4，目标价 1016.02 元
- 300604 长川科技：综合 81.6，短线 77.2，目标价 383.17 元
- 688072 拓荆科技：综合 79.8，短线 73.9，目标价 1071.99 元
- 300373 扬杰科技：综合 78.8，短线 72.1，目标价 179.89 元
- 300054 鼎龙股份：综合 78.5，短线 71.9，目标价 121.9 元
- 300666 江丰电子：综合 78.1，短线 75.4，目标价 435.88 元
- 002008 大族激光：综合 77.9，短线 85.9，目标价 189.93 元
- 603203 快克智能：综合 77.7，短线 72.2，目标价 90.33 元

## 异常说明

- 002741 光华科技：日线：FetchTimeoutError('request timed out')
- 688545 兴福电子：日线：FetchTimeoutError('request timed out')
- 300502 新易盛：财务：FetchTimeoutError('request timed out')

## 执行备注

```text
[INFO] 已加载实时快照 5867 条
[DONE] CSV: /Users/chenchen/codexwork/ccstock/cg_task/output/202606281808/stock_list_scored_20260628.csv
[DONE] XLSX: /Users/chenchen/codexwork/ccstock/cg_task/output/202606281808/stock_list_scored_20260628.xlsx
[DONE] JSON: /Users/chenchen/codexwork/ccstock/cg_task/output/202606281808/stock_list_scored_20260628.json
[DONE] MD: /Users/chenchen/codexwork/ccstock/cg_task/output/202606281808/stock_list_scoring_report_20260628.md
[DONE] profile 更新完成：152 个。
```
