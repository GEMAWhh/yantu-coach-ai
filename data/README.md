# Runtime Data

运行时数据目录由后端按环境自动创建，不提交到仓库。

默认目录：

```text
data/dev/
data/test/
data/prod/
```

开发和测试不得读写 `data/prod/`。正式数据目录只允许在明确设置 `YANTU_APP_ENV=prod` 时使用。
