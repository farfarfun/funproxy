import os
import sqlite3
import time
from pathlib import Path


def _default_db_path() -> str:
    configured_path = os.getenv("FUNPROXY_DB_PATH")
    if configured_path:
        return configured_path

    data_home = os.getenv("XDG_DATA_HOME")
    base_directory = Path(data_home) if data_home else Path.home() / ".local" / "share"
    return str(base_directory / "funproxy" / "proxy.db")


def verify_proxy_format(proxy: str) -> bool:
    """检查代理地址是否符合 IPv4:端口格式。

    Args:
        proxy: 待检查的代理地址。

    Returns:
        完整匹配 IPv4:端口形式时返回 True，否则返回 False。
    """
    import re
    verify_regex = r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5}"
    _proxy = re.findall(verify_regex, proxy)
    return True if len(_proxy) == 1 and _proxy[0] == proxy else False


verifyProxyFormat = verify_proxy_format


class ProxyDB:
    """使用标准库 sqlite3 持久化代理池记录。"""

    def __init__(self, db_path: str | None = None) -> None:
        """创建代理数据库。

        Args:
            db_path: SQLite 文件路径。未提供时依次使用 FUNPROXY_DB_PATH 和
                用户数据目录下的 funproxy/proxy.db。
        """
        self.db_path = db_path or _default_db_path()
        self.table_name = "proxy_pool"
        self.create()

    def create(self) -> None:
        """创建数据库目录和代理表。

        Returns:
            None。state 字段中 -1 表示删除，0 表示不可用，1 表示可用。
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

    def insert(self, properties: dict[str, object], *args: object, **kwargs: object) -> None:
        """插入或替换代理记录。

        Args:
            properties: 至少包含 ``proxy`` 的记录字段。
            *args: 保留的兼容参数，不参与处理。
            **kwargs: 保留的兼容参数，不参与处理。

        Returns:
            None。
        """
        values = self.extend_columns(dict(properties))
        columns = ",".join(values)
        marks = ",".join("?" for _ in values)
        with sqlite3.connect(self.db_path) as db:
            db.execute(f"insert or replace into {self.table_name} ({columns}) values ({marks})", tuple(values.values()))
            db.commit()

    def delete(self, properties: dict[str, object], *args: object, **kwargs: object) -> None:
        """将指定代理标记为已删除。

        Args:
            properties: 包含 ``proxy`` 的记录字段。
            *args: 保留的兼容参数，不参与处理。
            **kwargs: 保留的兼容参数，不参与处理。

        Returns:
            None。
        """
        properties = self.extend_columns(properties)
        properties['state'] = -1
        condition = {'proxy': properties.pop('proxy')}
        with sqlite3.connect(self.db_path) as db:
            db.execute(f"update {self.table_name} set state=? where proxy=?", (-1, condition["proxy"]))
            db.commit()

    def count(self, properties: dict[str, object], *args: object, **kwargs: object) -> int:
        """统计匹配字段的代理记录数。

        Args:
            properties: 用作查询条件的记录字段。
            *args: 保留的兼容参数，不参与处理。
            **kwargs: 保留的兼容参数，不参与处理。

        Returns:
            匹配的记录数。
        """
        values = dict(properties)
        where = " and ".join(f"{key}=?" for key in values)
        with sqlite3.connect(self.db_path) as db:
            return db.execute(f"select count(*) from {self.table_name} where {where}", tuple(values.values())).fetchone()[0]

    def select(self, query: str, *args: object, **kwargs: object) -> list[tuple[object, ...]]:
        """执行只读查询并返回记录。

        Args:
            query: 带问号占位符的 SQL 查询。
            *args: 按顺序绑定到查询占位符的值。
            **kwargs: 保留的兼容参数，不参与处理。

        Returns:
            查询结果元组列表。
        """
        with sqlite3.connect(self.db_path) as db:
            return db.execute(query, args).fetchall()

    @staticmethod
    def extend_columns(properties: dict[str, object]) -> dict[str, object]:
        """补充代理记录的派生字段和默认字段。

        Args:
            properties: 要原地补充的代理记录。

        Returns:
            补充后的同一个记录字典。

        Raises:
            ValueError: ``proxy`` 不含冒号分隔的地址和端口时抛出。
        """
        properties['update_time'] = int(time.time())
        if 'proxy' in properties.keys():
            properties['proxy_ip'], properties['proxy_port'] = properties['proxy'].split(':')
        if 'state' not in properties.keys():
            properties['state'] = 1
        return properties
