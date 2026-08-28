import os

from notetool.database import SqliteTable
from notetool.tool.time import now2unix


def verifyProxyFormat(proxy):
    """
    检查代理格式
    :param proxy:
    :return:
    """
    import re
    verify_regex = r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5}"
    _proxy = re.findall(verify_regex, proxy)
    return True if len(_proxy) == 1 and _proxy[0] == proxy else False


class ProxyDB(SqliteTable):
    def __init__(self, db_path=None, *args, **kwargs):
        db_path = db_path or os.path.abspath(os.path.dirname(__file__)) + '/data/proxy.db'
        super(ProxyDB, self).__init__(table_name='proxy_pool', db_path=db_path, *args, **kwargs)
        self.create()

    def create(self):
        """
        state: -1删除 0 不可用 1 可用
        :return:
        """
        self.execute("""
                create table if not exists {} (
                    proxy                 varchar(20)   primary key
                   ,proxy_ip              varchar(20)
                   ,proxy_port            integer
                   ,from_url              varchar(50)  
                   ,update_time           integer   DEFAULT (0)
                   ,state                 integer   DEFAULT (0) 
                   )
                """.format(self.table_name))
        self.columns = ['proxy', 'proxy_ip', 'proxy_port', 'from_url', 'update_time', 'state']

    def insert(self, properties: dict, *args, **kwargs):
        return super().insert(self.extend_columns(properties), *args, **kwargs)

    def delete(self, properties: dict, *args, **kwargs):
        properties = self.extend_columns(properties)
        properties['state'] = -1
        condition = {'proxy': properties.pop('proxy')}
        return super().update(properties, condition, *args, **kwargs)

    def count(self, properties: dict, *args, **kwargs):
        properties = self.extend_columns(properties)
        return super(ProxyDB, self).count(properties, *args, **kwargs)

    @staticmethod
    def extend_columns(properties: dict):
        properties['update_time'] = now2unix()
        if 'proxy' in properties.keys():
            properties['proxy_ip'], properties['proxy_port'] = properties['proxy'].split(':')
        if 'state' not in properties.keys():
            properties['state'] = 1
        return properties
