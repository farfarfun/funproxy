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

    monkeypatch.setattr(requests, "get", lambda _url, **_kwargs: SimpleNamespace(text="127.0.0.1:8080"))
    assert list(GetFreeProxy.free_proxy_02()) == [
        {"proxy": "127.0.0.1:8080", "from_url": "66ip"},
        {"proxy": "127.0.0.1:8080", "from_url": "66ip"},
    ]


def test_free_proxy_parser_request_failure(monkeypatch) -> None:
    from funproxy.job import GetFreeProxy

    def fail_request(_url: str, **_kwargs) -> None:
        raise requests.RequestException("network unavailable")

    monkeypatch.setattr(requests, "get", fail_request)
    assert list(GetFreeProxy.free_proxy_02()) == []


def test_free_proxy_01_uses_html_tree_parser(monkeypatch) -> None:
    """free_proxy_01 曾直接对 requests.Response 调用 .xpath() 而不是解析后的树，
    一旦真实请求就会抛 AttributeError；这里确保它改走 get_html_tree。"""
    from funproxy import job
    from funproxy.job import GetFreeProxy

    monkeypatch.setattr(job, "get_html_tree", lambda _url: None)
    assert list(GetFreeProxy.free_proxy_01()) == []


def test_free_proxy_01_skips_page_on_request_failure(monkeypatch) -> None:
    from funproxy.job import GetFreeProxy

    monkeypatch.setattr(requests, "get", lambda *_a, **_k: (_ for _ in ()).throw(requests.RequestException("timeout")))
    assert list(GetFreeProxy.free_proxy_01()) == []


@pytest.mark.parametrize(
    "collector",
    [
        "free_proxy_02",
        "free_proxy_07",
        "free_proxy_08",
        "free_proxy_10",
        "free_proxy_11",
        "free_proxy_12",
        "free_proxy_13",
        "free_proxy_14",
        "free_proxy_15",
    ],
)
def test_free_proxy_collectors_skip_request_failures(
    monkeypatch, collector: str
) -> None:
    """直接请求页面的采集器在来源不可达时应继续并返回空结果。"""
    from funproxy.job import GetFreeProxy

    monkeypatch.setattr(
        requests,
        "get",
        lambda *_a, **_k: (_ for _ in ()).throw(requests.RequestException("boom")),
    )
    assert list(getattr(GetFreeProxy, collector)()) == []


@pytest.mark.parametrize(
    "collector",
    [
        "free_proxy_03",
        "free_proxy_04",
        "free_proxy_05",
        "free_proxy_06",
        "free_proxy_09",
    ],
)
def test_free_proxy_collectors_skip_empty_html_tree(
    monkeypatch, collector: str
) -> None:
    """依赖 HTML 树的采集器在解析失败时应跳过来源。"""
    from funproxy import job
    from funproxy.job import GetFreeProxy

    monkeypatch.setattr(job, "get_html_tree", lambda _url: None)
    assert list(getattr(GetFreeProxy, collector)()) == []


def test_get_html_tree_returns_none_on_request_failure(monkeypatch) -> None:
    from funproxy.job import get_html_tree, getHtmlTree

    monkeypatch.setattr(requests, "get", lambda *_a, **_k: (_ for _ in ()).throw(requests.RequestException("boom")))
    assert get_html_tree("http://example.invalid") is None
    assert getHtmlTree is get_html_tree


def test_get_free_proxy_run_respects_level_and_inserts_valid_proxies(monkeypatch, tmp_path) -> None:
    """run() 应只调度 level 达标的采集器，并把合法代理写入数据库。"""
    from funproxy.job import GetFreeProxy

    job_instance = GetFreeProxy(db_path=str(tmp_path / "proxy.db"))
    inserted = []
    monkeypatch.setattr(job_instance.proxy_db, "insert", lambda proxy: inserted.append(proxy))
    monkeypatch.setattr(
        GetFreeProxy, "free_proxy_15", staticmethod(lambda: iter([{"proxy": "127.0.0.1:8080"}]))
    )
    monkeypatch.setattr(
        GetFreeProxy, "api_proxy_1", staticmethod(lambda: iter([{"proxy": "1.2.3.4:80", "from_url": "x"}]))
    )

    job_instance.run(level=5)

    # level=5 时只运行 api_proxy_1/api_proxy_2，free_proxy_15（level 3）不应被调度
    assert inserted == [{"proxy": "1.2.3.4:80", "from_url": "x"}]


def test_get_free_proxy_run_skips_malformed_proxy(monkeypatch, tmp_path) -> None:
    from funproxy.job import GetFreeProxy

    job_instance = GetFreeProxy(db_path=str(tmp_path / "proxy.db"))
    inserted = []
    monkeypatch.setattr(job_instance.proxy_db, "insert", lambda proxy: inserted.append(proxy))
    monkeypatch.setattr(
        GetFreeProxy, "api_proxy_1", staticmethod(lambda: iter([{"proxy": ""}, "not-a-dict"]))
    )
    monkeypatch.setattr(GetFreeProxy, "api_proxy_2", staticmethod(lambda: iter([])))

    job_instance.run(level=5)

    assert inserted == []


def test_get_free_proxy_run_continues_after_collector_parse_failure(
    monkeypatch, tmp_path
) -> None:
    """单个采集器的解析异常不应阻止后续来源写入代理。"""
    from funproxy.job import GetFreeProxy

    def fail_collector():
        raise ValueError("invalid source response")
        yield  # pragma: no cover

    job_instance = GetFreeProxy(db_path=str(tmp_path / "proxy.db"))
    inserted = []
    monkeypatch.setattr(
        job_instance.proxy_db, "insert", lambda proxy: inserted.append(proxy)
    )
    monkeypatch.setattr(GetFreeProxy, "api_proxy_1", staticmethod(fail_collector))
    monkeypatch.setattr(
        GetFreeProxy,
        "api_proxy_2",
        staticmethod(lambda: iter([{"proxy": "1.2.3.4:80", "from_url": "qydailiip"}])),
    )

    job_instance.run(level=5)

    assert inserted == [{"proxy": "1.2.3.4:80", "from_url": "qydailiip"}]


def test_api_proxy_1_success_path(monkeypatch) -> None:
    from funproxy.job import GetFreeProxy

    monkeypatch.setenv("FUNPROXY_XILA_UUID", "fake-uuid")
    captured_url = {}

    def fake_get(url, **kwargs):
        captured_url["url"] = url
        return SimpleNamespace(text="1.2.3.4:8080 5.6.7.8:8081")

    monkeypatch.setattr(requests, "get", fake_get)
    result = list(GetFreeProxy.api_proxy_1())
    assert result == [
        {"proxy": "1.2.3.4:8080", "from_url": "xiladaili"},
        {"proxy": "5.6.7.8:8081", "from_url": "xiladaili"},
    ]
    assert captured_url["url"] == "https://www.xiladaili.com/api/"


def test_api_proxy_1_request_failure_returns_nothing(monkeypatch) -> None:
    from funproxy.job import GetFreeProxy

    monkeypatch.setenv("FUNPROXY_XILA_UUID", "fake-uuid")
    monkeypatch.setattr(
        requests, "get", lambda *_a, **_k: (_ for _ in ()).throw(requests.RequestException("boom"))
    )
    assert list(GetFreeProxy.api_proxy_1()) == []


def test_api_proxy_2_success_path(monkeypatch) -> None:
    from funproxy.job import GetFreeProxy

    monkeypatch.setenv("FUNPROXY_QYDAILI_APIKEY", "fake-key")
    captured_url = {}

    def fake_get(url, **kwargs):
        captured_url["url"] = url
        return SimpleNamespace(text='["1.2.3.4:8080", "5.6.7.8:8081"]')

    monkeypatch.setattr(requests, "get", fake_get)
    result = list(GetFreeProxy.api_proxy_2())
    assert result == [
        {"proxy": "1.2.3.4:8080", "from_url": "qydailiip"},
        {"proxy": "5.6.7.8:8081", "from_url": "qydailiip"},
    ]
    assert captured_url["url"] == "http://dev.qydailiip.com/api/"


def test_api_proxy_2_malformed_response_is_skipped(monkeypatch) -> None:
    from funproxy.job import GetFreeProxy

    monkeypatch.setenv("FUNPROXY_QYDAILI_APIKEY", "fake-key")
    monkeypatch.setattr(requests, "get", lambda *_a, **_k: SimpleNamespace(text="not valid json at all......."))
    assert list(GetFreeProxy.api_proxy_2()) == []


def test_verify_proxy_format_alias_is_same_function() -> None:
    from funproxy.database import verifyProxyFormat

    assert verifyProxyFormat is verify_proxy_format


def test_proxy_pool_constructs_with_injected_db_path(tmp_path) -> None:
    """ProxyPool 在无 notetool 依赖时仍应能构造，并使用注入的数据库路径。"""
    from funproxy.core import ProxyPool

    db_path = str(tmp_path / "proxy.db")
    pool = ProxyPool(db_path=db_path)
    assert pool.proxy_db.db_path == db_path
