from requests import Session

from noteproxy.database import ProxyDB
from noteproxy.job import GetFreeProxy
from notetool.crawler.core import Node


class ProxyJob:
    proxy_db = ProxyDB()

    def __init__(self):
        self.proxy = ""
        self.proxies = ""
        self.get_proxy()

    def delete_proxy(self):
        print('delete ' + self.proxy)
        self.proxy_db.delete({'proxy': self.proxy})

    def change_proxy(self, sess: Session):
        self.get_proxy()
        sess.proxies.update({
            "http": "http://{}".format(self.proxy),
            "https": "http://{}".format(self.proxy),
        })

    def get_proxy(self):
        res = self.proxy_db.select("select proxy from table_name where state>=1 order by update_time desc limit 10 ")

        if res is None or len(res) == 0:
            print("proxy pool is pool")
            return

        self.proxy = res[0][0]

        self.proxies = {
            "http": "http://{}".format(self.proxy),
            "https": "https://{}".format(self.proxy),
        }
        print('set proxy ' + self.proxy)
        return self.proxy


class ProxyPool(Node):
    def __init__(self, *args, **kwargs):
        super(ProxyPool, self).__init__(*args, **kwargs)
        self.proxy_db = ProxyDB()

    def job(self):
        if self.qsize(0) < 1000:
            proxies = self.proxy_db.select(
                "select proxy from table_name where state>=1 order by update_time desc limit 1000 ")

            for proxy in proxies:
                self.put(proxy[0], index=0)

        while self.not_empty(1):
            proxy = self.get(1)
            self.proxy_db.delete({'proxy': proxy})
            self.logger.info("delete {}".format(proxy))
        job = GetFreeProxy()
        job.run(1)
