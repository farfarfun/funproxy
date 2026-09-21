# 更新日志

## [Unreleased]

### 新增

- 增加代理格式、SQLite 代理池和 API 凭据环境变量的测试。

### 修复

- 移除硬编码凭据和库代码 `print`，统一使用 `farlog`。
- 采集 API 改为缺少凭据时安全跳过。

### 变更

- **Breaking:** Renamed the import package and PyPI distribution name from `noteproxy` to `funproxy` to match the repository name. Anyone doing `import noteproxy` or `pip install noteproxy` must switch to `import funproxy` / `pip install funproxy`.
- The old `noteproxy` PyPI package will receive one final release that forwards to `funproxy` (manual follow-up by the repo owner, not part of this change).

### 废弃

- 删除旧的 setup.py/twine 发布脚本，构建使用 `uv build`。
