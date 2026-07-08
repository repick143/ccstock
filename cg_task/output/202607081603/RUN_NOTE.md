# 本次自动化运行说明

- 运行时间：2026-07-08 16:03（Asia/Shanghai）
- 交付目录：`cg_task/output/202607081603`
- 输入文件：`cg_task/file/stock_list.csv`
- 样本数量：225
- 运行结果：成功
- 分析日期参数：`2026-07-08`

## 数据口径

- 基本面：`akshare.stock_financial_abstract_new_ths`
- 实时快照：`akshare.stock_zh_a_spot_em`
- 趋势日线：`akshare.stock_zh_a_daily`
- 结果有效性检查：现价 222/225，信号价 222/225，毛利率 225/225，MA20 222/225，财报期 225/225，ROE 225/225，营收同比 225/225，归母净利润同比 225/225，总市值 0/225，PE(TTM) 0/225

## 文件说明

- `stock_list_scored_20260708.csv`：仅回填原始 13 列的交付表，不新增列
- `stock_list_scored_20260708.xlsx`：Excel 版本交付表
- `stock_list_scored_20260708.json`：保留抓取字段、评分细项与错误信息的结构化明细
- `stock_list_scoring_report_20260708.md`：评分标准、Top 排名和异常样本说明
- `run.log`：本轮脚本执行日志

## 执行结论

- 本轮 225 行全部完成评分和备注填充，`基本面打分`、`短线打分`、`长线打分`、`备注` 全部写回。
- 由于原始交付表结构限制，任务要求的“中期走势”维度继续映射回历史列 `长线打分`。
- 全市场实时快照 `akshare.stock_zh_a_spot_em` 再次返回 `RemoteDisconnected`，因此 `总市值_亿元` 与 `市盈率_TTM` 在 JSON 明细中全部缺失；脚本按既定降级逻辑继续使用日线与财务摘要完成其余字段和评分。
- 日线与财务抓取整体有效，仅 3 行缺失现价/信号价/MA20，因此 `月涨幅(%)` 覆盖 222/225，`年涨幅(%)` 覆盖 207/225，`目标价` 覆盖 222/225。

## 主要异常

- `akshare.stock_zh_a_spot_em` 整体失败：`ConnectionError(ProtocolError('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')))`
- 受此影响：
  - `总市值_亿元`：0/225
  - `市盈率_TTM`：0/225
  - 全样本 `spot_error` 为“东方财富实时快照缺失”

## 产出文件

- CSV: `/Users/chenchen/codexwork/ccstock/cg_task/output/202607081603/stock_list_scored_20260708.csv`
- XLSX: `/Users/chenchen/codexwork/ccstock/cg_task/output/202607081603/stock_list_scored_20260708.xlsx`
- JSON: `/Users/chenchen/codexwork/ccstock/cg_task/output/202607081603/stock_list_scored_20260708.json`
- MD: `/Users/chenchen/codexwork/ccstock/cg_task/output/202607081603/stock_list_scoring_report_20260708.md`
