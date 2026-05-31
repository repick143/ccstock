"""lib.config 配置加载模块单测。"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import lib.config


class TestGetConfig:
    """get_config() 功能测试。"""

    def test_load_valid_config(self, tmp_path):
        """正常 TOML 配置文件应能正确解析。"""
        cfg_file = tmp_path / "config.toml"
        cfg_file.write_text(
            "[database]\nhost = \"db_host\"\nport = 3306\n\n"
            "[mootdx]\nmarket = \"ext\"\ntimeout = 15\n\n"
            "[etl]\ndefault_years = 3\n",
            encoding="utf-8",
        )
        with patch.object(lib.config, "CONFIG_PATH", cfg_file):
            lib.config._config_cache = None
            cfg = lib.config.get_config()

        assert cfg["database"]["host"] == "db_host"
        assert cfg["database"]["port"] == 3306
        assert cfg["mootdx"]["market"] == "ext"
        assert cfg["mootdx"]["timeout"] == 15
        assert cfg["etl"]["default_years"] == 3

    def test_file_not_found(self):
        """配置文件不存在时应返回空字典，不抛异常。"""
        with patch.object(lib.config, "CONFIG_PATH", Path("/nonexistent/path/config.toml")):
            lib.config._config_cache = None
            cfg = lib.config.get_config()
        assert cfg == {}

    def test_invalid_toml(self, tmp_path):
        """配置内容是非法 TOML 时应返回空字典。"""
        cfg_file = tmp_path / "config.toml"
        cfg_file.write_text("garbage [[[ = 1", encoding="utf-8")
        with patch.object(lib.config, "CONFIG_PATH", cfg_file):
            lib.config._config_cache = None
            cfg = lib.config.get_config()
        assert cfg == {}

    def test_cache_works(self, tmp_path):
        """多次调用应命中缓存，不会重复读取文件。"""
        cfg_file = tmp_path / "config.toml"
        cfg_file.write_text("[database]\nhost = \"cached\"\n", encoding="utf-8")

        with patch.object(lib.config, "CONFIG_PATH", cfg_file):
            lib.config._config_cache = None
            cfg1 = lib.config.get_config()
            assert cfg1["database"]["host"] == "cached"

            # 修改文件内容
            cfg_file.write_text("[database]\nhost = \"changed\"\n", encoding="utf-8")
            cfg2 = lib.config.get_config()
            # 应命中缓存，仍是旧值
            assert cfg2["database"]["host"] == "cached"


class TestHelperFunctions:
    """get_database_config() / get_mootdx_config() 辅助函数测试。"""

    def test_get_database_config(self, tmp_path):
        cfg_file = tmp_path / "config.toml"
        cfg_file.write_text("[database]\nhost = \"x\"\nport = 1234\n", encoding="utf-8")
        with patch.object(lib.config, "CONFIG_PATH", cfg_file):
            lib.config._config_cache = None
            db_cfg = lib.config.get_database_config()
        assert db_cfg["host"] == "x"
        assert db_cfg["port"] == 1234

    def test_get_mootdx_config(self, tmp_path):
        cfg_file = tmp_path / "config.toml"
        cfg_file.write_text("[mootdx]\nmarket = \"std\"\ntimeout = 9\n", encoding="utf-8")
        with patch.object(lib.config, "CONFIG_PATH", cfg_file):
            lib.config._config_cache = None
            mdx_cfg = lib.config.get_mootdx_config()
        assert mdx_cfg["market"] == "std"
        assert mdx_cfg["timeout"] == 9
