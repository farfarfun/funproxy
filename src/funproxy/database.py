import os
import sqlite3
import time


def verify_proxy_format(proxy: str) -> bool:
    """检查代理是否符合 IPv4:端口格式。"""
    import re
    verify_regex = r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5}"
    _proxy = re.findall(verify_regex, proxy)
    return True if len(_proxy) == 1 and _proxy[0] == proxy else False


verifyProxyFormat = verify_proxy_format


class ProxyDB:
    """使用标准库 sqlite3 持久化代理池记录。"""

    def __init__(self, db_path: str | None = None, *args, **kwargs) -> None:
        db_path = db_path or os.path.abspath(os.path.dirname(__file__)) + '/data/proxy.db'
        self.db_path = db_path
        self.table_name = "proxy_pool"
        self.create()

    def create(self) -> None:
        """
        state: -1删除 0 不可用 1 可用
        :return:
        """
        directory = os.path.dirname(self.db_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with sqlite3.connect(self.db_path) as db:
            db.execute("""
                create table if not exists {} (
                    proxy                 varchar(20)   primary key
                   ,proxy_ip              varchar(20)
                   ,proxy_port            integer
                   ,from_url              varchar(50)  
                   ,update_time           integer   DEFAULT (0)
                   ,state                 integer   DEFAULT (0) 
                   )
                """.format(self.table_name))
            db.commit()
        self.columns = ['proxy', 'proxy_ip', 'proxy_port', 'from_url', 'update_time', 'state']

    def insert(self, properties: dict, *args, **kwargs) -> None:
        values = self.extend_columns(dict(properties))
        columns = ",".join(values)
        marks = ",".join("?" for _ in values)
        with sqlite3.connect(self.db_path) as db:
            db.execute(f"insert or replace into {self.table_name} ({columns}) values ({marks})", tuple(values.values()))
            db.commit()

    def delete(self, properties: dict, *args, **kwargs) -> None:
        properties = self.extend_columns(properties)
        properties['state'] = -1
        condition = {'proxy': properties.pop('proxy')}
        with sqlite3.connect(self.db_path) as db:
            db.execute(f"update {self.table_name} set state=? where proxy=?", (-1, condition["proxy"]))
            db.commit()

    def count(self, properties: dict, *args, **kwargs) -> int:
        values = self.extend_columns(dict(properties))
        where = " and ".join(f"{key}=?" for key in values)
        with sqlite3.connect(self.db_path) as db:
            return db.execute(f"select count(*) from {self.table_name} where {where}", tuple(values.values())).fetchone()[0]

    def select(self, query: str, *args, **kwargs) -> list[tuple]:
        """执行只读查询并返回记录。"""
        with sqlite3.connect(self.db_path) as db:
            return db.execute(query, args).fetchall()

    @staticmethod
    def extend_columns(properties: dict) -> dict:
        properties['update_time'] = int(time.time())
        if 'proxy' in properties.keys():
            properties['proxy_ip'], properties['proxy_port'] = properties['proxy'].split(':')
        if 'state' not in properties.keys():
            properties['state'] = 1
        return properties
