## 运行结果

- 时间：2026-06-05 16:02 CST
- 输入文件：`cg_task/file/stock_list.csv`
- 股票数量：176
- 结果：本次运行失败，未产出可用评分文件；已删除本次无效 CSV/XLSX/JSON/Markdown 输出，仅保留本说明。

## 根因

- `akshare.stock_individual_spot_xq` 依赖的 `xueqiu.com` DNS 解析失败。
- `akshare.stock_zh_a_daily` 依赖的 `finance.sina.com.cn` DNS 解析失败。
- `akshare.stock_financial_abstract_new_ths` 依赖的 `basic.10jqka.com.cn` DNS 解析失败。

## 验证结果

- 176/176 只股票的实时快照、日线、财务摘要字段均未成功获取。
- 本次生成文件中：
  - `现价`、`信号价`、`MA20`、`总市值_亿元`、`市盈率_TTM`、`毛利率`、`ROE`、`营收同比`、`归母净利润同比` 的有效数均为 0。
  - `基本面打分`、`短线打分`、`长线打分` 虽被脚本回填，但仅基于缺失数据下的默认兜底逻辑，不可作为有效分析结果。

## 处理原则

- 按要求未复用历史成功结果。
- 按要求尽可能完成抓取，单只失败未中断整体执行。
- 因所有上游数据源均不可用，本次直接报错处理，不提交、不推送。
