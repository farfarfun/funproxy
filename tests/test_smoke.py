"""funproxy 公开 API 与安全边界测试。"""

import importlib
from types import SimpleNamespace

import pytest
import requests
from requests import Session

from funproxy.database import ProxyDB, verify_proxy_format


def test_import_does_not_create_database(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FUNPROXY_DB_PATH", str(tmp_path / "proxy.db"))
    importlib.import_module("funproxy.core")
    assert not (tmp_path / "proxy.db").exists()


def test_verify_proxy_format_boundaries() -> None:
    """代理格式校验应接受标准地址并拒绝缺少端口的输入。"""
    assert verify_proxy_format("127.0.0.1:8080")
    assert not verify_proxy_format("127.0.0.1")


def test_proxy_db_insert_and_select(tmp_path) -> None:
    """代理记录应能写入并查询。"""
    db = ProxyDB(str(tmp_path / "proxy.db"))
    db.insert({"proxy": "127.0.0.1:8080", "from_url": "test"})
    assert db.select("select proxy from proxy_pool") == [("127.0.0.1:8080",)]


def test_proxy_db_uses_environment_path(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "configured" / "proxy.db"
    monkeypatch.setenv("FUNPROXY_DB_PATH", str(db_path))
    db = ProxyDB()
    assert db.db_path == str(db_path)
    assert db_path.is_file()


def test_proxy_db_delete_and_count(tmp_path) -> None:
    db = ProxyDB(str(tmp_path / "proxy.db"))
    db.insert({"proxy": "127.0.0.1:8080", "from_url": "test"})
    assert db.count({"proxy": "127.0.0.1:8080"}) == 1
    db.delete({"proxy": "127.0.0.1:8080"})
    assert db.count({"proxy": "127.0.0.1:8080", "state": -1}) == 1


def test_proxy_db_rejects_invalid_proxy() -> None:
    with pytest.raises(ValueError):
        ProxyDB.extend_columns({"proxy": "invalid"})


def test_proxy_job_selects_and_changes_proxy(tmp_path) -> None:
    from funproxy.core import ProxyJob

    db_path = str(tmp_path / "proxy.db")
    db = ProxyDB(db_path)
    db.insert({"proxy": "127.0.0.1:8080"})
    job = ProxyJob(db_path)
    session = Session()
    job.change_proxy(session)
    assert job.proxy == "127.0.0.1:8080"
    assert session.proxies["http"] == "http://127.0.0.1:8080"


def test_api_credentials_are_not_required(monkeypatch) -> None:
    """未配置 API 凭据时，采集器应安全返回空结果。"""
    monkeypatch.delenv("FUNPROXY_XILA_UUID", raising=False)
    monkeypatch.delenv("FUNPROXY_QYDAILI_APIKEY", raising=False)
    from funproxy.job import GetFreeProxy

    assert list(GetFreeProxy.api_proxy_1()) == []
    assert list(GetFreeProxy.api_proxy_2()) == []


def test_free_proxy_parser_success(monkeypatch) -> None:
    from funproxy.job import GetFreeProxy

    monkeypatch.setattr(requests, "get", lambda _url: SimpleNamespace(text="127.0.0.1:8080"))
    assert list(GetFreeProxy.free_proxy_02()) == [
        {"proxy": "127.0.0.1:8080", "from_url": "66ip"},
        {"proxy": "127.0.0.1:8080", "from_url": "66ip"},
    ]


def test_free_proxy_parser_request_failure(monkeypatch) -> None:
    from funproxy.job import GetFreeProxy

    def fail_request(_url: str) -> None:
        raise requests.RequestException("network unavailable")

    monkeypatch.setattr(requests, "get", fail_request)
    assert list(GetFreeProxy.free_proxy_02()) == []
