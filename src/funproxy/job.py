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


def _get_response_text(url: str) -> str | None:
    """获取页面文本；请求失败时记录来源并返回空值。"""
    try:
        return requests.get(url, timeout=10).text
    except requests.RequestException as e:
        logger.warning("请求页面失败 {}: {}", url, e)
        return None


def get_html_tree(url: str) -> etree._Element | None:
    """请求 URL 并解析为 HTML 节点树。

    Args:
        url: 待请求的网页地址。

    Returns:
        解析后的 HTML 根节点，解析失败时返回 None。
    """
    header = {'Connection': 'keep-alive',
              'Cache-Control': 'max-age=0',
              'Upgrade-Insecure-Requests': '1',
              'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_3) AppleWebKit/537.36 (KHTML, like Gecko)',
              'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
              'Accept-Encoding': 'gzip, deflate, sdch',
              'Accept-Language': 'zh-CN,zh;q=0.8',
              }
    try:
        html = requests.get(url=url, headers=header, timeout=10).content
    except requests.RequestException as e:
        logger.warning("请求页面失败 {}: {}", url, e)
        return None
    return etree.HTML(html)


# Backward-compatible alias for existing consumers.
getHtmlTree = get_html_tree


class GetFreeProxy:
    """从公开代理源采集代理记录。"""

    def __init__(self, db_path: str | None = None) -> None:
        """创建采集任务。

        Args:
            db_path: SQLite 文件路径；未提供时由 ProxyDB 解析默认路径。
        """
        self.proxy_db = ProxyDB(db_path=db_path)

    def run(self, level: int = 5) -> None:
        """运行指定等级以上的代理采集器并写入代理池。

        Args:
            level: 要运行的最低采集器等级。

        Returns:
            None。
        """
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
                try:
                    for proxy in method():
                        if isinstance(proxy, dict) and len(proxy['proxy']) > 5:
                            self.proxy_db.insert(proxy)
                except (
                    AttributeError, IndexError, KeyError, TypeError, ValueError
                ) as e:
                    logger.warning("采集器 {} 解析失败，已跳过: {}", method.__name__, e)

    def test(self) -> None:
        """输出一个采集器发现的代理，用于手工检查。"""
        for proxy in self.free_proxy_15():
            logger.info("发现代理 {}", proxy)

    @staticmethod  # -1
    def free_proxy_01() -> Iterator[dict[str, str]]:
        """
        无忧代理 http://www.data5u.com/
        几乎没有能用的

        Returns:
            Iterator[dict[str, str]]: 形如 ``{'proxy': 'ip:port', 'from_url': 'data5u'}``
            的代理记录；页面不可达或解析失败时直接跳过，不中断调用方。
        """
        url_list = [
            'http://www.data5u.com/',
            'http://www.data5u.com/free/gngn/index.shtml',
            'http://www.data5u.com/free/gnpt/index.shtml'
        ]
        key = 'ABCDEFGHIZ'
        for url in url_list:
            html_tree = get_html_tree(url)
            if html_tree is None:
                continue
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
                    logger.warning("解析代理失败: {}", e)

    @staticmethod  # 1
    def free_proxy_02(count: int = 50) -> Iterator[dict[str, str]]:
        """从 66ip 采集指定数量的代理。

        Args:
            count: 每个接口请求的代理数量。

        Returns:
            含 ``proxy`` 和 ``from_url`` 的代理记录；请求失败时跳过该接口。
        """
        urls = [
            "http://www.66ip.cn/mo.php?sxb=&tqsl={}&port=&export=&ktip=&sxa=&submit=%CC%E1++%C8%A1&textarea=",
            "http://www.66ip.cn/nmtq.php?getnum={}&isp=0&anonymoustype=0&s"
            "tart=&ports=&export=&ipaddress=&area=0&proxytype=2&api=66ip"
        ]

        for url in urls:
            html = _get_response_text(url.format(count))
            if html is None:
                continue
            ips = re.findall(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5}", html)
            for ip in ips:
                yield {'proxy': ip.strip(), 'from_url': '66ip'}

    @staticmethod  # 0
    def free_proxy_03(page_count: int = 1) -> Iterator[dict[str, str]]:
        """从西刺代理的高匿和透明列表采集代理。

        Args:
            page_count: 每个列表采集的页数。

        Returns:
            含 ``proxy`` 和 ``from_url`` 的代理记录；请求或页面解析失败时跳过该页。
        """
        url_list = [
            'http://www.xicidaili.com/nn/',  # 高匿
            'http://www.xicidaili.com/nt/',  # 透明
        ]
        for each_url in url_list:
            for i in range(1, page_count + 1):
                page_url = each_url + str(i)
                tree = get_html_tree(page_url)
                if tree is None:
                    continue
                proxy_list = tree.xpath('.//table[@id="ip_list"]//tr[position()>1]')
                for proxy in proxy_list:
                    try:
                        yield {'proxy': ':'.join(proxy.xpath('./td/text()')[0:2]), 'from_url': 'xicidaili'}
                    except (IndexError, ValueError) as e:
                        logger.warning("解析代理失败: {}", e)

    @staticmethod  # 1
    def free_proxy_04() -> Iterator[dict[str, str]]:
        """从 goubanjia 采集并解码混淆端口的代理。

        Returns:
            含 ``proxy`` 和 ``from_url`` 的代理记录；请求或页面解析失败时跳过来源或
            记录。
        """
        url = "http://www.goubanjia.com/"

        tree = get_html_tree(url)
        if tree is None:
            return
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
                logger.warning("解析代理失败: {}", e)

    @staticmethod  # 1
    def free_proxy_05() -> Iterator[dict[str, str]]:
        """从快代理的高匿和透明列表采集代理。

        Returns:
            含 ``proxy`` 和 ``from_url`` 的代理记录；请求或页面解析失败时跳过该页。
        """
        url_list = [
            'https://www.kuaidaili.com/free/inha/',
            'https://www.kuaidaili.com/free/intr/'
        ]
        for url in url_list:
            tree = get_html_tree(url)
            if tree is None:
                continue
            proxy_list = tree.xpath('.//table//tr')
            sleep(1)  # 必须sleep 不然第二条请求不到数据
            for tr in proxy_list[1:]:
                try:
                    yield {'proxy': ':'.join(tr.xpath('./td/text()')[0:2]), 'from_url': 'kuaidaili'}
                except (AttributeError, IndexError, TypeError) as e:
                    logger.warning("解析代理失败 {}: {}", url, e)

    @staticmethod  # 0
    def free_proxy_06() -> Iterator[dict[str, str]]:
        """从码农代理采集代理。

        Returns:
            含 ``proxy`` 和 ``from_url`` 的代理记录；请求或页面解析失败时跳过该页。
        """
        urls = ['https://proxy.coderbusy.com/']
        for url in urls:
            tree = get_html_tree(url)
            if tree is None:
                continue
            proxy_list = tree.xpath('.//table//tr')
            for tr in proxy_list[1:]:
                try:
                    yield {'proxy': ':'.join(tr.xpath('./td/text()')[0:2]), 'from_url': 'proxy.coderbusy'}
                except (AttributeError, IndexError, TypeError) as e:
                    logger.warning("解析代理失败 {}: {}", url, e)

    @staticmethod  # 1
    def free_proxy_07() -> Iterator[dict[str, str]]:
        """从 ip3366 的不同匿名级别列表采集代理。

        Returns:
            含 ``proxy`` 和 ``from_url`` 的代理记录；请求失败时跳过该页。
        """
        urls = ['http://www.ip3366.net/free/?stype=1', "http://www.ip3366.net/free/?stype=2"]
        for url in urls:
            text = _get_response_text(url)
            if text is None:
                continue
            proxies = re.findall(r'<td>(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})</td>[\s\S]*?<td>(\d+)</td>', text)
            for proxy in proxies:
                yield {'proxy': ':'.join(proxy), 'from_url': 'ip3366'}

    @staticmethod  # 0
    def free_proxy_08() -> Iterator[dict[str, str]]:
        """从 IP 海的不同代理列表采集代理。

        Returns:
            含 ``proxy`` 和 ``from_url`` 的代理记录；请求失败时跳过该页。
        """
        urls = [
            'http://www.iphai.com/free/ng',
            'http://www.iphai.com/free/np',
            'http://www.iphai.com/free/wg',
            'http://www.iphai.com/free/wp'
        ]

        for url in urls:
            text = _get_response_text(url)
            if text is None:
                continue
            proxies = re.findall(r'<td>\s*?(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s*?</td>[\s\S]*?<td>\s*?(\d+)\s*?</td>',
                                 text)
            for proxy in proxies:
                yield {'proxy': ':'.join(proxy), 'from_url': 'iphai'}

    @staticmethod  # 1
    def free_proxy_09(page_count: int = 1) -> Iterator[dict[str, str]]:
        """从免费代理库按页采集代理。

        Args:
            page_count: 要采集的页数。

        Returns:
            含 ``proxy`` 和 ``from_url`` 的代理记录；请求或页面解析失败时跳过该页。
        """
        for i in range(1, page_count + 1):
            url = 'http://ip.jiangxianli.com/?country=中国&?page={}'.format(i)
            html_tree = get_html_tree(url)
            if html_tree is None:
                continue
            for index, tr in enumerate(html_tree.xpath("//table//tr")):
                if index == 0:
                    continue
                try:
                    yield {'proxy': ":".join(tr.xpath("./td/text()")[0:2]).strip(), 'from_url': 'jiangxianli'}
                except (AttributeError, IndexError, TypeError) as e:
                    logger.warning("解析代理失败 {}: {}", url, e)

    @staticmethod  # -1
    def free_proxy_10() -> Iterator[dict[str, str]]:
        """从 cn-proxy 的公开页面采集代理。

        Returns:
            含 ``proxy`` 和 ``from_url`` 的代理记录；请求失败时跳过该页。
        """
        urls = ['http://cn-proxy.com/', 'http://cn-proxy.com/archives/218']

        for url in urls:
            text = _get_response_text(url)
            if text is None:
                continue
            proxies = re.findall(r'<td>(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})</td>[\w\W]<td>(\d+)</td>', text)
            for proxy in proxies:
                yield {'proxy': ':'.join(proxy), 'from_url': 'cn-proxy'}

    @staticmethod  # 0
    def free_proxy_11() -> Iterator[dict[str, str]]:
        """从 proxy-list.org 采集 Base64 编码的代理。

        Returns:
            含 ``proxy`` 和 ``from_url`` 的代理记录；请求或解码失败时跳过对应页面或
            记录。
        """
        urls = ['https://proxy-list.org/english/index.php?p=%s' % n for n in range(1, 10)]

        import base64
        for url in urls:
            text = _get_response_text(url)
            if text is None:
                continue
            proxies = re.findall(r"Proxy\('(.*?)'\)", text)
            for proxy in proxies:
                try:
                    yield {'proxy': base64.b64decode(proxy).decode(), 'from_url': 'proxy-list'}
                except (UnicodeDecodeError, ValueError) as e:
                    logger.warning("解析代理失败 {}: {}", url, e)

    @staticmethod  # -1
    def free_proxy_12() -> Iterator[dict[str, str]]:
        """从 proxylistplus 采集 HTTP 代理。

        Returns:
            Iterator[dict[str, str]]: 形如 ``{'proxy': 'ip:port', 'from_url': 'proxylistplus'}``
            的代理记录；请求失败时跳过该页。
        """
        urls = ['https://list.proxylistplus.com/Fresh-HTTP-Proxy-List-1']

        for url in urls:
            text = _get_response_text(url)
            if text is None:
                continue
            proxies = re.findall(r'<td>(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})</td>[\s\S]*?<td>(\d+)</td>', text)
            for proxy in proxies:
                yield {'proxy': ':'.join(proxy), 'from_url': 'proxylistplus'}

    @staticmethod  # 1
    def free_proxy_13(max_page: int = 2) -> Iterator[dict[str, str]]:
        """从齐云代理按页采集中国代理。

        Args:
            max_page: 要采集的最大页数。

        Returns:
            含 ``proxy`` 和 ``from_url`` 的代理记录；请求失败时跳过该页。
        """
        base_url = 'http://www.qydaili.com/free/?action=china&page='

        for page in range(1, max_page + 1):
            url = base_url + str(page)
            text = _get_response_text(url)
            if text is None:
                continue
            proxies = re.findall(r'<td.*?>(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})</td>[\s\S]*?<td.*?>(\d+)</td>', text)
            for proxy in proxies:
                yield {'proxy': ':'.join(proxy), 'from_url': 'qydaili'}

    @staticmethod  # 1
    def free_proxy_14(max_page: int = 2) -> Iterator[dict[str, str]]:
        """从 89 免费代理按页采集代理。

        Args:
            max_page: 要采集的最大页数。

        Returns:
            含 ``proxy`` 和 ``from_url`` 的代理记录；请求失败时跳过该页。
        """
        base_url = 'http://www.89ip.cn/index_{}.html'

        for page in range(1, max_page + 1):
            url = base_url.format(page)
            text = _get_response_text(url)
            if text is None:
                continue
            proxies = re.findall(
                r'<td.*?>[\s\S]*?(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})[\s\S]*?</td>[\s\S]*?<td.*?>[\s\S]*?(\d+)[\s\S]*?</td>',
                text)
            for proxy in proxies:
                yield {'proxy': ':'.join(proxy), 'from_url': '89ip'}

    @staticmethod  # 1
    def free_proxy_15() -> Iterator[dict[str, str]]:
        """从西拉代理的公开列表采集代理。

        Returns:
            Iterator[dict[str, str]]: 形如 ``{'proxy': 'ip:port'}`` 的代理记录，
            不含 ``from_url`` 字段；请求失败时跳过该页。
        """
        urls = ['http://www.xiladaili.com/putong/',
                "http://www.xiladaili.com/gaoni/",
                "http://www.xiladaili.com/http/",
                "http://www.xiladaili.com/https/"]
        for url in urls:
            text = _get_response_text(url)
            if text is None:
                continue
            ips = re.findall(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5}", text)
            for ip in ips:
                yield {'proxy': ip.strip()}

    @staticmethod  # 1
    def api_proxy_1() -> Iterator[dict[str, str]]:
        """从 Xila 代理 API 获取代理。

        Returns:
            含 ``proxy`` 和 ``from_url`` 的代理记录；未配置凭据、请求失败或响应不足时
            不返回记录。
        """
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

        try:
            response = requests.get('https://www.xiladaili.com/api/', params=params, timeout=10)
        except requests.RequestException as e:
            logger.warning("请求 Xila API 失败: {}", e)
            return

        if len(response.text) > 20:
            for proxy in response.text.split(' '):
                yield {'proxy': proxy, 'from_url': 'xiladaili'}
        else:
            logger.warning("Xila API 返回内容不足")

    @staticmethod  # 1
    def api_proxy_2() -> Iterator[dict[str, str]]:
        """从齐云代理 API 获取代理。

        Returns:
            含 ``proxy`` 和 ``from_url`` 的代理记录；未配置凭据、请求或 JSON 解析失败时
            不返回记录。

        注意：服务商 `dev.qydailiip.com` 未提供可用的 HTTPS 端点（TLS 连接会超时），
        仅能通过明文 HTTP 请求；`apikey` 会在传输中以明文暴露，请将其视为低信任凭据，
        并定期在服务商后台轮换。
        """
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

        try:
            response = requests.get('http://dev.qydailiip.com/api/', params=params, timeout=10)
        except requests.RequestException as e:
            logger.warning("请求齐云 API 失败: {}", e)
            return

        if len(response.text) <= 20:
            logger.warning("齐云 API 返回内容不足")
            return

        try:
            proxies = demjson.decode(response.text)
        except demjson.JSONDecodeError as e:
            logger.warning("解析齐云 API 响应失败: {}", e)
            return

        for proxy in proxies:
            yield {'proxy': proxy, 'from_url': 'qydailiip'}
