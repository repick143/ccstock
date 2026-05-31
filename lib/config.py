"""配置加载模块。

自动读取项目根目录 conf/config.toml，提供全局配置缓存。
"""

import sys
import tomllib
from pathlib import Path

# 项目根目录：lib/ 的上一级
ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "conf" / "config.toml"

_config_cache: dict | None = None


def get_config() -> dict:
    """加载配置文件（带缓存），失败时返回空字典。"""
    global _config_cache
    if _config_cache is not None:
        return _config_cache

    if not CONFIG_PATH.exists():
        print(f"[lib.config] 配置文件不存在: {CONFIG_PATH}", file=sys.stderr)
        _config_cache = {}
        return _config_cache

    try:
        with open(CONFIG_PATH, "rb") as f:
            _config_cache = tomllib.load(f)
    except Exception as e:
        print(f"[lib.config] 配置文件解析失败: {e}", file=sys.stderr)
        _config_cache = {}

    return _config_cache


def get_database_config() -> dict:
    """获取 MySQL 数据库配置段。"""
    return get_config().get("database", {})


def get_mootdx_config() -> dict:
    """获取 mootdx 行情服务器配置段。"""
    return get_config().get("mootdx", {})
