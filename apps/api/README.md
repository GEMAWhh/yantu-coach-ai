# API

FastAPI 本地后端骨架。当前阶段提供系统端点、统一 API 契约、SQLite 初始化、Alembic 迁移、审计事件、本地文件存储和备份恢复基础，用于验证服务、环境隔离、错误结构、事务和 CI。

## 契约端点

- `GET /health`
- `GET /api/v1/health`
- `GET /api/v1/meta`
- `POST /api/v1/meta/version-check`

成功响应统一使用 `{data, meta}`；错误响应统一使用 `{error}`；每次响应都带 `X-Request-ID`。

## 本地运行

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e "apps/api[dev]"
$env:YANTU_APP_ENV = "dev"
uvicorn app.main:app --app-dir apps/api --host 127.0.0.1 --port 8000 --reload
```

启动时会自动确保 `data/<env>/database/study.db` 初始化到 Alembic head。手动升级命令：

```powershell
$env:YANTU_APP_ENV = "dev"
alembic -c apps/api/alembic.ini upgrade head
```

测试必须设置 `YANTU_APP_ENV=test` 和临时 `YANTU_DATA_ROOT`，不得访问 `data/prod`。

## 文件与备份

当前提供服务层能力，不包含 OCR、PDF 解析或用户上传 UI：

- `app.files.storage.store_original_file`：校验文件名、扩展名、MIME 与文件头，按 SHA-256 去重后写入 `files/original/`。
- `app.files.storage.release_asset_reference`：减少引用计数。
- `app.files.storage.delete_asset_file_if_unreferenced`：只允许删除引用计数为 0 的原始文件。
- `app.files.backup.create_backup`：生成包含 `database/study.db`、`files/` 和 `manifest.json` 的 ZIP。
- `app.files.backup.verify_backup`：校验 manifest、路径安全和每个条目的 SHA-256。
- `app.files.backup.restore_backup`：恢复前自动创建 `pre-restore` 备份，恢复后重新建立运行目录。

## 测试

```powershell
python -m pytest apps/api
ruff format --check apps/api
ruff check apps/api
mypy apps/api/app apps/api/tests
```

## localStorage 导入

阶段 2 提供原型数据一次性导入边界，旧原型 key 固定为
`postgradCoachV11`。

- `POST /api/v1/imports/localstorage/preview`：只解析和生成迁移预览，不写入数据库。
- `POST /api/v1/imports/localstorage/commit`：事务化提交导入批次，按
  `source_key + source_sha256` 幂等；重复提交返回同一个 `batch_id` 且
  `created=false`。

请求体支持三种形态：

```json
{"version": "1.1", "settings": {}, "tasks": [], "knowledge": []}
```

```json
{"postgradCoachV11": "{\"version\":\"1.1\"}"}
```

```json
{"source_key": "postgradCoachV11", "payload": {"version": "1.1"}}
```

导入服务识别原型顶层字段
`version/settings/today/tasks/knowledge/wrongs/resources/inbox/goals/records/adjustments`。
其他顶层字段和二级字段会进入 `unknown_fields`，并保留在迁移报告中。历史
`knowledge` 掌握数据缺少可验证证据，因此只标记为
`imported_unverified`，不会直接升级为稳定掌握。

## 知识节点与前置关系

阶段 3 提供正式知识图谱的最小后端边界：

- `POST /api/v1/knowledge/nodes`：创建知识节点，层级必须遵循
  `subject -> module -> chapter -> knowledge`。
- `GET /api/v1/knowledge/nodes`：按 `parent_id` 查询节点列表，默认过滤软删除。
- `GET /api/v1/knowledge/nodes/{node_id}/tree`：返回节点及子树。
- `PATCH /api/v1/knowledge/nodes/{node_id}`：更新名称、状态、重要度、描述等非结构字段。
- `DELETE /api/v1/knowledge/nodes/{node_id}`：软删除节点子树，并软删除相关边。
- `POST /api/v1/knowledge/edges`：创建关系边，支持
  `belongs_to/prerequisite/similar_to/confused_with/co_tested/transforms_to`。
- `GET /api/v1/knowledge/nodes/{node_id}/prerequisites`：返回前置是否满足和结构化阻塞原因。

当前前置满足规则先使用前置节点 `status` 判断：
`satisfied/mastered/completed` 视为满足，其他状态返回
`PREREQUISITE_NOT_MET`。后续掌握状态机落地后，该判断应切换为正式
`mastery_snapshots`。
