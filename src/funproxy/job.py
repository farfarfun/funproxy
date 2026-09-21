import re
import os
from time import sleep
from collections.abc import Iterator

import demjson3 as demjson
import requests
from farlog import getLogger
from lxml import etree

from funproxy.database import ProxyDB

logger = getLogger("funproxy")


def get_html_tree(url: str):
    """请求 URL 并解析为 HTML 节点树。"""
    header = {'Connection': 'keep-alive',
              'Cache-Control': 'max-age=0',
              'Upgrade-Insecure-Requests': '1',
              'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_3) AppleWebKit/537.36 (KHTML, like Gecko)',
              'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
              'Accept-Encoding': 'gzip, deflate, sdch',
              'Accept-Language': 'zh-CN,zh;q=0.8',
              }
    html = requests.get(url=url, headers=header).content
    return etree.HTML(html)


# Backward-compatible alias for existing consumers.
getHtmlTree = get_html_tree


class GetFreeProxy:
    """从公开代理源采集代理记录。"""

    def __init__(self) -> None:
        self.proxy_db = ProxyDB()

    def run(self, level: int = 5) -> None:
        """运行指定等级以上的代理采集器并写入代理池。"""
        methods = [(self.free_proxy_01, -1),
                   (self.free_proxy_02, 1),
                   (self.free_proxy_03, 0),
                   (self.free_proxy_04, 1),
                   (self.free_proxy_05, 1),
                   (self.free_proxy_06, 0),
                   (self.free_proxy_07, 1),
                   (self.free_proxy_08, 0),
                   (self.free_proxy_09, 1),
                   (self.free_proxy_10, -1),
                   (self.free_proxy_11, 0),
                   (self.free_proxy_12, -1),
                   (self.free_proxy_13, 2),
                   (self.free_proxy_14, 2),
                   (self.free_proxy_15, 3),
                   (self.api_proxy_1, 5),
                   (self.api_proxy_2, 5)
                   ]
        for line in methods:
            if line[1] >= level:
                method = line[0]
                for proxy in method():
                    if isinstance(proxy, dict) and len(proxy['proxy']) > 5:
                        self.proxy_db.insert(proxy)

    def test(self) -> None:
        """输出一个采集器发现的代理，用于手工检查。"""
        for proxy in self.free_proxy_15():
            logger.info("发现代理 %s", proxy)

    @staticmethod  # -1
    def free_proxy_01() -> Iterator[dict[str, str]]:
        """
        无忧代理 http://www.data5u.com/
        几乎没有能用的
        :return:
        """
        url_list = [
            'http://www.data5u.com/',
            'http://www.data5u.com/free/gngn/index.shtml',
            'http://www.data5u.com/free/gnpt/index.shtml'
        ]
        key = 'ABCDEFGHIZ'
        for url in url_list:
            html_tree = requests.get(url)
            ul_list = html_tree.xpath('//ul[@class="l2"]')
            for ul in ul_list:
                try:
                    ip = ul.xpath('./span[1]/li/text()')[0]
                    classnames = ul.xpath('./span[2]/li/attribute::class')[0]
                    classname = classnames.split(' ')[1]
                    port_sum = 0
                    for c in classname:
                        port_sum *= 10
                        port_sum += key.index(c)
                    port = port_sum >> 3
                    yield {'proxy': '{}:{}'.format(ip, port), 'from_url': 'data5u'}
                except (IndexError, ValueError, AttributeError) as e:
                    logger.warning("解析代理失败: %s", e)

    @staticmethod  # 1
    def free_proxy_02(count: int = 50) -> Iterator[dict[str, str]]:
        """
        代理66 http://www.66ip.cn/
        :param count: 提取数量
        :return:
        """
        urls = [
            "http://www.66ip.cn/mo.php?sxb=&tqsl={}&port=&export=&ktip=&sxa=&submit=%CC%E1++%C8%A1&textarea=",
            "http://www.66ip.cn/nmtq.php?getnum={}&isp=0&anonymoustype=0&s"
            "tart=&ports=&export=&ipaddress=&area=0&proxytype=2&api=66ip"
        ]

        for url in urls:
            try:
                html = requests.get(url.format(count)).text
                ips = re.findall(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5}", html)
                for ip in ips:
                    yield {'proxy': ip.strip(), 'from_url': '66ip'}
            except (requests.RequestException, AttributeError) as e:
                logger.warning("读取代理失败: %s", e)

    @staticmethod  # 0
    def free_proxy_03(page_count: int = 1) -> Iterator[dict[str, str]]:
        """
        西刺代理 http://www.xicidaili.com
        :return:
        """
        url_list = [
            'http://www.xicidaili.com/nn/',  # 高匿
            'http://www.xicidaili.com/nt/',  # 透明
        ]
        for each_url in url_list:
            for i in range(1, page_count + 1):
                page_url = each_url + str(i)
                tree = get_html_tree(page_url)
                proxy_list = tree.xpath('.//table[@id="ip_list"]//tr[position()>1]')
                for proxy in proxy_list:
                    try:
                        yield {'proxy': ':'.join(proxy.xpath('./td/text()')[0:2]), 'from_url': 'xicidaili'}
                    except (IndexError, ValueError) as e:
                        logger.warning("解析代理失败: %s", e)

    @staticmethod  # 1
    def free_proxy_04() -> Iterator[dict[str, str]]:

        """
        # 此网站有隐藏的数字干扰，或抓取到多余的数字或.符号
        # 需要过滤掉<p style="display:none;">的内容

        # :符号裸放在td下，其他放在div span p中，先分割找出ip，再找port

        # HTML中的port是随机数，真正的端口编码在class后面的字母中。
        # 比如这个：
        # <span class="port CFACE">9054</span>
        # CFACE解码后对应的是3128。
        guobanjia http://www.goubanjia.com/
        :return:
        """
        url = "http://www.goubanjia.com/"

        tree = get_html_tree(url)
        proxy_list = tree.xpath('//td[@class="ip"]')
        xpath_str = """.//*[not(contains(@style, 'display: none')) and not(contains(@style, 'display:none'))
                                        and not(contains(@class, 'port')) ]/text()"""
        for each_proxy in proxy_list:
            try:
                ip_addr = ''.join(each_proxy.xpath(xpath_str))
                port = 0
                for _ in each_proxy.xpath(".//span[contains(@class, 'port')]/attribute::class")[0].replace("port ", ""):
                    port *= 10
                    port += (ord(_) - ord('A'))
                port /= 8

                yield {'proxy': '{}:{}'.format(ip_addr, int(port)), 'from_url': 'goubanjia'}
            except (IndexError, ValueError, TypeError, AttributeError) as e:
                logger.warning("解析代理失败: %s", e)

    @staticmethod  # 1
    def free_proxy_05() -> Iterator[dict[str, str]]:
        """
        快代理 https://www.kuaidaili.com
        """
        url_list = [
            'https://www.kuaidaili.com/free/inha/',
            'https://www.kuaidaili.com/free/intr/'
        ]
        for url in url_list:
            tree = get_html_tree(url)
            proxy_list = tree.xpath('.//table//tr')
            sleep(1)  # 必须sleep 不然第二条请求不到数据
            for tr in proxy_list[1:]:
                yield {'proxy': ':'.join(tr.xpath('./td/text()')[0:2]), 'from_url': 'kuaidaili'}

    @staticmethod  # 0
    def free_proxy_06() -> Iterator[dict[str, str]]:
        """
        码农代理 https://proxy.coderbusy.com/
        :return:
        """
        urls = ['https://proxy.coderbusy.com/']
        for url in urls:
            tree = get_html_tree(url)
            proxy_list = tree.xpath('.//table//tr')
            for tr in proxy_list[1:]:
                yield {'proxy': ':'.join(tr.xpath('./td/text()')[0:2]), 'from_url': 'proxy.coderbusy'}

    @staticmethod  # 1
    def free_proxy_07() -> Iterator[dict[str, str]]:
        """
        云代理 http://www.ip3366.net/free/
        :return:
        """
        urls = ['http://www.ip3366.net/free/?stype=1', "http://www.ip3366.net/free/?stype=2"]
        for url in urls:
            r = requests.get(url, timeout=10)
            proxies = re.findall(r'<td>(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})</td>[\s\S]*?<td>(\d+)</td>', r.text)
            for proxy in proxies:
                yield {'proxy': ':'.join(proxy), 'from_url': 'ip3366'}

    @staticmethod  # 0
    def free_proxy_08() -> Iterator[dict[str, str]]:
        """
        IP海 http://www.iphai.com/free/ng
        :return:
        """
        urls = [
            'http://www.iphai.com/free/ng',
            'http://www.iphai.com/free/np',
            'http://www.iphai.com/free/wg',
            'http://www.iphai.com/free/wp'
        ]

        for url in urls:
            r = requests.get(url, timeout=10)
            proxies = re.findall(r'<td>\s*?(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s*?</td>[\s\S]*?<td>\s*?(\d+)\s*?</td>',
                                 r.text)
            for proxy in proxies:
                yield {'proxy': ':'.join(proxy), 'from_url': 'iphai'}

    @staticmethod  # 1
    def free_proxy_09(page_count: int = 1) -> Iterator[dict[str, str]]:
        """
        http://ip.jiangxianli.com/?page=
        免费代理库
        :return:
        """
        for i in range(1, page_count + 1):
            url = 'http://ip.jiangxianli.com/?country=中国&?page={}'.format(i)
            html_tree = get_html_tree(url)
            for index, tr in enumerate(html_tree.xpath("//table//tr")):
                if index == 0:
                    continue
                yield {'proxy': ":".join(tr.xpath("./td/text()")[0:2]).strip(), 'from_url': 'jiangxianli'}

    @staticmethod  # -1
    def free_proxy_10() -> Iterator[dict[str, str]]:
        """
        墙外网站 cn-proxy
        :return:
        """
        urls = ['http://cn-proxy.com/', 'http://cn-proxy.com/archives/218']

        for url in urls:
            r = requests.get(url, timeout=10)
            proxies = re.findall(r'<td>(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})</td>[\w\W]<td>(\d+)</td>', r.text)
            for proxy in proxies:
                yield {'proxy': ':'.join(proxy), 'from_url': 'cn-proxy'}

    @staticmethod  # 0
    def free_proxy_11() -> Iterator[dict[str, str]]:
        """
        https://proxy-list.org/english/index.php
        :return:
        """
        urls = ['https://proxy-list.org/english/index.php?p=%s' % n for n in range(1, 10)]

        import base64
        for url in urls:
            r = requests.get(url, timeout=10)
            proxies = re.findall(r"Proxy\('(.*?)'\)", r.text)
            for proxy in proxies:
                yield {'proxy': base64.b64decode(proxy).decode(), 'from_url': 'proxy-list'}

    @staticmethod  # -1
    def free_proxy_12() -> Iterator[dict[str, str]]:
        urls = ['https://list.proxylistplus.com/Fresh-HTTP-Proxy-List-1']

        for url in urls:
            r = requests.get(url, timeout=10)
            proxies = re.findall(r'<td>(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})</td>[\s\S]*?<td>(\d+)</td>', r.text)
            for proxy in proxies:
                yield {'proxy': ':'.join(proxy), 'from_url': 'proxylistplus'}

    @staticmethod  # 1
    def free_proxy_13(max_page: int = 2) -> Iterator[dict[str, str]]:
        """
        http://www.qydaili.com/free/?action=china&page=1
        齐云代理
        :param max_page:
        :return:
        """
        base_url = 'http://www.qydaili.com/free/?action=china&page='

        for page in range(1, max_page + 1):
            url = base_url + str(page)
            r = requests.get(url, timeout=10)
            proxies = re.findall(r'<td.*?>(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})</td>[\s\S]*?<td.*?>(\d+)</td>', r.text)
            for proxy in proxies:
                yield {'proxy': ':'.join(proxy), 'from_url': 'qydaili'}

    @staticmethod  # 1
    def free_proxy_14(max_page: int = 2) -> Iterator[dict[str, str]]:
        """
        http://www.89ip.cn/index.html
        89免费代理
        :param max_page:
        :return:
        """
        base_url = 'http://www.89ip.cn/index_{}.html'

        for page in range(1, max_page + 1):
            url = base_url.format(page)
            r = requests.get(url, timeout=10)
            proxies = re.findall(
                r'<td.*?>[\s\S]*?(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})[\s\S]*?</td>[\s\S]*?<td.*?>[\s\S]*?(\d+)[\s\S]*?</td>',
                r.text)
            for proxy in proxies:
                yield {'proxy': ':'.join(proxy), 'from_url': '89ip'}

    @staticmethod  # 1
    def free_proxy_15() -> Iterator[dict[str, str]]:
        urls = ['http://www.xiladaili.com/putong/',
                "http://www.xiladaili.com/gaoni/",
                "http://www.xiladaili.com/http/",
                "http://www.xiladaili.com/https/"]
        for url in urls:
            r = requests.get(url, timeout=10)
            ips = re.findall(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5}", r.text)
            for ip in ips:
                yield {'proxy': ip.strip()}

    @staticmethod  # 1
    def api_proxy_1() -> Iterator[dict[str, str]]:
        """从 Xila 代理 API 获取代理，需要环境变量凭据。"""
        uuid = os.getenv("FUNPROXY_XILA_UUID")
        if not uuid:
            logger.warning("未配置 FUNPROXY_XILA_UUID，跳过 Xila API")
            return
        params = {
            'uuid': uuid,
            'num': 50,
            'protocol': 2,
            'sortby': 2,
            'repeat': 1,
            'format': 3,
            'position': 1,
        }

        response = requests.get('http://www.xiladaili.com/api/', params=params, proxies=None, verify=False, )

        if len(response.text) > 20:
            for proxy in response.text.split(' '):
                yield {'proxy': proxy, 'from_url': 'xiladaili'}
        else:
            res = '222.85.28.130:52590 58.220.95.80:9401 58.220.95.86:9401 119.178.101.18:8888 221.122.91.76:9480 58.220.95.78:9401 58.220.95.79:10000 1.119.166.180:8080 183.220.145.3:80 221.122.91.75:10286 150.138.253.71:808 221.122.91.74:9401'
            for proxy in res.split():
                yield {'proxy': proxy, 'from_url': 'xiladaili'}
            logger.warning("Xila API 返回内容不足")

    @staticmethod  # 1
    def api_proxy_2() -> Iterator[dict[str, str]]:
        """从齐云代理 API 获取代理，需要环境变量凭据。"""
        apikey = os.getenv("FUNPROXY_QYDAILI_APIKEY")
        if not apikey:
            logger.warning("未配置 FUNPROXY_QYDAILI_APIKEY，跳过齐云 API")
            return
        params = {
            'apikey': apikey,
            'num': '50',
            'type': 'json',
            'line': 'win',
            'proxy_type': 'putong',
            'sort': '1',
            'model': 'all',
            'protocol': 'https',
            'address': '',
            'kill_address': '',
            'port': '',
            'kill_port': '',
            'today': 'true',
            'abroad': '1',
            'isp': '',
            'anonymity': '',
        }

        response = requests.get('http://dev.qydailiip.com/api/', params=params, verify=False, )
        if len(response.text) > 20:
            for proxy in demjson.decode(response.text):
                yield {'proxy': proxy, 'from_url': 'qydailiip'}
