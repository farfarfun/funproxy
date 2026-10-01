# funproxy

`funproxy` 是一个轻量代理池工具，提供代理格式校验、SQLite 代理记录和公开代理源采集接口。

## 安装

```bash
pip install funproxy
```

## 最小示例

```python
from funproxy.database import ProxyDB, verify_proxy_format

assert verify_proxy_format("127.0.0.1:8080")
db = ProxyDB("/tmp/funproxy.db")
db.insert({"proxy": "127.0.0.1:8080", "from_url": "example"})
print(db.select("select proxy from proxy_pool"))
```

API 源需要凭据时，请通过 `FUNPROXY_XILA_UUID` 或 `FUNPROXY_QYDAILI_APIKEY` 环境变量提供，
不要把凭据写入代码或提交到仓库。

数据库路径可在构造 `ProxyDB`、`ProxyJob`、`ProxyPool` 或 `GetFreeProxy` 时显式传入，也可通过
`FUNPROXY_DB_PATH` 配置；默认使用用户数据目录下的 `funproxy/proxy.db`。

## 发布

项目统一通过组织工具执行发布流程：`funbuild upgrade` 递增版本，`funbuild install` 验证安装，
`funbuild build` 构建并发布，`funbuild tag` 创建版本标签。

---

## 关于 farfarfun

[farfarfun](https://github.com/farfarfun) 是一个专注于实用工具库的开源组织，
涵盖云存储、数据处理、AI、多媒体与开发工具链等方向。

- 🏠 组织主页：<https://github.com/farfarfun>
- 📦 PyPI：<https://pypi.org/user/niuliangtao/>
- 📧 联系：farfarfun@qq.com

本项目基于 [MIT](LICENSE) 协议开源。
