import re
from time import sleep

import demjson
import requests
from lxml import etree

from noteproxy.database import ProxyDB


def getHtmlTree(url):
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


class GetFreeProxy(object):

    def __init__(self):
        self.proxy_db = ProxyDB()

    def run(self, level=5):
        methods = [(self.freeProxy01, -1),
                   (self.freeProxy02, 1),
                   (self.freeProxy03, 0),
                   (self.freeProxy04, 1),
                   (self.freeProxy05, 1),
                   (self.freeProxy06, 0),
                   (self.freeProxy07, 1),
                   (self.freeProxy08, 0),
                   (self.freeProxy09, 1),
                   (self.freeProxy10, -1),
                   (self.freeProxy11, 0),
                   (self.freeProxy12, -1),
                   (self.freeProxy13, 2),
                   (self.freeProxy14, 2),
                   (self.freeProxy15, 3),
                   (self.apiProxy1, 5),
                   (self.apiProxy2, 5)
                   ]
        for line in methods:
            if line[1] >= level:
                method = line[0]
                for proxy in method():
                    if isinstance(proxy, dict) and len(proxy['proxy']) > 5:
                        self.proxy_db.insert(proxy)

                # print('{} done'.format(method))

    def test(self):
        for proxy in self.freeProxy15():
            print(proxy)

    @staticmethod  # -1
    def freeProxy01():
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
                except Exception as e:
                    print(e)

    @staticmethod  # 1
    def freeProxy02(count=50):
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
            except Exception as e:
                print(e)

    @staticmethod  # 0
    def freeProxy03(page_count=1):
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
                tree = getHtmlTree(page_url)
                proxy_list = tree.xpath('.//table[@id="ip_list"]//tr[position()>1]')
                for proxy in proxy_list:
                    try:
                        yield {'proxy': ':'.join(proxy.xpath('./td/text()')[0:2]), 'from_url': 'xicidaili'}
                    except Exception as e:
                        pass

    @staticmethod  # 1
    def freeProxy04():

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

        tree = getHtmlTree(url)
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
            except Exception as e:
                print(e)

    @staticmethod  # 1
    def freeProxy05():
        """
        快代理 https://www.kuaidaili.com
        """
        url_list = [
            'https://www.kuaidaili.com/free/inha/',
            'https://www.kuaidaili.com/free/intr/'
        ]
        for url in url_list:
            tree = getHtmlTree(url)
            proxy_list = tree.xpath('.//table//tr')
            sleep(1)  # 必须sleep 不然第二条请求不到数据
            for tr in proxy_list[1:]:
                yield {'proxy': ':'.join(tr.xpath('./td/text()')[0:2]), 'from_url': 'kuaidaili'}

    @staticmethod  # 0
    def freeProxy06():
        """
        码农代理 https://proxy.coderbusy.com/
        :return:
        """
        urls = ['https://proxy.coderbusy.com/']
        for url in urls:
            tree = getHtmlTree(url)
            proxy_list = tree.xpath('.//table//tr')
            for tr in proxy_list[1:]:
                yield {'proxy': ':'.join(tr.xpath('./td/text()')[0:2]), 'from_url': 'proxy.coderbusy'}

    @staticmethod  # 1
    def freeProxy07():
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
    def freeProxy08():
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
    def freeProxy09(page_count=1):
        """
        http://ip.jiangxianli.com/?page=
        免费代理库
        :return:
        """
        for i in range(1, page_count + 1):
            url = 'http://ip.jiangxianli.com/?country=中国&?page={}'.format(i)
            html_tree = getHtmlTree(url)
            for index, tr in enumerate(html_tree.xpath("//table//tr")):
                if index == 0:
                    continue
                yield {'proxy': ":".join(tr.xpath("./td/text()")[0:2]).strip(), 'from_url': 'jiangxianli'}

    @staticmethod  # -1
    def freeProxy10():
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
    def freeProxy11():
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
    def freeProxy12():
        urls = ['https://list.proxylistplus.com/Fresh-HTTP-Proxy-List-1']

        for url in urls:
            r = requests.get(url, timeout=10)
            proxies = re.findall(r'<td>(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})</td>[\s\S]*?<td>(\d+)</td>', r.text)
            for proxy in proxies:
                yield {'proxy': ':'.join(proxy), 'from_url': 'proxylistplus'}

    @staticmethod  # 1
    def freeProxy13(max_page=2):
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
    def freeProxy14(max_page=2):
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
    def freeProxy15():
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
    def apiProxy1():
        params = {
            'uuid': 'b6be7adb55b6464dbde573ce9362081f',
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
            for proxy in res:
                yield {'proxy': proxy, 'from_url': 'xiladaili'}
            print(response.text)

    @staticmethod  # 1
    def apiProxy2():
        params = {
            'apikey': 'e207a65392ddc530997b8d8547cd3273bcb7f057',
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
