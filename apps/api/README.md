# API

FastAPI 本地后端骨架。当前阶段提供系统端点、统一 API 契约、SQLite 初始化、Alembic 迁移和审计事件基础，用于验证服务、环境隔离、错误结构、事务和 CI。

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

## 测试

```powershell
python -m pytest apps/api
ruff format --check apps/api
ruff check apps/api
mypy apps/api/app apps/api/tests
```
