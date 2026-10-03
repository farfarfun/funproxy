# 更新日志

## [Unreleased]

### 新增

- 增加代理格式、SQLite 代理池和 API 凭据环境变量的测试。
- 补充 `GetFreeProxy.run` 调度逻辑、`ProxyPool` 构造、`free_proxy_01`、API 凭据成功/
  失败路径、公开兼容别名（`getHtmlTree`、`verifyProxyFormat`）的测试。

### 修复

- 移除硬编码凭据和库代码 `print`，统一使用 `farlog`。
- 采集 API 改为缺少凭据时安全跳过。
- `job.py`（5 处）、`core.py`（2 处）共 7 处日志误用 stdlib logging 的 `%s` 占位符，
  farlog（loguru）不支持该语法，参数被静默丢弃；统一改为 `{}` 占位符。
- `free_proxy_01` 直接对 `requests.Response` 调用 `.xpath()`（该对象没有此方法），
  一旦真实请求就会抛 `AttributeError`，导致该采集器从未真正工作过；改为统一走
  `get_html_tree` 解析后的节点树。
- `api_proxy_1`（Xila API）在响应内容不足时会 yield 一份硬编码的旧代理地址列表、
  伪装成真实采集结果写入代理池；移除该残留调试数据，改为仅记录警告。
- `get_html_tree`、`free_proxy_01`、`free_proxy_02`、`api_proxy_1`、`api_proxy_2`
  的 `requests.get` 补齐超时（10s）并捕获 `requests.RequestException`，避免单个
  代理源阻塞或中断整个采集流程；`api_proxy_2` 增加 `demjson.JSONDecodeError` 捕获。
- `api_proxy_1` 改用 `https://www.xiladaili.com/api/`（已验证支持 HTTPS）并移除
  `verify=False`；`api_proxy_2` 的 `dev.qydailiip.com` 经验证没有可用的 HTTPS
  监听（TLS 连接超时），仍走 HTTP，已在 docstring 中注明凭据会明文传输、建议
  定期轮换。
- 为 `free_proxy_01`/`free_proxy_12`/`free_proxy_15` 补齐中文 docstring。
- `pyproject.toml` 开发依赖补充 `ruff`，使规范要求的 `ruff check` / `ruff format`
  能在项目虚拟环境中直接执行。

### 变更

- **Breaking:** Renamed the import package and PyPI distribution name from `noteproxy` to `funproxy` to match the repository name. Anyone doing `import noteproxy` or `pip install noteproxy` must switch to `import funproxy` / `pip install funproxy`.

### 废弃

- 删除旧的 setup.py/twine 发布脚本，构建和发布统一使用 `funbuild build`。

### 说明

- 经核实，`noteproxy` 与 `funproxy` 在 PyPI 上均返回 404（从未发布过），因此不存在
  需要发布的"旧包最终转发版本"；上一条目里的转发计划已过时，予以移除。
