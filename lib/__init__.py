"""ccstock 数据访问库。

提供统一的数据层，优先读 MySQL，缺失自动从 mootdx 补全并落库。

用法：
    from lib import DailyMarket

    dm = DailyMarket()
    df = dm.bars("601869", offset=800)       # 与 mootdx 接口一致
    df = dm.bars_years("601869", years=2)    # 按年获取
"""

from .stock_daily import DailyMarket

__all__ = ["DailyMarket"]
