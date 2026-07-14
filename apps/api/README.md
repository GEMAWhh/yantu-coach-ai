# API

FastAPI 本地后端骨架。当前阶段提供系统端点和统一 API 契约，用于验证服务、环境隔离、错误结构和 CI。

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

## 测试

```powershell
python -m pytest apps/api
ruff format --check apps/api
ruff check apps/api
mypy apps/api/app apps/api/tests
```
