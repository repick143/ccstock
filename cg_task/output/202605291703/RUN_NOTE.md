# 本次自动化运行说明

- 运行时间：2026-05-29 17:03 CST
- 交付目录：`cg_task/output/202605291703`
- 输入文件：`cg_task/file/stock_list(2).csv`
- 样本数量：154 行，152 个唯一股票代码
- 运行结果：失败，未取得新的有效行情/日线/财务数据
- 分析日期参数：`2026-05-29`
- 实际采用底稿：沿用 `cg_task/output/202605281522` 的 2026-05-28 有效结果

## 数据口径

- 基本面：`akshare.stock_financial_abstract_new_ths`
- 实时快照：`akshare.stock_individual_spot_xq`
- 趋势日线：`akshare.stock_zh_a_daily`
- 有效性检查：现价 0/154，MA20 0/154，毛利率 0/154，ROE 0/154

## 数据异常

- `xueqiu.com` DNS 解析失败，雪球实时快照不可用，异常样本 154/154。
- `finance.sina.com.cn` DNS 解析失败，Sina 日线不可用，异常样本 154/154。
- `basic.10jqka.com.cn` DNS 解析失败，同花顺财务摘要不可用，异常样本 154/154。
- 本次跑批产出的评分 CSV/XLSX/JSON/MD 未通过有效性校验，已删除，避免误用无效评分。

## 本轮写入

- `cg_task/file/stock_list(2).csv` 仅在 `备注` 字段追加本轮复核失败说明；未覆盖 2026-05-28 的有效评分、目标价和短期判断。
- 已为 152 个 profile 追加 `2026-05-29 17:03 CST 预测复核`，说明本轮无法完成行情回归，短期框架沿用上一有效底稿。
