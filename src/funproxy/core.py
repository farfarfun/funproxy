from requests import Session
from farlog import getLogger

from funproxy.database import ProxyDB
from funproxy.job import GetFreeProxy
try:
    from notetool.crawler.core import Node
except ImportError:
    class Node:
        """无 notetool 时保证代理池模块可导入的兼容基类。"""

        def __init__(self, *args, **kwargs):
            pass


logger = getLogger("funproxy")


class ProxyJob:
    """从代理池获取并切换 HTTP 代理。"""
    proxy_db = ProxyDB()

    def __init__(self) -> None:
        self.proxy = ""
        self.proxies = ""
        self.get_proxy()

    def delete_proxy(self) -> None:
        logger.info("删除代理 %s", self.proxy)
        self.proxy_db.delete({'proxy': self.proxy})

    def change_proxy(self, sess: Session) -> None:
        self.get_proxy()
        sess.proxies.update({
            "http": "http://{}".format(self.proxy),
            "https": "http://{}".format(self.proxy),
        })

    def get_proxy(self) -> str | None:
        res = self.proxy_db.select("select proxy from proxy_pool where state>=1 order by update_time desc limit 10 ")

        if res is None or len(res) == 0:
            logger.warning("代理池为空")
            return

        self.proxy = res[0][0]

        self.proxies = {
            "http": "http://{}".format(self.proxy),
            "https": "https://{}".format(self.proxy),
        }
        logger.info("设置代理 %s", self.proxy)
        return self.proxy


class ProxyPool(Node):
    """向 notetool 节点队列提供代理任务。"""

    def __init__(self, *args, **kwargs) -> None:
        super(ProxyPool, self).__init__(*args, **kwargs)
        self.proxy_db = ProxyDB()

    def job(self) -> None:
        if self.qsize(0) < 1000:
            proxies = self.proxy_db.select(
                "select proxy from proxy_pool where state>=1 order by update_time desc limit 1000 ")

            for proxy in proxies:
                self.put(proxy[0], index=0)

        while self.not_empty(1):
            proxy = self.get(1)
            self.proxy_db.delete({'proxy': proxy})
            self.logger.info("delete {}".format(proxy))
        job = GetFreeProxy()
        job.run(1)
