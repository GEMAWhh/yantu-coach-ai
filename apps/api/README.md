# API

FastAPI 本地后端骨架。当前阶段只提供 `/health` 和 `/api/v1/health`，用于验证服务、环境隔离和 CI。

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
