"""funproxy 公开 API 与安全边界测试。"""

def test_import():
    import funproxy  # noqa: F401

from funproxy.database import ProxyDB, verify_proxy_format


def test_verify_proxy_format_boundaries() -> None:
    """代理格式校验应接受标准地址并拒绝缺少端口的输入。"""
    assert verify_proxy_format("127.0.0.1:8080")
    assert not verify_proxy_format("127.0.0.1")


def test_proxy_db_insert_and_select(tmp_path) -> None:
    """代理记录应能写入并查询。"""
    db = ProxyDB(str(tmp_path / "proxy.db"))
    db.insert({"proxy": "127.0.0.1:8080", "from_url": "test"})
    assert db.select("select proxy from proxy_pool") == [("127.0.0.1:8080",)]


def test_api_credentials_are_not_required(monkeypatch) -> None:
    """未配置 API 凭据时，采集器应安全返回空结果。"""
    monkeypatch.delenv("FUNPROXY_XILA_UUID", raising=False)
    monkeypatch.delenv("FUNPROXY_QYDAILI_APIKEY", raising=False)
    from funproxy.job import GetFreeProxy

    assert list(GetFreeProxy.api_proxy_1()) == []
    assert list(GetFreeProxy.api_proxy_2()) == []
