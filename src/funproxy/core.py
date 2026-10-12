from requests import Session
from farlog import getLogger

from funproxy.database import ProxyDB
from funproxy.job import GetFreeProxy


logger = getLogger("funproxy")


class ProxyJob:
    """从代理池获取并切换 HTTP 代理。"""
    def __init__(self, db_path: str | None = None) -> None:
        """创建代理任务。

        Args:
            db_path: SQLite 文件路径；未提供时由 ProxyDB 解析默认路径。
        """
        self.proxy_db = ProxyDB(db_path=db_path)
        self.proxy = ""
        self.proxies = ""
        self.get_proxy()

    def delete_proxy(self) -> None:
        """将当前代理标记为已删除。"""
        logger.info("删除代理 {}", self.proxy)
        self.proxy_db.delete({'proxy': self.proxy})

    def change_proxy(self, sess: Session) -> None:
        """从数据库选择代理并更新请求会话。

        Args:
            sess: 要更新 proxies 配置的 requests 会话。
        """
        self.get_proxy()
        sess.proxies.update({
            "http": "http://{}".format(self.proxy),
            "https": "http://{}".format(self.proxy),
        })

    def get_proxy(self) -> str | None:
        """选择最近更新的可用代理。

        Returns:
            代理地址；代理池为空时返回 None。
        """
        res = self.proxy_db.select("select proxy from proxy_pool where state>=1 order by update_time desc limit 10 ")

        if res is None or len(res) == 0:
            logger.warning("代理池为空")
            return

        self.proxy = res[0][0]

        self.proxies = {
            "http": "http://{}".format(self.proxy),
            "https": "https://{}".format(self.proxy),
        }
        logger.info("设置代理 {}", self.proxy)
        return self.proxy


__all__ = ["ProxyJob"]
