from requests import Session

from noteproxy.database import ProxyDB

proxy_db = ProxyDB()


class ProxyJob:
    def __init__(self):
        self.proxy = ""
        self.proxies = ""
        self.get_proxy()

    def delete_proxy(self):
        print('delete ' + self.proxy)
        proxy_db.delete({'proxy': self.proxy})

    def change_proxy(self, sess: Session):
        self.get_proxy()
        sess.proxies.update({
            "http": "http://{}".format(self.proxy),
            "https": "http://{}".format(self.proxy),
        })

    def get_proxy(self):
        res = proxy_db.select("select proxy from table_name where state>=1 limit 10")

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
