# 本次自动化运行说明

- 运行时间：2026-05-28 17:10 CST
- 输入文件：`cg_task/file/stock_list(2).csv`
- 样本数量：154 行，152 个唯一股票代码
- 现场跑批目录：`cg_task/output/202605281703`
- 现场跑批结果：失败，实时快照、Sina 日线、同花顺财务均未成功刷新
- 实际采用底稿：`cg_task/output/202605281522`，同日有效批量结果，覆盖目标文件全部唯一股票代码

## 数据异常

17:03 针对 `stock_list(2).csv` 直接调用 `akshare.stock_individual_spot_xq`、`akshare.stock_zh_a_daily`、`akshare.stock_financial_abstract_new_ths` 时，`xueqiu.com`、`finance.sina.com.cn`、`basic.10jqka.com.cn` 均出现 DNS 解析失败。该目录下生成的评分文件不作为本轮回填依据。

## 本轮写入

- 已刷新 `cg_task/file/stock_list(2).csv` 的涨幅、基本面/短线/长线打分、目标价和备注字段。
- 已为 152 个 profile 追加 `2026-05-28 17:10 CST 预测更新`，并与 2026-05-26/2026-05-27 前序预测做回归对比。
