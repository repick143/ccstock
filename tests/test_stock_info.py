"""lib.stock_info unit tests."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

import lib.stock_info as stock_info
from lib.stock_info import get_stock_info


SAMPLE_STOCK_CODES = [
    "301236",
    "300496",
    "300339",
    "688039",
    "600797",
    "300212",
    "300598",
    "300560",
    "300975",
    "300433",
]


def make_stock_info_row(code: str) -> dict:
    return {
        "stock_code": code,
        "stock_name": f"测试{code}",
        "eps": None,
        "bvps": None,
        "roe": None,
        "net_profit": None,
        "revenue": None,
        "gross_margin": None,
        "net_margin": None,
        "debt_ratio": None,
        "report_period": date(2026, 3, 31),
    }


def make_concept_rows(code: str) -> list[dict]:
    return [
        {
            "concept_id": int(code[-3:]) + 1000,
            "concept_code": "302035",
            "concept_name": "人工智能",
            "source": "ths",
            "source_code": "302035",
        },
        {
            "concept_id": int(code[-3:]) + 2000,
            "concept_code": "309020",
            "concept_name": "信创",
            "source": "ths",
            "source_code": "309020",
        },
    ]


@pytest.fixture(autouse=True)
def reset_stock_info_db():
    stock_info._db = None
    yield
    stock_info._db = None


@pytest.fixture
def mock_stock_info_db():
    with patch("lib.stock_info._connect") as mock_connect:
        conn = MagicMock()
        conn.open = True
        cursor = MagicMock()
        conn.cursor.return_value.__enter__.return_value = cursor
        mock_connect.return_value = conn
        yield cursor, conn


@pytest.mark.parametrize("code", SAMPLE_STOCK_CODES)
def test_get_stock_info_includes_concepts_for_sample_stocks(mock_stock_info_db, code):
    cursor, _conn = mock_stock_info_db
    cursor.fetchone.return_value = make_stock_info_row(code)
    cursor.fetchall.return_value = make_concept_rows(code)

    row = get_stock_info(code)

    assert row is not None
    assert row["stock_code"] == code
    assert len(row["concepts"]) >= 1
    for concept in row["concepts"]:
        assert set(concept) == {"concept_id", "concept_code", "concept_name", "source", "source_code"}
        assert concept["source"] == "ths"
        assert isinstance(concept["concept_id"], int)


def test_get_stock_info_concepts_use_concept_id_join(mock_stock_info_db):
    cursor, _conn = mock_stock_info_db
    cursor.fetchone.return_value = make_stock_info_row("301236")
    cursor.fetchall.return_value = make_concept_rows("301236")

    get_stock_info("301236")

    assert cursor.execute.call_count == 2
    concept_sql, params = cursor.execute.call_args_list[1].args
    assert "JOIN board_concept c ON c.id = m.concept_id" in concept_sql
    assert "m.concept_code" not in concept_sql
    assert params == ("301236",)


def test_get_stock_info_returns_empty_concepts_when_no_mapping(mock_stock_info_db):
    cursor, _conn = mock_stock_info_db
    cursor.fetchone.return_value = make_stock_info_row("000001")
    cursor.fetchall.return_value = []

    row = get_stock_info("000001")

    assert row is not None
    assert row["concepts"] == []


def test_get_stock_info_missing_stock_does_not_query_concepts(mock_stock_info_db):
    cursor, _conn = mock_stock_info_db
    cursor.fetchone.return_value = None

    row = get_stock_info("999999")

    assert row is None
    assert cursor.execute.call_count == 1
    assert not cursor.fetchall.called
